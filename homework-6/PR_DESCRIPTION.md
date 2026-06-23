# feat: homework-6 - Multi-Agent Banking Transaction Pipeline (Final Capstone)

## Summary

Implements **Homework 6: Final Capstone** - four meta-agents (specification, code generation, unit tests, documentation) that together produce a working multi-agent banking transaction pipeline. The pipeline itself is three cooperating, file-based agents (`transaction_validator` → `fraud_detector` → `compliance_checker`) orchestrated by `integrator.py`, communicating exclusively through JSON message envelopes under `shared/`. Built with Python 3.11+, `decimal.Decimal` for all monetary values, `pytest`/`pytest-cov` for testing, and `fastmcp` for a custom MCP server. The workflow used Claude Code throughout for planning and implementation, plus two independent external AI review passes (one of the plan, one of the in-progress code) and a third pass that caught and corrected a mistake in the second review's own documentation - all captured below.

---

## What Was Produced

### Agent 1 - Specification

- `specification.md` - all 5 required sections: High-Level Objective, 4 Mid-Level Objectives, Implementation Notes (Decimal-only money, ISO 4217 currency, ISO 8601 audit logging, PII masking), Context (beginning/ending state), and Low-Level Tasks (one per pipeline agent in the `Task/Prompt/File/Function/Details` format).
- `agents.md` - split into two clearly headed sections: **Meta-Agents (Homework Deliverables)** describing Agent 1-4's roles and "plus" requirements, and **Pipeline Agents (System Under Construction)** describing the 3 runtime agents' contracts and the shared message envelope.
- Skill: `.claude/commands/write-spec.md` - regenerates `specification.md` from the homework-3 banking template on demand.

### Agent 2 - Code Generation

- `agents/transaction_validator.py` - required-field checks, `Decimal`-based amount validation (positive, or negative only for `refund`), ISO 4217 currency allow-list, plus a `--dry-run` CLI mode that prints a formatted `transaction_id | valid/invalid | reason` table without touching `shared/`.
- `agents/fraud_detector.py` - risk scoring 0-100 (+50 high-value >$10,000, +20 odd-hour 00:00-06:00 UTC, +15 cross-border), flags anything ≥50 for review.
- `agents/compliance_checker.py` - the third required agent: combines upstream results into a final disposition (`cleared` / `rejected` / `flagged_for_review`) and writes it to `shared/results/`.
- `integrator.py` - orchestrates all three agents per transaction, sets up the `shared/{input,processing,output,results}` protocol, and persists a run summary.
- `research-notes.md` - two **live** `context7` MCP queries (not web search): "Python decimal module" → `/python/cpython`, and "FastMCP" → `/prefecthq/fastmcp`, each with the concrete pattern applied to the code.

### Agent 3 - Unit Tests + Coverage Gate

- `tests/` - 34 tests across `test_transaction_validator.py`, `test_fraud_detector.py`, `test_compliance_checker.py`, `test_common.py`, and an integration suite (`test_integration_pipeline.py`) that drives the full pipeline end-to-end against a `tmp_path`-isolated `shared/`, never touching the real one. **98% coverage** (gate is 80%, spec target was ≥90%).
- A **dual coverage gate**: a Claude Code `PreToolUse` hook (`.claude/settings.json` + `scripts/claude_coverage_gate.sh`, which parses the hook's stdin JSON itself to filter on `git push` rather than relying on an unsupported config-level filter) and a real `.git/hooks/pre-push` (installed from the tracked `scripts/pre-push` template, since `.git/hooks/` itself isn't version-controlled). Both call the same `scripts/check_coverage.sh`, which probes multiple Python interpreters to find one with `pytest` actually installed (a real issue hit during testing - see Challenges below).
- Skills: `.claude/commands/run-pipeline.md` and `.claude/commands/validate-transactions.md`, both invoked live as actual Claude Code slash commands for this PR's screenshots, not just run manually in a terminal.

### Agent 4 - Documentation

- `README.md` - author line ("Created by Peter Moroz"), system overview, agent responsibilities, ASCII pipeline diagram, tech stack table, and a Process Documentation section pointing at the external review material.
- `HOWTORUN.md` - numbered setup-to-demo steps.
- `mcp.json` + `mcp/server.py` - `context7` and a custom `pipeline-status` FastMCP server (`get_transaction_status`, `list_pipeline_results`, `pipeline://summary`), both connected and exercised live through Claude Code.

---

## AI Workflow Documentation

### Stage 1 - Planning (Claude Code)

Asked Claude Code to read `TASKS.md` and produce a detailed implementation plan before writing any code. The plan was reviewed and corrected once in-session (agent-to-task mapping, missing `--dry-run` CLI requirement, template-source confirmation) before approval.

![Initial task prompt](https://raw.githubusercontent.com/PeterMoroz17/gen-ai-software-engineering/homework-6-submission/homework-6/docs/process/01-task-prompt.png)
![Plan overview - layout and task breakdown](https://raw.githubusercontent.com/PeterMoroz17/gen-ai-software-engineering/homework-6-submission/homework-6/docs/process/plan-overview-1.png)
![Plan - target directory layout](https://raw.githubusercontent.com/PeterMoroz17/gen-ai-software-engineering/homework-6-submission/homework-6/docs/process/plan-directory-layout.png)
![Plan overview - task-by-task plan](https://raw.githubusercontent.com/PeterMoroz17/gen-ai-software-engineering/homework-6-submission/homework-6/docs/process/plan-overview-2.png)
![Plan - order of operations and success-criteria cross-check](https://raw.githubusercontent.com/PeterMoroz17/gen-ai-software-engineering/homework-6-submission/homework-6/docs/process/plan-order-and-verification.png)

### Stage 2 - Pipeline build and verification (Claude Code)

Built the 3 pipeline agents one at a time, smoke-testing each against the sample data before moving to the next, then ran the full pipeline and test suite.

![Full pipeline run - all 8 transactions processed](https://raw.githubusercontent.com/PeterMoroz17/gen-ai-software-engineering/homework-6-submission/homework-6/docs/screenshots/pipeline-run.png)
![Test suite - 34 passed, 98% coverage](https://raw.githubusercontent.com/PeterMoroz17/gen-ai-software-engineering/homework-6-submission/homework-6/docs/screenshots/test-coverage.png)

### Stage 3 - Skills executed live via AI

Both required skills invoked as real Claude Code slash commands (not their underlying terminal commands run manually), so the AI itself carried out the documented procedure.

![/run-pipeline executed via AI](https://raw.githubusercontent.com/PeterMoroz17/gen-ai-software-engineering/homework-6-submission/homework-6/docs/screenshots/skill-run-pipeline.png)
![/validate-transactions executed via AI](https://raw.githubusercontent.com/PeterMoroz17/gen-ai-software-engineering/homework-6-submission/homework-6/docs/process/skill-validate-transactions.png)

### Stage 4 - Coverage gate hook firing for real

Demonstrated the gate genuinely blocking (threshold temporarily raised above true coverage to force a real failure) and then passing once restored.

![Coverage gate blocking a real git push](https://raw.githubusercontent.com/PeterMoroz17/gen-ai-software-engineering/homework-6-submission/homework-6/docs/screenshots/hook-trigger.png)
![Coverage gate restored and passing](https://raw.githubusercontent.com/PeterMoroz17/gen-ai-software-engineering/homework-6-submission/homework-6/docs/process/hook-restore-and-pass.png)

### Stage 5 - MCP servers connected and queried live

Both `context7` and the custom `pipeline-status` server connected through Claude Code's `.mcp.json`, then exercised with real tool calls and queries (not simulated). TASKS.md's screenshot table names this requirement `mcp-interaction.png` (one screenshot showing both a context7 query result and a custom MCP tool call); that exact file is included below and is a duplicate of `mcp-context7-query.png`, which already shows both calls in the same capture. It's also split into two more granular files (`mcp-context7-query.png` / `mcp-tool-call.png`) for clarity.

![Both a context7 query result and a custom MCP tool call, per TASKS.md's mcp-interaction.png requirement](https://raw.githubusercontent.com/PeterMoroz17/gen-ai-software-engineering/homework-6-submission/homework-6/docs/screenshots/mcp-interaction.png)
![Live context7 queries: resolve-library-id and query-docs](https://raw.githubusercontent.com/PeterMoroz17/gen-ai-software-engineering/homework-6-submission/homework-6/docs/screenshots/mcp-context7-query.png)
![context7 query-docs results in detail](https://raw.githubusercontent.com/PeterMoroz17/gen-ai-software-engineering/homework-6-submission/homework-6/docs/process/context7-query-docs-only.png)
![Custom MCP tool calls: get_transaction_status and list_pipeline_results](https://raw.githubusercontent.com/PeterMoroz17/gen-ai-software-engineering/homework-6-submission/homework-6/docs/screenshots/mcp-tool-call.png)

### Stage 6 - Independent multi-pass review, including a self-correction

Beyond the primary build, the plan and the in-progress code were separately reviewed by other AI sessions - and one of those reviews was itself later found to need correcting, which is documented rather than hidden.

**Pass 1 - Plan review**, before any code was written. Caught the same agent-mislabeling and `--dry-run`-gap issues independently:

![Plan review - critical gaps found](https://raw.githubusercontent.com/PeterMoroz17/gen-ai-software-engineering/homework-6-submission/homework-6/docs/process/external-review/01-plan-review-critique.png)
![Plan review - secondary tightening suggestions](https://raw.githubusercontent.com/PeterMoroz17/gen-ai-software-engineering/homework-6-submission/homework-6/docs/process/external-review/02-plan-review-tightening-and-solid-parts.png)
![Plan review - approved, ready to execute](https://raw.githubusercontent.com/PeterMoroz17/gen-ai-software-engineering/homework-6-submission/homework-6/docs/process/external-review/03-plan-review-approved.png)

**Pass 2 - Implementation review**, mid-build. Independently caught real, since-fixed issues (`integrator.py` untested `main()`, the `validate-transactions.md` table-vs-plain-text mismatch, an invalid hook config field, missing `.gitignore`, a ghost nested directory):

![Implementation review - initial B-/6.5 rating](https://raw.githubusercontent.com/PeterMoroz17/gen-ai-software-engineering/homework-6-submission/homework-6/docs/process/external-review/04-impl-review-initial-rating-b-minus.png)
![Implementation review - detailed findings](https://raw.githubusercontent.com/PeterMoroz17/gen-ai-software-engineering/homework-6-submission/homework-6/docs/process/external-review/05-impl-review-issues-detail.png)
![Implementation review - re-scoped pre-run gaps](https://raw.githubusercontent.com/PeterMoroz17/gen-ai-software-engineering/homework-6-submission/homework-6/docs/process/external-review/06-impl-review-prerun-gaps.png)
![Implementation review - premature "ready to run" claim](https://raw.githubusercontent.com/PeterMoroz17/gen-ai-software-engineering/homework-6-submission/homework-6/docs/process/external-review/07-impl-review-premature-ready-claim.png)

**Pass 3 - a third session disputes this PR's own draft documentation.** An earlier draft of this PR's notes accused Pass 2 of fabricating its "97% coverage, 31 tests" figures without running any code. A third, independent review session disputed that characterization:

![Third review disputes the "hallucination" label](https://raw.githubusercontent.com/PeterMoroz17/gen-ai-software-engineering/homework-6-submission/homework-6/docs/process/external-review/08-third-review-disputes-mistake-label.png)
![Third review - submission checklist confirmation](https://raw.githubusercontent.com/PeterMoroz17/gen-ai-software-engineering/homework-6-submission/homework-6/docs/process/external-review/09-third-review-todo-summary.png)

Checking Pass 2's actual tool-call history confirmed Pass 3 was right - both coverage figures came from genuine `pytest` executions, verifiable by matching their exact reported uncovered-line numbers against this codebase's real history at those two points in time:

![Real execution evidence - run 1: 28 tests, 89% coverage](https://raw.githubusercontent.com/PeterMoroz17/gen-ai-software-engineering/homework-6-submission/homework-6/docs/process/external-review/10-evidence-real-run-1-28-tests-89pct.png)
![Real execution evidence - run 2: 31 tests, 97% coverage](https://raw.githubusercontent.com/PeterMoroz17/gen-ai-software-engineering/homework-6-submission/homework-6/docs/process/external-review/11-evidence-real-run-2-31-tests-97pct.png)

The genuine mistake was narrower than originally documented: Pass 2 called the project "ready to run" while it was still 3 tests and 1 coverage point short of its final state (34 tests / 98%) - a premature "done" judgment, not invented data. Full writeup in `docs/process/external-review/README.md`.

---

## Challenges & Solutions

| Challenge | How it was resolved |
|---|---|
| The plan initially mapped "Agent 3" to skills/hooks and bundled unit tests into Agent 4's task, contradicting `TASKS.md`'s explicit agent table | Corrected before implementation: Task 3 = Agent 3 = unit tests + coverage hook; Task 5 = Agent 4 = documentation only |
| `validate-transactions.md` promised a formatted table but `transaction_validator.py --dry-run` only printed plain text | Added a `transaction_id \| valid/invalid \| reason` table to the CLI's actual output so the skill's claim matches reality |
| `.claude/settings.json` used an `"if": "Bash(git push)"` key, which isn't a real Claude Code hook field - the hook would have fired on every Bash command | Moved the filtering logic inside `claude_coverage_gate.sh` itself, which parses the hook's stdin JSON and checks `tool_input.command` directly |
| Account masking (`mask_account`) always emitted exactly 3 asterisks regardless of input length, producing inconsistent output like `***1001` for an 8-character account number | Rewrote it to mask proportionally (`****1001` for `ACC-1001`), with new tests covering empty/short/normal inputs |
| `scripts/check_coverage.sh` failed inside git's actual hook shell with "No module named pytest" - the first `python` on PATH (an MSYS2 build) didn't have `pytest` installed, unlike the Windows Store Python used everywhere else | Made the script probe a list of candidate interpreters and pick the first one that can actually `import pytest`, instead of trusting the first `python` found on PATH |
| `/run-pipeline` and `/validate-transactions` skills weren't recognized by Claude Code because `.claude/commands/` was scoped to the `homework-6/` subfolder while the session's project root was the parent repo | Copied the skill (and later, MCP) configs up to the actual project root and reloaded the session, confirming the project-root scoping requirement explicitly rather than working around it |
| An early draft of the external-review documentation accused a reviewing AI session of fabricating coverage numbers it had supposedly never run | Verified against that session's actual tool-call evidence before publishing the claim, found it was wrong, and corrected the documentation rather than leaving an unverified accusation in place |

---

## Checklist

- [x] `specification.md` - all 5 sections, Low-Level Tasks per pipeline agent
- [x] `agents.md` - meta-agents and pipeline-agents clearly split, extended from the project's specifics
- [x] Skill `.claude/commands/write-spec.md` generates the spec from the homework-3 template
- [x] 3 cooperating pipeline agents (`transaction_validator`, `fraud_detector`, `compliance_checker`) + `integrator.py`, run end-to-end with no errors on all 8 sample transactions
- [x] All agents communicate via valid JSON envelopes through `shared/{input,processing,output,results}`
- [x] `research-notes.md` - 2 context7 queries run live through the connected MCP server, with library IDs and applied insights
- [x] `tests/` - 34 tests, 98% coverage (gate ≥80%, target ≥90% met)
- [x] Dual coverage-gate hook (Claude Code `PreToolUse` + real `git pre-push`), verified to both block and pass for real
- [x] `/run-pipeline` and `/validate-transactions` skills invoked live as actual AI-executed slash commands
- [x] `mcp.json` configures both `context7` and the custom `pipeline-status` server; both verified live
- [x] `mcp/server.py` exposes `get_transaction_status`, `list_pipeline_results`, and the `pipeline://summary` resource
- [x] `README.md` - author name ("Created by Peter Moroz"), ASCII architecture diagram, tech stack table, agent responsibilities
- [x] `HOWTORUN.md` - numbered setup-to-demo steps
- [x] All 6 required screenshots in `docs/screenshots/`, embedded above and in `README.md` (plus `mcp-interaction.png` included verbatim to match TASKS.md's exact filename, alongside the more granular `mcp-context7-query.png`/`mcp-tool-call.png` split)
- [x] Bonus: full planning and independent-review documentation in `docs/process/`, including a transparently corrected mistake in the review documentation itself
