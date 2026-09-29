#!/usr/bin/env python3
"""Validate Claude's structured PR review and render the required check report."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

MARKER = "<!-- claude-pr-review -->"
VERDICTS = {"APPROVED", "CHANGES_REQUESTED"}
SEVERITIES = {"critical", "high", "medium", "low"}


class ReviewError(ValueError):
    """Raised when Claude's structured review violates the gate contract."""


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReviewError(f"{field} must be a non-empty string")
    return value.strip()


def _safe_markdown(value: str) -> str:
    """Prevent mentions and comment markers from being injected into the report."""
    return value.replace("@", "@\u200b").replace("<!--", "&lt;!--")


def normalize_review(raw: str) -> dict[str, Any]:
    try:
        review = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ReviewError("Claude did not return valid structured JSON") from exc
    if not isinstance(review, dict):
        raise ReviewError("Claude review must be a JSON object")

    verdict = _text(review.get("verdict"), "verdict")
    if verdict not in VERDICTS:
        raise ReviewError(f"unsupported verdict: {verdict}")
    summary = _text(review.get("summary"), "summary")

    findings = review.get("findings")
    if not isinstance(findings, list):
        raise ReviewError("findings must be a list")
    normalized_findings: list[dict[str, Any]] = []
    for index, finding in enumerate(findings, start=1):
        if not isinstance(finding, dict):
            raise ReviewError(f"finding {index} must be an object")
        severity = _text(finding.get("severity"), f"finding {index} severity")
        if severity not in SEVERITIES:
            raise ReviewError(f"finding {index} has unsupported severity: {severity}")
        line = finding.get("line")
        if line is not None and (not isinstance(line, int) or isinstance(line, bool) or line < 1):
            raise ReviewError(f"finding {index} line must be null or a positive integer")
        normalized_findings.append(
            {
                "id": _text(finding.get("id"), f"finding {index} id"),
                "severity": severity,
                "path": _text(finding.get("path"), f"finding {index} path"),
                "line": line,
                "title": _text(finding.get("title"), f"finding {index} title"),
                "details": _text(finding.get("details"), f"finding {index} details"),
                "recommendation": _text(
                    finding.get("recommendation"), f"finding {index} recommendation"
                ),
            }
        )

    tests_reviewed = review.get("tests_reviewed")
    residual_risks = review.get("residual_risks")
    if not isinstance(tests_reviewed, list) or not all(isinstance(item, str) for item in tests_reviewed):
        raise ReviewError("tests_reviewed must be a list of strings")
    if not isinstance(residual_risks, list) or not all(isinstance(item, str) for item in residual_risks):
        raise ReviewError("residual_risks must be a list of strings")

    if verdict == "APPROVED" and normalized_findings:
        raise ReviewError("APPROVED is inconsistent with non-empty findings")
    if verdict == "CHANGES_REQUESTED" and not normalized_findings:
        raise ReviewError("CHANGES_REQUESTED requires at least one finding")

    return {
        "verdict": verdict,
        "summary": summary,
        "findings": normalized_findings,
        "tests_reviewed": [item.strip() for item in tests_reviewed if item.strip()],
        "residual_risks": [item.strip() for item in residual_risks if item.strip()],
    }


def render_review(review: dict[str, Any], reviewed_sha: str, route: str = "") -> str:
    approved = review["verdict"] == "APPROVED"
    icon = "✅" if approved else "❌"
    lines = [
        MARKER,
        "## Claude PR review",
        "",
        f"**{icon} {review['verdict']}** for commit `{reviewed_sha[:12] or 'unknown'}`",
        "",
        _safe_markdown(review["summary"]),
    ]
    if route:
        lines.extend(["", f"Review route: `{_safe_markdown(route).replace('`', "'")}`"])

    findings = review["findings"]
    lines.extend(["", f"### Actionable findings ({len(findings)})", ""])
    if not findings:
        lines.append("No actionable findings remain.")
    for finding in findings:
        location = finding["path"]
        if finding["line"] is not None:
            location += f":{finding['line']}"
        lines.extend(
            [
                f"- **[{finding['severity'].upper()}] {_safe_markdown(finding['title'])}** "
                f"(`{_safe_markdown(location).replace('`', "'")}`; "
                f"ID `{_safe_markdown(finding['id']).replace('`', "'")}`)",
                f"  - {_safe_markdown(finding['details'])}",
                f"  - Fix: {_safe_markdown(finding['recommendation'])}",
            ]
        )

    lines.extend(["", "### Evidence considered", ""])
    if review["tests_reviewed"]:
        lines.extend(f"- {_safe_markdown(item)}" for item in review["tests_reviewed"])
    else:
        lines.append("- No test evidence was reported by Claude.")

    lines.extend(["", "### Residual risks", ""])
    if review["residual_risks"]:
        lines.extend(f"- {_safe_markdown(item)}" for item in review["residual_risks"])
    else:
        lines.append("- None reported.")
    lines.extend(
        [
            "",
            "This report is replaced on every pushed revision. The required check passes only "
            "when the current commit is approved with zero actionable findings.",
        ]
    )
    return "\n".join(lines)[:60_000] + "\n"


def render_unavailable(reason: str, reviewed_sha: str) -> str:
    return "\n".join(
        [
            MARKER,
            "## Claude PR review",
            "",
            f"**⚠️ REVIEW UNAVAILABLE** for commit `{reviewed_sha[:12] or 'unknown'}`",
            "",
            _safe_markdown(reason),
            "",
            "The required check remains blocked until Claude returns a valid structured review.",
            "",
        ]
    )


def write_outputs(approved: bool, verdict: str, finding_count: int) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with Path(output_path).open("a", encoding="utf-8") as output:
        output.write(f"approved={'true' if approved else 'false'}\n")
        output.write(f"verdict={verdict}\n")
        output.write(f"finding_count={finding_count}\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    reviewed_sha = os.environ.get("REVIEWED_SHA", "")
    auth_configured = os.environ.get("CLAUDE_AUTH_CONFIGURED") == "true"
    action_outcome = os.environ.get("CLAUDE_ACTION_OUTCOME", "skipped")
    raw_review = os.environ.get("CLAUDE_REVIEW_JSON", "")
    review_route = os.environ.get("REVIEW_ROUTE", "")

    try:
        if not auth_configured:
            raise ReviewError(
                "Configure exactly one repository Actions secret: ANTHROPIC_API_KEY, or "
                "CLAUDE_CODE_OAUTH_TOKEN for a supported Claude Pro/Max subscription."
            )
        if action_outcome != "success":
            raise ReviewError(f"Claude Code Action outcome was {action_outcome!r}")
        review = normalize_review(raw_review)
        approved = review["verdict"] == "APPROVED"
        report = render_review(review, reviewed_sha, review_route)
        write_outputs(approved, review["verdict"], len(review["findings"]))
    except ReviewError as exc:
        report = render_unavailable(str(exc), reviewed_sha)
        write_outputs(False, "ERROR", 0)

    args.output.write_text(report, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
