#!/usr/bin/env python3
"""Validate Claude's structured PR review and render the required check report."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

MARKER = "<!-- claude-pr-review -->"
VERDICTS = {"APPROVED", "CHANGES_REQUESTED"}
SEVERITIES = {"critical", "high", "medium", "low"}
BLOCKING_SEVERITIES = {"critical", "high", "medium"}
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
MAX_FINDINGS = 100
ARTIFACT_SCHEMA_VERSION = 1


class ReviewError(ValueError):
    """Raised when Claude's structured review violates the gate contract."""


def validate_reviewed_sha(value: str) -> str:
    if not SHA_PATTERN.fullmatch(value):
        raise ReviewError("REVIEWED_SHA must be a 40-character lowercase Git commit ID")
    return value


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReviewError(f"{field} must be a non-empty string")
    return value.strip()


def _plain_text(value: str) -> str:
    """Flatten model text and neutralize mentions and automatically linked URLs."""
    flattened = " ".join(value.split())
    return (
        flattened.replace("<!--", "<\u200b!--")
        .replace("-->", "--\u200b>")
        .replace("@", "@\u200b")
        .replace("://", ":\u200b//")
        .replace("www.", "www\u200b.")
    )


def _safe_markdown(value: str) -> str:
    """Render model-controlled content as inert Markdown text."""
    flattened = _plain_text(value)
    escaped = re.sub(r"([\\`*_\[\]<>|~])", r"\\\1", flattened)
    if escaped.startswith(("#", ">", "-", "+")):
        escaped = "\\" + escaped
    return re.sub(r"^(\d+)\.", r"\1\\.", escaped)


def _inline_code(value: str) -> str:
    return _plain_text(value).replace("`", "'")


def _commit_label(reviewed_sha: str) -> str:
    return reviewed_sha[:12] if SHA_PATTERN.fullmatch(reviewed_sha) else "unknown"


def validate_subscription_result(
    auth_configured: bool, action_outcome: str, raw_review: str
) -> dict[str, Any]:
    if not auth_configured:
        raise ReviewError(
            "Configure CLAUDE_CODE_OAUTH_TOKEN for subscription review and/or "
            "ANTHROPIC_API_KEY as a metered fallback."
        )
    if action_outcome != "success":
        raise ReviewError(f"Claude Code Action outcome was {action_outcome!r}")
    if not raw_review.strip():
        raise ReviewError("Claude Code Action succeeded without a structured_output value")
    return normalize_review(raw_review)


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
    if len(findings) > MAX_FINDINGS:
        raise ReviewError(f"findings must contain at most {MAX_FINDINGS} items")
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
    if any(not item.strip() for item in tests_reviewed):
        raise ReviewError("tests_reviewed entries must be non-empty strings")
    if any(not item.strip() for item in residual_risks):
        raise ReviewError("residual_risks entries must be non-empty strings")

    blocking = [
        finding for finding in normalized_findings if finding["severity"] in BLOCKING_SEVERITIES
    ]
    if verdict == "APPROVED" and blocking:
        raise ReviewError("APPROVED is inconsistent with blocking findings")
    if verdict == "CHANGES_REQUESTED" and not blocking:
        raise ReviewError("CHANGES_REQUESTED requires at least one blocking finding")

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
        f"**{icon} {review['verdict']}** for commit `{_commit_label(reviewed_sha)}`",
        "",
        _safe_markdown(review["summary"]),
    ]
    if route:
        route_display = _inline_code(route)
        lines.extend(["", f"Review route: `{route_display}`"])

    findings = review["findings"]
    lines.extend(["", f"### Actionable findings ({len(findings)})", ""])
    if not findings:
        lines.append("No actionable findings remain.")
    for finding in findings:
        location = finding["path"]
        if finding["line"] is not None:
            location += f":{finding['line']}"
        location_display = _inline_code(location)
        finding_id_display = _inline_code(finding["id"])
        lines.extend(
            [
                f"- **[{finding['severity'].upper()}] {_safe_markdown(finding['title'])}** "
                f"(`{location_display}`; ID `{finding_id_display}`)",
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
            "when the current commit is approved with zero blocking findings.",
        ]
    )
    return "\n".join(lines)[:60_000] + "\n"


def render_unavailable(reason: str, reviewed_sha: str) -> str:
    return "\n".join(
        [
            MARKER,
            "## Claude PR review",
            "",
            f"**⚠️ REVIEW UNAVAILABLE** for commit `{_commit_label(reviewed_sha)}`",
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


def blocking_finding_count(review: dict[str, Any]) -> int:
    return sum(
        1 for finding in review["findings"] if finding["severity"] in BLOCKING_SEVERITIES
    )


def write_review_artifact(
    path: Path | None,
    *,
    reviewed_sha: str,
    route: str,
    review: dict[str, Any] | None = None,
    error: str = "",
) -> None:
    """Write the validated machine-readable handoff consumed by the publisher job."""
    if path is None:
        return
    payload: dict[str, Any] = {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "reviewed_sha": reviewed_sha,
        "route": route,
    }
    if review is None:
        payload.update({"status": "ERROR", "error": _plain_text(error)[:2_000]})
    else:
        payload.update({"status": "OK", "review": review})
    path.write_text(json.dumps(payload, ensure_ascii=True, separators=(",", ":")), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()

    reviewed_sha = os.environ.get("REVIEWED_SHA", "")
    auth_configured = os.environ.get("CLAUDE_AUTH_CONFIGURED") == "true"
    action_outcome = os.environ.get("CLAUDE_ACTION_OUTCOME", "skipped")
    raw_review = os.environ.get("CLAUDE_REVIEW_JSON", "")
    review_route = os.environ.get("REVIEW_ROUTE", "")

    try:
        reviewed_sha = validate_reviewed_sha(reviewed_sha)
        review = validate_subscription_result(auth_configured, action_outcome, raw_review)
        approved = review["verdict"] == "APPROVED"
        report = render_review(review, reviewed_sha, review_route)
        write_review_artifact(
            args.json_output,
            reviewed_sha=reviewed_sha,
            route=review_route,
            review=review,
        )
        write_outputs(approved, review["verdict"], blocking_finding_count(review))
    except ReviewError as exc:
        report = render_unavailable(str(exc), reviewed_sha)
        write_review_artifact(
            args.json_output,
            reviewed_sha=reviewed_sha,
            route=review_route,
            error=str(exc),
        )
        write_outputs(False, "ERROR", 0)

    args.output.write_text(report, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
