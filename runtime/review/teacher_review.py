from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict


LLM_SCORE_KEYS = (
    "prompt_match_score",
    "source_learning_score",
    "teaching_usefulness_score",
)


def _ask_score(key: str, current_value: Any) -> int:
    while True:
        raw = input(f"{key} [0/1/2, Enter=keep {current_value}]: ").strip()
        if not raw:
            return int(current_value)
        if raw in {"0", "1", "2"}:
            return int(raw)
        print("Please enter 0, 1, 2, or leave blank to keep the evaluator score.")


def collect_teacher_review(evaluation_result: Dict[str, Any]) -> Dict[str, Any]:
    """Collect teacher-corrected LLM-judge scores and revision feedback."""
    llm_result = evaluation_result.get("llm_result", {})
    corrected = deepcopy(llm_result)

    print("\nAutomatic evaluator scores:")
    for key in LLM_SCORE_KEYS:
        print(f"- {key}: {llm_result.get(key, 'n/a')}")
    reasons = llm_result.get("reason", [])
    if reasons:
        print("Automatic evaluator reasons:")
        for reason in reasons:
            print(f"- {reason}")

    print("\nTeacher score correction:")
    for key in LLM_SCORE_KEYS:
        corrected[key] = _ask_score(key, llm_result.get(key, 0))

    corrected_llm_avg = sum(corrected[key] for key in LLM_SCORE_KEYS) / len(LLM_SCORE_KEYS)
    hard_score = float(evaluation_result.get("hard_result", {}).get("score", 0.0))
    corrected_final_score = round(hard_score * 0.35 + corrected_llm_avg * 0.65, 2)

    correction_note = input("Teacher correction note (optional): ").strip()
    refinement_feedback = input("Refinement feedback (blank to accept current answer): ").strip()

    return {
        "auto_llm_result": llm_result,
        "teacher_corrected_llm_result": corrected,
        "teacher_corrected_final_score": corrected_final_score,
        "teacher_correction_note": correction_note,
        "refinement_feedback": refinement_feedback,
    }
