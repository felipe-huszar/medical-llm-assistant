"""
tests/ui/test_gradio_ui.py - Testes automatizados de UI via Playwright (headless).

Requer servidor rodando em BASE_URL antes de executar:
    USE_MOCK_LLM=true CHROMA_DB_PATH=/tmp/chroma_uitest python3 -m app_server

Cenários:
  TC-UI-01: Busca de paciente existente → perfil carrega na aba consulta
  TC-UI-02: Busca de CPF inexistente → formulário de cadastro aparece
  TC-UI-03: CPF inválido → mensagem de erro
  TC-UI-04: Cadastro de novo paciente → navega para consulta com CPF preenchido
  TC-UI-05: Consulta sem pergunta → aviso
  TC-UI-06: Consulta válida → resposta com seções Markdown
  TC-UI-07: CPF não cadastrado direto na aba consulta → erro claro
  TC-UI-08: Resposta contém seções esperadas
  TC-UI-09: Aviso médico presente
  TC-UI-10: Navegar entre abas não perde CPF
"""

import pytest
from playwright.sync_api import sync_playwright, Page, expect

import os
BASE_URL = os.environ.get("GRADIO_TEST_URL", "http://172.20.0.3:7860")


@pytest.fixture(scope="module")
def browser_ctx():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()
        yield ctx
        ctx.close()
        browser.close()


@pytest.fixture
def page(browser_ctx):
    pg = browser_ctx.new_page()
    pg.goto(BASE_URL, wait_until="domcontentloaded", timeout=15000)
    pg.wait_for_timeout(2000)  # aguarda Gradio montar os componentes
    yield pg
    pg.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fill_cpf_tab1(page: Page, cpf: str):
    """Preenche CPF na aba Paciente."""
    tab1_input = page.locator("input").first
    tab1_input.fill("")
    tab1_input.fill(cpf)


def click_buscar(page: Page):
    page.get_by_role("button", name="Buscar Paciente").click()
    page.wait_for_timeout(2000)


def go_consulta(page: Page):
    page.get_by_role("tab", name="🩺 Consulta").click()
    page.wait_for_timeout(800)


def go_paciente(page: Page):
    page.get_by_role("tab", name="👤 Paciente").click()
    page.wait_for_timeout(800)


def do_consulta(page: Page, cpf: str, question: str, timeout: int = 5000):
    go_consulta(page)
    inputs = page.locator("input")
    inputs.last.fill(cpf)
    page.locator("textarea").fill(question)
    page.get_by_role("button", name="Consultar").click()
    page.wait_for_timeout(timeout)


# ---------------------------------------------------------------------------
# TC-UI-01: Paciente existente
# ---------------------------------------------------------------------------

class TestLookup:
    def test_01a_existing_patient_shows_found_message(self, page):
        fill_cpf_tab1(page, "12345678900")
        click_buscar(page)
        assert "encontrado" in page.content().lower(), \
            "Mensagem 'Paciente encontrado' não apareceu"

    def test_01b_profile_visible_in_consulta(self, page):
        fill_cpf_tab1(page, "12345678900")
        click_buscar(page)
        go_consulta(page)
        content = page.content()
        assert "Maria" in content or "123.456.789-00" in content, \
            "Perfil da paciente não aparece na aba consulta após lookup"

    def test_01c_no_aguardando_cpf_after_lookup(self, page):
        fill_cpf_tab1(page, "12345678900")
        click_buscar(page)
        go_consulta(page)
        assert "(aguardando CPF)" not in page.content(), \
            "Texto '(aguardando CPF)' persiste após lookup bem-sucedido"

    def test_02_unknown_cpf_shows_registration_form(self, page):
        fill_cpf_tab1(page, "88877766655")
        click_buscar(page)
        assert "Cadastrar Novo Paciente" in page.content(), \
            "Formulário de cadastro não apareceu para CPF desconhecido"

    def test_03a_cpf_too_short_shows_error(self, page):
        fill_cpf_tab1(page, "123")
        click_buscar(page)
        content = page.content()
        assert "11" in content or "inválido" in content.lower(), \
            "Erro para CPF curto não apareceu"

    def test_03b_cpf_empty_shows_error(self, page):
        fill_cpf_tab1(page, "   ")
        click_buscar(page)
        page.wait_for_timeout(1000)
        content = page.content()
        assert "11" in content or "inválido" in content.lower() or "CPF" in content, \
            "Erro para CPF vazio não apareceu"


# ---------------------------------------------------------------------------
# TC-UI-04: Cadastro
# ---------------------------------------------------------------------------

class TestRegister:
    def test_04a_register_navigates_to_consulta(self, page):
        fill_cpf_tab1(page, "33322211100")
        click_buscar(page)
        page.wait_for_timeout(500)

        inputs = page.locator("input")
        # Nome (2º input visível)
        inputs.nth(1).fill("Paciente Teste UI")
        # Idade e peso (campos number)
        page.locator("input[type='number']").first.fill("40")
        page.locator("input[type='number']").last.fill("75")
        page.get_by_role("button", name="Registrar Paciente").click()
        page.wait_for_timeout(2000)

        active = page.locator("[aria-selected='true']").first.inner_text()
        assert "Consulta" in active, \
            f"Não navegou para aba Consulta após cadastro. Tab ativa: '{active}'"

    def test_04b_cpf_prefilled_after_register(self, page):
        fill_cpf_tab1(page, "22211100099")
        click_buscar(page)
        page.wait_for_timeout(500)

        page.locator("input").nth(1).fill("Segundo Paciente")
        page.locator("input[type='number']").first.fill("35")
        page.locator("input[type='number']").last.fill("65")
        page.get_by_role("button", name="Registrar Paciente").click()
        page.wait_for_timeout(2000)

        content = page.content()
        assert "222.111.000-99" in content or "22211100099" in content, \
            "CPF não pré-preenchido na aba consulta após cadastro"


# ---------------------------------------------------------------------------
# TC-UI-05 a 10: Consulta
# ---------------------------------------------------------------------------

class TestConsulta:
    def test_05_consult_without_question_shows_warning(self, page):
        go_consulta(page)
        page.locator("input").last.fill("123.456.789-00")
        # Não preenche textarea
        page.get_by_role("button", name="Consultar").click()
        page.wait_for_timeout(2000)
        content = page.content()
        assert "pergunta" in content.lower() or "Informe" in content, \
            "Aviso de pergunta obrigatória ausente"

    def test_06_valid_consult_returns_analysis(self, page):
        fill_cpf_tab1(page, "12345678900")
        click_buscar(page)
        do_consulta(page, "123.456.789-00",
                    "Paciente com cefaleia intensa há 2 dias e fotofobia.")
        assert "Análise Clínica" in page.content(), \
            "Título 'Análise Clínica' ausente na resposta"

    def test_07_unknown_cpf_direct_in_consulta_shows_error(self, page):
        go_consulta(page)
        page.locator("input").last.fill("00000000000")
        page.locator("textarea").fill("Qualquer pergunta")
        page.get_by_role("button", name="Consultar").click()
        page.wait_for_timeout(3000)
        content = page.content()
        assert "não cadastrado" in content.lower() or "não encontrado" in content.lower(), \
            "Erro de paciente não encontrado ausente"

    def test_08_response_has_expected_sections(self, page):
        fill_cpf_tab1(page, "12345678900")
        click_buscar(page)
        do_consulta(page, "123.456.789-00",
                    "Dor abdominal intensa após refeições gordurosas há 1 semana.")
        content = page.content()
        missing = [s for s in ["Diagnósticos", "Exames", "Raciocínio"] if s not in content]
        assert not missing, f"Seções ausentes na resposta: {missing}"

    def test_09_response_has_medical_disclaimer(self, page):
        fill_cpf_tab1(page, "12345678900")
        click_buscar(page)
        do_consulta(page, "123.456.789-00",
                    "Paciente com febre alta e calafrios há 48h.")
        content = page.content()
        assert "orientativa" in content.lower() or "responsabilidade" in content.lower(), \
            "Aviso médico obrigatório ausente na resposta"

    def test_10_tab_navigation_keeps_cpf(self, page):
        fill_cpf_tab1(page, "12345678900")
        click_buscar(page)
        page.wait_for_timeout(800)
        go_consulta(page)
        go_paciente(page)
        go_consulta(page)
        content = page.content()
        assert "123.456.789-00" in content or "12345678900" in content, \
            "CPF perdido ao navegar entre abas"
