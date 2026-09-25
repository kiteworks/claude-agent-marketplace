---
name: itar-compliance-check
description: >
  Use when the user asks to check Kiteworks content against ITAR --
  trigger phrases include `ITAR` `USML` `DDTC` `defense export` `deemed export` `technical assistance agreement`. Scans and, on confirmation,
  writes a CSV + txt/pdf report. Single-phase: no separate "apply" step
  to ask for. Fit tier: Good -- see below for what this can and can't
  actually check.
metadata:
  version: "0.3.3"
---

Delegate to the `itar-compliance-check` subagent on surfaces that support it (Claude Code, Cowork). If you already are that subagent, do not delegate again: follow this skill directly. If it reports no tools or fabricates results without tool calls, discard and check the `Kiteworks` connector. On other surfaces, follow this skill directly.

# ITAR Compliance Check -- fit tier: Good

Read `../compliance-mapping/SKILL.md` first for the shared mechanism (signals A/B/C/D, report shape, honesty framing) -- this skill only supplies framework-specific content, never its own scanning logic.

## What ITAR actually is

US defense export controls (22 CFR Parts 120-130) governing defense articles, services, and technical data on the US Munitions List.

## Signals this agent runs

Signals: **A, B, E (dormant)**. Signal A's default term list for this framework: "ITAR", "USML", "technical data", "defense article", "export controlled", "technical assistance agreement" (plus the built-in PII/secret presets, plus anything the user adds). Signal E (deemed-export exposure) is dormant per `../compliance-mapping/SKILL.md` -- see the important cap below on what it could ever actually tell you, even active.

## Control citations

Drawn directly from 22 CFR Part 120 (via eCFR), not the third-party GRC skill library.

- **Signal A** (technical-data content exposure): 22 CFR §120.43 and Part 121 (the US Munitions List) define "technical data" -- content that appears to match is what this signal flags.
- **Signal B / Signal E** (sharing, and deemed export specifically): 22 CFR §120.50(b) is the controlling deemed-export rule -- release of technical data to a foreign person, even entirely within the US, is treated as an export to every country of that person's citizenship or permanent residency. §120.54 carves out narrow exceptions (e.g. certain encrypted transmissions are not treated as exports at all).
- **Important cap on Signal E, even fully activated:** deemed-export status turns on a recipient's actual citizenship/residency, not on any field a file-sharing platform could ever responsibly hold. Even if Kiteworks eventually exposes a "recipient country" field, that's a mailing-address-adjacent proxy at best -- it is never a substitute for real §120.50(b) screening, and this agent must never imply otherwise.

## What this doesn't check

USML jurisdiction analysis, DDTC registration, export licensing, and Technology Control Plans require legal determination this scan cannot make -- this only flags where ITAR-related technical data appears to live or sit in a shared folder tree (the file-sharing analogue of a deemed-export risk, although this scan cannot tell whether a share reaches parties outside the organization). It also cannot see who a shared folder is shared with, or whether they are internal or external; directly shared files, and any sharing set above the top-level folder visible to the scanning user, are not detected.

## Recommended next steps

- Verify any flagged technical data has a current export license or applicable agreement (TAA/MLA) covering its disclosure.
- Confirm the organization's Technology Control Plan addresses the specific sharing pattern this scan found.
- Verify no foreign-person access exists for flagged content without a §120.50(b)-compliant license or exemption -- this scan cannot determine citizenship, only sharing.

## Source

Adapted from the ITAR skill in the Claude Skills for Governance, Risk & Compliance library (`Sushegaad/Claude-Skills-Governance-Risk-and-Compliance`) -- <https://sushegaad.github.io/Claude-Skills-Governance-Risk-and-Compliance/> -- which offers much deeper advisory capability (policy/document drafting, licensing walkthroughs, breach-notification procedures) than a content-governance scan can ever provide.
