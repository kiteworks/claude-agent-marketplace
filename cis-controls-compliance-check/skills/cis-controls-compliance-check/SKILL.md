---
name: cis-controls-compliance-check
description: >
  Use when the user asks to check Kiteworks content against CIS Controls v8 --
  trigger phrases include `CIS Controls` `CIS Top 18` `CIS v8` `Implementation Group`. Scans and, on confirmation,
  writes a CSV + txt/pdf report. Single-phase: no separate "apply" step
  to ask for. Fit tier: Light -- see below for what this can and can't
  actually check.
metadata:
  version: "0.3.3"
---

Delegate to the `cis-controls-compliance-check` subagent on surfaces that support it (Claude Code, Cowork). If it reports no tools or fabricates results without tool calls, discard and check the `Kiteworks` connector. On other surfaces, follow this skill directly.

# CIS Controls v8 Compliance Check -- fit tier: Light

Read `../compliance-mapping/SKILL.md` first for the shared mechanism (signals A/B/C/D, report shape, honesty framing) -- this skill only supplies framework-specific content, never its own scanning logic.

## What CIS Controls v8 actually is

The Center for Internet Security's 18 controls and 153 safeguards for essential cyber hygiene, scoped by Implementation Group (IG1-IG3).

## Signals this agent runs

Signals: **A, B**.

## Control citations

Drawn directly from CIS Controls v8 (Center for Internet Security), not the third-party GRC skill library.

- **Signal A** (sensitive-content exposure): Safeguard 3.1 (establish and maintain a data management process addressing sensitivity, ownership, handling, retention, and disposal) and Safeguard 3.3 (establish and maintain a data access control list) govern how sensitive content should be classified and gated.
- **Signal B** (sharing exposure): Safeguard 3.11 (encrypt sensitive data in transit and at rest) is the direct match for a file leaving the organization's control.

## What this doesn't check

Asset inventory, vulnerability management, and most of the 18 controls concern infrastructure and endpoint management this scan cannot see -- this speaks only to Control 3 (Data Protection)'s sharing/exposure angle. It also cannot see who a shared folder is shared with, or whether they are internal or external; directly shared files, and any sharing set above the top-level folder visible to the scanning user, are not detected.

## Recommended next steps

- Implement the full set of Control 3 safeguards appropriate to your Implementation Group (IG1-IG3), not just the three cited here.
- Extend the security program to the other 17 CIS Controls, which this scan has no visibility into at all.

## Source

Adapted from the CIS Controls v8 skill in the Claude Skills for Governance, Risk & Compliance library (`Sushegaad/Claude-Skills-Governance-Risk-and-Compliance`) -- <https://sushegaad.github.io/Claude-Skills-Governance-Risk-and-Compliance/> -- which offers much deeper advisory capability (policy/document drafting, licensing walkthroughs, breach-notification procedures) than a content-governance scan can ever provide.
