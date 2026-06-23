"""Shared helpers used by every pipeline agent: timestamps, audit logging, and PII masking."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

ISO_4217_CURRENCIES = {
    "USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "CNY", "NZD", "SEK",
}

REQUIRED_TRANSACTION_FIELDS = (
    "transaction_id",
    "timestamp",
    "source_account",
    "destination_account",
    "amount",
    "currency",
    "transaction_type",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def mask_account(account_number: str) -> str:
    if not account_number:
        return "****"
    if len(account_number) <= 4:
        return "*" * len(account_number)
    tail = account_number[-4:]
    masked_length = len(account_number) - 4
    return f"{'*' * masked_length}{tail}"


def audit_log(log_path: Path, agent_name: str, transaction_id: str, outcome: str) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    line = f"{now_iso()} | {agent_name} | {transaction_id} | {outcome}\n"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(line)
