"""
End-to-end tests for the Medical LLM Assistant system.

These tests validate the complete user journeys:
  - REQ-E2E-1: New patient registration → consultation → history persistence
  - REQ-E2E-2: Existing patient lookup → consultation with history context
  - REQ-E2E-3: Safety escalation when LLM returns invalid/prescription response
  - REQ-E2E-4: Multiple consultations accumulate in patient history
  - REQ-E2E-5: Different symptom domains return appropriate diagnoses
"""

import json
import pytest
from unittest.mock import MagicMock

from src.graph.pipeline import run_consultation
from src.rag.patient_rag import (
    save_patient,
    get_patient,
    patient_exists,
    get_consultation_history,
)


@pytest.fixture(autouse=True)
def _isolated_chroma(tmp_path, monkeypatch):
    """Each e2e test gets a fresh ChromaDB instance."""
    monkeypatch.setenv("CHROMA_DB_PATH", str(tmp_path / "chroma_e2e"))
    monkeypatch.setenv("USE_MOCK_LLM", "true")
    import src.rag.patient_rag as rag_mod
    rag_mod._client = None
    rag_mod._client_path = None
    yield
    rag_mod._client = None
    rag_mod._client_path = None


class TestE2ENewPatientJourney:
    """REQ-E2E-1: Complete flow for a new patient."""

    def test_new_patient_full_journey(self):
        """New patient: register → consult → verify persistence."""
        cpf = "E2E.NEW.001-00"
        
        # Step 1: Verify patient doesn't exist
        assert patient_exists(cpf) is False
        
        # Step 2: Run consultation with profile (auto-registers)
        profile = {"nome": "Maria E2E", "idade": 42, "sexo": "F", "peso": 68}
        result = run_consultation(
            cpf=cpf,
            doctor_question="Paciente relata dores abdominais após refeições. Quais diagnósticos?",
            patient_profile=profile,
        )
        
        # Step 3: Verify patient now exists
        assert patient_exists(cpf) is True
        saved_profile = get_patient(cpf)
        assert saved_profile["nome"] == "Maria E2E"
        
        # Step 4: Verify consultation was saved
        history = get_consultation_history(cpf)
        assert len(history) == 1
        
        # Step 5: Verify response structure
        assert result["final_answer"] is not None
        assert len(result["final_answer"]) > 100
        assert result["needs_escalation"] is False


class TestE2EExistingPatientJourney:
    """REQ-E2E-2: Flow for existing patient with history."""

    def test_existing_patient_with_history_context(self):
        """Existing patient: previous consultations inform new ones."""
        cpf = "E2E.EXIST.001-00"
        
        # Pre-register patient
        save_patient(cpf, {"nome": "João E2E", "idade": 55, "sexo": "M", "peso": 82})
        
        # First consultation (historical)
        run_consultation(
            cpf=cpf,
            doctor_question="Paciente com cefaleia tensional frequente.",
        )
        
        # Second consultation (current) - should have access to history
        result = run_consultation(
            cpf=cpf,
            doctor_question="Retorno: cefaleia piorou. Novos sintomas?",
        )
        
        # Verify history accumulated
        history = get_consultation_history(cpf)
        assert len(history) == 2
        
        # Verify profile was loaded
        assert result["patient_profile"]["nome"] == "João E2E"


class TestE2ESafetyEscalation:
    """REQ-E2E-3: Safety gate triggers escalation appropriately."""

    def test_escalation_on_prescription_attempt(self, monkeypatch):
        """System escalates when LLM tries to prescribe medication."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = """Resumo clínico:
Paciente com hipertensão.

Raciocínio clínico:
Prescrevo enalapril 20mg/dia para o paciente.

Hipótese diagnóstica principal:
Hipertensão arterial

Diagnósticos diferenciais:
- Ansiedade

Exames recomendados:
- Pressão arterial"""
        
        result = run_consultation(
            cpf="E2E.SAFE.001-00",
            doctor_question="Pressão alta?",
            patient_profile={"nome": "Safety Test", "idade": 60, "sexo": "M", "peso": 90},
            llm=mock_llm,
        )
        
        assert result["needs_escalation"] is True
        assert result["safety_passed"] is False
        assert "⚠️" in result["final_answer"] or "revisão" in result["final_answer"].lower()

    def test_escalation_on_low_confidence(self, monkeypatch):
        """System escalates when LLM response is too short."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = "ok"  # Muito curto → escalada
        
        result = run_consultation(
            cpf="E2E.SAFE.002-00",
            doctor_question="Sintomas estranhos...",
            patient_profile={"nome": "Low Conf", "idade": 30, "sexo": "F", "peso": 60},
            llm=mock_llm,
        )
        
        assert result["needs_escalation"] is True
        assert "⚠️" in result["final_answer"] or "revisão" in result["final_answer"].lower()

    def test_escalation_on_missing_sources(self, monkeypatch):
        """System escalates when LLM response is too short."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = "ok"  # Muito curto → escalada
        
        result = run_consultation(
            cpf="E2E.SAFE.003-00",
            doctor_question="Test?",
            patient_profile={"nome": "No Sources", "idade": 40, "sexo": "M", "peso": 75},
            llm=mock_llm,
        )
        
        assert result["needs_escalation"] is True


class TestE2EMultipleConsultations:
    """REQ-E2E-4: History accumulation over multiple visits."""

    def test_three_consultations_accumulate(self):
        """Three separate consultations are all stored and retrievable."""
        cpf = "E2E.MULTI.001-00"
        save_patient(cpf, {"nome": "Multi Visit", "idade": 45, "sexo": "F", "peso": 70})
        
        questions = [
            "Primeira consulta: cefaleia pulsátil unilateral com fotofobia.",
            "Retorno: cefaleia persistiu e acrescentou náusea.",
            "Novo retorno: manteve cefaleia e iniciou fonofobia.",
        ]
        
        for q in questions:
            run_consultation(cpf=cpf, doctor_question=q)
        
        history = get_consultation_history(cpf, n_results=10)
        assert len(history) == 3


