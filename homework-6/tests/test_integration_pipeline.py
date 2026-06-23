import json
import sys

import integrator
from integrator import build_envelope, build_summary, run_pipeline


SAMPLE_TRANSACTIONS = [
    {
        "transaction_id": "TXN_VALID",
        "timestamp": "2026-03-16T09:00:00Z",
        "source_account": "ACC-1001",
        "destination_account": "ACC-2001",
        "amount": "1500.00",
        "currency": "USD",
        "transaction_type": "transfer",
        "metadata": {"country": "US"},
    },
    {
        "transaction_id": "TXN_HIGH_RISK",
        "timestamp": "2026-03-16T03:00:00Z",
        "source_account": "ACC-1002",
        "destination_account": "ACC-3001",
        "amount": "25000.00",
        "currency": "USD",
        "transaction_type": "wire_transfer",
        "metadata": {"country": "DE"},
    },
    {
        "transaction_id": "TXN_INVALID",
        "timestamp": "2026-03-16T09:30:00Z",
        "source_account": "ACC-1003",
        "destination_account": "ACC-9999",
        "amount": "200.00",
        "currency": "XYZ",
        "transaction_type": "transfer",
        "metadata": {"country": "US"},
    },
]


def test_run_pipeline_writes_results_for_every_transaction(tmp_path):
    shared_dir = tmp_path / "shared"

    summary = run_pipeline(SAMPLE_TRANSACTIONS, shared_dir)

    results_dir = shared_dir / "results"
    for txn in SAMPLE_TRANSACTIONS:
        result_path = results_dir / f"{txn['transaction_id']}.json"
        assert result_path.exists()
        result = json.loads(result_path.read_text(encoding="utf-8"))
        assert result["transaction_id"] == txn["transaction_id"]
        assert result["status"] in {"cleared", "rejected", "flagged_for_review"}

    assert summary["total"] == 3
    assert summary["counts"]["rejected"] == 1
    assert summary["counts"]["flagged_for_review"] == 1
    assert summary["counts"]["cleared"] == 1


def test_run_pipeline_writes_summary_and_log(tmp_path):
    shared_dir = tmp_path / "shared"
    run_pipeline(SAMPLE_TRANSACTIONS, shared_dir)

    summary_path = shared_dir / "results" / "summary.json"
    log_path = shared_dir / "results" / "pipeline.log"
    assert summary_path.exists()
    assert log_path.exists()
    assert "transaction_validator" in log_path.read_text(encoding="utf-8")


def test_run_pipeline_writes_input_processing_output_hops(tmp_path):
    shared_dir = tmp_path / "shared"
    run_pipeline(SAMPLE_TRANSACTIONS, shared_dir)

    for subdir in ("input", "processing", "output"):
        files = list((shared_dir / subdir).glob("*.json"))
        assert len(files) == len(SAMPLE_TRANSACTIONS)


def test_build_envelope_has_standard_shape():
    envelope = build_envelope(SAMPLE_TRANSACTIONS[0])
    assert envelope["message_type"] == "transaction"
    assert envelope["source_agent"] == "integrator"
    assert envelope["target_agent"] == "transaction_validator"
    assert "message_id" in envelope
    assert envelope["data"]["transaction_id"] == "TXN_VALID"


def test_main_runs_pipeline_end_to_end(tmp_path, capsys):
    input_path = tmp_path / "sample.json"
    input_path.write_text(json.dumps(SAMPLE_TRANSACTIONS), encoding="utf-8")
    shared_dir = tmp_path / "shared"

    old_argv = sys.argv
    sys.argv = [
        "integrator.py",
        "--input", str(input_path),
        "--shared-dir", str(shared_dir),
    ]
    try:
        integrator.main()
    finally:
        sys.argv = old_argv

    captured = capsys.readouterr()
    assert "Loaded 3 transactions" in captured.out
    assert "Pipeline summary:" in captured.out
    assert (shared_dir / "results" / "summary.json").exists()


def test_build_summary_counts_by_status():
    results = [
        {"transaction_id": "A", "status": "cleared"},
        {"transaction_id": "B", "status": "cleared"},
        {"transaction_id": "C", "status": "rejected"},
    ]
    summary = build_summary(results)
    assert summary["total"] == 3
    assert summary["counts"]["cleared"] == 2
    assert summary["counts"]["rejected"] == 1
    assert summary["counts"]["flagged_for_review"] == 0
