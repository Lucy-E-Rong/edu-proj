# Local Educator Framework + SFT LoRA Scaffold

This repository contains a minimal runnable scaffold for:
- Runtime pipeline: CAG + RAG + orchestrator + verifier + refinement loop.
- Training pipeline: mock data generation + SFT with LoRA adapter export.

## 1) Environment (WSL2)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2) Base model
The base model is expected locally at:
- `models/granite-3.3-8b-instruct`

No weight download is performed by this scaffold.

## 3) Build RAG index
```bash
python -m runtime.app.cli ingest
```

## 4) Runtime CLI demos
Generate exercise (CAG + optional RAG + verifier + refinement):
```bash
python -m runtime.app.cli exercise "Create a beginner phishing quiz"
```

Generate rubric (uses explicit text or latest stored exercise):
```bash
python -m runtime.app.cli rubric "Focus on clarity and correctness"
python -m runtime.app.cli rubric --exercise-text "<paste exercise text>"
```

Factual Q&A with RAG:
```bash
python -m runtime.app.cli factual "What is least privilege?"
```

Run reports are written to `runs/<run_id>/report.md` and traces to `runs/<run_id>/trace.jsonl`.

## 5) Generate mock training data
```bash
python training/data_build/make_mock_data.py
```

## 6) Train LoRA adapter (SFT)
```bash
python training/train_lora.py --config configs/config.yaml
```

Dry-run (load config and model only):
```bash
python training/train_lora.py --dry-run
```

Adapter output is saved under `runs/<run_id>/adapter/`.

## 7) Inference with base + adapter
```bash
python training/infer_with_adapter.py --adapter runs/<run_id>/adapter --prompt "Create one cybersecurity scenario question"
```

## 8) Ollama export placeholder
See `training/export_ollama/README.md`.
