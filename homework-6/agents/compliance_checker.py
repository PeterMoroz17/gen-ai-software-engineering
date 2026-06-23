"""Compliance Checker agent: produces the final disposition and writes the result to shared/results/."""
from __future__ import annotations

import json
from pathlib import Path

from agents.common import now_iso

STATUS_TO_FINAL = {
    "rejected": "rejected",
    "flagged_for_review": "flagged_for_review",
    "cleared_fraud_check": "cleared",
}


def process_message(message: dict) -> dict:
    data = dict(message.get("data", {}))
    status = data.get("status")

    final_status = STATUS_TO_FINAL.get(status, "rejected")

    if status == "rejected":
        reason = data.get("reason")
    elif status == "flagged_for_review":
        reason = f"risk_score {data.get('risk_score')} >= threshold"
    elif status == "cleared_fraud_check":
        reason = None
    else:
        reason = f"unexpected upstream status: {status}"

    return {
        "transaction_id": data.get("transaction_id"),
        "status": final_status,
        "risk_score": data.get("risk_score"),
        "reason": reason,
        "processed_at": now_iso(),
    }


def write_result(result: dict, results_dir: Path) -> Path:
    results_dir.mkdir(parents=True, exist_ok=True)
    path = results_dir / f"{result['transaction_id']}.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return path
