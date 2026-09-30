---
name: storage-visualizer
description: >
  Use when the user asks to scan or summarize Kiteworks storage — trigger
  phrases include "scan my Kiteworks storage," "what's using the most
  space in X," "storage totals for [folder]," or "biggest folders/files
  in Kiteworks." Asks up front which report to save (CSV, PDF, TXT, or none), then scans and writes it. Single-phase: no separate "apply" step to ask for.
metadata:
  version: "1.0.2"
---

**Before anything else, run the report preflight** (`../report-export/SKILL.md`): ask the user which report to save — CSV, PDF, TXT, or no saved report (one multi-select question, with `AskUserQuestion` where the host has it) — and confirm the destination (default `My Folder/Agents/Storage Visualizer/`). Pass the answer to the subagent as the `Report preflight` block. The subagent cannot ask the user anything itself, so a save question asked after the scan deadlocks.

On surfaces that support plugin subagents, delegate to the `storage-visualizer` subagent. If it reports no tools available, or returns results without making any Kiteworks tool calls, treat the result as fabricated, discard it, and ask the user to check the `Kiteworks` connector is connected.

# Storage Visualizer

Read `../folder-scan/SKILL.md` first and follow its rules.

Productivity-grade helper, not the audited compliance runtime.

## Why this is one phase, not two

The only possible write action here is a CSV + txt/pdf report — nothing scanned is ever touched. A separate apply step doesn't protect against anything, so this is a single scan-then-offer-to-save flow: still asks before writing, just without a second named skill/agent.

## Collect from the user

A root scope: a folder (default to "My Folder" if unspecified, resolved per `folder-scan`'s gotcha) or `root_id`/`root_path`. Optional: whether to include deleted items.

## Walk and aggregate

Use `get_folder_children` recursion (storage totals need every item, not a date-filtered subset — this is one of the agents in this plugin that needs the full walk). Respect the bounded-walk limits from `folder-scan`. While walking, also collect: `isShared` counts (how much of the scanned storage is shared), and largest individual files/folders by size.

## Present the result, then save the chosen report

Summary card with: summary, totals (item count, total size), top items (largest files and folders, with links), a shared-vs-not-shared size breakdown (a free byproduct of the walk, genuinely useful for a platform built around secure sharing), coverage, warnings.

Then write the formats from the report preflight without asking again, and list what was saved (file names, links). With `formats: none`, end with the results only.

## Write the report the preflight selected

Read `../report-export/SKILL.md` first and follow it exactly. Default agent name for the folder convention: "Storage Visualizer".

1. Use the formats and destination from the report preflight. The CSV holds every scanned item, with size/shared columns.
2. Write the CSV: name, path, type, size, isShared, Kiteworks link.
3. Write the txt/pdf narrative: totals, top items, shared-vs-not breakdown, coverage/truncation caveats, disclaimer verbatim.
4. Report back file names/links created.

Never touch scanned files or folders themselves — this agent's only write action is creating the report files.
