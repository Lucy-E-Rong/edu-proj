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
    ingest_parser.add_argument(
        "--collection",
        choices=["general", "teacher"],
        default="general",
        help="RAG collection to ingest into.",
    )

    def add_model_profile_arg(cmd: argparse.ArgumentParser) -> None:
        cmd.add_argument(
            "--model-profile",
            choices=["base", "general", "teacher"],
            default="teacher",
            help="Runtime generator profile: base model only, general adapter, or teacher adapter.",
        )

    inc = sub.add_parser("incident", help="Generate an incident-style cybersecurity briefing")
    inc.add_argument("prompt", type=str, help="Incident generation request prompt")
    inc.add_argument("--no-rag", action="store_true", help="Disable RAG retrieval")
    add_model_profile_arg(inc)

    les = sub.add_parser("lesson", help="Generate a lesson-style cybersecurity explanation")
    les.add_argument("prompt", type=str, help="Lesson generation request prompt")
    les.add_argument("--no-rag", action="store_true", help="Disable RAG retrieval")
    add_model_profile_arg(les)

    pr = sub.add_parser("practice", help="Generate a classroom practice activity")
    pr.add_argument("prompt", type=str, help="Practice generation request prompt")
    pr.add_argument("--no-rag", action="store_true", help="Disable RAG retrieval")
    add_model_profile_arg(pr)

    rb = sub.add_parser("rubric", help="Generate rubric for latest/provided practice output")
    rb.add_argument("prompt", type=str, nargs="?", default="", help="Rubric constraints")
    rb.add_argument("--practice-text", type=str, default="", help="Explicit practice text")
    add_model_profile_arg(rb)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    cfg = load_config("configs/config.yaml")

    if args.command == "ingest":
        collection_name = cfg["rag"]["collections"][args.collection]
        if args.source_glob:
            count = ingest_markdown_corpus(
                source_glob=args.source_glob,
                collection_name=collection_name,
            )
            print(
                f"Ingest complete from glob {args.source_glob} into collection "
                f"{args.collection} ({collection_name}). Chunks indexed: {count}"
            )
        elif args.source_file:
            count = ingest_textbook(
                source_path=args.source_file,
                collection_name=collection_name,
            )
            print(
                f"Ingest complete from file {args.source_file} into collection "
                f"{args.collection} ({collection_name}). Chunks indexed: {count}"
            )
        elif Path("generated_modules").exists():
            count = ingest_markdown_corpus(
                source_glob="generated_modules/**/*.md",
                collection_name=collection_name,
            )
            print(
                "Ingest complete from generated_modules/**/*.md into collection "
                f"{args.collection} ({collection_name}). Chunks indexed: {count}"
            )
        else:
            count = ingest_textbook(
                source_path="assets/mock_textbook.txt",
                collection_name=collection_name,
            )
            print(
                f"Ingest complete into collection {args.collection} ({collection_name}). "
                f"Chunks indexed: {count}"
            )
        return

    if args.command == "incident":
        from runtime.workflow.orchestrator import Orchestrator

        orch = Orchestrator(cfg, model_profile=args.model_profile)
        result = orch.run(
            task_type="generate_incident",
            user_prompt=args.prompt,
            use_rag=not args.no_rag,
        )
    elif args.command == "lesson":
        from runtime.workflow.orchestrator import Orchestrator

        orch = Orchestrator(cfg, model_profile=args.model_profile)
        result = orch.run(
            task_type="generate_lesson",
            user_prompt=args.prompt,
            use_rag=not args.no_rag,
        )
    elif args.command == "practice":
        from runtime.workflow.orchestrator import Orchestrator

        orch = Orchestrator(cfg, model_profile=args.model_profile)
        result = orch.run(
            task_type="generate_practice",
            user_prompt=args.prompt,
            use_rag=not args.no_rag,
        )
    elif args.command == "rubric":
        from runtime.workflow.orchestrator import Orchestrator

        orch = Orchestrator(cfg, model_profile=args.model_profile)
        result = orch.run(
            task_type="generate_rubric",
            user_prompt=args.prompt,
            rubric_source_text=args.practice_text or None,
            use_rag=False,
        )
    else:
        raise ValueError(f"Unknown command: {args.command}")

    print(f"run_id={result['run_id']}")
    print(f"model_profile={result['model_profile']}")
    print(result["output"])
    print(f"verifier={result['verifier']}")


if __name__ == "__main__":
    main()
