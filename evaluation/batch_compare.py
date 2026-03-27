from __future__ import annotations

import argparse
import builtins
import json
from pathlib import Path
from typing import Any, Dict, List

from evaluation.run_eval import evaluate_output


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _save_general_output(prompt: str, output_text: str, adapter_path: str, output_file: Path) -> None:
    content = [
        "# Inference Output",
        f"- adapter: {adapter_path}",
        "",
        "## PROMPT",
        prompt,
        "",
        "## OUTPUT",
        output_text,
        "",
    ]
    output_file.write_text("\n".join(content), encoding="utf-8")


def _generate_general(
    prompt_row: Dict[str, Any],
    model: Any,
    adapter_path: str,
    output_dir: Path,
) -> Dict[str, str]:
    output_file = output_dir / f"{prompt_row['id']}_general.md"
    output_text = model.generate(
        messages=[{"role": "user", "content": prompt_row["prompt"]}],
        max_new_tokens=1000,
        temperature=0.7,
        do_sample=True,
        add_generation_prompt=True,
    )
    _save_general_output(prompt_row["prompt"], output_text, adapter_path, output_file)
    return {
        "output_text": output_text.strip(),
        "output_path": str(output_file.relative_to(REPO_ROOT)),
        "run_id": "",
    }


def _generate_teacher(prompt_row: Dict[str, Any], orchestrator: Any, output_dir: Path) -> Dict[str, str]:
    from runtime.workflow.orchestrator import SharedMemory

    orchestrator.memory = SharedMemory()
    original_input = builtins.input
    builtins.input = lambda _prompt="": ""
    try:
        result = orchestrator.run(
            task_type=f"generate_{prompt_row['task']}",
            user_prompt=prompt_row["prompt"],
            use_rag=True,
        )
    finally:
        builtins.input = original_input

    output_file = output_dir / f"{prompt_row['id']}_teacher.md"
    output_file.write_text(result["output"].strip() + "\n", encoding="utf-8")
    return {
        "output_text": result["output"].strip(),
        "output_path": str(output_file.relative_to(REPO_ROOT)),
        "run_id": result["run_id"],
    }


def _compare_summary(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not rows:
        return {"general_avg": 0.0, "teacher_avg": 0.0, "teacher_minus_general": 0.0}
    general_avg = sum(row["general_final_score"] for row in rows) / len(rows)
    teacher_avg = sum(row["teacher_final_score"] for row in rows) / len(rows)
    return {
        "general_avg": round(general_avg, 3),
        "teacher_avg": round(teacher_avg, 3),
        "teacher_minus_general": round(teacher_avg - general_avg, 3),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch compare general vs teacher on shared prompts.")
    parser.add_argument("--config", default="configs/config.yaml")
    parser.add_argument(
        "--general-adapter",
        default="runs/20260313_140305_general_train/adapter",
        help="Adapter path used for general model generation.",
    )
    parser.add_argument(
        "--prompts-file",
        default="evaluation/prompts/comparison_prompts.jsonl",
        help="Shared prompt set for comparison.",
    )
    parser.add_argument(
        "--output-root",
        default="runs/compare_eval",
        help="Directory for generated outputs and comparison results.",
    )
    args = parser.parse_args()

    prompts = _read_jsonl(REPO_ROOT / args.prompts_file)
    output_root = REPO_ROOT / args.output_root
    general_dir = output_root / "general"
    teacher_dir = output_root / "teacher"
    results_dir = output_root / "results"
    general_dir.mkdir(parents=True, exist_ok=True)
    teacher_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    from core.config import load_config
    from core.modeling import ChatModel, ModelSettings
    from evaluation.llm_judge import LLMJudge
    from runtime.workflow.orchestrator import Orchestrator

    cfg = load_config(args.config)
    general_model = ChatModel(
        ModelSettings(
            model_path=cfg["model"]["base_model_dir"],
            torch_dtype=cfg["model"].get("torch_dtype", "bfloat16"),
            adapter_path=args.general_adapter,
        )
    )
    teacher_orchestrator = Orchestrator(cfg, model_profile="teacher")
    judge = LLMJudge(config_path=args.config)

    summary_rows: List[Dict[str, Any]] = []
    for row in prompts:
        print(f"[run] {row['id']} generating general...", flush=True)
        general_generated = _generate_general(row, general_model, args.general_adapter, general_dir)
        print(f"[run] {row['id']} generating teacher...", flush=True)
        teacher_generated = _generate_teacher(row, teacher_orchestrator, teacher_dir)

        general_eval = evaluate_output(
            model_type="cybersecurity_eval",
            prompt=row["prompt"],
            output_text=general_generated["output_text"],
            config_path=args.config,
            judge=judge,
        )
        teacher_eval = evaluate_output(
            model_type="teacher_eval",
            prompt=row["prompt"],
            output_text=teacher_generated["output_text"],
            config_path=args.config,
            judge=judge,
        )

        pair_result = {
            "sample_id": row["id"],
            "task": row["task"],
            "prompt": row["prompt"],
            "general_output_path": general_generated["output_path"],
            "teacher_output_path": teacher_generated["output_path"],
            "teacher_run_id": teacher_generated["run_id"],
            "general_eval": general_eval,
            "teacher_eval": teacher_eval,
            "general_final_score": general_eval["final_score"],
            "teacher_final_score": teacher_eval["final_score"],
            "teacher_minus_general": round(teacher_eval["final_score"] - general_eval["final_score"], 2),
        }

        result_path = results_dir / f"{row['id']}.json"
        result_path.write_text(json.dumps(pair_result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        summary_rows.append(
            {
                "sample_id": row["id"],
                "task": row["task"],
                "general_final_score": general_eval["final_score"],
                "teacher_final_score": teacher_eval["final_score"],
                "teacher_minus_general": round(teacher_eval["final_score"] - general_eval["final_score"], 2),
                "general_output_path": general_generated["output_path"],
                "teacher_output_path": teacher_generated["output_path"],
                "teacher_run_id": teacher_generated["run_id"],
                "result_path": str(result_path.relative_to(REPO_ROOT)),
            }
        )
        print(
            f"[done] {row['id']} general={general_eval['final_score']} "
            f"teacher={teacher_eval['final_score']} delta={round(teacher_eval['final_score'] - general_eval['final_score'], 2)}"
        )

    summary_payload = {
        "summary": _compare_summary(summary_rows),
        "rows": summary_rows,
    }
    summary_file = results_dir / "summary.json"
    summary_file.write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[summary] saved to {summary_file.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
