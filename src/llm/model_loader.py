"""
model_loader.py - Loads a LoRA-fine-tuned model from Google Drive (Colab only).
Only used when USE_MOCK_LLM=false.
"""

import os
from typing import Any


def load_lora_model(model_path: str) -> Any:
    """
    Load a LoRA-fine-tuned model from the given path.
    Requires: transformers, peft, torch, accelerate.

    Returns a callable that accepts a prompt string and returns a string.
    """
    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
        from peft import PeftModel
    except ImportError as e:
        raise ImportError(
            "Dependências de modelo não instaladas. "
            "Execute: pip install transformers peft torch accelerate"
        ) from e

    base_model_id = os.environ.get("BASE_MODEL_ID", "mistralai/Mistral-7B-Instruct-v0.1")

    print(f"[model_loader] Carregando tokenizer de {base_model_id}...")
    tokenizer = AutoTokenizer.from_pretrained(base_model_id, trust_remote_code=True)

    print(f"[model_loader] Carregando modelo base...")
    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_id,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True,
    )

    print(f"[model_loader] Aplicando LoRA adapter de {model_path}...")
    model = PeftModel.from_pretrained(base_model, model_path)
    model.eval()

    pipe = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=512,
        temperature=0.1,
        do_sample=True,
    )

    class _LoRALLM:
        def invoke(self, prompt: str) -> str:
            out = pipe(prompt, return_full_text=False)
            return out[0]["generated_text"]

        def __call__(self, prompt: str) -> str:
            return self.invoke(prompt)

    print("[model_loader] Modelo carregado com sucesso.")
    return _LoRALLM()
