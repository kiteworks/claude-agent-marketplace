---
name: naming-cleanup-apply
description: >
  Use when the user has confirmed which renames to apply — trigger
  phrases include "rename those" or "apply the naming cleanup."
metadata:
  version: "0.1.0"
---

Delegate to the `naming-cleanup-apply` subagent, passing only user-confirmed old-name→new-name pairs. If you already are that subagent, do not delegate again: follow this skill directly. Read `../report-export/SKILL.md`.

# Naming Cleanup — apply

Confirmed live: `rename_file` works cleanly (tested renaming a file in place; metadata updated, path reflects new name). Require per-item confirmation before renaming — never bulk-rename an entire flagged list on one blanket "yes."

## Steps

1. For each confirmed item, call `rename_file` (or `rename_folder`) with the confirmed new name.
2. Write a CSV (old name, new name, path, link) and txt/pdf narrative (what was renamed, what was skipped, disclaimer verbatim) into `Agents/Naming Cleanup/` (or user destination).
3. Report back plainly what changed.

## Executive report record

For saved reports, the version 2 contract in the shared report-export and
kw-pdf-report skills supersedes older table/metadata layout examples here.
Use profile `naming` and document_kind: receipt; read the profile-specific
evidence requirements in kw-pdf-report/report-profiles.md. Preserve the full
enumerated population and per-check outcomes, not only flagged items.
Derive authorized PDF, TXT and complete-inventory CSV from that one record.
Explain why findings matter and what decision is needed. Any specialized
detail table remains supporting evidence, never a substitute for the ledger.
Record actions actually completed separately from proposals, failures and
skips, with verification and times. Do not invent missing execution evidence.

### Proposals and receipts

Reports written with `document_kind: proposal` or `receipt` keep their current
per-action format; the assessment rules for `report_mode`, themes and metrics
do not change them. Only an assessment-style report adopts the new rules, as
described in the Assessment contract in the kw-pdf-report SKILL.md.
