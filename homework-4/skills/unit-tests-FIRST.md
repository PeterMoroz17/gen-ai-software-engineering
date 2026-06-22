---
name: unit-tests-FIRST
description: Defines the FIRST principles (Fast, Independent, Repeatable, Self-validating, Timely) that all generated unit tests must satisfy.
---

# Skill: FIRST Unit Tests

Every test you generate must satisfy all five FIRST properties. Check each one
explicitly before finalizing a test file.

- **Fast** — a test runs in milliseconds. No real network calls, no real timers/
  `sleep`, no real filesystem unless the unit under test is the filesystem layer
  itself (and then use a temp directory, not the project's real `data/` file).
- **Independent** — a test does not depend on the order it runs in or on state
  left behind by another test. Build fresh input data (e.g. a new array/object)
  inside the test or in a `beforeEach`, never reuse/mutate shared module-level state.
- **Repeatable** — running the same test twice, locally or in CI, on any machine,
  produces the same result. No reliance on current date/time, random values without
  a fixed seed, or external services.
- **Self-validating** — the test itself reports pass/fail via assertions
  (`assert.equal`, `assert.throws`, etc.). No tests that just print output for a
  human to eyeball.
- **Timely** — the test is written close to the code change it covers (i.e. now,
  as part of this fix), targeting the new/changed behavior, not unrelated legacy code.

## Required output when applying this skill

For the test file(s) you generate, briefly confirm in `test-report.md` how each
FIRST property is satisfied (one short bullet per property is enough), then list
the actual test cases and the real `npm test` run result.
