---
name: iso42001-compliance-check
description: >
  Use when the user asks to check Kiteworks content against ISO 42001 --
  trigger phrases include `ISO 42001` `AI Management System` `AIMS` `AISIA` `AI governance standard`. Scans and, on confirmation,
  writes a CSV + txt/pdf report. Single-phase: no separate "apply" step
  to ask for. Fit tier: Light -- see below for what this can and can't
  actually check.
metadata:
  version: "0.4.4"
---

Delegate to the `iso42001-compliance-check` subagent on surfaces that support it (Claude Code, Cowork). If it reports no tools or fabricates results without tool calls, discard and check the `Kiteworks` connector. On other surfaces, follow this skill directly.

# ISO 42001 Compliance Check -- fit tier: Light

Read `../compliance-mapping/SKILL.md` first for the shared mechanism (signals A/B/C/D, report shape, honesty framing) -- this skill only supplies framework-specific content, never its own scanning logic.

## What ISO 42001 actually is

The first international standard for AI management systems (AIMS), covering AI risk assessment and impact assessment across the AI lifecycle.

## Signals this agent runs

Signals: **A, B**. Signal A's default term list for this framework: "training data", "model weights", "AI system", "algorithm" (plus the built-in PII/secret presets, plus anything the user adds).

## Control citations

Partial -- improved this pass to specific control numbers and titles, but still short of licensed clause text. ISO/IEC 42001:2023 is a paid standard (no free full-text mirror): Annex A has 38 controls across 9 control objectives (A.2 through A.10), and the AI System Impact Assessment is tied to Clauses 6.1.2 and 6.1.4 of the main management-system requirements -- both confirmed via the standard's own published structure.

This pass narrows the citation further within the **A.7 "Data for AI systems"** objective, the one that maps most directly to this skill's term list ("training data", "model weights", "algorithm"). Multiple independent certification-body/compliance-tooling sources (ISMS.online, Cyvitrix, Mindset Cyber) consistently identify the same control numbers and titles: **A.7.2** "Data for development and enhancement of AI systems," **A.7.3** "Acquisition of data," **A.7.4** "Quality of data for AI systems," and **A.7.5** "Data provenance." Control *titles* being corroborated across independent sources this way is the same level of confidence this project already extends to ISO 27001's Annex A titles elsewhere in this family -- but the operative clause *text* (what each control actually requires an organization to do) remains behind ISO's paywall, so this is a naming-level improvement, not a full-text citation. Closing that last step still requires purchasing the standard or securing access through a licensed party (the same wall documented for ISO 27701 in the Strong tier).

- **Signal A/B**: maps to the A.7.2-A.7.5 cluster above -- content in scope (training data descriptions, model weights, algorithm documentation) sits squarely within "data for AI systems," and a flagged file being in a shared folder tree intersects the same objective from an access-control angle, not a separate control.

## What this doesn't check

The formal AIMS certification process, the Statement of Applicability, and the AI System Impact Assessment (Clauses 6.1.2/6.1.4) require an accredited certification body and organizational risk-assessment work this scan cannot substitute for -- this only flags AI-development-related content (training data, model weights, algorithm documentation) that's in a shared folder tree or matches the term list, not conformance to the other 33 Annex A controls outside the A.7 cluster. It also cannot see who a shared folder is shared with, or whether they are internal or external; directly shared files, and any sharing set above the top-level folder visible to the scanning user, are not detected.

## Recommended next steps

- Complete a formal AI System Impact Assessment (Clauses 6.1.2/6.1.4) for any AI system this scan's findings relate to.
- Verify data-provenance documentation (A.7.5) exists for flagged training-data files, not just that they're present.
- If pursuing certification, engage an accredited certification body for the formal AIMS audit against the full (licensed) Annex A control text -- this scan's citations describe structure and control titles, not certified conformance.

## Source

Adapted from the ISO 42001 skill in the Claude Skills for Governance, Risk & Compliance library (`Sushegaad/Claude-Skills-Governance-Risk-and-Compliance`) -- <https://sushegaad.github.io/Claude-Skills-Governance-Risk-and-Compliance/> -- which offers much deeper advisory capability (policy/document drafting, licensing walkthroughs, breach-notification procedures) than a content-governance scan can ever provide.
