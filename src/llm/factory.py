"""
factory.py - Returns MockLLM or real LLM based on USE_MOCK_LLM env var.

Caches the real LLM after first load to avoid reloading the model into GPU RAM
on subsequent calls (e.g. demo cells + Gradio launch in the same Colab session).
"""

import os
from typing import Any

_cached_llm: Any = None


def get_llm(model_path: str = "") -> Any:
    """
    Factory function — idempotent for the real model.
    - USE_MOCK_LLM=true  → new MockLLM() every call (stateless, cheap)
    - USE_MOCK_LLM=false → loads once, caches globally (avoids double GPU load)
    """
    global _cached_llm

    use_mock = os.environ.get("USE_MOCK_LLM", "true").strip().lower()

    if use_mock == "true":
        from src.llm.mock_llm import MockLLM
        return MockLLM()

    # Real model: return cached instance if already loaded
    if _cached_llm is not None:
        return _cached_llm

    if not model_path:
        model_path = os.environ.get("MODEL_PATH", "")
    if not model_path:
        raise ValueError(
            "MODEL_PATH não definido. "
            "Configure a variável de ambiente MODEL_PATH com o caminho do LoRA adapter."
        )

    from src.llm.model_loader import load_lora_model
    _cached_llm = load_lora_model(model_path)
    return _cached_llm


def reset_llm_cache() -> None:
    """Force reload on next get_llm() call (useful for testing)."""
    global _cached_llm
    _cached_llm = None
