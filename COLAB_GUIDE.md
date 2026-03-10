# 🏥 Medical LLM Assistant - Guia Colab

## 📥 Download do Notebook

O notebook está pronto em dois arquivos:
1. `notebook.ipynb` - Versão principal
2. `Medical_LLM_Assistant_Colab.ipynb` - Versão alternativa

## 🚀 Como Usar no Google Colab

### Opção 1: Upload Direto
1. Baixe o arquivo `notebook.ipynb` do repositório
2. Acesse [colab.research.google.com](https://colab.research.google.com)
3. Clique em **Upload** e selecione o arquivo
4. Execute as células em ordem

### Opção 2: Abrir do GitHub
1. Acesse [colab.research.google.com/github](https://colab.research.google.com/github)
2. Cole a URL do repositório: `https://github.com/felipe-huszar/tech-challenge-fase3`
3. Selecione o arquivo `notebook.ipynb`

## 📋 Estrutura do Notebook

O notebook contém **6 seções principais**:

| Seção | Descrição | Tempo Est. |
|-------|-----------|------------|
| 1. Clone | Baixa o repositório | 10s |
| 2. Dependências | Instala pacotes | 2-3 min |
| 3. Configuração | Define variáveis | 10s |
| 4. Testes | Executa ~78 testes | 2-3 min |
| 5. Demonstração | 4 cenários clínicos | 30s |
| 6. Interface Gradio | UI completa | Contínuo |

## 🔧 Configuração

### Modo MockLLM (Recomendado para testes)
```python
os.environ['USE_MOCK_LLM'] = 'true'
```
- ✅ Rápido (sem GPU)
- ✅ Respostas determinísticas
- ✅ Ideal para validar pipeline

### Modo Modelo Real (Requer GPU)
```python
os.environ['USE_MOCK_LLM'] = 'false'
os.environ['MODEL_PATH'] = '/content/drive/MyDrive/medical_llm_lora'
```
- Requer GPU T4 ou superior
- Requer LoRA adapter no Google Drive
- Mais lento mas respostas reais

## 🧪 Testes Incluídos

```
📊 COBERTURA DE TESTES
============================================================
Unit Tests (Safety Gate)..................  13 testes
Integration Tests (Pipeline)..............  12 testes
E2E - Core Journeys.......................  10 testes
E2E - Pipeline............................  11 testes
E2E - Extended............................  32 testes
------------------------------------------------------------
TOTAL.....................................  78 testes
============================================================
```

## 🩺 Cenários de Demonstração

1. **GI Symptoms**: Dor abdominal + sangue nas fezes
2. **Follow-up**: Retorno com histórico de colonoscopia
3. **Cardio**: Dor torácica + ECG alterado
4. **Safety Test**: Tentativa de prescrição (deve ser bloqueada)

## 🖥️ Interface Gradio

A UI tem 2 abas:
- **👤 Paciente**: Busca/Cadastro por CPF
- **🩺 Consulta**: Pergunta clínica + resposta da IA

## ⚡ Dicas

- Use **Runtime > Change runtime type > GPU** se for usar modelo real
- Os testes rodam em ~2 minutos no modo MockLLM
- ChromaDB é persistido em `/content/chroma_db` (temporário)
- Para persistir dados, monte o Drive e ajuste `CHROMA_DB_PATH`

## 🐛 Troubleshooting

| Problema | Solução |
|----------|---------|
| ImportError | Reexecute célula 2 (dependências) |
| ChromaDB locked | Restart runtime e reexecute |
| GPU OOM | Use MockLLM ou reduza batch size |
| Gradio não abre | Verifique se está em ambiente Colab |

## 📁 Arquivos do Projeto

```
medical-llm-assistant/
├── notebook.ipynb          ⭐ Este notebook
├── app.py                  # UI Gradio
├── requirements.txt        # Dependências
├── src/
│   ├── graph/             # LangGraph pipeline
│   ├── rag/               # ChromaDB interface
│   ├── llm/               # MockLLM + Model Loader
│   └── safety/            # Safety Gate
├── tests/                 # ~78 testes
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── data/
    └── patients_seed.json # Pacientes de exemplo
```

## ✅ Checklist antes de entregar

- [ ] Notebook executa sem erros
- [ ] Todos os testes passam
- [ ] 4 cenários de demonstração funcionam
- [ ] Interface Gradio carrega
- [ ] Safety gate bloqueia prescrições

---

**Autor:** Felipe Huszar  
**Data:** Março 2026  
**Tech Challenge:** Fase 3 - Pós-Tech IA para Devs
