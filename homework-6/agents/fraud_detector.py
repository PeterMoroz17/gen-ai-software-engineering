"""Fraud Detector agent: scores validated transactions for high-value, odd-hour, and cross-border risk."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from agents.common import now_iso

HIGH_VALUE_THRESHOLD = Decimal("10000.00")
ODD_HOUR_START = 0
ODD_HOUR_END = 6
HOME_COUNTRY = "US"
FLAG_THRESHOLD = 50


def _parse_hour(timestamp: str) -> int | None:
    try:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).hour
    except (ValueError, AttributeError):
        return None


def compute_risk_score(data: dict) -> int:
    score = 0

    amount = Decimal(str(data["amount"])).copy_abs()
    if amount > HIGH_VALUE_THRESHOLD:
        score += 50

    hour = _parse_hour(data.get("timestamp", ""))
    if hour is not None and ODD_HOUR_START <= hour < ODD_HOUR_END:
        score += 20

    country = data.get("metadata", {}).get("country")
    if country and country != HOME_COUNTRY:
        score += 15

    return min(score, 100)


def process_message(message: dict) -> dict:
    data = dict(message.get("data", {}))

    if data.get("status") != "validated":
        # Pass rejected transactions through unchanged to compliance_checker.
        return {
            **message,
            "source_agent": "fraud_detector",
            "target_agent": "compliance_checker",
            "timestamp": now_iso(),
        }

    score = compute_risk_score(data)
    data["risk_score"] = score
    data["status"] = "flagged_for_review" if score >= FLAG_THRESHOLD else "cleared_fraud_check"

    return {
        **message,
        "data": data,
        "source_agent": "fraud_detector",
        "target_agent": "compliance_checker",
        "timestamp": now_iso(),
    }
