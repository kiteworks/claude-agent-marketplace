---
name: nis2-compliance-check
description: >
  Use when the user asks to check Kiteworks content against NIS2 --
  trigger phrases include `NIS2` `NIS 2` `essential entity` `important entity` `NIS2 incident reporting`. Scans and, on confirmation,
  writes a CSV + txt/pdf report. Single-phase: no separate "apply" step
  to ask for. Fit tier: Light -- see below for what this can and can't
  actually check.
metadata:
  version: "0.3.3"
---

Delegate to the `nis2-compliance-check` subagent on surfaces that support it (Claude Code, Cowork). If it reports no tools or fabricates results without tool calls, discard and check the `Kiteworks` connector. On other surfaces, follow this skill directly.

# NIS2 Compliance Check -- fit tier: Light

Read `../compliance-mapping/SKILL.md` first for the shared mechanism (signals A/B/C/D, report shape, honesty framing) -- this skill only supplies framework-specific content, never its own scanning logic.

## What NIS2 actually is

The EU's cybersecurity directive for essential and important entities, covering risk-management measures and incident-reporting timelines.

## Signals this agent runs

Signals: **B**.

## Control citations

Drawn directly from Directive (EU) 2022/2555 (EUR-Lex), not the third-party GRC skill library.

- **Signal B** (sharing exposure): Art. 21(2) lists 10 minimum risk-management measures essential/important entities must implement, including access control policies and cryptography/encryption use -- a file in a shared folder tree is exactly the kind of event those measures exist to govern. Where a flagged file's exposure looks like it could itself be a "significant incident," Art. 23 sets the reporting clock: an early warning within 24 hours of becoming aware, a full notification within 72 hours, and a final report within one month.

## What this doesn't check

Entity classification, the 10 Art. 21 risk-management measures, and the 24h/72h/1-month incident-reporting workflow are all outside file-scan visibility -- this speaks only to sharing exposure of any flagged documentation. It also cannot see who a shared folder is shared with, or whether they are internal or external; directly shared files, and any sharing set above the top-level folder visible to the scanning user, are not detected.

## Recommended next steps

- Confirm entity classification (essential/important) under the relevant EU member state's national transposition.
- Verify all 10 Art. 21(2) risk-management measures are implemented, not just the two this scan's signals touch.
- Rehearse the 24-hour/72-hour/1-month incident-reporting workflow so it's ready, not just documented.

## Source

Adapted from the NIS2 skill in the Claude Skills for Governance, Risk & Compliance library (`Sushegaad/Claude-Skills-Governance-Risk-and-Compliance`) -- <https://sushegaad.github.io/Claude-Skills-Governance-Risk-and-Compliance/> -- which offers much deeper advisory capability (policy/document drafting, licensing walkthroughs, breach-notification procedures) than a content-governance scan can ever provide.
