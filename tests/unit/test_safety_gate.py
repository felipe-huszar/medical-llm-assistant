"""
Tests for safety gate — prose format validation.
"""
import pytest
from src.safety.gate import validate_response, format_escalation_message, _extract_sections, _extract_list_items

# Resposta clínica válida no formato Lucas
_VALID_PROSE = """Resumo clínico:
Paciente com dispneia progressiva e edema periférico.

Raciocínio clínico:
Dispneia progressiva pode indicar comprometimento cardiopulmonar.

Hipótese diagnóstica principal:
Insuficiência cardíaca descompensada

Diagnósticos diferenciais:
- Tromboembolismo pulmonar
- Pneumonia bilateral

Exames recomendados:
- Ecocardiograma
- BNP
- Radiografia de tórax"""


class TestSafetyGateRules:
    def test_valid_response_passes(self):
        result = validate_response(_VALID_PROSE)
        assert result["safety_passed"] is True
        assert result["needs_escalation"] is False

    def test_short_response_escalates(self):
        result = validate_response("ok")
        assert result["needs_escalation"] is True
        assert "curta" in result["reason"].lower()

    def test_empty_string_escalates(self):
        result = validate_response("")
        assert result["needs_escalation"] is True

    def test_prescription_language_escalates(self):
        result = validate_response(_VALID_PROSE + "\nprescrevo amoxicilina 500mg/dia")
        assert result["needs_escalation"] is True
        assert "prescrição" in result["reason"].lower()

    def test_dose_prescription_escalates(self):
        result = validate_response("tome 2 comprimidos de 500mg/dia de enalapril")
        # Muito curto OU contém prescrição — ambos escapam
        assert result["needs_escalation"] is True

    def test_sections_extracted(self):
        result = validate_response(_VALID_PROSE)
        sections = result["sections"]
        assert "Hipótese diagnóstica principal" in sections
        assert "Diagnósticos diferenciais" in sections
        assert "Exames recomendados" in sections

    def test_hipotese_content(self):
        result = validate_response(_VALID_PROSE)
        hipotese = result["sections"].get("Hipótese diagnóstica principal", "")
        assert "Insuficiência cardíaca" in hipotese

    def test_safety_passed_true_on_valid(self):
        result = validate_response(_VALID_PROSE)
        assert result["safety_passed"] is True

    def test_safety_passed_false_on_short(self):
        result = validate_response("texto curto")
        assert result["safety_passed"] is False

    def test_high_quality_response_passes(self):
        long_prose = _VALID_PROSE + "\n\nInformações adicionais relevantes para o caso clínico apresentado pelo médico."
        result = validate_response(long_prose)
        assert result["safety_passed"] is True


class TestExtractSections:
    def test_extracts_all_sections(self):
        sections = _extract_sections(_VALID_PROSE)
        assert "Resumo clínico" in sections
        assert "Raciocínio clínico" in sections
        assert "Hipótese diagnóstica principal" in sections
        assert "Diagnósticos diferenciais" in sections
        assert "Exames recomendados" in sections

    def test_hipotese_value(self):
        sections = _extract_sections(_VALID_PROSE)
        assert "Insuficiência cardíaca" in sections["Hipótese diagnóstica principal"]

    def test_empty_text_returns_empty(self):
        sections = _extract_sections("")
        assert sections == {}


class TestExtractListItems:
    def test_dash_items(self):
        text = "- item um\n- item dois\n- item três"
        items = _extract_list_items(text)
        assert len(items) == 3
        assert "item um" in items

    def test_bullet_items(self):
        text = "• BNP\n• Ecocardiograma"
        items = _extract_list_items(text)
        assert len(items) == 2

    def test_empty_returns_empty(self):
        assert _extract_list_items("") == []


class TestEscalationMessage:
    def test_escalation_contains_reason(self):
        msg = format_escalation_message("resposta muito curta")
        assert "resposta muito curta" in msg

    def test_escalation_is_warning(self):
        msg = format_escalation_message("qualquer razão")
        assert "⚠️" in msg

    def test_escalation_no_prescription(self):
        msg = format_escalation_message("teste")
        assert "prescrevo" not in msg.lower()
