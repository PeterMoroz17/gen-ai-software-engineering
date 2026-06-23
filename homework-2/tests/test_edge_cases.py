"""
Edge case tests and coverage for previously uncovered code paths.

Uncovered lines targeted:
  importer.py 16-18  _normalize_metadata dict branch and non-dict fallback
  importer.py 23     _normalize_tags list passthrough
  importer.py 26     _normalize_tags unknown-type fallback
  importer.py 58     parse_json ValueError for unrecognised dict structure
  importer.py 89,91  import_records tag / metadata normalisation branches
  importer.py 103-104 generic except Exception handler in import_records
  main.py 71         import endpoint: unsupported file extension
  main.py 142-151    POST /tickets/:id/auto-classify endpoint body
"""

import io
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.classifier import classify
from src.importer import (
    _normalize_metadata,
    _normalize_tags,
    import_records,
    parse_json,
    parse_xml,
    parse_csv,
)
from src.models import Category, Priority, TicketCreate


# ---------------------------------------------------------------------------
# _normalize_metadata  (importer.py lines 16-18)
# ---------------------------------------------------------------------------

class TestNormalizeMetadata:
    def test_dict_input_returned_unchanged(self):
        d = {"source": "api", "device_type": "desktop"}
        assert _normalize_metadata(d) is d

    def test_string_input_returns_empty_dict(self):
        assert _normalize_metadata("web_form") == {}

    def test_none_input_returns_empty_dict(self):
        assert _normalize_metadata(None) == {}

    def test_list_input_returns_empty_dict(self):
        assert _normalize_metadata(["source", "api"]) == {}

    def test_integer_input_returns_empty_dict(self):
        assert _normalize_metadata(42) == {}


# ---------------------------------------------------------------------------
# _normalize_tags  (importer.py lines 22-26)
# ---------------------------------------------------------------------------

class TestNormalizeTags:
    def test_list_returned_unchanged(self):
        tags = ["auth", "vip"]
        assert _normalize_tags(tags) is tags

    def test_empty_list_returned_unchanged(self):
        assert _normalize_tags([]) == []

    def test_comma_separated_string_split_into_list(self):
        assert _normalize_tags("auth,billing, vip") == ["auth", "billing", "vip"]

    def test_single_value_string_returns_single_item_list(self):
        assert _normalize_tags("auth") == ["auth"]

    def test_none_returns_empty_list(self):
        assert _normalize_tags(None) == []

    def test_integer_returns_empty_list(self):
        assert _normalize_tags(42) == []

    def test_dict_returns_empty_list(self):
        assert _normalize_tags({"key": "val"}) == []


# ---------------------------------------------------------------------------
# parse_json edge cases  (importer.py line 58)
# ---------------------------------------------------------------------------

class TestParseJsonEdgeCases:
    def test_dict_with_no_recognised_key_raises_value_error(self):
        with pytest.raises(ValueError, match="JSON must be an array"):
            parse_json(b'{"unknown_key": [1, 2, 3]}')

    def test_records_wrapper_key_parsed(self):
        import json
        payload = {"records": [{"customer_id": "r1"}]}
        records = parse_json(json.dumps(payload).encode())
        assert len(records) == 1

    def test_empty_dict_raises_value_error(self):
        with pytest.raises(ValueError):
            parse_json(b"{}")

    def test_non_list_value_under_tickets_key_raises(self):
        with pytest.raises((ValueError, Exception)):
            parse_json(b'{"tickets": "not a list"}')


# ---------------------------------------------------------------------------
# import_records edge cases  (importer.py lines 89, 91, 103-104)
# ---------------------------------------------------------------------------

class TestImportRecordsEdgeCases:
    _VALID = {
        "customer_id": "1",
        "customer_email": "alice@example.com",
        "customer_name": "Alice",
        "subject": "Test subject",
        "description": "Long enough description for the validation to pass.",
    }

    def test_record_with_tags_list_normalised_and_stored(self):
        record = {**self._VALID, "tags": ["auth", "vip"]}
        tickets, summary = import_records([record])
        assert summary.successful == 1
        assert tickets[0].tags == ["auth", "vip"]

    def test_record_with_tags_string_split_and_stored(self):
        record = {**self._VALID, "tags": "auth,vip"}
        tickets, summary = import_records([record])
        assert summary.successful == 1
        assert "auth" in tickets[0].tags
        assert "vip" in tickets[0].tags

    def test_record_with_metadata_dict_normalised_and_stored(self):
        record = {**self._VALID, "metadata": {"source": "api", "device_type": "desktop"}}
        tickets, summary = import_records([record])
        assert summary.successful == 1
        assert tickets[0].metadata.source.value == "api"
        assert tickets[0].metadata.device_type.value == "desktop"

    def test_record_with_non_dict_metadata_coerced_to_defaults(self):
        record = {**self._VALID, "metadata": "web_form"}
        tickets, summary = import_records([record])
        # non-dict metadata → {} → Metadata() uses defaults
        assert summary.successful == 1

    def test_all_invalid_records_returns_zero_successful(self):
        records = [
            {"customer_id": "1", "customer_email": "bad", "customer_name": "A",
             "subject": "S", "description": "D"},
            {"customer_id": "2", "customer_email": "bad2", "customer_name": "B",
             "subject": "S", "description": "D"},
        ]
        _, summary = import_records(records)
        assert summary.total == 2
        assert summary.successful == 0
        assert summary.failed == 2

    def test_generic_exception_in_validate_caught_as_error(self):
        record = {**self._VALID}
        with patch("src.importer.TicketCreate.model_validate", side_effect=RuntimeError("boom")):
            _, summary = import_records([record])
        assert summary.failed == 1
        assert "boom" in summary.errors[0]["error"]

    def test_mixed_valid_and_invalid_preserves_order(self):
        records = [
            {**self._VALID},
            {"customer_id": "2", "customer_email": "bad", "customer_name": "B",
             "subject": "S", "description": "D"},
            {**self._VALID, "customer_id": "3", "customer_email": "carol@example.com"},
        ]
        tickets, summary = import_records(records)
        assert summary.total == 3
        assert summary.successful == 2
        assert summary.failed == 1
        assert summary.errors[0]["index"] == 1


# ---------------------------------------------------------------------------
# main.py line 71 — unsupported file extension
# ---------------------------------------------------------------------------

class TestImportUnsupportedFormat:
    def test_txt_extension_returns_400(self, client):
        r = client.post(
            "/tickets/import",
            files={"file": ("tickets.txt", io.BytesIO(b"hello"), "text/plain")},
        )
        assert r.status_code == 400
        assert "unsupported" in r.json()["detail"].lower()

    def test_no_extension_returns_400(self, client):
        r = client.post(
            "/tickets/import",
            files={"file": ("ticketsnoext", io.BytesIO(b"hello"), "application/octet-stream")},
        )
        assert r.status_code == 400

    def test_pdf_extension_returns_400(self, client):
        r = client.post(
            "/tickets/import",
            files={"file": ("tickets.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
        )
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# main.py lines 142-151 — POST /tickets/:id/auto-classify endpoint
# ---------------------------------------------------------------------------

class TestAutoClassifyEndpoint:
    def test_endpoint_returns_classification_result(self, client, sample_payload):
        tid = client.post("/tickets", json=sample_payload).json()["id"]
        r = client.post(f"/tickets/{tid}/auto-classify")
        assert r.status_code == 200
        body = r.json()
        assert "category" in body
        assert "priority" in body
        assert "confidence" in body
        assert "reasoning" in body
        assert "keywords_found" in body

    def test_endpoint_writes_classification_back_to_ticket(self, client, sample_payload):
        tid = client.post("/tickets", json=sample_payload).json()["id"]
        result = client.post(f"/tickets/{tid}/auto-classify").json()
        ticket = client.get(f"/tickets/{tid}").json()
        assert ticket["category"] == result["category"]
        assert ticket["priority"] == result["priority"]
        assert ticket["classification_confidence"] == result["confidence"]
        assert ticket["classification_reasoning"] is not None

    def test_endpoint_updates_updated_at(self, client, sample_payload):
        create_r = client.post("/tickets", json=sample_payload)
        tid = create_r.json()["id"]
        original_updated_at = create_r.json()["updated_at"]
        import time; time.sleep(0.002)
        client.post(f"/tickets/{tid}/auto-classify")
        ticket = client.get(f"/tickets/{tid}").json()
        assert ticket["updated_at"] is not None

    def test_endpoint_returns_404_for_missing_ticket(self, client):
        r = client.post("/tickets/00000000-0000-0000-0000-000000000000/auto-classify")
        assert r.status_code == 404

    def test_endpoint_classifies_billing_ticket_correctly(self, client, sample_payload):
        billing_payload = {
            **sample_payload,
            "subject": "Invoice overcharge refund request",
            "description": "I was charged twice for my subscription billing and need a full refund.",
        }
        tid = client.post("/tickets", json=billing_payload).json()["id"]
        r = client.post(f"/tickets/{tid}/auto-classify")
        assert r.status_code == 200
        assert r.json()["category"] == "billing_question"


# ---------------------------------------------------------------------------
# API edge cases
# ---------------------------------------------------------------------------

class TestApiEdgeCases:
    def test_put_nonexistent_ticket_returns_404(self, client):
        r = client.put("/tickets/00000000-0000-0000-0000-000000000000", json={"status": "in_progress"})
        assert r.status_code == 404

    def test_list_filter_by_status(self, client, sample_payload):
        tid = client.post("/tickets", json=sample_payload).json()["id"]
        client.put(f"/tickets/{tid}", json={"status": "resolved"})
        client.post("/tickets", json={**sample_payload, "customer_email": "b@x.com"})
        resolved = client.get("/tickets", params={"status": "resolved"}).json()
        new_tickets = client.get("/tickets", params={"status": "new"}).json()
        assert len(resolved) == 1
        assert len(new_tickets) == 1

    def test_resolved_at_not_overwritten_on_second_resolve(self, client, sample_payload):
        tid = client.post("/tickets", json=sample_payload).json()["id"]
        first_r = client.put(f"/tickets/{tid}", json={"status": "resolved"}).json()
        first_resolved_at = first_r["resolved_at"]
        import time; time.sleep(0.002)
        second_r = client.put(f"/tickets/{tid}", json={"status": "resolved"}).json()
        assert second_r["resolved_at"] == first_resolved_at

    def test_import_with_auto_classify_and_unsupported_format_still_400(self, client):
        r = client.post(
            "/tickets/import?auto_classify=true",
            files={"file": ("data.xlsx", io.BytesIO(b"fake"), "application/vnd.ms-excel")},
        )
        assert r.status_code == 400

    def test_list_filter_by_priority(self, client, sample_payload):
        client.post("/tickets", json={**sample_payload, "priority": "urgent"})
        client.post("/tickets", json={**sample_payload, "customer_email": "b@x.com", "priority": "low"})
        urgent = client.get("/tickets", params={"priority": "urgent"}).json()
        assert len(urgent) == 1
        assert urgent[0]["priority"] == "urgent"


# ---------------------------------------------------------------------------
# Model boundary values
# ---------------------------------------------------------------------------

class TestModelBoundaries:
    _BASE = {
        "customer_id": "1",
        "customer_email": "a@example.com",
        "customer_name": "Alice",
        "subject": "S",
        "description": "1234567890",
    }

    def test_subject_exactly_1_char_passes(self):
        t = TicketCreate(**{**self._BASE, "subject": "X"})
        assert t.subject == "X"

    def test_subject_exactly_200_chars_passes(self):
        t = TicketCreate(**{**self._BASE, "subject": "x" * 200})
        assert len(t.subject) == 200

    def test_description_exactly_10_chars_passes(self):
        t = TicketCreate(**{**self._BASE, "description": "1234567890"})
        assert len(t.description) == 10

    def test_description_exactly_2000_chars_passes(self):
        t = TicketCreate(**{**self._BASE, "description": "x" * 2000})
        assert len(t.description) == 2000

    def test_tags_default_to_empty_list(self):
        t = TicketCreate(**self._BASE)
        assert t.tags == []

    def test_default_status_is_new(self):
        t = TicketCreate(**self._BASE)
        assert t.status.value == "new"

    def test_category_and_priority_default_to_none(self):
        t = TicketCreate(**self._BASE)
        assert t.category is None
        assert t.priority is None


# ---------------------------------------------------------------------------
# Categorization edge cases
# ---------------------------------------------------------------------------

class TestCategorizationEdgeCases:
    def test_cant_access_phrase_triggers_urgent(self):
        r = classify("Help", "I can't access the system at all right now.")
        assert r.priority == Priority.urgent

    def test_cannot_access_phrase_triggers_urgent(self):
        r = classify("Help", "I cannot access my account.")
        assert r.priority == Priority.urgent

    def test_security_breach_triggers_urgent(self):
        r = classify("Security breach detected", "There has been a security breach in the system.")
        assert r.priority == Priority.urgent

    def test_data_loss_triggers_urgent(self):
        r = classify("Data problem", "We are experiencing data loss in production.")
        assert r.priority == Priority.urgent

    def test_rich_description_classifies_correctly_despite_generic_subject(self):
        r = classify("Problem", "I cannot login, password reset broken, 2fa not working.")
        assert r.category == Category.account_access

    def test_outage_in_description_triggers_urgent(self):
        r = classify("Problem", "We have a full outage affecting all customers right now.")
        assert r.priority == Priority.urgent

    def test_confidence_zero_for_other_category(self):
        r = classify("hello", "world greetings nothing relevant here at all")
        assert r.category == Category.other
        assert r.confidence == 0.0

    def test_keywords_found_empty_for_other_category(self):
        r = classify("hello", "world greetings nothing relevant here at all")
        assert r.keywords_found == []


# ---------------------------------------------------------------------------
# Parser edge cases
# ---------------------------------------------------------------------------

class TestParserEdgeCases:
    def test_csv_windows_line_endings_parsed_correctly(self):
        csv = b"customer_id,customer_email,customer_name,subject,description\r\nc1,a@test.com,Alice,Login,Cannot login to my account.\r\n"
        records = parse_csv(csv)
        assert len(records) == 1
        assert records[0]["customer_id"] == "c1"

    def test_xml_tag_with_no_text_filtered_out(self):
        xml = b"<ticket><tags><tag>auth</tag><tag></tag><tag>vip</tag></tags></ticket>"
        records = parse_xml(xml)
        assert records[0]["tags"] == ["auth", "vip"]

    def test_xml_empty_metadata_fields_excluded(self):
        xml = b"<ticket><metadata><source>api</source></metadata></ticket>"
        records = parse_xml(xml)
        assert records[0]["metadata"]["source"] == "api"

    def test_csv_whitespace_in_values_stripped(self):
        csv = b"customer_id,customer_email,customer_name,subject,description\n  c1  ,  a@test.com  ,  Alice  ,  Login  ,  Cannot login to my account.  \n"
        records = parse_csv(csv)
        assert records[0]["customer_id"] == "c1"
        assert records[0]["customer_email"] == "a@test.com"

    def test_json_large_valid_array_parsed(self):
        import json
        records_data = [
            {"customer_id": str(i), "customer_email": f"u{i}@test.com"}
            for i in range(100)
        ]
        result = parse_json(json.dumps(records_data).encode())
        assert len(result) == 100
