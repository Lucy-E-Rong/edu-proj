# Cybersecurity Education – Local SFT+LoRA Pipeline (Granite 3.3 2B)

## Goal
Fine-tune a local model using course assets to generate course-specific learning materials (questions, solutions, rubrics) without sending private data to external APIs.

## Base model
- ibm-granite/granite-3.3-2b-instruct (downloaded locally to `models/`)

## Repo structure
- scripts/     training & inference scripts
- configs/     config files
- data/        (ignored) private data & processed datasets
- models/      (ignored) downloaded base model
- runs/        (ignored) adapters/checkpoints/logs

## Quickstart (WSL2)
1. Create venv and install deps
2. Download base model into `models/`
3. Prepare data to `data/processed/train.jsonl`
4. Run SFT+LoRA training and save adapter under `runs/<tag>/adapter/`
