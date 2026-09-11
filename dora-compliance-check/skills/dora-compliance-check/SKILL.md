---
name: dora-compliance-check
description: >
  Use when the user asks to check Kiteworks content against DORA --
  trigger phrases include `DORA` `digital operational resilience` `ICT risk management` `Register of Information`. Scans and, on confirmation,
  writes a CSV + txt/pdf report. Single-phase: no separate "apply" step
  to ask for. Fit tier: Good -- see below for what this can and can't
  actually check.
metadata:
  version: "0.5.0"
---

Delegate to the `dora-compliance-check` subagent on surfaces that support it (Claude Code, Cowork). If it reports no tools or fabricates results without tool calls, discard and check the `Kiteworks` connector. On other surfaces, follow this skill directly.

# DORA Compliance Check -- fit tier: Good

Read `../compliance-mapping/SKILL.md` first for the shared mechanism (signals A/B/C/D/E, report shape, honesty framing) -- this skill only supplies framework-specific content, never its own scanning logic.

## What DORA actually is

The EU's Digital Operational Resilience Act for financial entities, covering ICT risk management, incident reporting, digital operational resilience testing, and third-party risk.

## Signals this agent runs

Signals: **A, B, C, E (dormant)**. Signal A's default term list for this framework: "ICT risk management framework", "critical or important function", "ICT third-party service provider", "vulnerability assessment", "legacy ICT system" (plus the built-in PII/secret presets, plus anything the user adds). Signal C's retention threshold: **365 days, fixed -- never ask the user.** Article 8(1) states a concrete annual cadence for its own documentation, so this is bucket 3 of the general Signal C policy in `../compliance-mapping/SKILL.md`, not bucket 2 -- the framework already answered the question. Signal E (cross-border/location) is dormant per `../compliance-mapping/SKILL.md` -- Art. 30(2)(b) requires financial entities to know the region/country where contracted data is processed and stored, but no Kiteworks field to check it against exists today.

## Control citations

Fully confirmed this pass, upgraded from Signal-B-only. Drawn from Regulation (EU) 2022/2554 (DORA) -- official text at EUR-Lex, OJ L 333, 27.12.2022, p. 1-79; article text cross-checked against the consolidated article-by-article mirror at digital-operational-resilience-act.com.

- **Signal A** (ICT asset/risk content): Article 8 ("Identification"), paragraphs 1, 2, 4 and 5 -- financial entities must "identify, classify and adequately document all ICT supported business functions, roles and responsibilities, the information assets and ICT assets supporting those functions," continuously "identify all sources of ICT risk" and "assess cyber threats and ICT vulnerabilities," map which assets are "critical," and separately "identify and document all processes that are dependent on ICT third-party service providers" and "interconnections with ICT third-party service providers that provide services that support critical or important functions." This is the direct source of this skill's term list -- content discussing ICT asset inventories, critical-function mapping, vulnerability assessments, or third-party ICT dependencies sits squarely within Article 8's identification obligation.
- **Signal B** (external sharing): Article 28 ("General principles", Register of Information) requires financial entities to maintain and report a register of all ICT third-party arrangements, including documentation and yearly reporting obligations -- a file documenting such an arrangement being shared externally is squarely within its scope. Article 9 ("Protection and prevention") requires financial entities to continuously monitor and control the security of ICT systems and maintain "high standards of availability, authenticity, integrity and confidentiality of data, whether at rest, in use or in transit" -- a file containing such at-risk data being shared externally sits within Art. 9's protection objective. Article 30 ("Key contractual provisions"), paragraph 2(b), additionally requires that ICT third-party contracts document "the locations, namely the regions or countries, where the contracted or subcontracted functions and ICT services are to be provided and where data is to be processed, including the storage location" -- a contract or location schedule containing this information being shared externally is the same exposure concern from a different angle.
- **Signal C** (documentation-currency, fixed cadence): Article 8(1)'s last sentence -- financial entities "shall review as needed, and **at least yearly**, the adequacy of this classification and of any relevant documentation" -- states a concrete annual cadence for the same asset/business-function documentation Signal A's term list targets. Article 8(2) and 8(7) apply the identical "at least yearly" cadence to risk-scenario review and legacy-ICT-system risk assessment respectively, reinforcing that DORA's own text treats "yearly" as its standard review interval for this class of documentation, not a one-off suggestion. **365 days is used directly as the cutoff -- this skill never asks the user for a different number**, per the general Signal C policy's bucket 3 (framework states a concrete cadence). **Anchor field: `created` alone.** DORA's own text does not contain "whichever is later" or equivalent phrasing the way HIPAA's 45 CFR §164.316(b)(2)(i) explicitly does, so per `../compliance-mapping/SKILL.md`'s 2026-07-24 correction, the `max(created, modified)` logic does not apply here -- do not borrow HIPAA's anchor rule onto DORA just because both happen to have a fixed number. **Known limitation, state it in the report:** because only `created` is checked, a document that was reviewed or updated more recently than it was originally created could be flagged as apparently overdue by this proxy even if its content is in fact current -- this scan cannot see review history, only file age, so a flagged item should be verified against the entity's actual Art. 8(1) review record before being treated as a real gap.
- **Signal E** (dormant, cross-border/location): Article 30(2)(b), quoted above under Signal B, is also the citation for Signal E once it activates -- it's the same clause that makes *location* itself, not just external sharing, a documented DORA concern.

## What this doesn't check

ICT incident classification and reporting, the Register of Information's actual completeness (Art. 28), digital operational resilience testing / TLPT programmes (Art. 24-27), the specific contractual-clause-by-clause review Art. 30 otherwise requires, and third-party concentration-risk assessment are entirely outside file-scan visibility -- this only flags ICT-asset/risk-related content that's externally shared, matches the term list, or is older than a year since last review, never whether an organization's actual ICT risk management framework or third-party contracts are DORA-conformant.

## Recommended next steps

- Complete or update the Register of Information (Art. 28) to reflect any ICT third-party arrangement this scan's findings relate to.
- Verify ICT security policies required under Art. 9 (information security policy, access control, authentication, change management, patch management) are actually documented and current for flagged content, not just present.
- Confirm flagged asset/business-function documentation older than a year has, in fact, had its classification adequacy reviewed per Art. 8(1) -- this scan's age check is a proxy for that review, not proof it happened.
- Review ICT third-party contracts for the full Art. 30(2)/(3) clause set (location, audit rights, exit strategy, TLPT cooperation) -- this scan cannot read or verify individual contract clauses.
- If cross-border/location tracking matters now, verify data-processing and storage locations manually per Art. 30(2)(b) until Signal E activates.

## Source

Adapted from the DORA skill in the Claude Skills for Governance, Risk & Compliance library (`Sushegaad/Claude-Skills-Governance-Risk-and-Compliance`) -- <https://sushegaad.github.io/Claude-Skills-Governance-Risk-and-Compliance/> -- which offers much deeper advisory capability (policy/document drafting, licensing walkthroughs, breach-notification procedures) than a content-governance scan can ever provide.
