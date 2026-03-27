from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from evaluation.hard_rules import evaluate_hard_rules
from evaluation.llm_judge import LLMJudge
from evaluation.prompt_parser import parse_prompt
from evaluation.source_locator import locate_sources


def _read_output(args: argparse.Namespace) -> str:
    if args.output_text:
        return args.output_text
    if args.output_file:
        return Path(args.output_file).read_text(encoding="utf-8")
    raise ValueError("Either --output-text or --output-file must be provided.")


def _final_score(hard_score: float, llm_result: Dict[str, Any]) -> float:
    llm_avg = (
        llm_result["prompt_match_score"]
        + llm_result["source_learning_score"]
        + llm_result["teaching_usefulness_score"]
    ) / 3.0
    return round(hard_score * 0.35 + llm_avg * 0.65, 2)


def evaluate_output(
    model_type: str,
    prompt: str,
    output_text: str,
    config_path: str = "configs/config.yaml",
    judge: LLMJudge | None = None,
) -> Dict[str, Any]:
    prompt_info = parse_prompt(prompt)
    source_info = locate_sources(model_type, prompt_info)
    hard_result = evaluate_hard_rules(prompt_info, output_text)

    effective_judge = judge or LLMJudge(config_path=config_path)
    llm_result = effective_judge.evaluate(
        prompt=prompt,
        task_type=prompt_info.get("task_type", "unknown"),
        output_text=output_text,
        source_snippets=source_info.get("snippets", []),
        source_status=source_info.get("status", "source_not_found"),
    )

    return {
        "model_type": model_type,
        "prompt_info": prompt_info,
        "source_info": source_info,
        "hard_result": hard_result,
        "llm_result": llm_result,
        "final_score": _final_score(hard_result["score"], llm_result),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate an existing model output.")
    parser.add_argument("--model-type", choices=["cybersecurity_eval", "teacher_eval"], required=True)
    parser.add_argument("--prompt", required=True, help="Original user prompt.")
    parser.add_argument("--output-file", default="", help="Path to the generated output file.")
    parser.add_argument("--output-text", default="", help="Generated output text.")
    parser.add_argument("--config", default="configs/config.yaml")
    parser.add_argument("--save-json", default="", help="Optional path to save the evaluation result.")
    args = parser.parse_args()

    output_text = _read_output(args)
    result = evaluate_output(
        model_type=args.model_type,
        prompt=args.prompt,
        output_text=output_text,
        config_path=args.config,
    )

    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    print(rendered)

    if args.save_json:
        output_path = Path(args.save_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
