from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List


REPO_ROOT = Path(__file__).resolve().parents[1]
CYBER_ROOT = REPO_ROOT / "generated_modules" / "21 Modules"
TEACHER_ROOT = REPO_ROOT / "data" / "teachers"


def _read_text_safe(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _candidate_files(model_type: str, task_type: str, module_id: str | None) -> List[Path]:
    if model_type == "cybersecurity_eval":
        if module_id:
            module_dir = CYBER_ROOT / module_id
            mapping = {
                "lesson": "security_lesson_document.md",
                "practice": "security_practice_document.md",
                "incident": "security_incident_document.md",
            }
            target = mapping.get(task_type)
            if target:
                candidate = module_dir / target
                return [candidate] if candidate.exists() else []
        return sorted(CYBER_ROOT.glob("module_*/*.md"))

    return sorted(TEACHER_ROOT.rglob("*"))


def _rank_matches(files: List[Path], retrieval_terms: List[str]) -> List[Path]:
    scored: List[tuple[int, Path]] = []
    lowered_terms = [term.lower() for term in retrieval_terms if term.strip()]
    for path in files:
        if not path.is_file():
            continue
        name = path.name.lower()
        text = _read_text_safe(path)[:12000].lower()
        score = 0
        for term in lowered_terms:
            if term in name:
                score += 4
            if term in text:
                score += 1
        if score > 0:
            scored.append((score, path))
    scored.sort(key=lambda item: (-item[0], str(item[1])))
    return [path for _, path in scored[:3]]


def locate_sources(model_type: str, parsed_prompt: Dict[str, Any]) -> Dict[str, Any]:
    task_type = parsed_prompt.get("task_type", "unknown")
    module_id = parsed_prompt.get("module_id")
    retrieval_terms = parsed_prompt.get("retrieval_terms", [])

    files = _candidate_files(model_type, task_type, module_id)
    matched = _rank_matches(files, retrieval_terms)

    if not matched:
        return {
            "status": "source_not_found",
            "source_paths": [],
            "snippets": [],
        }

    snippets: List[Dict[str, str]] = []
    for path in matched:
        text = _read_text_safe(path).strip()
        if not text:
            continue
        snippets.append(
            {
                "path": str(path.relative_to(REPO_ROOT)),
                "text": text[:4000],
            }
        )

    return {
        "status": "ok" if snippets else "source_not_found",
        "source_paths": [item["path"] for item in snippets],
        "snippets": snippets,
    }

