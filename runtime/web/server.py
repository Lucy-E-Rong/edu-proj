from __future__ import annotations

import json
import shutil
import subprocess
import sys
import uuid
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core.config import load_config
from core.modeling import ChatModel, ModelSettings
from evaluation.run_eval import evaluate_output
from runtime.web.adapter_registry import (
    adapter_exists,
    get_adapter,
    list_adapters,
    register_adapter,
    validate_adapter_name,
)
from runtime.workflow.orchestrator import Orchestrator


REPO_ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = Path(__file__).resolve().parent / "static"
SUPPORTED_UPLOAD_EXTS = {".md", ".txt", ".pdf"}
JOBS: Dict[str, Dict[str, Any]] = {}
SESSIONS: Dict[str, Dict[str, Any]] = {}


app = FastAPI(title="Local Educator Web UI")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class ChatGenerateRequest(BaseModel):
    adapter_name: str
    task_type: str
    prompt: str
    use_rag: bool = True


class RefineRequest(BaseModel):
    session_id: str
    prompt_match_score: int
    source_learning_score: int
    teaching_usefulness_score: int
    correction_note: str = ""
    feedback: str


def _cfg() -> Dict[str, Any]:
    return load_config(str(REPO_ROOT / "configs/config.yaml"))


def _task_to_runtime(task_type: str) -> str:
    if task_type not in {"lesson", "practice", "incident", "rubric"}:
        raise HTTPException(status_code=400, detail=f"Unsupported task_type: {task_type}")
    return f"generate_{task_type}"


def _config_for_adapter(config: Dict[str, Any], adapter_name: str) -> tuple[Dict[str, Any], str, str]:
    adapter = get_adapter(config, adapter_name)
    if adapter is None:
        raise HTTPException(status_code=404, detail=f"Unknown adapter: {adapter_name}")
    profile_name = adapter_name
    updated = deepcopy(config)
    updated.setdefault("runtime", {}).setdefault("model_profiles", {})[profile_name] = {
        "adapter_path": adapter.get("adapter_path"),
        "description": adapter.get("description", ""),
    }
    model_type = "teacher_eval" if adapter.get("type") == "teacher" else "cybersecurity_eval"
    return updated, profile_name, model_type


def _corrected_final_score(evaluation: Dict[str, Any], scores: Dict[str, int]) -> float:
    llm_avg = (
        scores["prompt_match_score"]
        + scores["source_learning_score"]
        + scores["teaching_usefulness_score"]
    ) / 3.0
    hard_score = float(evaluation.get("hard_result", {}).get("score", 0.0))
    return round(hard_score * 0.35 + llm_avg * 0.65, 2)


def _session_path(session_id: str) -> Path:
    return REPO_ROOT / "runs" / "web_sessions" / session_id / "session.json"


def _save_session(session: Dict[str, Any]) -> None:
    path = _session_path(session["session_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(session, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _run_job(job_id: str, adapter_name: str, description: str, source_files: List[str]) -> None:
    job = JOBS[job_id]

    def log(message: str) -> None:
        job["log"].append(message)

    try:
        config = _cfg()
        course_root = REPO_ROOT / "data" / "teachers" / adapter_name
        extracted = course_root / "extracted" / "blocks.jsonl"
        train_out = course_root / "processed" / "train.jsonl"
        eval_out = course_root / "processed" / "eval.jsonl"
        base_model = config["model"]["base_model_dir"]
        general_adapter = config["runtime"]["model_profiles"]["general"]["adapter_path"]

        commands = [
            [
                sys.executable,
                "-m",
                "training.data_build.extract_teacher_corpus",
                "--source-dir",
                str(course_root / "original"),
                "--course-id",
                adapter_name,
                "--out",
                str(extracted),
            ],
            [
                sys.executable,
                "-m",
                "training.data_build.generate_teacher_jsonl",
                "--extracted-file",
                str(extracted),
                "--train-out",
                str(train_out),
                "--eval-out",
                str(eval_out),
                "--model-path",
                base_model,
                "--adapter-path",
                general_adapter,
                "--torch-dtype",
                config["model"].get("torch_dtype", "bfloat16"),
            ],
            [
                sys.executable,
                "-m",
                "training.data_build.validate_teacher_jsonl",
                "--train-file",
                str(train_out),
                "--eval-file",
                str(eval_out),
            ],
            [
                sys.executable,
                "training/train_lora.py",
                "--mode",
                "teacher",
                "--config",
                "configs/config.yaml",
                "--init-adapter",
                general_adapter,
                "--train-file",
                str(train_out),
                "--eval-file",
                str(eval_out),
            ],
        ]

        job["status"] = "running"
        for command in commands:
            log("$ " + " ".join(command))
            completed = subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True)
            if completed.stdout:
                log(completed.stdout.strip())
            if completed.stderr:
                log(completed.stderr.strip())
            if completed.returncode != 0:
                raise RuntimeError(f"Command failed with exit code {completed.returncode}: {' '.join(command)}")

        adapter_path = ""
        for line in reversed(job["log"]):
            if "Adapter saved to " in line:
                adapter_path = line.rsplit("Adapter saved to ", 1)[1].strip().splitlines()[-1]
                break
        if not adapter_path:
            candidates = sorted((REPO_ROOT / "runs").glob("*_teacher_train/adapter"), key=lambda p: p.stat().st_mtime)
            if not candidates:
                raise RuntimeError("Training finished but no adapter directory was found.")
            adapter_path = str(candidates[-1].relative_to(REPO_ROOT))

        record = register_adapter(
            name=adapter_name,
            adapter_path=adapter_path,
            source_files=source_files,
            description=description,
            status="ready",
        )
        job["adapter"] = record
        job["status"] = "ready"
        log(f"Adapter registered: {adapter_path}")
    except Exception as exc:
        job["status"] = "failed"
        job["error"] = str(exc)
        log(f"ERROR: {exc}")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/adapters")
def api_list_adapters() -> Dict[str, Any]:
    return {"adapters": list_adapters(_cfg())}


@app.post("/api/adapters/create")
async def api_create_adapter(
    background_tasks: BackgroundTasks,
    adapter_name: str = Form(...),
    description: str = Form(""),
    files: List[UploadFile] = File(...),
) -> Dict[str, Any]:
    config = _cfg()
    try:
        name = validate_adapter_name(adapter_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if adapter_exists(config, name):
        raise HTTPException(status_code=409, detail=f"Adapter name already exists: {name}")
    if any(
        job.get("adapter_name") == name and job.get("status") in {"queued", "running"}
        for job in JOBS.values()
    ):
        raise HTTPException(status_code=409, detail=f"Adapter creation is already running: {name}")

    unsupported = [file.filename for file in files if Path(file.filename or "").suffix.lower() not in SUPPORTED_UPLOAD_EXTS]
    if unsupported:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Unsupported upload file type.",
                "unsupported_files": unsupported,
                "supported_file_types": sorted(SUPPORTED_UPLOAD_EXTS),
            },
        )

    original_dir = REPO_ROOT / "data" / "teachers" / name / "original"
    original_dir.mkdir(parents=True, exist_ok=True)
    saved_files: List[str] = []
    for upload in files:
        if not upload.filename:
            continue
        target = original_dir / Path(upload.filename).name
        with target.open("wb") as f:
            shutil.copyfileobj(upload.file, f)
        saved_files.append(str(target.relative_to(REPO_ROOT)))

    job_id = uuid.uuid4().hex
    JOBS[job_id] = {
        "job_id": job_id,
        "adapter_name": name,
        "status": "queued",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "log": [],
    }
    background_tasks.add_task(_run_job, job_id, name, description, saved_files)
    return {"job_id": job_id, "adapter_name": name, "status": "queued", "source_files": saved_files}


@app.get("/api/jobs/{job_id}")
def api_job_status(job_id: str) -> Dict[str, Any]:
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Unknown job: {job_id}")
    return job


@app.post("/api/chat/generate")
def api_chat_generate(request: ChatGenerateRequest) -> Dict[str, Any]:
    config, profile_name, model_type = _config_for_adapter(_cfg(), request.adapter_name)
    task_type = _task_to_runtime(request.task_type)
    orchestrator = Orchestrator(config, model_profile=profile_name)
    result = orchestrator.run(
        task_type=task_type,
        user_prompt=request.prompt,
        use_rag=request.use_rag,
        interactive_refinement=False,
    )
    evaluation = evaluate_output(
        model_type=model_type,
        prompt=f"{request.task_type}: {request.prompt}",
        output_text=result["output"],
        config_path=str(REPO_ROOT / "configs/config.yaml"),
    )
    session_id = uuid.uuid4().hex
    session = {
        "session_id": session_id,
        "adapter_name": request.adapter_name,
        "task_type": request.task_type,
        "prompt": request.prompt,
        "use_rag": request.use_rag,
        "rounds": [
            {
                "round": 0,
                "output": result["output"],
                "evaluation": evaluation,
                "run_id": result["run_id"],
            }
        ],
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    SESSIONS[session_id] = session
    _save_session(session)
    return {"session": session, "current_round": session["rounds"][-1]}


@app.post("/api/chat/refine")
def api_chat_refine(request: RefineRequest) -> Dict[str, Any]:
    session = SESSIONS.get(request.session_id)
    if session is None:
        path = _session_path(request.session_id)
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"Unknown session: {request.session_id}")
        session = json.loads(path.read_text(encoding="utf-8"))
        SESSIONS[request.session_id] = session

    existing_refinements = len(session["rounds"]) - 1
    if existing_refinements >= 2:
        raise HTTPException(status_code=400, detail="Maximum of two refinement rounds reached.")
    if not request.feedback.strip():
        raise HTTPException(status_code=400, detail="Refinement feedback is required.")

    scores = {
        "prompt_match_score": request.prompt_match_score,
        "source_learning_score": request.source_learning_score,
        "teaching_usefulness_score": request.teaching_usefulness_score,
    }
    if any(value not in {0, 1, 2} for value in scores.values()):
        raise HTTPException(status_code=400, detail="Scores must be 0, 1, or 2.")

    previous = session["rounds"][-1]
    previous["teacher_corrected_llm_result"] = scores
    previous["teacher_corrected_final_score"] = _corrected_final_score(previous["evaluation"], scores)
    previous["teacher_correction_note"] = request.correction_note
    previous["refinement_feedback"] = request.feedback

    config, profile_name, model_type = _config_for_adapter(_cfg(), session["adapter_name"])
    adapter = get_adapter(config, session["adapter_name"])
    model = ChatModel(
        ModelSettings(
            model_path=config["model"]["base_model_dir"],
            torch_dtype=config["model"].get("torch_dtype", "bfloat16"),
            adapter_path=(adapter or {}).get("adapter_path"),
        )
    )
    refine_prompt = (
        "Revise the previous answer using the teacher feedback while preserving educational quality and safety.\n\n"
        f"Original user request:\n{session['prompt']}\n\n"
        f"Teacher feedback:\n{request.feedback}\n\n"
        f"Previous answer:\n{previous['output']}"
    )
    output = model.generate(
        messages=[{"role": "user", "content": refine_prompt}],
        max_new_tokens=500,
        temperature=0.4,
        do_sample=True,
        add_generation_prompt=True,
    )
    evaluation = evaluate_output(
        model_type=model_type,
        prompt=f"{session['task_type']}: {session['prompt']}",
        output_text=output,
        config_path=str(REPO_ROOT / "configs/config.yaml"),
    )
    round_record = {
        "round": existing_refinements + 1,
        "output": output,
        "evaluation": evaluation,
    }
    session["rounds"].append(round_record)
    _save_session(session)
    return {"session": session, "current_round": round_record}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("runtime.web.server:app", host="127.0.0.1", port=8000, reload=True)
