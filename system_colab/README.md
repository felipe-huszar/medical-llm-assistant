# System Colab (1-Colab MVP)

Implementação base do plano Fase 3:

Fluxo canônico:
`Paciente -> Memória Chroma -> Prompt -> Modelo FT (Drive) -> Safety Gate -> Resposta -> Audit JSONL`

## Módulos
- `config.py`: configurações globais
- `memory_chroma.py`: persistência e retrieval por paciente
- `model_loader.py`: carga de modelo fine-tunado do Drive
- `safety_gate.py`: regras clínicas mínimas
- `audit_logger.py`: logging JSONL auditável
- `pipeline.py`: orquestração E2E
- `app_gradio.py`: UI

## Próximo passo
Rodar o notebook `colab/tc_fase3_system_single_colab.ipynb` no Colab e preencher as variáveis de ambiente/paths.
