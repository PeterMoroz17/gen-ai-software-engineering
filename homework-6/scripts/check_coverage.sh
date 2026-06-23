#!/usr/bin/env bash
# Coverage gate: fails (non-zero exit) if test coverage for agents/ + integrator.py
# drops below 80%. Used by both the Claude Code PreToolUse hook (.claude/settings.json)
# and the real git pre-push hook (.git/hooks/pre-push).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
THRESHOLD=80

cd "$PROJECT_DIR"

# On some Windows setups, the first "python"/"python3" on PATH (e.g. an MSYS2 build)
# isn't the one with pytest installed. Probe candidates and pick the first that can
# actually import pytest, instead of assuming the first interpreter found is usable.
CANDIDATES=(
  python
  python3
  "$LOCALAPPDATA/Microsoft/WindowsApps/python.exe"
)

PYTHON=""
for candidate in "${CANDIDATES[@]}"; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c "import pytest" >/dev/null 2>&1; then
    PYTHON="$candidate"
    break
  fi
done

if [ -z "$PYTHON" ]; then
  echo "check_coverage.sh: no python interpreter with pytest installed found on PATH" >&2
  echo "  tried: ${CANDIDATES[*]}" >&2
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
