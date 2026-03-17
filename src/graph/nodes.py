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
    """Assemble structured clinical prompt from profile + history + question."""
    profile = state.get("patient_profile", {})
    history = state.get("consultation_history", [])
    question = state.get("doctor_question", "")

    profile_text = (
        f"Paciente {profile.get('sexo', 'N/A')}, {profile.get('idade', 'N/A')} anos, "
        f"{profile.get('peso', 'N/A')} kg."
    ) if profile else "Paciente sem perfil cadastrado."

    history_text = (
        "\n---\n".join(history)
        if history
        else "Sem histórico de consultas anteriores."
    )

    # Formato alinhado com o treinamento do modelo (Lucas format)
    # system + user via apply_chat_template no model_loader
    prompt = (
        f"Contexto do paciente:\n{profile_text}\n\n"
        f"Histórico de consultas anteriores:\n{history_text}\n\n"
        f"Sintomas relatados:\n{question}"
    )

    state["prompt"] = prompt
    audit_log("node_executed", cpf=state["cpf"], node="build_prompt",
              prompt_length=len(prompt), has_history=bool(history))
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
