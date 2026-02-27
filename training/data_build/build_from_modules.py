from __future__ import annotations

import argparse
import json
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


FRONT_MATTER_RE = re.compile(r"(?ms)^---\s*\n(.*?)\n---\s*\n")
HEADING_RE = re.compile(r"(?m)^##\s+(.+?)\s*$")
CODE_BLOCK_RE = re.compile(r"(?ms)```.*?```")


@dataclass
class Section:
    module_id: str
    source_file: str
    doc_title: str
    section_title: str
    text: str
    # risk_level: str


def _iter_combined_files(source_dir: Path) -> Iterable[Tuple[str, Path]]:
    for module_dir in sorted(source_dir.glob("module_*")):
        if not module_dir.is_dir():
            continue
        combined = module_dir / "combined.md"
        if combined.exists():
            yield module_dir.name, combined


def _parse_front_matter(block: str) -> Dict[str, str]:
    meta: Dict[str, str] = {}
    for line in block.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip().lower()] = value.strip().strip('"').strip("'")
    return meta


def _split_docs(markdown: str) -> List[Tuple[str, str]]:
    matches = list(FRONT_MATTER_RE.finditer(markdown))
    if not matches:
        return [("Untitled", markdown)]

    docs: List[Tuple[str, str]] = []
    for idx, match in enumerate(matches):
        meta = _parse_front_matter(match.group(1))
        title = meta.get("title", f"Document {idx + 1}")
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(markdown)
        body = markdown[start:end].strip()
        if body:
            docs.append((title, body))
    return docs


def _split_sections(body: str) -> List[Tuple[str, str]]:
    headings = list(HEADING_RE.finditer(body))
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

#风险过滤
# Optional risk classification (disabled by default).
# To re-enable:
# 1) Uncomment this function.
# 2) Add `risk_level: str` back to Section.
# 3) Pass `risk_level` into Section(...) in build_dataset.
# 4) Switch _clean_text call to `_clean_text(section.text, max_chars=..., risk_level=section.risk_level)`.
# 5) Set `"risk_level": section.risk_level` in _make_sample.
#
# def _detect_risk_level(title: str, text: str) -> str:
#     hay = f"{title}\n{text}".lower()
#     high_terms = [
#         "exploit",
#         "payload",
#         "metasploit",
#         "execsync",
#         "remote code execution",
#         "command injection",
#         "proof-of-concept",
#     ]
#     low_terms = [
#         "mitigation",
#         "patch",
#         "defense",
#         "intended behavior",
#         "recommendation",
#         "secure design",
#     ]
#     if any(term in hay for term in high_terms):
#         return "high"
#     if any(term in hay for term in low_terms):
#         return "low"
#     return "medium"
#


def _clean_text(text: str, max_chars: int) -> str:   #过滤逻辑
    text = CODE_BLOCK_RE.sub("", text)
    text = re.sub(r"(?m)^---\s*$", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    # Optional risk-aware filtering (disabled by default).
    # def _clean_text(text: str, max_chars: int, risk_level: str) -> str:
    #     text = CODE_BLOCK_RE.sub("", text)
    #     text = re.sub(r"(?m)^---\s*$", "", text)
    #     text = re.sub(r"\n{3,}", "\n\n", text).strip()
    #
    #     if risk_level == "high":
    #         blocked_terms = [
    #             "exploit",
    #             "payload",
    #             "metasploit",
    #             "curl ",
    #             "wget ",
    #             "nc ",
    #             "bash -c",
    #             "powershell",
    #             "reverse shell",
    #             "execsync",
    #         ]
    #         safe_lines: List[str] = []
    #         for line in text.splitlines():
    #             lowered = line.lower()
    #             if any(term in lowered for term in blocked_terms):
    #                 continue
    #             safe_lines.append(line)
    #         text = "\n".join(safe_lines).strip()
    #
    #     return text[:max_chars].strip()

    return text[:max_chars].strip()


def _pick_sentences(text: str, limit: int = 5) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.replace("\n", " "))
    out: List[str] = []
    seen = set()
    for part in parts:
        part = part.strip(" -\t")
        if len(part) < 40:
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
    if not sents:
        sents = [text[:260].strip()] if text else []
    return "\n".join([f"- {s}" for s in sents if s])


def _build_checklist(text: str) -> str:
    candidates: List[str] = []
    for line in text.splitlines():
        lowered = line.lower()
        if any(k in lowered for k in ["should", "must", "recommend", "mitigation", "patch", "defense", "validate"]):
            candidates.append(line.strip(" -\t"))
    if not candidates:
        candidates = _pick_sentences(text, limit=4)
    return "\n".join([f"- {c}" for c in candidates[:6] if c])


def _make_sample(    #字段保留
    section: Section,
    task_type: str,
    user_content: str,
    assistant_content: str,
) -> Dict:
    return {
        "module_id": section.module_id,
        "source_file": section.source_file,
        "doc_title": section.doc_title,
        "section_title": section.section_title,
        "task_type": task_type,
        # "risk_level": section.risk_level,  # Enable with risk classification.
        "risk_level": "none",
        "messages": [
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": assistant_content},
        ],
    }


def _build_samples_for_section(section: Section) -> List[Dict]:
    cleaned = _clean_text(section.text, max_chars=2400)
    if len(cleaned) < 120:
        return []

    bullets = _build_bullets(cleaned, limit=5)
    checklist = _build_checklist(cleaned)
    short_answer = " ".join(_pick_sentences(cleaned, limit=3))[:900].strip()
    if not short_answer:
        short_answer = cleaned[:900]

    samples: List[Dict] = []

    explain_user = (
        f"Teach the section '{section.section_title}' from module {section.module_id} "
        f"to beginner cybersecurity students. Keep it clear, accurate, and defensive."
    )
    explain_assistant = (
        f"### {section.doc_title} - {section.section_title}\n"
        f"{bullets}\n"
    )
    samples.append(_make_sample(section, "explain", explain_user, explain_assistant))

    factual_user = (
        f"Based on module {section.module_id}, provide a concise factual summary of "
        f"'{section.section_title}' in 3-5 sentences."
    )
    factual_assistant = short_answer
    samples.append(_make_sample(section, "factual_qa", factual_user, factual_assistant))

    safe_user = (
        f"Rewrite the key points of '{section.section_title}' as a defensive checklist "
        f"for classroom use. Avoid operational attack instructions."
    )
    safe_assistant = checklist if checklist else bullets
    samples.append(_make_sample(section, "safe_rewrite", safe_user, safe_assistant))

    return samples


def build_dataset(source_dir: Path) -> List[Dict]:   #字段来源
    rows: List[Dict] = []
    for module_id, combined_path in _iter_combined_files(source_dir):
        markdown = combined_path.read_text(encoding="utf-8")
        docs = _split_docs(markdown)
        for doc_title, body in docs:
            for section_title, section_text in _split_sections(body):
                section = Section(
                    module_id=module_id,
                    source_file=str(combined_path),
                    doc_title=doc_title,
                    section_title=section_title,
                    text=section_text,
                    # risk_level=_detect_risk_level(section_title, section_text),
                )
                rows.extend(_build_samples_for_section(section))
    return rows


def _write_jsonl(path: Path, rows: List[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _split_train_eval(rows: List[Dict], eval_ratio: float, seed: int) -> Tuple[List[Dict], List[Dict]]:
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
    parser = argparse.ArgumentParser(description="Build training JSONL from generated_modules/combined.md")
    parser.add_argument("--source-dir", default="generated_modules")
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
    stats_by_risk: Dict[str, int] = {}
    for row in rows:
        stats_by_task[row["task_type"]] = stats_by_task.get(row["task_type"], 0) + 1
        stats_by_risk[row["risk_level"]] = stats_by_risk.get(row["risk_level"], 0) + 1

    print(f"Generated rows: {len(rows)}")
    print(f"Train rows: {len(train_rows)} -> {args.train_out}")
    print(f"Eval rows: {len(eval_rows)} -> {args.eval_out}")
    print(f"Task distribution: {json.dumps(stats_by_task, ensure_ascii=False)}")
    print(f"Risk distribution: {json.dumps(stats_by_risk, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
