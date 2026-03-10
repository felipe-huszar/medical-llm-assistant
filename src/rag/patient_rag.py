"""
patient_rag.py - ChromaDB interface for patient data and consultation history.
"""

import json
import os
from datetime import datetime
from typing import Optional

import chromadb
from chromadb.config import Settings


_CHROMA_PATH = os.environ.get("CHROMA_DB_PATH", "./chroma_db")

_client: Optional[chromadb.Client] = None


def _get_client() -> chromadb.Client:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=_CHROMA_PATH)
    return _client


def _patients_collection():
    client = _get_client()
    return client.get_or_create_collection(
        name="patients",
        metadata={"hnsw:space": "cosine"},
    )


def _consultations_collection():
    client = _get_client()
    return client.get_or_create_collection(
        name="consultations",
        metadata={"hnsw:space": "cosine"},
    )


# ---------------------------------------------------------------------------
# Patient CRUD
# ---------------------------------------------------------------------------

def save_patient(cpf: str, profile: dict) -> None:
    """Persist patient profile to ChromaDB."""
    col = _patients_collection()
    doc = json.dumps(profile, ensure_ascii=False)
    try:
        col.upsert(
            ids=[cpf],
            documents=[doc],
            metadatas=[{"cpf": cpf, "nome": profile.get("nome", "")}],
        )
    except Exception as e:
        raise RuntimeError(f"Erro ao salvar paciente {cpf}: {e}") from e


def get_patient(cpf: str) -> Optional[dict]:
    """Return patient profile dict or None if not found."""
    col = _patients_collection()
    try:
        result = col.get(ids=[cpf])
        if result["documents"]:
            return json.loads(result["documents"][0])
        return None
    except Exception:
        return None


def patient_exists(cpf: str) -> bool:
    return get_patient(cpf) is not None


# ---------------------------------------------------------------------------
# Consultation history
# ---------------------------------------------------------------------------

def save_consultation(cpf: str, question: str, answer: str, metadata: Optional[dict] = None) -> None:
    """Save a consultation record under the patient CPF."""
    col = _consultations_collection()
    doc_id = f"{cpf}_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
    meta = {
        "cpf": cpf,
        "timestamp": datetime.utcnow().isoformat(),
        **(metadata or {}),
    }
    doc = json.dumps(
        {"question": question, "answer": answer},
        ensure_ascii=False,
    )
    col.upsert(ids=[doc_id], documents=[doc], metadatas=[meta])


def get_consultation_history(cpf: str, n_results: int = 5) -> list[str]:
    """Return last n consultation summaries for a patient."""
    col = _consultations_collection()
    try:
        result = col.get(
            where={"cpf": cpf},
            limit=n_results,
        )
        entries = []
        for doc in result["documents"]:
            data = json.loads(doc)
            entries.append(
                f"Pergunta: {data.get('question', '')}\nResposta: {data.get('answer', '')}"
            )
        return entries
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Seed data loader
# ---------------------------------------------------------------------------

def seed_from_file(path: str = "data/patients_seed.json") -> int:
    """Load seed patients from JSON file. Returns count inserted."""
    if not os.path.exists(path):
        return 0
    with open(path, encoding="utf-8") as f:
        patients = json.load(f)
    count = 0
    for p in patients:
        cpf = p.get("cpf")
        if cpf and not patient_exists(cpf):
            save_patient(cpf, p)
            count += 1
    return count
