"""
Unit tests for src/rag/patient_rag.py

Requirements validated:
  - REQ-RAG-1: save_patient persists profile retrievable by CPF
  - REQ-RAG-2: patient_exists returns True/False correctly
  - REQ-RAG-3: get_patient returns None for unknown CPF
  - REQ-RAG-4: save_consultation persists and get_consultation_history retrieves
  - REQ-RAG-5: seed_from_file loads patients from JSON without duplicates
"""

import json
import os
import tempfile
import pytest

# Use isolated ChromaDB per test
@pytest.fixture(autouse=True)
def _isolated_chroma(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DB_PATH", str(tmp_path / "chroma"))
    # Reset the module-level singleton so each test gets a fresh client
    import src.rag.patient_rag as rag_mod
    rag_mod._client = None
    yield
    rag_mod._client = None


from src.rag.patient_rag import (
    save_patient,
    get_patient,
    patient_exists,
    save_consultation,
    get_consultation_history,
    seed_from_file,
)


# ---------------------------------------------------------------------------
# REQ-RAG-1 / REQ-RAG-2 / REQ-RAG-3
# ---------------------------------------------------------------------------

class TestPatientCRUD:
    def test_save_and_get_patient(self):
        """REQ-RAG-1: saved patient is retrievable by CPF."""
        profile = {"cpf": "111.000.000-01", "nome": "Alice", "idade": 30, "sexo": "F", "peso": 60}
        save_patient("111.000.000-01", profile)
        result = get_patient("111.000.000-01")
        assert result is not None
        assert result["nome"] == "Alice"
        assert result["idade"] == 30

    def test_patient_exists_true(self):
        """REQ-RAG-2: patient_exists returns True after save."""
        save_patient("222.000.000-02", {"nome": "Bob", "idade": 40, "sexo": "M", "peso": 80})
        assert patient_exists("222.000.000-02") is True

    def test_patient_exists_false(self):
        """REQ-RAG-2: patient_exists returns False for unknown CPF."""
        assert patient_exists("000.000.000-00") is False

    def test_get_patient_unknown_returns_none(self):
        """REQ-RAG-3: get_patient returns None for unknown CPF."""
        assert get_patient("999.999.999-99") is None

    def test_upsert_overwrites_profile(self):
        """Upsert semantics: saving same CPF twice keeps latest data."""
        save_patient("333.000.000-03", {"nome": "Carol", "idade": 20, "sexo": "F", "peso": 55})
        save_patient("333.000.000-03", {"nome": "Carol Updated", "idade": 21, "sexo": "F", "peso": 56})
        result = get_patient("333.000.000-03")
        assert result["nome"] == "Carol Updated"
        assert result["idade"] == 21


# ---------------------------------------------------------------------------
# REQ-RAG-4: Consultation history
# ---------------------------------------------------------------------------

class TestConsultationHistory:
    def test_save_and_retrieve_consultation(self):
        """REQ-RAG-4: save + retrieve consultation for a CPF."""
        save_consultation("444.000.000-04", "Dor abdominal?", "Análise: SII provável.")
        history = get_consultation_history("444.000.000-04")
        assert len(history) == 1
        assert "Dor abdominal?" in history[0]
        assert "SII provável" in history[0]

    def test_multiple_consultations(self):
        """REQ-RAG-4: multiple consultations are all retrievable."""
        cpf = "555.000.000-05"
        for i in range(3):
            save_consultation(cpf, f"Pergunta {i}", f"Resposta {i}")
        history = get_consultation_history(cpf, n_results=10)
        assert len(history) == 3

    def test_empty_history_for_new_patient(self):
        """REQ-RAG-4: new patient has empty history."""
        history = get_consultation_history("666.000.000-06")
        assert history == []

    def test_history_respects_n_results(self):
        """REQ-RAG-4: n_results cap is respected."""
        cpf = "777.000.000-07"
        for i in range(6):
            save_consultation(cpf, f"Q{i}", f"A{i}")
        history = get_consultation_history(cpf, n_results=3)
        assert len(history) <= 3


# ---------------------------------------------------------------------------
# REQ-RAG-5: Seed
# ---------------------------------------------------------------------------

class TestSeedFromFile:
    def test_seed_loads_patients(self, tmp_path):
        """REQ-RAG-5: seed_from_file inserts all patients from JSON."""
        seed_data = [
            {"cpf": "101.000.000-01", "nome": "Seed1", "idade": 50, "sexo": "M", "peso": 75},
            {"cpf": "102.000.000-02", "nome": "Seed2", "idade": 35, "sexo": "F", "peso": 62},
        ]
        seed_file = tmp_path / "seed.json"
        seed_file.write_text(json.dumps(seed_data), encoding="utf-8")

        count = seed_from_file(str(seed_file))
        assert count == 2
        assert patient_exists("101.000.000-01")
        assert patient_exists("102.000.000-02")

    def test_seed_skips_existing_patients(self, tmp_path):
        """REQ-RAG-5: seed does not overwrite existing patients."""
        cpf = "103.000.000-03"
        save_patient(cpf, {"nome": "Pre-existing", "idade": 40})

        seed_data = [{"cpf": cpf, "nome": "From Seed", "idade": 99}]
        seed_file = tmp_path / "seed.json"
        seed_file.write_text(json.dumps(seed_data), encoding="utf-8")

        count = seed_from_file(str(seed_file))
        assert count == 0  # already existed, skip

    def test_seed_missing_file_returns_zero(self):
        """REQ-RAG-5: missing seed file returns 0 without error."""
        count = seed_from_file("/nonexistent/path/seed.json")
        assert count == 0
