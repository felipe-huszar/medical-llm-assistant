"""
Tests for MockLLM — prose format (Lucas format).
"""

import pytest
from src.llm.mock_llm import MockLLM


@pytest.fixture
def llm():
    return MockLLM()


class TestMockLLMStructure:
    def test_returns_string(self, llm):
        raw = llm.invoke("sintoma genérico")
        assert isinstance(raw, str)

    def test_response_not_empty(self, llm):
        raw = llm.invoke("sintoma genérico")
        assert len(raw) > 50

    def test_has_hipotese_section(self, llm):
        raw = llm.invoke("dispneia e fadiga")
        assert "Hipótese diagnóstica principal" in raw

    def test_has_diferenciais_section(self, llm):
        raw = llm.invoke("dispneia e fadiga")
        assert "Diagnósticos diferenciais" in raw

    def test_has_exames_section(self, llm):
        raw = llm.invoke("dispneia e fadiga")
        assert "Exames recomendados" in raw

    def test_has_raciocinio_section(self, llm):
        raw = llm.invoke("dispneia e fadiga")
        assert "Raciocínio clínico" in raw

    def test_no_direct_prescription(self, llm):
        """Modelo nunca deve prescrever diretamente."""
        raw = llm.invoke("dor de cabeça")
        assert "prescrevo" not in raw.lower()
        assert "tome " not in raw.lower()

    def test_callable_interface(self, llm):
        raw = llm("dispneia e fadiga")
        assert isinstance(raw, str) and len(raw) > 0


class TestMockLLMKeywords:
    def test_abdominal_keywords(self, llm):
        raw = llm.invoke("dores abdominais ao evacuar")
        assert "Intestino" in raw or "intestino" in raw or "Crohn" in raw or "colite" in raw.lower()

    def test_cefaleia_keywords(self, llm):
        raw = llm.invoke("paciente com cefaleia intensa")
        assert "Enxaqueca" in raw or "enxaqueca" in raw or "tensional" in raw.lower()

    def test_cardio_keywords(self, llm):
        raw = llm.invoke("dispneia progressiva e edema em membros inferiores")
        assert "cardíaca" in raw.lower() or "insuficiência" in raw.lower()

    def test_diabetes_keywords(self, llm):
        raw = llm.invoke("paciente com polidipsia e poliuria")
        assert "diabetes" in raw.lower() or "Diabetes" in raw

    def test_unknown_symptom_returns_default(self, llm):
        raw = llm.invoke("xyz123 sintoma desconhecido")
        assert "Exames recomendados" in raw
        assert "Hemograma" in raw or "hemograma" in raw
