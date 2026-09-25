---
name: wcag-compliance-check
description: >
  Use when the user asks to check Kiteworks content against WCAG --
  trigger phrases include `WCAG` `WCAG 2.1` `WCAG 2.2` `web accessibility` `accessibility audit`. Scans and, on confirmation,
  writes a CSV + txt/pdf report. Single-phase: no separate "apply" step
  to ask for. Fit tier: Accessibility -- see below for what this can and can't
  actually check.
metadata:
  version: "0.5.0"
---

Delegate to the `wcag-compliance-check` subagent on surfaces that support it (Claude Code, Cowork). If you already are that subagent, do not delegate again: follow this skill directly. If it reports no tools or fabricates results without tool calls, discard and check the `Kiteworks` connector. On other surfaces, follow this skill directly.

# WCAG Compliance Check -- fit tier: Accessibility

Read `../compliance-mapping/SKILL.md` first for the shared mechanism (signals A/B/C/D, report shape, honesty framing) -- this skill only supplies framework-specific content, never its own scanning logic.

## What WCAG actually is

The W3C's Web Content Accessibility Guidelines (2.0/2.1/2.2) -- the technical foundation referenced by accessibility laws worldwide.

## Signals this agent runs

Signals: **D**.

## Control citations

Drawn directly from the W3C's WCAG 2.1 Recommendation (June 2018), not the third-party GRC skill library.

- **Signal D** (accessibility structure): 1.1.1 Non-text Content (Level A -- text alternatives for images/icons/charts), 1.3.1 Info and Relationships (Level A -- structure such as headings and tags is programmatically determinable, not just visual), 2.4.2 Page Titled (Level A -- a descriptive title for the page/document as a whole), and 3.1.1 Language of Page (Level A -- default human language is programmatically determinable) are the four Level-A success criteria closest to what the structural heuristic below actually tests for.

Which finding cites which criterion (use exactly these; do not improvise others):

| Finding | Cite | Why |
|---|---|---|
| Untagged PDF / no structure tree | 1.3.1 | Without tags, headings, lists and tables exist only visually (W3C technique PDF9 is a 1.3.1 technique). Not 4.1.2: that criterion is about UI components, which a static document does not have. |
| HTML heading level skipped (e.g. h1 -> h3) | 1.3.1 | Heading structure is information-and-relationships content (techniques H42, G141). You may add 2.4.6 Headings and Labels (Level AA) as a best-practice note, but do not report the skip as a 2.4.6 failure: 2.4.6 is about headings being descriptive, not about level order. |
| HTML page with no h1 | none (best practice) | WCAG does not require an h1. Report it as a best-practice note, not as a failure of any success criterion. |
| Slide with no title-placeholder text | 1.3.1 | A slide title is that slide's heading; text typed into a free text box instead of the title placeholder is not exposed as one. Not 2.4.2: W3C's Understanding SC 2.4.2 is about "each web page" having a title, and WCAG2ICT applies it to a non-web document as a whole, so for a deck it is the deck's Title metadata, not each slide. 2.4.6 (AA) may be added as a best-practice note. |
| Document/deck Title metadata or HTML `<title>` missing | 2.4.2 | The title of the document as a whole. |
| Language metadata or `<html lang>` missing | 3.1.1 | |
| Figures/images/picture shapes without alt text | 1.1.1 | |

This mapping was corrected on 2026-09-24: heading skips and untagged PDFs were previously cited as 4.1.2 and missing slide titles as 2.4.2. It has not yet been confirmed by an accessibility reviewer.

## Operational status: Operational (as of 2026-07-14)

Signal D now runs a real check -- `../compliance-mapping/scripts/accessibility_check.py` (pikepdf + python-docx + python-pptx, plus the stdlib `html.parser` for HTML) -- against every PDF/DOCX/PPTX/HTML file in scope, mapping directly to the four cited success criteria: tagged-PDF + structure tree presence, HTML heading hierarchy, or per-slide title placeholders (1.3.1, structure exposed to assistive technology), document/deck-level language metadata or `<html lang>` (3.1.1), Title metadata or `<title>` (2.4.2), and alt-text coverage on figures/inline images/picture shapes/`<img>` elements (1.1.1). Format coverage was PDF/DOCX-only from the 2026-07-14 launch through a same-day follow-up pass that added `.pptx` and `.html`/`.htm`. Before 2026-07-14 this signal was described but had no working implementation at all (`content-extract` is a text extractor: `pdftotext` for PDF and its own standard-library reader for DOCX, PPTX and XLSX, none of which can see PDF tag structure) -- treat any report or documentation from before that date as describing a check that did not actually run.

## What this doesn't check

Real WCAG conformance testing covers colour contrast, ARIA patterns, keyboard focus management, and live-region behaviour across interactive interfaces -- none of which a static document scan can evaluate, and the four cited success criteria are a small fraction of WCAG's full Level AA set (e.g. 1.4.3 Contrast Minimum is not checked at all). What now runs for real is limited to documents and static HTML pages (`.pdf`/`.docx`/`.pptx`/`.html`/`.htm`; no JavaScript-rendered content), not live web interfaces -- any other file type in scope is reported as explicitly skipped.

## Recommended next steps

- Commission real interactive-interface testing (colour-contrast analyzers, ARIA-pattern review, keyboard-focus and live-region testing) for any web property this scan's findings relate to -- a document-structure pass says nothing about a live web interface.
- Extend remediation beyond the four Level-A criteria checked here to the full WCAG 2.1/2.2 Level AA set actually required by most referencing laws (Section 508, EN 301 549, and similar).
- For any document flagged as untagged or missing alt text, remediate via Adobe Acrobat Pro's accessibility tools (PDF) or Word's built-in alt-text/accessibility checker (DOCX), then re-run this check to confirm.

## Source

Adapted from the WCAG skill in the Claude Skills for Governance, Risk & Compliance library (`Sushegaad/Claude-Skills-Governance-Risk-and-Compliance`) -- <https://sushegaad.github.io/Claude-Skills-Governance-Risk-and-Compliance/> -- which offers much deeper advisory capability (policy/document drafting, licensing walkthroughs, breach-notification procedures) than a content-governance scan can ever provide.

## Binary original lifetime

Follow `../content-extract/SKILL.md` and `../scratch-lifecycle/SKILL.md`. Use `--keep-source` while accessibility checks need the binary original; text extraction must not destroy it first. Reserve every staging/text/parser intermediate, release each in a consumer finally block after the last dependent check, and finalize the run. Preserve requested accessibility reports as deliverables. Report uncontrolled parser artifacts and cleanup failures separately from check results.
