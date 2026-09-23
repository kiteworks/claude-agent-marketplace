# Changelog

## 1.1.1 — 2026-09-23

Treats files whose security scan is still running as "scan pending" instead of unreadable, and paces Kiteworks calls so large folders finish <!-- whats-new: consolidated -->

- changed: skills/folder-scan/SKILL.md

## 1.1.0 — 2026-09-20

Ensure it works with any Kiteworks connector name and explains what it can and cannot do over your connection <!-- whats-new: consolidated -->

- added: hooks/allowlist.json
- added: hooks/hooks.json
- added: hooks/kw-allowlist.sh
- added: skills/connector-probe/SKILL.md
- changed: agents/storage-visualizer.md
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
- changed: agents/storage-visualizer.md
- changed: skills/kw-pdf-report/scripts/branded_pdf.py
- changed: skills/report-export/SKILL.md

## 1.0.3 — 2026-07-15

Refreshed the branded report and the safety pre-check.

- changed: skills/kw-pdf-report/scripts/branded_pdf.py
- changed: skills/surface-gate/SKILL.md

## 1.0.2 — 2026-07-14

Refined the storage breakdown and refreshed report export.

- changed: agents/storage-visualizer.md
- changed: skills/kw-pdf-report/SKILL.md
- changed: skills/kw-pdf-report/scripts/branded_pdf.py
- changed: skills/report-export/SKILL.md
- changed: skills/storage-visualizer/SKILL.md

## 1.0.1 — 2026-07-13

Shows what's eating space in a Kiteworks folder — totals, largest files and folders, and how much is shared — turning storage cleanup into a targeted, data-driven task.

- added: README.md
- added: agents/storage-visualizer.md
- added: skills/folder-scan/SKILL.md
- added: skills/kw-pdf-report/SKILL.md
- added: skills/kw-pdf-report/assets/hero-bg.png
- added: skills/kw-pdf-report/assets/kw-logo-white.png
- added: skills/kw-pdf-report/scripts/branded_pdf.py
- added: skills/report-export/SKILL.md
- added: skills/storage-visualizer/SKILL.md
- added: skills/surface-gate/SKILL.md
