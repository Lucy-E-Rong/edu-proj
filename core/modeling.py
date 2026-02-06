from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


_DTYPE_MAP = {
    "float32": torch.float32,
    "float16": torch.float16,
    "bfloat16": torch.bfloat16,
}


@dataclass
class ModelSettings:
    model_path: str
    torch_dtype: str = "bfloat16"
    device_map: str = "auto"
    adapter_path: Optional[str] = None


class ChatModel:
    def __init__(self, settings: ModelSettings) -> None:
        self.settings = settings
        chosen_dtype = _DTYPE_MAP.get(settings.torch_dtype, torch.bfloat16)
        if not torch.cuda.is_available() and chosen_dtype in {torch.float16, torch.bfloat16}:
            chosen_dtype = torch.float32

        self.tokenizer = AutoTokenizer.from_pretrained(settings.model_path)
        self.model = AutoModelForCausalLM.from_pretrained(
            settings.model_path,
            torch_dtype=chosen_dtype,
            device_map=settings.device_map,
        )
        if settings.adapter_path:
            self.model = PeftModel.from_pretrained(self.model, settings.adapter_path)

        if self.tokenizer.pad_token_id is None and self.tokenizer.eos_token_id is not None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

    def build_inputs(
        self,
        messages: List[Dict[str, str]],
        add_generation_prompt: bool = True,
    ) -> Dict[str, torch.Tensor]:
        inputs = self.tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=add_generation_prompt,
            return_tensors="pt",
            return_dict=True,
        )
        return inputs.to(self.model.device)

    def generate(
        self,
        messages: List[Dict[str, str]],
        max_new_tokens: int = 384,
        temperature: float = 0.7,
        do_sample: bool = True,
        add_generation_prompt: bool = True,
    ) -> str:
        inputs = self.build_inputs(messages, add_generation_prompt=add_generation_prompt)
        output = self.model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            do_sample=do_sample,
            pad_token_id=self.tokenizer.pad_token_id,
        )
        input_len = inputs["input_ids"].shape[1]
        return self.tokenizer.decode(output[0, input_len:], skip_special_tokens=True).strip()
