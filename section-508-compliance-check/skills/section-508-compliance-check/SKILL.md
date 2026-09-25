---
name: section-508-compliance-check
description: >
  Use when the user asks to check Kiteworks content against Section 508 --
  trigger phrases include `Section 508` `508 compliance` `VPAT` `ACR` `federal accessibility`. Scans and, on confirmation,
  writes a CSV + txt/pdf report. Single-phase: no separate "apply" step
  to ask for. Fit tier: Accessibility -- see below for what this can and can't
  actually check.
metadata:
  version: "0.5.0"
---

Delegate to the `section-508-compliance-check` subagent on surfaces that support it (Claude Code, Cowork). If you already are that subagent, do not delegate again: follow this skill directly. If it reports no tools or fabricates results without tool calls, discard and check the `Kiteworks` connector. On other surfaces, follow this skill directly.

# Section 508 Compliance Check -- fit tier: Accessibility

Read `../compliance-mapping/SKILL.md` first for the shared mechanism (signals A/B/C/D, report shape, honesty framing) -- this skill only supplies framework-specific content, never its own scanning logic.

## What Section 508 actually is

The US federal ICT accessibility standard, requiring federal web content, software, and documents to conform to WCAG 2.0 Level A/AA.

## Signals this agent runs

Signals: **D**.

## Control citations

Drawn directly from 36 CFR Part 1194 (the Access Board's 2017/2018 Section 508 Refresh, eCFR), not the third-party GRC skill library.

- **Signal D** (accessibility structure): 36 CFR 1194.1 and 1194.2, together with Appendix A, are what direct readers to the Revised 508 Standards, which incorporate WCAG 2.0 Level A and AA Success Criteria by reference for web content -- meaning a Section 508 document check is, at the technical level, a WCAG 2.0 A/AA check. See the WCAG skill's own citations for the specific success criteria this heuristic could reach if implemented.

## Operational status: Operational (as of 2026-07-14)

Signal D now runs a real check -- `../compliance-mapping/scripts/accessibility_check.py` (pikepdf + python-docx + python-pptx, plus the stdlib `html.parser` for HTML) -- against every PDF/DOCX/PPTX/HTML file in scope: whether a PDF is genuinely tagged (`MarkInfo.Marked` + a real `StructTreeRoot`), document/deck-level language and Title metadata (PDF/DOCX/PPTX), per-slide title coverage (PPTX), heading-level hierarchy and `<html lang>`/`<title>` presence (HTML), and alt-text coverage on figures/inline images/picture shapes/`<img>` elements. Format coverage was PDF/DOCX-only from the 2026-07-14 launch through a same-day follow-up pass that added `.pptx` and `.html`/`.htm`. Before 2026-07-14 this signal was described but had no working implementation at all (`content-extract` is a text extractor: `pdftotext` for PDF and its own standard-library reader for DOCX, PPTX and XLSX, none of which can see PDF tag structure) -- treat any report or documentation from before that date as describing a check that did not actually run.

## What this doesn't check

A real Section 508 conformance review -- VPAT/ACR completion, screen-reader testing with JAWS/NVDA/VoiceOver, keyboard-navigation testing, colour contrast, focus order across interactive interfaces -- requires interactive tools and human review this scan cannot replace. What now runs for real is a structural heuristic (tagged-PDF detection, title/language metadata, alt-text presence, plus per-slide title and HTML heading-hierarchy checks) over documents and HTML pages in scope, which is a small fraction of real conformance testing, and only covers `.pdf`/`.docx`/`.pptx`/`.html`/`.htm` -- any other file type in scope is reported as explicitly skipped.

## Recommended next steps

- Commission real assistive-technology testing (JAWS/NVDA/VoiceOver screen-reader passes, keyboard-only navigation testing) for any system or document set this scan flags -- a structural pass is not a substitute for a human conformance review.
- Complete or update a VPAT/ACR for any federally-procured ICT this scan's findings relate to.
- For any PDF flagged as untagged, remediate via Adobe Acrobat Pro's accessibility tools or an equivalent PDF/UA remediation workflow, then re-run this check to confirm.

## Source

Adapted from the Section 508 skill in the Claude Skills for Governance, Risk & Compliance library (`Sushegaad/Claude-Skills-Governance-Risk-and-Compliance`) -- <https://sushegaad.github.io/Claude-Skills-Governance-Risk-and-Compliance/> -- which offers much deeper advisory capability (policy/document drafting, licensing walkthroughs, breach-notification procedures) than a content-governance scan can ever provide.

## Binary original lifetime

Follow `../content-extract/SKILL.md` and `../scratch-lifecycle/SKILL.md`. Use `--keep-source` while accessibility checks need the binary original; text extraction must not destroy it first. Reserve every staging/text/parser intermediate, release each in a consumer finally block after the last dependent check, and finalize the run. Preserve requested accessibility reports as deliverables. Report uncontrolled parser artifacts and cleanup failures separately from check results.
