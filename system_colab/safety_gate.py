from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class GateResult:
    decision: str
    needs_human_review: bool
    reasons: list[str]


def run_safety_gate(response: Dict[str, Any], low_conf_threshold: float = 0.55) -> GateResult:
    reasons: list[str] = []
    decision = "allow"

    confidence = float(response.get("confidence", 0.0))
    rec_type = str(response.get("recommendation_type", "")).lower()
    sources = response.get("sources", [])

    if not sources:
        decision = "block_and_escalate"
        reasons.append("missing_sources")

    if rec_type in {"prescription", "dosage"}:
        decision = "block_and_escalate"
        reasons.append("critical_recommendation_requires_human")

    if confidence < low_conf_threshold and decision != "block_and_escalate":
        decision = "allow_with_warning"
        reasons.append("low_confidence")

    return GateResult(
        decision=decision,
        needs_human_review=decision != "allow",
        reasons=reasons,
    )
