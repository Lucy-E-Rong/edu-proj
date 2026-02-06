# Ollama Export Placeholder

This project does not implement conversion yet. Two future paths:

## Path A: Merge adapter then convert merged model to GGUF
1. Load base model + LoRA adapter.
2. Merge LoRA weights into base (`merge_and_unload` in PEFT).
3. Save merged Hugging Face model locally.
4. Convert merged model to GGUF using llama.cpp conversion tooling.
5. Create `Modelfile` with `FROM <merged-model.gguf>` and run `ollama create`.

## Path B: Keep base + adapter separated (GGUF adapter workflow)
1. Convert base model to GGUF.
2. Convert LoRA adapter to GGUF adapter format (tooling-dependent).
3. Create `Modelfile`:
   - `FROM <base-model.gguf>`
   - `ADAPTER <adapter.gguf>`
4. Build with `ollama create` and validate outputs.

Check current tooling compatibility before implementation because adapter GGUF support can vary by model architecture and llama.cpp/Ollama versions.
