import json
from urllib.request import Request, urlopen

KEY = None
with open('/root/.openclaw/.env', 'r', encoding='utf-8') as f:
    for line in f:
        if line.startswith('NOTION_API_KEY='):
            KEY = line.strip().split('=', 1)[1]
            break
if not KEY:
    raise SystemExit('NOTION_API_KEY missing')

parent_page_id = '31ac579bb234807faf7ac92eb99c3d51'

children = [
    {"object":"block","type":"heading_1","heading_1":{"rich_text":[{"type":"text","text":{"content":"Tech Challenge Fase 3 — Plano Revisado (V2)"}}]}},
    {"object":"block","type":"paragraph","paragraph":{"rich_text":[{"type":"text","text":{"content":"Revisão completa com foco em execução minuciosa, riscos, compliance, observabilidade e integração incremental (Felipe em Colab 2 aguardando Lucas no Colab 1)."}}]}},
    {"object":"block","type":"heading_2","heading_2":{"rich_text":[{"type":"text","text":{"content":"Objetivo de Negócio"}}]}},
    {"object":"block","type":"bulleted_list_item","bulleted_list_item":{"rich_text":[{"type":"text","text":{"content":"Entregar assistente médico confiável, com respostas contextualizadas e rastreáveis."}}]}},
    {"object":"block","type":"bulleted_list_item","bulleted_list_item":{"rich_text":[{"type":"text","text":{"content":"Evitar autonomia clínica indevida (human-in-the-loop obrigatório para condutas críticas)."}}]}},
    {"object":"block","type":"heading_2","heading_2":{"rich_text":[{"type":"text","text":{"content":"Arquitetura"}}]}},
    {"object":"block","type":"paragraph","paragraph":{"rich_text":[{"type":"text","text":{"content":"Fluxo: Contexto paciente -> Retrieval (RAG) -> Reasoning -> Safety Gate -> Resposta + Logs."}}]}},
    {"object":"block","type":"heading_2","heading_2":{"rich_text":[{"type":"text","text":{"content":"Plano de Implementação (TDD)"}}]}},
    {"object":"block","type":"numbered_list_item","numbered_list_item":{"rich_text":[{"type":"text","text":{"content":"Escrever testes de contrato (schemas, regras de gate, parser)."}}]}},
    {"object":"block","type":"numbered_list_item","numbered_list_item":{"rich_text":[{"type":"text","text":{"content":"Implementar pipeline mínimo com StubLLM e logs estruturados."}}]}},
    {"object":"block","type":"numbered_list_item","numbered_list_item":{"rich_text":[{"type":"text","text":{"content":"Validar integração de fluxo e evidências de auditoria."}}]}},
    {"object":"block","type":"numbered_list_item","numbered_list_item":{"rich_text":[{"type":"text","text":{"content":"Substituir StubLLM pelo modelo fine-tuned quando Lucas concluir."}}]}},
    {"object":"block","type":"heading_2","heading_2":{"rich_text":[{"type":"text","text":{"content":"Logging e Auditoria"}}]}},
    {"object":"block","type":"paragraph","paragraph":{"rich_text":[{"type":"text","text":{"content":"Cada execução registra: trace_id, timestamp, docs recuperados, scores, saída do reasoning, decisão de gate e motivo."}}]}},
    {"object":"block","type":"heading_2","heading_2":{"rich_text":[{"type":"text","text":{"content":"Status Atual"}}]}},
    {"object":"block","type":"paragraph","paragraph":{"rich_text":[{"type":"text","text":{"content":"Arquivos antigos foram removidos e o plano foi refeito do zero em projects/tech-challenge-fase3/docs (MASTER_PLAN, IMPLEMENTATION_CHECKLIST, TEST_PLAN)."}}]}},
]

payload = {
    "parent": {"page_id": parent_page_id},
    "properties": {
        "title": {"title": [{"type":"text","text":{"content":"Tech Challenge Fase 3 - Plano Revisado V2"}}]}
    },
    "children": children
}

req = Request(
    'https://api.notion.com/v1/pages',
    data=json.dumps(payload).encode('utf-8'),
    headers={
        'Authorization': f'Bearer {KEY}',
        'Notion-Version': '2025-09-03',
        'Content-Type': 'application/json'
    },
    method='POST'
)
with urlopen(req) as resp:
    print(resp.read().decode('utf-8'))
