"""
app.py - Gradio UI for the Medical LLM Assistant.

Tab 1: Paciente - CPF lookup / patient registration
Tab 2: Consulta  - Clinical question + LLM response
"""

import os
import re
import gradio as gr

from src.llm.factory import get_llm
from src.rag.patient_rag import get_patient, save_patient, patient_exists, seed_from_file
from src.graph.pipeline import run_consultation

# Seed DB on startup
seed_from_file("data/patients_seed.json")

# Global LLM (shared across requests)
_llm = get_llm()


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------

def _profile_text(profile: dict) -> str:
    if not profile:
        return "(nenhum paciente carregado)"
    return (
        f"**Nome:** {profile.get('nome', 'N/A')}  "
        f"**Idade:** {profile.get('idade', 'N/A')} anos  "
        f"**Sexo:** {profile.get('sexo', 'N/A')}  "
        f"**Peso:** {profile.get('peso', 'N/A')} kg"
    )


# ---------------------------------------------------------------------------
# Tab 1: Paciente
# ---------------------------------------------------------------------------

def _normalize_cpf(cpf: str) -> str:
    """Remove formatação e retorna apenas os dígitos."""
    return re.sub(r"\D", "", cpf.strip())


def _format_cpf(digits: str) -> str:
    """Formata 11 dígitos como xxx.xxx.xxx-xx."""
    d = digits[:11]
    if len(d) == 11:
        return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
    return d


def lookup_patient(cpf: str):
    digits = _normalize_cpf(cpf)
    if not digits:
        return "⚠️ Informe um CPF.", gr.update(visible=False), None
    if len(digits) != 11:
        return "⚠️ CPF deve ter 11 dígitos.", gr.update(visible=False), None
    cpf = _format_cpf(digits)
    profile = get_patient(cpf)
    if profile:
        return (
            f"✅ Paciente encontrado: **{profile.get('nome', '')}**",
            gr.update(visible=False),
            profile,
        )
    else:
        return (
            f"🆕 CPF **{cpf}** não cadastrado. Preencha os dados abaixo:",
            gr.update(visible=True),
            None,
        )


def register_patient(cpf: str, nome: str, idade, sexo: str, peso):
    digits = _normalize_cpf(cpf)
    if len(digits) != 11:
        return "❌ CPF inválido. Informe 11 dígitos.", None, gr.update(selected=0)
    cpf = _format_cpf(digits)
    if not nome.strip():
        return "❌ Nome é obrigatório.", None, gr.update(selected=0)
    try:
        profile = {
            "cpf": cpf,
            "nome": nome.strip(),
            "idade": int(idade or 0),
            "sexo": sexo.strip().upper(),
            "peso": float(peso or 0),
        }
    except ValueError as e:
        return f"❌ Dados inválidos: {e}", None, gr.update(selected=0)

    save_patient(cpf, profile)
    # Navega direto para aba de consulta após cadastro
    return (
        f"✅ Paciente **{nome}** cadastrado com sucesso.",
        profile,
        gr.update(selected=1),
    )


# ---------------------------------------------------------------------------
# Tab 2: Consulta
# ---------------------------------------------------------------------------

def run_consult(cpf: str, question: str, current_patient: dict | None):
    digits = _normalize_cpf(cpf)
    if len(digits) != 11:
        return "(aguardando CPF)", "⚠️ Informe um CPF válido com 11 dígitos."
    if not question.strip():
        return _profile_text(current_patient) if current_patient else "(aguardando CPF)", "⚠️ Informe uma pergunta clínica."

    cpf = _format_cpf(digits)
    # Sempre re-verifica o CPF — ignora state de outra aba
    profile = get_patient(cpf)
    if not profile:
        return "(paciente não encontrado)", f"⚠️ CPF **{cpf}** não cadastrado. Registre o paciente primeiro."

    try:
        result = run_consultation(
            cpf=cpf,
            doctor_question=question,
            llm=_llm,
            patient_profile=profile,
        )
        return _profile_text(result.get("patient_profile", profile)), result.get("final_answer", "Sem resposta.")
    except Exception as e:
        return "", f"❌ Erro durante a consulta: {e}"


# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------

with gr.Blocks(title="Medical LLM Assistant", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🏥 Medical LLM Assistant\nAssistente clínico com IA — diagnósticos e exames recomendados.")

    current_patient = gr.State(None)

    with gr.Tabs() as tabs:

        # ── Tab 1: Paciente ─────────────────────────────────────────────────
        with gr.Tab("👤 Paciente", id=0):
            cpf_input = gr.Textbox(label="CPF do Paciente", placeholder="123.456.789-00")
            lookup_btn = gr.Button("Buscar Paciente", variant="primary")

            with gr.Group(visible=False) as new_patient_form:
                gr.Markdown("### Cadastrar Novo Paciente")
                nome_input   = gr.Textbox(label="Nome completo")
                idade_input  = gr.Number(label="Idade", precision=0)
                sexo_input   = gr.Radio(["M", "F"], label="Sexo", value="M")
                peso_input   = gr.Number(label="Peso (kg)", precision=1)
                register_btn = gr.Button("Registrar Paciente", variant="secondary")

            # Mensagem de status abaixo do formulário
            patient_status = gr.Markdown("")

            lookup_btn.click(
                fn=lookup_patient,
                inputs=[cpf_input],
                outputs=[patient_status, new_patient_form, current_patient],
            )

            register_btn.click(
                fn=register_patient,
                inputs=[cpf_input, nome_input, idade_input, sexo_input, peso_input],
                outputs=[patient_status, current_patient, tabs],
            )

        # ── Tab 2: Consulta ─────────────────────────────────────────────────
        with gr.Tab("🩺 Consulta", id=1):
            gr.Markdown("### Realizar Consulta Clínica")
            consult_cpf = gr.Textbox(label="CPF do Paciente", placeholder="123.456.789-00")
            profile_display = gr.Markdown("(aguardando CPF)")

            question_input = gr.Textbox(
                label="Pergunta Clínica",
                placeholder="Ex: Paciente com dores abdominais ao evacuar há 3 semanas. Quais diagnósticos considerar?",
                lines=4,
            )
            consult_btn  = gr.Button("Consultar", variant="primary")
            answer_output = gr.Markdown(label="Resposta do Assistente")

            consult_btn.click(
                fn=run_consult,
                inputs=[consult_cpf, question_input, current_patient],
                outputs=[profile_display, answer_output],
            )

if __name__ == "__main__":
    demo.launch(share=False)
