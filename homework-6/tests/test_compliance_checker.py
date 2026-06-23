import json

from agents.compliance_checker import process_message, write_result


def test_rejected_status_maps_to_rejected():
    message = {"data": {"transaction_id": "TXN1", "status": "rejected", "reason": "bad currency"}}
    result = process_message(message)
    assert result["status"] == "rejected"
    assert result["reason"] == "bad currency"


def test_flagged_for_review_status_maps_through():
    message = {"data": {"transaction_id": "TXN2", "status": "flagged_for_review", "risk_score": 65}}
    result = process_message(message)
    assert result["status"] == "flagged_for_review"
    assert result["risk_score"] == 65
    assert "65" in result["reason"]


def test_cleared_fraud_check_maps_to_cleared():
    message = {"data": {"transaction_id": "TXN3", "status": "cleared_fraud_check", "risk_score": 0}}
    result = process_message(message)
    assert result["status"] == "cleared"
    assert result["reason"] is None


def test_unexpected_status_is_rejected_defensively():
    message = {"data": {"transaction_id": "TXN4", "status": "unknown_status"}}
    result = process_message(message)
    assert result["status"] == "rejected"
    assert "unknown_status" in result["reason"]


def test_write_result_creates_json_file(tmp_path):
    result = {"transaction_id": "TXN5", "status": "cleared", "reason": None, "processed_at": "2026-03-16T10:00:00Z"}
    results_dir = tmp_path / "results"
    path = write_result(result, results_dir)

    assert path.exists()
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["transaction_id"] == "TXN5"
    assert saved["status"] == "cleared"
