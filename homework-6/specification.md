# Multi-Agent Banking Transaction Pipeline Specification

> Ingest the information from this file, implement the Low-Level Tasks, and generate the code that will satisfy the High and Mid-Level Objectives.

## High-Level Objective

Build a file-based, multi-agent transaction processing pipeline that validates, risk-scores, and clears bank transactions from `sample-transactions.json`, producing auditable JSON results in `shared/results/`.

## Mid-Level Objectives

- Every transaction is checked for required fields, a positive `Decimal` amount (or a negative amount only when `transaction_type` is `refund`), and an ISO 4217 currency code; invalid transactions are rejected with a specific reason.
- Transactions with `amount > 10000.00` (in transaction currency) are flagged for fraud review and receive a numeric risk score; unusual-hour (00:00–06:00 local) and cross-border (`metadata.country` differs from the country implied by the destination account range) activity add to the score.
- Every transaction reaches a final disposition (`cleared`, `rejected`, or `flagged_for_review`) written as a JSON file to `shared/results/`, including a `reason` field for any non-`cleared` outcome.
- All agent operations are logged with ISO 8601 UTC timestamps, the agent name, the `transaction_id`, and the outcome — without ever writing account numbers or names in plaintext (only the transaction ID and masked account suffixes).
- The full pipeline run produces a persisted run summary (counts by disposition) consumable both from the terminal and via the `pipeline://summary` MCP resource, and the automated test suite covers ≥ 90% of `agents/` and `integrator.py`.

## Implementation Notes

- Monetary values: use `decimal.Decimal` for every amount; amounts are read from JSON as strings and converted via `Decimal(str(...))`, never `float`.
- Currency codes: validate against a fixed ISO 4217 allow-list (`USD`, `EUR`, `GBP`, `JPY`, ...); unknown codes (e.g. `XYZ`) are rejected.
- Logging: every agent emits one audit line per transaction to stdout and to `shared/results/pipeline.log`, formatted as `<ISO8601> | <agent_name> | <transaction_id> | <outcome>`.
- PII: `source_account` / `destination_account` are masked to their last 4 characters in any log line or printed summary; full account numbers are only ever present inside the JSON message payloads passed between agents, not in logs.
- Message passing: agents communicate exclusively through JSON files following the standard envelope (see Task 2 of `TASKS.md`), moved between `shared/input/` → `shared/processing/` → `shared/output/` → `shared/results/`.
- Language/stack: Python 3.11+, `pytest` + `pytest-cov` for testing, `fastmcp` for the custom MCP server.

## Context

### Beginning context
- `sample-transactions.json` — 8 raw transaction records (mixed valid/invalid: bad currency `TXN006`, negative non-refund-style amount `TXN007`, high-value wires `TXN002`/`TXN005`, odd-hour transfer `TXN004`).
- `TASKS.md` — assignment requirements.
- No pipeline code exists yet.

### Ending context
- `agents/transaction_validator.py`, `agents/fraud_detector.py`, `agents/compliance_checker.py` — three cooperating pipeline agents.
- `integrator.py` — orchestrator that runs all 8 sample transactions through the pipeline.
- `shared/results/` — one JSON result per transaction, plus `summary.json` and `pipeline.log`.
- `tests/` — unit tests per agent + 1 integration test, ≥ 90% coverage.
- `mcp/server.py` + `mcp.json` — queryable pipeline status via FastMCP, alongside context7.
- `README.md` / `HOWTORUN.md` — full documentation, with coverage gate hook configured.

## Low-Level Tasks

### 1. Transaction Validator

Task: Transaction Validator Agent
Prompt: "Create `agents/transaction_validator.py` with a `process_message(message: dict) -> dict` function that validates a transaction payload: required fields present (`transaction_id`, `timestamp`, `source_account`, `destination_account`, `amount`, `currency`, `transaction_type`); `amount` parses as `Decimal` and is > 0, except `transaction_type == 'refund'` may be negative; `currency` is in the ISO 4217 allow-list. Return a message with `data.status` set to `validated` or `rejected` plus a `data.reason` on rejection. Also add a CLI (`argparse`, `--dry-run`) that loads `sample-transactions.json`, runs validation only, and prints counts + reasons without touching `shared/`."
File to CREATE: `agents/transaction_validator.py`
Function to CREATE: `process_message(message: dict) -> dict`, `validate_transaction(data: dict) -> tuple[bool, str | None]`, `main()` (CLI/`--dry-run` entrypoint)
Details: Use `Decimal(str(amount))`; never `float`. Mask account numbers in any printed/logged output. Exit 0 always for `--dry-run` (it's a report, not a gate).

### 2. Fraud Detector

Task: Fraud Detector Agent
Prompt: "Create `agents/fraud_detector.py` with `process_message(message: dict) -> dict` that takes a validated transaction and computes a `risk_score` (int 0-100): +50 if `amount > 10000`, +20 if local hour (from `timestamp`, treated as UTC) is between 00:00 and 06:00, +15 if `metadata.country` suggests a cross-border transfer (destination jurisdiction proxy differs from `metadata.country`). Set `data.status` to `flagged_for_review` if `risk_score >= 50`, else `cleared_fraud_check`."
File to CREATE: `agents/fraud_detector.py`
Function to CREATE: `process_message(message: dict) -> dict`, `compute_risk_score(data: dict) -> int`
Details: Only runs on messages with `data.status == 'validated'`; pass through rejected messages unchanged. Log risk score per transaction without PII.

### 3. Compliance Checker

Task: Compliance Checker Agent
Prompt: "Create `agents/compliance_checker.py` with `process_message(message: dict) -> dict` that produces the final disposition: `rejected` (validator failed), `flagged_for_review` (fraud score high), or `cleared` (passed both checks). Write the final result as a JSON file to `shared/results/<transaction_id>.json` and append an audit line to `shared/results/pipeline.log`."
File to CREATE: `agents/compliance_checker.py`
Function to CREATE: `process_message(message: dict) -> dict`, `write_result(result: dict, results_dir: Path) -> Path`
Details: Final JSON includes `transaction_id`, `status`, `reason` (if any), `risk_score` (if computed), `processed_at` (ISO 8601).

### 4. Integrator / Orchestrator

Task: Integrator Agent
Prompt: "Create `integrator.py` that creates the `shared/{input,processing,output,results}` directories, loads `sample-transactions.json`, wraps each record into the standard message envelope, and runs it sequentially through `transaction_validator` → `fraud_detector` → `compliance_checker`, writing intermediate envelopes to `processing/`/`output/` and the final result to `results/`. After processing all transactions, print and persist a summary (`shared/results/summary.json`) with counts per disposition."
File to CREATE: `integrator.py`
Function to CREATE: `main()`, `run_pipeline(transactions: list[dict], shared_dir: Path) -> dict`
Details: Idempotent — clears `shared/{processing,output}` at the start of each run; never deletes prior `results/` unless explicitly run with a clean flag.
