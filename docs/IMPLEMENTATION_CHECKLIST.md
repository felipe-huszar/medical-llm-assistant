# Checklist de Implementação

## Base
- [ ] Definir schemas (entrada/saída)
- [ ] Definir contratos de erro
- [ ] Definir política de safety gate

## Pipeline
- [ ] ContextCollector
- [ ] Retriever
- [ ] Reasoning (StubLLM)
- [ ] SafetyGate
- [ ] Logger JSONL

## Integração
- [ ] Troca de StubLLM para modelo fine-tuned
- [ ] Verificação de campos obrigatórios (`sources`, `confidence`)
- [ ] Regras de bloqueio em conduta crítica

## Evidências
- [ ] Logs de execução
- [ ] Casos de teste com outputs esperados
- [ ] Resumo de métricas para relatório/vídeo
