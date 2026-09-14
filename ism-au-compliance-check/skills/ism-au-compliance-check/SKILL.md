---
name: ism-au-compliance-check
description: >
  Use when the user asks to check Kiteworks content against ISM (Australia) --
  trigger phrases include `ISM` `Information Security Manual` `IRAP assessment` `Essential Eight`. Scans and, on confirmation,
  writes a CSV + txt/pdf report. Single-phase: no separate "apply" step
  to ask for. Fit tier: Light -- see below for what this can and can't
  actually check.
metadata:
  version: "0.4.4"
---

Delegate to the `ism-au-compliance-check` subagent on surfaces that support it (Claude Code, Cowork). If it reports no tools or fabricates results without tool calls, discard and check the `Kiteworks` connector. On other surfaces, follow this skill directly.

# ISM (Australia) Compliance Check -- fit tier: Light

Read `../compliance-mapping/SKILL.md` first for the shared mechanism (signals A/B/C/D, report shape, honesty framing) -- this skill only supplies framework-specific content, never its own scanning logic.

## What ISM (Australia) actually is

The Australian Signals Directorate's whole-of-government information security manual, covering classification handling from Unclassified through Top Secret.

## Signals this agent runs

Signals: **A, B**. Signal A's default term list for this framework: "PROTECTED", "SECRET", "OFFICIAL: Sensitive" (plus the built-in PII/secret presets, plus anything the user adds).

## Control citations

Fully confirmed this pass, down to a specific control ID. Drawn from the Australian Government Information Security Manual's "Guidelines for data transfers" chapter (ASD/cyber.gov.au), confirmed current as of the June 2026 edition.

- **Signal A/B**: **ISM-0661** -- "Users transferring data to and from systems are held accountable for data transfers they perform" (Revision 8, last updated March 2022, still listed in the June 2026 edition of the "Guidelines for data transfers" chapter) -- this is the specific control this skill's classification/sharing-exposure logic reflects, replacing the earlier principle-only citation. Related controls in the same chapter that reinforce the same behavior this scan flags: data exported from SECRET and TOP SECRET systems must be reviewed and authorised by a trusted source beforehand, and all data transfers must be logged. The ISM classifies information across five levels (OFFICIAL through TOP SECRET) and applies different control requirements by sensitivity, which is the basis for this skill's term list.

## What this doesn't check

System authorisation, IRAP assessment, and the 22 guideline chapters covering cryptography, networking, and hardening concern infrastructure this scan cannot see -- this only flags classification-marked content that's in a shared folder tree. It also cannot see who a shared folder is shared with, or whether they are internal or external; directly shared files, and any sharing set above the top-level folder visible to the scanning user, are not detected.

## Recommended next steps

- Engage an IRAP assessor if formal system authorization is required.
- Verify cryptographic protection controls meet current ASD-approved-cryptography guidance (renamed from "data protection" in the June 2026 ISM update).
- Confirm ISM-0661's accountability requirement and the SECRET/TOP SECRET trusted-source authorisation and logging requirements are met, which this scan cannot see directly.

## Source

Adapted from the ISM (Australia) skill in the Claude Skills for Governance, Risk & Compliance library (`Sushegaad/Claude-Skills-Governance-Risk-and-Compliance`) -- <https://sushegaad.github.io/Claude-Skills-Governance-Risk-and-Compliance/> -- which offers much deeper advisory capability (policy/document drafting, licensing walkthroughs, breach-notification procedures) than a content-governance scan can ever provide.
