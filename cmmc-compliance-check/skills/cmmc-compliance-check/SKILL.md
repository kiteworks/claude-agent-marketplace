---
name: cmmc-compliance-check
description: >
  Use when the user asks to check Kiteworks content against CMMC 2.0 --
  trigger phrases include `CMMC` `CMMC 2.0` `CUI` `NIST 800-171` `DFARS 7021` `SPRS score`. Scans and, on confirmation,
  writes a CSV + txt/pdf report. Single-phase: no separate "apply" step
  to ask for. Fit tier: Good -- see below for what this can and can't
  actually check.
metadata:
  version: "0.3.3"
---

Delegate to the `cmmc-compliance-check` subagent on surfaces that support it (Claude Code, Cowork). If it reports no tools or fabricates results without tool calls, discard and check the `Kiteworks` connector. On other surfaces, follow this skill directly.

# CMMC 2.0 Compliance Check -- fit tier: Good

Read `../compliance-mapping/SKILL.md` first for the shared mechanism (signals A/B/C/D, report shape, honesty framing) -- this skill only supplies framework-specific content, never its own scanning logic.

## What CMMC 2.0 actually is

The US Department of Defense's cybersecurity certification model for contractors handling Controlled Unclassified Information (CUI).

## Signals this agent runs

Signals: **A, B**. Signal A's default term list for this framework: "CUI", "controlled unclassified information", "FOUO", "export controlled", "DFARS" (plus the built-in PII/secret presets, plus anything the user adds).

## Control citations

Drawn directly from NIST SP 800-171 Rev 2, which CMMC 2.0 Level 2 maps its 110 practices onto 1:1, not the third-party GRC skill library.

- **Signal A** (sensitive-content exposure): Practice 3.1.3 (control the flow of CUI in accordance with approved authorizations) governs where CUI-marked content is allowed to live.
- **Signal B** (sharing exposure): Practice 3.13.11 (employ FIPS-validated cryptography when used to protect the confidentiality of CUI) governs CUI once it leaves a controlled environment -- note this requires FIPS 140-2 *module* validation, not just an approved algorithm, a distinction this scan cannot verify from file metadata alone.

## What this doesn't check

SSP authorship, the 110 NIST SP 800-171 practice implementations, and SPRS scoring concern an organization's whole security programme, not one folder -- this only flags where CUI-marked content appears to live or be in a shared folder tree. It also cannot see who a shared folder is shared with, or whether they are internal or external; directly shared files, and any sharing set above the top-level folder visible to the scanning user, are not detected.

## Recommended next steps

- Complete or update the System Security Plan (SSP) and POA&M for any gap this scan surfaces.
- Verify the SPRS score reflects current NIST SP 800-171 practice implementation, not a stale self-assessment.
- If pursuing Level 2 certification, confirm C3PAO assessment readiness against the full 110-practice set.

## Source

Adapted from the CMMC 2.0 skill in the Claude Skills for Governance, Risk & Compliance library (`Sushegaad/Claude-Skills-Governance-Risk-and-Compliance`) -- <https://sushegaad.github.io/Claude-Skills-Governance-Risk-and-Compliance/> -- which offers much deeper advisory capability (policy/document drafting, licensing walkthroughs, breach-notification procedures) than a content-governance scan can ever provide.
