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
