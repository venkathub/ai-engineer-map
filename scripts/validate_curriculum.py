#!/usr/bin/env python3
"""Validate curriculum structure without third-party dependencies."""

from __future__ import annotations

import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
CURRICULUM = ROOT / "curriculum" / "concepts.json"
REQUIRED_FIELDS = {
    "id", "title", "track", "order", "level", "minutes", "status", "summary",
    "prerequisites", "outcomes", "lesson", "exercise", "next",
}


def validate() -> list[str]:
    errors: list[str] = []
    data = json.loads(CURRICULUM.read_text(encoding="utf-8"))
    tracks = {track["id"] for track in data.get("tracks", [])}
    concepts = data.get("concepts", [])
    ids = [concept.get("id") for concept in concepts]
    known_ids = set(ids)

    duplicates = sorted({concept_id for concept_id in ids if ids.count(concept_id) > 1})
    if duplicates:
        errors.append(f"duplicate concept ids: {', '.join(duplicates)}")

    for index, concept in enumerate(concepts):
        label = concept.get("id", f"index {index}")
        missing = REQUIRED_FIELDS - concept.keys()
        if missing:
            errors.append(f"{label}: missing fields {sorted(missing)}")
            continue
        if concept["track"] not in tracks:
            errors.append(f"{label}: unknown track {concept['track']}")
        if not isinstance(concept["minutes"], int) or concept["minutes"] <= 0:
            errors.append(f"{label}: minutes must be a positive integer")
        for relation in ("prerequisites", "next"):
            unknown = sorted(set(concept[relation]) - known_ids)
            if unknown:
                errors.append(f"{label}: unknown {relation} {unknown}")
        if label in concept["prerequisites"]:
            errors.append(f"{label}: concept cannot require itself")
        if concept["status"] == "published" and not concept["lesson"]:
            errors.append(f"{label}: published concept must have a lesson")
        for path_field in ("lesson", "exercise"):
            relative = concept[path_field]
            if relative and not (ROOT / relative).is_file():
                errors.append(f"{label}: missing {path_field} file {relative}")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("Curriculum validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Curriculum validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
