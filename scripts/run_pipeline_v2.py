#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.colab2.contracts import ClinicalRequest
from src.colab2.logging_audit import JsonlAuditLogger
from src.colab2.models import build_llm_backend
from src.colab2.pipeline import ClinicalAssistantPipeline
from src.colab2.retrieval import InMemoryRetriever
from src.colab2.safety import SafetyGate


def build_default_documents() -> list[dict]:
    return [
        {
            "id": "protocol-fever-001",
            "title": "Manejo inicial de febre",
            "content": "Febre persistente acima de 72 horas exige reavaliação clínica e investigação de sinais de alarme.",
            "source": "protocol://febre-001",
        },
        {
            "id": "protocol-respiratory-002",
            "title": "Queixa respiratória",
            "content": "Dispneia, dor torácica ou saturação baixa devem ser encaminhadas para avaliação médica imediata.",
            "source": "protocol://resp-002",
        },
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Colab 2 clinical assistant pipeline")
    parser.add_argument("--question", required=True)
    parser.add_argument("--patient-context", default="{}", help="JSON string")
    parser.add_argument("--backend", default=None, help="Model backend name")
    parser.add_argument("--audit-log", default="notes/audit_v2.jsonl")
    parser.add_argument("--trace-id", default=None, help="Optional fixed trace id for reproducibility")
    parser.add_argument("--retrieval-top-k", type=int, default=3, help="Retriever top-k (1..10)")
    args = parser.parse_args()

    patient_context = json.loads(args.patient_context)
    request = ClinicalRequest(
        question=args.question,
        patient_context=patient_context,
        retrieval_top_k=args.retrieval_top_k,
        trace_id=args.trace_id,
    )

    pipeline = ClinicalAssistantPipeline(
        retriever=InMemoryRetriever(build_default_documents()),
        llm=build_llm_backend(args.backend),
        safety_gate=SafetyGate(confidence_threshold=0.75),
        audit_logger=JsonlAuditLogger(Path(args.audit_log)),
    )

    result = pipeline.run(request)
    print(
        json.dumps(
            {
                "trace_id": result.trace_id,
                "approved": result.decision.approved,
                "needs_human_review": result.decision.needs_human_review,
                "reasons": result.decision.reasons,
                "answer": result.reasoning.answer,
                "sources": result.reasoning.sources,
                "audit_log_path": result.audit_log_path,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
