from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

SKIP_SECTION_TERMS = {
    "table of contents",
    "installation guide",
    "recommended learning resources",
    "exercises and solutions",
    "conclusion",
}


def _read_jsonl(path: Path) -> List[Dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _split_section_path(section_path: str) -> Tuple[str, str]:
    parts = [part.strip() for part in section_path.split("/") if part.strip()]
    if not parts:
        return "Document", "Overview"
    if len(parts) == 1:
        return parts[0], "Overview"
    if len(parts) == 2:
        return parts[1], "Overview"
    return parts[-2], parts[-1]


def _should_skip_row(row: Dict[str, object]) -> bool:
    path = str(row["section_path"]).lower()
    if "/" not in str(row["section_path"]):
        return True
    return any(term in path for term in SKIP_SECTION_TERMS)


def _make_sample(
    row: Dict[str, object],
    unit_title: str,
    section_title: str,
    task_type: str,
    user_content: str,
    assistant_content: str,
) -> Dict[str, object]:
    return {
        "course_id": row["course_id"],
        "source_file": row["source_file"],
        "source_type": row["source_type"],
        "section_path": row["section_path"],
        "unit_title": unit_title,
        "section_title": section_title,
        "task_type": task_type,
        "messages": [
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": assistant_content},
        ],
    }


def _build_model_prompt(row: Dict[str, object]) -> str:
    return (
        "You are building teacher-stage supervised fine-tuning data for a small language model.\n"
        "Input is a course material excerpt. Output must be strict JSON: a list of 2 or 3 objects.\n"
        "Each object must include keys: task_type, user, assistant.\n"
        "Goals:\n"
        "- keep the course context faithful to the source material\n"
        "- connect the material to defensive cybersecurity teaching where appropriate\n"
        "- avoid exploit instructions or operational abuse steps\n"
        "- keep outputs classroom-oriented\n\n"
        f"source_file: {row['source_file']}\n"
        f"section_path: {row['section_path']}\n\n"
        "course_text:\n"
        f"{row['text'][:2400]}\n"
    )


def _extract_json_list(raw: str) -> List[Dict[str, Any]]:
    decoder = json.JSONDecoder()
    for idx, char in enumerate(raw):
        if char != "[":
            continue
        try:
            payload, _ = decoder.raw_decode(raw[idx:])
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, list):
            continue
        out: List[Dict[str, Any]] = []
        for item in payload:
            if not isinstance(item, dict):
                raise ValueError("Generated JSON list contains a non-object item.")
            missing = {"task_type", "user", "assistant"} - set(item)
            if missing:
                raise ValueError(f"Generated JSON item missing keys: {sorted(missing)}")
            out.append(item)
        return out
    raise ValueError("No valid JSON list found in model output.")


def _generate_model_samples(row: Dict[str, object], model: object) -> List[Dict[str, object]]:
    unit_title, section_title = _split_section_path(str(row["section_path"]))
    raw = model.generate(
        messages=[{"role": "user", "content": _build_model_prompt(row)}],
        max_new_tokens=700,
        temperature=0.2,
        do_sample=False,
    )
    payload = _extract_json_list(raw)
    out: List[Dict[str, object]] = []
    for item in payload:
        out.append(
            _make_sample(
                row,
                unit_title,
                section_title,
                str(item["task_type"]),
                str(item["user"]),
                str(item["assistant"]),
            )
        )
    return out


def _split_train_eval(rows: List[Dict[str, object]], eval_ratio: float, seed: int) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
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


def _write_jsonl(path: Path, rows: List[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _append_jsonl(path: Path, row: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate teacher-stage train/eval JSONL from extracted teacher corpus")
    parser.add_argument("--extracted-file", required=True)
    parser.add_argument("--train-out", required=True)
    parser.add_argument("--eval-out", required=True)
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--adapter-path", default="")
    parser.add_argument("--torch-dtype", default="bfloat16")
    parser.add_argument("--eval-ratio", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rows = _read_jsonl(Path(args.extracted_file))
    input_rows = [
        row for row in rows
        if row.get("extraction_status") == "ok"
        and str(row.get("text", "")).strip()
        and not _should_skip_row(row)
    ]
    if not input_rows:
        raise ValueError("No usable extracted rows found.")

    from core.modeling import ChatModel, ModelSettings

    model = ChatModel(
        ModelSettings(
            model_path=args.model_path,
            adapter_path=args.adapter_path or None,
            torch_dtype=args.torch_dtype,
        )
    )

    samples: List[Dict[str, object]] = []
    failed_out = Path(args.train_out).parent / "failed_generation.jsonl"
    if failed_out.exists():
        failed_out.unlink()

    for idx, row in enumerate(input_rows, start=1):
        print(
            f"Generating teacher samples {idx}/{len(input_rows)}: {row.get('section_path')}",
            flush=True,
        )
        try:
            generated = _generate_model_samples(row, model)
        except Exception as exc:
            _append_jsonl(
                failed_out,
                {
                    "course_id": row.get("course_id"),
                    "source_file": row.get("source_file"),
                    "section_path": row.get("section_path"),
                    "error": str(exc),
                },
            )
            print(f"Skipped row {idx}: {exc}", flush=True)
            continue
        samples.extend(generated)

    if not samples:
        raise ValueError("No teacher-stage samples generated.")

    train_rows, eval_rows = _split_train_eval(samples, args.eval_ratio, args.seed)
    _write_jsonl(Path(args.train_out), train_rows)
    _write_jsonl(Path(args.eval_out), eval_rows)

    print(f"Generated samples: {len(samples)}")
    print(f"Train rows: {len(train_rows)} -> {args.train_out}")
    print(f"Eval rows: {len(eval_rows)} -> {args.eval_out}")
    if failed_out.exists():
        print(f"Failed rows logged to: {failed_out}")


if __name__ == "__main__":
    main()
