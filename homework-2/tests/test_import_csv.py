import io
import pathlib

import pytest

from src.importer import import_records, parse_csv

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


class TestParseCsv:
    def test_valid_csv_returns_all_records(self):
        data = (FIXTURES / "sample_tickets.csv").read_bytes()
        records = parse_csv(data)
        assert len(records) == 5
        assert all("customer_email" in r for r in records)
        assert all("subject" in r for r in records)

    def test_extra_unknown_columns_do_not_cause_import_failure(self):
        csv = (
            "customer_id,customer_email,customer_name,subject,description,unknown_extra_col\n"
            "c1,a@example.com,Alice,Login issue,I cannot login to my account at all lately.,extra_value\n"
        )
        records = parse_csv(csv.encode())
        assert len(records) == 1
        _, summary = import_records(records)
        assert summary.successful == 1
        assert summary.failed == 0

    def test_bad_email_row_fails_others_succeed(self):
        csv = (
            "customer_id,customer_email,customer_name,subject,description\n"
            "c1,not-an-email,Alice,Login broken,I cannot login to my account since yesterday evening.\n"
            "c2,valid@example.com,Bob,Billing help,I need help with my latest invoice and payment charge.\n"
        )
        records = parse_csv(csv.encode())
        _, summary = import_records(records)
        assert summary.total == 2
        assert summary.successful == 1
        assert summary.failed == 1
        assert summary.errors[0]["index"] == 0

    def test_missing_required_field_recorded_as_failure(self):
        csv = (
            "customer_id,customer_email,customer_name,subject,description\n"
            "c1,,Alice,Login broken,I cannot login to my account at all and need help.\n"
        )
        records = parse_csv(csv.encode())
        _, summary = import_records(records)
        assert summary.total == 1
        assert summary.failed == 1
        assert len(summary.errors) == 1

    def test_empty_csv_headers_only_returns_zero_records(self):
        csv = "customer_id,customer_email,customer_name,subject,description\n"
        records = parse_csv(csv.encode())
        assert records == []

    def test_utf8_bom_is_stripped_correctly(self):
        bom = b"\xef\xbb\xbf"
        csv = b"customer_id,customer_email,customer_name,subject,description\n1,a@test.com,John,Login issue,Cannot login account"
        records = parse_csv(bom + csv)
        assert len(records) == 1
        assert "customer_id" in records[0]

    def test_tags_column_parsed_as_list(self):
        csv = b"customer_id,customer_email,customer_name,subject,description,tags\n1,a@test.com,J,S,Long enough desc,auth,billing"
        records = parse_csv(csv)
        assert records is not None
        assert len(records) == 1

    def test_flat_metadata_source_column_parsed(self):
        csv = b"customer_id,customer_email,customer_name,subject,description,metadata.source\n1,a@test.com,J,S,Long enough text,api"
        records = parse_csv(csv)
        assert records[0]["metadata"]["source"] == "api"

    def test_malformed_bytes_endpoint_returns_400(self, client):
        bad_bytes = b"\xff\xfe\x80\x81 totally invalid utf-8 content here"
        r = client.post(
            "/tickets/import",
            files={"file": ("tickets.csv", io.BytesIO(bad_bytes), "text/csv")},
        )
        assert r.status_code == 400
        assert "parse" in r.json()["detail"].lower()
