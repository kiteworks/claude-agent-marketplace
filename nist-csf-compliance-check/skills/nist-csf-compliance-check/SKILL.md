---
name: nist-csf-compliance-check
description: >
  Use when the user asks to check Kiteworks content against NIST CSF --
  trigger phrases include `NIST CSF` `Cybersecurity Framework` `CSF 2.0` `Govern function` `cybersecurity profile`. Scans and, on confirmation,
  writes a CSV + txt/pdf report. Single-phase: no separate "apply" step
  to ask for. Fit tier: Light -- see below for what this can and can't
  actually check.
metadata:
  version: "0.3.3"
---

Delegate to the `nist-csf-compliance-check` subagent on surfaces that support it (Claude Code, Cowork). If it reports no tools or fabricates results without tool calls, discard and check the `Kiteworks` connector. On other surfaces, follow this skill directly.

# NIST CSF Compliance Check -- fit tier: Light

Read `../compliance-mapping/SKILL.md` first for the shared mechanism (signals A/B/C/D, report shape, honesty framing) -- this skill only supplies framework-specific content, never its own scanning logic.

## What NIST CSF actually is

NIST's Cybersecurity Framework -- Govern, Identify, Protect, Detect, Respond, Recover -- for describing and improving an organization's cybersecurity posture.

## Signals this agent runs

Signals: **B**.

## Control citations

Drawn directly from NIST CSF 2.0 (NIST.CSWP.29, February 2024), not the third-party GRC skill library.

- **Signal B** (sharing exposure): PR.DS-01 (the confidentiality, integrity, and availability of data-at-rest are protected) and PR.DS-02 (the confidentiality, integrity, and availability of data-in-transit are protected) are the two Protect-function subcategories a sharing-exposure check maps to most directly.

## What this doesn't check

NIST CSF describes an entire cybersecurity program across six functions; a file scan speaks only to a sliver of the Protect function's data-security expectations (PR.DS) via sharing exposure -- nothing about identification, detection, response, or recovery capability. It also cannot see who a shared folder is shared with, or whether they are internal or external; directly shared files, and any sharing set above the top-level folder visible to the scanning user, are not detected.

## Recommended next steps

- Complete a full CSF 2.0 profile across all 6 functions (Govern/Identify/Protect/Detect/Respond/Recover), not just the PR.DS subcategories this scan touches.
- Benchmark current implementation tier against the organization's target tier and prioritize gaps accordingly.

## Source

Adapted from the NIST CSF skill in the Claude Skills for Governance, Risk & Compliance library (`Sushegaad/Claude-Skills-Governance-Risk-and-Compliance`) -- <https://sushegaad.github.io/Claude-Skills-Governance-Risk-and-Compliance/> -- which offers much deeper advisory capability (policy/document drafting, licensing walkthroughs, breach-notification procedures) than a content-governance scan can ever provide.
