---
name: ear-compliance-check
description: >
  Use when the user asks to check Kiteworks content against EAR --
  trigger phrases include `EAR` `Export Administration Regulations` `ECCN` `EAR99` `BIS`. Scans and, on confirmation,
  writes a CSV + txt/pdf report. Single-phase: no separate "apply" step
  to ask for. Fit tier: Good -- see below for what this can and can't
  actually check.
metadata:
  version: "0.3.3"
---

Delegate to the `ear-compliance-check` subagent on surfaces that support it (Claude Code, Cowork). If you already are that subagent, do not delegate again: follow this skill directly. If it reports no tools or fabricates results without tool calls, discard and check the `Kiteworks` connector. On other surfaces, follow this skill directly.

# EAR Compliance Check -- fit tier: Good

Read `../compliance-mapping/SKILL.md` first for the shared mechanism (signals A/B/C/D, report shape, honesty framing) -- this skill only supplies framework-specific content, never its own scanning logic.

## What EAR actually is

US dual-use export controls (15 CFR Parts 730-774) administered by the Bureau of Industry and Security, covering ECCN classification and licensing.

## Signals this agent runs

Signals: **A, B, E (dormant)**. Signal A's default term list for this framework: "ECCN", "EAR99", "dual-use", "export controlled", "encryption technology" (plus the built-in PII/secret presets, plus anything the user adds). Signal E (deemed-export exposure) is dormant per `../compliance-mapping/SKILL.md` -- see the important cap below on what it could ever actually tell you, even active.

## Control citations

Drawn directly from 15 CFR Parts 734 and 736 (via eCFR and bis.gov), not the third-party GRC skill library.

- **Signal A** (controlled-technology content exposure): 15 CFR §734.13 defines "technology" and the deemed-export concept via "release" -- release includes visual inspection, verbal/oral exchange, and electronic transmission (email, shared screens), which is a notably broad definition for a file-sharing context to keep in mind.
- **Signal B / Signal E** (sharing, and deemed export specifically): 15 CFR §736.2(b)(10) is the general prohibition -- a deemed export/reexport of controlled technology to a foreign person requires a license absent an exception, and §734.13's "release" definition (above) is what triggers it.
- **Important cap on Signal E, even fully activated:** deemed-export status turns on a recipient's actual nationality, not on any field a file-sharing platform could ever responsibly hold. This agent must never imply a "recipient country" field, even once Kiteworks exposes one, closes this gap.

## What this doesn't check

ECCN classification, licence-exception analysis, and restricted-party screening require legal determination this scan cannot make -- this only flags where export-controlled technology descriptions appear to live or be shared, similar to the ITAR check. It also cannot see who a shared folder is shared with, or whether they are internal or external; directly shared files, and any sharing set above the top-level folder visible to the scanning user, are not detected.

## Recommended next steps

- Classify any flagged content under the correct ECCN using the Commerce Control List, rather than assuming EAR99.
- Verify deemed-export licensing is in place where foreign nationals have access to controlled technology this scan flagged.
- Confirm the term list and classifications used here reflect the most current CCL revision -- the CCL is amended more frequently than ITAR's USML.

## Source

Adapted from the EAR skill in the Claude Skills for Governance, Risk & Compliance library (`Sushegaad/Claude-Skills-Governance-Risk-and-Compliance`) -- <https://sushegaad.github.io/Claude-Skills-Governance-Risk-and-Compliance/> -- which offers much deeper advisory capability (policy/document drafting, licensing walkthroughs, breach-notification procedures) than a content-governance scan can ever provide.
