"""
test_audit_logging.py - E2E tests for structured audit logging.

Validates that every pipeline execution produces a complete, correct audit trail:
- All nodes logged
- Safety events recorded with reason
- CPF is never stored in plain text (privacy)
- Log entries are valid JSON
- Consultation saved event contains clinical metadata
"""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from src.audit.logger import audit_log, get_audit_trail


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def isolated_audit_log(tmp_path, monkeypatch):
    """Each test gets its own audit log file."""
    log_path = str(tmp_path / "audit.jsonl")
    monkeypatch.setenv("AUDIT_LOG_PATH", log_path)
    monkeypatch.setattr("src.audit.logger.AUDIT_LOG_PATH", log_path)
    yield log_path


@pytest.fixture()
def chroma_path(tmp_path, monkeypatch):
    path = str(tmp_path / "chroma")
    monkeypatch.setenv("CHROMA_DB_PATH", path)
    monkeypatch.setenv("USE_MOCK_LLM", "true")
    import src.rag.patient_rag as rag
    rag._client = None
    rag._client_path = None
    yield path
    rag._client = None
    rag._client_path = None


# ── Unit: audit_log function ──────────────────────────────────────────────────

class TestAuditLogFunction:
    def test_returns_dict(self):
        entry = audit_log("test_event", cpf="123.456.789-00", node="test")
        assert isinstance(entry, dict)

    def test_entry_has_required_fields(self):
        entry = audit_log("test_event", cpf="123.456.789-00")
        assert "timestamp" in entry
        assert "event_type" in entry
        assert "cpf_hash" in entry

    def test_cpf_is_hashed_not_plain(self):
        cpf = "123.456.789-00"
        entry = audit_log("test_event", cpf=cpf)
        # CPF plain text must NOT appear anywhere in the entry
        entry_str = json.dumps(entry)
        assert cpf not in entry_str
        assert cpf.replace(".", "").replace("-", "") not in entry_str

    def test_cpf_hash_is_consistent(self):
        cpf = "123.456.789-00"
        e1 = audit_log("event_a", cpf=cpf)
        e2 = audit_log("event_b", cpf=cpf)
        assert e1["cpf_hash"] == e2["cpf_hash"]

    def test_different_cpfs_different_hashes(self):
        e1 = audit_log("event", cpf="111.111.111-11")
        e2 = audit_log("event", cpf="222.222.222-22")
        assert e1["cpf_hash"] != e2["cpf_hash"]

    def test_no_cpf_sets_none(self):
        entry = audit_log("system_event")
        assert entry["cpf_hash"] is None

    def test_extra_kwargs_included(self):
        entry = audit_log("test_event", cpf="000", node="my_node", confidence=0.9)
        assert entry["node"] == "my_node"
        assert entry["confidence"] == 0.9

    def test_writes_to_file(self, isolated_audit_log):
        audit_log("write_test", cpf="999")
        with open(isolated_audit_log) as f:
            lines = f.readlines()
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["event_type"] == "write_test"

    def test_multiple_entries_appended(self, isolated_audit_log):
        audit_log("event_1", cpf="111")
        audit_log("event_2", cpf="222")
        audit_log("event_3", cpf="333")
        with open(isolated_audit_log) as f:
            lines = f.readlines()
        assert len(lines) == 3

    def test_each_line_is_valid_json(self, isolated_audit_log):
        for i in range(5):
            audit_log(f"event_{i}", cpf=str(i), extra=i)
        with open(isolated_audit_log) as f:
            for line in f:
                json.loads(line)  # must not raise


# ── get_audit_trail ───────────────────────────────────────────────────────────

class TestGetAuditTrail:
    def test_returns_empty_when_no_log(self, isolated_audit_log):
        trail = get_audit_trail()
        assert trail == []

    def test_returns_all_entries(self, isolated_audit_log):
        audit_log("e1", cpf="111")
        audit_log("e2", cpf="222")
        trail = get_audit_trail()
        assert len(trail) == 2

    def test_filter_by_event_type(self, isolated_audit_log):
        audit_log("node_executed", cpf="111", node="a")
        audit_log("safety_triggered", cpf="111")
        audit_log("node_executed", cpf="111", node="b")
        trail = get_audit_trail(event_type="node_executed")
        assert len(trail) == 2
        assert all(e["event_type"] == "node_executed" for e in trail)

    def test_filter_by_cpf(self, isolated_audit_log):
        audit_log("event", cpf="111.111.111-11")
        audit_log("event", cpf="222.222.222-22")
        audit_log("event", cpf="111.111.111-11")
        trail = get_audit_trail(cpf="111.111.111-11")
        assert len(trail) == 2

    def test_limit_respected(self, isolated_audit_log):
        for i in range(20):
            audit_log("event", cpf="111")
        trail = get_audit_trail(limit=5)
        assert len(trail) == 5

    def test_returns_most_recent_on_limit(self, isolated_audit_log):
        for i in range(10):
            audit_log("event", cpf="111", seq=i)
        trail = get_audit_trail(limit=3)
        seqs = [e["seq"] for e in trail]
        assert seqs == [7, 8, 9]


# ── E2E: pipeline produces complete audit trail ───────────────────────────────

class TestPipelineAuditTrail:
    def test_full_consultation_produces_audit_events(self, chroma_path, isolated_audit_log):
        from src.graph.pipeline import run_consultation
        from src.rag.patient_rag import save_patient

        save_patient("111.222.333-44", {"nome": "Audit Test", "idade": 40, "sexo": "M", "peso": 70})
        run_consultation(cpf="111.222.333-44", doctor_question="paciente com cefaleia")

        trail = get_audit_trail()
        event_types = [e["event_type"] for e in trail]

        assert "node_executed" in event_types
        assert "consultation_saved" in event_types

    def test_all_pipeline_nodes_logged(self, chroma_path, isolated_audit_log):
        from src.graph.pipeline import run_consultation
        from src.rag.patient_rag import save_patient

        save_patient("555.666.777-88", {"nome": "Node Test", "idade": 30, "sexo": "F", "peso": 60})
        run_consultation(cpf="555.666.777-88", doctor_question="dor abdominal")

        trail = get_audit_trail()
        nodes_logged = {e.get("node") for e in trail if e.get("node")}

        expected_nodes = {"check_patient", "retrieve_history", "build_prompt",
                          "llm_reasoning", "save_and_format"}
        assert expected_nodes.issubset(nodes_logged)

    def test_cpf_never_appears_in_log_file(self, chroma_path, isolated_audit_log):
        from src.graph.pipeline import run_consultation
        from src.rag.patient_rag import save_patient

        cpf = "999.888.777-66"
        save_patient(cpf, {"nome": "Privacy Test", "idade": 50, "sexo": "M", "peso": 80})
        run_consultation(cpf=cpf, doctor_question="sintomas")

        with open(isolated_audit_log) as f:
            raw_content = f.read()

        assert cpf not in raw_content
        assert cpf.replace(".", "").replace("-", "") not in raw_content

    def test_safety_escalation_logged(self, chroma_path, isolated_audit_log):
        """Safety Gate escalation must produce a safety_triggered audit event."""
        from src.graph.pipeline import run_consultation
        from src.rag.patient_rag import save_patient
        from unittest.mock import MagicMock, patch
        import json as _json

        save_patient("321.654.987-00", {"nome": "Safety Test", "idade": 35, "sexo": "F", "peso": 65})

        # Force LLM to return a short response (must trigger safety)
        bad_response = "ok"  # Muito curto → escalada
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = bad_response

        with patch("src.llm.factory.get_llm", return_value=mock_llm):
            run_consultation(cpf="321.654.987-00", doctor_question="pressão alta")

        trail = get_audit_trail(event_type="safety_triggered")
        assert len(trail) >= 1
        assert trail[0]["reason"] is not None

    def test_consultation_saved_event_has_metadata(self, chroma_path, isolated_audit_log):
        from src.graph.pipeline import run_consultation
        from src.rag.patient_rag import save_patient

        save_patient("444.333.222-11", {"nome": "Meta Test", "idade": 45, "sexo": "M", "peso": 75})
        run_consultation(cpf="444.333.222-11", doctor_question="glicose alta")

        saved = get_audit_trail(event_type="consultation_saved")
        assert len(saved) >= 1
        entry = saved[0]
        # Verifica campos do novo formato (prose)
        assert "hipotese" in entry or "exames_count" in entry or "diferenciais_count" in entry

    def test_audit_trail_order_is_chronological(self, chroma_path, isolated_audit_log):
        from src.graph.pipeline import run_consultation
        from src.rag.patient_rag import save_patient

        save_patient("777.888.999-00", {"nome": "Order Test", "idade": 28, "sexo": "F", "peso": 55})
        run_consultation(cpf="777.888.999-00", doctor_question="tontura")

        trail = get_audit_trail()
        timestamps = [e["timestamp"] for e in trail]
        assert timestamps == sorted(timestamps)
