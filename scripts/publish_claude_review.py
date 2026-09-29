#!/usr/bin/env python3
"""Publish a Kaasu-style, reviewer-owned Claude gate on a GitHub pull request."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

API = "https://api.github.com"
AUDIT_MARKER = "<!-- claude-pr-review -->"
PENDING_MARKER = "<!-- claude-review-state -->"
LEGACY_PENDING_MARKER = "<!-- claude-review-thread -->"
ROUND_MARKER = "<!-- claude-review-round:"
FINDING_MARKER = "<!-- claude-review-finding:"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
ROUND_RE = re.compile(r"<!-- claude-review-round:([0-9a-f]{40})(?::r([1-9][0-9]*))? -->")
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
BLOCKING = {"critical", "high", "medium"}
MAX_FILES = 300
MAX_RESPONSE = 5_000_000


class PublishError(RuntimeError):
    def __init__(self, message: str, *, status: int | None = None):
        super().__init__(message)
        self.status = status


def inert(value: object) -> str:
    text = " ".join(str(value).split())
    text = text.replace("<!--", "<\u200b!--").replace("-->", "--\u200b>")
    text = text.replace("@", "@\u200b").replace("://", ":\u200b//").replace("www.", "www\u200b.")
    return re.sub(r"([\\`*_\[\]<>|~])", r"\\\1", text)


def inline(value: object) -> str:
    return " ".join(str(value).split()).replace("`", "'").replace("@", "@\u200b")


def workflow_message(value: object) -> str:
    """Escape a workflow-command message body, never command properties."""
    return (
        str(value)
        .replace("%", "%25")
        .replace("::", "%3A%3A")
        .replace("\r", "%0D")
        .replace("\n", "%0A")
    )


def safe_path(path: object) -> bool:
    return (
        isinstance(path, str)
        and 0 < len(path) <= 1024
        and not path.startswith("/")
        and "\\" not in path
        and ".." not in path.split("/")
        and not re.search(r"[\x00-\x1f\x7f]", path)
    )


class GitHub:
    def __init__(self, repository: str, token: str):
        if not REPO_RE.fullmatch(repository) or not token:
            raise PublishError("valid GITHUB_REPOSITORY and GH_TOKEN are required")
        self.repository = repository
        self.token = token

    def request(self, method: str, path: str, payload: object | None = None) -> Any:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            API + path,
            data=data,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "User-Agent": "ai-engineer-map-claude-publisher",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read(MAX_RESPONSE + 1)
        except urllib.error.HTTPError as exc:
            raise PublishError(
                f"GitHub API {method} {path} failed with HTTP {exc.code}", status=exc.code
            ) from exc
        except (TimeoutError, urllib.error.URLError) as exc:
            raise PublishError("GitHub API request failed before receiving a response") from exc
        if len(raw) > MAX_RESPONSE:
            raise PublishError("GitHub API response exceeded the safety limit")
        return json.loads(raw) if raw else None

    def rest(self, method: str, suffix: str, payload: object | None = None) -> Any:
        return self.request(method, f"/repos/{self.repository}{suffix}", payload)

    def graphql(self, query: str, variables: dict[str, object]) -> Any:
        result = self.request("POST", "/graphql", {"query": query, "variables": variables})
        if result.get("errors"):
            raise PublishError("GitHub GraphQL request returned errors")
        return result["data"]


def list_pages(client: GitHub, suffix: str, *, limit: int = 10) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    separator = "&" if "?" in suffix else "?"
    for page in range(1, limit + 1):
        batch = client.rest("GET", f"{suffix}{separator}per_page=100&page={page}")
        if not isinstance(batch, list):
            raise PublishError("GitHub returned a non-list collection")
        items.extend(batch)
        if len(batch) < 100:
            break
    return items


def diff_anchors(
    files: list[dict[str, Any]],
) -> tuple[dict[str, set[int]], dict[str, set[int]], dict[str, object] | None, bool]:
    right: dict[str, set[int]] = {}
    left: dict[str, set[int]] = {}
    first: dict[str, object] | None = None
    budget = 50_000
    for file in files[:MAX_FILES]:
        path, patch = file.get("filename"), file.get("patch")
        if not safe_path(path) or not isinstance(patch, str):
            continue
        old_line = new_line = 0
        for text in patch.splitlines():
            budget -= 1
            if budget < 0:
                print("Claude publisher warning: diff-anchor scan reached its 50,000-line limit")
                return right, left, first, True
            header = re.match(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", text)
            if header:
                old_line, new_line = map(int, header.groups())
            elif text.startswith("+") and not text.startswith("+++"):
                right.setdefault(path, set()).add(new_line)
                first = first or {"path": path, "line": new_line, "side": "RIGHT"}
                new_line += 1
            elif text.startswith("-") and not text.startswith("---"):
                left.setdefault(path, set()).add(old_line)
                first = first or {"path": path, "line": old_line, "side": "LEFT"}
                old_line += 1
            else:
                if old_line and new_line:
                    right.setdefault(path, set()).add(new_line)
                    left.setdefault(path, set()).add(old_line)
                old_line += 1
                new_line += 1
    return right, left, first, False


THREAD_QUERY = """
query($owner:String!,$repo:String!,$number:Int!){repository(owner:$owner,name:$repo){pullRequest(number:$number){reviewThreads(first:100){pageInfo{hasNextPage endCursor} nodes{id isResolved comments(first:100){pageInfo{hasNextPage endCursor} nodes{databaseId body}}}}}}}
"""

PERMISSION_QUERY = """
query($owner:String!,$repo:String!){repository(owner:$owner,name:$repo){viewerPermission}}
"""


def verify_write_capability(client: GitHub) -> None:
    """Reject under-privileged user tokens; Actions tokens rely on job scopes."""
    owner, repo = client.repository.split("/", 1)
    data = client.graphql(PERMISSION_QUERY, {"owner": owner, "repo": repo})
    permission = data.get("repository", {}).get("viewerPermission")
    if permission in {"WRITE", "MAINTAIN", "ADMIN"}:
        return
    # GITHUB_TOKEN is an installation token whose endpoint permissions are
    # defined by the job's `permissions:` block. GraphQL viewerPermission can
    # still report READ, so repository-role probing cannot validate it. The
    # trusted workflow declares issues/pull-requests write; every subsequent
    # mutation remains fail-closed if GitHub denies that endpoint scope.
    if os.environ.get("GITHUB_ACTIONS") == "true" and permission == "READ":
        print(
            "GitHub Actions token write capability is enforced by job-scoped "
            "permissions; subsequent mutations remain fail-closed"
        )
        return
    raise PublishError("GitHub token does not have repository write capability")


def threads(client: GitHub, pr: int) -> list[dict[str, Any]]:
    owner, repo = client.repository.split("/", 1)
    data = client.graphql(THREAD_QUERY, {"owner": owner, "repo": repo, "number": pr})
    connection = data["repository"]["pullRequest"]["reviewThreads"]
    if connection["pageInfo"]["hasNextPage"]:
        raise PublishError("review thread inventory exceeds the 100-thread safety limit")
    result = connection["nodes"]
    if any(thread["comments"]["pageInfo"]["hasNextPage"] for thread in result):
        raise PublishError("a review thread exceeds the 100-comment safety limit")
    return result


def set_resolved(client: GitHub, thread: dict[str, Any], resolved: bool) -> None:
    if bool(thread["isResolved"]) == resolved:
        return
    operation = "resolveReviewThread" if resolved else "unresolveReviewThread"
    mutation = f"mutation($id:ID!){{{operation}(input:{{threadId:$id}}){{thread{{isResolved}}}}}}"
    client.graphql(mutation, {"id": thread["id"]})


def marker_thread(all_threads: list[dict[str, Any]], marker: str) -> dict[str, Any] | None:
    return next(
        (
            thread
            for thread in all_threads
            if any(marker in (comment.get("body") or "") for comment in thread["comments"]["nodes"])
        ),
        None,
    )


def create_inline(client: GitHub, pr: int, sha: str, anchor: dict[str, object], body: str) -> dict[str, Any]:
    return client.rest(
        "POST",
        f"/pulls/{pr}/comments",
        {"body": body[:60_000], "commit_id": sha, **anchor},
    )


def create_thread_or_review(
    client: GitHub, pr: int, sha: str, anchor: dict[str, object] | None, body: str
) -> None:
    if anchor:
        try:
            create_inline(client, pr, sha, anchor, body)
            return
        except PublishError as exc:
            if exc.status != 422:
                raise
    client.rest("POST", f"/pulls/{pr}/reviews", {"body": body[:60_000], "commit_id": sha, "event": "COMMENT"})


def update_root_comment(client: GitHub, thread: dict[str, Any], body: str) -> None:
    comment_id = thread["comments"]["nodes"][0]["databaseId"]
    client.rest("PATCH", f"/pulls/comments/{comment_id}", {"body": body[:60_000]})


def ensure_pending_comment(
    client: GitHub, pr: int, sha: str, issue_comments: list[dict[str, Any]]
) -> None:
    body = "\n".join(
        [
            PENDING_MARKER,
            "### 🔒 Claude review pending",
            "",
            f"Commit `{sha[:12]}` is blocked until the reviewer approves this exact revision.",
            "This standalone lifecycle comment is updated after the exact-head review.",
        ]
    )
    current = next(
        (comment for comment in issue_comments if PENDING_MARKER in (comment.get("body") or "")),
        None,
    )
    if current:
        client.rest("PATCH", f"/issues/comments/{current['id']}", {"body": body})
    else:
        client.rest("POST", f"/issues/{pr}/comments", {"body": body})


def remove_legacy_pending_threads(client: GitHub, all_threads: list[dict[str, Any]]) -> None:
    """Remove obsolete inline lifecycle markers; inline threads are findings only."""
    for thread in all_threads:
        roots = thread["comments"]["nodes"]
        if not any(LEGACY_PENDING_MARKER in (comment.get("body") or "") for comment in roots):
            continue
        comment_id = roots[0]["databaseId"]
        client.rest("DELETE", f"/pulls/comments/{comment_id}")


def block_exact_head(client: GitHub, pr: int, sha: str, forced_human_review: bool) -> None:
    """Revoke stale approval before preparing review state for a new head."""
    # This must remain the first mutation. A later file/thread API failure may
    # leave the required check red, but must never leave the previous head's
    # advisory approval label visible on the new commit.
    set_labels(client, pr, set(), {"claude:approved"})
    if "needs-human" in labels(client, pr) and not forced_human_review:
        raise PublishError(
            "automatic Claude review is paused by needs-human; a new maintainer/Codex fix commit is required"
        )
    issue_comments = list_pages(client, f"/issues/{pr}/comments")
    ensure_pending_comment(client, pr, sha, issue_comments)
    all_threads = threads(client, pr)
    remove_legacy_pending_threads(client, all_threads)
    # Narrow the ordinary-run TOCTOU window before changing pending state. A
    # hold added while ensure_pending was running must win this race.
    if "needs-human" in labels(client, pr) and not forced_human_review:
        raise PublishError(
            "needs-human was applied while blocking the head; refusing label mutation"
        )


def labels(client: GitHub, pr: int) -> set[str]:
    issue = client.rest("GET", f"/issues/{pr}")
    return {item["name"] for item in issue.get("labels", [])}


def set_labels(client: GitHub, pr: int, add: set[str], remove: set[str]) -> None:
    current = labels(client, pr)
    for label in sorted(add - current):
        client.rest("POST", f"/issues/{pr}/labels", {"labels": [label]})
    for label in sorted(remove & current):
        try:
            client.rest("DELETE", f"/issues/{pr}/labels/{label}")
        except PublishError:
            pass


def require_publish_authorization(
    client: GitHub, pr: int, forced_human_review: bool, stage: str
) -> None:
    """Fail closed when a human hold appears before a publication mutation."""
    if "needs-human" in labels(client, pr) and not forced_human_review:
        raise PublishError(f"publication paused by needs-human before {stage}")


def validate_head(client: GitHub, pr: int, sha: str) -> None:
    if not SHA_RE.fullmatch(sha):
        raise PublishError("REVIEWED_SHA must be a full lowercase commit ID")
    pull = client.rest("GET", f"/pulls/{pr}")
    if pull.get("head", {}).get("sha") != sha:
        raise PublishError("pull-request head changed before publication")


def finding_marker(finding: dict[str, Any], sha: str) -> str:
    key = f"{sha}\0{finding['id']}".encode("utf-8")
    return f"{FINDING_MARKER}{hashlib.sha256(key).hexdigest()[:20]} -->"


def finding_body(finding: dict[str, Any], sha: str, round_number: int) -> str:
    marker = finding_marker(finding, sha)
    location = inline(finding["path"])
    if finding.get("line"):
        location += f":{finding['line']}"
    return "\n".join(
        [
            marker,
            f"**[{str(finding['severity']).upper()}] {inert(finding['title'])}**",
            "",
            f"Location: `{location}`",
            "",
            inert(finding["details"]),
            "",
            f"**Fix:** {inert(finding['recommendation'])}",
            "",
            f"_Claude review round {round_number} · commit `{sha[:12]}` — reply here after fixing; do not resolve this thread._",
        ]
    )


def finding_anchor(
    finding: dict[str, Any], right: dict[str, set[int]], fallback: dict[str, object] | None
) -> dict[str, object] | None:
    """Choose a same-file changed line or a general review; never misplace a finding."""
    path, line = finding.get("path"), finding.get("line")
    if safe_path(path):
        changed_lines = right.get(path, set())
        if isinstance(line, int) and line in changed_lines:
            return {"path": path, "line": line, "side": "RIGHT"}
        if line is None and changed_lines:
            anchor_line = min(changed_lines)
            print(
                "Claude publisher warning: finding omitted a line; "
                f"using first changed line {anchor_line} in {inline(path)}"
            )
            return {"path": path, "line": anchor_line, "side": "RIGHT"}
        print(f"Claude publisher warning: no exact inline anchor for finding path {inline(path)}")
        return None
    return fallback


def review_round(records_source: list[dict[str, Any]], sha: str) -> tuple[int, dict[str, Any] | None]:
    """Return a stable round from legacy comments and native review records."""
    records: list[tuple[dict[str, Any], str, int | None]] = []
    for record in records_source:
        match = ROUND_RE.search(record.get("body") or "")
        if match:
            records.append((record, match.group(1), int(match.group(2)) if match.group(2) else None))
    same = next((record for record in records if record[1] == sha), None)
    explicit_max = max((record[2] or 0 for record in records), default=0)
    if same:
        # Explicit markers are authoritative. All pre-migration markers are
        # deliberately treated as round one instead of reconstructing history.
        if same[2]:
            return same[2], same[0]
        return 1, same[0]
    legacy_round = 1 if any(record[2] is None for record in records) else 0
    return max(explicit_max, legacy_round) + 1, None


def ensure_native_round_review(
    client: GitHub,
    pr: int,
    sha: str,
    body: str,
    reviews: list[dict[str, Any]] | None = None,
) -> None:
    """Expose each exact-head verdict once; API failures propagate and fail the gate."""
    marker = f"{ROUND_MARKER}{sha}:"
    if reviews is None:
        reviews = list_pages(client, f"/pulls/{pr}/reviews")
    if any(marker in (review.get("body") or "") for review in reviews):
        return
    # Do not catch this mutation: visibility is part of successful publication.
    # If it fails, no native marker exists, so a rerun retries the POST.
    client.rest(
        "POST",
        f"/pulls/{pr}/reviews",
        {"body": body[:60_000], "commit_id": sha, "event": "COMMENT"},
    )


def publish(args: argparse.Namespace, client: GitHub, files: list[dict[str, Any]]) -> None:
    artifact = json.loads(args.artifact.read_text(encoding="utf-8"))
    if artifact.get("schema_version") != 1 or artifact.get("reviewed_sha") != args.sha:
        raise PublishError("review artifact does not belong to the current head")
    # Re-check the human hold immediately before the first mutation. The
    # required check remains the authoritative merge gate; this closes the
    # block→analyze→publish label race on ordinary workflow runs. A maintainer-
    # authorized forced review must opt in explicitly for this one process.
    forced_human_review = os.environ.get("CLAUDE_HUMAN_REREVIEW") == "true"
    require_publish_authorization(client, args.pr, forced_human_review, "artifact validation")
    expected_approved = os.environ.get("REVIEW_APPROVED")
    expected_count = os.environ.get("REVIEW_FINDING_COUNT", "")
    if expected_approved not in {"true", "false"} or not expected_count.isdigit():
        raise PublishError("review decision outputs are missing or invalid")
    status = artifact.get("status")
    if status == "ERROR":
        if not isinstance(artifact.get("error"), str) or expected_approved != "false" or expected_count != "0":
            raise PublishError("error artifact disagrees with the fail-closed decision")
        review = None
        findings: list[dict[str, Any]] = []
    elif status != "OK":
        raise PublishError("validated review artifact has an invalid status")
    else:
        review = artifact.get("review")
        if not isinstance(review, dict) or review.get("verdict") not in {"APPROVED", "CHANGES_REQUESTED"}:
            raise PublishError("review artifact has an invalid verdict")
        findings = review.get("findings")
        if not isinstance(findings, list) or len(findings) > 100:
            raise PublishError("review artifact has invalid findings")
        blocking_count = sum(
            1 for finding in findings if finding.get("severity") in BLOCKING
        )
        if (review["verdict"] == "APPROVED") != (expected_approved == "true"):
            raise PublishError("review artifact disagrees with the approval decision")
        if blocking_count != int(expected_count):
            raise PublishError("review artifact disagrees with the blocking finding count")

    # Only validated artifacts may become visible PR state.
    issue_comments = list_pages(client, f"/issues/{args.pr}/comments")
    prior_audit = next((item for item in issue_comments if AUDIT_MARKER in (item.get("body") or "")), None)
    report = args.report.read_text(encoding="utf-8")[:60_000]
    require_publish_authorization(client, args.pr, forced_human_review, "audit mutation")
    if prior_audit:
        audit = client.rest("PATCH", f"/issues/comments/{prior_audit['id']}", {"body": report})
    else:
        audit = client.rest("POST", f"/issues/{args.pr}/comments", {"body": report})
    if status == "ERROR":
        require_publish_authorization(client, args.pr, forced_human_review, "error label mutation")
        set_labels(client, args.pr, set(), {"claude:approved"})
        return
    assert review is not None

    # Legacy versions also posted this marker as an issue comment. Read both
    # locations so round numbers remain monotonic without publishing the same
    # summary twice in the Conversation timeline.
    native_reviews = list_pages(client, f"/pulls/{args.pr}/reviews")
    round_number, _ = review_round([*issue_comments, *native_reviews], args.sha)
    counts = {severity: 0 for severity in ("critical", "high", "medium", "low")}
    for finding in findings:
        severity = finding.get("severity")
        if severity not in counts:
            raise PublishError("review artifact contains an invalid severity")
        counts[severity] += 1
    summary = [
        f"{ROUND_MARKER}{args.sha}:r{round_number} -->",
        f"### Claude review round {round_number} — {inert(review['verdict'])}",
        "",
        f"Reviewed commit: `{args.sha}`",
        f"Findings: {counts['critical']} CRITICAL / {counts['high']} HIGH / {counts['medium']} MEDIUM / {counts['low']} LOW.",
        inert(review["summary"]),
        "",
        f"[Complete sanitized audit report]({audit['html_url']})",
    ]
    low = [finding for finding in findings if finding.get("severity") == "low"]
    if low:
        summary.extend(["", "LOW notes (non-blocking):"])
        summary.extend(f"- **{inert(item['title'])}** — {inert(item['recommendation'])}" for item in low)
    if review["verdict"] == "CHANGES_REQUESTED":
        summary.extend(["", "Address every open Claude finding thread and reply in each with the fix and test evidence. Do not resolve reviewer threads."])
        if round_number >= 2:
            summary.extend(
                [
                    "",
                    "Automatic review limit reached after two rounds; `needs-human` is now required. "
                    "A maintainer must manually start Codex (or fix the blockers directly); pushing the fix commit starts the next Claude review.",
                ]
            )
    body = "\n".join(summary)[:60_000]
    require_publish_authorization(client, args.pr, forced_human_review, "native review mutation")
    ensure_native_round_review(client, args.pr, args.sha, body, native_reviews)

    right, _left, fallback, anchors_truncated = diff_anchors(files)
    if anchors_truncated:
        # Exact anchors already observed remain usable. An unanchored finding
        # must become a general review instead of being attached to an
        # unrelated early line from a partially scanned diff.
        fallback = None
    all_threads = threads(client, args.pr)
    pending = next(
        (comment for comment in issue_comments if PENDING_MARKER in (comment.get("body") or "")),
        None,
    )
    approved = review["verdict"] == "APPROVED"
    if approved:
        require_publish_authorization(client, args.pr, forced_human_review, "approval state mutation")
        if pending:
            client.rest(
                "PATCH",
                f"/issues/comments/{pending['id']}",
                {
                    "body": "\n".join(
                        [
                            PENDING_MARKER,
                            "### ✅ Claude approved",
                            "",
                            f"Approved exact commit `{args.sha}` in round {round_number}.",
                        ]
                    )
                },
            )
        for thread in all_threads:
            if any(FINDING_MARKER in (comment.get("body") or "") for comment in thread["comments"]["nodes"]):
                set_resolved(client, thread, True)
        require_publish_authorization(client, args.pr, forced_human_review, "approval label mutation")
        set_labels(client, args.pr, {"claude:approved"}, {"claude:changes-requested", "needs-human"})
        return

    current_markers = {
        finding_marker(finding, args.sha)
        for finding in findings
        if finding.get("severity") in BLOCKING
    }
    require_publish_authorization(client, args.pr, forced_human_review, "finding reconciliation")
    for thread in all_threads:
        bodies = [comment.get("body") or "" for comment in thread["comments"]["nodes"]]
        if any(FINDING_MARKER in body for body in bodies) and not any(
            marker in body for marker in current_markers for body in bodies
        ):
            set_resolved(client, thread, True)
    require_publish_authorization(client, args.pr, forced_human_review, "finding publication")
    for finding in findings:
        if finding.get("severity") not in BLOCKING:
            continue
        marker = finding_marker(finding, args.sha)
        existing = marker_thread(all_threads, marker)
        body = finding_body(finding, args.sha, round_number)
        if existing:
            update_root_comment(client, existing, body)
            set_resolved(client, existing, False)
            continue
        anchor = finding_anchor(finding, right, fallback)
        create_thread_or_review(client, args.pr, args.sha, anchor, body)
    additions = {"claude:changes-requested"}
    if round_number >= 2:
        additions.add("needs-human")
    require_publish_authorization(client, args.pr, forced_human_review, "changes label mutation")
    set_labels(client, args.pr, additions, {"claude:approved"})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("verify", "block", "publish"), required=True)
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--artifact", type=Path)
    args = parser.parse_args()
    if args.pr < 1 or not SHA_RE.fullmatch(args.sha):
        raise SystemExit("invalid PR number or reviewed SHA")
    client = GitHub(os.environ.get("GITHUB_REPOSITORY", ""), os.environ.get("GH_TOKEN", ""))
    # SECURITY INVARIANT: exact-head validation is the first API operation and
    # must remain before every file/thread read and every PR mutation.
    validate_head(client, args.pr, args.sha)
    if args.mode == "verify":
        return 0
    verify_write_capability(client)
    if args.mode == "block":
        forced_human_review = os.environ.get("CLAUDE_HUMAN_REREVIEW") == "true"
        block_exact_head(client, args.pr, args.sha, forced_human_review)
        return 0
    if args.report is None or args.artifact is None:
        raise SystemExit("--report and --artifact are required in publish mode")
    files = list_pages(client, f"/pulls/{args.pr}/files", limit=3)
    publish(args, client, files)
    return 0


def cli() -> int:
    try:
        return main()
    except PublishError as exc:
        print(
            f"::error title=Claude review publisher::{workflow_message(exc)}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(cli())
