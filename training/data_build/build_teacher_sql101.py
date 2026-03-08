from __future__ import annotations

import argparse
import json
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple


H2_RE = re.compile(r"(?m)^##\s+(.+?)\s*$")
H3_RE = re.compile(r"(?m)^###\s+(.+?)\s*$")
CODE_BLOCK_RE = re.compile(r"(?ms)```.*?```")

SKIP_SECTIONS = {
    "Table of Contents",
    "Installation Guide",
    "Recommended Learning Resources",
    "Exercises and Solutions",
    "Conclusion",
}


@dataclass
class Section:
    course_id: str
    source_file: str
    doc_title: str
    unit_title: str
    section_title: str
    text: str


def _clean_text(text: str, max_chars: int = 2400) -> str:
    text = CODE_BLOCK_RE.sub("", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text[:max_chars].strip()


def _pick_sentences(text: str, limit: int = 5) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.replace("\n", " "))
    out: List[str] = []
    seen = set()
    for part in parts:
        part = part.strip(" -\t")
        if len(part) < 35:
            continue
        key = part.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(part)
        if len(out) >= limit:
            break
    return out


def _build_bullets(text: str, limit: int = 5) -> str:
    sents = _pick_sentences(text, limit=limit)
    if not sents and text:
        sents = [text[:260].strip()]
    return "\n".join([f"- {s}" for s in sents if s])


def _security_focus(unit_title: str, section_title: str) -> Tuple[str, str]:
    hay = f"{unit_title} {section_title}".lower()

    def has_any(patterns: List[str]) -> bool:
        return any(re.search(pattern, hay) for pattern in patterns)

    if has_any([r"\bquery", r"\bfilter", r"\bsort", r"\bsubquer", r"\bviews?\b"]):
        return (
            "SQL injection prevention and safe query construction",
            "Show how application inputs must stay separate from SQL syntax by using parameterized queries and validated filtering logic.",
        )
    if has_any([r"\binsert", r"\bupdat", r"\bdelet", r"\btransaction", r"\bacid\b", r"\bisolation"]):
        return (
            "data integrity, safe state changes, and least-privilege database access",
            "Connect write operations to integrity protection, rollback safety, and restricted permissions.",
        )
    if has_any([r"\bjoin", r"\brelationship", r"\bforeign key", r"\bprimary key"]):
        return (
            "data exposure control and access boundaries",
            "Explain how combining related tables can widen visibility and why secure access design matters.",
        )
    if has_any([r"\bindex", r"\bperformance", r"\badvanced"]):
        return (
            "secure engineering and abuse-resistant database design",
            "Relate performance design to secure operation, controlled resource use, and maintainable systems.",
        )
    return (
        "secure database engineering fundamentals",
        "Tie the course topic to defensive software design and safe handling of database operations.",
    )


def _make_sample(section: Section, task_type: str, user_content: str, assistant_content: str) -> Dict[str, object]:
    return {
        "course_id": section.course_id,
        "source_file": section.source_file,
        "doc_title": section.doc_title,
        "unit_title": section.unit_title,
        "section_title": section.section_title,
        "task_type": task_type,
        "messages": [
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": assistant_content},
        ],
    }


def _build_samples_for_section(section: Section) -> List[Dict[str, object]]:
    cleaned = _clean_text(section.text)
    if len(cleaned) < 120:
        return []

    focus, bridge_hint = _security_focus(section.unit_title, section.section_title)
    bullets = _build_bullets(cleaned)
    summary = " ".join(_pick_sentences(cleaned, limit=3))[:900].strip() or cleaned[:900]

    explain_user = (
        f"You are customizing a general cybersecurity teaching model for a SQL course. "
        f"Teach the database course section '{section.section_title}' from the unit '{section.unit_title}' "
        f"to beginner students, and connect it to {focus}. Keep the explanation classroom-oriented, "
        f"accurate, and defensive."
    )
    explain_assistant = (
        f"### {section.unit_title} - {section.section_title}\n"
        f"{bullets}\n\n"
        f"Security connection: {bridge_hint}"
    )

    bridge_user = (
        f"For a database lecture on '{section.section_title}' in the unit '{section.unit_title}', "
        f"write a concise note explaining how this topic relates to {focus}. "
        f"Prefer prevention-focused cybersecurity guidance."
    )
    bridge_assistant = (
        f"{summary}\n\n"
        f"In a cybersecurity-aware SQL class, this topic should also be framed around {focus.lower()}. "
        f"{bridge_hint}"
    )

    practice_user = (
        f"Create one short classroom exercise for a SQL course section titled '{section.section_title}'. "
        f"The exercise should reinforce the database concept while teaching {focus}. "
        f"Keep it educational and non-operational."
    )
    practice_assistant = (
        "Exercise:\n"
        f"Ask students to explain the database concept behind '{section.section_title}' and identify one "
        f"defensive design choice that supports {focus.lower()}.\n\n"
        "Expected answer traits:\n"
        f"- Demonstrates understanding of the SQL concept in '{section.section_title}'.\n"
        f"- Connects the concept to {focus.lower()}.\n"
        "- Stays focused on safe design, validation, parameter binding, least privilege, or integrity protection as appropriate."
    )

    return [
        _make_sample(section, "teacher_explain", explain_user, explain_assistant),
        _make_sample(section, "lecture_security_bridge", bridge_user, bridge_assistant),
        _make_sample(section, "course_aligned_exercise", practice_user, practice_assistant),
    ]


def _split_h3_sections(unit_title: str, body: str) -> List[Tuple[str, str]]:
    matches = list(H3_RE.finditer(body))
    if not matches:
        if body.strip():
            return [("Overview", body.strip())]
        return []

    sections: List[Tuple[str, str]] = []
    prelude = body[: matches[0].start()].strip()
    if prelude:
        sections.append(("Overview", prelude))

    for idx, match in enumerate(matches):
        title = match.group(1).strip()
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(body)
        content = body[start:end].strip()
        if content:
            sections.append((title, content))
    return sections


def build_dataset(source_file: Path, course_id: str = "sql101") -> List[Dict[str, object]]:
    text = source_file.read_text(encoding="utf-8")
    h2_matches = list(H2_RE.finditer(text))
    rows: List[Dict[str, object]] = []
    doc_title = "SQL-101 Teacher Materials"

    for idx, match in enumerate(h2_matches):
        unit_title = match.group(1).strip()
        if unit_title in SKIP_SECTIONS:
            continue
        start = match.end()
        end = h2_matches[idx + 1].start() if idx + 1 < len(h2_matches) else len(text)
        body = text[start:end].strip()
        if not body:
            continue
        for section_title, section_text in _split_h3_sections(unit_title, body):
            section = Section(
                course_id=course_id,
                source_file=str(source_file),
                doc_title=doc_title,
                unit_title=unit_title,
                section_title=section_title,
                text=section_text,
            )
            rows.extend(_build_samples_for_section(section))
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
    parser = argparse.ArgumentParser(description="Build teacher-stage JSONL from SQL-101 course materials")
    parser.add_argument("--source-file", default="data/teachers/sql101/original/README.md")
    parser.add_argument("--course-id", default="sql101")
    parser.add_argument("--train-out", default="data/teachers/sql101/processed/train.jsonl")
    parser.add_argument("--eval-out", default="data/teachers/sql101/processed/eval.jsonl")
    parser.add_argument("--eval-ratio", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    source_file = Path(args.source_file)
    if not source_file.exists():
        raise FileNotFoundError(f"Source file not found: {source_file}")

    rows = build_dataset(source_file=source_file, course_id=args.course_id)
    if not rows:
        raise ValueError("No teacher-stage rows were generated.")

    train_rows, eval_rows = _split_train_eval(rows, eval_ratio=args.eval_ratio, seed=args.seed)
    _write_jsonl(Path(args.train_out), train_rows)
    _write_jsonl(Path(args.eval_out), eval_rows)

    stats_by_task: Dict[str, int] = {}
    stats_by_unit: Dict[str, int] = {}
    for row in rows:
        task_type = str(row["task_type"])
        unit_title = str(row["unit_title"])
        stats_by_task[task_type] = stats_by_task.get(task_type, 0) + 1
        stats_by_unit[unit_title] = stats_by_unit.get(unit_title, 0) + 1

    print(f"Generated rows: {len(rows)}")
    print(f"Train rows: {len(train_rows)} -> {args.train_out}")
    print(f"Eval rows: {len(eval_rows)} -> {args.eval_out}")
    print(f"Task distribution: {json.dumps(stats_by_task, ensure_ascii=False)}")
    print(f"Unit distribution: {json.dumps(stats_by_unit, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
