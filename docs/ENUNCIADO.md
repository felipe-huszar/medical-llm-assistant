# Tech Challenge - Fase 3 (Enunciado Oficial)

> Fonte: PDF original bc13bf35-0cc8-4ddf-bcb3-6fcb3f849fb6.pdf

## Desafio

Após o sucesso na automação de análises de exames e textos clínicos, o hospital quer avançar para um nível superior de personalização: **criar um assistente virtual médico, treinado com os dados próprios do hospital**, capaz de:
- Auxiliar nas condutas clínicas
- Responder dúvidas de médicos
- Sugerir procedimentos com base nos protocolos internos
- Organizar fluxos de decisão automatizados e seguros com **LangChain**

---

## Requisitos Obrigatórios

### 1. Fine-tuning de LLM com dados médicos internos
- Modelo: LLaMA, Falcon ou similar
- Dados: protocolos médicos, perguntas frequentes de médicos, laudos/receitas/procedimentos
- Técnicas: preprocessing, anonimização e curadoria

### 2. Assistente médico com LangChain
- Pipeline integrando a LLM customizada
- Consultas em base de dados estruturadas (prontuários, registros)
- Contextualização das respostas com informações do paciente

### 3. Segurança e validação
- ⚠️ Nunca prescrever diretamente sem validação humana
- Logging detalhado para rastreamento e auditoria
- Explainability: indicar a fonte da informação na resposta

### 4. Organização do código
- Projeto modularizado em Python
- README com instruções completas

---

## Entregáveis

### Repositório Git
- Pipeline de fine-tuning
- Integração com LangChain
- **Fluxos do LangGraph** ← explicitamente cobrado
- Dataset anonimizado ou sintético
- Relatório técnico com:
  - Explicação do processo de fine-tuning
  - Descrição do assistente médico
  - Diagrama do fluxo LangChain
  - Avaliação do modelo e análise dos resultados

### Vídeo (até 15 minutos)
- Treinamento e funcionamento da LLM personalizada
- Execução de um fluxo automatizado
- Resposta a perguntas clínicas contextualizadas
- Logs e validação das respostas

---

## Datasets Sugeridos

| Dataset | Conteúdo | Link |
|---|---|---|
| PubMedQA | Perguntas/respostas clínicas com base em publicações | https://pubmedqa.github.io/ |
| MedQuAD | Conjunto de perguntas e respostas sobre saúde | https://github.com/abachaa/MedQuAD |

---

## Peso
**90% da nota de todas as disciplinas da fase**
