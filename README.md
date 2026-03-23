# Medical LLM Assistant — Especialista em Cardiologia
## Tech Challenge Fase 3 — Branch `cardio-specialist`

Versão especializada do assistente médico, fine-tuned exclusivamente com dados de **cardiologia**.

> **Equipe:** Felipe Huszar · Lucas Janzen  
> Para o sistema clínico geral, veja a branch [`main`](https://github.com/felipe-huszar/medical-llm-assistant/tree/main).

---

## Sobre esta Branch

Esta versão explora a hipótese de **especialização de domínio**: um modelo treinado exclusivamente em casos cardiológicos oferece maior precisão dentro do domínio ao custo de não lidar com outras especialidades.

**Modelo:** Qwen 2.5 14B + LoRA, dataset focado em cardiologia  
**Diferenças do generalista:**
- Dataset de treino filtrado para casos cardíacos (SCA, FA, IC, HAS, dissecção aórtica, TEP, etc.)
- Guardrail de escopo: casos não-cardiológicos são encaminhados para especialista
- Safety gate adaptado para o contexto cardíaco

---

## Resultados Comparativos (Benchmark 100 casos)

| Categoria | Generalista | Especialista Cardio |
|-----------|-------------|---------------------|
| Core cardiológico (10 casos) | 52% | **70%** |
| Safety gate (prescrição direta) | **100%** | 20% |
| Abstention / dados vagos | **100%** | 0% |
| Fora de escopo | **100%** | ~30% |

**Conclusão:** especialização melhora acurácia no domínio, mas enfraquece as camadas de segurança. O dataset de treino do especialista precisa incluir mais exemplos de recusa/abstention para equilibrar os trade-offs.

---

## Arquitetura

Mesma pipeline LangGraph de 7 nós da branch `main`. Ver [diagrama completo](docs/).

---

## Estrutura

```
app.py                              ← Gradio UI adaptado para cardiologia
requirements.txt

colabs/specialist/
├── system_gradio.ipynb             ← Colab do sistema especialista
├── finetuning_cardio_specialist.ipynb  ← Fine-tuning cardiologia
└── gerador_casos_cardio_specialist.ipynb ← Gerador de casos cardíacos

src/                                ← Pipeline (idêntico ao main)
tests/                              ← Testes
data/patients_seed.json
```

---

## Como Executar

### Colab (modelo real)

Abra `colabs/specialist/system_gradio.ipynb` no Google Colab:

[Abrir no Colab](https://colab.research.google.com/github/felipe-huszar/medical-llm-assistant/blob/cardio-specialist/colabs/specialist/system_gradio.ipynb)

### Local (MockLLM)

```bash
pip install -r requirements.txt
USE_MOCK_LLM=true python app.py
```

---

## Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `USE_MOCK_LLM` | `true` | Usar MockLLM em vez do modelo real |
| `MODEL_PATH` | — | Caminho do adapter LoRA cardíaco |
| `BASE_MODEL_ID` | `Qwen/Qwen2.5-14B-Instruct` | Modelo base |
| `CHROMA_DB_PATH` | `./chroma_db` | Persistência ChromaDB |
