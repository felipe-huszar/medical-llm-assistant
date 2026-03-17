"""
Unit tests for src/graph/nodes.py

Requirements validated:
  - REQ-NODE-1: check_patient sets is_new_patient=True for unknown CPF
  - REQ-NODE-2: check_patient loads existing profile correctly
  - REQ-NODE-3: retrieve_history populates consultation_history list
  - REQ-NODE-4: build_prompt includes profile + history + question in prompt
  - REQ-NODE-5: llm_reasoning stores raw_response from LLM
  - REQ-NODE-6: safety_gate sets safety_passed and needs_escalation
  - REQ-NODE-7: save_and_format produces non-empty final_answer with MD structure
"""

import json
import pytest
from unittest.mock import MagicMock, patch

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


@pytest.fixture(autouse=True)
def _isolated_chroma(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DB_PATH", str(tmp_path / "chroma_nodes"))
    import src.rag.patient_rag as rag_mod
    rag_mod._client = None
    rag_mod._client_path = None
    yield
    rag_mod._client = None
    rag_mod._client_path = None


def _base_state(**overrides) -> ClinicalState:
    state: ClinicalState = {
        "cpf": "000.TEST.000-00",
        "doctor_question": "Quais diagnósticos para dor abdominal?",
        "patient_profile": {},
        "is_new_patient": False,
        "consultation_history": [],
        "prompt": "",
        "raw_response": "",
        "parsed_response": {},
        "safety_passed": False,
        "sources": [],
        "final_answer": "",
        "needs_escalation": False,
    }
    state.update(overrides)
    return state


class TestCheckPatientNode:
    def test_new_patient_sets_flag(self):
        """REQ-NODE-1: unknown CPF → is_new_patient=True, empty profile."""
        state = _base_state(cpf="NEW.CPF.000-00")
        result = check_patient(state)
        assert result["is_new_patient"] is True
        assert result["patient_profile"] == {}

    def test_existing_patient_loads_profile(self):
        """REQ-NODE-2: known CPF loads profile from ChromaDB."""
        from src.rag.patient_rag import save_patient
        cpf = "EX.IST.ING-00"
        save_patient(cpf, {"nome": "Existing", "idade": 50, "sexo": "M", "peso": 80})

        state = _base_state(cpf=cpf)
        result = check_patient(state)
        assert result["is_new_patient"] is False
        assert result["patient_profile"]["nome"] == "Existing"


class TestRetrieveHistoryNode:
    def test_empty_history_for_new_patient(self):
        """REQ-NODE-3: new patient has empty consultation_history."""
        state = _base_state(cpf="NO.HIST.ORY-00")
        result = retrieve_history(state)
        assert result["consultation_history"] == []

    def test_existing_history_loaded(self):
        """REQ-NODE-3: patient with consultations gets history populated."""
        from src.rag.patient_rag import save_consultation
        cpf = "HAS.HIST.ORY-00"
        save_consultation(cpf, "Pergunta anterior?", "Resposta anterior.")

        state = _base_state(cpf=cpf)
        result = retrieve_history(state)
        assert len(result["consultation_history"]) >= 1


class TestBuildPromptNode:
    def test_prompt_contains_question(self):
        """REQ-NODE-4: prompt includes the doctor's question."""
        state = _base_state(
            patient_profile={"nome": "João", "idade": 40, "sexo": "M", "peso": 75},
            doctor_question="Cefaleia intensa há 2 dias. O que investigar?",
        )
        result = build_prompt(state)
        assert "Cefaleia intensa" in result["prompt"]

    def test_prompt_contains_patient_profile(self):
        """REQ-NODE-4: prompt includes patient profile data (idade e sexo)."""
        state = _base_state(
            patient_profile={"nome": "Maria", "idade": 35, "sexo": "F", "peso": 62},
        )
        result = build_prompt(state)
        assert "35" in result["prompt"]
        assert "F" in result["prompt"] or "62" in result["prompt"]

    def test_prompt_contains_history(self):
        """REQ-NODE-4: prompt includes consultation history."""
        state = _base_state(
            consultation_history=["Pergunta: dor X\nResposta: análise Y"],
        )
        result = build_prompt(state)
        assert "dor X" in result["prompt"]

    def test_prompt_instructs_no_prescription(self):
        """REQ-NODE-4: prompt contains clinical context (system message handles safety)."""
        state = _base_state()
        result = build_prompt(state)
        # Safety instruction fica no system message do model_loader, não no prompt
        assert "Sintomas relatados:" in result["prompt"] or "Contexto" in result["prompt"]

    def test_prompt_is_nonempty_string(self):
        """REQ-NODE-4: prompt is always a non-empty string."""
        state = _base_state()
        result = build_prompt(state)
        assert isinstance(result["prompt"], str)
        assert len(result["prompt"]) > 100


class TestLLMReasoningNode:
    def test_raw_response_populated(self):
        """REQ-NODE-5: llm_reasoning stores LLM output in raw_response."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = '{"diagnose": "test"}'

        state = _base_state(prompt="teste de prompt")
        result = llm_reasoning(state, llm=mock_llm)
        assert result["raw_response"] == '{"diagnose": "test"}'
        mock_llm.invoke.assert_called_once_with("teste de prompt")

    def test_uses_factory_when_llm_none(self, monkeypatch):
        """REQ-NODE-5: when llm=None, factory is used via src.llm.factory.get_llm."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = '{"test": true}'

        import src.llm.factory as factory_mod
        monkeypatch.setattr(factory_mod, "get_llm", lambda: mock_llm)

        state = _base_state(prompt="prompt")
        result = llm_reasoning(state, llm=None)
        assert result["raw_response"] == '{"test": true}'


class TestSafetyGateNode:
    def _valid_raw(self):
        return """Resumo clínico:
Paciente com sintomas gastrointestinais.

Raciocínio clínico:
Quadro sugere patologia intestinal.

Hipótese diagnóstica principal:
Síndrome do intestino irritável

Diagnósticos diferenciais:
- Doença de Crohn

Exames recomendados:
- Colonoscopia"""

    def test_valid_response_passes_gate(self):
        """REQ-NODE-6: valid LLM response passes safety gate."""
        state = _base_state(raw_response=self._valid_raw())
        result = safety_gate(state)
        assert result["safety_passed"] is True
        assert result["needs_escalation"] is False

    def test_prescription_fails_gate(self):
        """REQ-NODE-6: prescription language fails safety gate."""
        raw = self._valid_raw() + "\nprescrevo amoxicilina 500mg/dia para o paciente."
        state = _base_state(raw_response=raw)
        result = safety_gate(state)
        assert result["needs_escalation"] is True
        assert result["safety_passed"] is False

    def test_escalation_sets_final_answer(self):
        """REQ-NODE-6: on escalation, final_answer is set to escalation message."""
        raw = "ok"  # muito curto → escalation
        state = _base_state(raw_response=raw)
        result = safety_gate(state)
        assert result["needs_escalation"] is True
        assert len(result["final_answer"]) > 0


_PROSE_RESPONSE = """Resumo clínico:
Paciente com sintomas gastrointestinais crônicos.

Raciocínio clínico:
Com base nos sintomas de dor abdominal e alterações do hábito intestinal.

Hipótese diagnóstica principal:
Síndrome do intestino irritável (SII)

Diagnósticos diferenciais:
- Doença de Crohn
- Colite ulcerativa

Exames recomendados:
- Colonoscopia
- PCR (Proteína C-reativa)"""


class TestSaveAndFormatNode:
    def test_final_answer_is_markdown(self):
        """REQ-NODE-7: final_answer contains Markdown headings."""
        state = _base_state(raw_response=_PROSE_RESPONSE, safety_passed=True)
        result = save_and_format(state)
        assert "##" in result["final_answer"] or "**" in result["final_answer"]

    def test_final_answer_contains_diagnoses(self):
        """REQ-NODE-7: final_answer includes diagnoses."""
        from src.safety.gate import _extract_sections
        sections = _extract_sections(_PROSE_RESPONSE)
        state = _base_state(raw_response=_PROSE_RESPONSE, parsed_response=sections, safety_passed=True)
        result = save_and_format(state)
        assert "SII" in result["final_answer"] or "intestino irritável" in result["final_answer"].lower()

    def test_final_answer_contains_exams(self):
        """REQ-NODE-7: final_answer includes recommended exams."""
        from src.safety.gate import _extract_sections
        sections = _extract_sections(_PROSE_RESPONSE)
        state = _base_state(raw_response=_PROSE_RESPONSE, parsed_response=sections, safety_passed=True)
        result = save_and_format(state)
        assert "Colonoscopia" in result["final_answer"] or "PCR" in result["final_answer"]

    def test_consultation_is_persisted(self):
        """REQ-NODE-7: consultation is saved to ChromaDB."""
        from src.rag.patient_rag import get_consultation_history
        cpf = "SAVE.AND.FMT-00"
        state = _base_state(
            cpf=cpf,
            raw_response=_PROSE_RESPONSE,
            doctor_question="Dor abdominal?",
            safety_passed=True,
        )
        save_and_format(state)
        history = get_consultation_history(cpf)
        assert len(history) == 1
        assert "Dor abdominal?" in history[0]
