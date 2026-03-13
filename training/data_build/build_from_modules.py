from __future__ import annotations

import argparse
import json
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


FRONT_MATTER_RE = re.compile(r"(?ms)^---\s*\n(.*?)\n---\s*\n")
H2_RE = re.compile(r"(?m)^##\s+(.+?)\s*$")
CODE_BLOCK_RE = re.compile(r"(?ms)```.*?```")

DOC_SPECS = {
    "security_incident_document.md": {
        "doc_kind": "incident",
        "task_type": "incident_brief",
        "user_template": (
            "Write a concise cybersecurity incident briefing for the section "
            "'{section_title}' from the module '{doc_title}'. Keep the content aligned "
            "with the original incident narrative and defensive context."
        ),
        "drop_code_blocks": True,
    },
    "security_lesson_document.md": {
        "doc_kind": "lesson",
        "task_type": "lesson_explain",
        "user_template": (
            "Teach the lesson section '{section_title}' from the module '{doc_title}' "
            "as course-aligned cybersecurity instruction. Preserve the original "
            "teaching intent and technical meaning."
        ),
        "drop_code_blocks": True,
    },
    "security_practice_document.md": {
        "doc_kind": "practice",
        "task_type": "practice_generation",
        "user_template": (
            "Create a classroom practice-style response for the section "
            "'{section_title}' from the module '{doc_title}'. Preserve the original "
            "task structure, lab intent, and instructional context."
        ),
        "drop_code_blocks": False,
    },
}


@dataclass
class Section:
    module_id: str
    source_file: str
    doc_title: str
    doc_kind: str
    task_type: str
    section_title: str
    text: str


def _iter_module_docs(source_dir: Path) -> Iterable[Tuple[str, Path, Dict[str, str | bool]]]:
    for module_dir in sorted(source_dir.glob("module_*")):
        if not module_dir.is_dir():
            continue
        for file_name, spec in DOC_SPECS.items():
            doc_path = module_dir / file_name
            if doc_path.exists():
                yield module_dir.name, doc_path, spec


def _parse_front_matter(block: str) -> Dict[str, str]:
    meta: Dict[str, str] = {}
    for line in block.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip().lower()] = value.strip().strip('"').strip("'")
    return meta


def _load_doc(path: Path) -> Tuple[str, str]:
    markdown = path.read_text(encoding="utf-8")
    match = FRONT_MATTER_RE.match(markdown)
    if not match:
        return path.stem, markdown.strip()

    meta = _parse_front_matter(match.group(1))
    title = meta.get("title", path.stem)
    return title, markdown[match.end() :].strip()


def _split_sections(body: str) -> List[Tuple[str, str]]:
    headings = list(H2_RE.finditer(body))
    if not headings:
        return [("Overview", body.strip())] if body.strip() else []

    sections: List[Tuple[str, str]] = []
    prelude = body[: headings[0].start()].strip()
    if prelude:
        sections.append(("Overview", prelude))

    for idx, heading in enumerate(headings):
        title = heading.group(1).strip()
        start = heading.end()
        end = headings[idx + 1].start() if idx + 1 < len(headings) else len(body)
        content = body[start:end].strip()
        if content:
            sections.append((title, content))
    return sections


def _normalize_text(text: str, drop_code_blocks: bool) -> str:
    normalized = text
    if drop_code_blocks:
        normalized = CODE_BLOCK_RE.sub("", normalized)
    normalized = re.sub(r"(?m)^---\s*$", "", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def _assistant_content(section: Section) -> str:
    return f"### {section.doc_title} - {section.section_title}\n\n{section.text}".strip()


def _make_sample(section: Section, user_content: str, assistant_content: str) -> Dict[str, object]:
    return {
        "module_id": section.module_id,
        "source_file": section.source_file,
        "doc_title": section.doc_title,
        "doc_kind": section.doc_kind,
        "section_title": section.section_title,
        "task_type": section.task_type,
        "risk_level": "none",
        "messages": [
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": assistant_content},
        ],
    }


def build_dataset(source_dir: Path) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for module_id, doc_path, spec in _iter_module_docs(source_dir):
        doc_title, body = _load_doc(doc_path)
        for section_title, section_text in _split_sections(body):
            normalized_text = _normalize_text(section_text, drop_code_blocks=bool(spec["drop_code_blocks"]))
            if not normalized_text:
                continue

            section = Section(
                module_id=module_id,
                source_file=str(doc_path),
                doc_title=doc_title,
                doc_kind=str(spec["doc_kind"]),
                task_type=str(spec["task_type"]),
                section_title=section_title,
                text=normalized_text,
            )
            user_content = str(spec["user_template"]).format(
                section_title=section.section_title,
                doc_title=section.doc_title,
            )
            rows.append(_make_sample(section, user_content, _assistant_content(section)))
    return rows


def _write_jsonl(path: Path, rows: List[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _split_train_eval(rows: List[Dict[str, object]], eval_ratio: float, seed: int) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    if not rows:
        return [], []
    rng = random.Random(seed)
    shuffled = list(rows)
    rng.shuffle(shuffled)

    eval_count = max(1, int(len(shuffled) * eval_ratio))
    eval_rows = shuffled[:eval_count]
    train_rows = shuffled[eval_count:]
    if not train_rows:
        train_rows = eval_rows
        eval_rows = eval_rows[:1]
    return train_rows, eval_rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build training JSONL from the new module incident/lesson/practice documents"
    )
    parser.add_argument("--source-dir", default="generated_modules/21 Modules")
    parser.add_argument("--train-out", default="data/processed/train.jsonl")
    parser.add_argument("--eval-out", default="data/processed/eval.jsonl")
    parser.add_argument("--eval-ratio", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    source_dir = Path(args.source_dir)
    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    rows = build_dataset(source_dir)
    if not rows:
        raise ValueError("No training rows were generated from modules.")

    train_rows, eval_rows = _split_train_eval(rows, eval_ratio=args.eval_ratio, seed=args.seed)
    _write_jsonl(Path(args.train_out), train_rows)
    _write_jsonl(Path(args.eval_out), eval_rows)

    stats_by_task: Dict[str, int] = {}
    stats_by_doc_kind: Dict[str, int] = {}
    for row in rows:
        task_type = str(row["task_type"])
        doc_kind = str(row["doc_kind"])
        stats_by_task[task_type] = stats_by_task.get(task_type, 0) + 1
        stats_by_doc_kind[doc_kind] = stats_by_doc_kind.get(doc_kind, 0) + 1

    print(f"Generated rows: {len(rows)}")
    print(f"Train rows: {len(train_rows)} -> {args.train_out}")
    print(f"Eval rows: {len(eval_rows)} -> {args.eval_out}")
    print(f"Task distribution: {json.dumps(stats_by_task, ensure_ascii=False)}")
    print(f"Doc distribution: {json.dumps(stats_by_doc_kind, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
