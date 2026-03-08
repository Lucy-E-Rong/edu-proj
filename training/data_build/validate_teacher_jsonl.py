from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List


REQUIRED_TOP_LEVEL = {
    "course_id",
    "source_file",
    "source_type",
    "section_path",
    "unit_title",
    "section_title",
    "task_type",
    "messages",
}


def _read_jsonl(path: Path) -> List[Dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _validate_row(idx: int, row: Dict[str, object]) -> List[str]:
    errors: List[str] = []
    missing = REQUIRED_TOP_LEVEL - set(row.keys())
    if missing:
        errors.append(f"row {idx}: missing keys {sorted(missing)}")

    messages = row.get("messages")
    if not isinstance(messages, list) or len(messages) != 2:
        errors.append(f"row {idx}: messages must be a list of length 2")
        return errors

    first, second = messages
    if first.get("role") != "user":
        errors.append(f"row {idx}: first message role must be user")
    if second.get("role") != "assistant":
        errors.append(f"row {idx}: second message role must be assistant")
    if not str(first.get("content", "")).strip():
        errors.append(f"row {idx}: user content is empty")
    if not str(second.get("content", "")).strip():
        errors.append(f"row {idx}: assistant content is empty")
    if len(str(second.get("content", ""))) < 60:
        errors.append(f"row {idx}: assistant content is too short")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate teacher-stage JSONL format")
    parser.add_argument("--train-file", required=True)
    parser.add_argument("--eval-file", required=True)
    args = parser.parse_args()

    errors: List[str] = []
    for label, path_str in [("train", args.train_file), ("eval", args.eval_file)]:
        rows = _read_jsonl(Path(path_str))
        if not rows:
            errors.append(f"{label}: file is empty")
            continue
        for idx, row in enumerate(rows, start=1):
            errors.extend(_validate_row(idx, row))

    if errors:
        for err in errors:
            print(err)
        raise SystemExit(1)

    print("Teacher JSONL validation passed.")


if __name__ == "__main__":
    main()
