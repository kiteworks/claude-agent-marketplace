# Changelog

## 0.6.5 — 2026-09-25

Maintenance release: reliability improvements. <!-- whats-new: consolidated -->

- changed: agents/offboarding-content-finder-apply.md
- changed: agents/offboarding-content-finder-preview.md
- changed: skills/folder-scan/SKILL.md
- changed: skills/offboarding-content-finder-apply/SKILL.md
- changed: skills/offboarding-content-finder-preview/SKILL.md
- changed: skills/scratch-lifecycle/SKILL.md
- changed: skills/scratch-lifecycle/scripts/scratch_lifecycle.py
- changed: skills/surface-gate/SKILL.md

## 0.6.4 — 2026-09-24

Clarifies how documents are read and which Kiteworks tools each step uses. <!-- whats-new: consolidated -->

- changed: skills/report-export/SKILL.md

## 0.6.3 — 2026-09-24

Checks which Kiteworks account it is connected to without being interrupted and cleans up its temporary local files at the end of each run. <!-- whats-new: consolidated -->

- changed: hooks/allowlist.json
- changed: skills/connector-probe/SKILL.md
- changed: skills/folder-scan/SKILL.md
- changed: skills/scratch-lifecycle/SKILL.md
- changed: skills/scratch-lifecycle/scripts/scratch_lifecycle.py

## 0.6.2 — 2026-09-24

Maintenance release: internal skill metadata cleanup. <!-- whats-new: consolidated -->

- changed: agents/offboarding-content-finder-apply.md
- changed: agents/offboarding-content-finder-preview.md

## 0.6.1 — 2026-09-23

Treats files whose security scan is still running as "scan pending" instead of unreadable, and paces Kiteworks calls so large folders finish <!-- whats-new: consolidated -->

- changed: agents/offboarding-content-finder-preview.md
- changed: skills/folder-scan/SKILL.md

## 0.6.0 — 2026-09-20

Ensure it works with any Kiteworks connector name and explains what it can and cannot do over your connection <!-- whats-new: consolidated -->

- added: hooks/allowlist.json
- added: hooks/hooks.json
- added: hooks/kw-allowlist.sh
- added: skills/connector-probe/SKILL.md
- changed: agents/offboarding-content-finder-apply.md
- changed: agents/offboarding-content-finder-preview.md
- changed: skills/folder-scan/SKILL.md
- changed: skills/kw-pdf-report/SKILL.md
- changed: skills/report-export/SKILL.md

## 0.5.5 — 2026-09-14

updated 1 file(s) <!-- whats-new: consolidated -->

- changed: skills/folder-scan/SKILL.md

## 0.5.4 — 2026-09-09

Own temporary document artifacts, honor cleanup permissions, and report residual files accurately.

- added: skills/scratch-lifecycle/SKILL.md
- added: skills/scratch-lifecycle/scripts/scratch_lifecycle.py
- changed: skills/report-export/SKILL.md
- changed: skills/surface-gate/SKILL.md

## 0.5.3 — 2026-09-07

Republished from the current source. The agent now states the marketplace terms acceptance line at the start of a session, and the bundle carries the current terms (version 2.0, effective 2026-08-15) instead of the superseded 1.0 install disclaimer. No change to what the agent does. <!-- whats-new: consolidated -->

- changed: README.md
- changed: agents/offboarding-content-finder-apply.md
- changed: agents/offboarding-content-finder-preview.md
- changed: skills/kw-pdf-report/scripts/branded_pdf.py
- changed: skills/report-export/SKILL.md

## 0.5.2 — 2026-08-01

Restores instructions that were cut off mid-sentence: the agent now matches people by the actual creator/user field on each item, checking both name and email case-insensitively and never using folder or file naming as a proxy for ownership, and reports which field matched alongside coverage and warnings.

- changed: skills/folder-scan/SKILL.md
- changed: skills/kw-pdf-report/SKILL.md
- changed: skills/kw-pdf-report/scripts/branded_pdf.py
- changed: skills/offboarding-content-finder-preview/SKILL.md
- changed: skills/report-export/SKILL.md

## 0.5.1 — 2026-07-15

Refreshed the branded report and the safety pre-check.

- changed: skills/kw-pdf-report/scripts/branded_pdf.py
- changed: skills/surface-gate/SKILL.md

## 0.5.0 — 2026-07-14

Improved the move/apply step and refreshed report export.

- changed: agents/offboarding-content-finder-apply.md
- changed: skills/kw-pdf-report/SKILL.md
- changed: skills/kw-pdf-report/scripts/branded_pdf.py
- changed: skills/offboarding-content-finder-apply/SKILL.md
- changed: skills/report-export/SKILL.md

## 0.4.0 — 2026-07-13

Finds everything a departing or transferring employee owns across Kiteworks and moves confirmed items to a holding folder — clean, auditable offboarding handovers.

- added: README.md
- added: agents/offboarding-content-finder-apply.md
- added: agents/offboarding-content-finder-preview.md
- added: skills/folder-scan/SKILL.md
- added: skills/kw-pdf-report/SKILL.md
- added: skills/kw-pdf-report/assets/hero-bg.png
- added: skills/kw-pdf-report/assets/kw-logo-white.png
- added: skills/kw-pdf-report/scripts/branded_pdf.py
- added: skills/offboarding-content-finder-apply/SKILL.md
- added: skills/offboarding-content-finder-preview/SKILL.md
- added: skills/report-export/SKILL.md
- added: skills/surface-gate/SKILL.md
