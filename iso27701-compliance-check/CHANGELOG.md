# Changelog

## 1.4.0 — 2026-10-03

Clearer executive reports: a concise PDF for decision makers, with the complete evidence in a linked CSV. <!-- whats-new: consolidated -->

## 1.3.5 — 2026-09-30

Agents now ask which report to save (CSV, PDF, TXT or none) before the scan, so saving works in Claude Desktop and Cowork. <!-- whats-new: consolidated -->

## 1.3.4 — 2026-09-29

Maintenance release: cleanup and reliability improvements. <!-- whats-new: consolidated -->

## 1.3.2 — 2026-09-25

Maintenance release: reliability improvements. <!-- whats-new: consolidated -->

## 1.3.1 — 2026-09-24

Reads PowerPoint speaker notes and grouped shapes when checking slide decks, and counts IBANs that run straight into the next field. <!-- whats-new: consolidated -->

## 1.3.0 — 2026-09-24

Detects email addresses, matches terms in folder names, reads spreadsheets and Word document titles reliably, and deletes its temporary local copies when a read-only run ends. <!-- whats-new: consolidated -->

## 1.2.3 — 2026-09-24

Maintenance release: internal skill metadata cleanup. <!-- whats-new: consolidated -->

## 1.2.2 — 2026-09-23

Maintenance release: internal skill metadata cleanup. <!-- whats-new: consolidated -->

## 1.2.1 — 2026-09-23

Treats files whose security scan is still running as "scan pending" instead of unreadable, and paces Kiteworks calls so large folders finish <!-- whats-new: consolidated -->

## 1.2.0 — 2026-09-20

Ensure it works with any Kiteworks connector name and explains what it can and cannot do over your connection <!-- whats-new: consolidated -->

## 1.1.0 — 2026-09-14

added 1 file(s); updated 3 file(s) <!-- whats-new: consolidated -->

## 1.0.1 — 2026-09-09

Own temporary document artifacts, honor cleanup permissions, and report residual files accurately.

## 1.0.0 — 2026-09-07

Promoted to general availability at 1.0.0. No change to what the agent checks. The agent now states the marketplace terms acceptance line at the start of a session, and the bundle carries the current terms (version 2.0, effective 2026-08-15) instead of the superseded 1.0 install disclaimer. <!-- whats-new: consolidated -->

## 0.5.3 — 2026-08-01

Retention checks now follow what each framework's own text actually says: you are only asked for a retention period when the framework leaves the number open, the framework's own figure is used when it states one, and the check is skipped entirely for frameworks that have no retention rule — so you are no longer asked for numbers this framework never required. Document-age checks now use the later of the created and last-modified date, so an actively maintained document is no longer wrongly flagged as overdue.

## 0.5.2 — 2026-07-15

Refined the ISO 27701 checks and PII term matching; refreshed the branded report and safety pre-check.

## 0.5.1 — 2026-07-14

Checks a Kiteworks folder for the ISO 27701-relevant signals a file-sharing platform can actually see — sensitive content and external sharing — and saves a report, clearly flagging what falls outside its view.
