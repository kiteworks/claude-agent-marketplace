---
name: activity-digest
description: >
  Use when the user wants a summary of recent activity in a Kiteworks
  folder — trigger phrases include "what's new in X this week," "activity
  digest for [folder]," or "what changed since Monday." Asks up front which report to save (CSV, PDF, TXT, or none), then scans and writes it. Single-phase: no separate
  "apply" step to ask for.
metadata:
  version: "1.0.2"
---

**Before anything else, run the report preflight** (`../report-export/SKILL.md`): ask the user which report to save — CSV, PDF, TXT, or no saved report (one multi-select question, with `AskUserQuestion` where the host has it) — and confirm the destination (default `My Folder/Agents/Activity Digest/`). Pass the answer to the subagent as the `Report preflight` block. The subagent cannot ask the user anything itself, so a save question asked after the scan deadlocks.

Delegate to the `activity-digest` subagent. If you already are that subagent, do not delegate again: follow this skill directly. Read `../folder-scan/SKILL.md` first.

# Activity Digest

## Why this is one phase, not two

The only write action here is a CSV + txt/pdf report — nothing scanned is touched. Folded into a single scan-then-offer-to-save flow rather than a separate apply skill.

## Collect from the user

A folder scope (required) and a time window (e.g. "this week," "since last Monday" — convert to an explicit `modified_after` date the same way `retention-sweeper` computes its cutoff, don't leave it fuzzy).

## Scan

Do the bounded `get_folder_children` walk per `folder-scan`, then filter client-side: `modified` after the window start = changed, `created` after the window start = new. **Do not scope this via `search_files`'s `modified_after`/`created_after` alone instead of walking** — confirmed live, a `parent_folder_id` + date-filter-only query (no text term) returns nothing. If the user gives a name pattern too (e.g. "anything with 'draft' changed this week"), `search_files` with `path_contains` + `modified_after` works fine and is recursive — use that instead of walking in that specific case.

## Present the result, then save the chosen report

Summary card: summary, window used, new items (created_after match), changed items (modified_after match, excluding new), most-active subfolder if discernible, coverage, warnings.

Then write the formats from the report preflight without asking again, and list what was saved (file names, links). With `formats: none`, end with the results only.

This skill also pairs naturally with the `schedule` capability for a recurring digest — mention that once, don't set it up unless asked.

## Write the report the preflight selected

Read `../report-export/SKILL.md`. Default agent name: "Activity Digest".

Write CSV (item, new/changed, date, link) and txt/pdf narrative (window used, counts, highlights, disclaimer verbatim). Never touch the scanned items themselves.

## Executive report record

For saved reports, the version 2 contract in the shared report-export and
kw-pdf-report skills supersedes older table/metadata layout examples here.
Use profile `activity` and document_kind: assessment; read the profile-specific
evidence requirements in kw-pdf-report/report-profiles.md. Preserve the full
enumerated population and per-check outcomes, not only flagged items.
Derive authorized PDF, TXT and complete-inventory CSV from that one record.
Explain why findings matter and what decision is needed. Any specialized
detail table remains supporting evidence, never a substitute for the ledger.
Record actions actually completed separately from proposals, failures and
skips, with verification and times. Do not invent missing execution evidence.

### Assessment rules (new-mode records)

Follow the Assessment contract in the kw-pdf-report SKILL.md; the points that
matter for this plugin are:

- Set `report_mode`: `companion` when both CSV and PDF are authorized (the PDF
  is a short companion to the complete CSV inventory), `compact` for a
  PDF-only request.
- Fill `cover.title` and `cover.scope_label` so the cover names the report and
  the scope actually examined.
- Use the canonical priority values; mark purely informational notes `info`.
- Give every check a `kind`, as the shared contract defines.
- Before writing any prose, run `branded_pdf.py metrics --json-file <record>`
  and quote its figures; do not recompute counts, sizes or percentages by hand.
- Group findings into themes with an affected count instead of listing one
  finding per file; the per-file rows belong in the CSV.
