---
name: lgpd-compliance-check
description: >
  Use when the user asks to check Kiteworks content against LGPD (Brazil) --
  trigger phrases include `LGPD` `Brazil data protection` `ANPD` `LGPD compliance`. Scans and, on confirmation,
  writes a CSV + txt/pdf report. Single-phase: no separate "apply" step
  to ask for. Fit tier: Strong -- see below for what this can and can't
  actually check.
metadata:
  version: "0.3.3"
---

Delegate to the `lgpd-compliance-check` subagent on surfaces that support it (Claude Code, Cowork). If you already are that subagent, do not delegate again: follow this skill directly. If it reports no tools or fabricates results without tool calls, discard and check the `Kiteworks` connector. On other surfaces, follow this skill directly.

# LGPD (Brazil) Compliance Check -- fit tier: Strong

Read `../compliance-mapping/SKILL.md` first for the shared mechanism (signals A/B/C/D, report shape, honesty framing) -- this skill only supplies framework-specific content, never its own scanning logic.

## What LGPD (Brazil) actually is

Brazil's general data protection law, applying extraterritorially to any organization processing the personal data of individuals in Brazil.

## Signals this agent runs

Signals: **A, B, C, E (dormant)**. Signal A's default term list for this framework: "personal data", "dados pessoais", "sensitive data" (plus the built-in PII/secret presets, plus anything the user adds). When the content deep-scan runs, call `../term-sweep/scripts/pii_patterns.py` with `--framework=lgpd`: that adds the CPF and CNPJ presets (mod-11 check digits) and the email preset to the general built-in presets. Signal C's retention threshold: ask the user -- LGPD requires deletion once purpose is fulfilled, with no universal fixed number. Signal E (cross-border transfer) is dormant per `../compliance-mapping/SKILL.md` -- Art. 33 governs it, but no Kiteworks field to check it against exists today.

## Control citations

Drawn directly from the official LGPD text (Lei 13.709/2018, via planalto.gov.br; English mirror lgpd-brazil.info), not the third-party GRC skill library.

- **Signal A** (sensitive-content exposure): Art. 5(II) defines "dado pessoal sensível" (sensitive personal data -- health, biometric, racial/ethnic origin, religious/political/philosophical belief, union membership, genetic data, sex life), the basis for this signal's term list. Art. 46 requires security and technical measures to protect personal data from unauthorized access and accidental or unlawful destruction, loss, alteration, communication, or dissemination.
- **Signal B** (sharing exposure): Art. 46 again (protection against unauthorized "communication" -- i.e. disclosure); where a share crosses a border, Art. 33 lists the specific permitted cases for international transfer, but see Signal E below.
- **Signal C** (retention): Art. 16 -- personal data must be eliminated after the end of its processing, subject to four listed exceptions (legal obligation, anonymized research use, third-party transfer under LGPD's own rules, or the controller's own anonymized internal use).

## What this doesn't check

Legal-basis analysis, RIPD impact reports, and the 3-working-day ANPD breach deadline require legal judgment this scan cannot make -- this covers the same observable slice as GDPR. It also cannot see who a shared folder is shared with, or whether they are internal or external; directly shared files, and any sharing set above the top-level folder visible to the scanning user, are not detected.

## Recommended next steps

- Confirm a Data Protection Officer (encarregado) is appointed if required, and that legal basis under Art. 7 is documented for flagged content.
- Complete a RIPD (impact report) for any high-risk processing this scan surfaces.
- Verify ANPD breach-notification procedures meet the applicable deadline and are rehearsed, not just written.

## Source

Adapted from the LGPD (Brazil) skill in the Claude Skills for Governance, Risk & Compliance library (`Sushegaad/Claude-Skills-Governance-Risk-and-Compliance`) -- <https://sushegaad.github.io/Claude-Skills-Governance-Risk-and-Compliance/> -- which offers much deeper advisory capability (policy/document drafting, licensing walkthroughs, breach-notification procedures) than a content-governance scan can ever provide.
