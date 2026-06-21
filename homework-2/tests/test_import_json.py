import io
import json
import pathlib

import pytest

from src.importer import import_records, parse_json

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


class TestParseJson:
    def test_valid_json_array_returns_all_records(self):
        data = (FIXTURES / "sample_tickets.json").read_bytes()
        records = parse_json(data)
        assert len(records) == 5
        assert all("customer_email" in r for r in records)

    def test_tickets_wrapper_object_parsed_correctly(self):
        payload = {
            "tickets": [
                {
                    "customer_id": "j1",
                    "customer_email": "a@example.com",
                    "customer_name": "Alice",
                    "subject": "Login issue",
                    "description": "Cannot log in to my account since the update last week.",
                }
            ]
        }
        records = parse_json(json.dumps(payload).encode())
        assert len(records) == 1
        assert records[0]["customer_email"] == "a@example.com"

    def test_data_key_wrapper_parsed_correctly(self):
        payload = {"data": [{"customer_id": "d1"}]}
        records = parse_json(json.dumps(payload).encode())
        assert len(records) == 1

    def test_invalid_json_syntax_raises_exception(self):
        with pytest.raises(Exception):
            parse_json(b"{ this is : not valid json }")

    def test_one_invalid_record_partial_success(self):
        payload = [
            {
                "customer_id": "j1",
                "customer_email": "alice@example.com",
                "customer_name": "Alice",
                "subject": "Valid ticket",
                "description": "This description is long enough to pass all validation rules easily.",
            },
            {
                "customer_id": "j2",
                "customer_email": "not-an-email",
                "customer_name": "Bob",
                "subject": "Bad email ticket",
                "description": "This ticket has an invalid email and should fail during import.",
            },
        ]
        records = parse_json(json.dumps(payload).encode())
        _, summary = import_records(records)
        assert summary.total == 2
        assert summary.successful == 1
        assert summary.failed == 1

    def test_empty_array_returns_zero_counts(self):
        records = parse_json(b"[]")
        _, summary = import_records(records)
        assert summary.total == 0
        assert summary.successful == 0
        assert summary.failed == 0
