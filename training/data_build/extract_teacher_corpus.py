from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List


HEADER_RE = re.compile(r"(?m)^(#{1,6})\s+(.+?)\s*$")
TEXT_EXTS = {".md", ".txt"}
PDF_EXTS = {".pdf"}


def _read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""

    try:
        reader = PdfReader(str(path))
        page_texts = [(page.extract_text() or "").strip() for page in reader.pages]
    except Exception:
        return ""

    return "\n\n".join(text for text in page_texts if text)


def _split_markdown_sections(text: str) -> List[Dict[str, str]]:
    matches = list(HEADER_RE.finditer(text))
    if not matches:
        cleaned = text.strip()
        return [{"section_path": "Document", "text": cleaned}] if cleaned else []

    sections: List[Dict[str, str]] = []
    stack: List[str] = []

    for idx, match in enumerate(matches):
        level = len(match.group(1))
        title = match.group(2).strip()
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if not body:
            continue

        stack = stack[: level - 1]
        stack.append(title)
        sections.append(
            {
                "section_path": " / ".join(stack),
                "text": body,
            }
        )
    return sections


def _split_plain_text_blocks(text: str, max_chars: int = 3200) -> List[Dict[str, str]]:
    paragraphs = [part.strip() for part in re.split(r"\n{2,}", text) if part.strip()]
    if not paragraphs:
        return []

    blocks: List[Dict[str, str]] = []
    current: List[str] = []
    current_len = 0

    for paragraph in paragraphs:
        next_len = current_len + len(paragraph) + (2 if current else 0)
        if current and next_len > max_chars:
            blocks.append(
                {
                    "section_path": f"Document / Block {len(blocks) + 1:03d}",
                    "text": "\n\n".join(current),
                }
            )
            current = []
            current_len = 0

        current.append(paragraph)
        current_len += len(paragraph) + (2 if current_len else 0)

    if current:
        blocks.append(
            {
                "section_path": f"Document / Block {len(blocks) + 1:03d}",
                "text": "\n\n".join(current),
            }
        )

    return blocks


def _normalize_text(text: str) -> str:
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _iter_source_files(source_dir: Path) -> Iterable[Path]:
    for path in sorted(source_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.name.startswith("."):
            continue
        if path.suffix.lower() in TEXT_EXTS | PDF_EXTS:
            yield path


def build_extracted_rows(source_dir: Path, course_id: str) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for path in _iter_source_files(source_dir):
        suffix = path.suffix.lower()
        raw_text = ""
        extraction_status = "ok"
        extraction_note = ""

        if suffix in TEXT_EXTS:
            raw_text = _read_text_file(path)
        elif suffix in PDF_EXTS:
            raw_text = _extract_pdf_text(path)
            if not raw_text.strip():
                extraction_status = "skipped"
                extraction_note = "pypdf unavailable or PDF text extraction failed"
        else:
            continue

        if extraction_status != "ok":
            rows.append(
                {
                    "course_id": course_id,
                    "source_file": str(path),
                    "source_type": suffix.lstrip("."),
                    "section_path": "Document",
                    "text": "",
                    "extraction_status": extraction_status,
                    "extraction_note": extraction_note,
                }
            )
            continue

        cleaned = _normalize_text(raw_text)
        sections = (
            _split_markdown_sections(cleaned)
            if suffix in TEXT_EXTS
            else _split_plain_text_blocks(cleaned)
        )
        for section in sections:
            text = _normalize_text(section["text"])
            if len(text) < 80:
                continue
            rows.append(
                {
                    "course_id": course_id,
                    "source_file": str(path),
                    "source_type": suffix.lstrip("."),
                    "section_path": section["section_path"],
                    "text": text,
                    "extraction_status": "ok",
                    "extraction_note": "",
                }
            )
    return rows


def write_jsonl(path: Path, rows: List[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract teacher materials into normalized text blocks")
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--course-id", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    source_dir = Path(args.source_dir)
    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    rows = build_extracted_rows(source_dir=source_dir, course_id=args.course_id)
    if not rows:
        raise ValueError("No extracted teacher rows produced.")

    write_jsonl(Path(args.out), rows)

    ok_count = sum(1 for row in rows if row["extraction_status"] == "ok")
    skipped_count = len(rows) - ok_count
    print(f"Extracted rows: {len(rows)}")
    print(f"OK rows: {ok_count}")
    print(f"Skipped rows: {skipped_count}")
    print(f"Output: {args.out}")


if __name__ == "__main__":
    main()
