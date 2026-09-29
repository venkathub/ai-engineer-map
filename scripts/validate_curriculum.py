#!/usr/bin/env python3
"""Validate curriculum completeness, references, and dependency structure."""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys
from urllib.parse import urlparse

ROOT = pathlib.Path(__file__).resolve().parents[1]
CURRICULUM = ROOT / "curriculum" / "concepts.json"
HOE_CATALOG = ROOT / "curriculum" / "hoe.json"
REQUIRED = {"id", "title", "track", "order", "level", "minutes", "summary", "prerequisites", "outcomes", "exercise"}
MODERN_CORE = {
    "transformers", "reasoning-models", "rag-quality", "mcp", "mcp-tasks", "a2a",
    "agent-skills-hooks", "realtime-voice", "agent-evals", "system-tevv",
    "prompt-injection", "agentic-security", "content-provenance", "ai-regulation",
    "training-pipelines", "model-registry", "synthetic-data", "reinforcement-learning",
    "peft", "quantization", "speculative-decoding", "edge-inference",
    "tracing-observability", "performance-benchmarking", "capstone",
}
REQUIRED_TRACKS = {
    "foundations", "ml", "models", "context", "rag", "agents", "multimodal",
    "evals", "safety", "dataops", "applied", "production",
}
EXERCISE_VERBS = {
    "add", "audit", "benchmark", "build", "classify", "compare", "configure",
    "containerize", "create", "define", "design", "evaluate", "extract", "generate",
    "implement", "measure", "model", "package", "prototype", "reduce", "review",
    "rewrite", "run", "secure", "specify", "storyboard", "threat-model", "train",
    "turn", "visualize", "write",
}
HOE_MODES = {"browser", "local", "byo-api", "gpu"}
HOE_STATUSES = {"guided", "automated", "setup-ready"}
HOE_RUNNERS = {"guided", "command", "manual"}
HOE_PROFILE_REQUIRED = {
    "mode", "status", "runner", "estimatedMinutes", "estimatedCost",
    "requirements", "setup", "run", "verify", "artifacts", "cleanup",
    "provider", "gpuBackend",
}
BANNED_COMMAND_EXECUTABLES = {"bash", "cmd", "fish", "powershell", "pwsh", "sh", "zsh"}


def validate_hoe_catalog(known: set[str]) -> list[str]:
    errors: list[str] = []
    try:
        catalog = json.loads(HOE_CATALOG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"cannot read HOE catalog: {error}"]
    if catalog.get("schemaVersion") != 1:
        errors.append("HOE schemaVersion must be 1")
    profiles = catalog.get("profiles", {})
    topics = catalog.get("topics", {})
    if not isinstance(profiles, dict) or not profiles:
        return errors + ["HOE profiles must be a non-empty object"]
    if not isinstance(topics, dict):
        return errors + ["HOE topics must be an object"]

    assigned = set(topics)
    if missing := sorted(known - assigned):
        errors.append(f"HOE topics missing concept assignments: {missing}")
    if extra := sorted(assigned - known):
        errors.append(f"HOE topics contain unknown concepts: {extra}")
    for topic_id, profile_id in topics.items():
        if profile_id not in profiles:
            errors.append(f"{topic_id}: unknown HOE profile {profile_id}")

    for profile_id, profile in profiles.items():
        if not isinstance(profile, dict):
            errors.append(f"{profile_id}: HOE profile must be an object")
            continue
        missing_fields = sorted(HOE_PROFILE_REQUIRED - set(profile))
        if missing_fields:
            errors.append(f"{profile_id}: missing HOE fields {missing_fields}")
            continue
        if profile["mode"] not in HOE_MODES:
            errors.append(f"{profile_id}: invalid HOE mode")
        if profile["status"] not in HOE_STATUSES:
            errors.append(f"{profile_id}: invalid HOE status")
        if profile["runner"] not in HOE_RUNNERS:
            errors.append(f"{profile_id}: invalid HOE runner")
        if not isinstance(profile["estimatedMinutes"], int) or profile["estimatedMinutes"] < 1:
            errors.append(f"{profile_id}: estimatedMinutes must be a positive integer")
        if not profile["estimatedCost"] or not profile["artifacts"]:
            errors.append(f"{profile_id}: cost and artifacts are required")
        for command_name in ("setup", "run", "verify"):
            command = profile[command_name]
            if command is not None and (
                not isinstance(command, list)
                or not command
                or not all(isinstance(part, str) and part for part in command)
            ):
                errors.append(f"{profile_id}: {command_name} must be null or a non-empty argv list")
            elif command and pathlib.Path(command[0]).name.lower() in BANNED_COMMAND_EXECUTABLES:
                errors.append(f"{profile_id}: {command_name} cannot invoke a shell")
        if profile["status"] == "automated" and (profile["runner"] != "command" or not profile["run"] or not profile["verify"]):
            errors.append(f"{profile_id}: automated profiles need command run and verify argv")
        if profile["mode"] in {"byo-api", "gpu"} and profile["status"] == "automated":
            errors.append(f"{profile_id}: external-cost profiles cannot be implicitly automated")
    return errors


def validate() -> list[str]:
    errors: list[str] = []
    data = json.loads(CURRICULUM.read_text(encoding="utf-8"))
    tracks = {item["id"]: item for item in data.get("tracks", [])}
    references = data.get("references", {})
    concepts = data.get("concepts", [])
    ids = [item.get("id") for item in concepts]
    known = set(ids)

    if data.get("schemaVersion") != 2:
        errors.append("schemaVersion must be 2")
    try:
        reviewed = dt.date.fromisoformat(data["reviewedAt"])
        if (dt.date.today() - reviewed).days > 365:
            errors.append("curriculum review is more than one year old")
    except (KeyError, ValueError):
        errors.append("reviewedAt must be an ISO date")
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    if duplicates:
        errors.append(f"duplicate concept ids: {duplicates}")
    framework = data.get("exerciseFramework", {})
    if set(framework) != {"inspect", "modify", "build"} or not all(framework.values()):
        errors.append("exerciseFramework must define inspect, modify, and build")
    if len(tracks) < 12 or len(concepts) < 100:
        errors.append("coverage floor is 12 tracks and 100 concepts")
    missing_tracks = sorted(REQUIRED_TRACKS - set(tracks))
    if missing_tracks:
        errors.append(f"missing role-coverage tracks: {missing_tracks}")
    missing_core = sorted(MODERN_CORE - known)
    if missing_core:
        errors.append(f"missing modern core topics: {missing_core}")

    for ref_id, ref in references.items():
        if not ref.get("title") or urlparse(ref.get("url", "")).scheme != "https":
            errors.append(f"invalid reference: {ref_id}")
    for track_id, item in tracks.items():
        if not item.get("refs"):
            errors.append(f"{track_id}: track needs primary references")
        for ref_id in item.get("refs", []):
            if ref_id not in references:
                errors.append(f"{track_id}: unknown reference {ref_id}")
        if sum(concept.get("track") == track_id for concept in concepts) < 6:
            errors.append(f"{track_id}: track needs at least six concepts")

    orders: set[tuple[str, int]] = set()
    graph: dict[str, list[str]] = {}
    for index, item in enumerate(concepts):
        label = item.get("id", f"index-{index}")
        missing = REQUIRED - item.keys()
        if missing:
            errors.append(f"{label}: missing {sorted(missing)}")
            continue
        if item["track"] not in tracks:
            errors.append(f"{label}: unknown track {item['track']}")
        pair = (item["track"], item["order"])
        if pair in orders:
            errors.append(f"{label}: duplicate order {pair}")
        orders.add(pair)
        if not isinstance(item["minutes"], int) or item["minutes"] <= 0:
            errors.append(f"{label}: minutes must be positive")
        if len(item["outcomes"]) < 2 or not item["exercise"].strip():
            errors.append(f"{label}: needs two outcomes and an exercise")
        verb = item["exercise"].split()[0].lower().strip(".,:")
        if verb not in EXERCISE_VERBS:
            errors.append(f"{label}: exercise must begin with an observable action verb")
        for ref_id in item.get("refs", []):
            if ref_id not in references:
                errors.append(f"{label}: unknown topic reference {ref_id}")
        unknown = sorted(set(item["prerequisites"]) - known)
        if unknown:
            errors.append(f"{label}: unknown prerequisites {unknown}")
        if label in item["prerequisites"]:
            errors.append(f"{label}: cannot require itself")
        graph[label] = item["prerequisites"]

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            errors.append(f"dependency cycle at {node}")
            return
        if node in visited:
            return
        visiting.add(node)
        for parent in graph.get(node, []):
            visit(parent)
        visiting.remove(node)
        visited.add(node)

    for concept_id in graph:
        visit(concept_id)
    if len({item["exercise"] for item in concepts}) != len(concepts):
        errors.append("every concept must have a unique hands-on exercise")
    errors.extend(validate_hoe_catalog(known))
    for track_id in tracks:
        actual = sorted(item["order"] for item in concepts if item["track"] == track_id)
        if actual != list(range(1, len(actual) + 1)):
            errors.append(f"{track_id}: concept order must be contiguous from 1")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("Curriculum validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    data = json.loads(CURRICULUM.read_text(encoding="utf-8"))
    print(f"Curriculum validation passed: {len(data['concepts'])} concepts across {len(data['tracks'])} tracks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
