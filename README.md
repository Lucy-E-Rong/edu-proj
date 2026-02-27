# Local Cybersecurity Education Pipeline (Granite + LoRA)

**Branch note**
- `main`: local development profile (2B)
- `server/8b`: server profile (8B)

This project is designed for **local, privacy-preserving cybersecurity education content creation and assessment support**. It provides a runnable pipeline for exercise/rubric/factual generation plus adapter fine-tuning.

## What This Tool Enables
- `CAG` asset grounding from local course files.
- Optional `RAG` retrieval from local Chroma (`top-3` by default).
- Orchestrator with shared run memory and trace/report outputs.
- Teacher-facing refinement loop (up to 2 rounds).
- Verifier gate before final output.
- `SFT + LoRA` adapter training from local JSONL data.
- Inference with `base model + adapter`.
- Ollama export placeholder (`training/export_ollama/README.md`).

## Pipeline Flowchart
```mermaid
flowchart TD
  TP[Teacher Prompt] --> ORCH[Orchestrator + Shared Memory]
  CAG[CAG Assets] --> ORCH
  ORCH --> RAG{Use RAG?}
  RAG -->|No| LLM[Primary LLM: Granite]
  RAG -->|Yes| RET[Retrieve top-3 from Chroma]
  RET --> LLM
  LLM --> VER[Verifier]
  VER --> OK{Pass?}
  OK -->|No, <=2 rounds| REF[Refinement Loop]
  REF --> LLM
  OK -->|Yes| OUT[Output + Run Report]

  CA[Course Assets] --> DB[Dataset Builder]
  DB --> SFT[SFT + LoRA Training]
  SFT --> ADP[Adapter]
  ADP --> INF[Inference: Base + Adapter]
  INF --> OLLA[Future: Ollama Export]
```

## Server Usage Guide (8B / H100)

### 1) Clone the repo
```bash
git clone <your_repo_url>
cd edu-proj
```

### 2) Create virtual environment and install requirements
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3) Download base model to local directory
Hugging Face model reference (plain text): `ibm-granite/granite-3.3-8b-instruct`

```bash
huggingface-cli download ibm-granite/granite-3.3-8b-instruct \
  --local-dir models/granite-3.3-8b-instruct
```

### 4) Update config
Edit `configs/config.yaml` and confirm:
```yaml
model:
  base_model_dir: "models/granite-3.3-8b-instruct"
```

### 5) Generate mock training data
```bash
python training/data_build/make_mock_data.py
```
Generate training data from real modules:
```bash
python training/data_build/make_data_from_modules.py --modules-dir generated_modules
```

### 6) Build local RAG index (ingest)
```bash
python -m runtime.app.cli ingest
```
If `generated_modules/` exists, `ingest` defaults to `generated_modules/**/*.md`.
You can also specify an explicit source:
```bash
python -m runtime.app.cli ingest --source-glob "generated_modules/**/*.md"
python -m runtime.app.cli ingest --source-file "assets/mock_textbook.txt"
```

### 7) Run runtime CLI demo
Exercise:
```bash
python -m runtime.app.cli exercise "Create a beginner phishing quiz"
```

Rubric:
```bash
python -m runtime.app.cli rubric "Focus on clarity and correctness"
# or
python -m runtime.app.cli rubric --exercise-text "<paste exercise text>"
```

Factual:
```bash
python -m runtime.app.cli factual "What is least privilege?"
```

### 8) Run LoRA training
Dry-run (config + model load check only):
```bash
python training/train_lora.py --dry-run
```

Full run:
```bash
python training/train_lora.py --config configs/config.yaml
```

### 9) Run inference with adapter and save output
```bash
python training/infer_with_adapter.py \
  --adapter runs/<run_id>/adapter \
  --prompt "Create one cybersecurity scenario question" \
  --out runs/<run_id>/inference/scenario.md \
  --save_prompt
```

### 10) Output locations
Artifacts are written under:
- `runs/<run_id>/report.md`
- `runs/<run_id>/trace.jsonl`
- `runs/<run_id>/adapter/`
- `runs/<run_id>/inference/...`

## Repository Artifact Tracking Notes
By default, local-heavy artifact folders are treated as non-source outputs:
- `models/`, `data/`, and `chroma/` are ignored by `.gitignore`.
- `runs/` should also be treated as generated runtime/training output; this branch may still include selected run artifacts for reference.

## 0227 Update

### What this tool is designed for
This tool is designed to support local, privacy-preserving cybersecurity education content workflows from end to end. It is meant to help instructors generate course-aligned learning materials,The system can generate content at runtime by integrating search results (not solely relying on model memory), and can train pluggable adapters locally, with the entire process independent of cloud hosting platforms.

### Motivation behind the design
The core motivation is to avoid a one-size-fits-all black-box generation process. Cybersecurity teaching content often needs strict local control, traceability to source materials, and the ability to adapt output style to course goals. The project therefore separates domain knowledge grounding, model adaptation, and runtime orchestration so each part can be inspected, updated, and reused.

### Enabled features and why they are meaningful
The runtime pipeline combines orchestrated generation with optional retrieval so outputs can stay aligned with local module data rather than only model priors. Shared-memory orchestration and run artifacts (`report.md`, `trace.jsonl`) make each run auditable for teaching review. The verifier and refinement loop provide a practical quality/safety checkpoint before final output is accepted. On the training side, module-to-JSONL transformation enables structured supervision from David's generated modules, while two-stage LoRA training (general adapter first, then teacher-specific continuation) supports both broad cybersecurity coverage and instructor-level customization without retraining the full base model.

### Changes 
1. Removed legacy mock assets and mock data generation flow.
2. Switched ingestion defaults to real corpus usage from `generated_modules`, including directory-based ingestion behavior.
3. Updated CAG asset loading defaults to non-mock paths and made asset loading tolerant when optional files are absent.
4. Implemented Stage 1 dataset builder from module corpus:
   - Added `training/data_build/build_from_modules.py`.
   - Added structured JSONL generation for `train/eval` with task-oriented `messages`.
5. Added Stage 1 data documentation:
   - Added `docs/data_pipeline.md` to document preserved fields, filtered content, and transformation rules.
6. Implemented Stage 2 two-stage training support:
   - Extended `training/train_lora.py` with `--mode`, `--init-adapter`, `--train-file`, `--eval-file`.
   - Added run naming and summary metadata for `general` vs `teacher` stages.
7. Added Stage 2 training documentation:
   - Added `docs/model_training_pipeline.md` for General -> Teacher adapter workflow.
8. Updated README operational steps to align with module-based data preparation, two-stage training, and current CLI behavior.
