# Tech Challenge Fase 3 — Plano Mestre (Revisão Minuciosa)

Data: 2026-03-05
Escopo desta revisão: replanejamento completo com foco em execução robusta, rastreável e auditável.

## 1) Objetivo de negócio
Entregar um assistente médico interno que:
1. Responda dúvidas clínicas com base em protocolos internos e contexto de paciente.
2. Nunca opere como prescritor autônomo (sempre human-in-the-loop para conduta crítica).
3. Seja auditável ponta-a-ponta (logs, fontes, decisão de gate, versão do modelo).
4. Permita evolução incremental: Colab 2 pode avançar antes do fine-tuning final.

## 2) Estratégia de execução (dependências reais)
- Lucas: Colab 1 (fine-tuning).
- Felipe: Colab 2 (orquestração LangChain/LangGraph + RAG + segurança + observabilidade).
- Colab 3 (QA/avaliação): começa com stubs e dados sintéticos, depois valida com modelo real.

Princípio-chave: **desacoplamento**. O motor de orquestração e segurança não depende do modelo final para ser construído/testado.

## 3) Arquitetura alvo
### 3.1 Camadas
1. Ingestão/normalização de contexto clínico.
2. Retrieval (RAG) sobre protocolos/documentos.
3. Reasoning (modelo/placeholder) com formato de saída controlado.
4. Safety Gate (políticas clínicas + compliance).
5. Logging e explainability.
6. Interface de resposta (com flags de revisão humana).

### 3.2 Fluxo lógico
`Contexto paciente -> Retriever -> Reasoning -> Safety Gate -> Resposta + Log`

### 3.3 Regras não-negociáveis
- recommendation_type=prescription => needs_human_review=true
- confidence abaixo de limiar => bloqueio/escalação
- toda resposta precisa de `sources[]`
- sem fonte => resposta inválida

## 4) Plano por Colab
## Colab 1 (Lucas)
- Fine-tuning com dataset interno + curadoria + anonimização.
- Entregável mínimo: endpoint/interface para inferência + versão do checkpoint.

## Colab 2 (Felipe)
- Implementar pipeline completo com stubs inicialmente.
- Definir contratos de entrada/saída e garantir observabilidade.
- Preparar swap simples do StubLLM para LLM real.

## Colab 3 (QA)
- Casos clínicos de validação.
- Métricas de qualidade, risco e rastreabilidade.
- Evidências para relatório técnico e vídeo.

## 5) Plano de implementação técnico (TDD)
1. Testes de contrato (schemas e validações).
2. Testes de retrieval (relevância, top-k, cache).
3. Testes de fluxo (StateGraph + gating + logs).
4. Implementação mínima para passar testes.
5. Refatoração orientada a legibilidade e rastreio.

## 6) Plano de testes (objetivo + evidência)
### 6.1 Unitários
- Schema válido/inválido.
- Regras de gate.
- Parser de saída.

### 6.2 Integração
- Fluxo completo com stub.
- Verificação de logs JSONL.
- Verificação de `trace_id`, `sources`, `needs_human_review`.

### 6.3 Regressão
- Testes repetíveis com cenário fixo.
- Baseline de tempo e cobertura funcional.

## 7) Logging, observabilidade e auditoria
Cada execução deve registrar:
- timestamp
- trace_id
- versão do pipeline
- pergunta/contexto (sanitizado)
- docs recuperados + scores
- saída do reasoning
- decisão do safety gate
- motivo de bloqueio/aprovação

Formato primário: JSONL (fácil de processar, auditar e demonstrar).

## 8) Compliance e risco
- Dados sensíveis: mascaramento/desidentificação antes de treino/teste.
- Risco clínico: bloquear conduta autônoma crítica.
- Risco reputacional: resposta sem fonte é inválida.
- Risco técnico: fallback para human review em baixa confiança.

## 9) Definição de pronto (DoD)
1. Colab 2 roda de ponta a ponta com logs e gate.
2. Testes automatizados passam em ambiente local/colab.
3. Substituição de StubLLM por LLM real ocorre sem quebrar contratos.
4. Evidências exportáveis para relatório e vídeo estão disponíveis.

## 10) Entregáveis práticos
- `docs/MASTER_PLAN.md` (este documento)
- `docs/IMPLEMENTATION_CHECKLIST.md`
- `docs/TEST_PLAN.md`
- Código do pipeline em `src/`
- Testes em `tests/`
- Evidências em `notes/` e logs estruturados

## 11) Próximos passos imediatos (ordem)
1. Fechar contratos de schema.
2. Implementar pipeline mínimo com stub + logs.
3. Rodar bateria inicial de testes.
4. Integrar com modelo do Lucas.
5. Executar validação final + preparar vídeo/relatório.
