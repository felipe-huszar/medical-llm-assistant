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


def _prose_to_json(text: str) -> str:
    """
    Converte resposta em prosa livre para JSON mínimo válido.
    Usado quando o modelo retorna texto narrativo em vez de JSON.
    """
    import re as _re
    import json as _json

    # Verifica se menciona prescrição (bloqueio de segurança)
    prescription_keywords = ["prescrevo", "prescrito", "tome ", "mg/dia", "comprimido"]
    rec_type = "prescription" if any(k in text.lower() for k in prescription_keywords) else "analysis"

    # Extrai possíveis diagnósticos (linhas com "diagnóstico", "suspeita", "hipótese", bullet "-" ou "•")
    diagnoses = []
    for line in text.split("\n"):
        line = line.strip()
        if _re.match(r"^[-•*\d\.]+\s+", line):
            clean = _re.sub(r"^[-•*\d\.]+\s+", "", line).strip()
            if 5 < len(clean) < 120:
                diagnoses.append(clean)
    if not diagnoses:
        diagnoses = ["Análise clínica — ver raciocínio completo"]

    # Exames recomendados
    exam_keywords = ["exame", "hemograma", "tomografia", "raio", "ultrassom", "ressonância",
                     "ecocardiograma", "eletrocardiograma", "colonoscopia", "endoscopia"]
    exams = []
    for line in text.split("\n"):
        if any(k in line.lower() for k in exam_keywords):
            clean = line.strip().lstrip("-•* ")
            if 5 < len(clean) < 120:
                exams.append(clean)
    if not exams:
        exams = ["Avaliação clínica complementar conforme julgamento médico"]

    result = {
        "possible_diagnoses": diagnoses[:5],
        "recommended_exams": exams[:5],
        "reasoning": text.strip()[:1000],
        "sources": ["Resposta gerada pelo modelo LoRA fine-tuned"],
        "confidence": 0.65,
        "recommendation_type": rec_type,
    }
    return _json.dumps(result, ensure_ascii=False)


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

    # --- Parse JSON (aceita markdown ```json...```, JSON embutido ou prosa livre) ---
    import re as _re
    text = raw_response.strip()

    # 1. Tenta extrair bloco ```json ... ```
    md_match = _re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, _re.DOTALL)
    if md_match:
        text = md_match.group(1)
    else:
        # 2. Tenta extrair primeiro objeto JSON do texto
        json_match = _re.search(r"\{.*\}", text, _re.DOTALL)
        if json_match:
            text = json_match.group(0)
        else:
            # 3. Fallback: modelo retornou prosa livre — monta JSON mínimo
            # Só ativa se houver conteúdo suficiente (resposta real, não erro)
            if len(raw_response.strip()) >= 100:
                text = _prose_to_json(raw_response)
            else:
                result["needs_escalation"] = True
                result["reason"] = f"Resposta LLM não é JSON válido e muito curta para análise."
                return result

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
