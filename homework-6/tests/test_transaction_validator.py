from agents.transaction_validator import process_message, validate_transaction


def make_txn(**overrides):
    txn = {
        "transaction_id": "TXN100",
        "timestamp": "2026-03-16T09:00:00Z",
        "source_account": "ACC-1001",
        "destination_account": "ACC-2001",
        "amount": "1500.00",
        "currency": "USD",
        "transaction_type": "transfer",
    }
    txn.update(overrides)
    return txn


def test_valid_transaction_passes():
    ok, reason = validate_transaction(make_txn())
    assert ok is True
    assert reason is None


def test_missing_field_is_rejected():
    txn = make_txn()
    del txn["currency"]
    ok, reason = validate_transaction(txn)
    assert ok is False
    assert "currency" in reason


def test_unsupported_currency_is_rejected():
    ok, reason = validate_transaction(make_txn(currency="XYZ"))
    assert ok is False
    assert "currency" in reason


def test_negative_amount_rejected_for_non_refund():
    ok, reason = validate_transaction(make_txn(amount="-100.00", transaction_type="transfer"))
    assert ok is False
    assert "refund" in reason


def test_negative_amount_allowed_for_refund():
    ok, reason = validate_transaction(make_txn(amount="-100.00", transaction_type="refund"))
    assert ok is True
    assert reason is None


def test_zero_amount_rejected():
    ok, reason = validate_transaction(make_txn(amount="0.00"))
    assert ok is False
    assert "zero" in reason


def test_invalid_amount_format_rejected():
    ok, reason = validate_transaction(make_txn(amount="not-a-number"))
    assert ok is False
    assert "invalid amount" in reason


def test_process_message_sets_validated_status():
    message = {
        "message_id": "m1",
        "timestamp": "2026-03-16T09:00:00Z",
        "source_agent": "integrator",
        "target_agent": "transaction_validator",
        "message_type": "transaction",
        "data": make_txn(),
    }
    result = process_message(message)
    assert result["data"]["status"] == "validated"
    assert result["source_agent"] == "transaction_validator"
    assert result["target_agent"] == "fraud_detector"


def test_process_message_sets_rejected_status_with_reason():
    message = {"data": make_txn(currency="XYZ")}
    result = process_message(message)
    assert result["data"]["status"] == "rejected"
    assert "reason" in result["data"]


def test_dry_run_cli_reports_counts(tmp_path, capsys):
    import json

    from agents import transaction_validator

    sample = [make_txn(transaction_id="TXN_OK"), make_txn(transaction_id="TXN_BAD", currency="XYZ")]
    input_path = tmp_path / "sample.json"
    input_path.write_text(json.dumps(sample), encoding="utf-8")

    import sys

    old_argv = sys.argv
    sys.argv = ["transaction_validator.py", "--input", str(input_path), "--dry-run"]
    try:
        transaction_validator.main()
    finally:
        sys.argv = old_argv

    captured = capsys.readouterr()
    assert "Total transactions: 2" in captured.out
    assert "Valid:   1" in captured.out
    assert "Invalid: 1" in captured.out
    assert "TXN_BAD" in captured.out
