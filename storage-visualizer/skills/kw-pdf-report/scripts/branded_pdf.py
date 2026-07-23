#!/usr/bin/env python3
"""Shared branded, overlap-safe PDF builder for kiteworks-agents reports.

Four problems this solves at once:

1. Brand consistency -- follows kw-brand-visual's OWN documented rules
   (references/colors-and-type.css's print/paper tokens, the "dark hero
   header with white inline logo" structure in rules/logo-usage.md, the
   "soft radial glows, blue + violet, low opacity" hero-surface recipe in
   rules/visual-foundations.md), not an invented palette or a flat block
   of solid accent color where the brand doesn't actually use one.

2. The table-text-overlap bug -- reportlab's Table() does NOT word-wrap
   plain strings. safe_table() wraps every cell in a Paragraph and sizes
   columns to fit the page.

3. Reports need to say who ran them and what they scanned. Every report
   carries a "Report details" block right under the hero, BEFORE any
   findings. standard_metadata() builds the generic part of that block
   (scope folder + link, where the report was saved + link, who ran it,
   when) that is the SAME for every agent -- each agent then appends its
   own specific rows (term list, retention threshold, time window, ...).

4. The hero band and the descriptive report title were overlapping and
   near-duplicate text (agent name eyebrow vs. "<Agent> Report" title
   stacked too close together). Fixed by making the hero pure brand
   identity -- logo + agent-name label, nothing else -- and moving the
   actual descriptive title into the body, as the first thing after the
   hero, where there's no positioning conflict.

5. Portable reports need the same legal limitation users accepted at install.
   Marketplace publishing stamps that single-source legal layer into this module;
   every PDF page renders it in the footer, outside caller control. The caller
   must still provide this plugin's own scope caveat.

Usage (see also SKILL.md):
    from branded_pdf import build_branded_pdf, safe_table, standard_metadata

    metadata = standard_metadata(
        scope_label="Folder scanned",
        scope_name="My Folder/Marketing Drafts",
        scope_link="https://kiteworks.example.com/folder/123",
        output_folder_name="My Folder/Agents/Sensitive Content Scanner",
        output_folder_link="https://kiteworks.example.com/folder/456",
        scanned_by="Rick Goud (rick.goud@kiteworks.com)",
        generated_on="2026-07-14",
    ) + [
        ("Terms / patterns checked", "confidential, ITAR; built-in: SSN, BSN, credit card, IBAN, AWS key (all checked by default)"),
    ]

    build_branded_pdf(
        output_path="/tmp/report.pdf",
        agent_name="Sensitive Content Scanner",
        report_title="Sensitive Content Scan Report",
        metadata=metadata,
        sections=[
            {"heading": "Summary", "paragraph": "12 of 340 files flagged..."},
            {"heading": "Flagged items", "table": {
                "data": [["File", "Path", "Match", "Link"], [...], ...],
                "col_widths_frac": [0.25, 0.35, 0.15, 0.25],
            }},
        ],
        scope_caveat="Plugin-specific scope caveat...",
    )
"""
import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
LOGO_WHITE_PATH = os.path.join(ASSETS_DIR, "kw-logo-white.png")
HERO_BG_PATH = os.path.join(ASSETS_DIR, "hero-bg.png")

# -- Brand tokens, taken directly from kw-brand-visual's own tokens/rules.
DEEP_SPACE = colors.HexColor("#050821")       # --kw-deep-space -- hero band fallback fill
ELECTRIC_INDIGO = colors.HexColor("#4D60FB")  # --kw-electric-indigo -- accent, used as TEXT/label/link color, not a big solid fill
FG_LINK = colors.HexColor("#4D60FB")          # --fg-link (same value as Electric Indigo, its own documented token)
MIST = colors.HexColor("#EFF2FF")             # --kw-mist -- light neutral tint, table header background
SIGNAL_GOLD = colors.HexColor("#FDCA13")      # --kw-signal-gold -- secondary accent, used sparingly
MUTED_LAVENDER = colors.HexColor("#B5BCF2")   # --kw-blue-200 / muted-lavender -- metadata on dark
BG_PAPER = colors.white                       # --bg-paper -- print/document background
BG_PAPER_SOFT = colors.HexColor("#E8EAF4")    # --bg-paper-soft -- zebra striping on paper
FG_PAPER_1 = colors.HexColor("#050821")       # --fg-paper-1 -- primary text on paper
FG_PAPER_2 = colors.HexColor("#505264")       # --fg-paper-2 (rgba(5,8,33,0.70) flattened onto white)
BORDER_PAPER = colors.HexColor("#D1D5DC")     # --border-paper -- rules/grid lines on paper

PAGE_SIZE = letter
PAGE_W, PAGE_H = PAGE_SIZE
MARGIN = 0.75 * inch
HERO_HEIGHT = 0.95 * inch  # logo + eyebrow only now -- no title crammed in here

LEGAL_DISCLAIMER = 'Kiteworks agents are provided **as is**. They are helpful, but they can be wrong. You are responsible for checking what an agent produces before you rely on it, and Kiteworks is not liable for outcomes from using them.'

FONT_BODY = "Helvetica"
FONT_BODY_BOLD = "Helvetica-Bold"
FONT_MONO = "Courier"
FONT_MONO_BOLD = "Courier-Bold"

_hero_eyebrow_style = ParagraphStyle(
    "kw_hero_eyebrow", fontName=FONT_MONO, fontSize=9, leading=12, textColor=MUTED_LAVENDER,
)
_doc_title_style = ParagraphStyle(
    "kw_doc_title", fontName=FONT_BODY_BOLD, fontSize=18, leading=22, textColor=FG_PAPER_1, spaceAfter=10,
)
_section_title_style = ParagraphStyle(
    "kw_section_title", fontName=FONT_BODY_BOLD, fontSize=16, leading=19, textColor=FG_PAPER_1, spaceBefore=14, spaceAfter=6,
)
_body_style = ParagraphStyle(
    "kw_body", fontName=FONT_BODY, fontSize=10, leading=14, textColor=FG_PAPER_1, spaceAfter=8,
)
_cell_style = ParagraphStyle(
    "kw_cell", fontName=FONT_BODY, fontSize=8.5, leading=11, textColor=FG_PAPER_1,
)
_header_cell_style = ParagraphStyle(
    "kw_header_cell", fontName=FONT_MONO_BOLD, fontSize=9, leading=11, textColor=ELECTRIC_INDIGO,
)
_meta_label_style = ParagraphStyle(
    "kw_meta_label", fontName=FONT_MONO, fontSize=8.5, leading=13, textColor=FG_PAPER_2,
)
_meta_value_style = ParagraphStyle(
    "kw_meta_value", fontName=FONT_BODY, fontSize=9.5, leading=13, textColor=FG_PAPER_1,
)
_disclaimer_style = ParagraphStyle(
    "kw_disclaimer", fontName=FONT_BODY, fontSize=8, leading=11, textColor=FG_PAPER_2, spaceBefore=10,
)
_legal_footer_style = ParagraphStyle(
    "kw_legal_footer", fontName=FONT_BODY, fontSize=6.25, leading=7.5,
    textColor=FG_PAPER_2,
)
_badge_style = ParagraphStyle(
    "kw_badge", fontName=FONT_MONO_BOLD, fontSize=8, leading=10, textColor=ELECTRIC_INDIGO,
)
_badge_warn_style = ParagraphStyle(
    "kw_badge_warn", fontName=FONT_MONO_BOLD, fontSize=8, leading=10, textColor=DEEP_SPACE,
)
_note_heading_style = ParagraphStyle(
    "kw_note_heading", fontName=FONT_MONO_BOLD, fontSize=9.5, leading=13, textColor=FG_PAPER_1, spaceAfter=3,
)
_note_body_style = ParagraphStyle(
    "kw_note_body", fontName=FONT_BODY, fontSize=9, leading=13, textColor=FG_PAPER_1,
)

# Fit tier -> badge label (operational-status colors are semantic, fit-tier is always neutral brand accent)
FIT_TIER_LABELS = {
    "strong": "FIT TIER: STRONG", "good": "FIT TIER: GOOD", "light": "FIT TIER: LIGHT",
    "accessibility": "FIT TIER: ACCESSIBILITY", "minimal": "FIT TIER: MINIMAL",
}
OPERATIONAL_STATUS_LABELS = {
    "operational": "STATUS: OPERATIONAL",
    "partially operational": "STATUS: PARTIALLY OPERATIONAL",
    "not yet operational": "STATUS: NOT YET OPERATIONAL",
}


def _printable_width():
    return PAGE_W - 2 * MARGIN


def _linkify(text, url):
    """Render `text` as a real clickable hyperlink to `url`, styled with
    the brand's own --fg-link token (same value as Electric Indigo).
    Falls back to plain text if no url is given."""
    if not url:
        return text
    return '<a href="%s" color="#4D60FB"><u>%s</u></a>' % (url, text)


def standard_metadata(scope_label, scope_name, scanned_by, generated_on,
                       scope_link=None, output_folder_name=None, output_folder_link=None,
                       extra_scope_label_suffix=None):
    """The GENERIC part of every report's "Report details" block -- the
    same shape for every agent in this plugin, so no agent has to
    reimplement it. `scope_label` lets each agent phrase the scope row in
    a way that fits it ("Folder scanned" for a scanner, "Folder reviewed"
    for naming-cleanup, "Person" for offboarding-content-finder, etc.)
    while everything else about the row (link handling, position, style)
    stays identical.

    Returns a list of (label, value) tuples ready to pass straight into
    `build_branded_pdf`'s `metadata` argument, or to extend with the
    agent-specific rows only that agent needs (e.g. term list, retention
    threshold, time window) -- append those after calling this."""
    rows = [(scope_label, _linkify(scope_name, scope_link) if scope_link else scope_name)]
    if output_folder_name:
        rows.append(("Report saved in", _linkify(output_folder_name, output_folder_link) if output_folder_link else output_folder_name))
    rows.append(("Scanned by", scanned_by))
    rows.append(("Generated", generated_on))
    return rows


def safe_table(data, col_widths_frac=None, header=True):
    """Build a reportlab Table that word-wraps every cell instead of
    overflowing/overlapping. `data` is a list of rows (list of strings);
    the first row is treated as the header if header=True. Header cell
    text is uppercased -- per kw-brand-visual's case rule, ALL-CAPS is used
    only for Geist Mono labels (which is the role a table header plays),
    never for Host Grotesk body/headings. Header background is a flat
    light neutral (Mist) with Electric Indigo text -- NOT a solid indigo
    block, since the brand uses that accent as a glow/label color, not a
    giant flat fill (see visual-foundations.md).
    `col_widths_frac`, if given, must be a list of fractions summing to
    ~1.0, one per column -- use this when one column (e.g. a file path)
    needs much more room than the others; equal-width division is the
    default and is usually wrong for mixed short/long columns."""
    if not data:
        return None

    n_cols = len(data[0])
    width = _printable_width()

    if col_widths_frac:
        if len(col_widths_frac) != n_cols:
            raise ValueError("col_widths_frac length must match number of columns")
        total = sum(col_widths_frac)
        col_widths = [width * (f / total) for f in col_widths_frac]
    else:
        col_widths = [width / n_cols] * n_cols

    wrapped_rows = []
    for r_idx, row in enumerate(data):
        is_header_row = header and r_idx == 0
        style = _header_cell_style if is_header_row else _cell_style
        wrapped_rows.append([
            Paragraph(str(cell).upper() if is_header_row else str(cell), style)
            for cell in row
        ])

    table = Table(wrapped_rows, colWidths=col_widths, repeatRows=1 if header else 0)

    style_cmds = [
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_PAPER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    if header:
        style_cmds.append(("BACKGROUND", (0, 0), (-1, 0), MIST))
        style_cmds.append(("LINEBELOW", (0, 0), (-1, 0), 1.2, ELECTRIC_INDIGO))
        style_cmds.append(("ROWBACKGROUNDS", (0, 1), (-1, -1), [BG_PAPER, BG_PAPER_SOFT]))
    else:
        style_cmds.append(("ROWBACKGROUNDS", (0, 0), (-1, -1), [BG_PAPER, BG_PAPER_SOFT]))
    table.setStyle(TableStyle(style_cmds))
    return table


def _metadata_block(metadata):
    """Report details -- who ran this and what it covers. Always the first
    thing after the hero and doc title, before any findings."""
    if not metadata:
        return None
    rows = [
        [Paragraph(str(label).upper(), _meta_label_style), Paragraph(str(value), _meta_value_style)]
        for label, value in metadata
    ]
    width = _printable_width()
    table = Table(rows, colWidths=[width * 0.28, width * 0.72])
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def _badge_row(fit_tier=None, operational_status=None):
    """Small badge chips rendered right under the report title, before
    'Report details' -- so a reader never has to open this skill's own
    documentation to learn the fit tier or whether the check is fully
    working. Fit tier always uses the neutral Mist+Indigo treatment (same
    as table headers); operational status is semantic: the same neutral
    treatment for 'Operational', and a Signal Gold fill (the brand's own
    secondary accent, used sparingly for exactly this kind of attention
    case) for 'Partially operational' / 'Not yet operational' -- so an
    agent that isn't fully working yet visually stands out from one that
    is, without inventing a color the brand doesn't use.

    Implemented as ONE small table with one column per badge (not nested
    tables, which reportlab sizes unreliably when auto-width is involved)
    -- each column gets its own BACKGROUND/BOX via explicit cell-range
    TableStyle commands, the same technique safe_table() already uses for
    header styling."""
    labels = []
    warn_flags = []

    if fit_tier:
        labels.append(FIT_TIER_LABELS.get(fit_tier.strip().lower(), "FIT TIER: %s" % fit_tier.upper()))
        warn_flags.append(False)

    if operational_status:
        key = operational_status.strip().lower()
        labels.append(OPERATIONAL_STATUS_LABELS.get(key, "STATUS: %s" % operational_status.upper()))
        warn_flags.append(key in ("partially operational", "not yet operational"))

    if not labels:
        return None

    row_data = [[
        Paragraph(label, _badge_warn_style if warn else _badge_style)
        for label, warn in zip(labels, warn_flags)
    ]]
    # Narrow, content-hugging columns (not full page width) -- fixed
    # generous-enough widths per badge rather than auto-sizing, since
    # reportlab's auto-width pass for a bare Table (no colWidths) stretches
    # to fill available space by default, which would make each chip span
    # the full printable width instead of hugging its own text.
    col_width = 2.2 * inch
    table = Table(row_data, colWidths=[col_width] * len(labels), hAlign="LEFT")
    style_cmds = [
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    for i, warn in enumerate(warn_flags):
        bg = SIGNAL_GOLD if warn else MIST
        line = SIGNAL_GOLD if warn else ELECTRIC_INDIGO
        style_cmds.append(("BACKGROUND", (i, 0), (i, 0), bg))
        style_cmds.append(("BOX", (i, 0), (i, 0), 0.75, line))
    table.setStyle(TableStyle(style_cmds))
    return table


def _note_box(heading, text):
    """A visually distinct, left-rule note box used for the Scope,
    Limitations, and Recommended Next Steps sections every
    *-compliance-check report carries -- so these three are consistently
    styled and immediately recognizable as a matched set, distinct from
    plain findings paragraphs. `text` may be a single string or a list of
    bullet strings (rendered as a simple dash-prefixed list)."""
    if isinstance(text, (list, tuple)):
        body_text = "<br/>".join("&#8226;&nbsp;%s" % t for t in text)
    else:
        body_text = text
    inner = [
        Paragraph(heading.upper(), _note_heading_style),
        Paragraph(body_text, _note_body_style),
    ]
    width = _printable_width()
    # Single-cell table so a colored left border can be drawn via LINEBEFORE
    # -- reportlab has no native "left-border box" flowable, this is the
    # standard workaround.
    t = Table([[inner]], colWidths=[width])
    t.setStyle(TableStyle([
        ("LINEBEFORE", (0, 0), (0, 0), 2.5, ELECTRIC_INDIGO),
        ("BACKGROUND", (0, 0), (-1, -1), BG_PAPER_SOFT),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def _draw_hero(canvas_obj, agent_name):
    """Full-bleed dark hero band -- pure brand identity ONLY: the real
    logo and an agent-name label. No report title, no scope-specific text,
    ever, here -- that's what caused the overlap/duplication bug (the
    eyebrow and a near-identical title were both fighting for the same
    small vertical space). The descriptive title lives in the body now."""
    canvas_obj.saveState()

    hero_y = PAGE_H - HERO_HEIGHT
    if os.path.exists(HERO_BG_PATH):
        canvas_obj.drawImage(HERO_BG_PATH, 0, hero_y, width=PAGE_W, height=HERO_HEIGHT, preserveAspectRatio=False, mask="auto")
    else:
        canvas_obj.setFillColor(DEEP_SPACE)
        canvas_obj.rect(0, hero_y, PAGE_W, HERO_HEIGHT, fill=1, stroke=0)

    logo_h = 0.24 * inch
    logo_bottom = hero_y + HERO_HEIGHT - 0.40 * inch  # comfortable gap from the top edge
    if os.path.exists(LOGO_WHITE_PATH):
        from PIL import Image as PILImage
        with PILImage.open(LOGO_WHITE_PATH) as im:
            aspect = im.width / im.height
        logo_w = logo_h * aspect
        canvas_obj.drawImage(LOGO_WHITE_PATH, MARGIN, logo_bottom, width=logo_w, height=logo_h, mask="auto")

    eyebrow = Paragraph(agent_name.upper(), _hero_eyebrow_style)
    eyebrow_y = logo_bottom - 0.30 * inch  # clear gap below the logo, no overlap
    eyebrow.wrap(_printable_width(), 0.3 * inch)
    eyebrow.drawOn(canvas_obj, MARGIN, eyebrow_y)

    canvas_obj.restoreState()


def _footer(canvas_obj, doc):
    canvas_obj.saveState()
    canvas_obj.setFont(FONT_MONO, 8)
    canvas_obj.setFillColor(FG_PAPER_2)
    canvas_obj.drawString(MARGIN, 0.68 * inch, "Kiteworks Agents")
    canvas_obj.drawRightString(PAGE_W - MARGIN, 0.68 * inch, "Page %d" % canvas_obj.getPageNumber())
    legal_footer = Paragraph(LEGAL_DISCLAIMER, _legal_footer_style)
    legal_footer.wrapOn(canvas_obj, _printable_width(), 0.42 * inch)
    legal_footer.drawOn(canvas_obj, MARGIN, 0.16 * inch)
    canvas_obj.restoreState()


def build_branded_pdf(output_path, agent_name, report_title, sections, metadata=None, scope_caveat=None,
                       fit_tier=None, operational_status=None, scope=None, limitations=None,
                       recommended_next_steps=None):
    """`report_title` is now rendered ONCE, as the first thing in the body
    (below the hero) -- never in the hero itself, which stays pure brand
    identity (logo + agent name only) to avoid the title/eyebrow overlap
    and redundancy an earlier version had.

    `metadata`: build the generic part with `standard_metadata()` and
    extend it with this agent's own specific rows (term list, retention
    threshold, time window, ...) before passing it in here.

    `scope_caveat`: the required plugin-specific statement of what this report
    did and did not evaluate. The legal disclaimer is publish-injected and is
    always rendered in the page footer; callers cannot replace or omit it.

    sections: list of dicts, each either
       {"heading": str, "paragraph": str}
    or {"heading": str, "table": {"data": [[...], ...], "col_widths_frac": [...]?}}.

    `fit_tier` / `operational_status` (both optional, primarily for
    *-compliance-check reports): rendered as small badge chips right under
    the title, before "Report details" -- see `_badge_row()`. fit_tier is
    one of strong/good/light/accessibility/minimal (case-insensitive);
    operational_status is one of operational/partially operational/not yet
    operational.

    `scope` (optional, str or list[str]): rendered as a distinctly-styled
    note box immediately after "Report details" and before any findings --
    exactly what was scanned, which file types were read vs. skipped and
    why, the retention cutoff actually used, and which signals ran.

    `limitations` (optional, str or list[str]): rendered as a matching note
    box after all findings -- the itemized, expanded version of what this
    scan structurally cannot see. Prefer a list of distinct bullet items
    over one collapsed paragraph.

    `recommended_next_steps` (optional, str or list[str]): rendered as a
    third matching note box immediately after Limitations -- concrete,
    framework-specific actions the organization should take beyond this
    scan, not generic advice."""
    if not LEGAL_DISCLAIMER:
        raise RuntimeError(
            "legal disclaimer was not injected; publish this plugin before generating a PDF"
        )
    if not scope_caveat:
        raise ValueError("scope_caveat is required for every branded report")

    def _on_page(canvas_obj, doc_obj):
        _draw_hero(canvas_obj, agent_name)
        _footer(canvas_obj, doc_obj)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=PAGE_SIZE,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=HERO_HEIGHT + 0.35 * inch,
        bottomMargin=1.05 * inch,
        title=report_title,
    )

    story = [Paragraph(report_title, _doc_title_style)]

    badge_row = _badge_row(fit_tier=fit_tier, operational_status=operational_status)
    if badge_row:
        story.append(badge_row)
        story.append(Spacer(1, 4))

    meta_table = _metadata_block(metadata)
    if meta_table:
        story.append(Paragraph("Report details", _section_title_style))
        story.append(meta_table)
        story.append(Spacer(1, 6))
        story.append(HRFlowable(width="100%", thickness=0.75, color=BORDER_PAPER, spaceBefore=6, spaceAfter=6))

    if scope:
        story.append(_note_box("Scope", scope))
        story.append(Spacer(1, 10))

    for section in sections:
        heading = section.get("heading")
        if heading:
            story.append(Paragraph(heading, _section_title_style))
        if "paragraph" in section:
            story.append(Paragraph(section["paragraph"], _body_style))
        if "table" in section:
            t = section["table"]
            table_flowable = safe_table(
                t["data"],
                col_widths_frac=t.get("col_widths_frac"),
                header=t.get("header", True),
            )
            if table_flowable:
                story.append(table_flowable)
                story.append(Spacer(1, 10))

    if limitations:
        story.append(_note_box("Limitations", limitations))
        story.append(Spacer(1, 10))

    if recommended_next_steps:
        story.append(_note_box("Recommended Next Steps", recommended_next_steps))
        story.append(Spacer(1, 10))

    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_PAPER, spaceBefore=10, spaceAfter=6))
    story.append(Paragraph(scope_caveat, _disclaimer_style))

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return output_path


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("usage: branded_pdf.py <path-to-json-spec>", file=sys.stderr)
        sys.exit(1)
    import json
    with open(sys.argv[1]) as f:
        spec = json.load(f)
    out = build_branded_pdf(
        output_path=spec["output_path"],
        agent_name=spec["agent_name"],
        report_title=spec["report_title"],
        sections=spec["sections"],
        metadata=spec.get("metadata"),
        scope_caveat=spec.get("scope_caveat"),
        fit_tier=spec.get("fit_tier"),
        operational_status=spec.get("operational_status"),
        scope=spec.get("scope"),
        limitations=spec.get("limitations"),
        recommended_next_steps=spec.get("recommended_next_steps"),
    )
    print(out)
