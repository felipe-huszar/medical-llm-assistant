"""
audit/logger.py - Structured audit logging for the medical assistant pipeline.

Logs every pipeline event as JSON (JSONL format) for traceability and compliance.
Each log entry contains: timestamp, event_type, cpf (hashed), node, metadata.

Usage:
    from src.audit.logger import audit_log, get_audit_trail
    audit_log("node_executed", node="check_patient", cpf=cpf, is_new=True)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── File logging (JSONL)
AUDIT_LOG_PATH = os.environ.get("AUDIT_LOG_PATH", "/tmp/medical_audit.jsonl")

# ── Python stdlib logger (console)
_logger = logging.getLogger("medical_audit")
if not _logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s [AUDIT] %(message)s"))
    _logger.addHandler(_handler)
    _logger.setLevel(logging.INFO)


def _hash_cpf(cpf: str) -> str:
    """One-way hash of CPF for privacy-safe logging."""
    return hashlib.sha256(cpf.encode()).hexdigest()[:12]


def audit_log(event_type: str, cpf: str = "", **kwargs: Any) -> dict:
    """
    Write a structured audit entry.

    Args:
        event_type: e.g. 'node_executed', 'safety_triggered', 'escalation', 'consultation_saved'
        cpf: patient CPF (will be hashed before logging)
        **kwargs: arbitrary metadata fields

    Returns:
        The log entry dict (useful for testing).
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "cpf_hash": _hash_cpf(cpf) if cpf else None,
        **kwargs,
    }

    # Write to JSONL file
    try:
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass  # never crash the pipeline due to logging

    # Console log
    _logger.info(json.dumps(entry, ensure_ascii=False))

    return entry


def get_audit_trail(cpf: str = "", event_type: str = "", limit: int = 100) -> list[dict]:
    """
    Read audit trail from JSONL file.

    Args:
        cpf: filter by CPF (hashed internally)
        event_type: filter by event type
        limit: max entries to return

    Returns:
        List of log entry dicts (most recent last).
    """
    path = Path(AUDIT_LOG_PATH)
    if not path.exists():
        return []

    cpf_hash = _hash_cpf(cpf) if cpf else None
    entries = []

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            if cpf_hash and entry.get("cpf_hash") != cpf_hash:
                continue
            if event_type and entry.get("event_type") != event_type:
                continue

            entries.append(entry)

    return entries[-limit:]
