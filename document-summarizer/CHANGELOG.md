# Changelog

## 0.6.5 — 2026-09-25

Maintenance release: reliability improvements. <!-- whats-new: consolidated -->

- changed: agents/document-summarizer.md
- changed: skills/content-extract/SKILL.md
- changed: skills/content-extract/scripts/extract_and_cleanup.py
- changed: skills/content-extract/scripts/scratch_lifecycle.py
- changed: skills/document-summarizer/SKILL.md
- changed: skills/scratch-lifecycle/SKILL.md
- changed: skills/scratch-lifecycle/scripts/scratch_lifecycle.py
- changed: skills/surface-gate/SKILL.md

## 0.6.4 — 2026-09-24

Reads PowerPoint speaker notes and grouped shapes when summarizing slide decks, and can find the destination folder when saving a summary. <!-- whats-new: consolidated -->

- changed: hooks/allowlist.json
- changed: skills/content-extract/SKILL.md
- changed: skills/content-extract/scripts/extract_and_cleanup.py
- changed: skills/report-export/SKILL.md

## 0.6.3 — 2026-09-24

Reads spreadsheets and Word document titles reliably and deletes its temporary local copies when it finishes. <!-- whats-new: consolidated -->

- changed: skills/connector-probe/SKILL.md
- changed: skills/content-extract/SKILL.md
- changed: skills/content-extract/scripts/extract_and_cleanup.py
- changed: skills/content-extract/scripts/scratch_lifecycle.py
- changed: skills/scratch-lifecycle/SKILL.md
- changed: skills/scratch-lifecycle/scripts/scratch_lifecycle.py

## 0.6.2 — 2026-09-24

Maintenance release: internal skill metadata cleanup. <!-- whats-new: consolidated -->

- changed: agents/document-summarizer.md

## 0.6.1 — 2026-09-23

Treats files whose security scan is still running as "scan pending" instead of unreadable, and paces Kiteworks calls so large folders finish <!-- whats-new: consolidated -->

- changed: skills/content-extract/SKILL.md
- changed: skills/document-summarizer/SKILL.md

## 0.6.0 — 2026-09-20

Ensure it works with any Kiteworks connector name and explains what it can and cannot do over your connection <!-- whats-new: consolidated -->

- added: hooks/allowlist.json
- added: hooks/hooks.json
- added: hooks/kw-allowlist.sh
- added: skills/connector-probe/SKILL.md
- changed: agents/document-summarizer.md
- changed: skills/content-extract/SKILL.md
- changed: skills/kw-pdf-report/SKILL.md
- changed: skills/report-export/SKILL.md

## 0.5.3 — 2026-09-09

Own temporary document artifacts, honor cleanup permissions, and report residual files accurately.

- added: skills/content-extract/scripts/scratch_lifecycle.py
- added: skills/scratch-lifecycle/SKILL.md
- added: skills/scratch-lifecycle/scripts/scratch_lifecycle.py
- changed: skills/content-extract/SKILL.md
- changed: skills/content-extract/scripts/extract_and_cleanup.py
- changed: skills/content-extract/scripts/scrub.py
- changed: skills/document-summarizer/SKILL.md
- changed: skills/report-export/SKILL.md
- changed: skills/surface-gate/SKILL.md

## 0.5.2 — 2026-09-07

Republished from the current source. The agent now states the marketplace terms acceptance line at the start of a session, and the bundle carries the current terms (version 2.0, effective 2026-08-15) instead of the superseded 1.0 install disclaimer. No change to what the agent does. <!-- whats-new: consolidated -->

- changed: README.md
- changed: agents/document-summarizer.md
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

Major update: virus/DLP pre-checks before summarizing, PII-safe summaries that never echo IDs verbatim, wider file-type extraction, and a branded PDF report.

- added: agents/document-summarizer.md
- added: skills/content-extract/SKILL.md
- added: skills/document-summarizer/SKILL.md
- added: skills/kw-pdf-report/SKILL.md
- added: skills/kw-pdf-report/assets/hero-bg.png
- added: skills/kw-pdf-report/assets/kw-logo-white.png
- added: skills/kw-pdf-report/scripts/branded_pdf.py
- added: skills/report-export/SKILL.md
- added: skills/surface-gate/SKILL.md
- changed: .claude-plugin/plugin.json
- changed: README.md
- removed: skills/kw-binary-file-bridge/SKILL.md
- removed: skills/kw-document-summarizer/SKILL.md

## 0.2.0 — 2026-07-09

added 4 file(s)

- added: .claude-plugin/plugin.json
- added: README.md
- added: skills/kw-binary-file-bridge/SKILL.md
- added: skills/kw-document-summarizer/SKILL.md
