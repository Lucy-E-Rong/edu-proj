from __future__ import annotations

import json
from typing import Any, Dict

from core.modeling import ChatModel, ModelSettings


class VerifierLLM:
    def __init__(self, model_path: str, torch_dtype: str = "bfloat16", adapter_path: str | None = None) -> None:
        self.model = ChatModel(
            ModelSettings(
                model_path=model_path,
                torch_dtype=torch_dtype,
                adapter_path=adapter_path,
            )
        )

    def verify(self, prompt: str, output: str) -> Dict[str, Any]:
        verifier_prompt = (
            "You are a safety and relevance verifier for educational content. "
            "Return strict JSON with keys: relevance_pass (bool), safety_pass (bool), "
            "reasons (array of strings), action (allow|block|revise)."
            "If unsafe, set action to block. If weak quality but safe, set action to revise.\n\n"
            f"Prompt:\n{prompt}\n\nOutput:\n{output}"
        )
        raw = self.model.generate(
            messages=[{"role": "user", "content": verifier_prompt}],
            max_new_tokens=220,
            temperature=0.0,
            do_sample=False,
            add_generation_prompt=True,
        )

        try:
            start = raw.find("{")
            end = raw.rfind("}")
            payload = json.loads(raw[start : end + 1])
            if not isinstance(payload, dict):
                raise ValueError("Verifier output was not a JSON object")
            for key in ["relevance_pass", "safety_pass", "reasons", "action"]:
                if key not in payload:
                    raise ValueError(f"Verifier output missing key: {key}")
            return payload
        except Exception:
            return {
                "relevance_pass": False,
                "safety_pass": True,
                "reasons": ["Verifier parse failed; defaulting to revise."],
                "action": "revise",
            }
