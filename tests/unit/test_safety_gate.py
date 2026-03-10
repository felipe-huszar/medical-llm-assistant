"""
Unit tests for src/safety/gate.py

Requirements validated:
  - REQ-SAFETY-1: recommendation_type == "prescription" → needs_escalation=True
  - REQ-SAFETY-2: confidence < 0.4 → needs_escalation=True
  - REQ-SAFETY-3: empty sources → needs_escalation=True, safety_passed=False
  - REQ-SAFETY-4: valid response → safety_passed=True, needs_escalation=False
  - REQ-SAFETY-5: invalid JSON → needs_escalation=True
  - REQ-SAFETY-6: escalation message is informative
"""

import json
import pytest

from src.safety.gate import validate_response, format_escalation_message


def _make_response(**overrides) -> str:
    """Helper to build a valid JSON response with optional field overrides."""
    base = {
        "possible_diagnoses": ["SII", "Crohn"],
        "recommended_exams": ["Colonoscopia"],
        "reasoning": "Análise baseada nos sintomas.",
        "sources": ["Protocolo GI-2024"],
        "confidence": 0.75,
        "recommendation_type": "analysis",
    }
    base.update(overrides)
    return json.dumps(base)


class TestSafetyGateRules:
    def test_valid_response_passes(self):
        """REQ-SAFETY-4: well-formed response passes all rules."""
        result = validate_response(_make_response())
        assert result["safety_passed"] is True
        assert result["needs_escalation"] is False
        assert result["sources"] == ["Protocolo GI-2024"]

    def test_prescription_type_escalates(self):
        """REQ-SAFETY-1: prescription type triggers escalation."""
        result = validate_response(_make_response(recommendation_type="prescription"))
        assert result["needs_escalation"] is True
        assert result["safety_passed"] is False
        assert "prescription" in result["reason"].lower() or "prescrição" in result["reason"].lower()

    def test_low_confidence_escalates(self):
        """REQ-SAFETY-2: confidence < 0.4 triggers escalation."""
        result = validate_response(_make_response(confidence=0.3))
        assert result["needs_escalation"] is True
        assert result["safety_passed"] is False
        assert "0.3" in result["reason"] or "confiança" in result["reason"].lower()

    def test_confidence_exactly_04_passes(self):
        """REQ-SAFETY-2: confidence == 0.4 is NOT escalated (boundary)."""
        result = validate_response(_make_response(confidence=0.4))
        assert result["safety_passed"] is True
        assert result["needs_escalation"] is False

    def test_confidence_below_threshold_edge(self):
        """REQ-SAFETY-2: confidence = 0.39 escalates."""
        result = validate_response(_make_response(confidence=0.39))
        assert result["needs_escalation"] is True

    def test_empty_sources_escalates(self):
        """REQ-SAFETY-3: empty sources triggers escalation."""
        result = validate_response(_make_response(sources=[]))
        assert result["needs_escalation"] is True
        assert result["safety_passed"] is False

    def test_missing_sources_key_escalates(self):
        """REQ-SAFETY-3: missing sources key is treated as empty."""
        payload = {
            "possible_diagnoses": ["X"],
            "recommended_exams": ["Y"],
            "reasoning": "ok",
            "confidence": 0.7,
            "recommendation_type": "analysis",
            # 'sources' key omitted
        }
        result = validate_response(json.dumps(payload))
        assert result["needs_escalation"] is True

    def test_invalid_json_escalates(self):
        """REQ-SAFETY-5: invalid JSON string triggers escalation."""
        result = validate_response("this is not json {{{")
        assert result["needs_escalation"] is True
        assert result["safety_passed"] is False
        assert "json" in result["reason"].lower() or "json" in result["reason"].lower()

    def test_empty_string_escalates(self):
        """REQ-SAFETY-5: empty string is invalid JSON."""
        result = validate_response("")
        assert result["needs_escalation"] is True

    def test_high_confidence_analysis_passes(self):
        """REQ-SAFETY-4: high confidence analysis response passes cleanly."""
        result = validate_response(_make_response(confidence=0.9, sources=["SBC", "AHA"]))
        assert result["safety_passed"] is True
        assert result["sources"] == ["SBC", "AHA"]


class TestEscalationMessage:
    def test_escalation_message_contains_reason(self):
        """REQ-SAFETY-6: escalation message includes the failure reason."""
        msg = format_escalation_message("Confiança muito baixa (0.30)")
        assert "0.30" in msg or "Confiança" in msg

    def test_escalation_message_is_warning(self):
        """REQ-SAFETY-6: escalation message signals need for medical review."""
        msg = format_escalation_message("algum motivo")
        # deve ter algum indicador de aviso
        assert any(w in msg for w in ["⚠️", "revisão", "especialista", "avaliação"])

    def test_escalation_message_no_prescription(self):
        """REQ-SAFETY-6: escalation message never implies medication prescription."""
        msg = format_escalation_message("qualquer motivo")
        assert "prescreva" not in msg.lower()
        assert "tome" not in msg.lower()
