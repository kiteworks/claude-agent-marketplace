---
name: dpdpa-compliance-check
description: >
  Use when the user asks to check Kiteworks content against DPDPA (India) --
  trigger phrases include `DPDPA` `Digital Personal Data Protection Act` `India data protection` `Data Fiduciary`. Scans and, on confirmation,
  writes a CSV + txt/pdf report. Single-phase: no separate "apply" step
  to ask for. Fit tier: Strong -- see below for what this can and can't
  actually check.
metadata:
  version: "0.3.2"
---

Delegate to the `dpdpa-compliance-check` subagent on surfaces that support it (Claude Code, Cowork). If it reports no tools or fabricates results without tool calls, discard and check the `Kiteworks` connector. On other surfaces, follow this skill directly.

# DPDPA (India) Compliance Check -- fit tier: Strong

Read `../compliance-mapping/SKILL.md` first for the shared mechanism (signals A/B/C/D, report shape, honesty framing) -- this skill only supplies framework-specific content, never its own scanning logic.

## What DPDPA (India) actually is

India's Digital Personal Data Protection Act, covering Data Fiduciary obligations, consent, and children's data protections.

## Signals this agent runs

Signals: **A, B, C, E (dormant)**. Signal A's default term list for this framework: "personal data", "aadhaar", "personal information" (plus the built-in PII/secret presets, plus anything the user adds). Signal C's retention threshold: ask the user -- DPDPA requires erasure once the specified purpose is served (see citation below), with no universal fixed number. Signal E (cross-border transfer) is dormant per `../compliance-mapping/SKILL.md` -- Section 16 governs it, but no Kiteworks field to check it against exists today.

## Control citations

Drawn directly from the Digital Personal Data Protection Act, 2023 and its 2025 Rules (via dpdpa.com's section-by-section mirror of the gazetted Act), not the third-party GRC skill library.

- **Signal A** (sensitive-content exposure): Section 2(t) defines "personal data"; Section 8(5) (implemented via DPDP Rules 2025, Rule 6) requires "reasonable security safeguards" -- encryption/tokenisation, access controls, monitoring/logs, and backups -- for personal data a Data Fiduciary processes.
- **Signal B** (external sharing): Section 8(5)/Rule 6's access-control obligations extend to any Data Processor a Data Fiduciary shares data with. Cross-border transfer itself is addressed in Section 16, which uses a blacklist model (transfer is permitted except to countries the Central Government specifically restricts by notification) -- see Signal E above for why this scan can't check destination today.
- **Signal C** (retention): Section 8(7) -- a Data Fiduciary must erase personal data upon consent withdrawal, or as soon as it's reasonable to assume the specified purpose is no longer being served (deemed, per Section 8(8), after a prescribed period of Data Principal inactivity), unless retention is required by another law.

## What this doesn't check

Consent-mechanism validity, Significant Data Fiduciary obligations, and breach-notification timelines require legal judgment this scan cannot make -- this covers the same observable slice as GDPR.

## Recommended next steps

- Verify consent-manager registration status and DPDP Rules 2025 compliance once fully in force.
- Confirm whether Significant Data Fiduciary obligations (DPO designation, independent audits) apply, and if so, that they're met.
- Verify the reasonable-security-safeguards obligation (Rule 6 -- encryption, access control, monitoring, backups) is actually implemented for flagged content, not just documented.

## Source

Adapted from the DPDPA (India) skill in the Claude Skills for Governance, Risk & Compliance library (`Sushegaad/Claude-Skills-Governance-Risk-and-Compliance`) -- <https://sushegaad.github.io/Claude-Skills-Governance-Risk-and-Compliance/> -- which offers much deeper advisory capability (policy/document drafting, licensing walkthroughs, breach-notification procedures) than a content-governance scan can ever provide.
