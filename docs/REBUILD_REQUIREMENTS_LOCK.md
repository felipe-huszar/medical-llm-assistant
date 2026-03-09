# Rebuild Lock - Aderência estrita ao Tech Challenge

## Requisitos que passam a ser obrigatórios (sem exceção)
1. LangGraph real (StateGraph, nós e arestas explícitos no código).
2. ChromaDB real (persistência vetorial + query de contexto).
3. Integração LangChain para orquestração com modelo (stub temporário permitido apenas até integração com Colab 1).
4. Safety + human-in-the-loop para condutas críticas.
5. Logging auditável com fontes e decisão de gate.
6. README e evidências de execução fim a fim.

## Critério de pronto
- Demo: paciente -> recuperação ChromaDB -> fluxo LangGraph -> resposta com fontes -> gate de segurança.
- Testes de integração cobrindo LangGraph + Chroma.
- Sem entregar features extras que não aumentem aderência ao requisito.
