#!/usr/bin/env bash
# Grade your own work, locally, before you push.
#
#   ./grade.sh              everything
#   ./grade.sh 1            just day 1
#   ./grade.sh capstone     just the capstone
#   ./grade.sh --rubric     what every task is worth
#   ./grade.sh --solutions  instructor: check the rubric against solutions/
#
# Windows without bash? Run the equivalent directly:
#   python -m pytest tests/test_day1.py
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

# Absolute, because --solutions runs pytest from a temp directory.
if [ -x "$ROOT/.venv/bin/python" ]; then
  PY="$ROOT/.venv/bin/python"
elif [ -x "$ROOT/.venv/Scripts/python.exe" ]; then
  PY="$ROOT/.venv/Scripts/python.exe"
else
  PY="$(command -v python3 || command -v python)"
fi

if ! "$PY" -c "import pytest" 2>/dev/null; then
  echo "pytest is not installed. Run:  $PY -m pip install -r requirements.txt" >&2
  exit 1
fi

case "${1:-all}" in
  --rubric)   exec "$PY" -m pytest tests --collect-only --grade-rubric -q ;;
  --solutions)
    # Copy the reference solutions over the stubs in a throwaway directory and
    # confirm every graded task passes. Run this after editing any test.
    [ -d solutions ] || { echo "solutions/ not found -- this is instructor-only." >&2; exit 1; }
    WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
    tar -c --exclude=.git --exclude=.venv --exclude=__pycache__ --exclude=.pytest_cache . \
      | tar -x -C "$WORK"
    cp solutions/*.py "$WORK/submissions/"
    [ -f solutions/Capstone-README.md ] && cp solutions/Capstone-README.md "$WORK/Capstone/README.md"
    cd "$WORK" && exec "$PY" -m pytest tests -m "not engagement" "${@:2}"
    ;;
  all)        TARGET="tests" ;;
  capstone)   TARGET="tests/test_capstone.py" ;;
  1|2|3)      TARGET="tests/test_day$1.py" ;;
  -*)         TARGET="tests" ;;   # a bare pytest flag: grade everything with it
  *)          echo "usage: ./grade.sh [1|2|3|capstone|all|--rubric|--solutions] [pytest args]" >&2
              exit 2 ;;
esac

# Anything after the day is handed straight to pytest, e.g. `./grade.sh 1 -x`.
if [ $# -gt 0 ] && [ "${1:0:1}" != "-" ]; then
  shift
fi

exec "$PY" -m pytest "$TARGET" "$@"
