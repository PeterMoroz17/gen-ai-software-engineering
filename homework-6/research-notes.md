# Research Notes

This file documents the technical research performed while building the pipeline (Agent 2 / Task 2) and the custom MCP server (Task 4). `mcp.json` configures the `context7` MCP server for use inside Claude Code; the two lookups below were performed during active development and their results were applied directly to the code in `agents/` and `mcp/server.py`.

## Query 1: Decimal/monetary arithmetic for Python

- **Search**: "Python decimal module ROUND_HALF_UP best practice monetary arithmetic"
- **context7 library ID**: `/python/cpython` (decimal module docs)
- **Applied**: Confirmed `Decimal` must always be constructed from a `str` (`Decimal(str(amount))`), never from a `float`, to avoid binary floating-point precision errors — this is exactly what `agents/transaction_validator.py:validate_transaction` and `agents/fraud_detector.py:compute_risk_score` do. Also confirmed `quantize()` with an explicit `rounding=ROUND_HALF_UP` is the correct pattern for any future cents-level rounding (e.g. settlement math); not currently needed since this pipeline only compares/sums amounts and never rounds, but the convention is recorded here for the next agent extension.

## Query 2: FastMCP tool/resource decorator syntax

- **Search**: "fastmcp python @mcp.tool @mcp.resource decorator syntax example"
- **context7 library ID**: `/jlowin/fastmcp`
- **Applied**: Confirmed the current (v3.x) decorator syntax is `@mcp.tool` (no parens needed for the simple case) for tools and `@mcp.resource("scheme://path")` for resources, with FastMCP deriving the JSON schema from type hints/docstrings automatically. Used directly in `mcp/server.py` for `get_transaction_status`, `list_pipeline_results`, and the `pipeline://summary` resource, and confirmed `mcp.run()` is the correct entrypoint for stdio transport (matching the `mcp.json` `command`/`args` configuration).
