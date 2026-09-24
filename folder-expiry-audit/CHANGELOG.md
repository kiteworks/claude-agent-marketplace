# Changelog

## 0.3.2 — 2026-09-24

Maintenance release: internal skill metadata cleanup. <!-- whats-new: consolidated -->

- changed: agents/folder-expiry-audit.md

## 0.3.1 — 2026-09-23

Treats files whose security scan is still running as "scan pending" instead of unreadable, and paces Kiteworks calls so large folders finish <!-- whats-new: consolidated -->

- changed: skills/folder-scan/SKILL.md

## 0.3.0 — 2026-09-20

Ensure it works with any Kiteworks connector name and explains what it can and cannot do over your connection <!-- whats-new: consolidated -->

- added: hooks/allowlist.json
- added: hooks/hooks.json
- added: hooks/kw-allowlist.sh
- added: skills/connector-probe/SKILL.md
- changed: agents/folder-expiry-audit.md
- changed: skills/folder-scan/SKILL.md

## 0.2.4 — 2026-09-14

updated 1 file(s) <!-- whats-new: consolidated -->

- changed: skills/folder-scan/SKILL.md

## 0.2.3 — 2026-09-09

Own temporary document artifacts, honor cleanup permissions, and report residual files accurately.

- added: skills/scratch-lifecycle/SKILL.md
- added: skills/scratch-lifecycle/scripts/scratch_lifecycle.py
- changed: skills/surface-gate/SKILL.md

## 0.2.2 — 2026-09-07

Republished from the current source. The agent now states the marketplace terms acceptance line at the start of a session, and the bundle carries the current terms (version 2.0, effective 2026-08-15) instead of the superseded 1.0 install disclaimer. No change to what the agent does. <!-- whats-new: consolidated -->

- changed: README.md
- changed: agents/folder-expiry-audit.md

## 0.2.1 — 2026-08-01

Restores the agent's procedure and reporting instructions, which were cut off mid-word. It now reports an expiry of 0 as "not configured in this tenant" rather than implying a bug, calls out the rare non-zero lifetime values explicitly, and states plainly that expiry cannot be configured through this connector — that requires the Kiteworks web UI.

- changed: agents/folder-expiry-audit.md
- changed: skills/folder-scan/SKILL.md

## 0.2.0 — 2026-07-15

Refreshed the safety pre-check.

- changed: skills/surface-gate/SKILL.md

## 0.1.1 — 2026-07-14

Refined the retention/expiry policy audit.

- changed: skills/folder-expiry-audit/SKILL.md

## 0.1.0 — 2026-07-13

Shows which Kiteworks folders have a retention/expiry policy and which don't, so you can close governance gaps before they become compliance findings.

- added: README.md
- added: agents/folder-expiry-audit.md
- added: skills/folder-expiry-audit/SKILL.md
- added: skills/folder-scan/SKILL.md
- added: skills/surface-gate/SKILL.md
