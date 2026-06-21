# HOWTORUN.md

Step-by-step guide to run the Customer Support Ticket Management System.

## 1. Prerequisites

- Python 3.13+

## 2. Install dependencies

```bash
cd homework-2
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

## 3. Run the API server

```bash
uvicorn src.main:app --reload
```

- API base URL: `http://127.0.0.1:8000`
- Interactive docs (Swagger UI): `http://127.0.0.1:8000/docs`

## 4. Try it out

Create a ticket with auto-classification:

```bash
curl -X POST "http://127.0.0.1:8000/tickets?auto_classify=true" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "CUST-1001",
    "customer_email": "jane@example.com",
    "customer_name": "Jane Smith",
    "subject": "Cannot access account",
    "description": "I cannot access my account after resetting my password and need assistance."
  }'
```

Bulk import a sample file:

```bash
curl -X POST "http://127.0.0.1:8000/tickets/import?auto_classify=true" \
  -F "file=@sample_tickets.csv"
```

List tickets with combined filters:

```bash
curl "http://127.0.0.1:8000/tickets?category=account_access&priority=urgent&status=new"
```

See [API_REFERENCE.md](API_REFERENCE.md) for the full endpoint reference.

## 5. Run the test suite

```bash
pytest
```

This runs all 161 tests and prints a coverage table. An HTML coverage report is
written to `docs/coverage/index.html` — open it in a browser to see per-file
coverage detail.

Run a single file or class:

```bash
pytest tests/test_ticket_api.py
pytest tests/test_ticket_api.py::TestCreateTicket
```

See [TESTING_GUIDE.md](TESTING_GUIDE.md) for the full testing guide.
