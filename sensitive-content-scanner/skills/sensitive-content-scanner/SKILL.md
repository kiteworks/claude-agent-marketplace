---
name: sensitive-content-scanner
description: >
  Use when the user wants to sweep a Kiteworks folder for sensitive
  terms — trigger phrases include "scan for sensitive content in X,"
  "find files mentioning [term]," or "sensitive content scan." Asks up front which report to save (CSV, PDF, TXT, or none), then scans and writes it. Single-phase: no
  separate "apply" step to ask for.
metadata:
  version: "1.3.0"
---

**Before anything else, run the report preflight** (`../report-export/SKILL.md`): ask the user which report to save — CSV, PDF, TXT, or no saved report (one multi-select question, with `AskUserQuestion` where the host has it) — and confirm the destination (default `My Folder/Agents/Sensitive Content Scanner/`). Pass the answer to the subagent as the `Report preflight` block. The subagent cannot ask the user anything itself, so a save question asked after the scan deadlocks. In the same question, ask whether to also run the content deep scan (a download and parse per candidate file, capped per run) and pass it as `- deep_scan: yes` or `- deep_scan: no` in the block.

Delegate to the `sensitive-content-scanner` subagent. If you already are that subagent, do not delegate again: follow this skill directly. Read `../term-sweep/SKILL.md` first — it has the confirmed caveat about `content_contains` reliability; do not skip it.

# Sensitive Content Scanner

## Why this is one phase, not two

This agent never touches flagged files — its only write action is a CSV + txt/pdf report. A separate apply skill didn't protect against anything real, so scanning and saving (in the formats the user picked before the run) are now one flow, one agent.

## Collect from the user

A folder scope (required) and a term list (required — never assume a default list; sensitivity vocabulary is organization-specific, e.g. "confidential", "SSN", "ITAR", a client name).

## Sweep

Always run the name/path match per `term-sweep` — metadata only, always on. It matches each term against the full `path` of every walked item, so a file inside a folder named for the term (e.g. `Confidential/`) is flagged even when its own name is neutral; `search_files(path_contains=...)` alone matches file names only and would miss it.

Content matching is a separate, opt-in "deep scan": it is real per-file work (it's real per-file work — a download and parse per candidate file, per `../content-extract/SKILL.md`), so the user decides in the report preflight, before the run (`deep_scan: yes` or `no`). Run it only on yes, and tell them how many files were in scope vs. actually checked. Respect `content-extract`'s per-run cap and disclose how many files were actually checked vs. in scope. Count the terms in each extracted text only with `../term-sweep/scripts/pii_patterns.py <extracted-text-file> --terms-file=<user-terms.txt>`, per `term-sweep`'s "Counting terms in extracted text"; never count them yourself.

## Built-in PII/secret pattern presets — all run by default

This is what makes this agent an actual *sensitive-content* scanner rather than just a keyword search the user has to fully configure themselves. Whenever the content deep-scan runs, also run `../term-sweep/SKILL.md`'s built-in pattern presets (`scripts/pii_patterns.py`) against the same extracted text with `--framework=sensitive-content-scanner`, alongside whatever custom terms the user gave. **Every general built-in category runs by default**, and the flag adds the plaintext-credential preset (`password = <value>`-style assignments, placeholder values excluded) — mention once, briefly, that this happens and that it can be turned off if the user only wants their own term list; don't ask them to pick categories up front or single out any one category (e.g. a country-specific one) as needing special permission.

**Keep the narration terse.** Don't preamble-list every category before running (per `term-sweep`'s presentation rule). In the summary card, name only the categories that actually got a hit, plus a one-line total count of categories checked. The full per-category breakdown — including zero-hit categories — goes into the exported report, not the chat turn. If the user asks what's checked, or wants to scan for a narrower subset (e.g. "just financial patterns," or by region), offer `term-sweep`'s tag-based `--categories` selector (`region:<value>`, `type:<value>`, exact category names, or `all`). The privacy-framework-gated presets (Aadhaar, CPF/CNPJ, Vietnamese CCCD, email, lat/lon) do not run by default here; select them by exact name if the user asks for them — but only when they ask or it's clearly useful, not as a standing question before every scan.

Each category also carries a `context_confirmed` count alongside its raw `valid` count — whether a relevant keyword (e.g. "BSN," "SSN," "IBAN," "card number") appeared within 60 characters of the match. A shape/checksum-valid match with no nearby keyword still counts as a hit (real PII is often unlabeled), but report both numbers so the user can see how many hits also have contextual support, not just checksum validity.

## Custom regex — for anything the built-in categories don't cover

If the user has their own pattern in mind (an internal ID shape, a partner account number, anything with a defined structure), ask for the regex, a label, and optionally context keywords, and run it through `term-sweep`'s custom regex mode (`scripts/pii_patterns.py`'s second, optional argument) alongside whatever else is running. A bad regex or a pathological one is reported as a per-pattern error, not a crash — surface that plainly if it happens rather than silently dropping the pattern.

## Present the result, then save the chosen report

Summary card: summary, term list used, name-match hits, whether a content deep-scan ran and its hits if so (or "not run — ask to include a content scan" if the preflight said `deep_scan: no`), how many built-in pattern categories were checked with which ones (if any) were flagged (name the hits, not the whole list), coverage, warnings.

Then write the formats from the report preflight without asking again, and list what was saved (file names, links). With `formats: none`, end with the results only.

## Write the report the preflight selected

Read `../report-export/SKILL.md`. Default agent name: "Sensitive Content Scanner". Never touches flagged files, never prints matched text or matched pattern values (per `term-sweep`), and the report must repeat the content-search reliability caveat.

Write CSV (name, path, term or pattern-category matched, match type name/custom-content/built-in-pattern, link) and txt/pdf narrative including the caveat verbatim. State every built-in category that was checked, with both its `valid` and `context_confirmed` counts, even for the ones with zero hits — a clean result is itself useful information in the saved report, even though the chat summary only names the flagged ones.

## Executive report record

For saved reports, the version 2 contract in the shared report-export and
kw-pdf-report skills supersedes older table/metadata layout examples here.
Use profile `sensitive-content` and document_kind: assessment; read the profile-specific
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

For this plugin specifically:

- Add one `fact_keys` entry per pattern category, including checked
  categories with zero hits, so zeros are recorded as checked rather than
  omitted.
- Do not write a name-match narrative and a content-match narrative for the
  same file; one finding per theme covers both.
- A finding names only the categories that actually matched.
