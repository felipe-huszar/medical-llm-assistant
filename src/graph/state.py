"""
state.py - Shared TypedDict state for the LangGraph pipeline.
"""

from __future__ import annotations
from typing import TypedDict


class ClinicalState(TypedDict, total=False):
    cpf: str
    patient_profile: dict           # nome, idade, sexo, peso
    is_new_patient: bool
    consultation_history: list[str]
    doctor_question: str
    prompt: str
    raw_response: str
    safety_passed: bool
    sources: list[str]
    final_answer: str
    needs_escalation: bool
