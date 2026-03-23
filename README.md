# Medical LLM Assistant — Tech Challenge Fase 3

Assistente médico virtual com **LLM fine-tuned** (Qwen 2.5 14B + LoRA), orquestrado por **LangGraph** e memória contextual via **ChromaDB**.

> **Equipe:** Felipe Huszar · Lucas Janzen · Rodrigo Felizardo · Victor Henrique · Victor Souza  
> **Disciplinas:** Pós-Tech IA para Devs — FIAP

---

## Visão Geral

O sistema auxilia médicos em condutas clínicas com respostas contextualizadas pelo perfil do paciente. Possui duas versões:

- **`main`** — Assistente clínico geral (Qwen 2.5 14B LoRA, treinado em múltiplas especialidades)
- **`cardio-specialist`** — Especialista em cardiologia (dataset e fine-tuning focados em cardio)

---

## Arquitetura — Pipeline LangGraph (7 nós)

```
[CPF + Pergunta Médica]
         ↓
[Nó 1] check_patient      → verifica CPF no ChromaDB, carrega perfil
         ↓
[Nó 2] retrieve_history   → histórico de consultas (opt-in pelo médico)
         ↓
[Nó 3] build_prompt       → monta contexto clínico estruturado
         ↓
[Nó 4] llm_reasoning      → Qwen 14B LoRA (ou MockLLM em dev)
         ↓
[Nó 5] safety_gate        → 6 camadas de validação independentes do LLM
         ↓
    [Aprovado?]
    ├── Sim → [Nó 6] save_and_format  → salva + formata resposta ao médico
    └── Não → [Nó 7] escalation       → aviso para revisão especializada
```

---

## Safety Gate — 6 camadas

O gate é **independente do LLM** — valida a resposta após a inferência:

| Camada | Regra |
|--------|-------|
| 1 | Resposta mínima — rejeita respostas < 80 caracteres |
| 2 | **Prescrição direta** — bloqueia qualquer padrão de posologia/prescrição |
| 3 | Consistência de status — insufficient_data + diagnóstico grave = inválido |
| 4 | Evidência mínima — hipóteses graves exigem marcadores clínicos presentes |
| 5 | Abstention — queixas sem discriminadores → pede mais dados |
| 6 | Anti-alucinação — impede referência a histórico não fornecido |

---

## Estrutura do Projeto

```
app.py                          ← Gradio UI (Aba Paciente + Aba Consulta)
requirements.txt
pytest.ini

src/
├── graph/
│   ├── pipeline.py             ← StateGraph LangGraph principal
│   ├── nodes.py                ← implementação de cada nó
│   └── state.py                ← ClinicalState TypedDict
├── rag/
│   └── patient_rag.py          ← ChromaDB: perfis e histórico de consultas
├── llm/
│   ├── factory.py              ← roteamento MockLLM / modelo real
│   ├── mock_llm.py             ← respostas realistas para desenvolvimento
│   └── model_loader.py         ← carrega adapter LoRA do Google Drive
├── safety/
│   └── gate.py                 ← safety gate multicamada
└── audit/
    └── logger.py               ← audit_log.jsonl por evento

colabs/
├── system_gradio.ipynb         ← sistema principal + Gradio (Colab)
├── finetuning.ipynb            ← fine-tuning Qwen 14B com LoRA
└── gerador_casos_sinteticos.ipynb ← gerador de dataset sintético

data/
└── patients_seed.json          ← 3 pacientes de exemplo

docs/
├── relatorio_tecnico.md        ← relatório técnico completo
├── diagrama_pipeline.md        ← diagramas Mermaid do LangGraph
└── benchmark_100.json          ← resultados do benchmark (100 casos)

scripts/
└── run_benchmark_100.py        ← script de avaliação automática (100 casos)

tests/
├── unit/                       ← testes unitários por módulo
├── integration/                ← testes de integração do pipeline
├── e2e/                        ← testes end-to-end
└── ui/                         ← testes da interface Gradio
```

---

## Como Executar

### Desenvolvimento local (MockLLM, sem GPU)

```bash
pip install -r requirements.txt
USE_MOCK_LLM=true python app.py
```

Acesse em `http://localhost:7860`

### Produção (modelo real, Google Colab + GPU)

1. Abra `colabs/system_gradio.ipynb` no Google Colab
2. Execute as células em ordem (a célula de dependências pode precisar de 2 execuções)
3. Defina `USE_MOCK_LLM = 'false'` na célula de configuração
4. Aguarde a URL `gradio.live` aparecer

**Links diretos:**

| Colab | Link |
|-------|------|
| Sistema + Gradio | [Abrir no Colab](https://colab.research.google.com/github/felipe-huszar/medical-llm-assistant/blob/main/colabs/system_gradio.ipynb) |
| Fine-tuning Qwen 14B | [Abrir no Colab](https://colab.research.google.com/github/felipe-huszar/medical-llm-assistant/blob/main/colabs/finetuning.ipynb) |
| Gerador de Dataset | [Abrir no Colab](https://colab.research.google.com/github/felipe-huszar/medical-llm-assistant/blob/main/colabs/gerador_casos_sinteticos.ipynb) |

---

## Testes

```bash
# Todos os testes
pytest

# Por módulo
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/
```

> 95 testes passando. Testes de UI requerem Gradio ativo (`USE_MOCK_LLM=true python app.py`).

---

## Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `USE_MOCK_LLM` | `true` | Usar MockLLM em vez do modelo real |
| `MODEL_PATH` | — | Caminho do adapter LoRA (Colab Drive) |
| `BASE_MODEL_ID` | `Qwen/Qwen2.5-14B-Instruct` | Modelo base HuggingFace |
| `CHROMA_DB_PATH` | `./chroma_db` | Diretório de persistência ChromaDB |

---

## Resultados — Benchmark (100 casos)

Avaliação com modelo real (Qwen 14B LoRA) em ambiente Colab:

| Categoria | Casos | Resultado |
|-----------|-------|-----------|
| 🛡️ Safety gate (prescrição direta) | 10 | **100%** |
| 🚫 Fora de escopo | 10 | **100%** |
| 🤷 Dados insuficientes | 20 | **100%** |
| 🩺 Hipótese clínica | 40 válidos | **52%** (keyword matching conservador) |

> Acurácia clínica estimada real: **68–75%** descontando false escalations do safety gate.  
> Ver análise completa em `docs/relatorio_tecnico.md`.

---

## Documentação

- [Relatório Técnico](docs/relatorio_tecnico.md) — fine-tuning, arquitetura, avaliação
- [Diagrama LangGraph](docs/diagrama_pipeline.md) — fluxo completo em Mermaid
- [Resultados do Benchmark](docs/benchmark_100.json) — 100 casos com entradas e saídas
