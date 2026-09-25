# Changelog

## 1.1.5 — 2026-09-25

Maintenance release: reliability improvements. <!-- whats-new: consolidated -->

- changed: agents/activity-digest.md
- changed: skills/activity-digest/SKILL.md
- changed: skills/folder-scan/SKILL.md
- changed: skills/scratch-lifecycle/SKILL.md
- changed: skills/scratch-lifecycle/scripts/scratch_lifecycle.py
- changed: skills/surface-gate/SKILL.md

## 1.1.4 — 2026-09-24

Clarifies how documents are read and which Kiteworks tools each step uses. <!-- whats-new: consolidated -->

- changed: skills/report-export/SKILL.md

## 1.1.3 — 2026-09-24

Checks which Kiteworks account it is connected to without being interrupted and cleans up its temporary local files at the end of each run. <!-- whats-new: consolidated -->

- changed: hooks/allowlist.json
- changed: skills/connector-probe/SKILL.md
- changed: skills/folder-scan/SKILL.md
- changed: skills/scratch-lifecycle/SKILL.md
- changed: skills/scratch-lifecycle/scripts/scratch_lifecycle.py

## 1.1.2 — 2026-09-24

Maintenance release: internal skill metadata cleanup. <!-- whats-new: consolidated -->

- changed: agents/activity-digest.md

## 1.1.1 — 2026-09-23

Treats files whose security scan is still running as "scan pending" instead of unreadable, and paces Kiteworks calls so large folders finish <!-- whats-new: consolidated -->

- changed: skills/folder-scan/SKILL.md

## 1.1.0 — 2026-09-20

Ensure it works with any Kiteworks connector name and explains what it can and cannot do over your connection <!-- whats-new: consolidated -->

- added: hooks/allowlist.json
- added: hooks/hooks.json
- added: hooks/kw-allowlist.sh
- added: skills/connector-probe/SKILL.md
- changed: agents/activity-digest.md
- changed: skills/folder-scan/SKILL.md
- changed: skills/kw-pdf-report/SKILL.md
- changed: skills/report-export/SKILL.md

## 1.0.6 — 2026-09-14

updated 1 file(s) <!-- whats-new: consolidated -->

- changed: skills/folder-scan/SKILL.md

## 1.0.5 — 2026-09-09

Own temporary document artifacts, honor cleanup permissions, and report residual files accurately.

- added: skills/scratch-lifecycle/SKILL.md
- added: skills/scratch-lifecycle/scripts/scratch_lifecycle.py
- changed: skills/report-export/SKILL.md
- changed: skills/surface-gate/SKILL.md

## 1.0.4 — 2026-09-07

Republished from the current source. The agent now states the marketplace terms acceptance line at the start of a session, and the bundle carries the current terms (version 2.0, effective 2026-08-15) instead of the superseded 1.0 install disclaimer. No change to what the agent does. <!-- whats-new: consolidated -->

- changed: README.md
- changed: agents/activity-digest.md
- changed: skills/kw-pdf-report/scripts/branded_pdf.py
- changed: skills/report-export/SKILL.md

## 1.0.3 — 2026-07-15

Refreshed the branded report and the safety pre-check.

- changed: skills/kw-pdf-report/scripts/branded_pdf.py
- changed: skills/surface-gate/SKILL.md

## 1.0.2 — 2026-07-14

Refreshed the saved activity report (branded PDF + export) and tightened change detection.

- changed: agents/activity-digest.md
- changed: skills/activity-digest/SKILL.md
- changed: skills/kw-pdf-report/SKILL.md
- changed: skills/kw-pdf-report/scripts/branded_pdf.py
- changed: skills/report-export/SKILL.md

## 1.0.1 — 2026-07-13

See what actually changed in a Kiteworks folder over any time window — new, edited, and moved files — and save it as a shareable report. Ends manual folder-diffing before status meetings and audits.

- added: README.md
- added: agents/activity-digest.md
- added: skills/activity-digest/SKILL.md
- added: skills/folder-scan/SKILL.md
- added: skills/kw-pdf-report/SKILL.md
- added: skills/kw-pdf-report/assets/hero-bg.png
- added: skills/kw-pdf-report/assets/kw-logo-white.png
- added: skills/kw-pdf-report/scripts/branded_pdf.py
- added: skills/report-export/SKILL.md
- added: skills/surface-gate/SKILL.md
