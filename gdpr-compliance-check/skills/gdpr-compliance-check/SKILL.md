---
name: gdpr-compliance-check
description: >
  Use when the user asks to check Kiteworks content against GDPR --
  trigger phrases include `GDPR` `data protection` `personal data` `DPIA` `data subject rights` `RoPA`. Scans and, on confirmation,
  writes a CSV + txt/pdf report. Single-phase: no separate "apply" step
  to ask for. Fit tier: Strong -- see below for what this can and can't
  actually check.
metadata:
  version: "0.3.3"
---

Delegate to the `gdpr-compliance-check` subagent on surfaces that support it (Claude Code, Cowork). If you already are that subagent, do not delegate again: follow this skill directly. If it reports no tools or fabricates results without tool calls, discard and check the `Kiteworks` connector. On other surfaces, follow this skill directly.

# GDPR Compliance Check -- fit tier: Strong

Read `../compliance-mapping/SKILL.md` first for the shared mechanism (signals A/B/C/D, report shape, honesty framing) -- this skill only supplies framework-specific content, never its own scanning logic.

## What GDPR actually is

The EU's comprehensive data protection regulation covering lawful basis, consent, data subject rights, and the storage-limitation principle for personal data.

## Signals this agent runs

Signals: **A, B, C, E (dormant)**. Signal A's default term list for this framework: "personal data", "special category data", "health data", "biometric", "racial or ethnic origin" (plus the built-in PII/secret presets, plus anything the user adds). When the content deep-scan runs, call `../term-sweep/scripts/pii_patterns.py` with `--framework=gdpr`: that adds the email preset to the general built-in presets. Signal C's retention threshold: GDPR sets no fixed number -- Art. 5(1)(e) storage limitation requires data kept 'no longer than necessary'; ask the user for their own documented retention schedule. Signal E (cross-border transfer) is dormant per `../compliance-mapping/SKILL.md` -- Art. 44 governs it, but no Kiteworks field to check it against exists today.

## Control citations

Drawn directly from the official GDPR text (EUR-Lex / gdpr-info.eu), not the third-party GRC skill library.

- **Signal A** (sensitive-content exposure): Art. 9 defines the special categories of personal data this signal's term list targets (health, biometric, racial/ethnic origin, religious/political belief, genetic data, sex life/orientation). Art. 5(1)(f) and Art. 32 (security of processing) govern the obligation to protect that content once found.
- **Signal B** (sharing exposure): Art. 32 (security of processing, including access control) for any sharing; where a shared file crosses a border, Art. 44 (general principle for transfers -- permitted only where the conditions of Chapter V are met) is the relevant article, but see Signal E below for why this scan can't detect *where* a share goes today.
- **Signal C** (retention): Art. 5(1)(e), storage limitation -- as stated above.

## What this doesn't check

Lawful-basis determination, consent-mechanism validity, DPIAs, international-transfer safeguards, and breach-notification timelines all require legal and contextual judgment a file scan cannot make -- this only flags where personal data appears to live, whether it's in a shared folder tree, and whether it's older than the user's own stated retention policy. It also cannot see who a shared folder is shared with, or whether they are internal or external; directly shared files, and any sharing set above the top-level folder visible to the scanning user, are not detected.

## Recommended next steps

- Complete a formal Data Protection Impact Assessment (DPIA) for any high-risk processing this scan's findings relate to.
- Verify lawful basis is documented for each processing activity involving flagged content, not assumed.
- Confirm Art. 30 records of processing activities are current and reflect what this scan found.
- If Signal E ever activates, treat any cross-border finding as a starting point for a real Art. 44-49 transfer-mechanism review (SCCs, adequacy decision, BCRs) -- never as the review itself.

## Source

Adapted from the GDPR skill in the Claude Skills for Governance, Risk & Compliance library (`Sushegaad/Claude-Skills-Governance-Risk-and-Compliance`) -- <https://sushegaad.github.io/Claude-Skills-Governance-Risk-and-Compliance/> -- which offers much deeper advisory capability (policy/document drafting, licensing walkthroughs, breach-notification procedures) than a content-governance scan can ever provide.
