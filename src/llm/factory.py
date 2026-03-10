"""
factory.py - Returns MockLLM or real LLM based on USE_MOCK_LLM env var.
"""

import os
from typing import Any


def get_llm(model_path: str = "") -> Any:
    """
    Factory function.
    - USE_MOCK_LLM=true  → MockLLM (default, no GPU required)
    - USE_MOCK_LLM=false → real LoRA model loaded from model_path
    """
    use_mock = os.environ.get("USE_MOCK_LLM", "true").strip().lower()

    if use_mock == "true":
        from src.llm.mock_llm import MockLLM
        return MockLLM()
    else:
        if not model_path:
            model_path = os.environ.get("MODEL_PATH", "")
        if not model_path:
            raise ValueError(
                "MODEL_PATH não definido. "
                "Configure a variável de ambiente MODEL_PATH com o caminho do LoRA adapter."
            )
        from src.llm.model_loader import load_lora_model
        return load_lora_model(model_path)
