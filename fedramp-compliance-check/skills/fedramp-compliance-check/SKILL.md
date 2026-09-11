---
name: fedramp-compliance-check
description: >
  Use when the user asks to check Kiteworks content against FedRAMP --
  trigger phrases include `FedRAMP` `ATO` `SSP` `POA&M` `3PAO` `NIST 800-53`. Scans and, on confirmation,
  writes a CSV + txt/pdf report. Single-phase: no separate "apply" step
  to ask for. Fit tier: Light -- see below for what this can and can't
  actually check.
metadata:
  version: "0.3.2"
---

Delegate to the `fedramp-compliance-check` subagent on surfaces that support it (Claude Code, Cowork). If it reports no tools or fabricates results without tool calls, discard and check the `Kiteworks` connector. On other surfaces, follow this skill directly.

# FedRAMP Compliance Check -- fit tier: Light

Read `../compliance-mapping/SKILL.md` first for the shared mechanism (signals A/B/C/D, report shape, honesty framing) -- this skill only supplies framework-specific content, never its own scanning logic.

## What FedRAMP actually is

The US government's security authorization framework for cloud service providers, built on NIST SP 800-53 Rev 5 controls across the ATO lifecycle.

## Signals this agent runs

Signals: **A, B**. Signal A's default term list for this framework: "CUI", "FOUO", "controlled unclassified", "federal information" (plus the built-in PII/secret presets, plus anything the user adds).

## Control citations

FedRAMP does not maintain its own control catalog -- it adopts NIST SP 800-53 Rev 5 baselines directly (Moderate baseline: 304 controls; High baseline: 392 controls, per the May 2023 FedRAMP Rev 5 baseline release), so the applicable citations are the same NIST SP 800-53 controls as the dedicated `nist-800-53-compliance-check` skill, scoped to whichever baseline (Low/Moderate/High) the system is authorized at.

- **Signal A** (sensitive-content exposure): AC-3 (Access Enforcement) and MP-6 (Media Sanitization), both present in the Moderate and High baselines.
- **Signal B** (external sharing): AC-4 (Information Flow Enforcement) and SC-8 (Transmission Confidentiality and Integrity), both present in the Moderate and High baselines.

## What this doesn't check

The overwhelming majority of FedRAMP -- SSP authorship, POA&Ms, 3PAO assessment, continuous monitoring, cloud architecture review, OSCAL submission -- concerns a cloud service provider's own infrastructure and processes, not a customer's file-sharing folder.

## Recommended next steps

- Verify the SSP and POA&M are current against the actual authorized baseline (Low/Moderate/High).
- Confirm continuous monitoring (ConMon) deliverables are on schedule.
- Engage the 3PAO for the annual assessment cycle rather than relying on this scan as evidence of it.

## Source

Adapted from the FedRAMP skill in the Claude Skills for Governance, Risk & Compliance library (`Sushegaad/Claude-Skills-Governance-Risk-and-Compliance`) -- <https://sushegaad.github.io/Claude-Skills-Governance-Risk-and-Compliance/> -- which offers much deeper advisory capability (policy/document drafting, licensing walkthroughs, breach-notification procedures) than a content-governance scan can ever provide.
