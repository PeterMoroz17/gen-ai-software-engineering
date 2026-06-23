import io
import pathlib

import pytest

from src.importer import import_records, parse_xml

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


class TestParseXml:
    def test_valid_xml_returns_all_records(self):
        data = (FIXTURES / "sample_tickets.xml").read_bytes()
        records = parse_xml(data)
        assert len(records) == 5
        assert all("customer_email" in r for r in records)

    def test_nested_metadata_and_tags_correctly_unpacked(self):
        xml = b"""<tickets>
          <ticket>
            <customer_id>x1</customer_id>
            <customer_email>alice@example.com</customer_email>
            <customer_name>Alice</customer_name>
            <subject>Test with nested fields</subject>
            <description>Testing that nested metadata and tags are correctly parsed by the XML importer.</description>
            <tags><tag>auth</tag><tag>vip</tag></tags>
            <metadata><source>web_form</source><device_type>desktop</device_type></metadata>
          </ticket>
        </tickets>"""
        records = parse_xml(xml)
        assert len(records) == 1
        r = records[0]
        assert r["tags"] == ["auth", "vip"]
        assert isinstance(r["metadata"], dict)
        assert r["metadata"]["source"] == "web_form"
        assert r["metadata"]["device_type"] == "desktop"

    def test_single_ticket_as_root_element(self):
        records = parse_xml(b"<ticket/>")
        assert len(records) == 1

    def test_malformed_xml_raises_exception(self):
        with pytest.raises(Exception):
            parse_xml(b"<tickets><ticket><unclosed_tag>no closing</ticket></tickets>")

    def test_one_invalid_ticket_partial_success(self):
        xml = b"""<tickets>
          <ticket>
            <customer_id>x1</customer_id>
            <customer_email>alice@example.com</customer_email>
            <customer_name>Alice</customer_name>
            <subject>Valid ticket</subject>
            <description>This is a perfectly valid ticket with a description that is long enough.</description>
          </ticket>
          <ticket>
            <customer_id>x2</customer_id>
            <customer_email>not-an-email</customer_email>
            <customer_name>Bob</customer_name>
            <subject>Invalid email</subject>
            <description>This ticket has an invalid email address and should fail validation check.</description>
          </ticket>
        </tickets>"""
        records = parse_xml(xml)
        _, summary = import_records(records)
        assert summary.total == 2
        assert summary.successful == 1
        assert summary.failed == 1

    def test_empty_tickets_element_returns_zero_records(self):
        records = parse_xml(b"<tickets></tickets>")
        _, summary = import_records(records)
        assert summary.total == 0
        assert summary.successful == 0
        assert summary.failed == 0
