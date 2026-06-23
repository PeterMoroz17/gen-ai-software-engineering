import io

import pytest
from fastapi.testclient import TestClient


class TestCreateTicket:
    def test_returns_201_with_uuid(self, client, sample_payload):
        r = client.post("/tickets", json=sample_payload)
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert len(data["id"]) == 36  # UUID hyphen format

    def test_invalid_email_returns_422(self, client, sample_payload):
        sample_payload["customer_email"] = "not-an-email"
        r = client.post("/tickets", json=sample_payload)
        assert r.status_code == 422

    def test_missing_required_field_returns_422(self, client, sample_payload):
        del sample_payload["subject"]
        r = client.post("/tickets", json=sample_payload)
        assert r.status_code == 422


class TestCreateTicketAutoClassify:
    def test_auto_classify_on_create_sets_category(self, client, ticket_payload):
        r = client.post("/tickets?auto_classify=true", json=ticket_payload)
        assert r.status_code == 201
        assert r.json()["category"] == "account_access"


class TestListTickets:
    def test_returns_all_tickets(self, client, sample_payload):
        client.post("/tickets", json=sample_payload)
        client.post("/tickets", json={**sample_payload, "customer_email": "bob@example.com"})
        r = client.get("/tickets")
        assert r.status_code == 200
        assert len(r.json()) == 2

    def test_empty_store_returns_empty_list(self, client):
        r = client.get("/tickets")
        assert r.status_code == 200
        assert r.json() == []

    def test_filter_by_category_returns_only_matching(self, client, sample_payload):
        client.post("/tickets", json={**sample_payload, "category": "billing_question"})
        client.post("/tickets", json={**sample_payload, "customer_email": "b@example.com", "category": "technical_issue"})
        r = client.get("/tickets", params={"category": "billing_question"})
        assert r.status_code == 200
        results = r.json()
        assert len(results) == 1
        assert results[0]["category"] == "billing_question"


class TestGetTicket:
    def test_get_by_id_returns_200_with_data(self, client, sample_payload):
        create_r = client.post("/tickets", json=sample_payload)
        tid = create_r.json()["id"]
        r = client.get(f"/tickets/{tid}")
        assert r.status_code == 200
        assert r.json()["id"] == tid
        assert r.json()["customer_email"] == sample_payload["customer_email"]

    def test_get_nonexistent_returns_404(self, client):
        r = client.get("/tickets/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 404


class TestUpdateTicket:
    def test_update_assigned_to_field(self, client, ticket_payload):
        tid = client.post("/tickets", json=ticket_payload).json()["id"]
        r = client.put(f"/tickets/{tid}", json={"assigned_to": "Bob"})
        assert r.status_code == 200
        assert r.json()["assigned_to"] == "Bob"

    def test_update_status_returns_200_with_new_status(self, client, sample_payload):
        tid = client.post("/tickets", json=sample_payload).json()["id"]
        r = client.put(f"/tickets/{tid}", json={"status": "in_progress"})
        assert r.status_code == 200
        assert r.json()["status"] == "in_progress"
        assert r.json()["updated_at"] is not None

    def test_update_to_resolved_sets_resolved_at(self, client, sample_payload):
        tid = client.post("/tickets", json=sample_payload).json()["id"]
        r = client.put(f"/tickets/{tid}", json={"status": "resolved"})
        assert r.status_code == 200
        assert r.json()["resolved_at"] is not None


class TestDeleteTicket:
    def test_delete_returns_204_then_get_returns_404(self, client, sample_payload):
        tid = client.post("/tickets", json=sample_payload).json()["id"]
        r = client.delete(f"/tickets/{tid}")
        assert r.status_code == 204
        assert client.get(f"/tickets/{tid}").status_code == 404

    def test_delete_nonexistent_returns_404(self, client):
        r = client.delete("/tickets/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 404


class TestImportEndpoint:
    def test_import_valid_csv_returns_all_successful(self, client):
        csv_data = (
            "customer_id,customer_email,customer_name,subject,description\n"
            "c1,a@example.com,Alice,Login issue,I cannot login to my account since yesterday evening.\n"
            "c2,b@example.com,Bob,Billing query,I have a question about the latest invoice charge amount.\n"
        )
        r = client.post(
            "/tickets/import",
            files={"file": ("tickets.csv", io.BytesIO(csv_data.encode()), "text/csv")},
        )
        assert r.status_code == 200
        s = r.json()
        assert s["total"] == 2
        assert s["successful"] == 2
        assert s["failed"] == 0
