# Agents Overview

This document describes the two distinct "agent" layers in this project: the **meta-agents** (the AI/automation workflows that are the homework deliverable) and the **pipeline agents** (the transaction-processing system those meta-agents produce).

---

## Meta-Agents (Homework Deliverables)

| Agent | Role | Produces | "Plus" requirement |
|---|---|---|---|
| **Agent 1 — Specification** | Writes the technical spec before any code is generated | `specification.md`, `agents.md` (this file) | Skill `.claude/commands/write-spec.md` that regenerates the spec from the template |
| **Agent 2 — Code generation** | Implements the pipeline (validator, fraud detector, compliance checker, integrator) from `specification.md` | `agents/*.py`, `integrator.py`, `requirements.txt` | Uses MCP **context7** to look up real library APIs (`decimal`, `fastmcp`); ≥2 queries logged in `research-notes.md` |
| **Agent 3 — Unit tests** | Writes the test suite covering every pipeline agent + integration path | `tests/*.py` | Coverage-gate hook (`.claude/settings.json` + `.git/hooks/pre-push`) blocks `git push` if coverage < 80% |
| **Agent 4 — Documentation** | Generates README, HOWTORUN, and the PR description | `README.md`, `HOWTORUN.md`, PR description | README includes "Created by Peter Moroz" |

---

## Pipeline Agents (System Under Construction)

These are the actual Python modules that process transactions at runtime — the *output* of Agent 2's work.

### `transaction_validator` (`agents/transaction_validator.py`)
- **Contract**: `process_message(message: dict) -> dict`
- **Consumes**: a standard envelope with `data.status` unset (raw transaction)
- **Produces**: the same envelope with `data.status` set to `validated` or `rejected` (+ `data.reason`)
- **Checks**: required fields present, `Decimal` amount valid (positive, or negative only for `refund`), ISO 4217 currency
- **Extra**: CLI entrypoint with `--dry-run` for the `/validate-transactions` skill

### `fraud_detector` (`agents/fraud_detector.py`)
- **Contract**: `process_message(message: dict) -> dict`
- **Consumes**: envelope with `data.status == "validated"`
- **Produces**: envelope with `data.risk_score` (0-100) and `data.status` set to `flagged_for_review` or `cleared_fraud_check`
- **Checks**: high-value (>$10,000), odd-hour timestamp, cross-border indicators

### `compliance_checker` (`agents/compliance_checker.py`)
- **Contract**: `process_message(message: dict) -> dict`
- **Consumes**: envelope from `fraud_detector` (or a `rejected` envelope from `transaction_validator`)
- **Produces**: final disposition (`rejected` / `flagged_for_review` / `cleared`), written to `shared/results/<transaction_id>.json`
- **Side effect**: appends a masked audit line to `shared/results/pipeline.log`

### `integrator` (`integrator.py`)
- **Contract**: `run_pipeline(transactions: list[dict], shared_dir: Path) -> dict`
- **Role**: orchestrates the 3 pipeline agents in order for every record in `sample-transactions.json`; sets up `shared/{input,processing,output,results}`; persists `shared/results/summary.json`

### Standard message envelope (shared by all pipeline agents)

```json
{
  "message_id": "uuid4-string",
  "timestamp": "2026-03-16T10:00:00Z",
  "source_agent": "transaction_validator",
  "target_agent": "fraud_detector",
  "message_type": "transaction",
  "data": {
    "transaction_id": "TXN001",
    "amount": "1500.00",
    "currency": "USD",
    "status": "validated"
  }
}
```
