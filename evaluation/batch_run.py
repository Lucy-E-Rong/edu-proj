from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

from evaluation.run_eval import evaluate_output


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _run_command(cmd: List[str]) -> str:
    completed = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        text=True,
        input="\n",
        capture_output=True,
        check=True,
    )
    return completed.stdout


def _extract_teacher_output(stdout: str) -> Dict[str, str]:
    lines = stdout.splitlines()
    run_id = ""
    content_lines: List[str] = []
    capture = False
    for line in lines:
        if line.startswith("run_id="):
            run_id = line.split("=", 1)[1].strip()
            continue
        if line.startswith("model_profile="):
            capture = True
            continue
        if line.startswith("verifier="):
            break
        if capture:
            content_lines.append(line)
    return {
        "run_id": run_id,
        "output_text": "\n".join(content_lines).strip(),
    }


def _generate_cybersecurity(prompt_row: Dict[str, Any], adapter_path: str, output_dir: Path) -> Dict[str, str]:
    output_file = output_dir / f"{prompt_row['id']}.md"
    stdout = _run_command(
        [
            sys.executable,
            "training/infer_with_adapter.py",
            "--adapter",
            adapter_path,
            "--prompt",
            prompt_row["prompt"],
            "--out",
            str(output_file),
            "--save_prompt",
        ]
    )
    return {
        "output_text": stdout.strip(),
        "raw_output_path": str(output_file.relative_to(REPO_ROOT)),
        "run_id": "",
    }


def _generate_teacher(prompt_row: Dict[str, Any], output_dir: Path) -> Dict[str, str]:
    stdout = _run_command(
        [
            sys.executable,
            "-m",
            "runtime.app.cli",
            prompt_row["task"],
            "--model-profile",
            "teacher",
            prompt_row["prompt"],
        ]
    )
    extracted = _extract_teacher_output(stdout)
    output_file = output_dir / f"{prompt_row['id']}.md"
    output_file.write_text(extracted["output_text"] + "\n", encoding="utf-8")
    return {
        "output_text": extracted["output_text"],
        "raw_output_path": str(output_file.relative_to(REPO_ROOT)),
        "run_id": extracted["run_id"],
    }


def _run_batch(
    model_type: str,
    prompts_file: Path,
    generated_dir: Path,
    results_dir: Path,
    config_path: str,
    adapter_path: str,
) -> None:
    prompts = _read_jsonl(prompts_file)
    generated_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    aggregate: List[Dict[str, Any]] = []
    for row in prompts:
        if model_type == "cybersecurity_eval":
            generated = _generate_cybersecurity(row, adapter_path, generated_dir)
        else:
            generated = _generate_teacher(row, generated_dir)

        evaluation = evaluate_output(
            model_type=model_type,
            prompt=row["prompt"],
            output_text=generated["output_text"],
            config_path=config_path,
        )
        evaluation["sample_id"] = row["id"]
        evaluation["task"] = row["task"]
        evaluation["prompt"] = row["prompt"]
        evaluation["generated_output_path"] = generated["raw_output_path"]
        evaluation["generation_run_id"] = generated["run_id"]

        result_file = results_dir / f"{row['id']}.json"
        result_file.write_text(json.dumps(evaluation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        aggregate.append(
            {
                "sample_id": row["id"],
                "task": row["task"],
                "final_score": evaluation["final_score"],
                "generated_output_path": generated["raw_output_path"],
                "result_path": str(result_file.relative_to(REPO_ROOT)),
            }
        )
        print(f"[done] {model_type} {row['id']} -> score={evaluation['final_score']}")

    summary_file = results_dir / "summary.json"
    summary_file.write_text(json.dumps(aggregate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[summary] saved to {summary_file.relative_to(REPO_ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch generate and evaluate prompt sets.")
    parser.add_argument(
        "--target",
        choices=["cybersecurity", "teacher", "all"],
        default="all",
        help="Which prompt set to run.",
    )
    parser.add_argument("--config", default="configs/config.yaml")
    parser.add_argument(
        "--general-adapter",
        default="runs/20260313_140305_general_train/adapter",
        help="Adapter path used for cybersecurity prompt generation.",
    )
    parser.add_argument(
        "--output-root",
        default="runs/batch_eval",
        help="Directory for generated outputs and evaluation results.",
    )
    args = parser.parse_args()

    output_root = REPO_ROOT / args.output_root

    if args.target in {"cybersecurity", "all"}:
        _run_batch(
            model_type="cybersecurity_eval",
            prompts_file=REPO_ROOT / "evaluation" / "prompts" / "cybersecurity_prompts.jsonl",
            generated_dir=output_root / "cybersecurity" / "generated",
            results_dir=output_root / "cybersecurity" / "results",
            config_path=args.config,
            adapter_path=args.general_adapter,
        )

    if args.target in {"teacher", "all"}:
        _run_batch(
            model_type="teacher_eval",
            prompts_file=REPO_ROOT / "evaluation" / "prompts" / "teacher_prompts.jsonl",
            generated_dir=output_root / "teacher" / "generated",
            results_dir=output_root / "teacher" / "results",
            config_path=args.config,
            adapter_path=args.general_adapter,
        )


if __name__ == "__main__":
    main()
