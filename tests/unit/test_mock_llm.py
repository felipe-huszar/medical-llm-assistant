"""
Unit tests for src/llm/mock_llm.py

Requirements validated:
  - REQ-LLM-1: MockLLM.invoke returns valid JSON string
  - REQ-LLM-2: JSON contains all required fields
  - REQ-LLM-3: Keyword matching returns domain-specific response
  - REQ-LLM-4: recommendation_type is always "analysis" (never "prescription")
  - REQ-LLM-5: confidence is between 0.0 and 1.0
  - REQ-LLM-6: sources list is never empty
"""

import json
import pytest

from src.llm.mock_llm import MockLLM

REQUIRED_FIELDS = {
    "possible_diagnoses",
    "recommended_exams",
    "reasoning",
    "sources",
    "confidence",
    "recommendation_type",
}


@pytest.fixture
def llm():
    return MockLLM()


class TestMockLLMStructure:
    def test_returns_valid_json(self, llm):
        """REQ-LLM-1: output is a valid JSON string."""
        raw = llm.invoke("sintoma genérico")
        parsed = json.loads(raw)  # must not raise
        assert isinstance(parsed, dict)

    def test_all_required_fields_present(self, llm):
        """REQ-LLM-2: all required fields are present in every response."""
        raw = llm.invoke("dor qualquer")
        parsed = json.loads(raw)
        for field in REQUIRED_FIELDS:
            assert field in parsed, f"Campo '{field}' ausente na resposta"

    def test_possible_diagnoses_is_list(self, llm):
        """REQ-LLM-2: possible_diagnoses is a non-empty list."""
        parsed = json.loads(llm.invoke("algum sintoma"))
        assert isinstance(parsed["possible_diagnoses"], list)
        assert len(parsed["possible_diagnoses"]) > 0

    def test_recommended_exams_is_list(self, llm):
        """REQ-LLM-2: recommended_exams is a non-empty list."""
        parsed = json.loads(llm.invoke("algum sintoma"))
        assert isinstance(parsed["recommended_exams"], list)
        assert len(parsed["recommended_exams"]) > 0

    def test_recommendation_type_is_never_prescription(self, llm):
        """REQ-LLM-4: MockLLM never returns 'prescription' type."""
        prompts = [
            "dor abdominal ao evacuar",
            "cefaleia intensa",
            "dispneia e dor no peito",
            "glicemia alta",
            "sintoma genérico sem keyword",
        ]
        for prompt in prompts:
            parsed = json.loads(llm.invoke(prompt))
            assert parsed["recommendation_type"] != "prescription", (
                f"Prompt '{prompt}' retornou 'prescription'"
            )

    def test_confidence_in_valid_range(self, llm):
        """REQ-LLM-5: confidence is between 0.0 and 1.0."""
        for prompt in ["dor intestinal", "cefaleia", "coração", "diabetes", "xyz"]:
            parsed = json.loads(llm.invoke(prompt))
            c = parsed["confidence"]
            assert 0.0 <= c <= 1.0, f"Confiança fora do range: {c}"

    def test_sources_never_empty(self, llm):
        """REQ-LLM-6: sources list is never empty."""
        for prompt in ["abdômen", "cabeça", "cardio", "glicemia", "sintoma X"]:
            parsed = json.loads(llm.invoke(prompt))
            assert parsed["sources"], f"Sources vazio para prompt: '{prompt}'"

    def test_callable_interface(self, llm):
        """MockLLM é callable além de ter .invoke()."""
        raw_via_call = llm("dor abdominal")
        raw_via_invoke = llm.invoke("dor abdominal")
        assert raw_via_call == raw_via_invoke


class TestMockLLMKeywords:
    def test_abdominal_keywords(self, llm):
        """REQ-LLM-3: prompt com 'abdomi' retorna diagnósticos GI."""
        parsed = json.loads(llm.invoke("Paciente com dor abdominal intensa"))
        diagnoses = [d.lower() for d in parsed["possible_diagnoses"]]
        assert any("intestin" in d or "crohn" in d or "colite" in d for d in diagnoses)

    def test_cefaleia_keywords(self, llm):
        """REQ-LLM-3: prompt com 'cefaleia' retorna diagnósticos neurológicos."""
        parsed = json.loads(llm.invoke("paciente relata cefaleia há 3 dias"))
        diagnoses = [d.lower() for d in parsed["possible_diagnoses"]]
        assert any("enxaqueca" in d or "cefaleia" in d for d in diagnoses)

    def test_cardio_keywords(self, llm):
        """REQ-LLM-3: prompt com 'dispneia' retorna diagnósticos cardíacos."""
        parsed = json.loads(llm.invoke("paciente com dispneia e dor no peito"))
        exams = [e.lower() for e in parsed["recommended_exams"]]
        assert any("ecg" in e or "ecocardiograma" in e or "troponina" in e for e in exams)

    def test_diabetes_keywords(self, llm):
        """REQ-LLM-3: prompt com 'glicemia' retorna diagnósticos metabólicos."""
        parsed = json.loads(llm.invoke("paciente com glicemia alta e polidipsia"))
        diagnoses = [d.lower() for d in parsed["possible_diagnoses"]]
        assert any("diabetes" in d for d in diagnoses)

    def test_unknown_symptom_returns_default(self, llm):
        """REQ-LLM-3: prompt sem keywords retorna resposta default válida."""
        parsed = json.loads(llm.invoke("xyzzy frobozz"))
        assert parsed["confidence"] < 0.8  # default é 0.45
        assert "recommendation_type" in parsed
