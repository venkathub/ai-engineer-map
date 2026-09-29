#!/usr/bin/env sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_DIR"

echo "[1/4] Validating curriculum"
python3 scripts/validate_curriculum.py

echo "[2/4] Validating AI contributor kit"
python3 scripts/validate_ai_kit.py

echo "[3/4] Running unit tests"
python3 -m unittest discover -s tests -v

echo "[4/4] Checking patch whitespace"
if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git diff --check
else
  echo "Git checkout not detected; skipped."
fi

echo "All checks passed."
