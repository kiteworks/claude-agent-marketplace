#!/usr/bin/env python3
"""
Merges static_findings.json + ai_findings.json into one summary, posts (or
updates) a single note on the merge request via the GitLab API, and exits
non-zero if any finding meets the blocking threshold -- which fails this job
and, with "Pipelines must succeed" enabled under Settings > Merge requests >
Merge checks, blocks the merge.

Required env vars (CI_API_V4_URL, CI_PROJECT_ID, CI_MERGE_REQUEST_IID are
predefined automatically by GitLab in merge request pipelines):
  GITLAB_TOKEN, CI_API_V4_URL, CI_PROJECT_ID, CI_MERGE_REQUEST_IID
Optional:
  STATIC_IN, AI_IN
  BLOCK_SEVERITY  minimum severity that blocks merge (default "high")
"""

import json
import os
import sys
from pathlib import Path

import requests

STATIC_IN = Path(os.environ.get("STATIC_IN", "static_findings.json"))
AI_IN = Path(os.environ.get("AI_IN", "ai_findings.json"))
BLOCK_SEVERITY = os.environ.get("BLOCK_SEVERITY", "high")

TOKEN = os.environ["GITLAB_TOKEN"]
API = os.environ["CI_API_V4_URL"]
PROJECT_ID = os.environ["CI_PROJECT_ID"]
MR_IID = os.environ["CI_MERGE_REQUEST_IID"]

HEADERS = {"PRIVATE-TOKEN": TOKEN}

SEV_ORDER = ["info", "low", "medium", "high", "critical"]
SEV_LABEL = {"critical": "CRITICAL", "high": "HIGH", "medium": "MEDIUM", "low": "LOW", "info": "INFO"}

MARKER = "<!-- kw-plugin-security-scan -->"


def sev_rank(sev):
    return SEV_ORDER.index(sev) if sev in SEV_ORDER else 0


def load(path):
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return []


def dedupe(findings):
    seen = set()
    out = []
    for f in findings:
        key = (f.get("file"), f.get("category"), f.get("description", "")[:80])
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return out


def build_summary(findings, verdict, threshold):
    lines = [MARKER, "## Plugin Security Scan", ""]

    if not findings:
        lines.append("No findings. Static pattern scan and AI review both came back clean. Result: PASS.")
        return "\n".join(lines)

    counts = {s: 0 for s in SEV_ORDER}
    for f in findings:
        counts[f.get("severity", "info")] = counts.get(f.get("severity", "info"), 0) + 1

    count_line = " · ".join(
        f"{SEV_LABEL[s]}: {counts[s]}" for s in reversed(SEV_ORDER) if counts.get(s)
    )
    lines.append(count_line)
    lines.append("")

    if verdict == "block":
        lines.append(f"**Result: BLOCKED — findings at or above `{threshold}` severity were found.**")
    else:
        lines.append(f"**Result: PASS — nothing at or above `{threshold}` severity.**")
    lines.append("")

    lines.append("| Severity | File | Category | Source | Description |")
    lines.append("|---|---|---|---|---|")
    for f in sorted(findings, key=lambda f: -sev_rank(f.get("severity", "info"))):
        sev = f.get("severity", "info")
        label = SEV_LABEL.get(sev, "INFO")
        file_ref = f.get("file", "?")
        if f.get("line"):
            file_ref += f":{f['line']}"
        desc = f.get("description", "").replace("|", "\\|")
        lines.append(
            f"| {label} | `{file_ref}` | {f.get('category','')} "
            f"| {f.get('source','')} | {desc} |"
        )

    lines.append("")
    lines.append(
        "_Static findings are pattern-based (fast, literal). AI findings come from a "
        "Claude review on Bedrock reading the diff in context. Treat both as a strong "
        "signal for human review, not an automatic verdict of malice — verify before acting._"
    )
    return "\n".join(lines)


def find_existing_note():
    url = f"{API}/projects/{PROJECT_ID}/merge_requests/{MR_IID}/notes"
    page = 1
    while True:
        resp = requests.get(url, headers=HEADERS, params={"per_page": 100, "page": page})
        resp.raise_for_status()
        notes = resp.json()
        if not notes:
            return None
        for n in notes:
            if MARKER in (n.get("body") or ""):
                return n["id"]
        if len(notes) < 100:
            return None
        page += 1


def upsert_note(body):
    existing_id = find_existing_note()
    if existing_id:
        url = f"{API}/projects/{PROJECT_ID}/merge_requests/{MR_IID}/notes/{existing_id}"
        resp = requests.put(url, headers=HEADERS, json={"body": body})
    else:
        url = f"{API}/projects/{PROJECT_ID}/merge_requests/{MR_IID}/notes"
        resp = requests.post(url, headers=HEADERS, json={"body": body})
    resp.raise_for_status()


def main():
    static_findings = load(STATIC_IN)
    ai_findings = load(AI_IN)
    all_findings = dedupe(static_findings + ai_findings)

    threshold_rank = sev_rank(BLOCK_SEVERITY)
    blocking_findings = [f for f in all_findings if sev_rank(f.get("severity", "info")) >= threshold_rank]
    verdict = "block" if blocking_findings else "pass"

    summary = build_summary(all_findings, verdict, BLOCK_SEVERITY)
    upsert_note(summary)

    print(summary)

    if verdict == "block":
        print(f"::error::{len(blocking_findings)} finding(s) at or above '{BLOCK_SEVERITY}' severity.")
        sys.exit(1)


if __name__ == "__main__":
    main()
