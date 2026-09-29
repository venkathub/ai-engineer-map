#!/usr/bin/env python3
"""Validate the machine-readable AI contributor and BYO exercise contract."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_PHASES = ["discover", "specify", "implement", "verify", "deliver"]
REQUIRED_FILES = [
    "AGENTS.md",
    ".ai/README.md",
    ".ai/BRANCHING.md",
    ".ai/PHASES.md",
    ".ai/templates/IMPLEMENTATION_PLAN.md",
    ".env.example",
    "docs/BYO_LLM_AND_GPU.md",
    "curriculum/hoe.json",
    "curriculum/hoe.schema.json",
]
SECRET_VARIABLES = {
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "OPENROUTER_API_KEY",
    "LLM_API_KEY",
    "JL_API_KEY",
}


def validate() -> list[str]:
    errors: list[str] = []
    for relative in REQUIRED_FILES:
        if not (ROOT / relative).is_file():
            errors.append(f"missing required AI kit file: {relative}")

    config_path = ROOT / ".ai" / "config.json"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"cannot read .ai/config.json: {error}"]

    if config.get("phases") != REQUIRED_PHASES:
        errors.append(f"phases must be exactly {REQUIRED_PHASES}")
    if config.get("protectedBranch") != "main":
        errors.append("protectedBranch must be main")
    if config.get("requiredCheck") != "curriculum-and-labs":
        errors.append("requiredCheck must match the GitHub Actions job")
    for field in ("branchPattern", "commitPattern"):
        try:
            re.compile(config.get(field, ""))
        except re.error as error:
            errors.append(f"invalid {field}: {error}")

    env_text = (ROOT / ".env.example").read_text(encoding="utf-8")
    present = {line.split("=", 1)[0].strip() for line in env_text.splitlines() if "=" in line}
    missing_variables = sorted(SECRET_VARIABLES - present)
    if missing_variables:
        errors.append(f".env.example is missing: {', '.join(missing_variables)}")

    ignore_text = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    if ".env" not in ignore_text:
        errors.append(".gitignore must ignore .env")
    if ".ai/work/" not in ignore_text:
        errors.append(".gitignore must ignore phase working state")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"AI kit validation failed: {error}", file=sys.stderr)
        return 1
    print("AI kit validation passed: five phases and BYO secret contract are present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
