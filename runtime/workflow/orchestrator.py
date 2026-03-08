from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.modeling import ChatModel, ModelSettings
from core.prompt_builders import build_cag_prompt, build_rag_prompt
from runtime.cag.load_assets import load_cag_assets
from runtime.rag.retrieve import retrieve
from runtime.verifier.verifier import VerifierLLM


@dataclass
class SharedMemory:
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    latest_exercise: str = ""
    latest_rubric: str = ""
    last_retrieved_chunks: List[Dict[str, Any]] = field(default_factory=list)


class Orchestrator:
    def __init__(self, config: Dict[str, Any], model_profile: Optional[str] = None) -> None:
        model_cfg = config["model"]
        runtime_cfg = config.get("runtime", {})
        self.config = config
        self.model_profile = model_profile or runtime_cfg.get("default_model_profile", "base")
        self.memory = SharedMemory()
        generator_settings = self._model_settings_for_profile(self.model_profile)
        verifier_profile = runtime_cfg.get("verifier_model_profile", "base")
        verifier_settings = self._model_settings_for_profile(verifier_profile)

        self.generator = ChatModel(
            generator_settings
        )
        self.verifier = VerifierLLM(
            model_path=verifier_settings.model_path,
            torch_dtype=verifier_settings.torch_dtype,
            adapter_path=verifier_settings.adapter_path,
        )
        self.verifier_profile = verifier_profile
        self.generator_adapter_path = generator_settings.adapter_path
        self.verifier_adapter_path = verifier_settings.adapter_path

    def _model_settings_for_profile(self, profile: str) -> ModelSettings:
        model_cfg = self.config["model"]
        runtime_cfg = self.config.get("runtime", {})
        profiles = runtime_cfg.get("model_profiles", {})
        profile_cfg = profiles.get(profile)
        if profile_cfg is None:
            known = ", ".join(sorted(profiles)) or "none"
            raise ValueError(f"Unknown runtime model profile '{profile}'. Known profiles: {known}")

        adapter_path = profile_cfg.get("adapter_path")
        if adapter_path:
            adapter_file = Path(adapter_path)
            if not adapter_file.exists():
                raise FileNotFoundError(f"Runtime adapter for profile '{profile}' not found: {adapter_path}")

        return ModelSettings(
            model_path=model_cfg["base_model_dir"],
            torch_dtype=model_cfg.get("torch_dtype", "bfloat16"),
            adapter_path=adapter_path or None,
        )

    def _new_run_dir(self) -> Path:
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = Path(self.config["output"]["runs_dir"]) / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def _append_trace(self, trace_file: Path, item: Dict[str, Any]) -> None:
        with trace_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    def _safe_refusal(self, verifier_result: Dict[str, Any]) -> str:
        reasons = verifier_result.get("reasons", [])
        reason_text = "; ".join(reasons) if reasons else "safety policy triggered"
        return (
            "I cannot provide that content as requested. "
            f"Reason: {reason_text}. "
            "Suggestion: ask for a safer educational variant with non-operational detail."
        )

    def _write_report(
        self,
        run_dir: Path,
        task_type: str,
        prompt_used: str,
        output_text: str,
        verifier_result: Dict[str, Any],
    ) -> None:
        report = run_dir / "report.md"
        chunks_block = "\n\n".join(
            [f"- chunk_id={c['chunk_id']} source={c['source']}\n\n{c['text']}" for c in self.memory.last_retrieved_chunks]
        )
        if not chunks_block:
            chunks_block = "- none"

        report.write_text(
            "# Run Report\n\n"
            f"- task_type: `{task_type}`\n"
            f"- generator_model_profile: `{self.model_profile}`\n"
            f"- generator_adapter_path: `{self.generator_adapter_path or 'none'}`\n"
            f"- verifier_model_profile: `{self.verifier_profile}`\n"
            f"- verifier_adapter_path: `{self.verifier_adapter_path or 'none'}`\n"
            f"- rag_topk: `{self.config['rag']['topk']}`\n"
            f"- chunk_size: `{self.config['rag']['chunk']}`\n"
            f"- chunk_overlap: `{self.config['rag']['overlap']}`\n\n"
            "## Prompt\n\n"
            f"```text\n{prompt_used}\n```\n\n"
            "## Retrieved Chunks\n\n"
            f"{chunks_block}\n\n"
            "## Output\n\n"
            f"```text\n{output_text}\n```\n\n"
            "## Verifier Result\n\n"
            f"```json\n{json.dumps(verifier_result, indent=2)}\n```\n",
            encoding="utf-8",
        )

    def run(
        self,
        task_type: str,
        user_prompt: str,
        use_rag: bool = False,
        rubric_source_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        if task_type not in {"generate_exercise", "generate_rubric", "factual_question"}:
            raise ValueError(f"Unsupported task_type: {task_type}")

        run_dir = self._new_run_dir()
        trace_file = run_dir / "trace.jsonl"

        retrieved = retrieve(user_prompt, k=self.config["rag"]["topk"]) if use_rag else []
        self.memory.last_retrieved_chunks = retrieved

        if task_type == "generate_rubric":
            base_text = rubric_source_text or self.memory.latest_exercise
            if not base_text:
                latest_path = Path(self.config["output"]["runs_dir"]) / "latest_exercise.txt"
                if latest_path.exists():
                    base_text = latest_path.read_text(encoding="utf-8").strip()
            user_prompt = (
                f"Create a concise grading rubric for this exercise:\n{base_text}\n\n"
                f"Additional constraints:\n{user_prompt}"
            )

        style_guide, example = load_cag_assets()
        cag_prompt = build_cag_prompt(style_guide, example, user_prompt)
        rag_prompt = build_rag_prompt(retrieved, self.memory.conversation_history, user_prompt)

        effective_prompt = cag_prompt
        if task_type == "factual_question" or (task_type == "generate_exercise" and use_rag):
            effective_prompt = f"{cag_prompt}\n\n{rag_prompt}"

        current_output = self.generator.generate(
            messages=[{"role": "user", "content": effective_prompt}],
            max_new_tokens=500,
            temperature=0.6,
            do_sample=True,
            add_generation_prompt=True,
        )
        self._append_trace(
            trace_file,
            {
                "stage": "initial",
                "task_type": task_type,
                "generator_model_profile": self.model_profile,
                "prompt": effective_prompt,
                "output": current_output,
            },
        )

        verifier_result = self.verifier.verify(effective_prompt, current_output)
        self._append_trace(trace_file, {"stage": "verify", "result": verifier_result})

        if verifier_result.get("action") == "block":
            current_output = self._safe_refusal(verifier_result)
            self._append_trace(trace_file, {"stage": "blocked_refusal", "output": current_output})
        else:
            for round_idx in range(1, 3):
                feedback = input(
                    f"Refinement round {round_idx}/2 - enter feedback (blank to accept): "
                ).strip()
                if not feedback:
                    break
                refine_prompt = (
                    "Revise the previous answer using this feedback while preserving educational quality and safety.\n\n"
                    f"Feedback: {feedback}\n\n"
                    f"Previous answer:\n{current_output}"
                )
                current_output = self.generator.generate(
                    messages=[{"role": "user", "content": refine_prompt}],
                    max_new_tokens=500,
                    temperature=0.4,
                    do_sample=True,
                    add_generation_prompt=True,
                )
                self._append_trace(
                    trace_file,
                    {
                        "stage": "refine",
                        "round": round_idx,
                        "feedback": feedback,
                        "output": current_output,
                    },
                )

        self.memory.conversation_history.append({"role": "user", "content": user_prompt})
        self.memory.conversation_history.append({"role": "assistant", "content": current_output})

        if task_type == "generate_exercise":
            self.memory.latest_exercise = current_output
            latest_path = Path(self.config["output"]["runs_dir"]) / "latest_exercise.txt"
            latest_path.parent.mkdir(parents=True, exist_ok=True)
            latest_path.write_text(current_output, encoding="utf-8")
        if task_type == "generate_rubric":
            self.memory.latest_rubric = current_output

        self._write_report(
            run_dir=run_dir,
            task_type=task_type,
            prompt_used=effective_prompt,
            output_text=current_output,
            verifier_result=verifier_result,
        )

        return {
            "run_id": run_dir.name,
            "model_profile": self.model_profile,
            "output": current_output,
            "verifier": verifier_result,
            "memory": asdict(self.memory),
        }
