# Changelog

## 0.5.4 — 2026-09-14

updated 1 file(s)

- changed: skills/folder-scan/SKILL.md

## 0.5.3 — 2026-09-09

Own temporary document artifacts, honor cleanup permissions, and report residual files accurately.

- added: skills/content-extract/scripts/scratch_lifecycle.py
- added: skills/scratch-lifecycle/SKILL.md
- added: skills/scratch-lifecycle/scripts/scratch_lifecycle.py
- changed: skills/content-extract/SKILL.md
- changed: skills/content-extract/scripts/extract_and_cleanup.py
- changed: skills/content-extract/scripts/scrub.py
- changed: skills/redactor-apply/SKILL.md
- changed: skills/report-export/SKILL.md
- changed: skills/surface-gate/SKILL.md
- changed: skills/term-sweep/SKILL.md

## 0.5.2 — 2026-09-07

Republished from the current source. The agent now states the marketplace terms acceptance line at the start of a session, and the bundle carries the current terms (version 2.0, effective 2026-08-15) instead of the superseded 1.0 install disclaimer. No change to what the agent does. <!-- whats-new: consolidated -->

- changed: README.md
- changed: agents/redactor-apply.md
- changed: agents/redactor-preview.md
- changed: skills/content-extract/SKILL.md
- changed: skills/content-extract/scripts/extract_and_cleanup.py
- changed: skills/content-extract/scripts/scrub.py
- changed: skills/kw-pdf-report/scripts/branded_pdf.py
- changed: skills/report-export/SKILL.md

## 0.5.1 — 2026-07-15

Improved the redaction preview and term matching; refreshed the branded report and safety pre-check.

- changed: skills/kw-pdf-report/scripts/branded_pdf.py
- changed: skills/redactor-preview/SKILL.md
- changed: skills/surface-gate/SKILL.md
- changed: skills/term-sweep/SKILL.md
- changed: skills/term-sweep/scripts/pii_patterns.py

## 0.5.0 — 2026-07-14

Improved content extraction and the redaction apply step; refreshed report export.

- changed: skills/content-extract/SKILL.md
- changed: skills/kw-pdf-report/SKILL.md
- changed: skills/kw-pdf-report/scripts/branded_pdf.py
- changed: skills/redactor-apply/SKILL.md
- changed: skills/report-export/SKILL.md

## 0.4.0 — 2026-07-13

Finds and replaces sensitive text across documents in a Kiteworks folder and writes redacted copies on approval — originals are never touched, so you can share safely.

- added: README.md
- added: agents/redactor-apply.md
- added: agents/redactor-preview.md
- added: skills/content-extract/SKILL.md
- added: skills/folder-scan/SKILL.md
- added: skills/kw-pdf-report/SKILL.md
- added: skills/kw-pdf-report/assets/hero-bg.png
- added: skills/kw-pdf-report/assets/kw-logo-white.png
- added: skills/kw-pdf-report/scripts/branded_pdf.py
- added: skills/redactor-apply/SKILL.md
- added: skills/redactor-preview/SKILL.md
- added: skills/report-export/SKILL.md
- added: skills/surface-gate/SKILL.md
- added: skills/term-sweep/SKILL.md
- added: skills/term-sweep/scripts/pii_patterns.py
