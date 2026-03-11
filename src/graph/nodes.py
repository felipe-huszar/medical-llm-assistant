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
        f"Nome: {profile.get('nome', 'N/A')}\n"
        f"Idade: {profile.get('idade', 'N/A')} anos\n"
        f"Sexo: {profile.get('sexo', 'N/A')}\n"
        f"Peso: {profile.get('peso', 'N/A')} kg"
    ) if profile else "Paciente sem perfil cadastrado."

    history_text = (
        "\n\n".join(history)
        if history
        else "Sem histórico de consultas anteriores."
    )

    prompt = f"""Você é um assistente médico especializado. Analise o caso clínico abaixo e retorne APENAS um JSON válido.

## Perfil do Paciente
{profile_text}

## Histórico de Consultas
{history_text}

## Pergunta do Médico
{question}

## Instrução
Responda SOMENTE com um JSON no formato abaixo (sem texto extra):
{{
  "possible_diagnoses": ["<diagnóstico 1>", "<diagnóstico 2>"],
  "recommended_exams": ["<exame 1>", "<exame 2>"],
  "reasoning": "<raciocínio clínico detalhado>",
  "sources": ["<fonte 1>", "<fonte 2>"],
  "confidence": <0.0 a 1.0>,
  "recommendation_type": "analysis"
}}

IMPORTANTE: Nunca prescreva medicamentos diretamente. Apenas análise e recomendação de exames."""

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
    audit_log("node_executed", cpf=state["cpf"], node="llm_reasoning",
              response_length=len(raw), llm_type=type(llm).__name__)
    return state


# ---------------------------------------------------------------------------
# Node 5: safety_gate
# ---------------------------------------------------------------------------

def safety_gate(state: ClinicalState) -> ClinicalState:
    """Validate LLM response against safety rules."""
    raw = state.get("raw_response", "")
    validation = validate_response(raw)

    state["safety_passed"] = validation["safety_passed"]
    state["needs_escalation"] = validation["needs_escalation"]
    state["sources"] = validation["sources"]

    if validation["needs_escalation"]:
        state["final_answer"] = format_escalation_message(validation["reason"])
        audit_log("safety_triggered", cpf=state["cpf"], node="safety_gate",
                  reason=validation["reason"], action="escalation")
    else:
        audit_log("node_executed", cpf=state["cpf"], node="safety_gate",
                  safety_passed=True, sources_count=len(validation["sources"]))

    return state


# ---------------------------------------------------------------------------
# Node 6: save_and_format
# ---------------------------------------------------------------------------

def save_and_format(state: ClinicalState) -> ClinicalState:
    """Persist consultation to ChromaDB and format the final answer."""
    cpf = state["cpf"]
    question = state.get("doctor_question", "")
    raw = state.get("raw_response", "")

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {}

    diagnoses = parsed.get("possible_diagnoses") or []
    exams = parsed.get("recommended_exams") or []
    reasoning = parsed.get("reasoning") or ""
    sources = parsed.get("sources") or []
    confidence = parsed.get("confidence") or 0.0

    # Format human-readable answer
    diag_text = "\n".join(f"  • {d}" for d in diagnoses) if diagnoses else "  • N/A"
    exam_text = "\n".join(f"  • {e}" for e in exams) if exams else "  • N/A"
    src_text = ", ".join(sources) if sources else "N/A"

    answer = (
        f"## Análise Clínica\n\n"
        f"**Possíveis Diagnósticos:**\n{diag_text}\n\n"
        f"**Exames Recomendados:**\n{exam_text}\n\n"
        f"**Raciocínio Clínico:**\n{reasoning}\n\n"
        f"**Fontes:** {src_text}\n"
        f"**Confiança:** {confidence:.0%}\n\n"
        f"⚕️ *Esta análise é apenas orientativa. A decisão clínica é responsabilidade do médico.*"
    )

    state["final_answer"] = answer

    audit_log("consultation_saved", cpf=cpf, node="save_and_format",
              diagnoses_count=len(diagnoses), exams_count=len(exams),
              confidence=confidence, sources=sources)

    # Persist to ChromaDB
    save_consultation(
        cpf=cpf,
        question=question,
        answer=answer,
        metadata={
            "diagnoses": json.dumps(diagnoses),
            "exams": json.dumps(exams),
            "confidence": str(confidence),
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
