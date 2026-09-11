---
name: nzism-compliance-check
description: >
  Use when the user asks to check Kiteworks content against NZISM --
  trigger phrases include `NZISM` `NZ government security` `GCSB compliance` `NZISM gap analysis`. Scans and, on confirmation,
  writes a CSV + txt/pdf report. Single-phase: no separate "apply" step
  to ask for. Fit tier: Light -- see below for what this can and can't
  actually check.
metadata:
  version: "0.4.3"
---

Delegate to the `nzism-compliance-check` subagent on surfaces that support it (Claude Code, Cowork). If it reports no tools or fabricates results without tool calls, discard and check the `Kiteworks` connector. On other surfaces, follow this skill directly.

# NZISM -- fit tier: Light

Read `../compliance-mapping/SKILL.md` first for the shared mechanism (signals A/B/C/D, report shape, honesty framing) -- this skill only supplies framework-specific content, never its own scanning logic.

## What NZISM actually is

New Zealand's mandatory information security manual for government agencies, covering classification handling from Unclassified through Top Secret.

## Signals this agent runs

Signals: **A, B**. Signal A's default term list for this framework: "RESTRICTED", "IN CONFIDENCE", "SENSITIVE" (plus the built-in PII/secret presets, plus anything the user adds).

## Control citations

Fully confirmed this pass, down to specific CIDs. Drawn from the New Zealand Information Security Manual, Section 21.1 "Data Transfers" (nzism.gcsb.govt.nz, v3.9, November 2025).

- **Signal A/B**: **CID:4141** -- "Agencies MUST ensure that system users transferring data to and from a system are held accountable for the data they transfer" (Must-level, all classifications) is the specific control this skill's classification/transfer term list reflects, replacing the earlier "convention confirmed, no CID pinned" citation. Closely related: **CID:4151** -- "Agencies MUST ensure that all data transferred to a system of a lesser classification or a less secure system, is approved by a trusted source" (Must-level, SECRET/CONFIDENTIAL/TOP SECRET). NZISM applies baseline controls to information marked UNCLASSIFIED, IN-CONFIDENCE, SENSITIVE or RESTRICTED, with additional controls layered on for CONFIDENTIAL, SECRET or TOP SECRET material -- the basis for this skill's term list. Individual controls carry a compliance strength of MUST/MUST NOT (cannot be risk-managed) or SHOULD/SHOULD NOT (can be risk-managed); both CIDs cited here are MUST-level.

## What this doesn't check

Certification & Accreditation, the 18+ control sections, and system-authorisation sign-off concern infrastructure this scan cannot see -- this only flags classification-marked content that's externally shared.

## Recommended next steps

- Engage a CISO-endorsed assessor if certification/accreditation is required for the system.
- Verify CID:4141 (accountability for data transfers) and CID:4151 (trusted-source approval for transfers to a lower classification) are met at a level of detail beyond what this scan's `isShared` check can see.

## Source

Adapted from the NZISM skill in the Claude Skills for Governance, Risk & Compliance library (`Sushegaad/Claude-Skills-Governance-Risk-and-Compliance`) -- <https://sushegaad.github.io/Claude-Skills-Governance-Risk-and-Compliance/> -- which offers much deeper advisory capability (policy/document drafting, licensing walkthroughs, breach-notification procedures) than a content-governance scan can ever provide.
