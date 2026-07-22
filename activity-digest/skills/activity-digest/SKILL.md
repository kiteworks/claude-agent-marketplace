---
name: activity-digest
description: >
  Use when the user wants a summary of recent activity in a Kiteworks
  folder — trigger phrases include "what's new in X this week," "activity
  digest for [folder]," or "what changed since Monday." Scans and, on
  confirmation, writes a CSV + txt/pdf report. Single-phase: no separate
  "apply" step to ask for.
metadata:
  version: "1.0.2"
---

Delegate to the `activity-digest` subagent. Read `../folder-scan/SKILL.md` first.

# Activity Digest

## Why this is one phase, not two

The only write action here is a CSV + txt/pdf report — nothing scanned is touched. Folded into a single scan-then-offer-to-save flow rather than a separate apply skill.

## Collect from the user

A folder scope (required) and a time window (e.g. "this week," "since last Monday" — convert to an explicit `modified_after` date the same way `retention-sweeper` computes its cutoff, don't leave it fuzzy).

## Scan

Do the bounded `get_folder_children` walk per `folder-scan`, then filter client-side: `modified` after the window start = changed, `created` after the window start = new. **Do not scope this via `search_files`'s `modified_after`/`created_after` alone instead of walking** — confirmed live, a `parent_folder_id` + date-filter-only query (no text term) returns nothing. If the user gives a name pattern too (e.g. "anything with 'draft' changed this week"), `search_files` with `path_contains` + `modified_after` works fine and is recursive — use that instead of walking in that specific case.

## Present the result, then actively offer to save it

Summary card: summary, window used, new items (created_after match), changed items (modified_after match, excluding new), most-active subfolder if discernible, coverage, warnings.

**Do not stop there and wait.** End by explicitly asking, e.g.: *"Want me to save this as a CSV + PDF report to `My Folder/Agents/Activity Digest/`?"*

This skill also pairs naturally with the `schedule` capability for a recurring digest — mention that once, don't set it up unless asked.

## If confirmed, write the report

Read `../report-export/SKILL.md`. Default agent name: "Activity Digest".

Write CSV (item, new/changed, date, link) and txt/pdf narrative (window used, counts, highlights, disclaimer verbatim). Never touch the scanned items themselves.
