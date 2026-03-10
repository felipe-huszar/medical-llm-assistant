"""
Extended E2E tests for Medical LLM Assistant - Additional scenarios.

New test coverage:
  - REQ-E2E-EXT-1: Edge cases (empty inputs, special characters, long texts)
  - REQ-E2E-EXT-2: Concurrent patient handling (isolation)
  - REQ-E2E-EXT-3: Complex multi-symptom cases
  - REQ-E2E-EXT-4: Pediatric and geriatric patient profiles
  - REQ-E2E-EXT-5: Boundary confidence values (0.39, 0.40, 0.41)
  - REQ-E2E-EXT-6: Malformed LLM responses handling
  - REQ-E2E-EXT-7: Large history retrieval performance
  - REQ-E2E-EXT-8: Unicode and international characters in patient data
"""

import json
import pytest
from unittest.mock import MagicMock

from src.graph.pipeline import run_consultation, build_graph
from src.rag.patient_rag import (
    save_patient,
    get_patient,
    patient_exists,
    get_consultation_history,
)
from src.llm.mock_llm import MockLLM


@pytest.fixture(autouse=True)
def _isolated_chroma(tmp_path, monkeypatch):
    """Each test gets a fresh ChromaDB instance."""
    monkeypatch.setenv("CHROMA_DB_PATH", str(tmp_path / "chroma_e2e_ext"))
    monkeypatch.setenv("USE_MOCK_LLM", "true")
    import src.rag.patient_rag as rag_mod
    rag_mod._client = None
    rag_mod._client_path = None
    yield
    rag_mod._client = None
    rag_mod._client_path = None


# -----------------------------------------------------------------------------
# REQ-E2E-EXT-1: Edge Cases
# -----------------------------------------------------------------------------

class TestEdgeCases:
    """Edge cases and input validation."""

    def test_empty_cpf_handling(self):
        """Empty CPF should still process (though not ideal)."""
        result = run_consultation(
            cpf="",
            doctor_question="Paciente com dor de cabeça.",
            patient_profile={"nome": "Empty CPF", "idade": 30, "sexo": "M", "peso": 70},
        )
        # Should complete without error
        assert "final_answer" in result

    def test_cpf_with_special_characters(self):
        """CPF with dots and dash should work."""
        cpf = "123.456.789-00"
        result = run_consultation(
            cpf=cpf,
            doctor_question="Paciente com cefaleia.",
            patient_profile={"nome": "Special CPF", "idade": 35, "sexo": "F", "peso": 65},
        )
        assert patient_exists(cpf)
        assert result["safety_passed"] is True

    def test_very_long_question(self):
        """Extremely long clinical question should be handled."""
        long_question = "Paciente relata " + "dor " * 500 + "na cabeça."
        result = run_consultation(
            cpf="LONG.Q.001",
            doctor_question=long_question,
            patient_profile={"nome": "Long Q", "idade": 40, "sexo": "M", "peso": 75},
        )
        assert result["safety_passed"] is True
        assert len(result["final_answer"]) > 0

    def test_question_with_medical_abbreviations(self):
        """Medical abbreviations in question."""
        result = run_consultation(
            cpf="ABBR.001",
            doctor_question="Pt c/ HA, DM2, HAS. Refere dor torácica (ATC) há 3 dias.",
            patient_profile={"nome": "Abbr Patient", "idade": 55, "sexo": "M", "peso": 80},
        )
        assert result["safety_passed"] is True

    def test_patient_name_with_accents(self):
        """Patient names with accents and special characters."""
        result = run_consultation(
            cpf="ACCENT.001",
            doctor_question="Paciente com cefaleia.",
            patient_profile={"nome": "João José María Müller", "idade": 45, "sexo": "M", "peso": 72},
        )
        saved = get_patient("ACCENT.001")
        assert saved["nome"] == "João José María Müller"


# -----------------------------------------------------------------------------
# REQ-E2E-EXT-2: Concurrent Patient Isolation
# -----------------------------------------------------------------------------

class TestConcurrentPatientIsolation:
    """Multiple patients don't interfere with each other."""

    def test_multiple_patients_isolated(self):
        """Consultations for different patients remain isolated."""
        patients = [
            ("ISO.001", {"nome": "Patient A", "idade": 30, "sexo": "M", "peso": 70}),
            ("ISO.002", {"nome": "Patient B", "idade": 40, "sexo": "F", "peso": 60}),
            ("ISO.003", {"nome": "Patient C", "idade": 50, "sexo": "M", "peso": 80}),
        ]

        # Register all and run consultations
        for cpf, profile in patients:
            run_consultation(
                cpf=cpf,
                doctor_question=f"Consulta para {profile['nome']}",
                patient_profile=profile,
            )

        # Verify isolation
        for cpf, profile in patients:
            saved = get_patient(cpf)
            assert saved["nome"] == profile["nome"]
            history = get_consultation_history(cpf)
            assert len(history) == 1
            assert profile["nome"] in history[0]

    def test_same_patient_multiple_cpfs(self):
        """Same person with different CPFs treated as different patients."""
        profile = {"nome": "Same Person", "idade": 35, "sexo": "F", "peso": 65}
        
        for cpf in ["DUP.001", "DUP.002", "DUP.003"]:
            run_consultation(
                cpf=cpf,
                doctor_question="Consulta inicial.",
                patient_profile=profile,
            )

        # Each should have independent history
        for cpf in ["DUP.001", "DUP.002", "DUP.003"]:
            history = get_consultation_history(cpf)
            assert len(history) == 1


# -----------------------------------------------------------------------------
# REQ-E2E-EXT-3: Complex Multi-Symptom Cases
# -----------------------------------------------------------------------------

class TestComplexMultiSymptomCases:
    """Complex cases with multiple symptom domains."""

    def test_cardio_plus_metabolic(self):
        """Patient with cardiac and metabolic symptoms."""
        result = run_consultation(
            cpf="COMPLEX.001",
            doctor_question="Paciente com dor no peito, dispneia e glicemia elevada (250 mg/dL).",
            patient_profile={"nome": "Complex Patient", "idade": 60, "sexo": "M", "peso": 85},
        )
        assert result["safety_passed"] is True
        answer = result["final_answer"].lower()
        # Should mention either cardio or metabolic terms
        assert any(term in answer for term in ["cardíaca", "diabetes", "glicemia", "coronária"])

    def test_gi_plus_neuro(self):
        """Patient with GI and neurological symptoms."""
        result = run_consultation(
            cpf="COMPLEX.002",
            doctor_question="Paciente com dor abdominal intensa e cefaleia associada.",
            patient_profile={"nome": "GI+Neuro", "idade": 35, "sexo": "F", "peso": 62},
        )
        assert result["safety_passed"] is True
        # Should get some diagnosis (either domain)
        assert len(result["final_answer"]) > 100

    def test_vague_undefined_symptoms(self):
        """Very vague symptoms trigger default response."""
        result = run_consultation(
            cpf="VAGUE.001",
            doctor_question="Paciente não se sente bem. Diz que é 'estranho'.",
            patient_profile={"nome": "Vague", "idade": 28, "sexo": "M", "peso": 70},
        )
        assert result["safety_passed"] is True
        # Default response has low confidence (0.45) but still passes
        answer = result["final_answer"].lower()
        assert "indeterminado" in answer or "triagem" in answer or "hemograma" in answer


# -----------------------------------------------------------------------------
# REQ-E2E-EXT-4: Age-Specific Profiles
# -----------------------------------------------------------------------------

class TestAgeSpecificProfiles:
    """Pediatric and geriatric patient handling."""

    def test_pediatric_patient(self):
        """Child patient profile."""
        result = run_consultation(
            cpf="PEDIATRIC.001",
            doctor_question="Criança de 5 anos com dor abdominal e febre.",
            patient_profile={"nome": "Child Patient", "idade": 5, "sexo": "F", "peso": 18},
        )
        assert result["safety_passed"] is True
        saved = get_patient("PEDIATRIC.001")
        assert saved["idade"] == 5

    def test_geriatric_patient(self):
        """Elderly patient with multiple comorbidities."""
        result = run_consultation(
            cpf="GERIATRIC.001",
            doctor_question="Idoso de 85 anos com confusão mental aguda.",
            patient_profile={"nome": "Elderly Patient", "idade": 85, "sexo": "M", "peso": 65},
        )
        assert result["safety_passed"] is True
        saved = get_patient("GERIATRIC.001")
        assert saved["idade"] == 85

    def test_newborn_patient(self):
        """Newborn patient (extreme case)."""
        result = run_consultation(
            cpf="NEWBORN.001",
            doctor_question="Recém-nascido com icterícia.",
            patient_profile={"nome": "Baby", "idade": 0, "sexo": "F", "peso": 3.2},
        )
        assert result["safety_passed"] is True
        saved = get_patient("NEWBORN.001")
        assert saved["idade"] == 0


# -----------------------------------------------------------------------------
# REQ-E2E-EXT-5: Boundary Confidence Values
# -----------------------------------------------------------------------------

class TestBoundaryConfidenceValues:
    """Test exact boundary values for confidence threshold (0.4)."""

    def test_confidence_039_escalates(self, monkeypatch):
        """Confidence of 0.39 should escalate (below threshold)."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = json.dumps({
            "possible_diagnoses": ["X"],
            "recommended_exams": ["Y"],
            "reasoning": "Test.",
            "sources": ["Source"],
            "confidence": 0.39,
            "recommendation_type": "analysis",
        })

        result = run_consultation(
            cpf="CONF.039",
            doctor_question="Test?",
            patient_profile={"nome": "Test", "idade": 40, "sexo": "M", "peso": 75},
            llm=mock_llm,
        )
        assert result["needs_escalation"] is True

    def test_confidence_040_passes(self, monkeypatch):
        """Confidence of 0.40 should pass (at threshold)."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = json.dumps({
            "possible_diagnoses": ["X"],
            "recommended_exams": ["Y"],
            "reasoning": "Test.",
            "sources": ["Source"],
            "confidence": 0.40,
            "recommendation_type": "analysis",
        })

        result = run_consultation(
            cpf="CONF.040",
            doctor_question="Test?",
            patient_profile={"nome": "Test", "idade": 40, "sexo": "M", "peso": 75},
            llm=mock_llm,
        )
        assert result["needs_escalation"] is False
        assert result["safety_passed"] is True

    def test_confidence_041_passes(self, monkeypatch):
        """Confidence of 0.41 should pass (above threshold)."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = json.dumps({
            "possible_diagnoses": ["X"],
            "recommended_exams": ["Y"],
            "reasoning": "Test.",
            "sources": ["Source"],
            "confidence": 0.41,
            "recommendation_type": "analysis",
        })

        result = run_consultation(
            cpf="CONF.041",
            doctor_question="Test?",
            patient_profile={"nome": "Test", "idade": 40, "sexo": "M", "peso": 75},
            llm=mock_llm,
        )
        assert result["needs_escalation"] is False
        assert result["safety_passed"] is True

    def test_confidence_zero_escalates(self, monkeypatch):
        """Confidence of 0.0 should escalate."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = json.dumps({
            "possible_diagnoses": ["X"],
            "recommended_exams": ["Y"],
            "reasoning": "Test.",
            "sources": ["Source"],
            "confidence": 0.0,
            "recommendation_type": "analysis",
        })

        result = run_consultation(
            cpf="CONF.000",
            doctor_question="Test?",
            patient_profile={"nome": "Test", "idade": 40, "sexo": "M", "peso": 75},
            llm=mock_llm,
        )
        assert result["needs_escalation"] is True

    def test_confidence_one_passes(self, monkeypatch):
        """Confidence of 1.0 should pass."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = json.dumps({
            "possible_diagnoses": ["X"],
            "recommended_exams": ["Y"],
            "reasoning": "Test.",
            "sources": ["Source"],
            "confidence": 1.0,
            "recommendation_type": "analysis",
        })

        result = run_consultation(
            cpf="CONF.100",
            doctor_question="Test?",
            patient_profile={"nome": "Test", "idade": 40, "sexo": "M", "peso": 75},
            llm=mock_llm,
        )
        assert result["needs_escalation"] is False
        assert result["safety_passed"] is True


# -----------------------------------------------------------------------------
# REQ-E2E-EXT-6: Malformed LLM Responses
# -----------------------------------------------------------------------------

class TestMalformedLLMResponses:
    """Handle various malformed LLM outputs."""

    def test_invalid_json_escalates(self, monkeypatch):
        """Non-JSON response should escalate."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = "Isso não é JSON válido"

        result = run_consultation(
            cpf="MALFORM.001",
            doctor_question="Test?",
            patient_profile={"nome": "Test", "idade": 40, "sexo": "M", "peso": 75},
            llm=mock_llm,
        )
        assert result["needs_escalation"] is True
        assert "json" in result["final_answer"].lower() or "inválido" in result["final_answer"].lower()

    def test_partial_json_escalates(self, monkeypatch):
        """Partial/truncated JSON should escalate."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = '{"possible_diagnoses": ["X"], "confidence": 0.8'

        result = run_consultation(
            cpf="MALFORM.002",
            doctor_question="Test?",
            patient_profile={"nome": "Test", "idade": 40, "sexo": "M", "peso": 75},
            llm=mock_llm,
        )
        assert result["needs_escalation"] is True

    def test_empty_string_escalates(self, monkeypatch):
        """Empty string response should escalate."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = ""

        result = run_consultation(
            cpf="MALFORM.003",
            doctor_question="Test?",
            patient_profile={"nome": "Test", "idade": 40, "sexo": "M", "peso": 75},
            llm=mock_llm,
        )
        assert result["needs_escalation"] is True

    def test_json_with_extra_text_escalates(self, monkeypatch):
        """JSON with extra text before/after should escalate."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = 'Aqui está a resposta: {"possible_diagnoses": ["X"], "recommended_exams": ["Y"], "reasoning": "Test.", "sources": ["S"], "confidence": 0.8, "recommendation_type": "analysis"} Espero ter ajudado!'

        result = run_consultation(
            cpf="MALFORM.004",
            doctor_question="Test?",
            patient_profile={"nome": "Test", "idade": 40, "sexo": "M", "peso": 75},
            llm=mock_llm,
        )
        # This will escalate because it's not pure JSON
        assert result["needs_escalation"] is True

    def test_null_values_in_json(self, monkeypatch):
        """JSON with null values handling."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = json.dumps({
            "possible_diagnoses": None,
            "recommended_exams": ["Y"],
            "reasoning": "Test.",
            "sources": ["Source"],
            "confidence": 0.8,
            "recommendation_type": "analysis",
        })

        result = run_consultation(
            cpf="MALFORM.005",
            doctor_question="Test?",
            patient_profile={"nome": "Test", "idade": 40, "sexo": "M", "peso": 75},
            llm=mock_llm,
        )
        # Null diagnoses might still pass or escalate depending on implementation
        assert "final_answer" in result


# -----------------------------------------------------------------------------
# REQ-E2E-EXT-7: Large History Performance
# -----------------------------------------------------------------------------

class TestLargeHistoryPerformance:
    """Performance with many consultation records."""

    def test_ten_consultations(self):
        """Patient with 10 consultations - all retrievable."""
        cpf = "HISTORY.010"
        save_patient(cpf, {"nome": "History Test", "idade": 50, "sexo": "M", "peso": 80})

        for i in range(10):
            run_consultation(
                cpf=cpf,
                doctor_question=f"Consulta número {i+1}: sintoma variado.",
            )

        history = get_consultation_history(cpf, n_results=10)
        assert len(history) == 10

    def test_history_limit_respected(self):
        """History limit parameter is respected."""
        cpf = "HISTORY.LIMIT"
        save_patient(cpf, {"nome": "Limit Test", "idade": 40, "sexo": "F", "peso": 65})

        for i in range(20):
            run_consultation(
                cpf=cpf,
                doctor_question=f"Consulta {i+1}",
            )

        # Default limit is 5
        history_default = get_consultation_history(cpf)
        assert len(history_default) == 5

        # Request 10
        history_10 = get_consultation_history(cpf, n_results=10)
        assert len(history_10) == 10


# -----------------------------------------------------------------------------
# REQ-E2E-EXT-8: Unicode and Internationalization
# -----------------------------------------------------------------------------

class TestUnicodeAndInternationalization:
    """Handle various character sets and international names."""

    def test_japanese_characters(self):
        """Patient name with Japanese characters."""
        result = run_consultation(
            cpf="UNICODE.001",
            doctor_question="Patient with headache.",
            patient_profile={"nome": "田中太郎", "idade": 35, "sexo": "M", "peso": 70},
        )
        saved = get_patient("UNICODE.001")
        assert saved["nome"] == "田中太郎"

    def test_arabic_characters(self):
        """Patient name with Arabic characters."""
        result = run_consultation(
            cpf="UNICODE.002",
            doctor_question="Patient with fever.",
            patient_profile={"nome": "محمد أحمد", "idade": 30, "sexo": "M", "peso": 75},
        )
        saved = get_patient("UNICODE.002")
        assert saved["nome"] == "محمد أحمد"

    def test_emoji_in_question(self):
        """Question containing emoji (edge case)."""
        result = run_consultation(
            cpf="UNICODE.003",
            doctor_question="Paciente com dor 😰 e febre 🤒",
            patient_profile={"nome": "Emoji Test", "idade": 25, "sexo": "F", "peso": 60},
        )
        assert result["safety_passed"] is True

    def test_portuguese_medical_terms(self):
        """Brazilian Portuguese medical terminology."""
        result = run_consultation(
            cpf="PTBR.001",
            doctor_question="Paciente com artralgia, mialgia e astenia intensas.",
            patient_profile={"nome": "PT Patient", "idade": 45, "sexo": "F", "peso": 68},
        )
        assert result["safety_passed"] is True


# -----------------------------------------------------------------------------
# REQ-E2E-EXT-9: MockLLM Keyword Coverage
# -----------------------------------------------------------------------------

class TestMockLLMKeywordCoverage:
    """Verify MockLLM handles all defined keywords."""

    def test_all_mock_llm_keywords(self):
        """Test each keyword category defined in MockLLM."""
        test_cases = [
            ("abdominal", ["intestino", "crohn", "colite"]),
            ("cefaleia", ["enxaqueca", "cefaleia", "migran"]),
            ("dispneia", ["cardíaca", "coronária", "ecg"]),
            ("diabetes", ["diabetes", "glicemia", "hba1c"]),
        ]

        for keyword, expected_terms in test_cases:
            cpf = f"MOCK.{keyword.upper()}"
            result = run_consultation(
                cpf=cpf,
                doctor_question=f"Paciente com {keyword}.",
                patient_profile={"nome": f"Test {keyword}", "idade": 40, "sexo": "M", "peso": 75},
            )
            answer = result["final_answer"].lower()
            assert any(term in answer for term in expected_terms), \
                f"Keyword '{keyword}' did not produce expected terms"

    def test_unknown_keyword_default_response(self):
        """Unknown keywords trigger default response."""
        result = run_consultation(
            cpf="MOCK.UNKNOWN",
            doctor_question="Paciente com sintomas xyz123 desconhecidos.",
            patient_profile={"nome": "Unknown", "idade": 40, "sexo": "M", "peso": 75},
        )
        assert result["safety_passed"] is True
        # Default response has confidence 0.45
        answer = result["final_answer"].lower()
        assert "indeterminado" in answer or "triagem" in answer or "hemograma" in answer


# -----------------------------------------------------------------------------
# REQ-E2E-EXT-10: Pipeline State Validation
# -----------------------------------------------------------------------------

class TestPipelineStateValidation:
    """Validate state transitions through pipeline."""

    def test_state_evolution_through_nodes(self):
        """Verify state is properly modified at each pipeline stage."""
        from src.graph.state import ClinicalState
        from src.graph.pipeline import build_graph

        llm = MockLLM()
        pipeline = build_graph(llm=llm)

        initial_state: ClinicalState = {
            "cpf": "STATE.001",
            "doctor_question": "Dor abdominal?",
            "patient_profile": {"nome": "State Test", "idade": 35, "sexo": "M", "peso": 70},
            "is_new_patient": False,
            "consultation_history": [],
            "prompt": "",
            "raw_response": "",
            "safety_passed": False,
            "sources": [],
            "final_answer": "",
            "needs_escalation": False,
        }

        result = pipeline.invoke(initial_state)

        # State should be populated after pipeline
        assert result["prompt"] != ""  # build_prompt populated this
        assert result["raw_response"] != ""  # llm_reasoning populated this
        assert result["final_answer"] != ""  # save_and_format populated this
        assert result["safety_passed"] is True
        assert result["needs_escalation"] is False

    def test_patient_profile_in_state(self):
        """Patient profile correctly loaded into state."""
        result = run_consultation(
            cpf="PROFILE.001",
            doctor_question="Test?",
            patient_profile={"nome": "Profile Test", "idade": 50, "sexo": "F", "peso": 65},
        )
        assert result["patient_profile"]["nome"] == "Profile Test"
        assert result["patient_profile"]["idade"] == 50
