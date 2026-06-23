#!/usr/bin/env bash
# Coverage gate: fails (non-zero exit) if test coverage for agents/ + integrator.py
# drops below 80%. Used by both the Claude Code PreToolUse hook (.claude/settings.json)
# and the real git pre-push hook (.git/hooks/pre-push).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
THRESHOLD=95

cd "$PROJECT_DIR"

if command -v python >/dev/null 2>&1; then
  PYTHON=python
elif command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
else
  echo "check_coverage.sh: no python interpreter found on PATH" >&2
  exit 1
fi

echo "Running coverage gate (threshold: ${THRESHOLD}%)..."

set +e
"$PYTHON" -m pytest --cov=agents --cov=integrator --cov-report=term-missing \
    "--cov-fail-under=${THRESHOLD}" -q
STATUS=$?
set -e

if [ "$STATUS" -eq 0 ]; then
  echo "Coverage gate PASSED (>= ${THRESHOLD}%)."
else
  echo "Coverage gate FAILED: coverage is below ${THRESHOLD}%. Push blocked." >&2
fi
exit "$STATUS"
