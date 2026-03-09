import hashlib
import json
import time
import uuid
from typing import Any, Dict


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def write_audit_line(file_path: str, payload: Dict[str, Any]) -> None:
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def build_audit_payload(
    patient_id_hash: str,
    model_version: str,
    user_message: str,
    retrieved_ids: list[str],
    gate_decision: str,
    latency_ms: int,
    answer_text: str,
) -> Dict[str, Any]:
    return {
        "request_id": str(uuid.uuid4()),
        "timestamp": int(time.time()),
        "patient_id_hash": patient_id_hash,
        "model_version": model_version,
        "prompt_hash": _hash_text(user_message),
        "retrieved_ids": retrieved_ids,
        "gate_decision": gate_decision,
        "latency_ms": latency_ms,
        "response_hash": _hash_text(answer_text),
    }
