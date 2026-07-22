---
name: retention-sweeper
description: >
  Use when the user asks to check, scan, or review what's past retention
  in a Kiteworks folder — trigger phrases include "show me what's past
  retention in X," "what's older than N months/years in this folder," or
  "check retention on [folder]." Scans and, on confirmation, writes a
  CSV + txt/pdf report. Single-phase: no separate "apply" step to ask for.
metadata:
  version: "1.0.2"
---

On surfaces that support plugin subagents (Claude Code, Claude Cowork), delegate to the `retention-sweeper` subagent. If it reports no tools available, or returns results without making any Kiteworks tool calls, treat the result as fabricated, discard it, and ask the user to check the `Kiteworks` connector is connected. On other surfaces, follow this skill directly.

# Retention Sweeper

Read `../folder-scan/SKILL.md` first and follow its rules for scope, bounded walk, link-building, and metadata fields.

Productivity-grade helper. Not the audited Kiteworks compliance runtime. Legal hold is NOT evaluated — this is metadata only and results are review candidates, never a deletion or disposition basis.

## Why this is one phase, not two

This agent's only possible action is writing a new CSV + txt/pdf report — it never moves, renames, or deletes the files it flags. A separate "apply" step doesn't gate anything risky here (unlike Duplicate Finder, which actually relocates files), so it collapsed into a single scan-then-offer-to-save flow. This still asks before writing anything — it just doesn't need a second named skill/agent to do it.

## Collect from the user

- A folder (path or ID) to scan — required, never scan blindly.
- A retention threshold, e.g. "18 months" or "7 years." Accept per-folder or per-file-type rules if the user gives more than one (e.g. "drafts: 18 months, contracts: 7 years").
- Whether to report only past-retention items or the full scanned set (this also determines what the CSV would contain if exported).

## Compute the cutoff deterministically

Before scanning, compute the actual cutoff date (today minus the threshold) as a plain date, e.g. "threshold 18 months, today 2026-07-13 → cutoff 2025-01-13." Do this arithmetic explicitly and state it in the result. Then do the bounded `get_folder_children` walk per `folder-scan` and compare each item's `modified` (or `created`, whichever the user's policy is anchored to — ask if unclear) against that fixed cutoff string client-side.

**Do not use `search_files`'s `modified_before`/`created_before` alone as a substitute for the walk.** Confirmed live: a query with only `parent_folder_id` plus a date filter and no text term returns nothing at all, same as an empty query. The full `get_folder_children` recursion is the only way to see the whole tree for a pure date-based sweep.

## Present the result, then actively offer to save it

A summary card with: summary, cutoff date and threshold used, counts (flagged vs. total scanned), top items (name, path, last-modified, link), coverage (scanned vs. truncated), warnings (legal hold caveat, truncation).

**Do not stop there and wait.** End the result by explicitly asking, e.g.: *"Want me to save this as a CSV + PDF report to `My Folder/Agents/Retention Sweeper/`?"* Don't make the user remember to separately ask for an export — offer it every time, as part of the same response.

## If confirmed, write the report

Read `../report-export/SKILL.md` and follow its destination convention, disclaimer, and confirm-before-write rules exactly. Default agent name for the folder convention: "Retention Sweeper".

1. Confirm the destination folder (default `My Folder/Agents/Retention Sweeper/`, or user-specified) and whether the CSV should contain only past-retention items or the full scanned set with a flag column, if not already clear.
2. Write the CSV with columns: name, path, last-modified date, threshold applied, past-retention (yes/no), Kiteworks link.
3. Write the txt/pdf narrative: cutoff date and threshold used, counts, top flagged items, coverage/truncation caveats, and the standard disclaimer verbatim.
4. Report back the file names/links created.

Never move, rename, or delete the flagged files themselves — this agent's only write action is creating the report files. If asked to also relocate or delete flagged files, decline and explain that's out of scope by design (legal-hold/retention-policy risk makes touching the files themselves out of scope here, unlike Duplicate Finder).
