#!/usr/bin/env python3
"""Validate that exactly one Claude review route produced a gateable result."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from claude_review_gate import ReviewError, render_unavailable, write_outputs

VALID_VERDICTS = {"APPROVED", "CHANGES_REQUESTED", "ERROR"}


def select_result(
    subscription_outcome: str,
    subscription_gate_outcome: str,
    subscription_approved: str,
    subscription_verdict: str,
    api_gate_outcome: str,
    api_approved: str,
    api_verdict: str,
) -> tuple[bool, str]:
    if subscription_outcome == "success":
        if subscription_gate_outcome != "success":
            raise ReviewError("subscription review succeeded but its report gate did not complete")
        if api_gate_outcome not in {"", "skipped"}:
            raise ReviewError("API fallback ran after a successful subscription review")
        approved, verdict = subscription_approved, subscription_verdict
    else:
        if api_gate_outcome != "success":
            raise ReviewError("subscription review failed and API fallback did not complete")
        approved, verdict = api_approved, api_verdict

    if approved not in {"true", "false"}:
        raise ReviewError("selected review route did not emit an approved output")
    if verdict not in VALID_VERDICTS:
        raise ReviewError("selected review route did not emit a valid verdict")
    if (approved == "true") != (verdict == "APPROVED"):
        raise ReviewError("selected review route emitted inconsistent approval and verdict outputs")
    return approved == "true", verdict


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        approved, verdict = select_result(
            os.environ.get("SUBSCRIPTION_OUTCOME", ""),
            os.environ.get("SUBSCRIPTION_GATE_OUTCOME", ""),
            os.environ.get("SUBSCRIPTION_APPROVED", ""),
            os.environ.get("SUBSCRIPTION_VERDICT", ""),
            os.environ.get("API_GATE_OUTCOME", ""),
            os.environ.get("API_APPROVED", ""),
            os.environ.get("API_VERDICT", ""),
        )
        if not args.report.is_file():
            raise ReviewError("selected review route did not create a report")
    except ReviewError as exc:
        approved, verdict = False, "ERROR"
        reviewed_sha = os.environ.get("REVIEWED_SHA", "")
        args.report.write_text(render_unavailable(str(exc), reviewed_sha), encoding="utf-8")

    write_outputs(approved, verdict, 0)
    print(f"Selected Claude review verdict: {verdict}; approved={str(approved).lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

