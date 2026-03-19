"""
nodes.py - LangGraph node functions for the medical assistant pipeline.

Nodes:
  1. check_patient      → lookup CPF in ChromaDB
  2. retrieve_history   → fetch consultation history
  3. build_prompt       → assemble LLM prompt
  4. llm_reasoning      → call LLM
  5. safety_gate        → validate response
  6. save_and_format    → persist + format final answer
  7. escalation         → handle unsafe responses
"""

from __future__ import annotations

import json
import os
from typing import Any

from src.graph.state import ClinicalState
from src.audit.logger import audit_log
from src.rag.patient_rag import (
    get_patient,
    patient_exists,
    save_patient,
    get_consultation_history,
    save_consultation,
)
from src.safety.gate import validate_response, format_escalation_message
from src.llm.factory import get_llm


# ---------------------------------------------------------------------------
# Node 1: check_patient
# ---------------------------------------------------------------------------

def check_patient(state: ClinicalState) -> ClinicalState:
    """Lookup CPF; load profile if exists, otherwise mark as new."""
    cpf = state["cpf"]
    profile = get_patient(cpf)

    if profile is None:
        state["is_new_patient"] = True
        state["patient_profile"] = {}
    else:
        state["is_new_patient"] = False
        state["patient_profile"] = profile

    audit_log("node_executed", cpf=cpf, node="check_patient",
              is_new_patient=state["is_new_patient"])
    return state


# ---------------------------------------------------------------------------
# Node 2: retrieve_history
# ---------------------------------------------------------------------------

def retrieve_history(state: ClinicalState) -> ClinicalState:
    """Fetch last consultation summaries for this patient."""
    cpf = state["cpf"]
    history = get_consultation_history(cpf, n_results=5)
    state["consultation_history"] = history
    audit_log("node_executed", cpf=cpf, node="retrieve_history",
              history_count=len(history))
    return state


# ---------------------------------------------------------------------------
# Node 3: build_prompt
# ---------------------------------------------------------------------------

def build_prompt(state: ClinicalState) -> ClinicalState:
    """Assemble structured clinical prompt from profile + history + question.

    Alinhado com o formato de treinamento do Lucas (dataset sintético):

        Contexto do paciente:
        Paciente <sexo>, <idade> anos.
        Histórico: <comorbidades ou queixas anteriores resumidas>

        Sintomas relatados:
        <queixa atual>

    O campo "Histórico" no treinamento continha comorbidades (ex: "hipertensão, diabetes"),
    NÃO respostas completas de consultas anteriores. Por isso injetamos apenas as
    queixas passadas (1 linha cada), não as respostas do LLM.
    """
    profile = state.get("patient_profile", {})
    history = state.get("consultation_history", [])
    question = state.get("doctor_question", "")

    sexo  = profile.get("sexo", "N/A")
    idade = profile.get("idade", "N/A")
    peso  = profile.get("peso", "")

    peso_text = f", {peso} kg" if peso else ""
    profile_line = f"Paciente {sexo}, {idade} anos{peso_text}."

    # Prioridade 1: comorbidades registradas no perfil (condições crônicas permanentes)
    # Alinhado com o treinamento: "Histórico: hipertensão, diabetes"
    comorbidades = profile.get("comorbidades", [])
    if isinstance(comorbidades, list):
        comorbidades_text = ", ".join(comorbidades) if comorbidades else ""
    else:
        comorbidades_text = str(comorbidades).strip()

    # Prioridade 2 (fallback): queixas anteriores do ChromaDB se não há comorbidades
    if not comorbidades_text and history:
        queixas = []
        for entry in history:
            for line in entry.split("\n"):
                if line.startswith("Pergunta:"):
                    q = line.replace("Pergunta:", "").strip()
                    if q:
                        queixas.append(q)
                    break
        comorbidades_text = "; ".join(queixas)

    # Monta contexto no formato exato do treinamento, mas explicitando ausência de histórico
    if comorbidades_text:
        history_line = f"Histórico: {comorbidades_text}"
    else:
        history_line = "Histórico: não informado. Comorbidades registradas: nenhuma."

    guardrail_block = (
        "Regras críticas:\n"
        "- Use apenas informações explicitamente fornecidas.\n"
        "- Não invente histórico, comorbidades ou fatores de risco prévios.\n"
        "- Se não houver histórico, escreva literalmente: 'Histórico relevante não informado'."
    )

    context_block = (
        f"Contexto do paciente:\n"
        f"{profile_line}\n"
        f"{history_line}"
    )

    prompt = f"{context_block}\n\n{guardrail_block}\n\nSintomas relatados:\n{question}"

    state["prompt"] = prompt
    state["has_explicit_history"] = bool(comorbidades_text)
    audit_log("node_executed", cpf=state["cpf"], node="build_prompt",
              prompt_length=len(prompt), has_history=bool(comorbidades_text))
    return state


# ---------------------------------------------------------------------------
# Node 4: llm_reasoning
# ---------------------------------------------------------------------------

def llm_reasoning(state: ClinicalState, llm: Any = None) -> ClinicalState:
    """Call LLM with the assembled prompt."""
    if llm is None:
        # Lazy import to allow factory to be set at runtime
        from src.llm.factory import get_llm
        llm = get_llm()

    prompt = state.get("prompt", "")
    raw = llm.invoke(prompt)
    state["raw_response"] = raw
    # Loga prompt enviado e primeiros 300 chars da resposta
    audit_log("node_executed", cpf=state["cpf"], node="llm_reasoning",
              response_length=len(raw), llm_type=type(llm).__name__,
              prompt_sent=prompt[:500],  # LOG DO PROMPT ENVIADO
              raw_preview=raw[:300] if raw else "")
    return state


# ---------------------------------------------------------------------------
# Node 5: safety_gate
# ---------------------------------------------------------------------------

def safety_gate(state: ClinicalState) -> ClinicalState:
    """Validate LLM response against safety rules (prose format)."""
    raw = state.get("raw_response", "")
    validation = validate_response(raw)

    state["safety_passed"] = validation["safety_passed"]
    state["needs_escalation"] = validation["needs_escalation"]
    state["sources"] = []
    state["parsed_response"] = validation.get("sections", {})

    # Guardrail adicional: se não houve histórico/comorbidades no contexto,
    # o modelo não pode afirmar histórico específico na resposta.
    has_explicit_history = state.get("has_explicit_history", False)
    if not validation["needs_escalation"] and not has_explicit_history:
        sections = validation.get("sections", {})
        summary_and_reasoning = "\n".join([
            sections.get("Resumo clínico", ""),
            sections.get("Raciocínio clínico", ""),
        ]).lower()

        # Permite explicitar ausência de histórico/comorbidades.
        allowed_absence_markers = [
            "histórico relevante não informado",
            "histórico não informado",
            "sem histórico relevante",
            "não há histórico",
            "comorbidades registradas: nenhuma",
            "comorbidades conhecidas como nenhuma",
            "sem comorbidades",
            "nenhuma comorbidade",
        ]

        # Bloqueia apenas afirmação positiva de histórico específico ausente do contexto.
        suspicious_markers = [
            "com histórico de ",
            "histórico de ",
            "histórico relevante:",
            "paciente com histórico de ",
        ]

        has_allowed_absence = any(marker in summary_and_reasoning for marker in allowed_absence_markers)
        has_positive_history_claim = any(marker in summary_and_reasoning for marker in suspicious_markers)

        if has_positive_history_claim and not has_allowed_absence:
            validation["needs_escalation"] = True
            validation["safety_passed"] = False
            validation["reason"] = (
                "Resposta inferiu histórico/comorbidades não fornecidos no contexto do paciente."
            )
            state["safety_passed"] = False
            state["needs_escalation"] = True

    if validation["needs_escalation"]:
        state["final_answer"] = format_escalation_message(validation["reason"])
        audit_log("safety_triggered", cpf=state["cpf"], node="safety_gate",
                  reason=validation["reason"], action="escalation")
    else:
        sections = validation.get("sections", {})
        audit_log("node_executed", cpf=state["cpf"], node="safety_gate",
                  safety_passed=True, sections_found=list(sections.keys()))

    return state


# ---------------------------------------------------------------------------
# Node 6: save_and_format
# ---------------------------------------------------------------------------

def save_and_format(state: ClinicalState) -> ClinicalState:
    """Persist consultation to ChromaDB and format the final answer (prose format)."""
    from src.safety.gate import _extract_list_items

    cpf = state["cpf"]
    question = state.get("doctor_question", "")
    raw = state.get("raw_response", "")
    sections = state.get("parsed_response") or {}

    # Extrai seções da prosa
    resumo      = sections.get("Resumo clínico", "").strip()
    raciocinio  = sections.get("Raciocínio clínico", "").strip()
    hipotese    = sections.get("Hipótese diagnóstica principal", "").strip()
    diferenciais_raw = sections.get("Diagnósticos diferenciais", "")
    exames_raw  = sections.get("Exames recomendados", "")

    diferenciais = _extract_list_items(diferenciais_raw)
    exames       = _extract_list_items(exames_raw)

    # --- Monta markdown rico para o Gradio ---
    def _bullet_list(items):
        return "\n".join(f"  • {i}" for i in items) if items else "  • N/A"

    parts = ["## 🩺 Análise Clínica\n"]

    if resumo:
        parts.append(f"### 📋 Resumo Clínico\n{resumo}\n")

    if hipotese:
        parts.append(f"### 🎯 Hipótese Diagnóstica Principal\n{hipotese}\n")

    if diferenciais:
        parts.append(f"### 🔍 Diagnósticos Diferenciais\n{_bullet_list(diferenciais)}\n")

    if exames:
        parts.append(f"### 🧪 Exames Recomendados\n{_bullet_list(exames)}\n")

    if raciocinio:
        parts.append(f"### 💭 Raciocínio Clínico\n{raciocinio}\n")

    parts.append("---\n> ⚕️ *Esta análise é apenas orientativa. A decisão clínica final é responsabilidade do médico assistente.*")

    answer = "\n".join(parts)
    state["final_answer"] = answer

    audit_log("consultation_saved", cpf=cpf, node="save_and_format",
              hipotese=hipotese, diferenciais_count=len(diferenciais),
              exames_count=len(exames), sections_found=list(sections.keys()))

    # Salva prosa no ChromaDB (contexto para próximas consultas)
    save_consultation(
        cpf=cpf,
        question=question,
        answer=raw,  # salva resposta bruta para contexto de RAG
        metadata={
            "hipotese": hipotese,
            "exames": json.dumps(exames),
            "diferenciais": json.dumps(diferenciais),
        },
    )

    return state


# ---------------------------------------------------------------------------
# Node 7: escalation
# ---------------------------------------------------------------------------

def escalation(state: ClinicalState) -> ClinicalState:
    """Handle escalation path — message already set by safety_gate."""
    # final_answer already populated by safety_gate with escalation message
    return state
