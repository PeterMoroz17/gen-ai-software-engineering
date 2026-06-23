import threading

import pytest
from fastapi.testclient import TestClient

from src.classifier import classify
from src.importer import parse_csv, parse_json, parse_xml
from src.main import app
from src.models import Ticket
from src.storage import store


def _make_ticket(n: int) -> Ticket:
    return Ticket(
        customer_id=f"perf-{n}",
        customer_email=f"user{n}@example.com",
        customer_name=f"User {n}",
        subject=f"Performance test ticket number {n}",
        description="This ticket exists solely for performance testing and benchmarking purposes.",
    )


class TestPerformanceBenchmarks:
    def test_classification_speed(self, benchmark):
        benchmark.group = "parsing"
        benchmark(classify, "login", "password reset")

    def test_csv_parse_speed(self, benchmark):
        benchmark.group = "parsing"
        benchmark(
            parse_csv,
            b"customer_id,customer_email,customer_name,subject,description\n"
            b"1,a@test.com,John,Login issue,Cannot login to my account at all",
        )

    def test_json_parse_speed(self, benchmark):
        benchmark.group = "parsing"
        benchmark(parse_json, b'[{"customer_id":"1"}]')

    def test_xml_parse_speed(self, benchmark):
        benchmark.group = "parsing"
        benchmark(parse_xml, b"<ticket/>")

    def test_bulk_ticket_creation_speed(self, benchmark, client, ticket_payload):
        benchmark.group = "http"
        benchmark(lambda: client.post("/tickets", json=ticket_payload))


class TestConcurrency:
    def test_50_concurrent_gets_all_succeed(self):
        for i in range(10):
            store.add(_make_ticket(i))
        c = TestClient(app)
        status_codes = []
        errors = []

        def do_get():
            try:
                r = c.get("/tickets")
                status_codes.append(r.status_code)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=do_get) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread errors: {errors}"
        assert all(s == 200 for s in status_codes)
