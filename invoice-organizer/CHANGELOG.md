# Changelog

## 0.6.0 — 2026-09-20

Ensure it works with any Kiteworks connector name and explains what it can and cannot do over your connection <!-- whats-new: consolidated -->

- added: hooks/allowlist.json
- added: hooks/hooks.json
- added: hooks/kw-allowlist.sh
- added: skills/connector-probe/SKILL.md
- changed: agents/invoice-organizer-apply.md
- changed: agents/invoice-organizer-preview.md
- changed: skills/content-extract/SKILL.md
- changed: skills/folder-scan/SKILL.md
- changed: skills/kw-pdf-report/SKILL.md
- changed: skills/report-export/SKILL.md

## 0.5.4 — 2026-09-14

updated 1 file(s) <!-- whats-new: consolidated -->

- changed: skills/folder-scan/SKILL.md

## 0.5.3 — 2026-09-09

Own temporary document artifacts, honor cleanup permissions, and report residual files accurately.

- added: skills/content-extract/scripts/scratch_lifecycle.py
- added: skills/scratch-lifecycle/SKILL.md
- added: skills/scratch-lifecycle/scripts/scratch_lifecycle.py
- changed: skills/content-extract/SKILL.md
- changed: skills/content-extract/scripts/extract_and_cleanup.py
- changed: skills/content-extract/scripts/scrub.py
- changed: skills/invoice-organizer-preview/SKILL.md
- changed: skills/invoice-organizer-preview/scripts/ocr_extract.py
- changed: skills/report-export/SKILL.md
- changed: skills/surface-gate/SKILL.md

## 0.5.2 — 2026-09-07

Republished from the current source. The agent now states the marketplace terms acceptance line at the start of a session, and the bundle carries the current terms (version 2.0, effective 2026-08-15) instead of the superseded 1.0 install disclaimer. No change to what the agent does. <!-- whats-new: consolidated -->

- changed: README.md
- changed: agents/invoice-organizer-apply.md
- changed: agents/invoice-organizer-preview.md
- changed: skills/content-extract/SKILL.md
- changed: skills/content-extract/scripts/extract_and_cleanup.py
- changed: skills/content-extract/scripts/scrub.py
- changed: skills/kw-pdf-report/scripts/branded_pdf.py
- changed: skills/report-export/SKILL.md

## 0.5.1 — 2026-07-15

Refreshed the branded report and the safety pre-check.

- changed: skills/kw-pdf-report/scripts/branded_pdf.py
- changed: skills/surface-gate/SKILL.md

## 0.5.0 — 2026-07-14

Finds invoices and receipts (including photos and scans) in a Kiteworks folder, extracts vendor, date, amount, and tax, and — on your approval — renames them consistently and builds a categorized spreadsheet for expenses or taxes.

- added: README.md
- added: agents/invoice-organizer-apply.md
- added: agents/invoice-organizer-preview.md
- added: skills/content-extract/SKILL.md
- added: skills/folder-scan/SKILL.md
- added: skills/invoice-organizer-apply/SKILL.md
- added: skills/invoice-organizer-preview/SKILL.md
- added: skills/invoice-organizer-preview/scripts/mask_sensitive_numbers.py
- added: skills/invoice-organizer-preview/scripts/ocr_extract.py
- added: skills/kw-pdf-report/SKILL.md
- added: skills/kw-pdf-report/assets/hero-bg.png
- added: skills/kw-pdf-report/assets/kw-logo-white.png
- added: skills/kw-pdf-report/scripts/branded_pdf.py
- added: skills/report-export/SKILL.md
- added: skills/surface-gate/SKILL.md
