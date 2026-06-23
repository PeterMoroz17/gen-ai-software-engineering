# Research Notes

This file documents the technical research performed while building the pipeline (Agent 2 / Task 2) and the custom MCP server (Task 4), using the `context7` MCP server configured in `mcp.json`. Both queries below were run live through context7 (not web search) once the MCP server was connected in Claude Code, and their results were applied directly to the code in `agents/` and `mcp/server.py`.

## Query 1: Decimal/monetary arithmetic for Python

- **Search**: "Python decimal module ROUND_HALF_UP monetary arithmetic best practice, constructing Decimal from string vs float"
- **context7 library ID**: `/python/cpython` (resolved via `resolve-library-id` with `libraryName: "Python decimal"`)
- **Key result returned**: `Decimal.from_float(0.1)` yields `Decimal('0.1000000000000000055511151231257827021181583404541015625')` — confirming float inputs carry binary-representation noise — versus constructing directly from a string literal (`Decimal('8')`, `Decimal('0.70')`), which is exact. The docs also showed `round(Decimal('0.70') * Decimal('1.05'), 2)` giving the correct `Decimal('0.74')` versus the equivalent float expression giving the wrong `0.73`.
- **Applied**: Confirmed and reinforced the existing design decision in `agents/transaction_validator.py:validate_transaction` and `agents/fraud_detector.py:compute_risk_score` to always construct via `Decimal(str(amount))`, never from a float or by accepting a float input directly. This is exactly the failure mode the docs demonstrate (`0.73` vs `0.74`), which would silently corrupt fraud-threshold comparisons (e.g. an amount sitting right at the $10,000 boundary) if floats were used instead.

## Query 2: FastMCP tool/resource decorator syntax

- **Search**: "@mcp.tool and @mcp.resource decorator syntax, defining a resource with a custom URI scheme"
- **context7 library ID**: `/prefecthq/fastmcp` (resolved via `resolve-library-id` with `libraryName: "FastMCP"`; note this is the correct current ID — an earlier draft of these notes guessed `/jlowin/fastmcp`, which context7 did not return)
- **Key result returned**: `@mcp.resource("resource://greeting")` / `@mcp.resource("data://config")` examples confirming resources are declared with an arbitrary custom URI scheme (`scheme://path`), and that the decorated function's return value (string or JSON-serialized string) becomes the resource content. Also confirmed the `@resource` decorator's full argument set (`uri`, `name`, `description`, `mime_type`, `tags`, `annotations`, etc.).
- **Applied**: Validated that `mcp/server.py`'s `@mcp.resource("pipeline://summary")` declaration uses exactly this pattern — a custom `pipeline://` scheme is just as valid as the docs' `resource://` / `data://` examples — and that returning a plain formatted string from `pipeline_summary()` is the correct, idiomatic way to expose the latest run summary as a resource.

## Live verification (custom `pipeline-status` MCP server)

Once both servers were connected via `.mcp.json`, the custom server was exercised directly against real pipeline output (from a fresh `python integrator.py` run):
- `get_transaction_status(transaction_id="TXN002")` → `{"found": true, "status": "flagged_for_review", "risk_score": 50, "reason": "risk_score 50 >= threshold", ...}`
- `list_pipeline_results()` → `{"total": 8, "counts": {"cleared": 5, "flagged_for_review": 2, "rejected": 1}, "transactions": [...]}`

Both matched `shared/results/TXN002.json` and `shared/results/summary.json` exactly, confirming the MCP server reads live pipeline state correctly.
