# CHALLENGE_STATE

## updated_at_utc
2026-03-19T23:53:00Z

## current_focus
Implementar plano de correção de alucinações e diagnósticos errados em etapas por colab.

## progress_notes
- Estado inicializado porque o projeto não tinha CHALLENGE_STATE.md.
- Próximas etapas: system_gradio, gerador_casos_sinteticos, finetuning.

- Etapa 1 concluída: benchmark_mode adicionado ao pipeline/runtime e ao colab principal.
- Teste executado: pytest -q tests/unit/test_nodes.py (23 passed).
- Etapa 2 concluída: gerador sintético reescrito para casos dirigidos por doença, negativos explícitos e classes de insufficient_data/out_of_scope.
- Smoke test do gerador executado com 50 exemplos.
- Etapa 3 concluída: finetuning reescrito para single-stage mixed training com eval set e adapter-only save.
- Validação executada: parsing/syntax check das células de código do notebook.
- Etapa 4 concluída: guardrails de backend implementados para insufficient_data, out_of_scope e minimum_evidence_gate.
- Prompt de inferência e notebook de fine-tuning alinhados com status explícito da análise.
- Testes executados: pytest -q tests/unit/test_safety_gate.py tests/unit/test_nodes.py (46 passed).
- Etapa 5 concluída: suíte backend enxugada para reduzir duplicação entre unit/integration/e2e.
- Arquivos removidos: tests/e2e/test_extended_e2e.py, tests/e2e/test_pipeline_e2e.py.
- Arquivo simplificado: tests/e2e/test_audit_logging.py.
- Resultado: coleta total 171 -> 105; backend 91 passed em 31.88s.
- Etapa 6 concluída: guardrail endurecido para impedir status insufficient_data com hipótese grave afirmativa e corrigido match normalizado de hipóteses graves (ex.: SCA com/sem acento).
- Testes executados: pytest -q tests/unit/test_safety_gate.py tests/unit/test_nodes.py (47 passed).
- Etapa 7 concluída: recalibração para reduzir conservadorismo excessivo.
- Ajustes: status aliases (ex.: suspicious -> supported_hypothesis), prompts menos conservadores, gerador com 80/12/8 e casos supported_hypothesis com dados acessórios faltantes.
- Testes executados: pytest -q tests/unit/test_safety_gate.py tests/unit/test_nodes.py (48 passed).
