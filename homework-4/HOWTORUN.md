# How to Run

## Prerequisites

- Node.js (no npm dependencies are required — this app and pipeline are
  zero-dependency).
- The `claude` CLI installed and authenticated on your machine (the pipeline
  shells out to it once per stage). Verify with:
  ```bash
  claude --version
  ```

## 1. Install

```bash
cd gen-ai-software-engineering/homework-4
npm install   # no-op, no dependencies, but keeps the workflow standard
```

## 2. Run the sample app directly

```bash
node src/index.js add https://example.com "Example"
node src/index.js list
node src/index.js remove 1
node src/index.js check https://example.com
```

## 3. Run the tests

```bash
npm test
```

## 4. Run the full 4-agent pipeline (single command)

```bash
npm run pipeline
```

This runs all 6 stages (Bug Researcher → Research Verifier → Bug Planner →
Bug Fixer → Security Verifier → Unit Test Generator) end-to-end with **no
manual intervention** — each stage shells out to `claude -p` in headless mode
with `--permission-mode bypassPermissions`. Output is logged to the console
and also saved to `docs/screenshots/pipeline-run-transcript.txt`. The script
exits non-zero immediately if any stage fails or fails to produce its
expected output file.

All generated artifacts land under `context/bugs/001/`:
- `research/codebase-research.md`
- `research/verified-research.md`
- `implementation-plan.md`
- `fix-summary.md`
- `security-report.md`
- `test-report.md`

## 5. Verify the fixes

After the pipeline runs, re-run:

```bash
npm test
```

You should see 8/8 tests pass (3 original + 5 new tests added by the Unit
Test Generator stage). You can also manually re-run the app commands from
step 2 to confirm pagination, removal, and the command-injection guard now
behave correctly.
