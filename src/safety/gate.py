"""
gate.py - Safety gate for LLM responses.

Rules:
  1. recommendation_type == "prescription" → needs_escalation = True
  2. confidence < 0.4 → needs_escalation = True
  3. sources is empty → invalid response → needs_escalation = True
  4. Never return as direct prescription.
"""

import json
from typing import Any


def validate_response(raw_response: str) -> dict:
    """
    Parse and validate an LLM JSON response.

    Returns a dict with keys:
      - safety_passed (bool)
      - needs_escalation (bool)
      - sources (list[str])
      - parsed (dict)   # the parsed JSON or {}
      - reason (str)    # why it failed, if applicable
    """
    result = {
        "safety_passed": False,
        "needs_escalation": False,
        "sources": [],
        "parsed": {},
        "reason": "",
    }

    # --- Parse JSON (aceita markdown ```json ... ``` e texto com JSON embutido) ---
    import re as _re
    text = raw_response.strip()
    # Extrai bloco ```json ... ``` se existir
    md_match = _re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, _re.DOTALL)
    if md_match:
        text = md_match.group(1)
    else:
        # Tenta extrair primeiro objeto JSON do texto
        json_match = _re.search(r"\{.*\}", text, _re.DOTALL)
        if json_match:
            text = json_match.group(0)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as e:
        result["needs_escalation"] = True
        result["reason"] = f"Resposta LLM não é JSON válido: {e}"
        return result

    result["parsed"] = parsed

    # --- Rule 1: prescription type ---
    rec_type = parsed.get("recommendation_type", "analysis")
    if rec_type == "prescription":
        result["needs_escalation"] = True
        result["reason"] = "Tipo 'prescription' não permitido — requer revisão médica."
        return result

    # --- Rule 2: confidence too low ---
    confidence = parsed.get("confidence", 0.0)
    if confidence < 0.4:
        result["needs_escalation"] = True
        result["reason"] = f"Confiança muito baixa ({confidence:.2f} < 0.40)."
        return result

    # --- Rule 3: empty sources ---
    sources = parsed.get("sources", [])
    if not sources:
        result["needs_escalation"] = True
        result["reason"] = "Resposta sem fontes (sources vazio) — inválida."
        return result

    result["safety_passed"] = True
    result["sources"] = sources
    return result


def format_escalation_message(reason: str) -> str:
    """Return a user-friendly escalation message."""
    return (
        "⚠️ **Resposta requer revisão médica especializada.**\n\n"
        f"Motivo: {reason}\n\n"
        "Por favor, encaminhe o paciente para avaliação presencial ou consulte um especialista."
    )
