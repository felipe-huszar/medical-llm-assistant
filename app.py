"""
app.py - Gradio UI for the Medical LLM Assistant.

Tab 1: Paciente - CPF lookup / patient registration
Tab 2: Consulta  - Clinical question + LLM response
"""

import os
import re
import gradio as gr

from src.llm.factory import get_llm
from src.rag.patient_rag import get_patient, save_patient, patient_exists, seed_from_file, get_consultation_history
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

COMORBIDADES_OPCOES = [
    "Hipertensão arterial",
    "Diabetes tipo 2",
    "Diabetes tipo 1",
    "Insuficiência cardíaca",
    "Doença coronariana",
    "DPOC",
    "Asma",
    "Insuficiência renal crônica",
    "Hipotireoidismo",
    "Obesidade",
    "Dislipidemia",
    "Fibrilação atrial",
    "AVC prévio",
    "Neoplasia",
    "HIV/AIDS",
    "Hepatite crônica",
    "Cirrose hepática",
    "Lúpus eritematoso",
    "Artrite reumatoide",
]


def _profile_text(profile: dict) -> str:
    if not profile:
        return "(nenhum paciente carregado)"
    comorbidades = profile.get("comorbidades", [])
    comorbidades_str = (
        f"\n**Comorbidades:** {', '.join(comorbidades)}" if comorbidades else ""
    )
    return (
        f"**Nome:** {profile.get('nome', 'N/A')}  "
        f"**Idade:** {profile.get('idade', 'N/A')} anos  "
        f"**Sexo:** {profile.get('sexo', 'N/A')}  "
        f"**Peso:** {profile.get('peso', 'N/A')} kg"
        f"{comorbidades_str}"
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


def register_patient(cpf: str, nome: str, idade, sexo: str, peso,
                     comorbidades_check: list, comorbidades_other: str):
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

    # Combina checkboxes + campo livre (split por vírgula)
    comorbidades = list(comorbidades_check or [])
    for item in (comorbidades_other or "").split(","):
        item = item.strip()
        if item and item not in comorbidades:
            comorbidades.append(item)

    profile = {
        "cpf": cpf,
        "nome": nome.strip(),
        "idade": idade_val,
        "sexo": sexo.strip().upper(),
        "peso": peso_val,
        "comorbidades": comorbidades,
    }

    save_patient(cpf, profile)
    return (
        f"✅ Paciente **{nome}** cadastrado com sucesso.",
        profile,
        cpf,
        _profile_text(profile),
        "",
        gr.update(selected=1),
        "",
    )


# ---------------------------------------------------------------------------
# Helpers compartilhados
# ---------------------------------------------------------------------------

def _get_history_questions(cpf: str) -> list:
    """Retorna lista de tuplas (display, pergunta_completa) para o dropdown de histórico."""
    entries = get_consultation_history(cpf, n_results=5)
    if not entries:
        return []
    
    questions = []
    for entry in reversed(entries):
        entry_str = str(entry) if not isinstance(entry, str) else entry
        # Procura por "Pergunta:" ou usa a primeira linha como fallback
        q = None
        for line in entry_str.split("\n"):
            line = line.strip()
            if line.startswith("Pergunta:"):
                q = line.replace("Pergunta:", "").strip()
                break
            elif line.startswith("Sintomas:") or line.startswith("sintomas:"):
                q = line.replace("Sintomas:", "").replace("sintomas:", "").strip()
                break
        
        # Se não encontrou padrão, usa a entrada completa (limitada)
        if not q:
            q = entry_str[:200] if len(entry_str) > 200 else entry_str
        
        if q:
            # Trunca para exibir no dropdown
            display = q[:60] + "..." if len(q) > 60 else q
            questions.append((display, q))
    
    return questions


def _format_history_md(cpf: str) -> str:
    """Formata as últimas consultas do ChromaDB como Markdown para o accordion."""
    entries = get_consultation_history(cpf, n_results=5)
    if not entries:
        return "*(sem consultas anteriores registradas)*"
    lines = []
    for i, entry in enumerate(reversed(entries), 1):
        for line in entry.split("\n"):
            if line.startswith("Pergunta:"):
                q = line.replace("Pergunta:", "").strip()
                lines.append(f"**Consulta {i}:** {q}")
                break
    return "\n\n".join(lines) if lines else "*(sem consultas anteriores registradas)*"


# ---------------------------------------------------------------------------
# Tab 2: Consulta
# ---------------------------------------------------------------------------

_LOADING_STAGES = [
    (0.15, "🔍 Buscando dados do paciente..."),
    (0.35, "🧠 Construindo contexto clínico..."),
    (0.60, "⚕️ Analisando com o modelo..."),
    (0.85, "🛡️ Validando resposta..."),
]

def run_consult(cpf: str, question: str, selected_history: list[str] | None,
                current_patient: dict | None, progress=gr.Progress(track_tqdm=False)):
    if not cpf or not cpf.strip():
        yield "", "⚠️ **CPF não informado.** Digite o CPF e clique em Carregar Paciente.", ""
        return
    ok, cpf_or_err = _valid_cpf(cpf)
    if not ok:
        yield "", f"⚠️ {cpf_or_err}", ""
        return
    cpf = cpf_or_err

    profile = get_patient(cpf)
    if not profile:
        yield "", f"❌ CPF **{cpf}** não encontrado. Registre o paciente na aba **👤 Paciente** primeiro.", ""
        return

    if not question.strip():
        yield _profile_text(profile), "⚠️ Informe uma pergunta clínica.", ""
        return

    # Etapas de progresso visíveis no topo da tela (progress bar nativa do Gradio)
    for pct, label in _LOADING_STAGES[:-1]:
        progress(pct, desc=label)

    try:
        result = run_consultation(
            cpf=cpf,
            doctor_question=question,
            llm=_get_llm(),
            patient_profile=profile,
            selected_history=selected_history or [],
        )
        progress(0.95, desc="🛡️ Validando resposta...")
        history_md = _format_history_md(cpf)
        progress(1.0, desc="✅ Concluído")
        yield (
            _profile_text(result.get("patient_profile", profile)),
            result.get("final_answer", "Sem resposta."),
            history_md,
        )
    except Exception as e:
        yield "", f"❌ Erro durante a consulta: {e}", ""


# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------


_CSS = """
.gradio-container { max-width: 1200px !important; margin: 0 auto; }
.tabitem { padding: 20px !important; }
.generating { margin-top: 24px !important; }
.progress-bar-wrap { margin-top: 20px !important; margin-bottom: 8px !important; }
.eta-bar { margin-top: 20px !important; }
/* Evita width jump durante loading */
#answer-output { min-height: 80px; }
#profile-display { min-height: 40px; }
"""

with gr.Blocks(title="Medical LLM Assistant") as demo:
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
                with gr.Row():
                    nome_input  = gr.Textbox(label="Nome completo", scale=3)
                    sexo_input  = gr.Radio(["M", "F"], label="Sexo", value="M", scale=1)
                with gr.Row():
                    idade_input = gr.Number(label="Idade (anos)", precision=0, minimum=0, scale=1)
                    peso_input  = gr.Number(label="Peso (kg)", precision=1, minimum=0, scale=1)
                gr.Markdown("**Comorbidades** *(condições crônicas — ficam no histórico permanente do paciente)*")
                comorbidades_check = gr.CheckboxGroup(
                    choices=COMORBIDADES_OPCOES,
                    label="",
                    value=[],
                )
                comorbidades_other = gr.Textbox(
                    label="Outras comorbidades (separadas por vírgula)",
                    placeholder="Ex: epilepsia, doença de Crohn",
                    max_lines=1,
                )
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
                "ou registre na aba **👤 Paciente** primeiro.",
                elem_id="profile-display",
            )

            with gr.Accordion("📋 Histórico de consultas anteriores", open=False) as history_accordion:
                history_display = gr.Markdown("*(carregue um paciente para ver o histórico)*")
                
                # Dropdown para selecionar pergunta anterior
                history_dropdown = gr.Dropdown(
                    label="↪️ Consultas anteriores para adicionar ao histórico da análise",
                    choices=[],
                    value=[],
                    multiselect=True,
                    interactive=True,
                    visible=False,
                )
                use_history_btn = gr.Button("↪️ Usar esta pergunta", variant="secondary", visible=False)

            question_input = gr.Textbox(
                label="Pergunta Clínica",
                placeholder="Ex: Paciente com dores abdominais ao evacuar há 3 semanas. Quais diagnósticos considerar?",
                lines=4,
            )
            consult_btn   = gr.Button("🔬 Consultar", variant="primary", size="lg")
            answer_output = gr.Markdown("", elem_id="answer-output")

    # ── Botão Carregar Paciente (aba Consulta) ──────────────────────────────
    def load_patient_for_consult(cpf: str):
        ok, cpf_or_err = _valid_cpf(cpf)
        if not ok:
            return (
                "⚠️ CPF inválido — deve ter 11 dígitos.", cpf_or_err, "", "",
                gr.update(visible=False, choices=[], value=[]),
                gr.update(visible=False),
            )
        profile = get_patient(cpf_or_err)
        if not profile:
            return (
                f"❌ Paciente **{cpf_or_err}** não encontrado.\n\n"
                "👉 Registre o paciente na aba **👤 Paciente** antes de consultar.",
                cpf_or_err, "", "",
                gr.update(visible=False, choices=[], value=[]),
                gr.update(visible=False),
            )
        history_md = _format_history_md(cpf_or_err)
        history_questions = _get_history_questions(cpf_or_err)

        if history_questions:
            return (
                _profile_text(profile), cpf_or_err, history_md, "",
                gr.update(visible=True, choices=history_questions, value=[]),
                gr.update(visible=False),
            )
        else:
            return (
                _profile_text(profile), cpf_or_err, history_md, "",
                gr.update(visible=False, choices=[], value=[]),
                gr.update(visible=False),
            )

    load_patient_btn.click(
        fn=load_patient_for_consult,
        inputs=[consult_cpf],
        outputs=[profile_display, consult_cpf, history_display, answer_output,
                 history_dropdown, use_history_btn],
        show_progress="hidden",
    )

    # ── Consulta ────────────────────────────────────────────────────────────
    consult_btn.click(
        fn=run_consult,
        inputs=[consult_cpf, question_input, history_dropdown, current_patient],
        outputs=[profile_display, answer_output, history_display],
        show_progress="full",
    )

    # ── Eventos Tab 1 ───────────────────────────────────────────────────────
    def lookup_patient_with_loading(cpf: str):
        """Wrapper com estado de loading para busca de paciente.
        Outputs: patient_status, new_patient_form, current_patient, consult_cpf, profile_display
        """
        yield "⏳ Buscando paciente...", gr.update(visible=False), None, "", ""
        r = lookup_patient(cpf)
        yield r[0], r[1], r[2], r[3], r[4]

    lookup_btn.click(
        fn=lookup_patient_with_loading,
        inputs=[cpf_input],
        outputs=[patient_status, new_patient_form, current_patient, consult_cpf, profile_display],
        show_progress="hidden",
    )

    def register_patient_with_loading(cpf, nome, idade, sexo, peso,
                                       comorbidades_check, comorbidades_other):
        """Wrapper com estado de loading para cadastro.
        Outputs: patient_status, current_patient, consult_cpf, profile_display,
                 question_input, tabs, answer_output
        """
        yield "⏳ Cadastrando paciente...", None, "", "", "", gr.update(selected=0), ""
        r = register_patient(cpf, nome, idade, sexo, peso,
                              comorbidades_check, comorbidades_other)
        yield r[0], r[1], r[2], r[3], r[4], r[5], r[6]

    register_btn.click(
        fn=register_patient_with_loading,
        inputs=[cpf_input, nome_input, idade_input, sexo_input, peso_input,
                comorbidades_check, comorbidades_other],
        outputs=[patient_status, current_patient, consult_cpf, profile_display,
                 question_input, tabs, answer_output],
        show_progress="hidden",
    )

if __name__ == "__main__":
    demo.queue().launch(
        share=False,
        theme=gr.themes.Soft(),
        css=_CSS,
    )
