import hashlib
import time
import uuid

import gradio as gr

from config import Settings, ensure_paths
from memory_chroma import get_vector_store, upsert_patient_event
from model_loader import load_model_and_tokenizer
from pipeline import run_pipeline


settings = Settings()
ensure_paths(settings)

vector_store = get_vector_store(settings.chroma_dir, settings.collection_name)
model, tokenizer = load_model_and_tokenizer(settings.model_dir)
MODEL_VERSION = "ft-v1"


def _hash_patient_id(raw_id: str) -> str:
    return hashlib.sha256(raw_id.encode("utf-8")).hexdigest()[:24]


def handle_chat(operator_id: str, patient_id: str, message: str):
    patient_hash = _hash_patient_id(patient_id)

    result = run_pipeline(
        settings=settings,
        vector_store=vector_store,
        model=model,
        tokenizer=tokenizer,
        patient_id_hash=patient_hash,
        user_message=message,
        model_version=MODEL_VERSION,
    )

    upsert_patient_event(
        vs=vector_store,
        patient_id_hash=patient_hash,
        event_id=str(uuid.uuid4()),
        text=message,
        event_type="patient_message",
        timestamp=int(time.time()),
    )

    upsert_patient_event(
        vs=vector_store,
        patient_id_hash=patient_hash,
        event_id=str(uuid.uuid4()),
        text=result["answer"][:1000],
        event_type="assistant_response",
        timestamp=int(time.time()),
    )

    summary = f"Gate: {result['gate_decision']} | Review: {result['needs_human_review']} | Latency: {result['latency_ms']}ms"
    return result["answer"], summary


with gr.Blocks(title="TC Fase3 - Clinical Assistant") as demo:
    gr.Markdown("# TC Fase3 - Clinical Assistant (1 Colab MVP)")
    with gr.Row():
        operator_id = gr.Textbox(label="Operator ID", value="operator-01")
        patient_id = gr.Textbox(label="Patient ID (não usar CPF real em demo)")
    message = gr.Textbox(label="Mensagem clínica")
    run_btn = gr.Button("Enviar")
    answer = gr.Textbox(label="Resposta")
    status = gr.Textbox(label="Status")

    run_btn.click(handle_chat, [operator_id, patient_id, message], [answer, status])


if __name__ == "__main__":
    demo.launch(share=True)
