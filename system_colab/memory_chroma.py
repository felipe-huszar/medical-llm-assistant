from typing import List, Dict, Any

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings


def get_vector_store(persist_dir: str, collection_name: str) -> Chroma:
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    return Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=persist_dir,
    )


def upsert_patient_event(
    vs: Chroma,
    patient_id_hash: str,
    event_id: str,
    text: str,
    event_type: str,
    timestamp: int,
) -> None:
    doc = Document(
        page_content=text,
        metadata={
            "patient_id_hash": patient_id_hash,
            "event_id": event_id,
            "event_type": event_type,
            "timestamp": timestamp,
        },
    )
    vs.add_documents([doc], ids=[event_id])


def retrieve_patient_context(
    vs: Chroma,
    patient_id_hash: str,
    query: str,
    top_k: int = 4,
) -> List[Dict[str, Any]]:
    docs = vs.similarity_search(query, k=top_k, filter={"patient_id_hash": patient_id_hash})
    out: List[Dict[str, Any]] = []
    for d in docs:
        out.append({
            "event_id": d.metadata.get("event_id"),
            "text": d.page_content,
            "event_type": d.metadata.get("event_type"),
            "timestamp": d.metadata.get("timestamp"),
        })
    return out
