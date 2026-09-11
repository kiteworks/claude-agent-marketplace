---
name: iso27701-compliance-check
description: >
  Use when the user asks to check Kiteworks content against ISO 27701 --
  trigger phrases include `ISO 27701` `PIMS` `privacy information management` `PII controller` `PII processor`. Scans and, on confirmation,
  writes a CSV + txt/pdf report. Single-phase: no separate "apply" step
  to ask for. Fit tier: Strong -- see below for what this can and can't
  actually check.
metadata:
  version: "0.3.2"
---

Delegate to the `iso27701-compliance-check` subagent on surfaces that support it (Claude Code, Cowork). If it reports no tools or fabricates results without tool calls, discard and check the `Kiteworks` connector. On other surfaces, follow this skill directly.

# ISO 27701 Compliance Check -- fit tier: Strong

Read `../compliance-mapping/SKILL.md` first for the shared mechanism (signals A/B/C/D, report shape, honesty framing) -- this skill only supplies framework-specific content, never its own scanning logic.

## What ISO 27701 actually is

A privacy information management system (PIMS) extension to ISO 27001, covering both PII controller and PII processor obligations.

## Signals this agent runs

Signals: **A, B, C**. Signal A's default term list for this framework: "personal data", "PII", "data subject", "privacy notice" (plus the built-in PII/secret presets, plus anything the user adds). Signal C's retention threshold: ask the user -- ISO 27701 requires a documented retention schedule but sets no universal fixed number.

## Control citations

ISO/IEC 27701:2025's Annex A structure is confirmed via the standard's own listing (iso.org/standard/27701) and certification-body summaries (isms.online): 78 controls total -- A.1 (31 PII controller controls), A.2 (18 PII processor controls), A.3 (29 controls shared with ISO 27001 Annex A, covering things like cryptography and access control).

- **Signal A** (sensitive-content exposure): maps to the A.3 shared security controls (cryptography, access control) that also anchor ISO 27001.
- **Signal B** (external sharing): A.1.5.x and A.2.5.x are dedicated international-transfer control clusters in the controller/processor tables -- confirmed to exist. A.1.5.5 specifically, "Records of PII disclosures," requires recording who PII was disclosed to and when, which is a genuinely good match for what this signal observes.
- **Signal C** (retention): **not independently verified to a specific control number.** ISO/IEC 27701, unlike the laws cited elsewhere in this family, is a paywalled standard -- the actual clause text isn't freely mirrored the way government-published law is, so this project could confirm the Annex A structure (control counts, section groupings) from secondary sources but not the exact sub-control number for a retention-schedule requirement. That's a structurally different kind of gap than "we didn't look hard enough": it's a licensing barrier, not a research one. Flagged honestly rather than guessed.

## What this doesn't check

The formal PIMS certification process, Statement of Applicability, and the 78 Annex A controls beyond data handling itself are outside scan visibility -- this covers the same observable slice as GDPR, since ISO 27701 is explicitly built to align with it.

## Recommended next steps

- Complete a full PIMS internal audit against the actual (licensed) Annex A control text -- this scan's citations describe structure, not certified conformance.
- Verify records-of-PII-disclosure logging (A.1.5.5) exists at a level of detail beyond what Signal B's `isShared` boolean can see.
- If pursuing certification, engage an accredited certification body for the formal audit; this scan is not a substitute for one.

## Source

Adapted from the ISO 27701 skill in the Claude Skills for Governance, Risk & Compliance library (`Sushegaad/Claude-Skills-Governance-Risk-and-Compliance`) -- <https://sushegaad.github.io/Claude-Skills-Governance-Risk-and-Compliance/> -- which offers much deeper advisory capability (policy/document drafting, licensing walkthroughs, breach-notification procedures) than a content-governance scan can ever provide.
