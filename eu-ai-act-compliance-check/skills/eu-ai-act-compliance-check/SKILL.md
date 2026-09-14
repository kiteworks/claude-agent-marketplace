---
name: eu-ai-act-compliance-check
description: >
  Use when the user asks to check Kiteworks content against EU AI Act --
  trigger phrases include `EU AI Act` `AI Act` `high-risk AI` `prohibited AI` `GPAI model`. Scans and, on confirmation,
  writes a CSV + txt/pdf report. Single-phase: no separate "apply" step
  to ask for. Fit tier: Light -- see below for what this can and can't
  actually check.
metadata:
  version: "0.3.3"
---

Delegate to the `eu-ai-act-compliance-check` subagent on surfaces that support it (Claude Code, Cowork). If it reports no tools or fabricates results without tool calls, discard and check the `Kiteworks` connector. On other surfaces, follow this skill directly.

# EU AI Act Compliance Check -- fit tier: Light

Read `../compliance-mapping/SKILL.md` first for the shared mechanism (signals A/B/C/D, report shape, honesty framing) -- this skill only supplies framework-specific content, never its own scanning logic.

## What EU AI Act actually is

The EU's horizontal AI regulation classifying AI systems by risk tier and imposing obligations on providers and deployers of high-risk AI.

## Signals this agent runs

Signals: **A, B**. Signal A's default term list for this framework: "training data", "model card", "AI system", "biometric" (plus the built-in PII/secret presets, plus anything the user adds).

## Control citations

Drawn directly from Regulation (EU) 2024/1689 (EUR-Lex), not the third-party GRC skill library.

- **Signal A** (sensitive-content exposure): Art. 10 (Data and data governance) requires training/validation/testing datasets for high-risk AI to be relevant, representative, and error-free, and specifically calls out bias detection and mitigation -- content flagged as AI-training-data-shaped is exactly what Art. 10 governs. Art. 6, read with Annex III, is what determines whether a given AI system counts as "high-risk" in the first place, which this scan cannot determine on its own.
- **Signal B** (sharing exposure): no article maps directly; sharing exposure here is a proxy for data-governance hygiene, not a named AI Act obligation.

## What this doesn't check

AI system risk classification, prohibited-practice screening, and provider/deployer obligations require context about a specific AI system this scan doesn't have -- this only flags AI-related documents that are in a shared folder tree or contain personal/biometric data. It also cannot see who a shared folder is shared with, or whether they are internal or external; directly shared files, and any sharing set above the top-level folder visible to the scanning user, are not detected.

## Recommended next steps

- Complete AI system risk classification under Art. 6/Annex III for any system this scan's term list flags.
- If classified high-risk, verify conformity assessment and CE marking are in progress.
- Track the Act's phased-applicability dates so obligations are addressed on schedule, not retroactively.

## Source

Adapted from the EU AI Act skill in the Claude Skills for Governance, Risk & Compliance library (`Sushegaad/Claude-Skills-Governance-Risk-and-Compliance`) -- <https://sushegaad.github.io/Claude-Skills-Governance-Risk-and-Compliance/> -- which offers much deeper advisory capability (policy/document drafting, licensing walkthroughs, breach-notification procedures) than a content-governance scan can ever provide.
