---
name: nist-ai-rmf-compliance-check
description: >
  Use when the user asks to check Kiteworks content against NIST AI RMF --
  trigger phrases include `NIST AI RMF` `AI Risk Management Framework` `GOVERN function` `AI risk register`. Scans and, on confirmation,
  writes a CSV + txt/pdf report. Single-phase: no separate "apply" step
  to ask for. Fit tier: Light -- see below for what this can and can't
  actually check.
metadata:
  version: "0.4.4"
---

Delegate to the `nist-ai-rmf-compliance-check` subagent on surfaces that support it (Claude Code, Cowork). If you already are that subagent, do not delegate again: follow this skill directly. If it reports no tools or fabricates results without tool calls, discard and check the `Kiteworks` connector. On other surfaces, follow this skill directly.

# NIST AI RMF Compliance Check -- fit tier: Light

Read `../compliance-mapping/SKILL.md` first for the shared mechanism (signals A/B/C/D, report shape, honesty framing) -- this skill only supplies framework-specific content, never its own scanning logic.

## What NIST AI RMF actually is

NIST's AI Risk Management Framework -- Govern, Map, Measure, Manage -- for identifying and treating risks across the AI lifecycle.

## Signals this agent runs

Signals: **A, B**. Signal A's default term list for this framework: "training data", "model card", "AI system" (plus the built-in PII/secret presets, plus anything the user adds).

## Control citations

Fully confirmed this pass, down to a specific subcategory. Drawn from NIST AI 100-1 (AI RMF 1.0, January 2023) and its companion AI RMF Playbook (airc.nist.gov/airmf-resources/playbook/govern).

- **Signal A/B** (AI-document exposure): **GOVERN 1.4** -- "The risk management process and its outcomes are established through transparent policies, procedures, and other controls based on organizational risk priorities" -- is the specific subcategory this skill's document-hygiene angle reflects, closing the gap the prior research pass left open. The Playbook's Suggested Actions for GOVERN 1.4 call for documentation policies covering, among other things, "description and characterization of training data," directly citing the Model Cards for Model Reporting and Datasheets for Datasets literature -- the origin of this skill's "model card" term and a precise match for its term list.

## What this doesn't check

AI trustworthiness evaluation (bias, explainability, robustness) requires access to the model itself, not just documents about it -- this only flags AI-related documents that are in a shared folder tree or contain personal data. It also cannot see who a shared folder is shared with, or whether they are internal or external; directly shared files, and any sharing set above the top-level folder visible to the scanning user, are not detected.

## Recommended next steps

- Complete AI risk mapping and measurement per the Map/Measure functions for any AI system this scan flags.
- Use the AI RMF Playbook's GOVERN 1.4 documentation-policy checklist (training data description, model documentation inventory, public disclosure policy) as the basis for a real AI-documentation audit, not just this scan's document-hygiene proxy.

## Source

Adapted from the NIST AI RMF skill in the Claude Skills for Governance, Risk & Compliance library (`Sushegaad/Claude-Skills-Governance-Risk-and-Compliance`) -- <https://sushegaad.github.io/Claude-Skills-Governance-Risk-and-Compliance/> -- which offers much deeper advisory capability (policy/document drafting, licensing walkthroughs, breach-notification procedures) than a content-governance scan can ever provide.
