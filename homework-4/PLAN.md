# Homework 4 — 4-Agent Pipeline (gen-ai-software-engineering/homework-4)

> This is the approved implementation plan, kept here verbatim as the design
> record for this submission.

## Context

`gen-ai-software-engineering/homework-4` currently contains only `TASKS.md`. The
assignment requires: a small sample app with 2 seeded bugs + 1 seeded security
issue, 4 required agents (`*.agent.md`) with justified model choices, 2 skills
(research-quality rubric, FIRST), and a **single command** that runs the whole
pipeline end-to-end with no manual per-agent invocation — producing real
artifacts, passing tests, and screenshots.

Key constraint to design around: a prior attempt at this kind of headless
multi-stage `claude -p` pipeline broke because each stage's permission mode
still prompted interactively for Bash/tool approval, defeating the "single
command, no manual steps" requirement. `claude --help` confirms
`--permission-mode bypassPermissions` is the documented way to run `-p`
headless with zero interactive prompts — the orchestrator must use that (not
`acceptEdits`, which still gates Bash) for every stage that touches the
filesystem or runs tests.

All work happens only inside `gen-ai-software-engineering/homework-4/`.

## Group 1 — Build agents (Tasks 1–4 + 2 skills)

`homework-4/skills/`:
- `research-quality-measurement.md` — rubric defining Excellent/Good/Fair/Poor
  research-quality levels (reference accuracy %, completeness, clarity), with
  a required-output section (accuracy %, level + justification, go/no-go for
  the planning step).
- `unit-tests-FIRST.md` — defines Fast/Independent/Repeatable/
  Self-validating/Timely with concrete per-property guidance for this stack
  (no real timers/network, no shared state, `assert`-based, scoped to the diff).

`homework-4/agents/` — one `*.agent.md` per required agent, each with YAML
frontmatter (`name`, `description`, `model`, `model_justification`, `tools`)
and a body covering Role / Inputs / Process / Required output sections /
Constraints:

| Agent | Model | Why |
|---|---|---|
| `research-verifier.agent.md` | `claude-opus-4-8` | Fact-checking file:line claims and scoring quality needs deep reasoning to avoid rubber-stamping. |
| `bug-fixer.agent.md` | `claude-haiku-4-5-20251001` | Plan already has exact before/after code — mechanical execution. |
| `security-verifier.agent.md` | `claude-opus-4-8` | Reliable injection/validation analysis benefits from the strongest reasoning model. |
| `unit-test-generator.agent.md` | `claude-haiku-4-5-20251001` | Scaffolding tests for an already-fixed, already-understood diff is routine. |

Each agent file's responsibilities/required-output-sections must match
TASKS.md exactly (e.g. research-verifier's `verified-research.md` needs
Verification Summary / Verified Claims / Discrepancies Found / Research
Quality Assessment / References; security-verifier is report-only, no Edit
tool; unit-test-generator must cite the FIRST skill explicitly).

Two short connective steps (not graded agents, just inline prompts in the
orchestrator) are needed to produce the inputs Tasks 1–2 read: a "Bug
Researcher" step that writes `context/bugs/001/research/codebase-research.md`
from `bug-context.md` + the real source, and a "Bug Planner" step that turns
verified research into `implementation-plan.md` (exact before/after snippets
+ test command). These run with a balanced default model
(`claude-sonnet-4-6`).

## Group 2 — Build app (Task 5)

Create a small, dependency-free Node.js CLI app under `homework-4/src/` (+
`homework-4/tests/`, `homework-4/data/`) with **2 intentional bugs + 1
intentional security issue**, all genuinely reproducible (verified by actually
running the app, not just by code inspection):

- `src/bookmarks.js` — core logic: `addBookmark`, `listBookmarks`,
  `removeBookmark`, `checkUrlReachable`.
- `src/index.js` — CLI entry point (`add`/`list`/`remove`/`check` commands),
  reading/writing `data/bookmarks.json`.
- `tests/*.test.js` — Node's built-in `node:test` runner (`npm test` →
  `node --test`), covering only the pre-existing correct behavior.
- `package.json` — `scripts.start`, `scripts.test`, `scripts.pipeline`.

Seeded issues (each must actually trigger the described symptom end-to-end):
1. **Pagination off-by-one** — `listBookmarks` slices one short, dropping the
   last item of every page.
2. **Type-mismatch removal bug** — `removeBookmark` does a strict `!==`
   comparison; the CLI must pass the raw string id through (no premature
   `Number()` coercion in `index.js`) so the comparison genuinely never
   matches and removal silently no-ops. **Verify this manually before
   finalizing** — it's easy to write this bug in the helper function but
   accidentally neutralize it with a type coercion elsewhere in the CLI glue
   code, which would make the "bug" undetectable by the pipeline.
3. **Security: command injection** — `checkUrlReachable` builds a shell string
   via interpolation and runs it with `child_process.exec`, e.g.
   `` exec(`ping -n 1 ${host}`) `` — host is taken from user input with no
   allow-listing/validation.

`context/bugs/001/bug-context.md` — the user-facing bug report describing all
3 symptoms, written as input for the pipeline's research stage.

**Verification for this group**: run the app manually (add 10+ bookmarks,
confirm page 1 size 10 drops the 10th; confirm `remove <id>` reports removed
but the item is still present), run `npm test` (all pre-existing tests green),
and confirm (by reading the code, not exploiting it) that `checkUrlReachable`
would pass attacker-controlled string into `exec`.

## Group 3 — Run them (single-command pipeline)

`homework-4/scripts/run-pipeline.js` (invoked via `npm run pipeline`):
- Shells out to the real `claude` CLI once per stage, in order: Bug Researcher
  → Research Verifier → Bug Planner → Bug Fixer → Security Verifier → Unit
  Test Generator.
- For each required-agent stage, loads `model` from that agent file's
  frontmatter and builds the system prompt from the agent body (+ the
  relevant skill file, stripped of its own frontmatter) — no hardcoded
  duplication of agent instructions in the script.
- **Critical fix vs. the naive approach**: every `claude -p` call uses
  `--permission-mode bypassPermissions` (confirmed via `claude --help` as a
  valid mode), not `acceptEdits` — `acceptEdits` still interactively gates
  Bash/test execution, which is exactly what breaks "single command, no
  manual invocation." `--disallowedTools Edit` stays on the Security Verifier
  stage so it truly cannot touch source.
- Captures stdout/stderr per stage into a transcript, writes it to
  `docs/screenshots/pipeline-run-transcript.txt`, and exits non-zero (stopping
  the pipeline) if any stage fails — matching the Bug Fixer's "stop and
  document, don't guess" contract.

Execution + verification steps (in order):
1. `npm install` (none needed, zero deps) / `npm test` — confirm baseline
   green before the pipeline touches anything.
2. Manually re-confirm the 2 bugs + security issue reproduce (Group 1's
   verification), since the whole pipeline's credibility depends on the
   seeded issues being real.
3. `npm run pipeline` — run the full 6-stage sequence end-to-end with zero
   manual intervention. If a stage still prompts or hangs, fix the specific
   flag/tool list causing it (most likely culprit: a tool stage needs that
   isn't in its `tools` allow-list) rather than reverting to manual prompting.
4. Inspect all produced artifacts under `context/bugs/001/`
   (`research/codebase-research.md`, `research/verified-research.md`,
   `implementation-plan.md`, `fix-summary.md`, `security-report.md`,
   `test-report.md`) for completeness against each agent's required sections.
5. `npm test` again — confirm all original tests plus the newly generated
   tests pass, and that the 3 seeded issues are now actually fixed (re-run the
   manual repro commands from step 2 and confirm the symptoms are gone,
   including a safe non-destructive command-injection check like a harmless
   payload that would have echoed extra output under the old code).
6. Capture real screenshots into `docs/screenshots/`: pipeline run in
   progress/complete, the code diff from the fix, the security report, `npm
   test` passing pre- and post-fix.
7. Write `homework-4/README.md` (overview, agent/model table + justification,
   skills used, author info) and `homework-4/HOWTORUN.md` (run app, run tests,
   run pipeline, prerequisites — Node + authenticated `claude` CLI).

## Documentation

Copy this plan into `homework-4/PLAN.md` (verbatim, as the design record for
the submission) once work starts, and keep it in the repo alongside the other
deliverables.

## Files to create

```
homework-4/
├── README.md, HOWTORUN.md, PLAN.md
├── package.json
├── agents/{research-verifier,bug-fixer,security-verifier,unit-test-generator}.agent.md
├── skills/{research-quality-measurement,unit-tests-FIRST}.md
├── scripts/run-pipeline.js
├── src/{index.js,bookmarks.js}
├── tests/bookmarks.test.js
├── data/.gitkeep
├── context/bugs/001/bug-context.md  (+ pipeline-generated artifacts after step 3)
└── docs/screenshots/  (pipeline-run-transcript.txt + .png screenshots)
```

## Post-plan deviation: model swap for helper stages

During execution, the Bug Researcher and Bug Planner helper stages (originally
`claude-sonnet-4-6` per this plan) failed with "Usage credits are required for
long context requests" — an account-level billing limitation tied to that
model's long-context handling, not a bug in the orchestrator. Both stages were
switched to `claude-haiku-4-5-20251001`, which ran successfully with no other
changes required. See `README.md` for the final model table.
