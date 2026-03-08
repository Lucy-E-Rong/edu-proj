from __future__ import annotations

import argparse
from pathlib import Path
from core.config import load_config
from runtime.rag.ingest import  ingest_markdown_corpus, ingest_textbook


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local educator framework CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest_parser = sub.add_parser("ingest", help="Ingest markdown/text sources into local ChromaDB")
    ingest_parser.add_argument(
        "--source-glob",
        type=str,
        default="",
        help="Glob for corpus files, e.g. 'generated_modules/**/*.md'",
    )
    ingest_parser.add_argument(
        "--source-file",
        type=str,
        default="",
        help="Single source file, e.g. 'assets/mock_textbook.txt'",
    )

    def add_model_profile_arg(cmd: argparse.ArgumentParser) -> None:
        cmd.add_argument(
            "--model-profile",
            choices=["base", "general", "teacher"],
            default="teacher",
            help="Runtime generator profile: base model only, general adapter, or teacher adapter.",
        )

    ex = sub.add_parser("exercise", help="Generate an exercise")
    ex.add_argument("prompt", type=str, help="Exercise request prompt")
    ex.add_argument("--no-rag", action="store_true", help="Disable RAG retrieval")
    add_model_profile_arg(ex)

    rb = sub.add_parser("rubric", help="Generate rubric for latest/provided exercise")
    rb.add_argument("prompt", type=str, nargs="?", default="", help="Rubric constraints")
    rb.add_argument("--exercise-text", type=str, default="", help="Explicit exercise text")
    add_model_profile_arg(rb)

    fq = sub.add_parser("factual", help="Answer factual question with RAG")
    fq.add_argument("question", type=str)
    add_model_profile_arg(fq)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    cfg = load_config("configs/config.yaml")

    if args.command == "ingest":
        if args.source_glob:
            count = ingest_markdown_corpus(source_glob=args.source_glob)
            print(f"Ingest complete from glob {args.source_glob}. Chunks indexed: {count}")
        elif args.source_file:
            count = ingest_textbook(source_path=args.source_file)
            print(f"Ingest complete from file {args.source_file}. Chunks indexed: {count}")
        elif Path("generated_modules").exists():
            count = ingest_markdown_corpus(source_glob="generated_modules/**/*.md")
            print("Ingest complete from generated_modules/**/*.md. Chunks indexed:", count)
        else:
            count = ingest_textbook(source_path="assets/mock_textbook.txt")
            print(f"Ingest complete. Chunks indexed: {count}")
        return

    if args.command == "exercise":
        from runtime.workflow.orchestrator import Orchestrator

        orch = Orchestrator(cfg, model_profile=args.model_profile)
        result = orch.run(
            task_type="generate_exercise",
            user_prompt=args.prompt,
            use_rag=not args.no_rag,
        )
    elif args.command == "rubric":
        from runtime.workflow.orchestrator import Orchestrator

        orch = Orchestrator(cfg, model_profile=args.model_profile)
        result = orch.run(
            task_type="generate_rubric",
            user_prompt=args.prompt,
            rubric_source_text=args.exercise_text or None,
            use_rag=False,
        )
    elif args.command == "factual":
        from runtime.workflow.orchestrator import Orchestrator

        orch = Orchestrator(cfg, model_profile=args.model_profile)
        result = orch.run(
            task_type="factual_question",
            user_prompt=args.question,
            use_rag=True,
        )
    else:
        raise ValueError(f"Unknown command: {args.command}")

    print(f"run_id={result['run_id']}")
    print(f"model_profile={result['model_profile']}")
    print(result["output"])
    print(f"verifier={result['verifier']}")


if __name__ == "__main__":
    main()
