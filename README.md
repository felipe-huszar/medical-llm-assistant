# Medical LLM Assistant — Tech Challenge Fase 3

Assistente médico com LLM fine-tuned (Mistral via LoRA), orquestrado por **LangGraph** e memória via **ChromaDB**.

## Arquitetura

```
[CPF input]
     ↓
[Nó 1] check_patient    → busca no ChromaDB por CPF
     ↓
[Nó 2] retrieve_history → histórico de consultas
     ↓
[Nó 3] build_prompt     → perfil + histórico + pergunta
     ↓
[Nó 4] llm_reasoning    → MockLLM ou modelo real (Mistral LoRA)
     ↓
[Nó 5] safety_gate      → validação: sem prescrição, confiança, fontes
     ↓
[Nó 6] save_and_format  → salva no ChromaDB + formata resposta
        (ou escalation se falha no safety)
```

## Estrutura de Arquivos

```
src/
├── graph/
│   ├── pipeline.py   ← StateGraph principal
│   ├── nodes.py      ← funções de cada nó
│   └── state.py      ← ClinicalState TypedDict
├── rag/
│   └── patient_rag.py  ← ChromaDB: salvar/buscar pacientes e consultas
├── llm/
│   ├── factory.py    ← MockLLM ou real (via USE_MOCK_LLM)
│   ├── mock_llm.py   ← respostas canned realistas
│   └── model_loader.py ← carrega LoRA do Drive (Colab)
└── safety/
    └── gate.py       ← regras de segurança

data/
└── patients_seed.json  ← 3 pacientes de exemplo

app.py             ← Gradio UI (Tab Paciente + Tab Consulta)
colabs/system_gradio.ipynb ← Colab principal do sistema/Gradio
colabs/            ← Colabs versionados no repo
requirements.txt
```

## Uso Rápido

```bash
# Modo mock (sem GPU)
USE_MOCK_LLM=true python app.py

# Modo real (requer modelo LoRA no Drive)
USE_MOCK_LLM=false MODEL_PATH=/content/drive/MyDrive/medical_llm_lora python app.py
```

## Colab

Abra `colabs/system_gradio.ipynb` no Google Colab e execute as células em ordem.
Para usar o modelo real, defina `USE_MOCK_LLM = 'false'` na célula de config
e certifique-se de que o adapter LoRA está montado no Drive.

### Colabs versionados

- Sistema principal / Gradio:
  - `colabs/system_gradio.ipynb`
  - https://colab.research.google.com/github/felipe-huszar/medical-llm-assistant/blob/main/colabs/system_gradio.ipynb
- Gerador de casos sintéticos:
  - `colabs/gerador_casos_sinteticos.ipynb`
  - https://colab.research.google.com/github/felipe-huszar/medical-llm-assistant/blob/main/colabs/gerador_casos_sinteticos.ipynb
- Fine-tuning Qwen 14B:
  - `colabs/finetuning_qwen14b.ipynb`
  - https://colab.research.google.com/github/felipe-huszar/medical-llm-assistant/blob/main/colabs/finetuning_qwen14b.ipynb

## Safety Gate

- `recommendation_type == "prescription"` → escalação automática  
- `confidence < 0.4` → escalação automática  
- `sources` vazio → resposta inválida → escalação  
- Nunca retorna prescrição direta

## Variáveis de Ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `USE_MOCK_LLM` | `true` | Usar MockLLM em vez do modelo real |
| `MODEL_PATH` | — | Caminho do adapter LoRA (necessário se mock=false) |
| `BASE_MODEL_ID` | `mistralai/Mistral-7B-Instruct-v0.1` | Modelo base HuggingFace |
| `CHROMA_DB_PATH` | `./chroma_db` | Diretório de persistência ChromaDB |
# Notebook atualizado em 2026-03-16T18:48:40Z
