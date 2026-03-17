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
# Para injetar o modelo já carregado do notebook: app._llm = seu_modelo
_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        _llm = get_llm()
    return _llm


def set_llm(model):
    """Injeta LLM já carregado — atualiza tanto o cache local quanto o da factory."""
    global _llm
    _llm = model
    # Propaga para o cache da factory para evitar duplo carregamento
    import src.llm.factory as _factory
    _factory._cached_llm = model


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
        return cpf_or_err, None, "", "", "", gr.update(selected=0), ""
    cpf = cpf_or_err

    if not nome.strip():
        return "❌ Nome é obrigatório.", None, "", "", "", gr.update(selected=0), ""

    try:
        idade_val = int(idade or 0)
        peso_val  = float(peso or 0)
    except (ValueError, TypeError) as e:
        return f"❌ Dados inválidos: {e}", None, "", "", "", gr.update(selected=0), ""

    if not (0 < idade_val <= 150):
        return "❌ Idade deve ser entre 1 e 150.", None, "", "", "", gr.update(selected=0), ""
    if not (0 < peso_val <= 500):
        return "❌ Peso deve ser entre 1 e 500 kg.", None, "", "", "", gr.update(selected=0), ""

    profile = {
        "cpf": cpf,
        "nome": nome.strip(),
        "idade": idade_val,
        "sexo": sexo.strip().upper(),
        "peso": peso_val,
    }

    save_patient(cpf, profile)
    return (
        f"✅ Paciente **{nome}** cadastrado com sucesso.",
        profile,
        cpf,                     # pre-preenche CPF na aba Consulta
        _profile_text(profile),  # profile_display
        "",                      # limpa pergunta anterior
        gr.update(selected=1),   # navega para aba Consulta
        "",                      # limpa answer_output
    )


# ---------------------------------------------------------------------------
# Tab 2: Consulta
# ---------------------------------------------------------------------------

def run_consult(cpf: str, question: str, current_patient: dict | None):
    if not cpf or not cpf.strip():
        yield "", "⚠️ **CPF não informado.** Digite o CPF do paciente e clique em Carregar Paciente antes de consultar."
        return
    ok, cpf_or_err = _valid_cpf(cpf)
    if not ok:
        yield "", f"⚠️ {cpf_or_err}"
        return
    cpf = cpf_or_err

    # Sempre busca direto no DB pelo CPF digitado
    profile = get_patient(cpf)
    if not profile:
        yield "", f"❌ CPF **{cpf}** não encontrado. Registre o paciente na aba **👤 Paciente** primeiro."
        return

    if not question.strip():
        yield _profile_text(profile), "⚠️ Informe uma pergunta clínica."
        return

    # Mostra loading imediatamente
    yield _profile_text(profile), "⏳ **Analisando caso clínico...** Isso pode levar 20-30 segundos."

    try:
        result = run_consultation(
            cpf=cpf,
            doctor_question=question,
            llm=_get_llm(),
            patient_profile=profile,
        )
        yield _profile_text(result.get("patient_profile", profile)), result.get("final_answer", "Sem resposta.")
    except Exception as e:
        yield "", f"❌ Erro durante a consulta: {e}"


# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------


with gr.Blocks(title="Medical LLM Assistant", theme=gr.themes.Soft(), css="""
.gradio-container { max-width: 1200px !important; margin: 0 auto; }
.tabitem { padding: 20px !important; }
.generating { margin-top: 24px !important; }
.progress-bar-wrap { margin-top: 20px !important; margin-bottom: 8px !important; }
.eta-bar { margin-top: 20px !important; }
""") as demo:
    gr.Markdown("# 🏥 Medical LLM Assistant\nAssistente clínico com IA — diagnósticos e exames recomendados.")

    current_patient = gr.State(None)

    with gr.Tabs() as tabs:

        # ── Tab 1: Paciente ─────────────────────────────────────────────────
        with gr.Tab("👤 Paciente", id=0):
            cpf_input = gr.Textbox(
                label="CPF do Paciente",
                placeholder="Ex: 123.456.789-00",
                max_lines=1,
            )
            lookup_btn = gr.Button("🔍 Buscar Paciente", variant="primary")
            patient_status = gr.Markdown("")

            with gr.Group(visible=False) as new_patient_form:
                gr.Markdown("### Cadastrar Novo Paciente")
                nome_input  = gr.Textbox(label="Nome completo")
                idade_input = gr.Number(label="Idade (anos)", precision=0, minimum=0)
                sexo_input  = gr.Radio(["M", "F"], label="Sexo", value="M")
                peso_input  = gr.Number(label="Peso (kg)", precision=1, minimum=0)
                register_btn = gr.Button("✅ Registrar Paciente", variant="secondary")

        # ── Tab 2: Consulta ─────────────────────────────────────────────────
        with gr.Tab("🩺 Consulta", id=1):
            gr.Markdown("### Realizar Consulta Clínica")
            with gr.Row():
                consult_cpf = gr.Textbox(
                    label="CPF do Paciente",
                    placeholder="Ex: 123.456.789-00",
                    max_lines=1,
                    scale=3,
                )
                load_patient_btn = gr.Button("👤 Carregar Paciente", scale=1)

            profile_display = gr.Markdown(
                "ℹ️ **Nenhum paciente carregado.** Digite o CPF e clique em **Carregar Paciente** — "
                "ou registre na aba **👤 Paciente** primeiro."
            )

            question_input = gr.Textbox(
                label="Pergunta Clínica",
                placeholder="Ex: Paciente com dores abdominais ao evacuar há 3 semanas. Quais diagnósticos considerar?",
                lines=4,
            )
            consult_btn   = gr.Button("🔬 Consultar", variant="primary", size="lg")
            answer_output = gr.Markdown("")

    # ── Botão Carregar Paciente (aba Consulta) ──────────────────────────────
    def load_patient_for_consult(cpf: str):
        ok, cpf_or_err = _valid_cpf(cpf)
        if not ok:
            return "⚠️ CPF inválido — deve ter 11 dígitos.", cpf_or_err, ""
        profile = get_patient(cpf_or_err)
        if not profile:
            return (
                f"❌ Paciente **{cpf_or_err}** não encontrado.\n\n"
                "👉 Registre o paciente na aba **👤 Paciente** antes de consultar.",
                cpf_or_err,
                "",
            )
        # Paciente encontrado: limpa answer_output antigo
        return _profile_text(profile), cpf_or_err, ""

    load_patient_btn.click(
        fn=load_patient_for_consult,
        inputs=[consult_cpf],
        outputs=[profile_display, consult_cpf, answer_output],
    )

    # ── Consulta ────────────────────────────────────────────────────────────
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
        outputs=[patient_status, current_patient, consult_cpf, profile_display, question_input, tabs, answer_output],
    )

if __name__ == "__main__":
    demo.queue().launch(share=False)
