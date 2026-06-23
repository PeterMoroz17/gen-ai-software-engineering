import pytest
from pydantic import ValidationError

from src.models import Category, DeviceType, Metadata, Priority, Source, Status, TicketCreate

_BASE = {
    "customer_id": "cust-1",
    "customer_email": "alice@example.com",
    "customer_name": "Alice",
    "subject": "Test subject",
    "description": "This is a valid description with more than ten characters.",
}


class TestTicketModelValidation:
    def test_valid_ticket_create_passes(self):
        t = TicketCreate(**_BASE)
        assert t.customer_email == "alice@example.com"
        assert t.status == Status.new

    def test_blank_customer_id_fails(self):
        with pytest.raises(ValidationError):
            TicketCreate(**{**_BASE, "customer_id": "   "})

    def test_blank_customer_name_fails(self):
        with pytest.raises(ValidationError):
            TicketCreate(**{**_BASE, "customer_name": "   "})

    def test_subject_empty_string_fails(self):
        with pytest.raises(ValidationError) as exc_info:
            TicketCreate(**{**_BASE, "subject": ""})
        assert "subject" in str(exc_info.value)

    def test_subject_over_200_chars_fails(self):
        with pytest.raises(ValidationError):
            TicketCreate(**{**_BASE, "subject": "x" * 201})

    def test_description_under_10_chars_fails(self):
        with pytest.raises(ValidationError) as exc_info:
            TicketCreate(**{**_BASE, "description": "too short"})
        assert "description" in str(exc_info.value)

    def test_description_over_2000_chars_fails(self):
        with pytest.raises(ValidationError):
            TicketCreate(**{**_BASE, "description": "x" * 2001})

    def test_invalid_email_format_fails(self):
        with pytest.raises(ValidationError) as exc_info:
            TicketCreate(**{**_BASE, "customer_email": "not-an-email"})
        assert "customer_email" in str(exc_info.value)

    def test_invalid_category_enum_fails(self):
        with pytest.raises(ValidationError) as exc_info:
            TicketCreate(**{**_BASE, "category": "nonexistent_category"})
        assert "category" in str(exc_info.value)

    def test_invalid_priority_enum_fails(self):
        with pytest.raises(ValidationError) as exc_info:
            TicketCreate(**{**_BASE, "priority": "super_urgent"})
        assert "priority" in str(exc_info.value)

    def test_invalid_metadata_source_enum_fails(self):
        with pytest.raises(ValidationError) as exc_info:
            TicketCreate(**{**_BASE, "metadata": {"source": "carrier_pigeon"}})
        assert "source" in str(exc_info.value)
