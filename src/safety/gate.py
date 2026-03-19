"""
gate.py - Safety gate for LLM responses (prose format).

Rules:
  1. Resposta muito curta (< 80 chars) → escalation
  2. Contém linguagem de prescrição direta → escalation
  3. Guardrails de segurança clínica:
     - insuficiência de dados
     - fora de escopo
     - evidência mínima para hipóteses graves
"""

import re
import unicodedata
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

_SECTION_HEADERS = [
    "Status da análise",
    "Resumo clínico",
    "Raciocínio clínico",
    "Hipótese diagnóstica principal",
    "Diagnósticos diferenciais",
    "Exames recomendados",
    "Dados faltantes",
    "Especialidade sugerida",
]

_OUT_OF_SCOPE_PATTERNS = [
    r"dermatoscopia",
    r"les[aã]o cut[aâ]nea cr[oô]nica",
    r"antidepressivo",
    r"psiqui[aá]tric",
    r"fundoscopia",
    r"oftalmol[oó]gic",
    r"quimioter",
    r"oncolog",
    r"subespecial",
]

_GRAVE_HYPOTHESES_RULES = {
    "meningite": ["rigidez de nuca", "fotofobia", "confus", "alteracao de consciencia", "febre"],
    "hemorragia subaracnoide": ["cefaleia subita", "thunderclap", "trovoada", "rebaixamento", "vomitos"],
    "apendicite": ["quadrante inferior direito", "qid", "dor abdominal", "nausea", "vomito", "febre baixa"],
    "síndrome coronariana aguda": ["dor toracica opressiva", "sudorese", "dispneia", "irradiacao", "equivalente anginoso"],
    "tromboembolismo pulmonar": ["dispneia subita", "dor pleuritica", "hemoptise", "sincope", "taquicardia"],
    "tep": ["dispneia subita", "dor pleuritica", "hemoptise", "sincope", "taquicardia"],
}

_STATUS_ALIASES = {
    "suspicious": "supported_hypothesis",
    "provavel": "supported_hypothesis",
    "provável": "supported_hypothesis",
    "likely": "supported_hypothesis",
    "plausible": "supported_hypothesis",
    "urgent": "needs_urgent_escalation",
}

_ALLOWED_NONSUPPORTED_STATUSES = {
    "insufficient_data",
    "out_of_scope",
    "needs_urgent_escalation",
}

_INSUFFICIENT_DATA_HYPOTHESIS_ALLOWED = {
    "indeterminada",
    "indeterminada com os dados atuais",
    "necessita refinamento clinico",
    "necessita refinamento clínico",
    "avaliacao adicional necessaria",
    "avaliação adicional necessária",
}

_OUT_OF_SCOPE_HYPOTHESIS_ALLOWED = {
    "fora do escopo principal do assistente",
    "avaliacao especializada necessaria",
    "avaliação especializada necessária",
}


def validate_response(raw_response: str, context_text: str = "") -> dict:
    """
    Valida resposta em prosa do modelo clínico.

    Returns dict with keys:
      - safety_passed (bool)
      - needs_escalation (bool)
      - sections (dict)
      - reason (str)
      - analysis_status (str)
    """
    result = {
        "safety_passed": False,
        "needs_escalation": False,
        "sections": {},
        "reason": "",
        "analysis_status": "",
    }

    text = (raw_response or "").strip()

    if len(text) < 80:
        result["needs_escalation"] = True
        result["reason"] = f"Resposta muito curta ({len(text)} chars) — possivelmente incompleta."
        return result

    text_lower = text.lower()
    for pattern in _PRESCRIPTION_PATTERNS:
        if re.search(pattern, text_lower):
            result["needs_escalation"] = True
            result["reason"] = "Resposta contém linguagem de prescrição direta — não permitido."
            return result

    sections = _extract_sections(text)
    result["sections"] = sections

    raw_status = sections.get("Status da análise", "").strip()
    analysis_status = _normalize(raw_status)
    analysis_status = _STATUS_ALIASES.get(analysis_status, analysis_status)
    if raw_status:
        sections["Status da análise"] = analysis_status
    result["analysis_status"] = analysis_status

    hypothesis = sections.get("Hipótese diagnóstica principal", "").strip()
    normalized_hypothesis = _normalize(hypothesis)

    # Guardrail 1: fora de escopo deve ser reconhecido explicitamente
    if _looks_out_of_scope(context_text):
        specialty = sections.get("Especialidade sugerida", "").strip()
        if analysis_status != "out_of_scope" and "fora do escopo" not in normalized_hypothesis and not specialty:
            result["needs_escalation"] = True
            result["reason"] = "Caso potencialmente fora do escopo principal do assistente sem reconhecimento explícito de limitação."
            return result

    # Guardrail 2: status insuficiente/fora de escopo precisa ser consistente com a hipótese principal
    if analysis_status == "insufficient_data":
        if normalized_hypothesis not in {_normalize(x) for x in _INSUFFICIENT_DATA_HYPOTHESIS_ALLOWED}:
            result["needs_escalation"] = True
            result["reason"] = "Status insufficient_data inconsistente com hipótese principal afirmativa. A hipótese principal deve permanecer indeterminada quando faltarem dados."
            return result

    if analysis_status == "out_of_scope":
        if normalized_hypothesis not in {_normalize(x) for x in _OUT_OF_SCOPE_HYPOTHESIS_ALLOWED}:
            result["needs_escalation"] = True
            result["reason"] = "Status out_of_scope inconsistente com hipótese principal. O caso deve ser tratado como fora do escopo e orientar especialidade."
            return result

    # Guardrail 3: hipóteses graves precisam de evidência mínima no contexto
    if hypothesis and analysis_status not in _ALLOWED_NONSUPPORTED_STATUSES:
        min_evidence_failure = _check_minimum_evidence_failure(hypothesis, context_text)
        if min_evidence_failure:
            result["needs_escalation"] = True
            result["reason"] = min_evidence_failure
            return result

    # Guardrail 4: se o caso é vago e o modelo não admitiu insuficiência de dados, bloquear falsa precisão
    if _looks_insufficient_data_case(context_text):
        if analysis_status != "insufficient_data":
            result["needs_escalation"] = True
            result["reason"] = "Dados insuficientes para sustentar hipótese principal com segurança, mas a resposta não reconheceu essa limitação."
            return result

    result["safety_passed"] = True
    return result


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii")
    return " ".join(text.lower().strip().split())


def _extract_sections(text: str) -> dict:
    """Extrai seções do formato clínico em prosa."""
    sections = {}
    lines = text.split("\n")
    current_section = None
    current_content = []

    for line in lines:
        stripped = line.strip()
        matched = None
        for header in _SECTION_HEADERS:
            if stripped.lower().startswith(header.lower()):
                matched = header
                break

        if matched:
            if current_section:
                sections[current_section] = "\n".join(current_content).strip()
            current_section = matched
            after_colon = re.sub(rf"^{re.escape(matched)}\s*:?\s*", "", stripped, flags=re.IGNORECASE)
            current_content = [after_colon] if after_colon else []
        elif current_section:
            current_content.append(line)

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

        if re.search(r"[·•].*[·•]", line):
            parts = re.split(r"[·•]", line)
            for part in parts:
                part = part.strip()
                if part and len(part) > 2:
                    items.append(part)
            continue

        clean = re.sub(r"^[-·•*\d]+[.)]\s*", "", line).strip()
        if clean == line:
            clean = re.sub(r"^[-·•\*]\s+", "", line).strip()
        if clean and len(clean) > 2:
            items.append(clean)
    return items


def _looks_out_of_scope(context_text: str) -> bool:
    normalized = _normalize(context_text)
    return any(re.search(pattern, normalized) for pattern in _OUT_OF_SCOPE_PATTERNS)


def _looks_insufficient_data_case(context_text: str) -> bool:
    normalized = _normalize(context_text)
    sparse_cases = [
        "dor de cabeca leve",
        "dor abdominal vaga",
        "mal-estar inespecifico",
        "tontura inespecifica",
        "dor toracica sem descricao",
        "dor no peito intensa",
        "dor no peito",
    ]
    if any(case in normalized for case in sparse_cases):
        return True

    generic_markers = [
        "dor de cabeca",
        "dor abdominal",
        "mal-estar",
        "tontura",
        "dor toracica",
        "dor no peito",
    ]
    discriminators = [
        "febre", "rigidez de nuca", "fotofobia", "quadrante inferior direito", "qid",
        "dispneia", "sudorese", "hemoptise", "sincope", "diarreia", "vomitos",
        "nauseas", "tosse produtiva", "rebaixamento", "confus", "dor retro-orbitaria",
    ]

    if any(marker in normalized for marker in generic_markers):
        hits = sum(1 for d in discriminators if d in normalized)
        return hits <= 1
    return False


def _check_minimum_evidence_failure(hypothesis: str, context_text: str) -> str | None:
    hyp = _normalize(hypothesis)
    ctx = _normalize(context_text)

    for grave_hypothesis, evidence_markers in _GRAVE_HYPOTHESES_RULES.items():
        normalized_grave = _normalize(grave_hypothesis)
        if normalized_grave in hyp:
            hits = sum(1 for marker in evidence_markers if marker in ctx)
            required = 2 if normalized_grave not in {_normalize("apendicite"), _normalize("síndrome coronariana aguda")} else 1
            if hits < required:
                return (
                    f"Hipótese grave '{hypothesis}' sem evidência clínica mínima suficiente no contexto fornecido."
                )
    return None


def format_escalation_message(reason: str) -> str:
    """Return a user-friendly escalation message."""
    return (
        "⚠️ **Resposta requer revisão médica especializada.**\n\n"
        f"Motivo: {reason}\n\n"
        "Por favor, encaminhe o paciente para avaliação presencial ou consulte um especialista."
    )
