# Changelog

## 1.1.1 — 2026-09-23

Treats files whose security scan is still running as "scan pending" instead of unreadable, and paces Kiteworks calls so large folders finish <!-- whats-new: consolidated -->

- changed: skills/content-extract/SKILL.md
- changed: skills/folder-scan/SKILL.md

## 1.1.0 — 2026-09-20

Ensure it works with any Kiteworks connector name and explains what it can and cannot do over your connection <!-- whats-new: consolidated -->

- added: hooks/allowlist.json
- added: hooks/hooks.json
- added: hooks/kw-allowlist.sh
- added: skills/connector-probe/SKILL.md
- changed: agents/contract-radar.md
- changed: skills/content-extract/SKILL.md
- changed: skills/folder-scan/SKILL.md
- changed: skills/kw-pdf-report/SKILL.md
- changed: skills/report-export/SKILL.md

## 1.0.7 — 2026-09-14

updated 1 file(s) <!-- whats-new: consolidated -->

- changed: skills/folder-scan/SKILL.md

## 1.0.6 — 2026-09-09

Own temporary document artifacts, honor cleanup permissions, and report residual files accurately.

- added: skills/content-extract/scripts/scratch_lifecycle.py
- added: skills/scratch-lifecycle/SKILL.md
- added: skills/scratch-lifecycle/scripts/scratch_lifecycle.py
- changed: skills/content-extract/SKILL.md
- changed: skills/content-extract/scripts/extract_and_cleanup.py
- changed: skills/content-extract/scripts/scrub.py
- changed: skills/report-export/SKILL.md
- changed: skills/surface-gate/SKILL.md
- changed: skills/term-sweep/SKILL.md

## 1.0.5 — 2026-09-07

Republished from the current source. The agent now states the marketplace terms acceptance line at the start of a session, and the bundle carries the current terms (version 2.0, effective 2026-08-15) instead of the superseded 1.0 install disclaimer. No change to what the agent does. <!-- whats-new: consolidated -->

- changed: README.md
- changed: agents/contract-radar.md
- changed: skills/content-extract/SKILL.md
- changed: skills/content-extract/scripts/extract_and_cleanup.py
- changed: skills/content-extract/scripts/scrub.py
- changed: skills/kw-pdf-report/scripts/branded_pdf.py
- changed: skills/report-export/SKILL.md

## 1.0.4 — 2026-07-15

Refined contract and renewal term matching; refreshed the branded report and safety pre-check.

- changed: skills/kw-pdf-report/scripts/branded_pdf.py
- changed: skills/surface-gate/SKILL.md
- changed: skills/term-sweep/SKILL.md
- changed: skills/term-sweep/scripts/pii_patterns.py

## 1.0.3 — 2026-07-14

Improved contract and renewal extraction and refreshed the branded PDF report.

- changed: agents/contract-radar.md
- changed: skills/content-extract/SKILL.md
- changed: skills/contract-radar/SKILL.md
- changed: skills/kw-pdf-report/SKILL.md
- changed: skills/kw-pdf-report/scripts/branded_pdf.py
- changed: skills/report-export/SKILL.md

## 1.0.1 — 2026-07-13

Surfaces contracts, agreements, and upcoming renewals buried in a Kiteworks folder and reports them in one place, so renewal deadlines stop slipping through the cracks.

- added: README.md
- added: agents/contract-radar.md
- added: skills/content-extract/SKILL.md
- added: skills/contract-radar/SKILL.md
- added: skills/folder-scan/SKILL.md
- added: skills/kw-pdf-report/SKILL.md
- added: skills/kw-pdf-report/assets/hero-bg.png
- added: skills/kw-pdf-report/assets/kw-logo-white.png
- added: skills/kw-pdf-report/scripts/branded_pdf.py
- added: skills/report-export/SKILL.md
- added: skills/surface-gate/SKILL.md
- added: skills/term-sweep/SKILL.md
- added: skills/term-sweep/scripts/pii_patterns.py
