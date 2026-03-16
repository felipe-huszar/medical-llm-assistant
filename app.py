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

# LLM instanciado na primeira requisição (lê USE_MOCK_LLM do ambiente no momento do uso)
_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        _llm = get_llm()
    return _llm


# ---------------------------------------------------------------------------
# CPF helpers
# ---------------------------------------------------------------------------

def _normalize_cpf(cpf: str) -> str:
    """Remove formatação e retorna apenas os dígitos."""
    return re.sub(r"\D", "", cpf.strip())


def _format_cpf(digits: str) -> str:
    """Formata 11 dígitos como xxx.xxx.xxx-xx."""
    d = re.sub(r"\D", "", digits)[:11]
    if len(d) == 11:
        return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
    return d


def _valid_cpf(cpf: str) -> tuple[bool, str]:
    """Valida e retorna (ok, cpf_formatado_ou_erro)."""
    digits = _normalize_cpf(cpf)
    if len(digits) != 11:
        return False, "⚠️ CPF deve ter 11 dígitos (apenas números)."
    return True, _format_cpf(digits)


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

def lookup_patient(cpf: str):
    ok, cpf_or_err = _valid_cpf(cpf)
    if not ok:
        return cpf_or_err, gr.update(visible=False), None, "", ""

    cpf = cpf_or_err
    profile = get_patient(cpf)
    if profile:
        return (
            f"✅ Paciente encontrado: **{profile.get('nome', '')}**",
            gr.update(visible=False),
            profile,
            cpf,                    # pre-preenche o CPF na aba de consulta
            _profile_text(profile), # atualiza profile_display imediatamente
        )
    else:
        return (
            f"🆕 CPF **{cpf}** não cadastrado. Preencha os dados abaixo:",
            gr.update(visible=True),
            None,
            "",
            "(paciente não cadastrado)",
        )


def register_patient(cpf: str, nome: str, idade, sexo: str, peso):
    ok, cpf_or_err = _valid_cpf(cpf)
    if not ok:
        return cpf_or_err, None, gr.update(selected=0), "", "", ""
    cpf = cpf_or_err

    if not nome.strip():
        return "❌ Nome é obrigatório.", None, gr.update(selected=0), "", "", ""
    try:
        profile = {
            "cpf": cpf,
            "nome": nome.strip(),
            "idade": int(idade or 0),
            "sexo": sexo.strip().upper(),
            "peso": float(peso or 0),
        }
    except ValueError as e:
        return f"❌ Dados inválidos: {e}", None, gr.update(selected=0), "", "", ""

    save_patient(cpf, profile)
    return (
        f"✅ Paciente **{nome}** cadastrado com sucesso.",
        profile,
        cpf,                     # pre-preenche o CPF na aba de consulta
        _profile_text(profile),  # atualiza profile_display imediatamente
        "",                      # limpa pergunta anterior
        gr.update(selected=1),   # navega para aba de consulta (por último)
    )


# ---------------------------------------------------------------------------
# Tab 2: Consulta
# ---------------------------------------------------------------------------

def run_consult(cpf: str, question: str, current_patient: dict | None):
    ok, cpf_or_err = _valid_cpf(cpf)
    if not ok:
        return "⚠️ CPF inválido", cpf_or_err
    cpf = cpf_or_err

    # Sempre busca direto no DB pelo CPF digitado
    profile = get_patient(cpf)
    if not profile:
        return "❌ Paciente não encontrado", f"⚠️ CPF **{cpf}** não cadastrado. Registre o paciente primeiro."

    if not question.strip():
        return _profile_text(profile), "⚠️ Informe uma pergunta clínica."

    try:
        result = run_consultation(
            cpf=cpf,
            doctor_question=question,
            llm=_get_llm(),
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
            cpf_input = gr.Textbox(label="CPF do Paciente", placeholder="12345678900 ou 123.456.789-00")
            lookup_btn = gr.Button("Buscar Paciente", variant="primary")

            with gr.Group(visible=False) as new_patient_form:
                gr.Markdown("### Cadastrar Novo Paciente")
                nome_input  = gr.Textbox(label="Nome completo")
                idade_input = gr.Number(label="Idade", precision=0)
                sexo_input  = gr.Radio(["M", "F"], label="Sexo", value="M")
                peso_input  = gr.Number(label="Peso (kg)", precision=1)
                register_btn = gr.Button("Registrar Paciente", variant="secondary")

            patient_status = gr.Markdown("")

        # ── Tab 2: Consulta ─────────────────────────────────────────────────
        with gr.Tab("🩺 Consulta", id=1):
            gr.Markdown("### Realizar Consulta Clínica")
            consult_cpf = gr.Textbox(label="CPF do Paciente", placeholder="12345678900 ou 123.456.789-00")
            profile_display = gr.Markdown("(aguardando CPF)")
            gr.Markdown("💡 *Dica: Clique em **Consultar** para carregar o perfil do paciente.*")
            
            # Quando a aba Consulta é ativada, carrega o perfil do CPF preenchido
            def on_consulta_tab_selected(selected_tab, cpf):
                if selected_tab != 1:  # não é a aba Consulta
                    return "(aguardando CPF)"
                if not cpf:
                    return "(aguardando CPF)"
                ok, cpf_or_err = _valid_cpf(cpf)
                if not ok:
                    return "⚠️ CPF inválido"
                profile = get_patient(cpf_or_err)
                if profile:
                    return _profile_text(profile)
                return "❌ Paciente não encontrado"
            
            tabs.select(fn=on_consulta_tab_selected, inputs=[tabs, consult_cpf], outputs=[profile_display])
            
            question_input = gr.Textbox(
                label="Pergunta Clínica",
                placeholder="Ex: Paciente com dores abdominais ao evacuar há 3 semanas. Quais diagnósticos considerar?",
                lines=4,
            )
            consult_btn   = gr.Button("Consultar", variant="primary")
            answer_output = gr.Markdown(label="Resposta do Assistente")

            consult_btn.click(
                fn=run_consult,
                inputs=[consult_cpf, question_input, current_patient],
                outputs=[profile_display, answer_output],
                show_progress="full",
            )

    # ── Eventos Tab 1 ───────────────────────────────────────────────────────
    lookup_btn.click(
        fn=lookup_patient,
        inputs=[cpf_input],
        outputs=[patient_status, new_patient_form, current_patient, consult_cpf, profile_display],
    )

    register_btn.click(
        fn=register_patient,
        inputs=[cpf_input, nome_input, idade_input, sexo_input, peso_input],
        outputs=[patient_status, current_patient, consult_cpf, profile_display, question_input, tabs],
    )

if __name__ == "__main__":
    demo.launch(share=False)
