# How to Run

## 1. Install dependencies

```bash
cd homework-6
pip install -r requirements.txt
```

## 2. (Optional) Install the real git pre-push hook

`.git/hooks/` is not tracked by git, so the coverage gate must be installed manually once per clone:

```bash
cp scripts/pre-push ../.git/hooks/pre-push   # run from inside homework-6/
chmod +x ../.git/hooks/pre-push
```

## 3. Run the pipeline

```bash
python integrator.py
```

This processes all 8 transactions in `sample-transactions.json` and writes results to `shared/results/`, including `summary.json` and `pipeline.log`.

## 4. Run the validator in dry-run mode (no pipeline side effects)

```bash
python agents/transaction_validator.py --dry-run
```

## 5. Run the tests and check coverage

```bash
python -m pytest --cov=agents --cov=integrator --cov-report=term-missing
```

Coverage must stay ≥ 80% (gate) — current coverage is ~90%.

## 6. Use the Claude Code skills

Inside Claude Code, with this folder open:
- `/run-pipeline` — runs the full pipeline and summarizes results.
- `/validate-transactions` — validates without processing.
- `/write-spec` — regenerates `specification.md` from the template.

## 7. Try the coverage-gate hook

```bash
git add -A
git commit -m "demo"
git push   # the pre-push hook (and the Claude Code PreToolUse hook, if pushing via Claude) runs scripts/check_coverage.sh and blocks the push if coverage < 80%
```

## 8. Configure and use the MCP servers

1. Point your MCP-aware client (Claude Code) at `mcp.json` in this folder.
2. Query `context7` for any library documentation (e.g. "fastmcp resource decorator").
3. Call the custom `pipeline-status` server's tools:
   - `get_transaction_status(transaction_id="TXN002")`
   - `list_pipeline_results()`
   - Read the `pipeline://summary` resource.

(You can also test the MCP server directly without a host, using `fastmcp`'s in-process `Client` against `mcp/server.py`'s `mcp` object.)
