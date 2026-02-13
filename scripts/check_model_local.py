from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

MODEL_PATH = "models/granite-3.3-8b-instruct"

tok = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    device_map="auto",
    torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
)

print("Loaded from:", MODEL_PATH)
print("CUDA:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
