# 🏦 Multi-Agent Banking Transaction Pipeline

**Created by Peter Moroz**

## Overview

This project is a file-based, multi-agent transaction processing pipeline for a bank. Raw transactions from `sample-transactions.json` flow through three cooperating agents — a validator, a fraud detector, and a compliance checker — each communicating exclusively through JSON message files under `shared/`. The pipeline produces an auditable disposition (`cleared`, `rejected`, or `flagged_for_review`) for every transaction, a persisted run summary, and a full audit log, all queryable live through a custom MCP server.

This is also the final capstone for the GenAI/Agentic AI for Software Engineering course: the four "meta-agents" required by the assignment (specification, code generation, unit tests, documentation) produced everything below, each supported by its required "plus" (a spec-writing skill, MCP context7 research, a coverage-gate hook, and this README).

## Agent Responsibilities

- **Transaction Validator** (`agents/transaction_validator.py`) — checks required fields, validates `Decimal` amounts (positive, or negative only for refunds), and enforces an ISO 4217 currency allow-list; rejects anything that fails with a specific reason.
- **Fraud Detector** (`agents/fraud_detector.py`) — scores validated transactions 0-100 for risk: +50 high-value (>$10,000), +20 odd-hour (00:00-06:00 UTC), +15 cross-border; flags anything scoring ≥50 for review.
- **Compliance Checker** (`agents/compliance_checker.py`) — combines the upstream results into a final disposition and writes it to `shared/results/`, plus an audit log line.
- **Integrator** (`integrator.py`) — orchestrates all three agents for every transaction in `sample-transactions.json` and persists a run summary.

## Architecture

```
sample-transactions.json
        │
        ▼
   ┌─────────────┐      shared/input/        shared/processing/
   │ Integrator  │ ───► (raw envelope) ───► (in-flight envelope)
   └─────────────┘
        │
        ▼
┌────────────────────────┐
│  Transaction Validator  │  validated / rejected
└────────────────────────┘
        │
        ▼
┌────────────────────────┐
│     Fraud Detector      │  risk_score, cleared_fraud_check / flagged_for_review
└────────────────────────┘
        │           shared/output/ (intermediate hop)
        ▼
┌────────────────────────┐
│   Compliance Checker    │  final disposition
└────────────────────────┘
        │
        ▼
   shared/results/*.json  +  summary.json  +  pipeline.log
        │
        ▼
┌────────────────────────┐        ┌────────────────────┐
│  mcp/server.py (FastMCP)│◄──────►│ context7 MCP server │
│  get_transaction_status │        │ (library lookups)   │
│  list_pipeline_results  │        └────────────────────┘
│  pipeline://summary     │
└────────────────────────┘

Skills:  /run-pipeline   /validate-transactions   /write-spec
Hooks:   coverage-gate (.claude/settings.json + .git/hooks/pre-push)
```

## Tech Stack

| Layer | Choice |
|---|---|
| Language | Python 3.11+ |
| Money | `decimal.Decimal` (never `float`) |
| Testing | `pytest` + `pytest-cov` |
| MCP server | `fastmcp` |
| MCP research | `context7` (Upstash) |
| Automation | Claude Code skills (`.claude/commands/`) + coverage-gate hook |

## Key Files

- `specification.md`, `agents.md` — Agent 1 deliverables
- `integrator.py`, `agents/*.py`, `research-notes.md` — Agent 2 deliverables
- `tests/`, `scripts/check_coverage.sh`, `.claude/settings.json`, `.git/hooks/pre-push` — Agent 3 deliverables
- `mcp.json`, `mcp/server.py` — MCP integration
- `README.md`, `HOWTORUN.md` — Agent 4 deliverables

See `HOWTORUN.md` for step-by-step setup and demo instructions.
