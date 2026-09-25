---
name: iso27001-compliance-check
description: >
  Use when the user asks to check Kiteworks content against ISO 27001 --
  trigger phrases include `ISO 27001` `ISMS` `Annex A` `SoA` `gap analysis` `certification readiness`. Scans and, on confirmation,
  writes a CSV + txt/pdf report. Single-phase: no separate "apply" step
  to ask for. Fit tier: Light -- see below for what this can and can't
  actually check.
metadata:
  version: "0.3.3"
---

Delegate to the `iso27001-compliance-check` subagent on surfaces that support it (Claude Code, Cowork). If you already are that subagent, do not delegate again: follow this skill directly. If it reports no tools or fabricates results without tool calls, discard and check the `Kiteworks` connector. On other surfaces, follow this skill directly.

# ISO 27001 Compliance Check -- fit tier: Light

Read `../compliance-mapping/SKILL.md` first for the shared mechanism (signals A/B/C/D, report shape, honesty framing) -- this skill only supplies framework-specific content, never its own scanning logic.

## What ISO 27001 actually is

An international standard for information security management systems (ISMS), covering mandatory clauses and up to 93 Annex A controls (2022 edition).

## Signals this agent runs

Signals: **A, B**. When the content deep-scan runs, call `../term-sweep/scripts/pii_patterns.py` with `--framework=iso27001`: that adds the plaintext-credential preset (`password = <value>`-style assignments, placeholder values excluded) to the general built-in presets.

## Control citations

Drawn directly from ISO/IEC 27001:2022's own Annex A control list (the 93-control, 4-theme structure published alongside the standard), not the third-party GRC skill library.

- **Signal A** (sensitive-content exposure): A.5.12 (Classification of information) and A.5.13 (Labelling of information) govern how content like this should be marked; A.8.24 (Use of cryptography) governs how it should be protected once classified.
- **Signal B** (sharing exposure): A.5.14 (Information transfer) is the control that directly names electronic, physical, and verbal transfer of information as in scope -- sharing exposure is exactly this control's subject.

## What this doesn't check

Nearly all of ISO 27001's substance -- risk assessment methodology, the Statement of Applicability, and the other 90+ Annex A controls covering HR security, physical security, supplier relationships, incident management, and business continuity -- has no file-content or sharing-state signature at all. It also cannot see who a shared folder is shared with, or whether they are internal or external; directly shared files, and any sharing set above the top-level folder visible to the scanning user, are not detected.

## Recommended next steps

- Complete or update the Statement of Applicability against the full 93-control Annex A, not just the 3 cited here.
- Conduct an internal audit covering the People, Physical, and remaining Organizational controls this scan has no visibility into.
- Confirm management review and the risk treatment plan are current, not just the ISMS documentation.

## Source

Adapted from the ISO 27001 skill in the Claude Skills for Governance, Risk & Compliance library (`Sushegaad/Claude-Skills-Governance-Risk-and-Compliance`) -- <https://sushegaad.github.io/Claude-Skills-Governance-Risk-and-Compliance/> -- which offers much deeper advisory capability (policy/document drafting, licensing walkthroughs, breach-notification procedures) than a content-governance scan can ever provide.
