"""
Tests for safety gate — prose format validation.
"""
import pytest
from src.safety.gate import validate_response, format_escalation_message, _extract_sections, _extract_list_items

_VALID_PROSE = """Status da análise:
supported_hypothesis

Resumo clínico:
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
        ctx = "Sintomas relatados:\ndispneia progressiva; edema em membros inferiores; ortopneia"
        result = validate_response(_VALID_PROSE, context_text=ctx)
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
        assert result["needs_escalation"] is True

    def test_sections_extracted(self):
        result = validate_response(_VALID_PROSE, context_text="dispneia progressiva e edema")
        sections = result["sections"]
        assert "Hipótese diagnóstica principal" in sections
        assert "Diagnósticos diferenciais" in sections
        assert "Exames recomendados" in sections
        assert "Status da análise" in sections

    def test_hipotese_content(self):
        result = validate_response(_VALID_PROSE, context_text="dispneia progressiva e edema")
        hipotese = result["sections"].get("Hipótese diagnóstica principal", "")
        assert "Insuficiência cardíaca" in hipotese

    def test_insufficient_data_guardrail_escalates_if_not_recognized(self):
        raw = """Status da análise:
supported_hypothesis

Resumo clínico:
Paciente com dor de cabeça leve.

Raciocínio clínico:
Sugere quadro neurológico a esclarecer.

Hipótese diagnóstica principal:
hemorragia subaracnoide

Diagnósticos diferenciais:
- enxaqueca

Exames recomendados:
- tomografia de crânio"""
        result = validate_response(raw, context_text="Sintomas relatados:\ndor de cabeça leve")
        assert result["needs_escalation"] is True
        assert "insuficientes" in result["reason"].lower() or "evidência" in result["reason"].lower()

    def test_out_of_scope_guardrail_escalates_if_not_recognized(self):
        raw = """Status da análise:
supported_hypothesis

Resumo clínico:
Paciente com lesão cutânea crônica.

Raciocínio clínico:
Necessita avaliação.

Hipótese diagnóstica principal:
dermatite

Diagnósticos diferenciais:
- psoríase

Exames recomendados:
- avaliação clínica"""
        result = validate_response(raw, context_text="Lesão cutânea crônica com necessidade de dermatoscopia.")
        assert result["needs_escalation"] is True
        assert "fora do escopo" in result["reason"].lower() or "escopo" in result["reason"].lower()

    def test_out_of_scope_status_passes(self):
        raw = """Status da análise:
out_of_scope

Resumo clínico:
Caso requer avaliação especializada.

Hipótese diagnóstica principal:
fora do escopo principal do assistente

Diagnósticos diferenciais:
- avaliação especializada necessária

Exames recomendados:
- encaminhamento para especialista

Raciocínio clínico:
Pergunta exige exame especializado.

Especialidade sugerida:
dermatologia especializada"""
        result = validate_response(raw, context_text="Lesão cutânea crônica com necessidade de dermatoscopia.")
        assert result["needs_escalation"] is False
        assert result["safety_passed"] is True

    def test_insufficient_data_cannot_keep_grave_main_hypothesis(self):
        raw = """Status da análise:
insufficient_data

Resumo clínico:
Paciente apresentando dor no peito intensa.

Hipótese diagnóstica principal:
síndrome coronariana aguda

Diagnósticos diferenciais:
- dor torácica inespecífica

Exames recomendados:
- ECG
- troponina

Dados faltantes:
- localização da dor
- irradiação

Raciocínio clínico:
Dor torácica pode ter causa importante."""
        result = validate_response(raw, context_text="Sintomas relatados:\ndor no peito intensa")
        assert result["needs_escalation"] is True
        assert "inconsistente" in result["reason"].lower()

    def test_safety_passed_true_on_valid(self):
        result = validate_response(_VALID_PROSE, context_text="dispneia progressiva edema ortopneia")
        assert result["safety_passed"] is True

    def test_safety_passed_false_on_short(self):
        result = validate_response("texto curto")
        assert result["safety_passed"] is False


class TestExtractSections:
    def test_extracts_all_sections(self):
        sections = _extract_sections(_VALID_PROSE)
        assert "Resumo clínico" in sections
        assert "Raciocínio clínico" in sections
        assert "Hipótese diagnóstica principal" in sections
        assert "Diagnósticos diferenciais" in sections
        assert "Exames recomendados" in sections
        assert "Status da análise" in sections

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
