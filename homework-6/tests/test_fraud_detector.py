from agents.fraud_detector import _parse_hour, compute_risk_score, process_message


def make_validated_data(**overrides):
    data = {
        "transaction_id": "TXN200",
        "timestamp": "2026-03-16T12:00:00Z",
        "amount": "1500.00",
        "currency": "USD",
        "status": "validated",
        "metadata": {"country": "US"},
    }
    data.update(overrides)
    return data


def test_parse_hour_returns_none_for_malformed_timestamp():
    assert _parse_hour("not-a-timestamp") is None
    assert _parse_hour("") is None


def test_malformed_timestamp_does_not_add_odd_hour_risk():
    score = compute_risk_score(make_validated_data(timestamp="not-a-timestamp"))
    assert score == 0


def test_low_value_daytime_domestic_has_low_score():
    score = compute_risk_score(make_validated_data())
    assert score == 0


def test_high_value_adds_fifty():
    score = compute_risk_score(make_validated_data(amount="25000.00"))
    assert score >= 50


def test_odd_hour_adds_twenty():
    score = compute_risk_score(make_validated_data(timestamp="2026-03-16T02:47:00Z"))
    assert score == 20


def test_cross_border_adds_fifteen():
    score = compute_risk_score(make_validated_data(metadata={"country": "DE"}))
    assert score == 15


def test_combined_risk_factors_flag_for_review():
    data = make_validated_data(amount="75000.00", timestamp="2026-03-16T03:00:00Z", metadata={"country": "GB"})
    score = compute_risk_score(data)
    assert score == 85


def test_process_message_flags_high_risk_transaction():
    message = {"data": make_validated_data(amount="25000.00")}
    result = process_message(message)
    assert result["data"]["status"] == "flagged_for_review"
    assert result["data"]["risk_score"] >= 50
    assert result["target_agent"] == "compliance_checker"


def test_process_message_clears_low_risk_transaction():
    message = {"data": make_validated_data()}
    result = process_message(message)
    assert result["data"]["status"] == "cleared_fraud_check"


def test_process_message_passes_through_rejected_transactions():
    message = {"data": {"transaction_id": "TXN_BAD", "status": "rejected", "reason": "missing field"}}
    result = process_message(message)
    assert result["data"]["status"] == "rejected"
    assert "risk_score" not in result["data"]
    assert result["target_agent"] == "compliance_checker"
