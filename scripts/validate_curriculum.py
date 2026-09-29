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
MODERN_CORE = {"transformers", "rag-quality", "mcp", "a2a", "realtime-voice", "agent-evals", "prompt-injection", "peft", "quantization", "tracing-observability", "capstone"}


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
    if len(tracks) < 10 or len(concepts) < 70:
        errors.append("coverage floor is 10 tracks and 70 concepts")
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
