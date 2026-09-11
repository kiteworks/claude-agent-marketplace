---
name: ccpa-compliance-check
description: >
  Use when the user asks to check Kiteworks content against CCPA/CPRA --
  trigger phrases include `CCPA` `CPRA` `California Consumer Privacy Act` `Do Not Sell or Share` `GPC signal`. Scans and, on confirmation,
  writes a CSV + txt/pdf report. Single-phase: no separate "apply" step
  to ask for. Fit tier: Strong -- see below for what this can and can't
  actually check.
metadata:
  version: "0.3.2"
---

Delegate to the `ccpa-compliance-check` subagent on surfaces that support it (Claude Code, Cowork). If it reports no tools or fabricates results without tool calls, discard and check the `Kiteworks` connector. On other surfaces, follow this skill directly.

# CCPA/CPRA Compliance Check -- fit tier: Strong

Read `../compliance-mapping/SKILL.md` first for the shared mechanism (signals A/B/C/D, report shape, honesty framing) -- this skill only supplies framework-specific content, never its own scanning logic.

## What CCPA/CPRA actually is

California's consumer privacy law (CCPA/CPRA), covering consumer rights to know, delete, and correct personal information, plus limits on Sensitive Personal Information.

## Signals this agent runs

Signals: **A, B, C**. Signal A's default term list for this framework: "personal information", "sensitive personal information", "precise geolocation", "biometric" (plus the built-in PII/secret presets, plus anything the user adds). Signal C's retention threshold: ask the user -- CPRA requires disclosed retention periods per data category but sets no universal fixed number.

## Control citations

Drawn directly from the California Civil Code text (via California Legislative Information, leginfo.ca.gov), not the third-party GRC skill library.

- **Signal A** (sensitive-content exposure): Cal. Civ. Code §1798.140 defines "sensitive personal information" -- 12 categories including SSN, financial account credentials, precise geolocation, race/ethnicity, religion, union membership, genetic/biometric/health data, and sex life/orientation. This signal's term list targets that definition.
- **Signal B** (external sharing): §1798.140's definitions of "sell" and "share," and §1798.135's opt-out-of-sale/share requirement -- an externally shared file is the observable proxy this scan can check against those definitions.
- **Signal C** (retention): §1798.100(a)(3) requires a business to disclose the retention period for each category of personal information it collects, and prohibits retaining it longer than reasonably necessary -- no fixed number is set, which is why this signal asks the user for their own disclosed policy.

## What this doesn't check

Business-applicability threshold determination, ad-tech sale/sharing classification, and consumer-rights-request workflows require business context this scan doesn't have -- this covers the same observable slice as GDPR.

## Recommended next steps

- Verify the "Do Not Sell or Share" / GPC opt-out mechanism actually covers any flagged sharing activity.
- Confirm disclosed retention periods per data category match what Signal C found in practice.
- If a large data handler, review CPPA cybersecurity-audit and risk-assessment requirements against this scan's findings.

## Source

Adapted from the CCPA/CPRA skill in the Claude Skills for Governance, Risk & Compliance library (`Sushegaad/Claude-Skills-Governance-Risk-and-Compliance`) -- <https://sushegaad.github.io/Claude-Skills-Governance-Risk-and-Compliance/> -- which offers much deeper advisory capability (policy/document drafting, licensing walkthroughs, breach-notification procedures) than a content-governance scan can ever provide.
