"""Custom FastMCP server exposing the banking pipeline's results as MCP tools/resources.

Tools:
  - get_transaction_status(transaction_id): current status of one transaction
  - list_pipeline_results(): summary of all processed transactions

Resource:
  - pipeline://summary: latest pipeline run summary as text
"""
from __future__ import annotations

import json
from pathlib import Path

from fastmcp import FastMCP

BASE_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = BASE_DIR / "shared" / "results"

mcp = FastMCP(name="pipeline-status")


def _load_result(transaction_id: str) -> dict | None:
    path = RESULTS_DIR / f"{transaction_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _load_all_results() -> list[dict]:
    results = []
    if not RESULTS_DIR.exists():
        return results
    for path in sorted(RESULTS_DIR.glob("*.json")):
        if path.name == "summary.json":
            continue
        results.append(json.loads(path.read_text(encoding="utf-8")))
    return results


@mcp.tool
def get_transaction_status(transaction_id: str) -> dict:
    """Return the current status/disposition of a transaction from shared/results/."""
    result = _load_result(transaction_id)
    if result is None:
        return {"transaction_id": transaction_id, "found": False, "status": "unknown"}
    return {"found": True, **result}


@mcp.tool
def list_pipeline_results() -> dict:
    """Return a summary of all processed transactions: counts by status and the full list."""
    results = _load_all_results()
    counts: dict[str, int] = {}
    for result in results:
        counts[result["status"]] = counts.get(result["status"], 0) + 1
    return {"total": len(results), "counts": counts, "transactions": results}


@mcp.resource("pipeline://summary")
def pipeline_summary() -> str:
    """Return the latest pipeline run summary as text."""
    summary_path = RESULTS_DIR / "summary.json"
    if not summary_path.exists():
        return "No pipeline run found yet. Run `python integrator.py` first."
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    lines = [
        f"Pipeline run summary (generated_at: {summary.get('generated_at')})",
        f"Total transactions: {summary.get('total')}",
    ]
    for status, count in summary.get("counts", {}).items():
        lines.append(f"  {status}: {count}")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
