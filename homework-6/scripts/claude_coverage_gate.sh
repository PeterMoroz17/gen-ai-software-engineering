#!/usr/bin/env bash
# Claude Code PreToolUse hook for the Bash matcher. Receives the hook JSON payload on
# stdin (fields: tool_name, tool_input.command, ...). Only acts when tool_input.command
# contains "git push" -- the matching is done here, not via an "if" key in settings.json
# (no such filtering key exists in the PreToolUse hook schema), then runs
# scripts/check_coverage.sh and emits the permissionDecision JSON the hooks API expects.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if command -v python >/dev/null 2>&1; then
  PYTHON=python
else
  PYTHON=python3
fi

HOOK_INPUT="$(cat)"

COMMAND="$(printf '%s' "$HOOK_INPUT" | "$PYTHON" -c "
import json, sys
try:
    payload = json.load(sys.stdin)
except Exception:
    print('')
    sys.exit(0)
print(payload.get('tool_input', {}).get('command', ''))
")"

case "$COMMAND" in
  *"git push"*) ;;
  *) exit 0 ;;  # not a git push -- allow silently, no output
esac

if "$SCRIPT_DIR/check_coverage.sh" > /tmp/coverage_gate_output.txt 2>&1; then
  exit 0
fi

"$PYTHON" - <<'PY'
import json
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": "Coverage gate failed: test coverage is below 80%. Push blocked. See scripts/check_coverage.sh output for details.",
    }
}))
PY
exit 0
