---
name: contract-radar
description: >
  Use when the user wants to find contracts, agreements, or renewal-related
  documents in Kiteworks — trigger phrases include "find our contracts in
  X," "what agreements are in this folder," "contract radar," or "flag
  anything renewal-related." Asks up front which report to save (CSV, PDF, TXT, or none), then scans and writes it. Single-phase: no separate "apply" step to ask for.
metadata:
  version: "1.0.3"
---

**Before anything else, run the report preflight** (`../report-export/SKILL.md`): ask the user which report to save — CSV, PDF, TXT, or no saved report (one multi-select question, with `AskUserQuestion` where the host has it) — and confirm the destination (default `My Folder/Agents/Contract Radar/`). Pass the answer to the subagent as the `Report preflight` block. The subagent cannot ask the user anything itself, so a save question asked after the scan deadlocks. In the same question, ask whether to also run the content deep scan (a download and parse per candidate file, capped per run) and pass it as `- deep_scan: yes` or `- deep_scan: no` in the block.

Delegate to the `contract-radar` subagent. If you already are that subagent, do not delegate again: follow this skill directly. Read `../folder-scan/SKILL.md` first, and `../term-sweep/SKILL.md` if a content deep-scan is confirmed.

# Contract Radar

## Why this is one phase, not two

This agent never touches candidate files — its only write action is a CSV + txt/pdf report. Folded into one scan-then-offer-to-save flow rather than a separate apply skill.

## Collect from the user

A folder scope (required). Term list is optional — default to `agreement, MSA, SOW, NDA, contract, renewal` if the user doesn't give one, but say so explicitly so they can override it.

## Sweep

Name/path match against the term list per `term-sweep`, always on. Folder names in each item's path count, so a file under a `Contracts/` folder matches "contract" even when its own name does not; `search_files(path_contains=...)` alone would miss it, because it matches file names only. Surface `modified`/`created` dates on every candidate — contract radar is inherently about staleness/renewal timing, so dates matter even before any content check.

Content matching is a separate, opt-in "deep scan" (real per-file work — a download and parse per candidate, per `../content-extract/SKILL.md`): the user decides in the report preflight, before the run (`deep_scan: yes` or `no`). Run it only on yes, and tell them how many candidates were in scope vs. actually checked. Respect `content-extract`'s per-run cap and disclose how many files were actually checked vs. in scope. Count the terms in each extracted text only with `../term-sweep/scripts/pii_patterns.py <extracted-text-file> --terms-file=<user-terms.txt>`, per `term-sweep`'s "Counting terms in extracted text"; never count them yourself.

## Present the result, then save the chosen report

Summary card: summary, term list used (and whether it was the default), name-match hits with last-modified dates, whether a content deep-scan ran and its hits if so, coverage, warnings — including that this is a **candidate list, not a verified inventory of active contracts** (a name/date match doesn't confirm the document is actually a current, executed agreement).

Then write the formats from the report preflight without asking again, and list what was saved (file names, links). With `formats: none`, end with the results only.

## Write the report the preflight selected

Read `../report-export/SKILL.md`. Default agent name: "Contract Radar".

Write CSV (name, path, term matched, last modified, link) and txt/pdf narrative including both caveats verbatim: the candidate-list-not-verified caveat above, and (if a content deep-scan ran) the content-search reliability caveat from `term-sweep`. Never touch candidate files — this agent's only write action is the report itself.

## Executive report record

For saved reports, the version 2 contract in the shared report-export and
kw-pdf-report skills supersedes older table/metadata layout examples here.
Use profile `contracts` and document_kind: assessment; read the profile-specific
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
