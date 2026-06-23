# Plan: Homework 6 — Multi-Agent Banking Pipeline Capstone

## Context

`gen-ai-software-engineering/homework-6/TASKS.md` defines the final capstone: build 4 "meta-agents" (spec writer, code generator, test generator, doc generator) whose *output* is a working file-based multi-agent transaction-processing pipeline (validator → fraud detector → a third agent). Today only `TASKS.md` and `sample-transactions.json` exist in the folder.

`specification-TEMPLATE-hint.md` and the starter `agents.md` mentioned in the task text are **confirmed not present** anywhere in this repo (verified via repo-wide search). `homework-3/specification-TEMPLATE-example.md` **is confirmed present and was read in full** — it contains a "Banking-Specific Specification Template" section that maps directly onto the 5 required `specification.md` sections, so it is the structural reference for Task 1 (no further verification needed before implementation). The starter `agents.md` will be authored from scratch since no seed file exists.

Prior homeworks (confirmed via exploration) establish the house conventions to follow:
- **Python** is the stack used throughout (homework-5's `custom-mcp-server` uses a `.venv`, `fastmcp` v3.4+, `mcp` v1.28+).
- FastMCP servers use `from fastmcp import FastMCP`, `@mcp.tool` / `@mcp.resource` decorators, `mcp.run()`.
- No `mcp.json`, `.claude/commands/*.md`, or coverage/hook config exists anywhere yet in this repo — homework-6 is the first to need them, so they're built fresh, not adapted.
- README/HOWTORUN conventions from hw-1–4: emoji-titled README with a student-name/metadata line near the top, separate `HOWTORUN.md` with numbered setup→run→test steps.

This plan stays entirely inside `gen-ai-software-engineering/homework-6/`. Nothing outside it will be touched. No code will be written in this turn — this is the plan only.

## Correcting the agent-to-task mapping

TASKS.md's agent table is explicit and must be followed exactly:

| Agent | Role | Task |
|---|---|---|
| Agent 1 | Specification | Task 1 |
| Agent 2 | Code generation | Task 2 |
| **Agent 3** | **Unit tests** (coverage hook is its "plus", not its whole job) | **Task 3** |
| **Agent 4** | **Documentation** | **Task 5** |

So: **Task 3 = Agent 3 = write the unit test suite, then add the coverage-gate hook on top of it.** Task 5 = Agent 4 = documentation only (README, HOWTORUN, PR description). The two Claude Code skills (`run-pipeline.md`, `validate-transactions.md`) are infrastructure that supports Agent 3's testing/automation story per TASKS.md Task 3, so they live in Task 3 alongside the tests and hook — not split out into a separate "skills task."

## Chosen stack (for the eventual implementation)

- **Language**: Python 3.11+
- **Money**: `decimal.Decimal` everywhere (never `float`)
- **Test framework**: `pytest` + `pytest-cov`
- **MCP**: `fastmcp` (matches homework-5 precedent) for the custom `pipeline-status` server; `@upstash/context7-mcp` via `npx` for context7
- **Coverage gate mechanism**: a Claude Code `PreToolUse` hook in `.claude/settings.json` (project-local to homework-6) that intercepts `Bash` tool calls matching `git push`, runs `pytest --cov --cov-fail-under=80` (or reads `coverage.json`) and exits non-zero (blocking) if coverage < 80%. A real `.git/hooks/pre-push` companion script is added too — the Claude Code hook gives the screenshot-able "hook firing" demo, the git hook gives literal push-time enforcement.

## Pre-planned context7 queries (Task 2/4 — decide now, log as executed)

Locking these in now so Task 4's "≥2 documented queries" requirement isn't an afterthought:
1. **Query 1** — search "Python decimal module" while writing the `Decimal`/rounding logic shared by `transaction_validator.py` and `fraud_detector.py`; expect a `/python/decimal`-style library ID; apply `ROUND_HALF_UP` (or whatever pattern it surfaces) consistently for amount comparisons/thresholds.
2. **Query 2** — search "fastmcp" while writing `mcp/server.py`; expect the `/jlowin/fastmcp`-style library ID; apply the correct `@mcp.tool` / `@mcp.resource("pipeline://summary")` decorator syntax and `mcp.run()` invocation.
Both get logged into `research-notes.md` in the required format (search term, library ID returned, insight applied) at the point they're actually run — not faked after the fact.

## Target directory layout (to be created in Task execution, not now)

```
homework-6/
├── TASKS.md                          (existing)
├── sample-transactions.json          (existing)
├── specification.md                  [Task 1]
├── agents.md                         [Task 1]
├── research-notes.md                 [Task 2/4]
├── integrator.py                     [Task 2]
├── requirements.txt                  [Task 2]
├── agents/
│   ├── __init__.py
│   ├── transaction_validator.py      [Task 2 — includes __main__ + --dry-run CLI]
│   ├── fraud_detector.py             [Task 2]
│   └── compliance_checker.py         [Task 2 — 3rd required agent]
├── shared/
│   ├── input/ processing/ output/ results/   (created at runtime by integrator)
├── mcp/
│   └── server.py                     [Task 4 — FastMCP: get_transaction_status, list_pipeline_results, pipeline://summary]
├── mcp.json                          [Task 4]
├── .claude/
│   ├── settings.json                 [Task 3 — coverage-gate PreToolUse hook]
│   └── commands/
│       ├── write-spec.md             [Task 1]
│       ├── run-pipeline.md           [Task 3]
│       └── validate-transactions.md  [Task 3]
├── scripts/
│   └── check_coverage.sh (or .py)    [Task 3 — used by both the Claude hook and pre-push hook]
├── tests/
│   ├── test_transaction_validator.py [Task 3]
│   ├── test_fraud_detector.py        [Task 3]
│   ├── test_compliance_checker.py    [Task 3]
│   └── test_integration_pipeline.py  [Task 3]
├── README.md                         [Task 5 — must include student name]
├── HOWTORUN.md                       [Task 5]
└── docs/
    └── screenshots/
        ├── pipeline-run.png
        ├── test-coverage.png
        ├── skill-run-pipeline.png
        ├── hook-trigger.png
        ├── mcp-context7-query.png        (split out per item below)
        └── mcp-tool-call.png             (split out per item below)
```

## Task-by-task execution plan

### Task 1 — Specification (Agent 1)
1. Write `specification.md` with the 5 required sections, using `homework-3/specification-TEMPLATE-example.md`'s "Banking-Specific Specification Template" as the structural skeleton: High-Level Objective; 4-5 Mid-Level Objectives that are concretely testable (e.g. "$10k+ flagged with risk score", "rejects land in shared/results/ with a reason field", "ISO 8601 timestamps on every audit log line", "ISO 4217 currency validation", "coverage ≥ 90%"); Implementation Notes per the Decimal/ISO4217/logging/PII bullets already given in TASKS.md; Context — beginning = `sample-transactions.json`, ending = `shared/results/` + summary report + ≥90% coverage; Low-Level Tasks — one block per agent in the exact `Task/Prompt/File to CREATE/Function to CREATE/Details` format, covering: transaction_validator, fraud_detector, compliance_checker, integrator.
2. Write `agents.md` with two clearly separated, headed sections so the meta layer and the system layer never get confused mid-implementation:
   - **"Meta-Agents (Homework Deliverables)"** — Agent 1–4 from the TASKS.md table, extended with this project's specifics (which files each meta-agent's work produces, which "plus" requirement it satisfies, which model/skill/MCP it uses).
   - **"Pipeline Agents (System Under Construction)"** — transaction_validator, fraud_detector, compliance_checker, integrator: their file paths, the message schema they consume/produce, and their `process_message(message: dict) -> dict` contract.
3. Create `.claude/commands/write-spec.md` — a skill whose body, when invoked, walks Claude Code through regenerating `specification.md` from the template structure above (mirrors the `run-pipeline.md` skill shape given in TASKS.md: numbered steps, references the banking template from homework-3 as structural reference, fills in project-specific objectives).

### Task 2 — Pipeline implementation (Agent 2)
1. Design the shared JSON message schema (already given in TASKS.md) and the `shared/{input,processing,output,results}` directory protocol.
2. Implement 3 agents as plain Python modules with a `process_message(message: dict) -> dict` entrypoint each:
   - `transaction_validator.py` — required fields, `Decimal` amount > 0, ISO 4217 currency check (small allow-list: USD/EUR/GBP/JPY… ; reject XYZ from the sample data), negative-amount handling for `refund` type vs other types. **Also implements a CLI entrypoint**: `if __name__ == "__main__":` with `argparse` supporting `--dry-run`, which loads `sample-transactions.json`, runs every record through validation only (no fraud/compliance steps, no file writes to `shared/`), and prints total/valid/invalid counts plus rejection reasons — this is what `validate-transactions.md` actually invokes (`python agents/transaction_validator.py --dry-run`), so the skill isn't broken on first use.
   - `fraud_detector.py` — risk score from amount thresholds (>$10,000 ⇒ flagged, matches TXN002/TXN005/TXN003-borderline from sample data), unusual timing (e.g. outside 06:00–22:00 local — matches TXN004 at 02:47), cross-border (`metadata.country` ≠ account's home country, or differing source/destination jurisdiction proxy).
   - `compliance_checker.py` (the 3rd required agent) — final disposition combining validator + fraud results, writes to `shared/results/`.
3. `integrator.py` — orchestrator: creates `shared/*` dirs, loads `sample-transactions.json`, wraps each record in the standard message envelope, runs it through validator → fraud_detector → compliance_checker in order, writes intermediate hops to `processing/`/`output/`, final outcome to `results/`, and prints + persists a run summary (for the MCP `pipeline://summary` resource in Task 4).
4. Run the two pre-planned context7 queries (above) while writing the Decimal logic and prepping for the MCP server; log them into `research-notes.md` as they're actually executed.
5. `requirements.txt`: pin `pytest`, `pytest-cov`, `fastmcp`, and anything else used (e.g. `pydantic` if chosen).

### Task 3 — Unit tests + coverage hook (Agent 3)
1. `tests/` — one test module per agent (happy path + rejection/edge cases drawn directly from `sample-transactions.json`: TXN006 bad currency, TXN007 negative amount on a refund, TXN002/TXN005 high-value fraud flags, TXN004 odd-hour flag) plus `test_integration_pipeline.py` driving `integrator.py` end-to-end against a `tmp_path`-isolated `shared/` (never touch the real `shared/` dir from tests). Also a small test for the validator's `--dry-run` CLI path.
2. `scripts/check_coverage.sh`: runs `pytest --cov=agents --cov=integrator --cov-report=json --cov-fail-under=80`; non-zero exit on failure.
3. `.claude/settings.json`: add a `PreToolUse` hook matched on `Bash` tool invocations whose command contains `git push`, which shells out to `scripts/check_coverage.sh` and blocks (denies) the tool call on failure.
4. Add a literal `.git/hooks/pre-push` (executable, calls the same `scripts/check_coverage.sh`) so the gate is enforced even outside Claude Code.
5. `.claude/commands/run-pipeline.md` and `.claude/commands/validate-transactions.md` — copy the bodies already specified verbatim in TASKS.md (steps are given), adapted to the actual file paths chosen above; `validate-transactions.md` relies on the `--dry-run` CLI built in Task 2.
6. Capture `docs/screenshots/skill-run-pipeline.png` (running `/run-pipeline`), `docs/screenshots/test-coverage.png` (coverage report ≥80%, ideally ≥90%), and `docs/screenshots/hook-trigger.png` (the hook firing/blocking — deliberately drop coverage and attempt a push, then restore and push again to show it passing).

### Task 4 — MCP integration
1. `mcp.json` at `homework-6/` root: both `context7` (npx) and `pipeline-status` (`python mcp/server.py`) entries, exactly per the schema given in TASKS.md.
2. `mcp/server.py` using `fastmcp.FastMCP`:
   - `@mcp.tool get_transaction_status(transaction_id: str)` — reads `shared/results/*.json`, returns the matching record's status.
   - `@mcp.tool list_pipeline_results()` — aggregates all files in `shared/results/` into a summary (counts by status/disposition).
   - `@mcp.resource("pipeline://summary")` — returns the latest run's textual summary (written by `integrator.py`).
3. Finish `research-notes.md` with both context7 queries fully documented.
4. Capture **two separate screenshots** (TASKS.md requires both a context7 query result and a custom MCP tool call to be visible): `docs/screenshots/mcp-context7-query.png` (a real context7 lookup result) and `docs/screenshots/mcp-tool-call.png` (calling `get_transaction_status` or `list_pipeline_results` against real `shared/results/` data). Both get referenced under the single "MCP usage" bullet in the PR description.

### Task 5 — Documentation (Agent 4)
1. `README.md` — include "Created by [Name]" line (will ask the user for their name before writing this, since it's not yet known), 1-2 paragraph system description, one bullet per agent's responsibility, an ASCII pipeline diagram (input → validator → fraud_detector → compliance_checker → results, with the MCP server and skills annotated alongside), and a tech-stack table.
2. `HOWTORUN.md` — numbered steps: install deps, set up `mcp.json`, run `integrator.py`, run tests/coverage, invoke `/run-pipeline` and `/validate-transactions`, query the MCP server.
3. **PR description** — last concrete step: write the PR description text embedding/linking all required screenshots (spec produced, pipeline run, tests/coverage, skill/hook in action, both MCP screenshots, README showing the name) each with a one-line caption, ready to paste into the actual PR.

## Order of operations (per "Tips for Success" in TASKS.md)

Strictly sequential, finishing and smoke-testing each before moving on:
1. Task 1 (spec + agents.md + write-spec skill) — sign off on `specification.md` before any code.
2. Task 2, one agent at a time: validator (incl. `--dry-run`) → smoke-test manually against the sample file → fraud_detector → compliance_checker → integrator wiring them together. Run and log the 2 context7 queries as they happen.
3. Task 3 (Agent 3: tests, then coverage hook) — once there's real code to test.
4. Task 4 (MCP) — once `shared/results/` is actually being populated, so the tools have real data to query.
5. Task 5 (Agent 4: docs + PR description) last.
6. Screenshots taken live during each step above, saved straight into `docs/screenshots/` as each milestone is hit.

## Success-criteria cross-check (from TASKS.md, to verify before calling this done)

| Criterion | Plan coverage |
|---|---|
| `specification.md` 5 sections + Low-Level Tasks per agent | Task 1 |
| Skill generating spec from template present | Task 1, `write-spec.md` |
| Pipeline runs end-to-end with no errors | Task 2, smoke-tested per agent |
| All agents write valid JSON to `shared/` | Task 2 message envelope |
| `/run-pipeline` skill executes pipeline | Task 3 |
| Coverage-gate hook configured, blocks push <80% | Task 3, dual hook (Claude + git) |
| `mcp.json` has both servers, both respond | Task 4 |
| Coverage ≥80% gate, aim ≥90% | Task 3 |
| README has name + ASCII diagram | Task 5 (need user's name) |
| `HOWTORUN.md` numbered steps | Task 5 |
| 5 screenshots in `docs/screenshots/` + in PR description | Captured live throughout (6 files since MCP needs 2); PR description written explicitly in Task 5 |

## Open item before implementation starts

Need the user's actual name for the required "Created by [Name]" line in `README.md` — will ask once we move to implementation (not blocking the plan itself).

## Verification (once implemented)

- `python integrator.py` from `homework-6/` — all 8 sample transactions land in `shared/results/` with no unhandled exceptions.
- `python agents/transaction_validator.py --dry-run` — prints total/valid/invalid counts and rejection reasons without touching `shared/`.
- `pytest --cov=agents --cov=integrator --cov-report=term-missing` — coverage ≥ 80% (target ≥ 90%).
- Trigger `/run-pipeline` and `/validate-transactions` skills inside Claude Code and confirm they execute as written.
- Attempt a `git push` with coverage artificially dropped below 80% to confirm the hook blocks it; restore and push again to confirm it lets a passing build through.
- Start `mcp/server.py` per `mcp.json` and call `get_transaction_status`, `list_pipeline_results`, and read the `pipeline://summary` resource against real `shared/results/` data; separately run the two pre-planned context7 queries and record them.
