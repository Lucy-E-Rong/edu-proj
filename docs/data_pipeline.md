# Data Pipeline Notes (Stage 1)

This document explains how `generated_modules` is transformed into training JSONL for LoRA fine-tuning.

## Scope

- Script: `training/data_build/build_from_modules.py`
- Input: `generated_modules/21 Modules/module_*/security_{incident,lesson,practice}_document.md`
- Output:
  - `data/processed/train.jsonl`
  - `data/processed/eval.jsonl`

## Build Command

```bash
python -m training.data_build.build_from_modules \
  --source-dir "generated_modules/21 Modules" \
  --train-out data/processed/train.jsonl \
  --eval-out data/processed/eval.jsonl
```

## What Is Preserved

Each output JSONL row keeps these fields:

- `module_id`: source module folder (for traceability)
- `source_file`: exact file path used for this sample
- `doc_title`: parsed from front matter `title` or fallback title
- `doc_kind`: source document type (`incident`, `lesson`, `practice`)
- `section_title`: markdown section title (`## ...`) or `Overview`
- `task_type`: generated supervision type (`incident_brief`, `lesson_explain`, `practice_generation`)
- `risk_level`: currently fixed to `none`
- `messages`: training-ready chat pair (`user`, `assistant`)

Reason:
- Keep provenance (`module_id`, `source_file`) for auditing.
- Keep semantic context (`doc_title`, `doc_kind`, `section_title`) for debugging and evaluation.
- Keep task label (`task_type`) for dataset analysis and future sampling controls.
- Keep `messages` to match `training/train_lora.py` expected format.

## What Is Filtered or Dropped

Active filtering in current script:

- Markdown code blocks are removed for `incident` and `lesson` documents.
- Markdown code blocks are preserved for `practice` documents.
- Markdown separator lines (`---`) are removed from section text.
- Extra blank lines are collapsed.

Reason:
- Keep incident and lesson samples focused on explanatory natural language.
- Preserve practice scaffolding where code is part of the exercise format.
- Remove separator noise while keeping section content intact.

Not preserved as standalone fields:

- Raw front matter key-values except `title`.
- Original full markdown formatting after cleaning.

## Segmentation Rules

1. Enumerate `module_*/security_incident_document.md`, `security_lesson_document.md`, and `security_practice_document.md`.
2. Parse front matter to recover the document title.
3. Split each document by markdown `##` headings.
4. Convert each section into exactly one task based on document type:
   - `incident -> incident_brief`
   - `lesson -> lesson_explain`
   - `practice -> practice_generation`

Reason:
- The module's built-in incident/lesson/practice separation is treated as the supervision signal rather than being remapped into the old generic task trio.

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
  - `module_id`, `source_file`, `doc_title`, `doc_kind`, `section_title`, `task_type`, `risk_level`, `messages`
- Confirm `risk_level` is `none` in current mode.
