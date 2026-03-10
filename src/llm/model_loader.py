"""
model_loader.py - Loads the LoRA-fine-tuned Mistral adapter.
Only used when USE_MOCK_LLM=false.

Base model: unsloth/mistral-7b-bnb-4bit
Adapter: trained with PEFT/LoRA via unsloth (r=16, alpha=16)
"""

import os
from typing import Any


def load_lora_model(model_path: str) -> Any:
    """
    Load the Mistral LoRA adapter using unsloth (matches training environment).

    Args:
        model_path: local path to adapter folder (adapter_config.json + adapter_model.safetensors)

    Returns:
        A callable LLM object with .invoke(prompt) -> str
    """
    try:
        from unsloth import FastLanguageModel
    except ImportError as e:
        raise ImportError(
            "unsloth não instalado. Execute: pip install unsloth"
        ) from e

    base_model_id = os.environ.get("BASE_MODEL_ID", "unsloth/mistral-7b-bnb-4bit")

    print(f"[model_loader] Carregando base model: {base_model_id}")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=base_model_id,
        max_seq_length=2048,
        load_in_4bit=True,
    )

    print(f"[model_loader] Aplicando LoRA adapter: {model_path}")
    from peft import PeftModel
    model = PeftModel.from_pretrained(model, model_path)
    FastLanguageModel.for_inference(model)

    print("[model_loader] Modelo pronto para inferência.")

    class _LoRALLM:
        def invoke(self, prompt: str) -> str:
            inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
            import torch
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=512,
                    temperature=0.1,
                    do_sample=True,
                    pad_token_id=tokenizer.eos_token_id,
                )
            # Retorna só o texto gerado (sem o prompt)
            input_len = inputs["input_ids"].shape[1]
            generated = outputs[0][input_len:]
            return tokenizer.decode(generated, skip_special_tokens=True)

        def __call__(self, prompt: str) -> str:
            return self.invoke(prompt)

    return _LoRALLM()
