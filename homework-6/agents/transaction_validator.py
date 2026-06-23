"""Transaction Validator agent: checks required fields, amount, and ISO 4217 currency."""
from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

if __package__ in (None, ""):
    # Allow running directly as `python agents/transaction_validator.py` (used by the
    # /validate-transactions skill), where Python only adds this file's own directory
    # (agents/) to sys.path, not its parent.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from agents.common import ISO_4217_CURRENCIES, REQUIRED_TRANSACTION_FIELDS, now_iso
else:
    from agents.common import ISO_4217_CURRENCIES, REQUIRED_TRANSACTION_FIELDS, now_iso


def validate_transaction(data: dict) -> tuple[bool, str | None]:
    for field in REQUIRED_TRANSACTION_FIELDS:
        if not data.get(field):
            return False, f"missing required field: {field}"

    try:
        amount = Decimal(str(data["amount"]))
    except InvalidOperation:
        return False, "invalid amount format"

    if amount == 0:
        return False, "amount must not be zero"
    if amount < 0 and data.get("transaction_type") != "refund":
        return False, "negative amount only allowed for refund transactions"

    currency = str(data.get("currency", "")).upper()
    if currency not in ISO_4217_CURRENCIES:
        return False, f"unsupported currency code: {currency}"

    return True, None


def process_message(message: dict) -> dict:
    data = dict(message.get("data", {}))
    is_valid, reason = validate_transaction(data)
    data["status"] = "validated" if is_valid else "rejected"
    if reason:
        data["reason"] = reason

    return {
        **message,
        "data": data,
        "source_agent": "transaction_validator",
        "target_agent": "fraud_detector",
        "timestamp": now_iso(),
    }


def _load_transactions(input_path: Path) -> list[dict]:
    return json.loads(input_path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate transactions without running the full pipeline.")
    parser.add_argument(
        "--input",
        default=str(Path(__file__).resolve().parent.parent / "sample-transactions.json"),
        help="Path to the transactions JSON file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate only; never writes to shared/.",
    )
    args = parser.parse_args()

    transactions = _load_transactions(Path(args.input))
    rows: list[tuple[str, str, str]] = []
    valid_count = 0
    invalid: list[tuple[str, str]] = []

    for txn in transactions:
        ok, reason = validate_transaction(txn)
        txn_id = txn.get("transaction_id", "UNKNOWN")
        if ok:
            valid_count += 1
            rows.append((txn_id, "valid", "-"))
        else:
            reason = reason or "unknown reason"
            invalid.append((txn_id, reason))
            rows.append((txn_id, "invalid", reason))

    total = len(transactions)
    print(f"Total transactions: {total}")
    print(f"Valid:   {valid_count}")
    print(f"Invalid: {len(invalid)}")

    print("\ntransaction_id | valid/invalid | reason")
    print("---------------|---------------|------------------------------")
    for txn_id, status, reason in rows:
        print(f"{txn_id:<14} | {status:<13} | {reason}")


if __name__ == "__main__":
    main()
