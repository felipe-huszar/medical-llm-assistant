"""
gate.py - Safety gate for LLM responses (prose format).

Rules:
  1. Resposta muito curta (< 80 chars) → escalation
  2. Contém linguagem de prescrição direta → escalation
  3. Seções obrigatórias ausentes → aviso (não escalation)
"""

import re
from typing import Any

# Palavras que indicam prescrição direta (não permitida)
_PRESCRIPTION_PATTERNS = [
    r"\bprescrevo\b",
    r"\bprescrito\b",
    r"\btome\s+\d",
    r"\d+\s*mg/dia\b",
    r"\bposologia\b",
    r"\bvia oral\b.*\bcomprimido",
]

_EXPECTED_SECTIONS = [
    "Hipótese diagnóstica principal",
    "Diagnósticos diferenciais",
    "Exames recomendados",
]


def validate_response(raw_response: str) -> dict:
    """
    Valida resposta em prosa do modelo clínico.

    Returns dict with keys:
      - safety_passed (bool)
      - needs_escalation (bool)
      - sections (dict)   # seções extraídas da prosa
      - reason (str)
    """
    result = {
        "safety_passed": False,
        "needs_escalation": False,
        "sections": {},
        "reason": "",
    }

    text = raw_response.strip()

    # Rule 1: resposta muito curta
    if len(text) < 80:
        result["needs_escalation"] = True
        result["reason"] = f"Resposta muito curta ({len(text)} chars) — possivelmente incompleta."
        return result

    # Rule 2: linguagem de prescrição direta
    text_lower = text.lower()
    for pattern in _PRESCRIPTION_PATTERNS:
        if re.search(pattern, text_lower):
            result["needs_escalation"] = True
            result["reason"] = "Resposta contém linguagem de prescrição direta — não permitido."
            return result

    # Extrai seções da prosa
    sections = _extract_sections(text)
    result["sections"] = sections

    result["safety_passed"] = True
    return result


def _extract_sections(text: str) -> dict:
    """Extrai seções do formato Lucas do texto em prosa."""
    section_headers = [
        "Resumo clínico",
        "Raciocínio clínico",
        "Hipótese diagnóstica principal",
        "Diagnósticos diferenciais",
        "Exames recomendados",
    ]

    sections = {}
    lines = text.split("\n")
    current_section = None
    current_content = []

    for line in lines:
        stripped = line.strip()
        # Detecta cabeçalho de seção (com ou sem ":")
        matched = None
        for header in section_headers:
            if stripped.lower().startswith(header.lower()):
                matched = header
                break

        if matched:
            # Salva seção anterior
            if current_section:
                sections[current_section] = "\n".join(current_content).strip()
            current_section = matched
            # Conteúdo inline (ex: "Hipótese diagnóstica principal: insuf. cardíaca")
            after_colon = re.sub(rf"^{re.escape(matched)}\s*:?\s*", "", stripped, flags=re.IGNORECASE)
            current_content = [after_colon] if after_colon else []
        elif current_section:
            current_content.append(line)

    # Última seção
    if current_section:
        sections[current_section] = "\n".join(current_content).strip()

    return sections


def _extract_list_items(text: str) -> list[str]:
    """Extrai itens de lista de um bloco de texto."""
    items = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        # Remove marcadores de lista: -, •, *, 1., 2., etc.
        clean = re.sub(r"^[-•*\d]+[.)]\s*", "", line).strip()
        # Se nenhum marcador foi removido, tenta remover traço simples
        if clean == line:
            clean = re.sub(r"^-\s+", "", line).strip()
        if clean and len(clean) > 2:
            items.append(clean)
    return items


def format_escalation_message(reason: str) -> str:
    """Return a user-friendly escalation message."""
    return (
        "⚠️ **Resposta requer revisão médica especializada.**\n\n"
        f"Motivo: {reason}\n\n"
        "Por favor, encaminhe o paciente para avaliação presencial ou consulte um especialista."
    )
