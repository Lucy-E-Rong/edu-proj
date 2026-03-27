from __future__ import annotations

import json
from typing import Any, Dict, List


def _extract_json(raw: str) -> Dict[str, Any]:
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model output")
    return json.loads(raw[start : end + 1])


class LLMJudge:
    def __init__(self, config_path: str = "configs/config.yaml") -> None:
        from core.config import load_config
        from core.modeling import ChatModel, ModelSettings

        cfg = load_config(config_path)
        model_cfg = cfg["model"]
        self.model = ChatModel(
            ModelSettings(
                model_path=model_cfg["base_model_dir"],
                torch_dtype=model_cfg.get("torch_dtype", "bfloat16"),
            )
        )

    def evaluate(
        self,
        prompt: str,
        task_type: str,
        output_text: str,
        source_snippets: List[Dict[str, str]],
        source_status: str,
    ) -> Dict[str, Any]:
        source_block = "\n\n".join(
            f"[SOURCE {idx + 1}] {item['path']}\n{item['text']}"
            for idx, item in enumerate(source_snippets)
        )
        if not source_block:
            source_block = "SOURCE_NOT_FOUND"

        judge_prompt = f"""You are an evaluator for educational content generation.

Evaluate the generated output using the user prompt and the retrieved source content.

Focus on only these three questions:

1. prompt_match:
Did the output satisfy the main request in the prompt?

2. source_learning:
Does the output show that it learned from or used the source content?
Do NOT check whether the output copied the source text.
Check whether it:
- covers key concepts from the source
- preserves the main instructional intent of the source
- does not clearly drift away from the source topic

3. teaching_usefulness:
Can this output be directly used as teaching material for students?
Check whether it:
- is readable for students
- is clear
- is structured
- is suitable as a lesson, practice, or incident-style classroom material

Scoring:
- 2 = clearly satisfies
- 1 = partially satisfies
- 0 = does not satisfy

Return strict JSON only with this schema:
{{
  "prompt_match_score": 0,
  "source_learning_score": 0,
  "teaching_usefulness_score": 0,
  "reason": ["", "", ""]
}}

Rules:
- Return JSON only.
- Do not use markdown.
- Keep reasons short and concrete.
- Base your judgment only on the prompt, output, and source content given below.
- If source content is missing, lower confidence for source_learning and mention that in reason.

User prompt:
{prompt}

Task type:
{task_type}

Source status:
{source_status}

Retrieved source content:
{source_block}

Model output:
{output_text}
"""

        raw = self.model.generate(
            messages=[{"role": "user", "content": judge_prompt}],
            max_new_tokens=280,
            temperature=0.0,
            do_sample=False,
            add_generation_prompt=True,
        )

        try:
            payload = _extract_json(raw)
            for key in ["prompt_match_score", "source_learning_score", "teaching_usefulness_score", "reason"]:
                if key not in payload:
                    raise ValueError(f"Missing key: {key}")
            return payload
        except Exception:
            return {
                "prompt_match_score": 0,
                "source_learning_score": 0 if source_status == "source_not_found" else 1,
                "teaching_usefulness_score": 0,
                "reason": ["LLM judge parse failed."],
            }
