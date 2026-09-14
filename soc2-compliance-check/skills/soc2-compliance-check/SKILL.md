---
name: soc2-compliance-check
description: >
  Use when the user asks to check Kiteworks content against SOC 2 --
  trigger phrases include `SOC 2` `Trust Services Criteria` `TSC` `audit readiness` `control statement`. Scans and, on confirmation,
  writes a CSV + txt/pdf report. Single-phase: no separate "apply" step
  to ask for. Fit tier: Light -- see below for what this can and can't
  actually check.
metadata:
  version: "0.3.3"
---

Delegate to the `soc2-compliance-check` subagent on surfaces that support it (Claude Code, Cowork). If it reports no tools or fabricates results without tool calls, discard and check the `Kiteworks` connector. On other surfaces, follow this skill directly.

# SOC 2 Compliance Check -- fit tier: Light

Read `../compliance-mapping/SKILL.md` first for the shared mechanism (signals A/B/C/D, report shape, honesty framing) -- this skill only supplies framework-specific content, never its own scanning logic.

## What SOC 2 actually is

An AICPA auditing standard against the Trust Services Criteria: Security, Availability, Confidentiality, Processing Integrity, and Privacy.

## Signals this agent runs

Signals: **A, B**.

## Control citations

Drawn directly from the AICPA's 2017 Trust Services Criteria (as revised 2022), not the third-party GRC skill library.

- **Signal A** (sensitive-content exposure): C1.1 (the entity identifies and maintains confidential information to meet its objectives) and C1.2 (the entity disposes of confidential information to meet its objectives, using encryption, access restriction, and secure deletion as example protection mechanisms).
- **Signal B** (sharing exposure): CC6.1 (the entity implements logical access security measures to protect against unauthorized access) and CC6.6 (the entity implements controls to prevent or detect and act upon unauthorized network connections) -- sharing exposure sits squarely inside both.

## What this doesn't check

SOC 2 is fundamentally an auditor's assessment of internal controls, evidenced through interviews, control testing, and system walkthroughs -- a file scan can speak to the Confidentiality and Privacy criteria's data-handling expectations at best, nothing about Security, Availability, Processing Integrity, or the audit process itself. It also cannot see who a shared folder is shared with, or whether they are internal or external; directly shared files, and any sharing set above the top-level folder visible to the scanning user, are not detected.

## Recommended next steps

- Engage a licensed CPA firm for the actual Type I/II audit -- this scan is not, and cannot be, a substitute.
- If Availability, Processing Integrity, or Privacy criteria are in engagement scope, verify those controls separately; this scan only touches Confidentiality and the CC6 access-control series.

## Source

Adapted from the SOC 2 skill in the Claude Skills for Governance, Risk & Compliance library (`Sushegaad/Claude-Skills-Governance-Risk-and-Compliance`) -- <https://sushegaad.github.io/Claude-Skills-Governance-Risk-and-Compliance/> -- which offers much deeper advisory capability (policy/document drafting, licensing walkthroughs, breach-notification procedures) than a content-governance scan can ever provide.
