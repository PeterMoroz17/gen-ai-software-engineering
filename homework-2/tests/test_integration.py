import io
import threading

import pytest
from fastapi.testclient import TestClient

from src.main import app


class TestIntegration:
    def test_full_ticket_lifecycle(self, client, sample_payload):
        # Create
        r = client.post("/tickets", json=sample_payload)
        assert r.status_code == 201
        tid = r.json()["id"]

        # Read
        r = client.get(f"/tickets/{tid}")
        assert r.status_code == 200
        assert r.json()["status"] == "new"

        # Update to in_progress
        r = client.put(f"/tickets/{tid}", json={"status": "in_progress"})
        assert r.status_code == 200
        assert r.json()["status"] == "in_progress"

        # Resolve
        r = client.put(f"/tickets/{tid}", json={"status": "resolved"})
        assert r.status_code == 200
        assert r.json()["resolved_at"] is not None

        # Delete
        assert client.delete(f"/tickets/{tid}").status_code == 204

        # Confirm gone
        assert client.get(f"/tickets/{tid}").status_code == 404

    def test_bulk_csv_import_with_auto_classify(self, client):
        csv_rows = "\n".join([
            "customer_id,customer_email,customer_name,subject,description",
            "c1,a@example.com,Alice,Production down critical outage,The system has crashed completely and data loss is occurring right now.",
            "c2,b@example.com,Bob,Invoice refund request billing,I was charged twice for my subscription and need a refund of the fee.",
            "c3,c@example.com,Carol,Feature request for dark mode,It would be a nice enhancement to add a dark theme option to settings.",
        ])
        r = client.post(
            "/tickets/import?auto_classify=true",
            files={"file": ("t.csv", io.BytesIO(csv_rows.encode()), "text/csv")},
        )
        assert r.status_code == 200
        assert r.json()["successful"] == 3

        tickets = client.get("/tickets").json()
        assert len(tickets) == 3
        assert all(t["category"] is not None for t in tickets)
        assert all(t["priority"] is not None for t in tickets)
        assert all(t["classification_confidence"] is not None for t in tickets)

    def test_concurrent_ticket_creation_all_stored_uniquely(self, sample_payload):
        results = []
        errors = []

        def create_ticket():
            c = TestClient(app)
            try:
                r = c.post("/tickets", json=sample_payload)
                results.append(r.status_code)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=create_ticket) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread errors: {errors}"
        assert results.count(201) == 20

        verify_client = TestClient(app)
        all_tickets = verify_client.get("/tickets").json()
        ids = [t["id"] for t in all_tickets]
        assert len(ids) == 20
        assert len(set(ids)) == 20  # all UUIDs unique

    def test_combined_category_and_priority_filter(self, client, sample_payload):
        client.post("/tickets", json={**sample_payload, "category": "billing_question", "priority": "high"})
        client.post("/tickets", json={**sample_payload, "customer_email": "b@x.com", "category": "billing_question", "priority": "low"})
        client.post("/tickets", json={**sample_payload, "customer_email": "c@x.com", "category": "technical_issue", "priority": "high"})

        r = client.get("/tickets", params={"category": "billing_question", "priority": "high"})
        assert r.status_code == 200
        results = r.json()
        assert len(results) == 1
        assert results[0]["category"] == "billing_question"
        assert results[0]["priority"] == "high"

    def test_json_import_then_list(self, client):
        data = b'[{"customer_id":"1","customer_email":"a@test.com","customer_name":"J","subject":"Hello","description":"Long enough description"}]'
        client.post("/tickets/import", files={"file": ("a.json", data, "application/json")})
        assert len(client.get("/tickets").json()) == 1

    def test_json_import_with_auto_classify(self, client):
        data = b'[{"customer_id":"1","customer_email":"a@test.com","customer_name":"J","subject":"login","description":"password reset issue here"}]'
        client.post("/tickets/import?auto_classify=true", files={"file": ("a.json", data, "application/json")})
        ticket = client.get("/tickets").json()[0]
        assert ticket["category"] == "account_access"

    def test_multiple_tickets_stored_and_counted(self, client, ticket_payload):
        for _ in range(3):
            client.post("/tickets", json=ticket_payload)
        assert len(client.get("/tickets").json()) == 3

    def test_mixed_import_partial_success_and_stored_count(self, client):
        csv = "\n".join([
            "customer_id,customer_email,customer_name,subject,description",
            "c1,alice@example.com,Alice,Valid ticket one,This description has enough characters to be fully valid here.",
            "c2,bob@example.com,Bob,Valid ticket two,Another valid ticket description with more than ten characters.",
            "c3,not-an-email,Carol,Bad email row,This row has an invalid email address and must fail validation.",
            "c4,dave@example.com,Dave,Valid ticket three,Third valid ticket description that has sufficient character length.",
            "c5,,Eve,Missing email row,This row is missing the required email field and should fail here.",
        ])
        r = client.post(
            "/tickets/import",
            files={"file": ("t.csv", io.BytesIO(csv.encode()), "text/csv")},
        )
        assert r.status_code == 200
        s = r.json()
        assert s["total"] == 5
        assert s["successful"] == 3
        assert s["failed"] == 2
        assert len(s["errors"]) == 2

        stored = client.get("/tickets").json()
        assert len(stored) == 3
