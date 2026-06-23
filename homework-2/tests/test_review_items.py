"""
Tests addressing gaps identified in the code review:
  - UUID format validation
  - Confidence score quality (not just range)
  - Manual category override persistence
  - Decision logging (reasoning populated and meaningful)
  - Three-way combined filter (category + priority + status)
  - updated_at timestamp actually changes
  - resolved_at behaviour when unresolving
  - Full status lifecycle (waiting_customer, closed)
  - CSV quoted commas / multiline values
  - JSON null optional fields
  - XML minimal-node tickets
  - XML import with auto_classify=true
  - Performance assertions with concrete time thresholds
"""

import io
import time
import uuid as _uuid

import pytest
from fastapi.testclient import TestClient

from src.classifier import classify
from src.importer import import_records, parse_csv, parse_xml
from src.models import Category


# ---------------------------------------------------------------------------
# UUID format validation
# ---------------------------------------------------------------------------

class TestUuidValidation:
    def test_created_ticket_id_is_valid_uuid(self, client, sample_payload):
        r = client.post("/tickets", json=sample_payload)
        assert r.status_code == 201
        ticket_id = r.json()["id"]
        parsed = _uuid.UUID(ticket_id)          # raises ValueError if not a valid UUID
        assert str(parsed) == ticket_id         # round-trip confirms canonical format

    def test_imported_tickets_all_have_valid_uuids(self, client):
        csv = (
            "customer_id,customer_email,customer_name,subject,description\n"
            "c1,a@test.com,Alice,Login broken,I cannot login to my account at all.\n"
            "c2,b@test.com,Bob,Billing query,I have a question about my latest invoice.\n"
        )
        client.post("/tickets/import",
                    files={"file": ("t.csv", io.BytesIO(csv.encode()), "text/csv")})
        for ticket in client.get("/tickets").json():
            _uuid.UUID(ticket["id"])            # raises ValueError if malformed

    def test_concurrent_create_produces_unique_uuids(self, sample_payload):
        import threading
        ids = []

        def create():
            c = TestClient(__import__("src.main", fromlist=["app"]).app)
            r = c.post("/tickets", json=sample_payload)
            ids.append(r.json()["id"])

        threads = [threading.Thread(target=create) for _ in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert len(ids) == 20
        assert len(set(ids)) == 20              # no duplicates
        for tid in ids:
            _uuid.UUID(tid)                     # each is a valid UUID


# ---------------------------------------------------------------------------
# Confidence score quality
# ---------------------------------------------------------------------------

class TestConfidenceQuality:
    def test_relevant_keywords_produce_higher_confidence_than_generic(self):
        relevant = classify(
            "login password reset account",
            "I cannot login and the password reset email is not arriving in my inbox.",
        )
        generic = classify("hello", "world nothing specific here at all")
        assert relevant.confidence > generic.confidence

    def test_confidence_zero_only_when_no_category_keywords_match(self):
        r = classify("hello there friend", "nothing relevant to support at all here")
        assert r.category == Category.other
        assert r.confidence == 0.0

    def test_confidence_increases_with_more_keyword_hits(self):
        few_hits = classify("login", "I need help")
        many_hits = classify(
            "login password 2fa authentication",
            "locked out sign in account access credentials reset forgot",
        )
        assert many_hits.confidence >= few_hits.confidence

    def test_confidence_capped_at_1(self):
        r = classify(
            "login password 2fa locked sign in authentication account access reset forgot credentials logout",
            "login password 2fa locked sign in authentication account access reset forgot credentials logout",
        )
        assert r.confidence <= 1.0


# ---------------------------------------------------------------------------
# Manual override persistence
# ---------------------------------------------------------------------------

class TestManualOverride:
    def test_manual_category_persists_after_auto_classify(self, client, sample_payload):
        # Create and auto-classify (expects account_access for login ticket)
        tid = client.post("/tickets?auto_classify=true", json=sample_payload).json()["id"]
        assert client.get(f"/tickets/{tid}").json()["category"] is not None

        # Manually override to "other"
        client.put(f"/tickets/{tid}", json={"category": "other"})
        assert client.get(f"/tickets/{tid}").json()["category"] == "other"

    def test_unrelated_put_does_not_reclassify(self, client, sample_payload):
        tid = client.post("/tickets?auto_classify=true", json=sample_payload).json()["id"]
        original_category = client.get(f"/tickets/{tid}").json()["category"]

        # Update a field unrelated to classification
        client.put(f"/tickets/{tid}", json={"assigned_to": "Bob"})
        after = client.get(f"/tickets/{tid}").json()
        assert after["category"] == original_category  # not reclassified

    def test_override_priority_persists(self, client, sample_payload):
        tid = client.post("/tickets?auto_classify=true", json=sample_payload).json()["id"]
        client.put(f"/tickets/{tid}", json={"priority": "urgent"})
        assert client.get(f"/tickets/{tid}").json()["priority"] == "urgent"

        # Another unrelated update should not change the priority
        client.put(f"/tickets/{tid}", json={"assigned_to": "Alice"})
        assert client.get(f"/tickets/{tid}").json()["priority"] == "urgent"


# ---------------------------------------------------------------------------
# Decision logging — classification_reasoning is populated and meaningful
# ---------------------------------------------------------------------------

class TestDecisionLogging:
    def test_auto_classify_stores_non_empty_reasoning(self, client, sample_payload):
        tid = client.post("/tickets", json=sample_payload).json()["id"]
        client.post(f"/tickets/{tid}/auto-classify")
        ticket = client.get(f"/tickets/{tid}").json()
        assert ticket["classification_reasoning"] is not None
        assert len(ticket["classification_reasoning"]) > 10

    def test_reasoning_mentions_matched_keywords(self, client, sample_payload):
        billing_payload = {
            **sample_payload,
            "subject": "Invoice overcharge refund",
            "description": "I was billed twice and need a refund for the subscription charge.",
        }
        tid = client.post("/tickets", json=billing_payload).json()["id"]
        result = client.post(f"/tickets/{tid}/auto-classify").json()
        assert "Matched" in result["reasoning"]
        assert len(result["keywords_found"]) > 0

    def test_create_with_auto_classify_stores_reasoning(self, client, sample_payload):
        r = client.post("/tickets?auto_classify=true", json=sample_payload)
        ticket = r.json()
        assert ticket["classification_reasoning"] is not None
        assert ticket["classification_confidence"] is not None

    def test_reasoning_differs_by_ticket_content(self, client, sample_payload):
        login_payload = {**sample_payload,
                         "subject": "Login broken", "description": "Cannot login password reset."}
        billing_payload = {**sample_payload, "customer_email": "b@x.com",
                           "subject": "Invoice refund", "description": "Billing refund for subscription."}
        r1 = classify(login_payload["subject"], login_payload["description"])
        r2 = classify(billing_payload["subject"], billing_payload["description"])
        assert r1.reasoning != r2.reasoning


# ---------------------------------------------------------------------------
# Three-way combined filter
# ---------------------------------------------------------------------------

class TestThreeWayFilter:
    def test_category_priority_status_all_applied(self, client, sample_payload):
        # billing/high/new
        client.post("/tickets", json={
            **sample_payload,
            "category": "billing_question", "priority": "high", "status": "new",
        })
        # billing/high/in_progress
        client.post("/tickets", json={
            **sample_payload, "customer_email": "b@x.com",
            "category": "billing_question", "priority": "high", "status": "in_progress",
        })
        # billing/low/new
        client.post("/tickets", json={
            **sample_payload, "customer_email": "c@x.com",
            "category": "billing_question", "priority": "low", "status": "new",
        })
        # technical/high/new
        client.post("/tickets", json={
            **sample_payload, "customer_email": "d@x.com",
            "category": "technical_issue", "priority": "high", "status": "new",
        })

        r = client.get("/tickets", params={
            "category": "billing_question", "priority": "high", "status": "new"
        })
        results = r.json()
        assert len(results) == 1
        t = results[0]
        assert t["category"] == "billing_question"
        assert t["priority"] == "high"
        assert t["status"] == "new"

    def test_no_results_when_filter_matches_nothing(self, client, sample_payload):
        client.post("/tickets", json={**sample_payload, "category": "billing_question"})
        r = client.get("/tickets", params={"category": "technical_issue"})
        assert r.json() == []


# ---------------------------------------------------------------------------
# Datetime field lifecycle
# ---------------------------------------------------------------------------

class TestDatetimeFields:
    def test_created_at_and_updated_at_set_on_creation(self, client, sample_payload):
        r = client.post("/tickets", json=sample_payload)
        t = r.json()
        assert t["created_at"] is not None
        assert t["updated_at"] is not None
        assert t["resolved_at"] is None

    def test_updated_at_actually_changes_after_put(self, client, sample_payload):
        create_r = client.post("/tickets", json=sample_payload)
        tid = create_r.json()["id"]
        original_updated_at = create_r.json()["updated_at"]
        time.sleep(0.05)                        # 50 ms — enough for any OS clock
        update_r = client.put(f"/tickets/{tid}", json={"assigned_to": "Bob"})
        assert update_r.json()["updated_at"] != original_updated_at

    def test_resolved_at_preserved_when_status_changes_from_resolved(self, client, sample_payload):
        tid = client.post("/tickets", json=sample_payload).json()["id"]
        resolved = client.put(f"/tickets/{tid}", json={"status": "resolved"}).json()
        first_resolved_at = resolved["resolved_at"]
        assert first_resolved_at is not None

        # Change status away from resolved
        back = client.put(f"/tickets/{tid}", json={"status": "in_progress"}).json()
        # resolved_at preserved (documents current behaviour: first resolution time kept)
        assert back["resolved_at"] == first_resolved_at

    def test_created_at_does_not_change_on_update(self, client, sample_payload):
        create_r = client.post("/tickets", json=sample_payload)
        tid = create_r.json()["id"]
        original_created_at = create_r.json()["created_at"]
        client.put(f"/tickets/{tid}", json={"assigned_to": "Bob"})
        assert client.get(f"/tickets/{tid}").json()["created_at"] == original_created_at


# ---------------------------------------------------------------------------
# Full status lifecycle
# ---------------------------------------------------------------------------

class TestFullStatusLifecycle:
    def test_all_status_values_accepted(self, client, sample_payload):
        tid = client.post("/tickets", json=sample_payload).json()["id"]
        for status_val in ["in_progress", "waiting_customer", "resolved", "closed"]:
            r = client.put(f"/tickets/{tid}", json={"status": status_val})
            assert r.status_code == 200, f"Failed for status={status_val}"
            assert r.json()["status"] == status_val

    def test_waiting_customer_status_stored_and_retrievable(self, client, sample_payload):
        tid = client.post("/tickets", json=sample_payload).json()["id"]
        client.put(f"/tickets/{tid}", json={"status": "waiting_customer"})
        ticket = client.get(f"/tickets/{tid}").json()
        assert ticket["status"] == "waiting_customer"

    def test_closed_status_stored_and_retrievable(self, client, sample_payload):
        tid = client.post("/tickets", json=sample_payload).json()["id"]
        client.put(f"/tickets/{tid}", json={"status": "closed"})
        ticket = client.get(f"/tickets/{tid}").json()
        assert ticket["status"] == "closed"

    def test_status_filter_returns_waiting_customer(self, client, sample_payload):
        tid = client.post("/tickets", json=sample_payload).json()["id"]
        client.put(f"/tickets/{tid}", json={"status": "waiting_customer"})
        results = client.get("/tickets", params={"status": "waiting_customer"}).json()
        assert len(results) == 1
        assert results[0]["id"] == tid


# ---------------------------------------------------------------------------
# Import format edge cases
# ---------------------------------------------------------------------------

class TestImportFormatEdgeCases:
    def test_csv_quoted_commas_in_values(self):
        csv = (
            'customer_id,customer_email,customer_name,subject,description\n'
            '1,a@test.com,"Smith, Alice",Login issue,'
            '"Cannot login, account is locked and 2fa is broken too"\n'
        )
        records = parse_csv(csv.encode())
        assert len(records) == 1
        assert records[0]["customer_name"] == "Smith, Alice"
        assert "Cannot login" in records[0]["description"]

    def test_csv_quoted_commas_passes_validation(self):
        csv = (
            'customer_id,customer_email,customer_name,subject,description\n'
            '1,a@test.com,"Smith, Alice",Login issue,'
            '"Cannot login, account is locked and the 2fa code is not working either"\n'
        )
        records = parse_csv(csv.encode())
        _, summary = import_records(records)
        assert summary.successful == 1

    def test_json_null_optional_fields_accepted(self):
        import json
        payload = [{
            "customer_id": "1",
            "customer_email": "a@test.com",
            "customer_name": "Alice",
            "subject": "Test ticket",
            "description": "Long enough description that passes the ten character minimum.",
            "category": None,
            "priority": None,
            "assigned_to": None,
            "tags": [],
        }]
        from src.importer import parse_json
        records = parse_json(json.dumps(payload).encode())
        _, summary = import_records(records)
        assert summary.successful == 1
        # null optional fields → defaults applied

    def test_xml_ticket_with_only_required_fields(self):
        xml = b"""<tickets>
          <ticket>
            <customer_id>1</customer_id>
            <customer_email>a@test.com</customer_email>
            <customer_name>Alice</customer_name>
            <subject>Minimal ticket</subject>
            <description>Just the minimum required fields and nothing else at all.</description>
          </ticket>
        </tickets>"""
        records = parse_xml(xml)
        _, summary = import_records(records)
        assert summary.successful == 1

    def test_xml_import_with_auto_classify(self, client):
        xml = b"""<tickets>
          <ticket>
            <customer_id>1</customer_id>
            <customer_email>a@test.com</customer_email>
            <customer_name>Alice</customer_name>
            <subject>Login broken password reset</subject>
            <description>I cannot login and the password reset is not working either here.</description>
          </ticket>
        </tickets>"""
        r = client.post(
            "/tickets/import?auto_classify=true",
            files={"file": ("t.xml", io.BytesIO(xml), "application/xml")},
        )
        assert r.status_code == 200
        assert r.json()["successful"] == 1
        tickets = client.get("/tickets").json()
        assert tickets[0]["category"] == "account_access"
        assert tickets[0]["classification_confidence"] is not None


# ---------------------------------------------------------------------------
# Performance assertions with concrete thresholds
# ---------------------------------------------------------------------------

class TestPerformanceAssertions:
    def test_single_classify_call_under_1ms(self):
        start = time.perf_counter()
        classify("login password reset", "I cannot access my account at all.")
        elapsed = time.perf_counter() - start
        assert elapsed < 0.001, f"Single classify() took {elapsed * 1000:.3f} ms (limit 1 ms)"

    def test_100_row_csv_import_under_2s(self, client):
        rows = ["customer_id,customer_email,customer_name,subject,description"]
        for i in range(100):
            rows.append(
                f"c{i},u{i}@test.com,User {i},Subject {i},"
                f"Description long enough for performance ticket number {i} here."
            )
        csv_data = "\n".join(rows).encode()
        start = time.perf_counter()
        r = client.post("/tickets/import",
                        files={"file": ("p.csv", io.BytesIO(csv_data), "text/csv")})
        elapsed = time.perf_counter() - start
        assert r.json()["successful"] == 100
        assert elapsed < 2.0, f"100-row CSV import took {elapsed:.3f}s (limit 2s)"

    def test_get_tickets_with_500_stored_under_300ms(self, client):
        from src.models import Ticket
        from src.storage import store
        for i in range(500):
            store.add(Ticket(
                customer_id=f"p{i}",
                customer_email=f"u{i}@test.com",
                customer_name=f"User {i}",
                subject=f"Perf ticket {i}",
                description="Performance test ticket with enough description text.",
            ))
        start = time.perf_counter()
        r = client.get("/tickets")
        elapsed = time.perf_counter() - start
        assert r.status_code == 200
        assert len(r.json()) == 500
        assert elapsed < 0.3, f"GET /tickets (500 items) took {elapsed:.3f}s (limit 0.3s)"

    def test_classify_100_calls_under_100ms(self):
        start = time.perf_counter()
        for _ in range(100):
            classify("login password reset account", "Cannot access system.")
        elapsed = time.perf_counter() - start
        assert elapsed < 0.1, f"100 classify() calls took {elapsed * 1000:.1f}ms (limit 100ms)"
