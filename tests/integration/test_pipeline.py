"""
Integration tests for src/graph/pipeline.py

Requirements validated:
  - REQ-PIPE-1: build_graph returns a compiled StateGraph
  - REQ-PIPE-2: run_consultation completes all nodes for new patient
  - REQ-PIPE-3: run_consultation loads existing patient profile
  - REQ-PIPE-4: run_consultation persists consultation to history
  - REQ-PIPE-5: full pipeline produces final_answer with diagnoses and exams
"""

import json
import pytest
from unittest.mock import MagicMock

from src.graph.pipeline import build_graph, run_consultation
from src.rag.patient_rag import save_patient


@pytest.fixture(autouse=True)
def _isolated_chroma(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DB_PATH", str(tmp_path / "chroma_pipeline"))
    monkeypatch.setenv("USE_MOCK_LLM", "true")
    import src.rag.patient_rag as rag_mod
    rag_mod._client = None
    rag_mod._client_path = None
    yield
    rag_mod._client = None
    rag_mod._client_path = None


class TestBuildGraph:
    def test_build_graph_returns_callable(self):
        """REQ-PIPE-1: build_graph produces a runnable graph."""
        graph = build_graph()
        assert callable(graph) or hasattr(graph, "invoke")


class TestRunConsultationNewPatient:
    def test_new_patient_consultation(self):
        """REQ-PIPE-2: full pipeline runs for new patient with profile."""
        result = run_consultation(
            cpf="NEW.PAT.001-00",
            doctor_question="Paciente com dor abdominal há 2 semanas. Quais diagnósticos?",
            patient_profile={
                "nome": "Test Patient",
                "idade": 35,
                "sexo": "F",
                "peso": 65,
            },
        )
        assert result["final_answer"] is not None
        assert len(result["final_answer"]) > 0
        assert result["is_new_patient"] is False  # After registration

    def test_final_answer_contains_markdown(self):
        """REQ-PIPE-5: final_answer is formatted Markdown."""
        result = run_consultation(
            cpf="NEW.PAT.002-00",
            doctor_question="Dor abdominal?",
            patient_profile={"nome": "Test", "idade": 40, "sexo": "M", "peso": 80},
        )
        assert "##" in result["final_answer"] or "**" in result["final_answer"]



class TestRunConsultationExistingPatient:
    def test_existing_patient_profile_loaded(self):
        """REQ-PIPE-3: existing patient profile is loaded from ChromaDB."""
        from src.rag.patient_rag import save_patient
        cpf = "EXIST.PAT.001-00"
        save_patient(cpf, {"nome": "Existing Patient", "idade": 60, "sexo": "F", "peso": 68})

        result = run_consultation(
            cpf=cpf,
            doctor_question="Cefaleia recorrente?",
        )
        assert result["patient_profile"]["nome"] == "Existing Patient"
        assert result["patient_profile"]["idade"] == 60

    def test_consultation_history_accumulates(self):
        """REQ-PIPE-4: multiple consultations are persisted and retrievable."""
        from src.rag.patient_rag import get_consultation_history
        cpf = "HIST.PAT.001-00"
        save_patient(cpf, {"nome": "History Test", "idade": 30, "sexo": "M", "peso": 75})

        # First consultation
        run_consultation(cpf=cpf, doctor_question="Primeira consulta?")
        history1 = get_consultation_history(cpf)
        assert len(history1) == 1

        # Second consultation
        run_consultation(cpf=cpf, doctor_question="Segunda consulta?")
        history2 = get_consultation_history(cpf)
        assert len(history2) == 2

    def test_selected_history_is_used_but_unselected_history_is_not(self):
        from src.rag.patient_rag import save_consultation
        cpf = "HIST.PAT.002-00"
        save_patient(cpf, {"nome": "History Select Test", "idade": 42, "sexo": "F", "peso": 66})
        save_consultation(cpf, "Primeira consulta relevante", "Resposta anterior")
        save_consultation(cpf, "Segunda consulta irrelevante", "Resposta anterior")

        result = run_consultation(
            cpf=cpf,
            doctor_question="Nova consulta",
            selected_history=["Primeira consulta relevante"],
        )
        prompt = result["prompt"]
        assert "Primeira consulta relevante" in prompt
        assert "Segunda consulta irrelevante" not in prompt


class TestPipelineSafetyIntegration:
    def test_escalation_path_for_invalid_response(self, monkeypatch):
        """Safety gate triggers escalation for short LLM response."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = "ok"  # Muito curto → escalada

        result = run_consultation(
            cpf="SAFETY.TEST.001-00",
            doctor_question="Test?",
            patient_profile={"nome": "Safety", "idade": 40, "sexo": "M", "peso": 80},
            llm=mock_llm,
        )
        assert result["needs_escalation"] is True
        assert "⚠️" in result["final_answer"] or "revisão" in result["final_answer"].lower()

    def test_safe_path_for_valid_response(self):
        """Normal flow produces analysis response (no escalation) for sufficiently specified case."""
        result = run_consultation(
            cpf="SAFE.TEST.001-00",
            doctor_question="Paciente com cefaleia pulsátil unilateral, fotofobia, fonofobia e náuseas.",
            patient_profile={"nome": "Safe", "idade": 35, "sexo": "F", "peso": 65},
        )
        assert result["needs_escalation"] is False
        assert result["safety_passed"] is True
        assert "##" in result["final_answer"]

    def test_hallucinated_history_is_blocked_when_context_has_none(self):
        """Guardrail blocks invented history/comorbidities absent from prompt context."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = """Resumo clínico:
Paciente apresentando dor abdominal, com histórico de cirrose hepática e obesidade.

Raciocínio clínico:
Paciente com histórico de cirrose hepática e obesidade, o que representa fator de risco.

Hipótese diagnóstica principal:
apendicite aguda

Diagnósticos diferenciais:
- gastroenterite aguda

Exames recomendados:
- hemograma"""

        result = run_consultation(
            cpf="SAFE.TEST.002-00",
            doctor_question="Dor abdominal?",
            patient_profile={"nome": "Safe", "idade": 35, "sexo": "F", "peso": 65},
            llm=mock_llm,
        )
        assert result["needs_escalation"] is True
        assert result["safety_passed"] is False
        assert "histórico/comorbidades" in result["final_answer"].lower() or "revisão" in result["final_answer"].lower()
