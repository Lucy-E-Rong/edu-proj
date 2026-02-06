from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import torch
from datasets import Dataset
from peft import LoraConfig, get_peft_model
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.config import load_config


_DTYPE_MAP = {
    "float32": torch.float32,
    "float16": torch.float16,
    "bfloat16": torch.bfloat16,
}


def _read_jsonl(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _messages_to_text(tokenizer: AutoTokenizer, messages: List[Dict[str, str]]) -> str:
    return tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=False,
    )


def _tokenize_dataset(ds: Dataset, tokenizer: AutoTokenizer, max_seq_len: int) -> Dataset:
    def _map_fn(example: Dict[str, Any]) -> Dict[str, Any]:
        text = _messages_to_text(tokenizer, example["messages"])
        tokens = tokenizer(text, truncation=True, max_length=max_seq_len)
        tokens["labels"] = tokens["input_ids"].copy()
        return tokens

    return ds.map(_map_fn, remove_columns=ds.column_names)


def _make_run_dir(cfg: Dict[str, Any]) -> Path:
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_train")
    path = Path(cfg["output"]["runs_dir"]) / run_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="SFT + LoRA trainer")
    parser.add_argument("--config", default="configs/config.yaml")
    parser.add_argument("--dry-run", action="store_true", help="Load config/model and exit before training")
    args = parser.parse_args()

    cfg = load_config(args.config)
    model_cfg = cfg["model"]
    lora_cfg = cfg["lora"]
    train_cfg = cfg["training"]

    dtype = _DTYPE_MAP.get(model_cfg.get("torch_dtype", "bfloat16"), torch.bfloat16)
    if not torch.cuda.is_available() and dtype in {torch.float16, torch.bfloat16}:
        dtype = torch.float32

    tokenizer = AutoTokenizer.from_pretrained(model_cfg["base_model_dir"])
    if tokenizer.pad_token_id is None and tokenizer.eos_token_id is not None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_cfg["base_model_dir"],
        torch_dtype=dtype,
        device_map="auto",
    )

    peft_config = LoraConfig(
        r=lora_cfg["r"],
        lora_alpha=lora_cfg["alpha"],
        lora_dropout=lora_cfg["dropout"],
        target_modules=lora_cfg["target_modules"],
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, peft_config)

    if args.dry_run:
        print("Dry run complete: config and model loaded successfully.")
        return

    train_rows = _read_jsonl(cfg["data"]["train_file"])
    eval_rows = _read_jsonl(cfg["data"]["eval_file"])

    train_ds = Dataset.from_list(train_rows)
    eval_ds = Dataset.from_list(eval_rows) if eval_rows else None

    max_seq_len = int(train_cfg["max_seq_len"])
    train_tok = _tokenize_dataset(train_ds, tokenizer, max_seq_len)
    eval_tok = _tokenize_dataset(eval_ds, tokenizer, max_seq_len) if eval_ds is not None else None

    run_dir = _make_run_dir(cfg)
    adapter_dir = run_dir / cfg["output"]["adapter_subdir"]
    adapter_dir.mkdir(parents=True, exist_ok=True)

    training_args = TrainingArguments(
        output_dir=str(run_dir / "trainer_tmp"),
        learning_rate=float(train_cfg["lr"]),
        num_train_epochs=float(train_cfg["epochs"]),
        per_device_train_batch_size=int(train_cfg["batch"]),
        gradient_accumulation_steps=int(train_cfg["grad_accum"]),
        logging_steps=5,
        save_strategy="no",
        eval_strategy="no" if eval_tok is None else "epoch",
        report_to=[],
        bf16=torch.cuda.is_available(),
        fp16=False,
    )

    data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_tok,
        eval_dataset=eval_tok,
        data_collator=data_collator,
    )

    trainer.train()
    model.save_pretrained(adapter_dir)

    summary = {
        "base_model_dir": model_cfg["base_model_dir"],
        "adapter_dir": str(adapter_dir),
        "train_examples": len(train_rows),
        "eval_examples": len(eval_rows),
        "lr": train_cfg["lr"],
        "epochs": train_cfg["epochs"],
    }
    (run_dir / "train_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    sample_prompts = [
        "Create one short-answer cybersecurity question for beginners.",
        "Create one MCQ about network segmentation.",
    ]
    lines = ["# Eval Samples", ""]
    for prompt in sample_prompts:
        messages = [{"role": "user", "content": prompt}]
        inputs = tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_tensors="pt",
            return_dict=True,
        ).to(model.device)
        out = model.generate(**inputs, max_new_tokens=120)
        gen = tokenizer.decode(out[0, inputs["input_ids"].shape[1] :], skip_special_tokens=True)
        lines.append(f"## Prompt\n{prompt}\n\n## Output\n{gen}\n")

    (run_dir / "eval_samples.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Training complete. Adapter saved to {adapter_dir}")


if __name__ == "__main__":
    main()
