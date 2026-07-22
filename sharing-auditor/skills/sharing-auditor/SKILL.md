---
name: sharing-auditor
description: >
  Use when the user asks what's shared or exposed in Kiteworks — trigger
  phrases include "what's shared in X folder," "find externally shared
  files," "sharing audit," or "what's exposed outside my team." Scans
  and, on confirmation, writes a CSV + txt/pdf report. Single-phase: no
  separate "apply" step to ask for.
metadata:
  version: "1.0.2"
---

On surfaces that support plugin subagents, delegate to the `sharing-auditor` subagent. If it reports no tools or fabricates results without tool calls, discard and check the `Kiteworks` connector.

# Sharing Auditor

Read `../folder-scan/SKILL.md` first. Confirmed live: folder/file objects returned by `get_top_folders`/`get_folder_children` carry an `isShared` boolean directly — use it, don't rely on `search_filter: 'shared'` with no term (confirmed to return nothing unscoped).

## Why this is one phase, not two

This agent never changes sharing settings (no such tool exists) and never touches flagged items — its only write action is a CSV + txt/pdf report. That doesn't need a separate confirmation gate as its own skill; it's folded into one scan-then-offer-to-save flow.

## Collect from the user

A folder scope (required). Optionally: whether to include subfolders recursively (default yes, bounded per `folder-scan`).

## Walk and flag

Walk the folder with `get_folder_children`, note every item where `isShared` is true. Cross-reference item names against any sensitive-sounding terms the user cares about (optional; if given, flag matches as higher priority) but do not require a term list — the core value here is just surfacing what's shared at all.

## Present the result, then actively offer to save it

Summary card: summary, counts (shared vs. total), shared items with name/path/link/owner, coverage, warnings (note this reports sharing *state* only — it cannot see who specifically has access or whether that's appropriate; that judgment is the user's).

**Do not stop there and wait.** End by explicitly asking, e.g.: *"Want me to save this as a CSV + PDF report to `My Folder/Agents/Sharing Auditor/`?"*

## If confirmed, write the report

Read `../report-export/SKILL.md` and follow it exactly. Default agent name: "Sharing Auditor".

Write the CSV (name, path, isShared, owner, link) and the txt/pdf narrative (counts, top shared items, coverage, disclaimer verbatim). Never change sharing settings or touch flagged items — this agent's only write action is the report files.
