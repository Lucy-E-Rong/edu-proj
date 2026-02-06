from __future__ import annotations

import argparse

from core.config import load_config
from runtime.rag.ingest import ingest_textbook


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local educator framework CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("ingest", help="Ingest mock textbook into local ChromaDB")

    ex = sub.add_parser("exercise", help="Generate an exercise")
    ex.add_argument("prompt", type=str, help="Exercise request prompt")
    ex.add_argument("--no-rag", action="store_true", help="Disable RAG retrieval")

    rb = sub.add_parser("rubric", help="Generate rubric for latest/provided exercise")
    rb.add_argument("prompt", type=str, nargs="?", default="", help="Rubric constraints")
    rb.add_argument("--exercise-text", type=str, default="", help="Explicit exercise text")

    fq = sub.add_parser("factual", help="Answer factual question with RAG")
    fq.add_argument("question", type=str)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    cfg = load_config("configs/config.yaml")

    if args.command == "ingest":
        count = ingest_textbook(source_path="assets/mock_textbook.txt")
        print(f"Ingest complete. Chunks indexed: {count}")
        return

    if args.command == "exercise":
        from runtime.workflow.orchestrator import Orchestrator

        orch = Orchestrator(cfg)
        result = orch.run(
            task_type="generate_exercise",
            user_prompt=args.prompt,
            use_rag=not args.no_rag,
        )
    elif args.command == "rubric":
        from runtime.workflow.orchestrator import Orchestrator

        orch = Orchestrator(cfg)
        result = orch.run(
            task_type="generate_rubric",
            user_prompt=args.prompt,
            rubric_source_text=args.exercise_text or None,
            use_rag=False,
        )
    elif args.command == "factual":
        from runtime.workflow.orchestrator import Orchestrator

        orch = Orchestrator(cfg)
        result = orch.run(
            task_type="factual_question",
            user_prompt=args.question,
            use_rag=True,
        )
    else:
        raise ValueError(f"Unknown command: {args.command}")

    print(f"run_id={result['run_id']}")
    print(result["output"])
    print(f"verifier={result['verifier']}")


if __name__ == "__main__":
    main()
