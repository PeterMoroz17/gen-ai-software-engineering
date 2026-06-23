"""Orchestrator for the multi-agent banking transaction pipeline.

Loads sample-transactions.json, wraps each record in the standard message
envelope, and runs it through transaction_validator -> fraud_detector ->
compliance_checker, persisting every hop under shared/.
"""
from __future__ import annotations

import argparse
import json
import shutil
import uuid
from pathlib import Path

from agents import compliance_checker, fraud_detector, transaction_validator
from agents.common import audit_log, mask_account, now_iso

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SHARED_DIR = BASE_DIR / "shared"
DEFAULT_INPUT_FILE = BASE_DIR / "sample-transactions.json"
SHARED_SUBDIRS = ("input", "processing", "output", "results")


def setup_shared_dirs(shared_dir: Path) -> None:
    for subdir in ("processing", "output"):
        path = shared_dir / subdir
        if path.exists():
            shutil.rmtree(path)
    for subdir in SHARED_SUBDIRS:
        (shared_dir / subdir).mkdir(parents=True, exist_ok=True)


def build_envelope(transaction: dict) -> dict:
    return {
        "message_id": str(uuid.uuid4()),
        "timestamp": now_iso(),
        "source_agent": "integrator",
        "target_agent": "transaction_validator",
        "message_type": "transaction",
        "data": dict(transaction),
    }


def build_summary(results: list[dict]) -> dict:
    counts = {"cleared": 0, "rejected": 0, "flagged_for_review": 0}
    for result in results:
        counts[result["status"]] = counts.get(result["status"], 0) + 1
    return {
        "total": len(results),
        "counts": counts,
        "generated_at": now_iso(),
    }


def run_pipeline(transactions: list[dict], shared_dir: Path) -> dict:
    setup_shared_dirs(shared_dir)
    log_path = shared_dir / "results" / "pipeline.log"
    results: list[dict] = []

    for transaction in transactions:
        txn_id = transaction["transaction_id"]
        envelope = build_envelope(transaction)
        (shared_dir / "input" / f"{txn_id}.json").write_text(
            json.dumps(envelope, indent=2), encoding="utf-8"
        )
        (shared_dir / "processing" / f"{txn_id}.json").write_text(
            json.dumps(envelope, indent=2), encoding="utf-8"
        )

        validated = transaction_validator.process_message(envelope)
        audit_log(log_path, "transaction_validator", txn_id, validated["data"]["status"])

        fraud_checked = fraud_detector.process_message(validated)
        audit_log(log_path, "fraud_detector", txn_id, fraud_checked["data"].get("status", "skipped"))
        (shared_dir / "output" / f"{txn_id}.json").write_text(
            json.dumps(fraud_checked, indent=2), encoding="utf-8"
        )

        result = compliance_checker.process_message(fraud_checked)
        compliance_checker.write_result(result, shared_dir / "results")
        audit_log(log_path, "compliance_checker", txn_id, result["status"])

        results.append(result)
        print(
            f"  {txn_id} "
            f"[{mask_account(transaction['source_account'])} -> {mask_account(transaction['destination_account'])}] "
            f"=> {result['status']}"
            + (f" ({result['reason']})" if result.get("reason") else "")
        )

    summary = build_summary(results)
    (shared_dir / "results" / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the multi-agent banking pipeline end-to-end.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT_FILE))
    parser.add_argument("--shared-dir", default=str(DEFAULT_SHARED_DIR))
    args = parser.parse_args()

    transactions = json.loads(Path(args.input).read_text(encoding="utf-8"))
    print(f"Loaded {len(transactions)} transactions from {args.input}")
    print("Running pipeline...")

    summary = run_pipeline(transactions, Path(args.shared_dir))

    print("\nPipeline summary:")
    print(f"  {'Total:':<20}{summary['total']}")
    print(f"  {'Cleared:':<20}{summary['counts']['cleared']}")
    print(f"  {'Rejected:':<20}{summary['counts']['rejected']}")
    print(f"  {'Flagged for review:':<20}{summary['counts']['flagged_for_review']}")


if __name__ == "__main__":
    main()
