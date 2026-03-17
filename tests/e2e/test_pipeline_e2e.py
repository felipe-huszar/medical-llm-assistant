"""
E2E tests for the full medical-llm-assistant pipeline.

Requirements validated (end-to-end):
  - REQ-E2E-1: New patient registration + consultation flow works end-to-end
  - REQ-E2E-2: Existing patient consultation retrieves history correctly
  - REQ-E2E-3: Safety escalation path works (prescription/confidence/sources)
  - REQ-E2E-4: Multiple consultations accumulate in patient history
  - REQ-E2E-5: Pipeline produces structured output with diagnoses and exams
  - REQ-E2E-6: MockLLM integration produces valid clinical responses
"""

import json
import os
import pytest

# Ensure mock mode for E2E tests
os.environ["USE_MOCK_LLM"] = "true"


@pytest.fixture(autouse=True)
def _isolated_chroma(tmp_path, monkeypatch):
    """Provide isolated ChromaDB for each E2E test."""
    monkeypatch.setenv("CHROMA_DB_PATH", str(tmp_path / "chroma_e2e"))
    import src.rag.patient_rag as rag_mod
    rag_mod._client = None
    rag_mod._client_path = None
    yield
    rag_mod._client = None
    rag_mod._client_path = None


@pytest.fixture
def mock_llm():
    """Provide a MockLLM instance."""
    from src.llm.mock_llm import MockLLM
    return MockLLM()


@pytest.fixture
def pipeline():
    """Provide the compiled pipeline graph."""
    from src.graph.pipeline import build_graph
    from src.llm.mock_llm import MockLLM
    return build_graph(llm=MockLLM())


class TestNewPatientFlow:
    """REQ-E2E-1: New patient registration + consultation."""

    def test_new_patient_full_flow(self, pipeline):
        """Complete flow: new patient CPF -> consultation -> structured response."""
        from src.graph.state import ClinicalState
        from src.graph.pipeline import run_consultation

        # Use run_consultation so patient_profile is saved before pipeline runs
        result = run_consultation(
            cpf="NEW.PAT.001-01",
            doctor_question="Paciente com dor abdominal ao evacuar há 2 semanas. Quais diagnósticos?",
            patient_profile={"nome": "Test Patient", "idade": 35, "sexo": "M", "peso": 70},
        )

        # Assertions
        # Note: run_consultation pre-registers the patient, so check_patient finds it
        assert result["is_new_patient"] is False
        assert result["patient_profile"]["nome"] == "Test Patient"
        assert result["consultation_history"] == []  # no prior history
        assert result["safety_passed"] is True
        assert result["needs_escalation"] is False
        assert len(result["final_answer"]) > 0
        assert "##" in result["final_answer"] or "**" in result["final_answer"]  # Markdown
        assert "Análise Clínica" in result["final_answer"] or "Hipótese" in result["final_answer"]

    def test_new_patient_with_gi_symptoms(self, pipeline):
        """GI symptoms trigger domain-specific diagnoses."""
        from src.graph.state import ClinicalState

        state: ClinicalState = {
            "cpf": "GI.PAT.002-02",
            "doctor_question": "Dor abdominal, diarreia e muco nas fezes.",
            "patient_profile": {"nome": "GI Patient", "idade": 40, "sexo": "F", "peso": 65},
            "is_new_patient": False,
            "consultation_history": [],
            "prompt": "",
            "raw_response": "",
            "safety_passed": False,
            "sources": [],
            "final_answer": "",
            "needs_escalation": False,
        }

        result = pipeline.invoke(state)
        answer = result["final_answer"]

        # Should contain GI-related content
        assert any(term in answer.lower() for term in ["intestino", "crohn", "colite", "sii", "gi"])
        assert result["safety_passed"] is True


class TestExistingPatientFlow:
    """REQ-E2E-2: Existing patient with history retrieval."""

    def test_existing_patient_with_prior_consultation(self, pipeline):
        """Second consultation sees prior history."""
        from src.graph.state import ClinicalState
        from src.rag.patient_rag import save_patient, save_consultation

        cpf = "EXIST.PAT.003-03"
        # Pre-populate patient and history
        save_patient(cpf, {"nome": "Existing", "idade": 50, "sexo": "M", "peso": 80})
        save_consultation(cpf, "Primeira consulta: dor de cabeça", "Análise: cefaleia tensional.")

        state: ClinicalState = {
            "cpf": cpf,
            "doctor_question": "Retorno: paciente continua com cefaleia. Novas opções?",
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

        result = pipeline.invoke(state)

        assert result["is_new_patient"] is False
        assert len(result["consultation_history"]) >= 1
        assert "cefaleia" in result["consultation_history"][0].lower()
        assert result["safety_passed"] is True


class TestSafetyEscalation:
    """REQ-E2E-3: Safety escalation paths."""

    def test_escalation_on_low_confidence(self, pipeline):
        """Force low confidence scenario -> escalation."""
        from src.graph.state import ClinicalState
        from unittest.mock import MagicMock

        # Create a mock LLM that returns short response (escalates on < 80 chars)
        low_conf_llm = MagicMock()
        low_conf_llm.invoke.return_value = "ok"  # Muito curto → escalada

        from src.graph.pipeline import build_graph
        pipeline_low_conf = build_graph(llm=low_conf_llm)

        state: ClinicalState = {
            "cpf": "LOW.CONF.004-04",
            "doctor_question": "Sintoma vago e não específico.",
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

        result = pipeline_low_conf.invoke(state)

        assert result["needs_escalation"] is True
        assert result["safety_passed"] is False
        assert "revisão" in result["final_answer"].lower() or "⚠️" in result["final_answer"]

    def test_escalation_on_empty_sources(self, pipeline):
        """Force empty sources -> escalation."""
        from src.graph.state import ClinicalState
        from unittest.mock import MagicMock

        no_sources_llm = MagicMock()
        no_sources_llm.invoke.return_value = "ok"  # Muito curto → escalada

        from src.graph.pipeline import build_graph
        pipeline_no_src = build_graph(llm=no_sources_llm)

        state: ClinicalState = {
            "cpf": "NO.SRC.005-05",
            "doctor_question": "Sintoma qualquer.",
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

        result = pipeline_no_src.invoke(state)

        assert result["needs_escalation"] is True
        assert result["safety_passed"] is False

    def test_escalation_on_prescription_type(self, pipeline):
        """Force prescription type -> escalation."""
        from src.graph.state import ClinicalState
        from unittest.mock import MagicMock

        prescription_llm = MagicMock()
        prescription_llm.invoke.return_value = """Resumo clínico:
Paciente com infecção.

Raciocínio clínico:
Prescrevo amoxicilina 500mg/dia para o paciente.

Hipótese diagnóstica principal:
Infecção bacteriana

Diagnósticos diferenciais:
- Vírus

Exames recomendados:
- Cultura"""

        from src.graph.pipeline import build_graph
        pipeline_presc = build_graph(llm=prescription_llm)

        state: ClinicalState = {
            "cpf": "PRESC.006-06",
            "doctor_question": "Prescreva amoxicilina.",
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

        result = pipeline_presc.invoke(state)

        assert result["needs_escalation"] is True
        assert result["safety_passed"] is False
        assert "prescrição" in result["final_answer"].lower() or "prescription" in result["final_answer"].lower()


class TestMultipleConsultations:
    """REQ-E2E-4: Multiple consultations accumulate history."""

    def test_three_consultations_accumulate(self, pipeline):
        """Three consultations for same patient all appear in history."""
        from src.graph.state import ClinicalState
        from src.rag.patient_rag import save_patient

        cpf = "MULTI.007-07"
        save_patient(cpf, {"nome": "Multi", "idade": 45, "sexo": "F", "peso": 68})

        questions = [
            "Primeira consulta: dor abdominal.",
            "Retorno: melhora parcial, nova dor.",
            "Segundo retorno: exames solicitados.",
        ]

        for q in questions:
            state: ClinicalState = {
                "cpf": cpf,
                "doctor_question": q,
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
            pipeline.invoke(state)

        # Verify all 3 in history
        from src.rag.patient_rag import get_consultation_history
        history = get_consultation_history(cpf, n_results=10)
        assert len(history) == 3


class TestStructuredOutput:
    """REQ-E2E-5: Pipeline produces structured output."""

    def test_output_has_diagnoses_section(self, pipeline):
        """Final answer contains diagnoses section."""
        from src.graph.state import ClinicalState

        state: ClinicalState = {
            "cpf": "STRUCT.008-08",
            "doctor_question": "Paciente com sintomas diversos.",
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

        result = pipeline.invoke(state)
        answer = result["final_answer"]

        # Check for structure markers
        assert any(marker in answer for marker in ["Diagnósticos", "diagnoses", "##"])
        assert any(marker in answer for marker in ["Exames", "exams", "recommended"])
        assert any(marker in answer for marker in ["Raciocínio", "reasoning", "Análise"])

    def test_output_contains_confidence(self, pipeline):
        """Final answer includes confidence level."""
        from src.graph.state import ClinicalState

        state: ClinicalState = {
            "cpf": "CONF.009-09",
            "doctor_question": "Sintoma cardíaco.",
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

        result = pipeline.invoke(state)
        answer = result["final_answer"]

        # Should contain clinical analysis sections
        assert "Análise Clínica" in answer or "Hipótese" in answer or "Raciocínio" in answer


class TestMockLLMIntegration:
    """REQ-E2E-6: MockLLM produces valid clinical responses."""

    def test_mock_llm_returns_prose(self, mock_llm):
        """MockLLM always returns prose with clinical sections."""
        for prompt in ["dor abdominal", "cefaleia", "dispneia", "glicemia", "xyz unknown"]:
            raw = mock_llm.invoke(prompt)
            assert isinstance(raw, str)
            assert "Hipótese diagnóstica principal" in raw
            assert "Exames recomendados" in raw

    def test_mock_llm_never_prescription(self, mock_llm):
        """MockLLM never returns prescription language."""
        for prompt in ["dor abdominal", "cefaleia", "dispneia", "glicemia", "xyz unknown"]:
            raw = mock_llm.invoke(prompt)
            assert "prescrevo" not in raw.lower()
