---
name: hipaa-compliance-check
description: >
  Use when the user asks to check Kiteworks content against HIPAA --
  trigger phrases include `HIPAA` `PHI` `ePHI` `covered entity` `BAA` `breach notification`. Scans and, on confirmation,
  writes a CSV + txt/pdf report. Single-phase: no separate "apply" step
  to ask for. Fit tier: Strong -- see below for what this can and can't
  actually check.
metadata:
  version: "0.3.3"
---

Delegate to the `hipaa-compliance-check` subagent on surfaces that support it (Claude Code, Cowork). If it reports no tools or fabricates results without tool calls, discard and check the `Kiteworks` connector. On other surfaces, follow this skill directly.

# HIPAA Compliance Check -- fit tier: Strong

Read `../compliance-mapping/SKILL.md` first for the shared mechanism (signals A/B/C/D, report shape, honesty framing) -- this skill only supplies framework-specific content, never its own scanning logic.

## What HIPAA actually is

The US health-data privacy and security law (Privacy Rule, Security Rule, Breach Notification Rule) governing protected health information (PHI/ePHI).

## Signals this agent runs

Signals: **A, B, C**. Signal A's default term list for this framework: "PHI", "ePHI", "protected health information", "patient", "diagnosis", "medical record number" (plus the built-in PII/secret presets, plus anything the user adds). Signal C's retention threshold: 6 years from creation or last effective date, per the HIPAA Security Rule documentation-retention requirement (45 CFR 164.316(b)(2)).

## Control citations

Drawn directly from the HIPAA Security Rule text at 45 CFR Part 164 (via eCFR), not the third-party GRC skill library.

- **Signal A** (PHI-shaped content exposure): 45 CFR §164.312(a)(1), the Access Control technical safeguard -- ePHI access must be restricted to authorized users. This signal flags where PHI-shaped content sits before that control can even be evaluated.
- **Signal B** (sharing exposure): 45 CFR §164.312(e)(1), Transmission Security -- guards against unauthorized access to ePHI transmitted over a network. A file in a shared folder tree with PHI-shaped content is the observable proxy for this control's concern.
- **Signal C** (retention): 45 CFR §164.316(b)(2)(i) -- required documentation must be retained 6 years from the date of creation or the date it last was in effect, whichever is later.

## What this doesn't check

Technical/administrative/physical safeguard implementation, Business Associate Agreements, breach risk-assessment, and workforce training are entirely outside what content, sharing, and age can reveal -- this only flags where PHI-shaped content appears to live, is in a shared folder tree, or has aged past the documentation-retention window. It also cannot see who a shared folder is shared with, or whether they are internal or external; directly shared files, and any sharing set above the top-level folder visible to the scanning user, are not detected.

## Recommended next steps

- Complete a formal HIPAA Security Risk Analysis (45 CFR §164.308(a)(1)) -- this scan is not a substitute for one.
- Verify Business Associate Agreements are in place for any party a flagged file was shared with.
- Confirm workforce training covers the specific PHI-handling gaps this scan surfaced.

## Source

Adapted from the HIPAA skill in the Claude Skills for Governance, Risk & Compliance library (`Sushegaad/Claude-Skills-Governance-Risk-and-Compliance`) -- <https://sushegaad.github.io/Claude-Skills-Governance-Risk-and-Compliance/> -- which offers much deeper advisory capability (policy/document drafting, licensing walkthroughs, breach-notification procedures) than a content-governance scan can ever provide.
