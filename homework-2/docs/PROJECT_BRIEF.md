# PROJECT_BRIEF — Customer Support Ticket Management System

> **Purpose of this file**: this is a self-contained context dump for AI models that have
> no memory of how this project was built. Paste this entire file as a system/context
> message before asking a model to write documentation (API_REFERENCE.md,
> ARCHITECTURE.md, or TESTING_GUIDE.md). Everything below is extracted directly from
> the source code — do not invent endpoints, fields, or behavior beyond what's listed
> here.

---

## 1. What this project is

A REST API for managing customer support tickets. Built with **Python 3.13, FastAPI,
Pydantic v2**. Storage is an in-memory, thread-safe dict (no database). It supports:

- CRUD on tickets
- Bulk import from CSV / JSON / XML with per-record validation and a summary report
- Keyword-based auto-classification (category + priority + confidence + reasoning)
- Filtering ticket listings by category, priority, status (combinable)

Tech stack: `fastapi==0.115.5`, `uvicorn==0.32.1`, `pydantic[email]==2.10.3`,
`python-multipart==0.0.18`. Test stack: `pytest==8.3.4`, `httpx==0.28.1`,
`pytest-cov==6.0.0`, `pytest-asyncio==0.24.0`, `pytest-benchmark==4.0.0`.

No database, no auth layer, no persistence across restarts — this is intentionally
a single-process in-memory system for the assignment's scope.

---

## 2. File layout

```
src/
  main.py        FastAPI app + 7 route handlers
  models.py      Pydantic models & enums
  storage.py     TicketStore — thread-safe in-memory dict, module-level singleton `store`
  importer.py    CSV/JSON/XML parsers + import_records()
  classifier.py  classify(subject, description) -> ClassificationResult
tests/
  conftest.py             shared fixtures: client, ticket_payload, sample_payload, fresh_store (autouse)
  test_ticket_api.py      API endpoint tests
  test_ticket_model.py    Pydantic validation tests
  test_import_csv.py / test_import_json.py / test_import_xml.py
  test_categorization.py  classifier tests
  test_integration.py     end-to-end workflow tests
  test_performance.py     pytest-benchmark + concurrency tests
  test_edge_cases.py      boundary / previously-uncovered-branch tests
  test_review_items.py    tests added in response to a code review
  fixtures/               sample_tickets.{csv,json,xml}, invalid_tickets.{csv,json,xml}
docs/
  coverage/        generated HTML coverage report (pytest.ini --cov-report=html)
  screenshots/     test_coverage.png
sample_tickets.csv   50 rows
sample_tickets.json  20 records
sample_tickets.xml   30 records
invalid_tickets.*    negative-test fixtures
```

---

## 3. Data model (`src/models.py`)

### Enums (all string-valued)

```python
Category: account_access | technical_issue | billing_question | feature_request | bug_report | other
Priority: urgent | high | medium | low
Status:   new | in_progress | waiting_customer | resolved | closed
Source:   web_form | email | api | chat | phone
DeviceType: desktop | mobile | tablet
```

### `Metadata`
```python
source: Source = Source.api          # defaults to "api"
browser: Optional[str] = None
device_type: Optional[DeviceType] = None
```

### `TicketCreate` (request body for POST /tickets, also base for import records)
```python
customer_id: str                                  # not blank (custom validator)
customer_email: EmailStr                          # real email format validation
customer_name: str                                # not blank (custom validator)
subject: str                                      # 1–200 chars
description: str                                  # 10–2000 chars
category: Optional[Category] = None
priority: Optional[Priority] = None
status: Status = Status.new
assigned_to: Optional[str] = None
tags: list[str] = []
metadata: Metadata = Metadata()
```

### `TicketUpdate` (request body for PUT /tickets/:id) — every field optional,
only fields present in the request body are applied (`exclude_none` on dump).

### `Ticket` (response model — extends TicketCreate)
```python
id: str                                  # UUID4 string, server-generated
created_at: datetime                     # UTC, server-generated, immutable
updated_at: datetime                     # UTC, bumped on every PUT and auto-classify
resolved_at: Optional[datetime] = None   # set once, the FIRST time status becomes "resolved"; preserved afterwards even if status changes away from resolved
classification_confidence: Optional[float] = None
classification_reasoning: Optional[str] = None
```

### `ImportSummary` (response body for POST /tickets/import)
```python
total: int
successful: int
failed: int
errors: list[dict]   # each: {"index": int, "record": dict, "error": ...}
```

### `ClassificationResult` (response body for POST /tickets/:id/auto-classify)
```python
category: Category
priority: Priority
confidence: float        # 0.0–1.0
reasoning: str            # human-readable sentence(s)
keywords_found: list[str] # union of matched category + priority keywords, de-duplicated, order preserved
```

---

## 4. API endpoints (`src/main.py`)

All routes are mounted directly on the FastAPI `app` (no prefix/versioning).

| Method | Path | Query params | Body | Response | Status codes |
|---|---|---|---|---|---|
| POST | `/tickets` | `auto_classify: bool = false` | `TicketCreate` | `Ticket` | 201 created, 422 validation error |
| POST | `/tickets/import` | `auto_classify: bool = false` | multipart file upload, field name `file` | `ImportSummary` | 200 ok, 400 unsupported format / parse failure |
| GET | `/tickets` | `category`, `priority`, `status` (all optional, combinable, exact match) | — | `list[Ticket]` | 200 |
| GET | `/tickets/{ticket_id}` | — | — | `Ticket` | 200, 404 not found |
| PUT | `/tickets/{ticket_id}` | — | `TicketUpdate` (partial) | `Ticket` | 200, 404 not found |
| DELETE | `/tickets/{ticket_id}` | — | — | empty body | 204 no content, 404 not found |
| POST | `/tickets/{ticket_id}/auto-classify` | — | — | `ClassificationResult` | 200, 404 not found |

### Behavioral notes that matter for documentation accuracy

- `POST /tickets/import`: file extension is read from the uploaded filename
  (`.csv` / `.json` / `.xml`); unsupported or missing extension → `400` with
  `detail: "Unsupported file format '<ext>'. Use csv, json, or xml."`. Parser
  exceptions are caught and surfaced as `400` with `detail: "Failed to parse <EXT> file: <error>"`.
- Bulk import never aborts on a bad record — each record is validated independently;
  the response always has status 200 with `total/successful/failed/errors` reflecting
  per-record outcomes.
- `auto_classify=true` on both `POST /tickets` and `POST /tickets/import` runs the
  classifier and writes `category`, `priority`, `classification_confidence`,
  `classification_reasoning` onto the ticket(s) before storing.
- Manual override: a later `PUT` with an explicit `category`/`priority` overwrites
  the auto-classified values and is NOT re-classified by subsequent unrelated `PUT`s
  (classification only happens on creation w/ flag, or on the explicit auto-classify
  endpoint — never implicitly on update).
- `resolved_at` is set the first time `status` transitions to `"resolved"` and is
  never cleared or overwritten by later status changes (documented, intentional
  behavior, not a bug).
- `updated_at` is bumped on every `PUT` and on the auto-classify endpoint call.
- `GET /tickets` filters are combined with AND semantics (category AND priority AND status).
- IDs are UUID4 strings, generated server-side; clients never supply an `id`.

### Error response shape

FastAPI/Pydantic default error envelope:
```json
{"detail": "Ticket not found"}
```
for `HTTPException`s (404, 400), and FastAPI's standard structured shape for 422
validation errors:
```json
{"detail": [{"type": "...", "loc": ["body", "field"], "msg": "...", "input": "..."}]}
```

---

## 5. Import formats (`src/importer.py`)

All three parsers return `list[dict]` of raw records, which are then each validated
through `TicketCreate.model_validate(...)`.

- **CSV**: `csv.DictReader`, UTF-8 with BOM handling (`utf-8-sig`). `tags` column is a
  comma-separated string, split into a list. Columns named `metadata.source`,
  `metadata.browser`, `metadata.device_type` are un-flattened into a nested `metadata` dict.
- **JSON**: accepts either a top-level array of records, or an object with one of the
  keys `tickets` / `data` / `records` mapping to an array. Anything else raises
  `ValueError`.
- **XML**: root may be a `<tickets>` wrapper (containing `<ticket>` children) or a
  single `<ticket>` root. Inside each `<ticket>`, a `<tags>` element with `<tag>`
  children becomes a list; a `<metadata>` element with sub-elements becomes a nested dict.
- `import_records(raw_records)` normalizes `tags`/`metadata` shapes, validates each
  record against `TicketCreate`, catches `pydantic.ValidationError` (and any other
  exception) per-record, and returns `(list[Ticket], ImportSummary)`.

---

## 6. Auto-classification rules (`src/classifier.py`)

`classify(subject, description) -> ClassificationResult`. Logic, exactly as implemented:

1. Concatenate `f"{subject} {description}".lower()`.
2. **Category scoring**: for each of the 5 real categories, count how many of that
   category's keywords appear as substrings in the text; score = hits / total keywords
   for that category. Pick the highest-scoring category.
   - If the best score is `0.0`, category = `other`, confidence = `0.0`, no keywords found.
   - Otherwise, `confidence = min(best_score * 5, 1.0)` (i.e. a 20% keyword-hit rate
     already saturates confidence to 1.0).
3. **Priority scoring**: checked in fixed order — `urgent` keywords first, then `high`,
   then `low`; first one with any keyword match wins. If none match, priority = `medium`
   (default, no keyword list for medium).
4. `keywords_found` = de-duplicated union of matched category keywords + matched
   priority keywords, insertion order preserved.
5. `reasoning` = one or two sentences naming which category/priority keywords matched,
   or stating that none matched and a default was used.

### Exact keyword lists

**Category keywords:**
- `account_access`: login, log in, log-in, password, 2fa, two factor, two-factor, locked, lock out, lockout, sign in, sign-in, signin, authentication, authenticate, account access, reset, forgot, credentials, username, session, logout, log out
- `technical_issue`: error, crash, crashing, not working, doesn't work, broken, exception, failure, fails, timeout, timed out, outage, down, unavailable, slow, hang, hangs, freeze, freezing, 500, internal server error, 502, 503
- `billing_question`: payment, pay, invoice, charge, charged, refund, subscription, billing, bill, receipt, overcharged, overcharge, price, pricing, cost, fee, credit card, debit, plan, upgrade, downgrade, cancel, cancellation
- `feature_request`: feature, suggestion, suggest, enhancement, enhance, would be nice, could you add, please add, request, wishlist, idea, improvement, improve, new functionality, support for, allow us, ability to
- `bug_report`: bug, defect, reproduce, steps to reproduce, regression, unexpected behavior, unexpected behaviour, wrong output, incorrect, misbehaving, reproducible, repro, workaround, glitch

**Priority keywords** (checked in this order — urgent wins over high wins over low):
- `urgent`: can't access, cannot access, critical, production down, prod down, security breach, data loss, data breach, outage
- `high`: important, blocking, blocked, asap, as soon as possible, high priority, top priority, escalate
- `low`: minor, cosmetic, suggestion, nice to have, nice-to-have, when possible, whenever, low priority, not urgent, someday
- (no keyword list for `medium` — it's the fallback)

Note: `"urgent"` itself is deliberately NOT a urgent-priority keyword (avoids false
positives like "this is not urgent").

---

## 7. Storage (`src/storage.py`)

`TicketStore` — plain Python dict keyed by ticket UUID, guarded by a single
`threading.Lock()` for `add`/`update`/`delete`/`clear`. `get`/`list` are unguarded
reads. Module-level singleton `store = TicketStore()` is imported by `main.py`. No
persistence — data is lost on process restart. This is sufficient for the assignment's
concurrency tests (20+ simultaneous creates, 50 simultaneous reads) because Python's
GIL plus the explicit lock around writes prevents corruption, though reads are not
strictly serialized with writes (acceptable for this scope).

---

## 8. Test suite summary

- **161 tests total**, **100% line coverage** across all 5 files in `src/` (322
  statements, 0 missed), measured via `pytest-cov` (`pytest.ini` runs `--cov=src
  --cov-report=term-missing --cov-report=html:docs/coverage` by default).
- Test files map roughly to: ticket API (CRUD), ticket model (Pydantic validation),
  one file per import format (CSV/JSON/XML), classifier/categorization, integration
  (full workflows), performance (benchmarks + concurrency), edge cases (boundary
  values, previously-uncovered branches), review-driven tests (gaps found in a manual
  code review: UUID format validation, confidence score quality, manual override
  persistence, decision logging, three-way filters, datetime field lifecycle, full
  status lifecycle, import format edge cases, concrete performance thresholds).
- Performance benchmarks (via `pytest-benchmark`, grouped to avoid misleading
  cross-group ratios): an `http` group (`test_bulk_ticket_creation_speed`, full
  HTTP round-trip through FastAPI + validation + storage, ~2.8–11ms per call) and a
  `parsing` group (`classify`, `parse_csv`, `parse_json`, `parse_xml`, all in the
  1–10 microsecond range).
- Concurrency tests: 20 simultaneous `POST /tickets` all succeed with unique UUIDs;
  50 simultaneous `GET /tickets` all return 200.
- Fixtures: `tests/conftest.py` provides a `client` (FastAPI `TestClient`), two
  reusable valid payloads (`ticket_payload`, `sample_payload`), and an `autouse`
  `fresh_store` fixture that clears the in-memory store before and after every test
  for isolation.

---

## 9. What NOT to invent

- There is no authentication/authorization anywhere in this API.
- There is no database — do not describe SQL schemas, migrations, or ORMs.
- There is no rate limiting, pagination, or sorting on `GET /tickets`.
- There is no websocket / async notification mechanism.
- There is no separate "priority medium" keyword list — medium is purely the default.
- Tags and metadata are optional and default to `[]` / `Metadata()` respectively.
