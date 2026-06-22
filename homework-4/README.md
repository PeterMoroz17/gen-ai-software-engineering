# Homework 4 — 4-Agent Pipeline

**Author**: Peter Moroz (peter.moroz17@gmail.com)

## Overview

This is a self-contained, single-command pipeline that runs 4 required agents
(plus 2 unsupervised connective steps) end-to-end against a small sample CLI
app (`src/`) that has 2 intentional bugs and 1 intentional security issue
seeded into it. The whole run produces real, inspectable artifacts under
`context/bugs/001/`, applies real code fixes, and adds real passing unit
tests — with **zero manual per-agent invocation**.

```
Bug Researcher → Research Verifier → Bug Planner → Bug Fixer → Security Verifier → Unit Test Generator
```

The first and third stages (Bug Researcher, Bug Planner) are not graded
agents — they're small connective steps that produce the inputs the four
required agents read (`codebase-research.md` and `implementation-plan.md`
respectively), inline-prompted by the orchestrator rather than defined as
`*.agent.md` files.

## The sample app (Task 5)

A tiny dependency-free Node CLI bookmark manager (`src/bookmarks.js`,
`src/index.js`) with 3 seeded issues, described in
[`context/bugs/001/bug-context.md`](context/bugs/001/bug-context.md):

1. **Pagination off-by-one** — `listBookmarks` sliced one item short, so the
   last bookmark of every page was silently dropped.
2. **Remove-by-id type mismatch** — the CLI passed a raw string id into a
   strict `!==` comparison against numeric stored ids, so `remove` always
   silently no-op'd.
3. **Command injection (security)** — `checkUrlReachable` interpolated an
   unsanitized host straight into a shell string passed to
   `child_process.exec`.

All three are genuinely reproducible pre-fix (verified manually, not just by
inspection) and were fixed by the pipeline (see
[`context/bugs/001/fix-summary.md`](context/bugs/001/fix-summary.md)).

**Note on the baseline tests**: `tests/bookmarks.test.js`'s original 3 tests
intentionally do not exercise either seeded bug — they only cover the
already-correct behavior that existed before the pipeline ran. This is
deliberate: the pipeline's own Unit Test Generator stage is what adds
regression tests for the bug fixes (5 new tests, see
[`context/bugs/001/test-report.md`](context/bugs/001/test-report.md)), so the
"before" state legitimately shows 3/3 green despite the bugs being present.

## The 4 required agents and their models

| Agent | File | Model | Why this model |
|---|---|---|---|
| Bug Research Verifier | `agents/research-verifier.agent.md` | `claude-opus-4-8` | Fact-checking file:line claims and scoring research quality against a rubric needs strong reasoning to avoid rubber-stamping incorrect claims. |
| Bug Fixer | `agents/bug-fixer.agent.md` | `claude-haiku-4-5-20251001` | By this stage the plan already specifies exact before/after code — mechanical execution of a known plan, so a fast/cheap model is sufficient. |
| Security Vulnerabilities Verifier | `agents/security-verifier.agent.md` | `claude-opus-4-8` | Reliably spotting injection/validation/comparison issues (not just keyword matching) benefits from the strongest available reasoning model. |
| Unit Test Generator | `agents/unit-test-generator.agent.md` | `claude-haiku-4-5-20251001` | Scaffolding tests for an already-understood, already-fixed diff is routine, well-specified work. |

The two connective helper steps (Bug Researcher, Bug Planner) run on
`claude-haiku-4-5-20251001` as well — they were originally on
`claude-sonnet-4-6`, but that model's long-context handling on this account
required additional usage credits even for these short prompts, so they were
switched to Haiku, which runs them without issue.

## The 2 skills

- [`skills/research-quality-measurement.md`](skills/research-quality-measurement.md) —
  defines the Excellent/Good/Fair/Poor research-quality rubric (reference
  accuracy %, completeness, clarity) that the Research Verifier must use when
  writing `verified-research.md`.
- [`skills/unit-tests-FIRST.md`](skills/unit-tests-FIRST.md) — defines
  Fast/Independent/Repeatable/Self-validating/Timely with concrete guidance
  for this stack, used by the Unit Test Generator.

## Running the pipeline

See [HOWTORUN.md](HOWTORUN.md). In short: `npm run pipeline`. No manual prompt
entry, no per-agent invocation — `scripts/run-pipeline.js` shells out to the
`claude` CLI once per stage in headless mode
(`--permission-mode bypassPermissions`), loading each stage's model and
instructions straight from the `agents/*.agent.md` and `skills/*.md` files.

## Design record

[`PLAN.md`](PLAN.md) is the approved implementation plan this homework was
built from, kept here as a documentation artifact.

## Generated artifacts

All under [`context/bugs/001/`](context/bugs/001/):
`research/codebase-research.md`, `research/verified-research.md`,
`implementation-plan.md`, `fix-summary.md`, `security-report.md`,
`test-report.md`.

## Screenshots

See [`docs/screenshots/`](docs/screenshots/):

- `pipeline-run-1/2.png` — the full `npm run pipeline` run, all 6 stages
- `app-before.png` / `app-after.png` — the seeded bugs reproducing, then fixed
- `fixes-applied-1/2/3.png` — `fix-summary.md`'s before/after code for all 3 fixes
- `security-scan-1/2.png` — `security-report.md`'s findings and verdict
- `unit-tests.png` — `npm test` showing 8/8 passing
- `ai-planning-1..4.png` — the original planning prompt, the approved plan, and the resulting todo list
- `ai-agent-scaffold-1..4.png` — all 4 actual `*.agent.md` files

One screenshot type called for by the assignment, `ai-pipeline-debug` (a live
moment of Claude diagnosing a pipeline failure), was lost to a session
compaction during development. The two real debugging incidents it would have
shown are documented in text instead: the "Usage credits are required for
long context requests" model swap (see `PLAN.md`'s "Post-plan deviation"
section) and the Windows CRLF frontmatter-parsing bug in
`scripts/run-pipeline.js` (the `readFile` normalizes `\r\n` to `\n` specifically
because of this).
