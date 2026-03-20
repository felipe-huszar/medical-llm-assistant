"""
nodes.py - LangGraph node functions for the medical assistant pipeline.

Nodes:
  1. check_patient      → lookup CPF in ChromaDB
  2. retrieve_history   → fetch consultation history
  3. build_prompt       → assemble LLM prompt
  4. llm_reasoning      → call LLM
  5. safety_gate        → validate response
  6. save_and_format    → persist + format final answer
  7. escalation         → handle unsafe responses
"""

from __future__ import annotations

import json
import os
from typing import Any

from src.graph.state import ClinicalState
from src.audit.logger import audit_log
from src.rag.patient_rag import (
    get_patient,
    patient_exists,
    save_patient,
    get_consultation_history,
    save_consultation,
)
from src.safety.gate import validate_response, format_escalation_message
from src.llm.factory import get_llm


# ---------------------------------------------------------------------------
# Node 1: check_patient
# ---------------------------------------------------------------------------

def check_patient(state: ClinicalState) -> ClinicalState:
    """Lookup CPF; load profile if exists, otherwise mark as new."""
    cpf = state["cpf"]
    profile = get_patient(cpf)

    if profile is None:
        state["is_new_patient"] = True
        state["patient_profile"] = {}
    else:
        state["is_new_patient"] = False
        state["patient_profile"] = profile

    audit_log("node_executed", cpf=cpf, node="check_patient",
              is_new_patient=state["is_new_patient"])
    return state


# ---------------------------------------------------------------------------
# Node 2: retrieve_history
# ---------------------------------------------------------------------------

def retrieve_history(state: ClinicalState) -> ClinicalState:
    """Fetch last consultation summaries for this patient."""
    cpf = state["cpf"]
    benchmark_mode = bool(state.get("benchmark_mode", False))
    if benchmark_mode:
        state["consultation_history"] = []
        audit_log("node_executed", cpf=cpf, node="retrieve_history",
                  history_count=0, benchmark_mode=True)
        return state

    history = get_consultation_history(cpf, n_results=5)
    state["consultation_history"] = history
    audit_log("node_executed", cpf=cpf, node="retrieve_history",
              history_count=len(history), benchmark_mode=False)
    return state


# ---------------------------------------------------------------------------
# Node 3: build_prompt
# ---------------------------------------------------------------------------

def build_prompt(state: ClinicalState) -> ClinicalState:
    """Assemble structured clinical prompt from profile + history + question.

    Alinhado com o formato de treinamento do Lucas (dataset sintético):

        Contexto do paciente:
        Paciente <sexo>, <idade> anos.
        Histórico: <comorbidades ou queixas anteriores resumidas>

        Sintomas relatados:
        <queixa atual>

    O campo "Histórico" no treinamento continha comorbidades (ex: "hipertensão, diabetes")
    e, quando útil, contexto clínico prévio explicitamente selecionado pelo médico.
    Consultas anteriores recuperadas da lista ficam visíveis na UI, mas só entram no
    prompt se forem selecionadas explicitamente.
    """
    profile = state.get("patient_profile", {})
    selected_history = state.get("selected_history", []) or []
    question = state.get("doctor_question", "")

    sexo  = profile.get("sexo", "N/A")
    idade = profile.get("idade", "N/A")
    peso  = profile.get("peso", "")

    peso_text = f", {peso} kg" if peso else ""
    profile_line = f"Paciente {sexo}, {idade} anos{peso_text}."

    # Prioridade 1: comorbidades registradas no perfil (condições crônicas permanentes)
    # Alinhado com o treinamento: "Histórico: hipertensão, diabetes"
    comorbidades = profile.get("comorbidades", [])
    if isinstance(comorbidades, list):
        comorbidades_text = ", ".join(comorbidades) if comorbidades else ""
    else:
        comorbidades_text = str(comorbidades).strip()

    history_parts = []
    if comorbidades_text:
        history_parts.append(comorbidades_text)

    # Consultas anteriores só entram no prompt se forem selecionadas explicitamente pelo médico.
    explicit_selected_history = [item.strip() for item in selected_history if str(item).strip()]
    if explicit_selected_history:
        history_parts.extend(explicit_selected_history)

    # Monta contexto no formato do treinamento, mas sem reaproveitar histórico implicitamente.
    if history_parts:
        history_line = f"Histórico: {'; '.join(history_parts)}"
    else:
        history_line = "Histórico: não informado. Comorbidades registradas: nenhuma."

    guardrail_block = (
        "Regras críticas:\n"
        "- Use apenas informações explicitamente fornecidas.\n"
        "- Não invente histórico, comorbidades ou fatores de risco prévios.\n"
        "- Se não houver histórico, escreva literalmente: 'Histórico relevante não informado'.\n"
        "- Use status 'insufficient_data' somente quando os dados disponíveis não permitirem priorização clínica razoável.\n"
        "- A ausência de detalhes acessórios ou exames ainda não realizados não impede 'supported_hypothesis' quando o quadro clínico central já for suficientemente característico.\n"
        "- Se o caso estiver fora do escopo principal do assistente, use status 'out_of_scope' e sugira a especialidade.\n"
        "- Não afirme hipótese grave como principal sem evidência mínima no caso informado.\n"
        "- Use apenas um destes status: supported_hypothesis, insufficient_data, out_of_scope, needs_urgent_escalation.\n"
        "- Estruture a resposta com: Status da análise, Resumo clínico, Hipótese diagnóstica principal, Diagnósticos diferenciais, Exames recomendados, Raciocínio clínico.\n"
        "- Se aplicável, inclua Dados faltantes e Especialidade sugerida."
    )

    context_block = (
        f"Contexto do paciente:\n"
        f"{profile_line}\n"
        f"{history_line}"
    )

    prompt = f"{context_block}\n\n{guardrail_block}\n\nSintomas relatados:\n{question}"

    state["prompt"] = prompt
    state["has_explicit_history"] = bool(history_parts)
    audit_log("node_executed", cpf=state["cpf"], node="build_prompt",
              prompt_length=len(prompt), has_history=bool(history_parts),
              selected_history_count=len(explicit_selected_history))
    return state


# ---------------------------------------------------------------------------
# Node 4: llm_reasoning
# ---------------------------------------------------------------------------

def llm_reasoning(state: ClinicalState, llm: Any = None) -> ClinicalState:
    """Call LLM with the assembled prompt."""
    if llm is None:
        # Lazy import to allow factory to be set at runtime
        from src.llm.factory import get_llm
        llm = get_llm()

    prompt = state.get("prompt", "")
    raw = llm.invoke(prompt)
    state["raw_response"] = raw
    # Loga prompt enviado e primeiros 300 chars da resposta
    audit_log("node_executed", cpf=state["cpf"], node="llm_reasoning",
              response_length=len(raw), llm_type=type(llm).__name__,
              prompt_sent=prompt[:500],  # LOG DO PROMPT ENVIADO
              raw_preview=raw[:300] if raw else "")
    return state


# ---------------------------------------------------------------------------
# Node 5: safety_gate
# ---------------------------------------------------------------------------

def safety_gate(state: ClinicalState) -> ClinicalState:
    """Validate LLM response against safety rules (prose format)."""
    raw = state.get("raw_response", "")
    validation = validate_response(raw, context_text=state.get("prompt", ""))

    state["safety_passed"] = validation["safety_passed"]
    state["needs_escalation"] = validation["needs_escalation"]
    state["sources"] = []
    state["parsed_response"] = validation.get("sections", {})

    # Guardrail adicional: se não houve histórico/comorbidades no contexto,
    # o modelo não pode afirmar histórico específico na resposta.
    has_explicit_history = state.get("has_explicit_history", False)
    if not validation["needs_escalation"] and not has_explicit_history:
        sections = validation.get("sections", {})
        summary_and_reasoning = "\n".join([
            sections.get("Resumo clínico", ""),
            sections.get("Raciocínio clínico", ""),
        ]).lower()

        # Permite explicitar ausência de histórico/comorbidades.
        allowed_absence_markers = [
            "histórico relevante não informado",
            "histórico não informado",
            "sem histórico relevante",
            "não há histórico",
            "comorbidades registradas: nenhuma",
            "comorbidades conhecidas como nenhuma",
            "sem comorbidades",
            "nenhuma comorbidade",
        ]

        # Bloqueia apenas afirmação positiva de histórico específico ausente do contexto.
        suspicious_markers = [
            "com histórico de ",
            "histórico de ",
            "histórico relevante:",
            "paciente com histórico de ",
        ]

        has_allowed_absence = any(marker in summary_and_reasoning for marker in allowed_absence_markers)
        has_positive_history_claim = any(marker in summary_and_reasoning for marker in suspicious_markers)

        if has_positive_history_claim and not has_allowed_absence:
            validation["needs_escalation"] = True
            validation["safety_passed"] = False
            validation["reason"] = (
                "Resposta inferiu histórico/comorbidades não fornecidos no contexto do paciente."
            )
            state["safety_passed"] = False
            state["needs_escalation"] = True

    if validation["needs_escalation"]:
        state["final_answer"] = format_escalation_message(validation["reason"])
        audit_log("safety_triggered", cpf=state["cpf"], node="safety_gate",
                  reason=validation["reason"], action="escalation")
    else:
        sections = validation.get("sections", {})
        audit_log("node_executed", cpf=state["cpf"], node="safety_gate",
                  safety_passed=True, sections_found=list(sections.keys()))

    return state


# ---------------------------------------------------------------------------
# Node 6: save_and_format
# ---------------------------------------------------------------------------

def save_and_format(state: ClinicalState) -> ClinicalState:
    """Persist consultation to ChromaDB and format the final answer (prose format)."""
    from src.safety.gate import _extract_list_items

    cpf = state["cpf"]
    question = state.get("doctor_question", "")
    raw = state.get("raw_response", "")
    sections = state.get("parsed_response") or {}

    # Extrai seções da prosa
    status_analise = sections.get("Status da análise", "").strip()
    resumo      = sections.get("Resumo clínico", "").strip()
    raciocinio  = sections.get("Raciocínio clínico", "").strip()
    hipotese    = sections.get("Hipótese diagnóstica principal", "").strip()
    diferenciais_raw = sections.get("Diagnósticos diferenciais", "")
    exames_raw  = sections.get("Exames recomendados", "")
    dados_faltantes_raw = sections.get("Dados faltantes", "")
    especialidade_sugerida = sections.get("Especialidade sugerida", "").strip()

    diferenciais = _extract_list_items(diferenciais_raw)
    exames       = _extract_list_items(exames_raw)
    dados_faltantes = _extract_list_items(dados_faltantes_raw)

    # --- Monta markdown rico para o Gradio ---
    def _bullet_list(items):
        return "\n".join(f"  • {i}" for i in items) if items else "  • N/A"

    parts = ["## 🩺 Análise Clínica\n"]

    if status_analise:
        parts.append(f"### 🧭 Status da Análise\n{status_analise}\n")

    if resumo:
        parts.append(f"### 📋 Resumo Clínico\n{resumo}\n")

    if hipotese:
        parts.append(f"### 🎯 Hipótese Diagnóstica Principal\n{hipotese}\n")

    if diferenciais:
        parts.append(f"### 🔍 Diagnósticos Diferenciais\n{_bullet_list(diferenciais)}\n")

    if exames:
        parts.append(f"### 🧪 Exames Recomendados\n{_bullet_list(exames)}\n")

    if dados_faltantes:
        parts.append(f"### ❓ Dados Faltantes\n{_bullet_list(dados_faltantes)}\n")

    if especialidade_sugerida:
        parts.append(f"### 👨‍⚕️ Especialidade Sugerida\n{especialidade_sugerida}\n")

    if raciocinio:
        parts.append(f"### 💭 Raciocínio Clínico\n{raciocinio}\n")

    parts.append("---\n> ⚕️ *Esta análise é apenas orientativa. A decisão clínica final é responsabilidade do médico assistente.*")

    answer = "\n".join(parts)
    state["final_answer"] = answer

    benchmark_mode = bool(state.get("benchmark_mode", False))
    audit_log("consultation_saved", cpf=cpf, node="save_and_format",
              hipotese=hipotese, analysis_status=status_analise,
              diferenciais_count=len(diferenciais),
              exames_count=len(exames), sections_found=list(sections.keys()),
              benchmark_mode=benchmark_mode)

    # Salva prosa no ChromaDB (contexto para próximas consultas)
    if not benchmark_mode:
        save_consultation(
            cpf=cpf,
            question=question,
            answer=raw,  # salva resposta bruta para contexto de RAG
            metadata={
                "hipotese": hipotese,
                "exames": json.dumps(exames),
                "diferenciais": json.dumps(diferenciais),
            },
        )

    return state


# ---------------------------------------------------------------------------
# Node 7: escalation
# ---------------------------------------------------------------------------

def escalation(state: ClinicalState) -> ClinicalState:
    """Handle escalation path — message already set by safety_gate."""
    # final_answer already populated by safety_gate with escalation message
    return state
