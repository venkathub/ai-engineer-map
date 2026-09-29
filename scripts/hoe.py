#!/usr/bin/env python3
"""Validate optional hands-on exercise configuration without using credentials."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys


PROVIDERS = {
    "none": (),
    "openai": ("OPENAI_API_KEY", "OPENAI_MODEL"),
    "anthropic": ("ANTHROPIC_API_KEY", "ANTHROPIC_MODEL"),
    "gemini": ("GEMINI_API_KEY", "GEMINI_MODEL"),
    "openrouter": ("OPENROUTER_API_KEY", "OPENROUTER_MODEL"),
    "compatible": ("LLM_BASE_URL", "LLM_MODEL"),
}
GPU_BACKENDS = ("none", "local", "jarvislabs")


def load_env(path: Path, environ: dict[str, str] | None = None) -> dict[str, str]:
    """Load simple KEY=VALUE entries without replacing exported variables."""
    target = os.environ if environ is None else environ
    if not path.exists():
        return target
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or not key.replace("_", "").isalnum() or key[0].isdigit():
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        target.setdefault(key, value)
    return target


def configuration_report(
    provider: str,
    gpu: str,
    environ: dict[str, str],
    which=shutil.which,
) -> dict[str, object]:
    required = PROVIDERS[provider]
    missing = [name for name in required if not environ.get(name, "").strip()]
    provider_report: dict[str, object] = {
        "name": provider,
        "configured": not missing,
        "missing": missing,
    }

    gpu_missing: list[str] = []
    notes: list[str] = []
    if gpu == "local" and which("nvidia-smi") is None:
        gpu_missing.append("nvidia-smi")
    elif gpu == "jarvislabs":
        if which("jl") is None:
            gpu_missing.append("jl CLI")
        if not environ.get("JL_API_KEY", "").strip():
            notes.append("JL_API_KEY is absent; interactive authentication from `jl setup` may still be available.")
    gpu_report: dict[str, object] = {
        "name": gpu,
        "configured": not gpu_missing,
        "missing": gpu_missing,
        "notes": notes,
    }
    return {
        "provider": provider_report,
        "gpu": gpu_report,
        "safe_to_start": not missing and not gpu_missing,
        "action": "configuration check only; no API request or GPU provisioning occurred",
    }


def render_human(report: dict[str, object]) -> str:
    lines = ["HOE configuration check"]
    for section_name in ("provider", "gpu"):
        section = report[section_name]
        assert isinstance(section, dict)
        state = "ready" if section["configured"] else "needs configuration"
        lines.append(f"- {section_name}: {section['name']} ({state})")
        missing = section.get("missing", [])
        if missing:
            lines.append(f"  missing: {', '.join(str(item) for item in missing)}")
        for note in section.get("notes", []):
            lines.append(f"  note: {note}")
    lines.append(f"- {report['action']}")
    return "\n".join(lines)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    subparsers = root.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser("check", help="validate configuration without connecting")
    check.add_argument("--provider", choices=PROVIDERS, default="none")
    check.add_argument("--gpu", choices=GPU_BACKENDS, default="none")
    check.add_argument("--env-file", type=Path, default=Path(".env"))
    check.add_argument("--json", action="store_true", dest="as_json")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    environ: dict[str, str] = dict(os.environ)
    load_env(args.env_file, environ)
    report = configuration_report(args.provider, args.gpu, environ)
    if args.as_json:
        print(json.dumps(report, indent=2))
    else:
        print(render_human(report))
    return 0 if report["safe_to_start"] else 1


if __name__ == "__main__":
    sys.exit(main())
