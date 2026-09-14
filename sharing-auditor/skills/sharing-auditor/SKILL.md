---
name: sharing-auditor
description: >
  Use when the user asks what's shared or exposed in Kiteworks — trigger
  phrases include "what's shared in X folder," "find files and folders
  exposed through sharing," "sharing audit," or "what's exposed outside my team." Scans
  and, on confirmation, writes a CSV + txt/pdf report. Single-phase: no
  separate "apply" step to ask for.
metadata:
  version: "1.1.0"
---

On surfaces that support plugin subagents, delegate to the `sharing-auditor` subagent. If it reports no tools or fabricates results without tool calls, discard and check the `Kiteworks` connector.

# Sharing Auditor

Read `../folder-scan/SKILL.md` and `../sharing-exposure/SKILL.md` first. Confirmed live: folder records from `get_top_folders`/`get_folder_children` carry `isShared` (only when true; files never carry it, and it cascades to every subfolder), so resolve the scan root's own flag and share origin per `sharing-exposure` before walking. Do not rely on `search_filter: 'shared'` with no term (confirmed to return nothing unscoped).

## Why this is one phase, not two

This agent never changes sharing settings (no such tool exists) and never touches flagged items — its only write action is a CSV + txt/pdf report. That doesn't need a separate confirmation gate as its own skill; it's folded into one scan-then-offer-to-save flow.

## Collect from the user

A folder scope (required). Optionally: whether to include subfolders recursively (default yes, bounded per `folder-scan`).

## Walk and flag

First read the scan root's flag and, if it is shared, resolve the share origin (`sharing-exposure` steps 1 and 2). Then walk with `get_folder_children` and apply its step 3: report one finding per share origin with the counts of files and subfolders that inherit; files inherit their folder and are never judged from a missing field. Cross-reference item names against any sensitive-sounding terms the user cares about (optional; if given, flag matches as higher priority) but do not require a term list — the core value here is just surfacing what's shared at all.

## Present the result, then actively offer to save it

Summary card: summary, counts (items exposed vs. items seen), share origins with name/path/link/creator, coverage, warnings (this reports folder-level sharing *state*; it cannot see who has access or whether they are internal or external, and directly shared files are not detected; whether the exposure is appropriate is the user's judgment). Include the sharing-context Scope lines from `sharing-exposure` (Sharing context always; Share origin only when the root is shared; Members always).

**Do not stop there and wait.** End by explicitly asking, e.g.: *"Want me to save this as a CSV + PDF report to `My Folder/Agents/Sharing Auditor/`?"*

## If confirmed, write the report

Read `../report-export/SKILL.md` and follow it exactly. Default agent name: "Sharing Auditor".

Write the CSV (name, path, exposure_source, share_origin, origin_depth, inherited_files, inherited_folders, creator, link), one row per share origin, and the txt/pdf narrative (counts, share origins, coverage, disclaimer verbatim). Never change sharing settings or touch flagged items — this agent's only write action is the report files.
