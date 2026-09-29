#!/usr/bin/env python3
"""Inspect and run versioned hands-on exercises without implicit paid actions."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
from typing import Callable


ROOT = Path(__file__).resolve().parents[1]
CURRICULUM_PATH = ROOT / "curriculum" / "concepts.json"
CATALOG_PATH = ROOT / "curriculum" / "hoe.json"
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
    which: Callable[[str], str | None] = shutil.which,
) -> dict[str, object]:
    missing = [name for name in PROVIDERS[provider] if not environ.get(name, "").strip()]
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


def _jl_json(
    arguments: list[str],
    environ: dict[str, str],
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> object:
    result = runner(
        ["jl", *arguments, "--json"],
        env=environ,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout or f"exit {result.returncode}").strip()
        for name, value in environ.items():
            if (name.endswith("_API_KEY") or name.endswith("_TOKEN")) and value:
                detail = detail.replace(value, "[redacted]")
        raise RuntimeError(detail[:300])
    return json.loads(result.stdout)


def jarvislabs_live_report(
    environ: dict[str, str],
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, object]:
    """Query read-only account state and availability without exposing secrets."""
    configured_gpu = environ.get("JARVISLABS_GPU", "L4").strip() or "L4"
    configured_region = environ.get("JARVISLABS_REGION", "IN2").strip() or "IN2"
    configured_workload = environ.get("JARVISLABS_WORKLOAD", "container").strip() or "container"
    try:
        storage_gb = int(environ.get("JARVISLABS_STORAGE_GB", "100"))
    except ValueError:
        storage_gb = 0
    try:
        status = _jl_json(["status"], environ, runner)
        instances = _jl_json(["list"], environ, runner)
        offers = _jl_json(["gpus"], environ, runner)
    except (RuntimeError, json.JSONDecodeError) as error:
        return {
            "authenticated": False,
            "configured_gpu_available": False,
            "error": str(error),
        }
    if not isinstance(status, dict) or not isinstance(instances, list) or not isinstance(offers, list):
        return {
            "authenticated": True,
            "configured_gpu_available": False,
            "error": "JarvisLabs returned an unexpected JSON shape",
        }
    matching = [
        offer for offer in offers
        if offer.get("gpu_type") == configured_gpu
        and offer.get("region") == configured_region
        and offer.get("workload_type") == configured_workload
    ]
    safe_offers = [
        {
            "gpu_type": offer.get("gpu_type"),
            "region": offer.get("region"),
            "workload_type": offer.get("workload_type"),
            "vram_gb": offer.get("vram"),
            "free_devices": offer.get("num_free_devices"),
            "price_per_hour": offer.get("price_per_hour"),
            "spot_price": offer.get("spot_price"),
        }
        for offer in matching
    ]
    running = [item for item in instances if str(item.get("status", "")).lower() == "running"]
    balance = status.get("balance", {})
    amount = balance.get("balance", 0) if isinstance(balance, dict) else 0
    return {
        "authenticated": True,
        "configured": {
            "gpu": configured_gpu,
            "region": configured_region,
            "workload": configured_workload,
            "storage_gb": storage_gb,
        },
        "account_funded": isinstance(amount, (int, float)) and amount > 0,
        "currency": status.get("currency"),
        "resources": status.get("resources", {}),
        "instance_count": len(instances),
        "running_instance_count": len(running),
        "matching_offers": safe_offers,
        "configured_gpu_available": any((offer.get("num_free_devices") or 0) > 0 for offer in matching),
        "remote_environment_check": (
            "available-but-not-executed" if running else "not-checked-no-running-instance"
        ),
        "action": "read-only API audit; no instance was created, resumed, resized, paused, or destroyed",
    }


def render_configuration(report: dict[str, object]) -> str:
    lines = ["HOE configuration check"]
    for section_name in ("provider", "gpu"):
        section = report[section_name]
        assert isinstance(section, dict)
        state = "ready" if section["configured"] else "needs configuration"
        lines.append(f"- {section_name}: {section['name']} ({state})")
        if section.get("missing"):
            lines.append(f"  missing: {', '.join(str(item) for item in section['missing'])}")
        for note in section.get("notes", []):
            lines.append(f"  note: {note}")
    lines.append(f"- {report['action']}")
    live = report.get("jarvislabs_live")
    if isinstance(live, dict):
        lines.append("- JarvisLabs live audit:")
        lines.append(f"  authenticated: {live.get('authenticated', False)}")
        configured = live.get("configured", {})
        if isinstance(configured, dict):
            lines.append(
                "  target: "
                f"{configured.get('gpu')} / {configured.get('region')} / {configured.get('workload')} / "
                f"{configured.get('storage_gb')} GB"
            )
        lines.append(f"  funded: {live.get('account_funded', False)}")
        lines.append(f"  target available: {live.get('configured_gpu_available', False)}")
        lines.append(f"  instances: {live.get('instance_count', 0)} total, {live.get('running_instance_count', 0)} running")
        lines.append(f"  remote environment: {live.get('remote_environment_check', 'not checked')}")
        if live.get("error"):
            lines.append(f"  error: {live['error']}")
        lines.append(f"  {live.get('action', 'read-only audit failed')}")
    return "\n".join(lines)


def load_catalog() -> tuple[dict[str, dict[str, object]], dict[str, object]]:
    curriculum = json.loads(CURRICULUM_PATH.read_text(encoding="utf-8"))
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    concepts = {item["id"]: item for item in curriculum["concepts"]}
    return concepts, catalog


def resolve_topic(topic_id: str) -> dict[str, object]:
    concepts, catalog = load_catalog()
    if topic_id not in concepts:
        raise KeyError(f"unknown topic: {topic_id}")
    profile_id = catalog["topics"][topic_id]
    profile = dict(catalog["profiles"][profile_id])
    concept = concepts[topic_id]
    return {
        "id": topic_id,
        "title": concept["title"],
        "track": concept["track"],
        "exercise": concept["exercise"],
        "acceptance": concept["outcomes"],
        "profile": profile_id,
        **profile,
    }


def command_text(command: object) -> str:
    if not command:
        return "manual"
    assert isinstance(command, list)
    return shlex.join(str(part) for part in command)


def render_topic(topic: dict[str, object]) -> str:
    lines = [
        f"{topic['title']} ({topic['id']})",
        f"- track: {topic['track']}",
        f"- profile: {topic['profile']} / {topic['mode']} / {topic['status']}",
        f"- time: about {topic['estimatedMinutes']} minutes",
        f"- cost: {topic['estimatedCost']}",
        f"- exercise: {topic['exercise']}",
        f"- setup: {command_text(topic.get('setup'))}",
        f"- run: {command_text(topic.get('run'))}",
        f"- verify: {command_text(topic.get('verify'))}",
        "- acceptance:",
    ]
    lines.extend(f"  - {item}" for item in topic["acceptance"])
    lines.append("- artifacts:")
    lines.extend(f"  - {item}" for item in topic["artifacts"])
    if topic["cleanup"]:
        lines.append("- cleanup:")
        lines.extend(f"  - {item}" for item in topic["cleanup"])
    if topic["status"] != "automated":
        lines.append("- automation: not yet automated; follow the guided or setup-ready instructions")
    return "\n".join(lines)


def list_topics(mode: str | None, status: str | None) -> int:
    concepts, catalog = load_catalog()
    rows = []
    for topic_id, concept in concepts.items():
        profile_id = catalog["topics"][topic_id]
        profile = catalog["profiles"][profile_id]
        if mode and profile["mode"] != mode:
            continue
        if status and profile["status"] != status:
            continue
        rows.append((topic_id, concept["track"], profile["mode"], profile["status"]))
    print(f"{'TOPIC':<28} {'TRACK':<14} {'MODE':<9} STATUS")
    for row in rows:
        print(f"{row[0]:<28} {row[1]:<14} {row[2]:<9} {row[3]}")
    print(f"\n{len(rows)} topic(s)")
    return 0


def execute_topic(topic: dict[str, object], action: str, allow_billable: bool) -> int:
    mode = str(topic["mode"])
    command = topic.get(action)
    if mode in {"byo-api", "gpu"} and not allow_billable:
        print(render_topic(topic), flush=True)
        print("\nRefusing external-cost execution without --allow-billable.", file=sys.stderr)
        return 2
    if not command:
        print(render_topic(topic))
        if mode == "browser":
            print(f"\nOpen lab.html?id={topic['id']} to complete and record the evidence checklist.")
            return 0
        print(f"\n{action} is manual for this setup-ready profile; no command was executed.", file=sys.stderr)
        return 2
    assert isinstance(command, list)
    print(f"Executing: {command_text(command)}", flush=True)
    result = subprocess.run(command, cwd=ROOT, check=False)
    return result.returncode


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    subparsers = root.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser("check", help="validate provider/GPU configuration")
    check.add_argument("--provider", choices=PROVIDERS, default="none")
    check.add_argument("--gpu", choices=GPU_BACKENDS, default="none")
    check.add_argument("--env-file", type=Path, default=Path(".env"))
    check.add_argument("--json", action="store_true", dest="as_json")
    check.add_argument("--live", action="store_true", help="perform read-only JarvisLabs auth and availability queries")
    listing = subparsers.add_parser("list", help="list curriculum topics and execution modes")
    listing.add_argument("--mode", choices=("browser", "local", "byo-api", "gpu"))
    listing.add_argument("--status", choices=("guided", "automated", "setup-ready"))
    inspect = subparsers.add_parser("inspect", help="show the resolved execution contract")
    inspect.add_argument("topic")
    inspect.add_argument("--json", action="store_true", dest="as_json")
    for action in ("run", "verify"):
        action_parser = subparsers.add_parser(action, help=f"{action} a declared topic command")
        action_parser.add_argument("topic")
        action_parser.add_argument(
            "--allow-billable",
            action="store_true",
            help="acknowledge possible API/GPU cost; never provisions resources",
        )
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "check":
        environ: dict[str, str] = dict(os.environ)
        load_env(args.env_file, environ)
        report = configuration_report(args.provider, args.gpu, environ)
        if args.live:
            if args.gpu != "jarvislabs":
                print("--live currently requires --gpu jarvislabs", file=sys.stderr)
                return 2
            live = jarvislabs_live_report(environ)
            report["jarvislabs_live"] = live
            report["safe_to_start"] = bool(
                report["safe_to_start"]
                and live.get("authenticated")
                and live.get("account_funded")
                and live.get("configured_gpu_available")
            )
            report["action"] = "local configuration plus read-only JarvisLabs API audit completed"
        print(json.dumps(report, indent=2) if args.as_json else render_configuration(report))
        return 0 if report["safe_to_start"] else 1
    if args.command == "list":
        return list_topics(args.mode, args.status)
    try:
        topic = resolve_topic(args.topic)
    except KeyError as error:
        print(str(error), file=sys.stderr)
        return 2
    if args.command == "inspect":
        print(json.dumps(topic, indent=2) if args.as_json else render_topic(topic))
        return 0
    return execute_topic(topic, args.command, args.allow_billable)


if __name__ == "__main__":
    raise SystemExit(main())
