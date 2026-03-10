"""
pipeline.py - LangGraph StateGraph for the medical assistant.

Flow:
  check_patient → retrieve_history → build_prompt → llm_reasoning
  → safety_gate → (safe: save_and_format | escalation: escalation)
"""

from __future__ import annotations

from functools import partial
from typing import Any, Literal

from langgraph.graph import StateGraph, END

from src.graph.state import ClinicalState
from src.graph.nodes import (
    check_patient,
    retrieve_history,
    build_prompt,
    llm_reasoning,
    safety_gate,
    save_and_format,
    escalation,
)


def _route_after_safety(state: ClinicalState) -> Literal["save_and_format", "escalation"]:
    """Conditional edge: route based on safety check result."""
    if state.get("needs_escalation", False):
        return "escalation"
    return "save_and_format"


def build_graph(llm: Any = None) -> StateGraph:
    """Compile and return the LangGraph StateGraph."""
    # Bind LLM to the llm_reasoning node
    bound_llm_reasoning = partial(llm_reasoning, llm=llm)

    graph = StateGraph(ClinicalState)

    # Add nodes
    graph.add_node("check_patient", check_patient)
    graph.add_node("retrieve_history", retrieve_history)
    graph.add_node("build_prompt", build_prompt)
    graph.add_node("llm_reasoning", bound_llm_reasoning)
    graph.add_node("safety_gate", safety_gate)
    graph.add_node("save_and_format", save_and_format)
    graph.add_node("escalation", escalation)

    # Linear edges
    graph.set_entry_point("check_patient")
    graph.add_edge("check_patient", "retrieve_history")
    graph.add_edge("retrieve_history", "build_prompt")
    graph.add_edge("build_prompt", "llm_reasoning")
    graph.add_edge("llm_reasoning", "safety_gate")

    # Conditional edge after safety gate
    graph.add_conditional_edges(
        "safety_gate",
        _route_after_safety,
        {
            "save_and_format": "save_and_format",
            "escalation": "escalation",
        },
    )

    graph.add_edge("save_and_format", END)
    graph.add_edge("escalation", END)

    return graph.compile()


def run_consultation(
    cpf: str,
    doctor_question: str,
    llm: Any = None,
    patient_profile: dict | None = None,
) -> ClinicalState:
    """
    Run the full consultation pipeline.

    Args:
        cpf: Patient CPF string.
        doctor_question: Clinical question from the doctor.
        llm: LLM instance (MockLLM or real). If None, factory is used.
        patient_profile: Optional profile to auto-register new patients.

    Returns:
        Final ClinicalState with 'final_answer'.
    """
    from src.rag.patient_rag import save_patient, patient_exists

    # Validate CPF
    if not cpf or not cpf.strip():
        return {
            "cpf": cpf,
            "doctor_question": doctor_question,
            "patient_profile": {},
            "is_new_patient": False,
            "consultation_history": [],
            "prompt": "",
            "raw_response": "",
            "safety_passed": False,
            "sources": [],
            "final_answer": "⚠️ CPF inválido ou vazio. Informe um CPF válido.",
            "needs_escalation": True,
        }

    # Pre-register patient if profile provided and not yet in DB
    if patient_profile and not patient_exists(cpf):
        save_patient(cpf, patient_profile)

    pipeline = build_graph(llm=llm)

    initial_state: ClinicalState = {
        "cpf": cpf,
        "doctor_question": doctor_question,
        "patient_profile": {},
        "is_new_patient": False,
        "consultation_history": [],
        "prompt": "",
        "raw_response": "",
        "safety_passed": False,
        "sources": [],
        "final_answer": "",
        "needs_escalation": False,
    }

    final_state = pipeline.invoke(initial_state)
    return final_state
