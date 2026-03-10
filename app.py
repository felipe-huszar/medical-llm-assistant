"""
app.py - Gradio UI for the Medical LLM Assistant.

Tab 1: Paciente - CPF lookup / patient registration
Tab 2: Consulta  - Clinical question + LLM response
"""

import os
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
        f"**Nome:** {profile.get('nome', 'N/A')}\n"
        f"**Idade:** {profile.get('idade', 'N/A')} anos\n"
        f"**Sexo:** {profile.get('sexo', 'N/A')}\n"
        f"**Peso:** {profile.get('peso', 'N/A')} kg"
    )


# ---------------------------------------------------------------------------
# Tab 1: Paciente
# ---------------------------------------------------------------------------

def lookup_patient(cpf: str):
    cpf = cpf.strip()
    if not cpf:
        return "⚠️ Informe um CPF.", gr.update(visible=False), None

    profile = get_patient(cpf)
    if profile:
        return (
            f"✅ Paciente encontrado:\n\n{_profile_text(profile)}",
            gr.update(visible=False),
            profile,
        )
    else:
        return (
            f"🆕 CPF **{cpf}** não cadastrado. Preencha os dados abaixo:",
            gr.update(visible=True),
            None,
        )


def register_patient(cpf: str, nome: str, idade: str, sexo: str, peso: str):
    cpf = cpf.strip()
    try:
        profile = {
            "cpf": cpf,
            "nome": nome.strip(),
            "idade": int(idade),
            "sexo": sexo.strip().upper(),
            "peso": float(peso),
        }
    except ValueError as e:
        return f"❌ Dados inválidos: {e}", None

    save_patient(cpf, profile)
    return f"✅ Paciente **{nome}** cadastrado com sucesso.", profile


# ---------------------------------------------------------------------------
# Tab 2: Consulta
# ---------------------------------------------------------------------------

def run_consult(cpf: str, question: str, current_patient: dict | None):
    cpf = cpf.strip()
    if not cpf:
        return "⚠️ CPF não informado. Registre o paciente na aba 'Paciente'.", ""
    if not question.strip():
        return "", "⚠️ Informe uma pergunta clínica."

    profile = current_patient or get_patient(cpf)

    try:
        result = run_consultation(
            cpf=cpf,
            doctor_question=question,
            llm=_llm,
            patient_profile=profile,
        )
        return _profile_text(result.get("patient_profile", {})), result.get("final_answer", "Sem resposta.")
    except Exception as e:
        return "", f"❌ Erro durante a consulta: {e}"


# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------

with gr.Blocks(title="Medical LLM Assistant", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🏥 Medical LLM Assistant\nAssistente clínico com IA — diagnósticos e exames recomendados.")

    current_patient = gr.State(None)
    current_cpf = gr.State("")

    with gr.Tab("👤 Paciente"):
        cpf_input = gr.Textbox(label="CPF do Paciente", placeholder="123.456.789-00")
        lookup_btn = gr.Button("Buscar Paciente", variant="primary")
        patient_status = gr.Markdown("(aguardando busca)")

        with gr.Group(visible=False) as new_patient_form:
            gr.Markdown("### Cadastrar Novo Paciente")
            nome_input = gr.Textbox(label="Nome completo")
            idade_input = gr.Number(label="Idade", precision=0)
            sexo_input = gr.Radio(["M", "F"], label="Sexo", value="M")
            peso_input = gr.Number(label="Peso (kg)", precision=1)
            register_btn = gr.Button("Registrar Paciente", variant="secondary")

        lookup_btn.click(
            fn=lookup_patient,
            inputs=[cpf_input],
            outputs=[patient_status, new_patient_form, current_patient],
        )

        register_btn.click(
            fn=register_patient,
            inputs=[cpf_input, nome_input, idade_input, sexo_input, peso_input],
            outputs=[patient_status, current_patient],
        )

    with gr.Tab("🩺 Consulta"):
        gr.Markdown("### Realizar Consulta Clínica")
        consult_cpf = gr.Textbox(label="CPF do Paciente", placeholder="123.456.789-00")
        profile_display = gr.Markdown("(carregue o paciente)")
        question_input = gr.Textbox(
            label="Pergunta Clínica",
            placeholder="Ex: Paciente com dores abdominais ao evacuar há 3 semanas. Quais diagnósticos considerar?",
            lines=4,
        )
        consult_btn = gr.Button("Consultar", variant="primary")
        answer_output = gr.Markdown(label="Resposta do Assistente")

        consult_btn.click(
            fn=run_consult,
            inputs=[consult_cpf, question_input, current_patient],
            outputs=[profile_display, answer_output],
        )

if __name__ == "__main__":
    demo.launch(share=False)
