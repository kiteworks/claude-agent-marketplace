---
name: vn-pdpl-compliance-check
description: >
  Use when the user asks to check Kiteworks content against Vietnam PDPL --
  trigger phrases include `Vietnam data privacy` `VN-PDPL` `Vietnam PDPL` `Vietnam data protection`. Scans and, on confirmation,
  writes a CSV + txt/pdf report. Single-phase: no separate "apply" step
  to ask for. Fit tier: Strong -- see below for what this can and can't
  actually check.
metadata:
  version: "0.4.4"
---

Delegate to the `vn-pdpl-compliance-check` subagent on surfaces that support it (Claude Code, Cowork). If you already are that subagent, do not delegate again: follow this skill directly. If it reports no tools or fabricates results without tool calls, discard and check the `Kiteworks` connector. On other surfaces, follow this skill directly.

# Vietnam PDPL Compliance Check -- fit tier: Strong

Read `../compliance-mapping/SKILL.md` first for the shared mechanism (signals A/B/C/D, report shape, honesty framing) -- this skill only supplies framework-specific content, never its own scanning logic.

## What Vietnam PDPL actually is

Vietnam's first comprehensive personal data protection law, applying extraterritorially to organizations processing Vietnamese citizens' data.

## Signals this agent runs

Signals: **A, B, C, E (dormant)**. Signal A's default term list for this framework: "personal data" (plus the built-in PII/secret presets, plus anything the user adds). When the content deep-scan runs, call `../term-sweep/scripts/pii_patterns.py` with `--framework=vn-pdpl`: that adds the Vietnamese CCCD preset (12 digits, documented province-code prefix) and the email preset to the general built-in presets. Signal C's retention threshold: ask the user -- the Act states a purpose-limitation retention principle, not a fixed number (see below). Signal E (cross-border transfer) is dormant per `../compliance-mapping/SKILL.md` -- Art. 20 governs it, but no Kiteworks field to check it against exists today.

## Control citations

Drawn from Vietnam's Law No. 91/2025/QH15 on Personal Data Protection, effective 1 January 2026 -- official English translation via english.luatvietnam.vn, LuatVietnam being the sole authorized distributor of Official Gazette English translations published by the Vietnam News Agency. This pass closes the citation gap the previous research left open: the general security-measure and retention obligations turned out to sit in Chapter I's principles article, not Chapter III as originally guessed.

- **Signal B** (sharing exposure / cross-border): Article 20 ("Cross-border transfer of personal data") defines cross-border transfer and the scenarios that qualify, plus the impact-assessment and periodic-inspection regime around it -- confirmed and citable to the article level.
- **Signal A** (general security measures): Article 3, Clause 4 ("Principles of personal data protection") requires agencies, organizations and individuals "to synchronously and effectively implement appropriate institutional, technical and human resource-related measures and solutions to protect personal data" -- this is the general security-measure obligation Signal A's content scan reflects, now confirmed to a specific clause.
- **Signal C** (retention): Article 3, Clause 3 requires data holders "to ensure the accuracy of personal data ... to store personal data for a period appropriate to the purpose of personal data processing, unless otherwise prescribed by law" -- confirmed to a specific clause. This is a purpose-based retention principle rather than a fixed figure, so this skill still asks the user for their own retention threshold rather than inventing a number -- the honest caveat about "no universal fixed number" still applies, but the citation itself is no longer a gap.
- **Correction from the prior research pass:** Chapter III of the Law ("Forces and Conditions to Ensure Personal Data Protection", Articles 33+) turned out, on a full read of the statute text, to cover designated personnel and the regulator -- not general security obligations. Those obligations sit in Chapter I (Article 3) instead. Noted here so a future pass doesn't re-search Chapter III for something that isn't there.

## What this doesn't check

Cross-border transfer impact assessments, DPIAs, and breach-notification timelines require legal and contextual judgment a file scan cannot make -- this only flags where personal data appears to live, whether it's in a shared folder tree, and whether it's older than the user's own stated retention policy. This covers the same observable slice as GDPR's storage-limitation and exposure concerns. It also cannot see who a shared folder is shared with, or whether they are internal or external; directly shared files, and any sharing set above the top-level folder visible to the scanning user, are not detected.

## Recommended next steps

- Complete a cross-border transfer impact assessment under Article 20 for any flagged content that in fact leaves Vietnam, once Signal E activates or is checked manually.
- Verify a documented retention schedule exists and matches what this scan found in practice -- Article 3, Clause 3's purpose-based principle requires one, even without a fixed number.
- Confirm the general security-measure obligation (Article 3, Clause 4) is actually implemented for flagged content, not just documented.

## Source

Adapted from the Vietnam PDPL skill in the Claude Skills for Governance, Risk & Compliance library (`Sushegaad/Claude-Skills-Governance-Risk-and-Compliance`) -- <https://sushegaad.github.io/Claude-Skills-Governance-Risk-and-Compliance/> -- which offers much deeper advisory capability (policy/document drafting, licensing walkthroughs, breach-notification procedures) than a content-governance scan can ever provide.
