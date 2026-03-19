"""
Lean E2E tests for structured audit logging.

Goal:
- keep only critical backend guarantees
- avoid repeating unit/integration behavior already covered elsewhere
"""

from __future__ import annotations

import json

import pytest

from src.audit.logger import audit_log, get_audit_trail


@pytest.fixture(autouse=True)
def isolated_audit_log(tmp_path, monkeypatch):
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


class TestAuditLogCore:
    def test_hashes_cpf_and_never_stores_plain_text(self, isolated_audit_log):
        cpf = "123.456.789-00"
        entry = audit_log("test_event", cpf=cpf, node="test")
        dumped = json.dumps(entry)
        assert cpf not in dumped
        assert cpf.replace(".", "").replace("-", "") not in dumped
        assert entry["cpf_hash"] is not None

    def test_writes_valid_jsonl_entries(self, isolated_audit_log):
        audit_log("event_1", cpf="111")
        audit_log("event_2", cpf="222")
        with open(isolated_audit_log) as f:
            rows = [json.loads(line) for line in f]
        assert len(rows) == 2
        assert rows[0]["event_type"] == "event_1"
        assert rows[1]["event_type"] == "event_2"

    def test_get_audit_trail_filters_by_event_type(self, isolated_audit_log):
        audit_log("node_executed", cpf="111", node="a")
        audit_log("safety_triggered", cpf="111")
        audit_log("node_executed", cpf="111", node="b")
        trail = get_audit_trail(event_type="node_executed")
        assert len(trail) == 2
        assert all(e["event_type"] == "node_executed" for e in trail)


class TestPipelineAuditTrail:
    def test_full_consultation_logs_core_events(self, chroma_path, isolated_audit_log):
        from src.graph.pipeline import run_consultation
        from src.rag.patient_rag import save_patient

        save_patient("111.222.333-44", {"nome": "Audit Test", "idade": 40, "sexo": "M", "peso": 70})
        run_consultation(cpf="111.222.333-44", doctor_question="paciente com cefaleia")

        trail = get_audit_trail()
        event_types = [e["event_type"] for e in trail]
        nodes_logged = {e.get("node") for e in trail if e.get("node")}

        assert "node_executed" in event_types
        assert "consultation_saved" in event_types
        assert {"check_patient", "retrieve_history", "build_prompt", "llm_reasoning", "save_and_format"}.issubset(nodes_logged)

    def test_safety_escalation_logs_reason(self, chroma_path, isolated_audit_log):
        from src.graph.pipeline import run_consultation
        from src.rag.patient_rag import save_patient
        from unittest.mock import MagicMock

        save_patient("321.654.987-00", {"nome": "Safety Test", "idade": 35, "sexo": "F", "peso": 65})

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = "ok"

        run_consultation(
            cpf="321.654.987-00",
            doctor_question="pressão alta",
            llm=mock_llm,
        )

        trail = get_audit_trail(event_type="safety_triggered")
        assert len(trail) >= 1
        assert trail[0]["reason"]

    def test_benchmark_mode_is_reflected_in_audit(self, chroma_path, isolated_audit_log):
        from src.graph.pipeline import run_consultation
        from src.rag.patient_rag import save_patient

        save_patient("444.333.222-11", {"nome": "Bench Test", "idade": 45, "sexo": "M", "peso": 75})
        run_consultation(
            cpf="444.333.222-11",
            doctor_question="glicose alta",
            benchmark_mode=True,
        )

        saved = get_audit_trail(event_type="consultation_saved")
        assert len(saved) >= 1
        assert saved[0].get("benchmark_mode") is True
