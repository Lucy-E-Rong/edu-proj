from __future__ import annotations

import argparse
import sys
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.config import load_config
from core.modeling import ChatModel, ModelSettings


def main() -> None:
    parser = argparse.ArgumentParser(description="Inference with base + LoRA adapter")
    parser.add_argument("--adapter", required=True, help="Path to LoRA adapter directory")
    parser.add_argument("--prompt", default="Create one beginner cybersecurity exercise.")
    parser.add_argument("--config", default="configs/config.yaml")
    parser.add_argument(
        "--out",
        default="",
        help="Optional file path to save the inference result. If empty, prints only.",
    )
    parser.add_argument(
        "--save_prompt",
        action="store_true",
        help="If set, include the prompt in the saved file.",
    )

    args = parser.parse_args()

    cfg = load_config(args.config)
    model_cfg = cfg["model"]

    model = ChatModel(
        ModelSettings(
            model_path=model_cfg["base_model_dir"],
            torch_dtype=model_cfg.get("torch_dtype", "bfloat16"),
            adapter_path=args.adapter,
        )
    )

    output = model.generate(
        messages=[{"role": "user", "content": args.prompt}],
        add_generation_prompt=True,
        max_new_tokens=1000,
    )
    print(output)
        # Save to file if requested
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().isoformat(timespec="seconds")
        content_lines = [
            f"# Inference Output",
            f"- timestamp: {timestamp}",
            f"- adapter: {args.adapter}",
            "",
        ]

        if args.save_prompt:
            content_lines.extend(
                [
                    "## PROMPT",
                    args.prompt,
                    "",
                ]
            )

        content_lines.extend(
            [
                "## OUTPUT",
                output,
                "",
            ]
        )

        out_path.write_text("\n".join(content_lines), encoding="utf-8")


if __name__ == "__main__":
    main()
