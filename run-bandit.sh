#!/bin/bash
# Bandit security scan wrapper
# Excludes test, audit, and non-production directories
# Usage: ./run-bandit.sh [OPTIONS]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Run bandit with proper exclusions
python -m bandit -r "$SCRIPT_DIR" \
    -x "./tests,./htmlcov,./__pycache__,./.venv,./scripts/stability-audit,./research,./icon-generator,./frontend" \
    "$@"

# Exit with bandit's exit code
exit $?
