# Changelog

## 1.1.0 — 2026-09-14

added 1 file(s); updated 3 file(s)

- added: skills/sharing-exposure/SKILL.md
- changed: skills/compliance-mapping/SKILL.md
- changed: skills/folder-scan/SKILL.md
- changed: skills/hipaa-compliance-check/SKILL.md

## 1.0.1 — 2026-09-09

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

## 1.0.0 — 2026-09-07

Promoted to general availability at 1.0.0. No change to what the agent checks. The agent now states the marketplace terms acceptance line at the start of a session, and the bundle carries the current terms (version 2.0, effective 2026-08-15) instead of the superseded 1.0 install disclaimer. <!-- whats-new: consolidated -->

- changed: README.md
- changed: agents/hipaa-compliance-check.md
- changed: skills/content-extract/SKILL.md
- changed: skills/content-extract/scripts/extract_and_cleanup.py
- changed: skills/content-extract/scripts/scrub.py
- changed: skills/kw-pdf-report/scripts/branded_pdf.py
- changed: skills/report-export/SKILL.md

## 0.5.3 — 2026-08-01

Retention checks now follow what each framework's own text actually says: you are only asked for a retention period when the framework leaves the number open, the framework's own figure is used when it states one, and the check is skipped entirely for frameworks that have no retention rule — so you are no longer asked for numbers this framework never required. Document-age checks now use the later of the created and last-modified date, so an actively maintained document is no longer wrongly flagged as overdue.

- changed: skills/compliance-mapping/SKILL.md
- changed: skills/compliance-mapping/scripts/accessibility_check.py
- changed: skills/content-extract/SKILL.md
- changed: skills/folder-scan/SKILL.md
- changed: skills/hipaa-compliance-check/SKILL.md
- changed: skills/kw-pdf-report/SKILL.md
- changed: skills/kw-pdf-report/scripts/branded_pdf.py
- changed: skills/report-export/SKILL.md
- changed: skills/term-sweep/SKILL.md
- changed: skills/term-sweep/scripts/pii_patterns.py

## 0.5.2 — 2026-07-15

Refined the HIPAA checks and PII term matching; refreshed the branded report and safety pre-check.

- changed: skills/hipaa-compliance-check/SKILL.md
- changed: skills/kw-pdf-report/scripts/branded_pdf.py
- changed: skills/surface-gate/SKILL.md
- changed: skills/term-sweep/SKILL.md
- changed: skills/term-sweep/scripts/pii_patterns.py

## 0.5.1 — 2026-07-14

Checks a Kiteworks folder for the HIPAA-relevant signals a file-sharing platform can actually see — sensitive content and external sharing — and saves a report, clearly flagging what falls outside its view.

- added: README.md
- added: agents/hipaa-compliance-check.md
- added: skills/compliance-mapping/SKILL.md
- added: skills/compliance-mapping/scripts/accessibility_check.py
- added: skills/content-extract/SKILL.md
- added: skills/folder-scan/SKILL.md
- added: skills/hipaa-compliance-check/SKILL.md
- added: skills/kw-pdf-report/SKILL.md
- added: skills/kw-pdf-report/assets/hero-bg.png
- added: skills/kw-pdf-report/assets/kw-logo-white.png
- added: skills/kw-pdf-report/scripts/branded_pdf.py
- added: skills/report-export/SKILL.md
- added: skills/surface-gate/SKILL.md
- added: skills/term-sweep/SKILL.md
- added: skills/term-sweep/scripts/pii_patterns.py
