#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.pipeline import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="LangGraph + Chroma rebuild demo")
    parser.add_argument("--question", required=True)
    parser.add_argument("--patient-context", default="{}", help="JSON")
    parser.add_argument("--trace-id", default="trace-demo-001")
    parser.add_argument("--retrieval-top-k", type=int, default=3)
    parser.add_argument("--persist-directory", default=None)
    parser.add_argument("--audit-log", default=None)
    args = parser.parse_args()

    patient_context = json.loads(args.patient_context)

    result = run_pipeline(
        question=args.question,
        patient_context=patient_context,
        trace_id=args.trace_id,
        retrieval_top_k=args.retrieval_top_k,
        persist_directory=args.persist_directory,
        audit_log_path=args.audit_log,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
