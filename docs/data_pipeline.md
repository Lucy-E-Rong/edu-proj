# Data Pipeline Notes (Stage 1)

This document explains how `generated_modules` is transformed into training JSONL for LoRA fine-tuning.

## Scope

- Script: `training/data_build/build_from_modules.py`
- Input: `generated_modules/module_*/combined.md`
- Output:
  - `data/processed/train.jsonl`
  - `data/processed/eval.jsonl`

## Build Command

```bash
python -m training.data_build.build_from_modules \
  --source-dir generated_modules \
  --train-out data/processed/train.jsonl \
  --eval-out data/processed/eval.jsonl
```

## What Is Preserved

Each output JSONL row keeps these fields:

- `module_id`: source module folder (for traceability)
- `source_file`: exact file path used for this sample
- `doc_title`: parsed from front matter `title` or fallback title
- `section_title`: markdown section title (`## ...`) or `Overview`
- `task_type`: generated supervision type (`explain`, `factual_qa`, `safe_rewrite`)
- `risk_level`: currently fixed to `none`
- `messages`: training-ready chat pair (`user`, `assistant`)

Reason:
- Keep provenance (`module_id`, `source_file`) for auditing.
- Keep semantic context (`doc_title`, `section_title`) for debugging and evaluation.
- Keep task label (`task_type`) for dataset analysis and future sampling controls.
- Keep `messages` to match `training/train_lora.py` expected format.

## What Is Filtered or Dropped

Active filtering in current script:

- Markdown code blocks are removed from section text.
- Markdown separator lines (`---`) are removed from section text.
- Extra blank lines are collapsed.
- Section text is truncated by character limit (`max_chars` in script).
- Very short cleaned sections (`<120` chars) are skipped.

Reason:
- Prevent code-heavy or noisy chunks from dominating supervision text.
- Keep per-sample length bounded and stable.
- Drop low-information fragments.

Not preserved as standalone fields:

- Raw front matter key-values except `title`.
- Original full markdown formatting after cleaning.

## Segmentation Rules

1. Enumerate `module_*/combined.md`.
2. Split file into document blocks by front matter (`--- ... ---`).
3. For each block, split by markdown `##` headings.
4. Convert each section into up to 3 training tasks:
   - `explain`
   - `factual_qa`
   - `safe_rewrite`

Reason:
- One long combined file is transformed into many short, task-specific supervised samples.

## Risk Logic Status

Current mode:
- Risk classification is disabled.
- `risk_level` is always `none`.

Code note:
- Legacy risk classification and risk-aware cleaning are kept as comments in
  `training/data_build/build_from_modules.py`.
- You can re-enable by uncommenting those blocks and switching call sites as annotated in the file.

## Reproducibility

- Train/eval split uses seed-based shuffle (`--seed`, default `42`).
- Eval ratio configurable by `--eval-ratio` (default `0.15`).

## Validation Checklist

- Confirm files exist:
  - `data/processed/train.jsonl`
  - `data/processed/eval.jsonl`
- Confirm fields:
  - `module_id`, `source_file`, `doc_title`, `section_title`, `task_type`, `risk_level`, `messages`
- Confirm `risk_level` is `none` in current mode.
