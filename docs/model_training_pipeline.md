# Model Training Pipeline (Stage 2)

This project uses a two-stage adapter training workflow:

1. Stage A: train a general cybersecurity education adapter from David's modules.
2. Stage B: continue training from Stage A to produce teacher-specific adapters.

## Stage A: General Model Adapter

Input:
- `generated_modules/21 Modules/module_*/security_{incident,lesson,practice}_document.md`
  (converted to JSONL via `build_from_modules.py`)

Command:

```bash
python -m training.data_build.build_from_modules \
  --source-dir "generated_modules/21 Modules" \
  --train-out data/processed/train.jsonl \
  --eval-out data/processed/eval.jsonl

python training/train_lora.py \
  --mode general \
  --config configs/config.yaml
```

Output:
- `runs/<timestamp>_general_train/adapter/`

## Stage B: Teacher Custom Adapter

Input:
- Stage A adapter (`runs/<general_run_id>/adapter/`)
- Teacher-specific JSONL files

Command:

```bash
python training/train_lora.py \
  --mode teacher \
  --config configs/config.yaml \
  --init-adapter runs/<general_run_id>/adapter \
  --train-file data/teachers/<teacher_id>/processed/train.jsonl \
  --eval-file data/teachers/<teacher_id>/processed/eval.jsonl
```

Output:
- `runs/<timestamp>_teacher_train/adapter/`

## Inference

Use the teacher adapter directly:

```bash
python training/infer_with_adapter.py \
  --adapter runs/<teacher_run_id>/adapter \
  --prompt "Create one beginner cybersecurity exercise." \
  --out runs/<teacher_run_id>/inference/sample.md \
  --save_prompt
```

## Why this design

- Stage A captures broad domain knowledge from David's module corpus, using the
  module's own incident/lesson/practice document split as the supervision
  structure.
- Stage B adds individual teacher preferences and local curriculum style.
- Keeping adapters separate makes retraining and comparison simpler.
