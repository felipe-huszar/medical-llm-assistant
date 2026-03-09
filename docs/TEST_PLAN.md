# Plano de Testes

## Objetivo
Garantir que o Colab 2 esteja funcional, auditável e seguro antes da integração com o modelo final.

## Casos mínimos
1. Fluxo feliz (resposta com fonte e confiança aceitável)
2. Prescrição detectada => `needs_human_review=true`
3. Baixa confiança => bloqueio
4. Sem sources => falha de validação
5. Logging completo (trace_id, docs, gate)

## Critério de aceite
- 100% dos casos críticos acima passando
- Logs válidos em JSONL
- Reprodutibilidade do fluxo em execução repetida
