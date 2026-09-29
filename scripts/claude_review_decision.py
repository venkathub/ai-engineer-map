#!/usr/bin/env python3
"""Validate that exactly one Claude review route produced a gateable result."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from claude_review_gate import ReviewError, render_unavailable, validate_reviewed_sha, write_outputs

VALID_VERDICTS = {"APPROVED", "CHANGES_REQUESTED", "ERROR"}


def select_result(
    subscription_outcome: str,
    subscription_gate_outcome: str,
    subscription_approved: str,
    subscription_verdict: str,
    subscription_finding_count: str,
    api_gate_outcome: str,
    api_approved: str,
    api_verdict: str,
    api_finding_count: str,
) -> tuple[bool, str, int]:
    if subscription_outcome == "success":
        if subscription_gate_outcome != "success":
            raise ReviewError("subscription review succeeded but its report gate did not complete")
        if api_gate_outcome != "skipped":
            raise ReviewError("API fallback ran after a successful subscription review")
        approved, verdict, finding_count = (
            subscription_approved,
            subscription_verdict,
            subscription_finding_count,
        )
    else:
        if subscription_gate_outcome != "skipped":
            raise ReviewError(
                "subscription report gate completed without a successful subscription review"
            )
        if api_gate_outcome != "success":
            raise ReviewError("subscription review failed and API fallback did not complete")
        approved, verdict, finding_count = api_approved, api_verdict, api_finding_count

    if approved not in {"true", "false"}:
        raise ReviewError("selected review route did not emit an approved output")
    if verdict not in VALID_VERDICTS:
        raise ReviewError("selected review route did not emit a valid verdict")
    if (approved == "true") != (verdict == "APPROVED"):
        raise ReviewError("selected review route emitted inconsistent approval and verdict outputs")
    if not finding_count.isdigit():
        raise ReviewError("selected review route did not emit a valid finding count")
    count = int(finding_count)
    if (verdict == "APPROVED" and count != 0) or (verdict == "CHANGES_REQUESTED" and count < 1):
        raise ReviewError("selected review route emitted inconsistent verdict and finding count")
    if verdict == "ERROR" and count != 0:
        raise ReviewError("failed review route emitted a nonzero finding count")
    return approved == "true", verdict, count


def write_failure_report(report: Path, reason: str, reviewed_sha: str) -> bool:
    try:
        report.write_text(render_unavailable(reason, reviewed_sha), encoding="utf-8")
    except OSError as exc:
        print(f"Could not write fail-closed Claude report: {exc}")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        reviewed_sha = validate_reviewed_sha(os.environ.get("REVIEWED_SHA", ""))
        approved, verdict, finding_count = select_result(
            os.environ.get("SUBSCRIPTION_OUTCOME", ""),
            os.environ.get("SUBSCRIPTION_GATE_OUTCOME", ""),
            os.environ.get("SUBSCRIPTION_APPROVED", ""),
            os.environ.get("SUBSCRIPTION_VERDICT", ""),
            os.environ.get("SUBSCRIPTION_FINDING_COUNT", ""),
            os.environ.get("API_GATE_OUTCOME", ""),
            os.environ.get("API_APPROVED", ""),
            os.environ.get("API_VERDICT", ""),
            os.environ.get("API_FINDING_COUNT", ""),
        )
        if not args.report.is_file():
            raise ReviewError("selected review route did not create a report")
    except ReviewError as exc:
        approved, verdict, finding_count = False, "ERROR", 0
        reviewed_sha = os.environ.get("REVIEWED_SHA", "")
        report_written = write_failure_report(args.report, str(exc), reviewed_sha)
        if not report_written:
            write_outputs(approved, verdict, 0)
            return 1

    write_outputs(approved, verdict, finding_count)
    print(f"Selected Claude review verdict: {verdict}; approved={str(approved).lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
