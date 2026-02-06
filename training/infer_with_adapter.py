from __future__ import annotations

import argparse
import sys
from pathlib import Path

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
        max_new_tokens=256,
    )
    print(output)


if __name__ == "__main__":
    main()
