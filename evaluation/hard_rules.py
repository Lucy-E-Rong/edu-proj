from __future__ import annotations

import re
from typing import Any, Dict, List


def _sentence_count(text: str) -> int:
    parts = re.split(r"[。！？!?]+|(?<=[a-zA-Z0-9])[.](?=\s|$)", text)
    return len([part for part in parts if part.strip()])


def _looks_like_dialogue(text: str) -> bool:
    lowered = text.lower()
    patterns = ["user:", "assistant:", "system:"]
    return any(pattern in lowered for pattern in patterns)


def _task_shape_ok(task_type: str, text: str) -> bool:
    lowered = text.lower()
    if task_type == "lesson":
        return any(token in lowered for token in ["explain", "lesson", "concept", "learn", "understand", "teaching"])
    if task_type == "practice":
        return any(token in lowered for token in ["task", "practice", "exercise", "question", "steps"])
    if task_type == "incident":
        return any(token in lowered for token in ["incident", "risk", "impact", "mitigation", "vulnerability"])
    return True


def _score_bool(value: bool) -> int:
    return 2 if value else 0


def evaluate_hard_rules(prompt_info: Dict[str, Any], output_text: str) -> Dict[str, Any]:
    checks: Dict[str, bool] = {}
    max_chars = prompt_info.get("max_chars")
    if max_chars is not None:
        checks["length_ok"] = len(output_text.strip()) <= max_chars

    sentence_range = prompt_info.get("sentence_range")
    if sentence_range:
        sentence_count = _sentence_count(output_text)
        checks["sentence_ok"] = sentence_range[0] <= sentence_count <= sentence_range[1]

    if prompt_info.get("no_dialogue"):
        checks["no_dialogue_ok"] = not _looks_like_dialogue(output_text)

    task_type = prompt_info.get("task_type", "unknown")
    if task_type != "unknown":
        checks["task_shape_ok"] = _task_shape_ok(task_type, output_text)

    if not checks:
        return {
            "score": 2.0,
            "checks": {},
        }

    raw_scores: List[int] = [_score_bool(value) for value in checks.values()]
    score = round(sum(raw_scores) / len(raw_scores), 2)
    return {
        "score": score,
        "checks": checks,
    }

