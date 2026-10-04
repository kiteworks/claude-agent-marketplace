---
name: offboarding-content-finder-apply
description: >
  Use when the user has confirmed which owned items to stage for
  reassignment — trigger phrases include "move their files to a
  holding folder" or "stage that for reassignment."
metadata:
  version: "0.1.0"
---

Delegate to the `offboarding-content-finder-apply` subagent, passing only user-confirmed items and destination. If you already are that subagent, do not delegate again: follow this skill directly. Read `../report-export/SKILL.md`.

# Offboarding Content Finder — apply

Like Duplicate Finder, this agent relocates rather than deletes: move confirmed items into a holding folder (default `My Folder/Agents/Offboarding Content Finder/<Person Name>/`, or user-specified) using `move_file`/`move_folder`. Never delete. Require confirmation of the item set before moving — this is someone's real work product, treat it carefully.

Since preview now defaults to a tenant-wide sweep, the confirmed item set can span many different top-level folders. Keep the holding folder flat (don't try to recreate each item's original folder structure inside it) — the CSV's original-path column is what preserves where each item came from, not the destination layout.

## Steps

1. Create the holding folder if missing.
2. Move confirmed items into it.
3. Write a CSV (item, original path, new path, was-shared, link) and txt/pdf narrative (who this was for, what moved, where, disclaimer verbatim).
4. Report back plainly: what moved, where, and that the user/team should review and reassign ownership manually — this agent doesn't and can't change file ownership itself (no such tool exists).

## Executive report record

For saved reports, the version 2 contract in the shared report-export and
kw-pdf-report skills supersedes older table/metadata layout examples here.
Use profile `offboarding` and document_kind: receipt; read the profile-specific
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
