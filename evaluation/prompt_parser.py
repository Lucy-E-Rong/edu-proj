from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


TASK_TYPES = ("lesson", "practice", "incident")
GENERIC_RETRIEVAL_STOPWORDS = {
    "Write",
    "Create",
    "Generate",
    "Explain",
    "Brief",
    "Beginner",
    "Friendly",
    "Simple",
    "Short",
}


def _extract_task_type(prompt: str) -> str:
    lowered = prompt.lower()
    for task_type in TASK_TYPES:
        if re.search(rf"\b{re.escape(task_type)}\b", lowered):
            return task_type
    return "unknown"


def _extract_module_id(prompt: str) -> Optional[str]:
    match = re.search(r"\bmodule[_\s-]?(\d{1,3})\b", prompt, flags=re.IGNORECASE)
    if not match:
        return None
    return f"module_{int(match.group(1)):03d}"


def _extract_max_chars(prompt: str) -> Optional[int]:
    patterns = [
        r"(\d+)\s*字以内",
        r"控制在\s*(\d+)\s*字以内",
        r"within\s*(\d+)\s*characters",
    ]
    for pattern in patterns:
        match = re.search(pattern, prompt, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def _extract_sentence_range(prompt: str) -> Optional[List[int]]:
    patterns = [
        r"(\d+)\s*[-~至到]\s*(\d+)\s*句",
        r"(\d+)\s*[-~]\s*(\d+)\s*sentences?",
    ]
    for pattern in patterns:
        match = re.search(pattern, prompt, flags=re.IGNORECASE)
        if match:
            start, end = int(match.group(1)), int(match.group(2))
            if start <= end:
                return [start, end]
    exact = re.search(r"\b(\d+)\s*sentences?\b", prompt, flags=re.IGNORECASE)
    if exact:
        value = int(exact.group(1))
        return [value, value]
    return None


def _extract_style_hints(prompt: str) -> List[str]:
    hints: List[str] = []
    hint_patterns = {
        "brief": [r"简短", r"brief", r"concise", r"short"],
        "beginner_friendly": [r"beginner-friendly", r"初学者", r"新手", r"beginner"],
        "final_only": [r"only final answer", r"仅输出最终答案", r"输出 only final answer"],
        "no_dialogue": [r"不要写成对话", r"do not write as dialogue", r"不要对话体"],
    }
    for name, patterns in hint_patterns.items():
        if any(re.search(pattern, prompt, flags=re.IGNORECASE) for pattern in patterns):
            hints.append(name)
    return hints


def _extract_retrieval_terms(prompt: str, module_id: Optional[str], task_type: str) -> List[str]:
    terms: List[str] = []
    if module_id:
        terms.append(module_id)
    if task_type != "unknown":
        terms.append(task_type)

    explicit_terms = re.findall(r"\b[A-Z][A-Za-z0-9&()/_-]+(?:\s+[A-Z][A-Za-z0-9&()/_-]+)*\b", prompt)
    cleaned = [
        term.strip()
        for term in explicit_terms
        if len(term.strip()) > 2 and term.strip() not in GENERIC_RETRIEVAL_STOPWORDS
    ]
    for term in cleaned:
        if term not in terms:
            terms.append(term)

    quoted = re.findall(r'"([^"]+)"', prompt)
    for term in quoted:
        term = term.strip()
        if term and term not in terms:
            terms.append(term)

    return terms[:10]


def parse_prompt(prompt: str) -> Dict[str, Any]:
    task_type = _extract_task_type(prompt)
    module_id = _extract_module_id(prompt)
    style_hints = _extract_style_hints(prompt)

    parsed: Dict[str, Any] = {
        "task_type": task_type,
        "module_id": module_id,
        "max_chars": _extract_max_chars(prompt),
        "sentence_range": _extract_sentence_range(prompt),
        "no_dialogue": "no_dialogue" in style_hints,
        "style_hints": style_hints,
        "retrieval_terms": _extract_retrieval_terms(prompt, module_id, task_type),
    }
    return parsed
