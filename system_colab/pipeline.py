import time
from typing import Dict, Any

from config import Settings
from memory_chroma import retrieve_patient_context
from safety_gate import run_safety_gate
from audit_logger import build_audit_payload, write_audit_line


SYSTEM_PROMPT = """Você é um assistente clínico para apoio à decisão.
Não dê diagnóstico definitivo.
Sempre indique fontes/contexto usado e limite da recomendação.
"""


def build_prompt(user_message: str, context_items: list[dict]) -> str:
    ctx = "\n".join([f"- ({c['event_type']}) {c['text']}" for c in context_items])
    return f"""{SYSTEM_PROMPT}

Contexto recuperado do paciente:
{ctx if ctx else '- sem histórico relevante'}

Pergunta atual:
{user_message}

Responda em JSON com campos: answer, sources, confidence, recommendation_type.
"""


def run_pipeline(
    settings: Settings,
    vector_store,
    model,
    tokenizer,
    patient_id_hash: str,
    user_message: str,
    model_version: str,
) -> Dict[str, Any]:
    t0 = time.time()

    context_items = retrieve_patient_context(
        vector_store,
        patient_id_hash,
        query=user_message,
        top_k=settings.top_k,
    )

    prompt = build_prompt(user_message, context_items)

    from model_loader import generate_response
    raw_answer = generate_response(model, tokenizer, prompt)

    # Placeholder parsing: enquanto não houver parser robusto, empacota fallback
    response = {
        "answer": raw_answer,
        "sources": [c["event_id"] for c in context_items if c.get("event_id")],
        "confidence": 0.6,
        "recommendation_type": "analysis",
    }

    gate = run_safety_gate(response, settings.safety_low_conf_threshold)
    latency_ms = int((time.time() - t0) * 1000)

    audit = build_audit_payload(
        patient_id_hash=patient_id_hash,
        model_version=model_version,
        user_message=user_message,
        retrieved_ids=response["sources"],
        gate_decision=gate.decision,
        latency_ms=latency_ms,
        answer_text=response["answer"],
    )
    write_audit_line(settings.audit_log_file, audit)

    response["gate_decision"] = gate.decision
    response["needs_human_review"] = gate.needs_human_review
    response["gate_reasons"] = gate.reasons
    response["latency_ms"] = latency_ms

    return response
