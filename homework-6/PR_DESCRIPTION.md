# Homework 6: Multi-Agent Banking Pipeline Capstone

## Summary

- Built a 3-agent file-based transaction pipeline (validator → fraud detector → compliance checker) orchestrated by `integrator.py`, producing auditable results for all 8 sample transactions.
- Added the 4 required meta-agent deliverables: `specification.md` + `agents.md` + `/write-spec` skill (Agent 1), the pipeline code with 2 documented context7 lookups in `research-notes.md` (Agent 2), a 90%-coverage test suite plus a dual coverage-gate hook (Claude Code `PreToolUse` + real `git pre-push`) and the `/run-pipeline` / `/validate-transactions` skills (Agent 3), and this README/HOWTORUN (Agent 4).
- Added a custom FastMCP server (`mcp/server.py`) exposing `get_transaction_status`, `list_pipeline_results`, and the `pipeline://summary` resource, configured alongside `context7` in `mcp.json`.

## Test plan

- [x] `python integrator.py` — all 8 transactions land in `shared/results/` with no errors (1 rejected for bad currency, 2 flagged for review, 5 cleared).
- [x] `python agents/transaction_validator.py --dry-run` — reports 7 valid / 1 invalid without touching `shared/`.
- [x] `python -m pytest --cov=agents --cov=integrator` — 28 tests passing, ~90% coverage (gate is 80%).
- [x] Coverage gate verified to actually block: temporarily raised the local threshold to 95%, confirmed `scripts/check_coverage.sh` exits non-zero and the installed `.git/hooks/pre-push` blocks; restored to 80% and confirmed it passes again.
- [x] FastMCP server verified via `fastmcp.Client` in-process: `get_transaction_status`, `list_pipeline_results`, and `pipeline://summary` all return correct data against real `shared/results/`.
- [ ] **Manual, not yet captured**: `/run-pipeline` and `/validate-transactions` skills exercised live inside Claude Code.
- [ ] **Manual, not yet captured**: a live `context7` MCP query inside Claude Code (the lookups in `research-notes.md` were researched via web search since context7 wasn't connected as a live MCP tool in this automated session — re-run them live for the required screenshot).

## Screenshots

> The following must be captured manually (this PR description is a template — replace the `_(capture pending)_` markers with the actual embedded images from `docs/screenshots/`):

| Screenshot | Status |
|---|---|
| `docs/screenshots/pipeline-run.png` — full terminal output of `python integrator.py` | _(capture pending)_ |
| `docs/screenshots/test-coverage.png` — coverage report ≥ 80% | _(capture pending)_ |
| `docs/screenshots/skill-run-pipeline.png` — `/run-pipeline` executing in Claude Code | _(capture pending)_ |
| `docs/screenshots/hook-trigger.png` — coverage-gate hook firing/blocking a push | _(capture pending)_ |
| `docs/screenshots/mcp-context7-query.png` — a real context7 query result | _(capture pending)_ |
| `docs/screenshots/mcp-tool-call.png` — `get_transaction_status` or `list_pipeline_results` called via MCP | _(capture pending)_ |
| README showing "Created by Peter Moroz" | See `README.md` line 3 |
