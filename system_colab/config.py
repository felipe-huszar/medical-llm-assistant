from dataclasses import dataclass
from pathlib import Path


@dataclass
class Settings:
    model_dir: str = "/content/drive/MyDrive/Colab Notebooks/medical_llm_lora"
    chroma_dir: str = "/content/chroma_db"
    audit_log_file: str = "/content/audit_logs/requests.jsonl"
    collection_name: str = "patient_memory"
    top_k: int = 4
    safety_low_conf_threshold: float = 0.55


def ensure_paths(settings: Settings) -> None:
    Path(settings.chroma_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.audit_log_file).parent.mkdir(parents=True, exist_ok=True)
