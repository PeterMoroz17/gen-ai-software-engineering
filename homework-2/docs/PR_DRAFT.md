# Homework 2: Customer Support Ticket Management System

## Summary

This PR implements a REST API for managing customer support tickets, built with
**FastAPI + Pydantic v2** and an in-memory, thread-safe store (no database).

It covers all five tasks in `homework-2/TASKS.md`:

- **Task 1 — Multi-Format Ticket Import API**: full CRUD on tickets, plus bulk
  import from CSV, JSON, and XML, each format parsed independently and validated
  per-record (a bad row never aborts the whole import — see `ImportSummary`).
- **Task 2 — Auto-Classification**: a deterministic, keyword-based classifier
  assigns `category` (6 values) and `priority` (4 values), with a 0–1 confidence
  score and a human-readable reasoning string. Can run automatically on creation
  (`?auto_classify=true`), via a dedicated `POST /tickets/{id}/auto-classify`
  endpoint, or be manually overridden via `PUT` without being silently
  re-classified afterward.
- **Task 3 — Test Suite**: 161 tests across 10 files, **100% line coverage**
  (322/322 statements) on every file in `src/`.
- **Task 4 — Multi-Level Documentation**: `README.md`, `API_REFERENCE.md`,
  `ARCHITECTURE.md`, `TESTING_GUIDE.md`, plus `HOWTORUN.md`. Four Mermaid
  diagrams total (component flowchart + sequence diagram in `ARCHITECTURE.md`,
  test pyramid in `TESTING_GUIDE.md`, architecture overview in `README.md`).
- **Task 5 — Integration & Performance Tests**: full ticket lifecycle
  (create → in_progress → resolve → delete → 404), bulk import with
  auto-classification verification, 20+ concurrent ticket creations all
  producing unique UUIDs, and combined category+priority+status filtering.

Reviewers unfamiliar with the branch: start with
[`README.md`](README.md) for the architecture and feature overview, then
[`HOWTORUN.md`](HOWTORUN.md) to run it, then [`API_REFERENCE.md`](API_REFERENCE.md)
for the exact request/response contract of every endpoint.

---

## 🛠️ AI Tools Used

This project followed the **Context-Model-Prompt** framework: one model with
full build context wrote the code and tests, then a separate, portable context
document (`docs/PROJECT_BRIEF.md`) was extracted from the *finished, working
code* so other models could write documentation without ever having seen the
build process.

| Artifact | Model | Workflow |
|---|---|---|
| `src/`, `tests/`, `README.md`, `docs/PROJECT_BRIEF.md` | **Claude Code** | Full session context — planned the API task-by-task, implemented the FastAPI app and classifier, generated the 161-test suite, debugged failures, then wrote `PROJECT_BRIEF.md` as a code-accurate handoff document (data models, all 7 endpoint contracts, the exact classifier keyword lists/scoring formula, storage internals, test suite breakdown). |
| `API_REFERENCE.md` | **ChatGPT** | Given `PROJECT_BRIEF.md` + a scoped prompt asking specifically for endpoint examples, schemas, error formats, and curl commands, with an explicit "use only the facts given, don't invent" instruction. |
| `ARCHITECTURE.md` | **Gemini 3.5 Flash** | Same handoff, prompted for a component diagram, a sequence diagram for bulk import, design trade-offs, and security/performance notes. |
| `TESTING_GUIDE.md` | **Copilot** | Same handoff, prompted for the test pyramid, run commands, fixture locations, and a manual testing checklist. |

**Why the handoff document was necessary:** the three external models have no
memory of this build. A bare "write API docs for this ticket system" prompt
produces plausible-sounding but fabricated content. `PROJECT_BRIEF.md` solves
this by being generated *from the actual code*, then fed back in as ground
truth before each doc-writing prompt — turning the cross-model documentation
requirement into something that can actually stay accurate.

**What I verified myself, and what I caught:**

Every AI-generated doc was checked line-by-line against the real source files
before being accepted. This caught several errors that were fluent and
plausible but factually wrong:

- **`API_REFERENCE.md`**: invented a `customer_id` field on `TicketUpdate` that
  doesn't exist in `models.py` (it's immutable after creation); used generic
  prose for `classification_reasoning` examples instead of the classifier's
  real `"Matched category '...' keywords: [...]"` output format; a `PUT`
  example incorrectly showed `classification_reasoning` reset to `null` (it
  can't be — `TicketUpdate` has no such field to set it through); and several
  `classification_confidence` example values didn't match the stated formula
  given the keywords shown (fixed by recomputing `min(hits/total*5, 1.0)`
  against the real 23-keyword `account_access` list).
- **`ARCHITECTURE.md`**: both the component flowchart and the sequence diagram
  wrongly drew edges from `importer.py` straight to the classifier and the
  store. In the real code, `importer.py` only parses and validates —
  `main.py` is the orchestrator that calls the classifier and the store, in
  two separate sequential passes *after* import finishes. Redrew both
  diagrams to match. A design-decision section also overstated manual
  override protection as a permanent "lock"; in reality the explicit
  `/auto-classify` endpoint will still overwrite a manual override — only
  *implicit* reclassification on unrelated `PUT`s is prevented.
- **`TESTING_GUIDE.md`**: referenced a test path,
  `tests/test_ticket_api.py::TestTicketAPI::test_create_ticket`, that doesn't
  exist (wrong class *and* function name). Corrected to the real class,
  `TestCreateTicket`.

None of these were obviously wrong on a skim — they were well-formatted and
consistent with the surrounding text. Catching them required reading the
actual source line-by-line and checking every concrete claim (field names,
which module calls what, keyword lists, formulas) against the code itself.

---

## ⚠️ Challenges Encountered

- **FastAPI 204 response body error.** `DELETE /tickets/{id}` initially
  returned `None`, which newer FastAPI/Starlette rejects for a 204 with
  `AssertionError: Status code 204 must not have a response body`. Fixed by
  returning an explicit `Response(status_code=status.HTTP_204_NO_CONTENT)`.
- **Classifier false positive on priority.** A smoke test with the phrase "not
  urgent at all" was classified as `urgent` priority — the literal substring
  `"urgent"` was itself one of the urgent-priority keywords, so any mention of
  the word (even in negation) fired it. Fixed by removing `"urgent"`,
  `"emergency"`, and `"immediately"` from the urgent keyword list, keeping only
  the more specific phrases (`"can't access"`, `"production down"`,
  `"security breach"`, etc.).
- **Misleading benchmark output.** `pytest-benchmark` by default compares every
  test in a run against the single fastest one. Since a full HTTP round-trip
  (`~3.5ms`) was benchmarked alongside raw parsing functions (`~1-10µs`), the
  report showed nonsensical `(>1000.0)` ratios in red for the HTTP test, which
  looked like a failure even though all tests passed. Fixed by tagging tests
  with `benchmark.group = "http"` / `"parsing"` so ratios are only computed
  within comparable groups.
- **AI-generated documentation drift.** The largest recurring issue wasn't a
  bug in the application — it was that AI-written docs (even with a context
  document in hand) introduced specific, plausible-but-wrong details (see "AI
  Tools Used" above). This made line-by-line verification against the actual
  source non-negotiable before accepting any doc.

---

## ✅ How to Run & Verify

```bash
cd homework-2
pip install -r requirements.txt

# run the full test suite (161 tests, prints coverage table)
pytest

# start the API
uvicorn src.main:app --reload
# Swagger UI: http://127.0.0.1:8000/docs
```

Full step-by-step instructions, including example curl calls for every
endpoint: [`HOWTORUN.md`](HOWTORUN.md). Full endpoint contract:
[`API_REFERENCE.md`](API_REFERENCE.md). Design rationale and diagrams:
[`ARCHITECTURE.md`](ARCHITECTURE.md). Test suite structure and manual testing
checklist: [`TESTING_GUIDE.md`](TESTING_GUIDE.md).

---

## 📸 Screenshots

> All images also added to `docs/screenshots/`.

- `test_coverage.png` — full test run: 161 passed, 100% coverage
- `swagger_ui.png` — `/docs` showing all 7 endpoints
- `create_ticket_autoclassify.png` — `POST /tickets?auto_classify=true` request/response
- `bulk_import_summary.png` — `POST /tickets/import` with a sample CSV, showing `ImportSummary`
- `combined_filter.png` — `GET /tickets` with category+priority+status filters
- `benchmark_output.png` — performance test run, `http`/`parsing` groups
- `ai_doc_generation_chatgpt.png`, `ai_doc_generation_gemini.png`, `ai_doc_generation_copilot.png` — the actual prompts/responses used to generate the three handed-off docs
- `ai_correction_*.png` — the classifier false-positive fix and the documentation-error corrections described above

<!-- ![test coverage](docs/screenshots/test_coverage.png) -->
<!-- embed the rest the same way once the files are in place -->
