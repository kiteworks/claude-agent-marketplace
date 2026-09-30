---
name: nist-800-53-compliance-check
description: >
  Use when the user asks to check Kiteworks content against NIST SP 800-53 --
  trigger phrases include `NIST SP 800-53` `SP 800-53` `RMF` `FISMA` `ATO` `SSP narrative`. Asks up front which report to save (CSV, PDF, TXT, or none), then scans and writes it. Single-phase: no separate "apply" step
  to ask for. Fit tier: Light -- see below for what this can and can't
  actually check.
metadata:
  version: "0.3.3"
---

**Before anything else, run the report preflight** (`../report-export/SKILL.md`): ask the user which report to save -- CSV, PDF, TXT, or no saved report (one multi-select question, with `AskUserQuestion` where the host has it) -- and confirm the destination (default `My Folder/Agents/NIST SP 800-53 Compliance Check/`). Pass the answer to the subagent as the `Report preflight` block. The subagent cannot ask the user anything itself, so a save question asked after the scan deadlocks.

Delegate to the `nist-800-53-compliance-check` subagent on surfaces that support it (Claude Code, Cowork). If you already are that subagent, do not delegate again: follow this skill directly. If it reports no tools or fabricates results without tool calls, discard and check the `Kiteworks` connector. On other surfaces, follow this skill directly.

# NIST SP 800-53 Compliance Check -- fit tier: Light

Read `../compliance-mapping/SKILL.md` first for the shared mechanism (signals A/B/C/D, report shape, honesty framing) -- this skill only supplies framework-specific content, never its own scanning logic.

## What NIST SP 800-53 actually is

NIST's federal security and privacy controls catalog (Rev 5) underlying FISMA, RMF, and FedRAMP baselines across 20 control families.

## Signals this agent runs

Signals: **A, B**. Signal A's default term list for this framework: "CUI", "federal information", "controlled unclassified" (plus the built-in PII/secret presets, plus anything the user adds). Count these terms, and the user's own terms, only with `../term-sweep/scripts/pii_patterns.py <extracted-text-file> --framework=nist-800-53 --framework-terms [--terms-file=<user-terms.txt>]`: the script holds this exact list and applies one fixed matching rule, so never count them yourself. When the content deep-scan runs, call `../term-sweep/scripts/pii_patterns.py` with `--framework=nist-800-53`: that adds the plaintext-credential preset (`password = <value>`-style assignments, placeholder values excluded) to the general built-in presets.

## Control citations

Drawn directly from NIST SP 800-53 Rev 5 (September 2020, with errata), not the third-party GRC skill library. Rev 5 has 1,196 controls and enhancements across 20 families.

- **Signal A** (sensitive-content exposure): AC-3 (Access Enforcement) and MP-6 (Media Sanitization) are the closest family matches for CUI/PII-shaped content found at rest.
- **Signal B** (sharing exposure): AC-4 (Information Flow Enforcement) and SC-8 (Transmission Confidentiality and Integrity) directly govern data leaving an authorized boundary.

## What this doesn't check

System categorisation, control tailoring, and SSP narrative authorship concern a federal system's whole control implementation, not one folder -- this only flags CUI/PII-shaped content and its sharing exposure, touching the Media Protection and Access Control families at the edges. It also cannot see who a shared folder is shared with, or whether they are internal or external; directly shared files, and any sharing set above the top-level folder visible to the scanning user, are not detected.

## Recommended next steps

- Complete or update the System Security Plan (SSP) reflecting actual control implementation across all 20 families, not just AC/MP/SC.
- Confirm continuous monitoring is current per the applicable Risk Management Framework (RMF) step.

## Source

Adapted from the NIST SP 800-53 skill in the Claude Skills for Governance, Risk & Compliance library (`Sushegaad/Claude-Skills-Governance-Risk-and-Compliance`) -- <https://sushegaad.github.io/Claude-Skills-Governance-Risk-and-Compliance/> -- which offers much deeper advisory capability (policy/document drafting, licensing walkthroughs, breach-notification procedures) than a content-governance scan can ever provide.
