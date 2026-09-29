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

import argparse
import base64
import datetime as _dt
import json
import os
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape as _xml_escape
from xml.sax.saxutils import unescape as _xml_unescape

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ASSETS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets"
)
LOGO_WHITE_PATH = os.path.join(ASSETS_DIR, "kw-logo-white.png")
HERO_BG_PATH = os.path.join(ASSETS_DIR, "hero-bg.png")

# -- Brand tokens, taken directly from kw-brand-visual's own tokens/rules.
DEEP_SPACE = colors.HexColor("#050821")  # --kw-deep-space -- hero band fallback fill
ELECTRIC_INDIGO = colors.HexColor(
    "#4D60FB"
)  # --kw-electric-indigo -- accent, used as TEXT/label/link color, not a big solid fill
FG_LINK = colors.HexColor(
    "#4D60FB"
)  # --fg-link (same value as Electric Indigo, its own documented token)
MIST = colors.HexColor(
    "#EFF2FF"
)  # --kw-mist -- light neutral tint, table header background
SIGNAL_GOLD = colors.HexColor(
    "#FDCA13"
)  # --kw-signal-gold -- secondary accent, used sparingly
MUTED_LAVENDER = colors.HexColor(
    "#B5BCF2"
)  # --kw-blue-200 / muted-lavender -- metadata on dark
BG_PAPER = colors.white  # --bg-paper -- print/document background
BG_PAPER_SOFT = colors.HexColor("#E8EAF4")  # --bg-paper-soft -- zebra striping on paper
FG_PAPER_1 = colors.HexColor("#050821")  # --fg-paper-1 -- primary text on paper
FG_PAPER_2 = colors.HexColor(
    "#505264"
)  # --fg-paper-2 (rgba(5,8,33,0.70) flattened onto white)
BORDER_PAPER = colors.HexColor("#D1D5DC")  # --border-paper -- rules/grid lines on paper

PAGE_SIZE = letter
PAGE_W, PAGE_H = PAGE_SIZE
MARGIN = 0.75 * inch
HERO_HEIGHT = 0.95 * inch  # logo + eyebrow only now -- no title crammed in here

LEGAL_DISCLAIMER = 'This report was generated by an AI agent and is not a compliance certification, audit opinion, or legal determination of compliance with any law, standard or framework, nor legal advice. It reflects only the files and inputs actually scanned on {scan_date} and may be incomplete or inaccurate. Provided "as is", without warranty to the extent permitted by applicable law — verify independently before relying on it or sharing it with an auditor or regulator. Full terms: https://agents.kiteworks.com/legal/marketplace-terms'

# The published legal footer carries a {scan_date} token that is filled in when a
# report is BUILT, not when the plugin was published: the sentence ties its claim
# to the files actually scanned on that date, so a publish-time date would be
# confidently wrong on every report generated afterwards.
SCAN_DATE_TOKEN = "{scan_date}"

# The local folder a report run stages its files in (#307): the agent writes
# spec.json and the CSV there with the Write tool (hooks/kw-write-guard.sh
# allows nothing else), `build` removes a spec it read from there, and
# `cleanup` empties it once the PDF and CSV are uploaded.
STAGING_DIR_NAME = "_kiteworks-report"
STAGING_SUFFIXES = (".json", ".csv", ".txt", ".md", ".pdf", ".b64")

# The JSON spec keys: build_branded_pdf keyword arguments minus output_path.
SPEC_KEYS = (
    "agent_name",
    "report_title",
    "sections",
    "metadata",
    "scope_caveat",
    "fit_tier",
    "operational_status",
    "scope",
    "limitations",
    "recommended_next_steps",
    "scan_date",
)
TABLE_SHAPE = (
    '{"data": [["Header A", "Header B"], ["row 1 text", {"text": "link text", '
    '"url": "https://..."}]], "col_widths_frac": [0.4, 0.6]}'
)
_LINK_SCHEMES = ("http://", "https://", "mailto:")
# A cell that is exactly one link, as _linkify builds it. Anything else that
# merely looks like markup is rendered as the literal text it is.
_ANCHOR_CELL_RE = re.compile(
    r'\A\s*<a\s+href="(?P<url>[^"<>]*)"[^<>]*>(?:<u>)?(?P<text>[^<>]*?)(?:</u>)?</a>\s*\Z',
    re.IGNORECASE,
)


def _escape_report_text(text):
    """Escape `<`, `>` and `&` so report text supplied by a caller -- which
    may legitimately contain HTML-looking snippets such as `<html lang>` or
    `<title>` -- renders as literal text in a reportlab Paragraph instead of
    being parsed as (and breaking on) unrecognized markup. Internally
    generated markup (the `<a href=...>` links `_linkify` builds, the
    `<br/>` separators note boxes use) is built AFTER this escaping, never
    passed back through it, so real markup is never double-escaped."""
    return _xml_escape(str(text))


def _resolve_legal_footer(scan_date=None):
    """The legal footer with its scan date filled in.

    `scan_date` is the day the scan ran, as an ISO `YYYY-MM-DD` string. It
    defaults to today because a report is generated at the end of the scan it
    describes; pass it explicitly when a report is rebuilt from earlier results,
    so the line keeps describing the scan rather than the rebuild.
    """
    if not LEGAL_DISCLAIMER:
        raise RuntimeError(
            "legal disclaimer was not injected; publish this plugin before generating a PDF"
        )
    resolved = scan_date or _dt.date.today().isoformat()
    return LEGAL_DISCLAIMER.replace(SCAN_DATE_TOKEN, str(resolved))


FONT_BODY = "Helvetica"
FONT_BODY_BOLD = "Helvetica-Bold"
FONT_MONO = "Courier"
FONT_MONO_BOLD = "Courier-Bold"

_hero_eyebrow_style = ParagraphStyle(
    "kw_hero_eyebrow",
    fontName=FONT_MONO,
    fontSize=9,
    leading=12,
    textColor=MUTED_LAVENDER,
)
_doc_title_style = ParagraphStyle(
    "kw_doc_title",
    fontName=FONT_BODY_BOLD,
    fontSize=18,
    leading=22,
    textColor=FG_PAPER_1,
    spaceAfter=10,
)
_section_title_style = ParagraphStyle(
    "kw_section_title",
    fontName=FONT_BODY_BOLD,
    fontSize=16,
    leading=19,
    textColor=FG_PAPER_1,
    spaceBefore=14,
    spaceAfter=6,
)
_body_style = ParagraphStyle(
    "kw_body",
    fontName=FONT_BODY,
    fontSize=10,
    leading=14,
    textColor=FG_PAPER_1,
    spaceAfter=8,
)
_cell_style = ParagraphStyle(
    "kw_cell",
    fontName=FONT_BODY,
    fontSize=8.5,
    leading=11,
    textColor=FG_PAPER_1,
)
_header_cell_style = ParagraphStyle(
    "kw_header_cell",
    fontName=FONT_MONO_BOLD,
    fontSize=9,
    leading=11,
    textColor=ELECTRIC_INDIGO,
)
_meta_label_style = ParagraphStyle(
    "kw_meta_label",
    fontName=FONT_MONO,
    fontSize=8.5,
    leading=13,
    textColor=FG_PAPER_2,
)
_meta_value_style = ParagraphStyle(
    "kw_meta_value",
    fontName=FONT_BODY,
    fontSize=9.5,
    leading=13,
    textColor=FG_PAPER_1,
)
_disclaimer_style = ParagraphStyle(
    "kw_disclaimer",
    fontName=FONT_BODY,
    fontSize=8,
    leading=11,
    textColor=FG_PAPER_2,
    spaceBefore=10,
)
_legal_footer_style = ParagraphStyle(
    "kw_legal_footer",
    fontName=FONT_BODY,
    fontSize=6.25,
    leading=7.5,
    textColor=FG_PAPER_2,
)
_badge_style = ParagraphStyle(
    "kw_badge",
    fontName=FONT_MONO_BOLD,
    fontSize=8,
    leading=10,
    textColor=ELECTRIC_INDIGO,
)
_badge_warn_style = ParagraphStyle(
    "kw_badge_warn",
    fontName=FONT_MONO_BOLD,
    fontSize=8,
    leading=10,
    textColor=DEEP_SPACE,
)
_note_heading_style = ParagraphStyle(
    "kw_note_heading",
    fontName=FONT_MONO_BOLD,
    fontSize=9.5,
    leading=13,
    textColor=FG_PAPER_1,
    spaceAfter=3,
)
_note_body_style = ParagraphStyle(
    "kw_note_body",
    fontName=FONT_BODY,
    fontSize=9,
    leading=13,
    textColor=FG_PAPER_1,
)

# Fit tier -> badge label (operational-status colors are semantic, fit-tier is always neutral brand accent)
FIT_TIER_LABELS = {
    "strong": "FIT TIER: STRONG",
    "good": "FIT TIER: GOOD",
    "light": "FIT TIER: LIGHT",
    "accessibility": "FIT TIER: ACCESSIBILITY",
    "minimal": "FIT TIER: MINIMAL",
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
    Falls back to plain text if no url is given. The result is a valid
    metadata value or table cell: both recognise a whole-cell link."""
    if not url:
        return text
    return _link_markup(text, url)


def _link_markup(text, url):
    """Paragraph markup for `text` (escaped) linked to `url`, or just the
    escaped text when there is no url."""
    label = _escape_report_text(text)
    if not url:
        return label
    return '<a href="%s" color="#4D60FB"><u>%s</u></a>' % (
        _xml_escape(str(url), {'"': "&quot;"}),
        label,
    )


def _is_link_url(url):
    return str(url).strip().lower().startswith(_LINK_SCHEMES)


def _type_name(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true/false"
    if isinstance(value, dict):
        return "an object"
    if isinstance(value, (list, tuple)):
        return "a list"
    if isinstance(value, str):
        return "a string"
    if isinstance(value, (int, float)):
        return "a number"
    return type(value).__name__


def _check_cell(cell, where):
    """A table cell or metadata value is text, a number, empty (null) or a
    link object {"text": ..., "url": "https://..."}."""
    if isinstance(cell, dict):
        unknown = sorted(set(cell) - {"text", "url"})
        if unknown:
            raise ValueError(
                '%s: a link cell may only have "text" and "url"; got %s'
                % (where, ", ".join(unknown))
            )
        if "text" not in cell:
            raise ValueError(
                '%s: a link cell must be {"text": "...", "url": "https://..."}; '
                '"text" is missing' % where
            )
        _check_cell(cell["text"], where + ".text")
        url = cell.get("url")
        if url and (not isinstance(url, str) or not _is_link_url(url)):
            raise ValueError(
                '%s: link "url" must start with http://, https:// or mailto:' % where
            )
        return
    if cell is not None and (
        isinstance(cell, bool) or not isinstance(cell, (str, int, float))
    ):
        raise ValueError(
            '%s must be text, a number or a link object {"text": "...", "url": '
            '"https://..."}; got %s' % (where, _type_name(cell))
        )


def _cell_text(cell):
    """The plain text of a cell (a link object's text)."""
    if isinstance(cell, dict):
        cell = cell.get("text")
    return "" if cell is None else str(cell)


def _cell_markup(cell, where="cell"):
    """Paragraph markup for one table cell or metadata value.

    Allowed formats: plain text or a number (escaped, so `<html lang>` shows
    as written), a link object `{"text": ..., "url": ...}`, or a string that
    is exactly one `<a href="https://...">text</a>` as `_linkify` builds it.
    Both link forms render as a real link; any other markup stays literal."""
    _check_cell(cell, where)
    if isinstance(cell, dict):
        return _link_markup(_cell_text(cell), cell.get("url"))
    text = _cell_text(cell)
    match = _ANCHOR_CELL_RE.match(text)
    if match:
        url = _xml_unescape(match.group("url"), {"&quot;": '"'})
        if _is_link_url(url):
            return _link_markup(_xml_unescape(match.group("text")), url)
    return _escape_report_text(text)


def _validate_table(table, where):
    if not isinstance(table, dict):
        raise ValueError(
            "%s must be an object like %s; got %s"
            % (where, TABLE_SHAPE, _type_name(table))
        )
    unknown = sorted(set(table) - {"data", "col_widths_frac", "header"})
    if unknown:
        raise ValueError(
            "%s has unknown key(s) %s; allowed: data, col_widths_frac, header"
            % (where, ", ".join(unknown))
        )
    data = table.get("data")
    if not isinstance(data, (list, tuple)) or not data:
        raise ValueError(
            "%s.data must be a non-empty list of rows, header row first, like %s"
            % (where, TABLE_SHAPE)
        )
    width = None
    for r, row in enumerate(data):
        if not isinstance(row, (list, tuple)):
            raise ValueError(
                "%s.data[%d] must be a list of cells; got %s"
                % (where, r, _type_name(row))
            )
        if width is None:
            width = len(row)
            if not width:
                raise ValueError("%s.data[0] (the header row) is empty" % where)
        elif len(row) != width:
            raise ValueError(
                "%s.data[%d] has %d cell(s); the header row has %d cells"
                % (where, r, len(row), width)
            )
        for c, cell in enumerate(row):
            _check_cell(cell, "%s.data[%d][%d]" % (where, r, c))
    fracs = table.get("col_widths_frac")
    if fracs is not None and (
        not isinstance(fracs, (list, tuple))
        or len(fracs) != width
        or not all(
            isinstance(f, (int, float)) and not isinstance(f, bool) and f > 0
            for f in fracs
        )
    ):
        raise ValueError(
            "%s.col_widths_frac must be a list of %d positive numbers, one per column"
            % (where, width)
        )
    if not isinstance(table.get("header", True), bool):
        raise ValueError("%s.header must be true or false" % where)


def _validate_text_or_list(value, where):
    if value is None or isinstance(value, str):
        return
    if isinstance(value, (list, tuple)) and all(isinstance(v, str) for v in value):
        return
    raise ValueError(
        "%s must be a string or a list of strings; got %s" % (where, _type_name(value))
    )


def _validate_sections(sections):
    if not isinstance(sections, (list, tuple)):
        raise ValueError(
            'sections must be a list of objects like {"heading": "...", '
            '"paragraph": "..."} or {"heading": "...", "table": %s}; got %s'
            % (TABLE_SHAPE, _type_name(sections))
        )
    for i, section in enumerate(sections):
        where = "sections[%d]" % i
        if not isinstance(section, dict):
            raise ValueError(
                '%s must be an object with "heading" and a "paragraph" and/or '
                '"table"; got %s' % (where, _type_name(section))
            )
        unknown = sorted(set(section) - {"heading", "paragraph", "table"})
        if unknown:
            raise ValueError(
                "%s has unknown key(s) %s; allowed: heading, paragraph, table"
                % (where, ", ".join(unknown))
            )
        if "paragraph" not in section and "table" not in section:
            raise ValueError('%s needs a "paragraph" or a "table"' % where)
        for key in ("heading", "paragraph"):
            if key in section and not isinstance(section[key], str):
                raise ValueError(
                    "%s.%s must be a string; got %s"
                    % (where, key, _type_name(section[key]))
                )
        if "table" in section:
            _validate_table(section["table"], where + ".table")


def _validate_metadata(metadata):
    if metadata is None:
        return
    if not isinstance(metadata, (list, tuple)):
        raise ValueError(
            "metadata must be a list of [label, value] rows; got %s"
            % _type_name(metadata)
        )
    for i, row in enumerate(metadata):
        if not isinstance(row, (list, tuple)) or len(row) != 2:
            raise ValueError(
                "metadata[%d] must be a [label, value] row; got %r" % (i, row)
            )
        if not isinstance(row[0], str):
            raise ValueError("metadata[%d] label must be a string" % i)
        _check_cell(row[1], "metadata[%d][1]" % i)


def standard_metadata(
    scope_label,
    scope_name,
    scanned_by,
    generated_on,
    scope_link=None,
    output_folder_name=None,
    output_folder_link=None,
    extra_scope_label_suffix=None,
):
    """The GENERIC part of every report's "Report details" block -- the
    same shape for every agent in this plugin, so no agent has to
    reimplement it. `scope_label` lets each agent phrase the scope row in
    a way that fits it ("Folder scanned" for a scanner, "Folder reviewed"
    for naming-cleanup, "Person" for offboarding-content-finder, etc.)
    while everything else about the row (link handling, position, style)
    stays identical.

    Returns a list of [label, value] pairs (JSON-round-trippable: a plain
    list of two-item lists, not tuples) ready to pass straight into
    `build_branded_pdf`'s `metadata` argument, or to extend with the
    agent-specific rows only that agent needs (e.g. term list, retention
    threshold, time window) -- append those after calling this."""
    rows = [
        [scope_label, _linkify(scope_name, scope_link) if scope_link else scope_name]
    ]
    if output_folder_name:
        rows.append(
            [
                "Report saved in",
                _linkify(output_folder_name, output_folder_link)
                if output_folder_link
                else output_folder_name,
            ]
        )
    rows.append(["Scanned by", scanned_by])
    rows.append(["Generated", generated_on])
    return rows


def safe_table(data, col_widths_frac=None, header=True):
    """Build a reportlab Table that word-wraps every cell instead of
    overflowing/overlapping. `data` is a list of rows (lists of cells);
    the first row is treated as the header if header=True. A cell is plain
    text or a number (shown literally, `<html lang>` included), null (empty),
    or a link: a `{"text": ..., "url": "https://..."}` object, or a string
    that is exactly one `_linkify` link. Header cells show their text only. Header cell
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
        wrapped_rows.append(
            [
                Paragraph(
                    _escape_report_text(_cell_text(cell).upper())
                    if is_header_row
                    else _cell_markup(cell, "data[%d][%d]" % (r_idx, c_idx)),
                    style,
                )
                for c_idx, cell in enumerate(row)
            ]
        )

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
        style_cmds.append(
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [BG_PAPER, BG_PAPER_SOFT])
        )
    else:
        style_cmds.append(
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [BG_PAPER, BG_PAPER_SOFT])
        )
    table.setStyle(TableStyle(style_cmds))
    return table


def _metadata_block(metadata):
    """Report details -- who ran this and what it covers. Always the first
    thing after the hero and doc title, before any findings."""
    if not metadata:
        return None
    rows = [
        [
            Paragraph(_escape_report_text(str(label).upper()), _meta_label_style),
            Paragraph(_cell_markup(value, "metadata value"), _meta_value_style),
        ]
        for label, value in metadata
    ]
    width = _printable_width()
    table = Table(rows, colWidths=[width * 0.28, width * 0.72])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
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
        labels.append(
            FIT_TIER_LABELS.get(
                fit_tier.strip().lower(),
                "FIT TIER: %s" % _escape_report_text(fit_tier.upper()),
            )
        )
        warn_flags.append(False)

    if operational_status:
        key = operational_status.strip().lower()
        labels.append(
            OPERATIONAL_STATUS_LABELS.get(
                key, "STATUS: %s" % _escape_report_text(operational_status.upper())
            )
        )
        warn_flags.append(key in ("partially operational", "not yet operational"))

    if not labels:
        return None

    row_data = [
        [
            Paragraph(label, _badge_warn_style if warn else _badge_style)
            for label, warn in zip(labels, warn_flags)
        ]
    ]
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
        body_text = "<br/>".join(
            "&#8226;&nbsp;%s" % _escape_report_text(t) for t in text
        )
    else:
        body_text = _escape_report_text(text)
    inner = [
        Paragraph(_escape_report_text(heading.upper()), _note_heading_style),
        Paragraph(body_text, _note_body_style),
    ]
    width = _printable_width()
    # Single-cell table so a colored left border can be drawn via LINEBEFORE
    # -- reportlab has no native "left-border box" flowable, this is the
    # standard workaround.
    t = Table([[inner]], colWidths=[width])
    t.setStyle(
        TableStyle(
            [
                ("LINEBEFORE", (0, 0), (0, 0), 2.5, ELECTRIC_INDIGO),
                ("BACKGROUND", (0, 0), (-1, -1), BG_PAPER_SOFT),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
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
        canvas_obj.drawImage(
            HERO_BG_PATH,
            0,
            hero_y,
            width=PAGE_W,
            height=HERO_HEIGHT,
            preserveAspectRatio=False,
            mask="auto",
        )
    else:
        canvas_obj.setFillColor(DEEP_SPACE)
        canvas_obj.rect(0, hero_y, PAGE_W, HERO_HEIGHT, fill=1, stroke=0)

    logo_h = 0.24 * inch
    logo_bottom = (
        hero_y + HERO_HEIGHT - 0.40 * inch
    )  # comfortable gap from the top edge
    if os.path.exists(LOGO_WHITE_PATH):
        from PIL import Image as PILImage

        with PILImage.open(LOGO_WHITE_PATH) as im:
            aspect = im.width / im.height
        logo_w = logo_h * aspect
        canvas_obj.drawImage(
            LOGO_WHITE_PATH,
            MARGIN,
            logo_bottom,
            width=logo_w,
            height=logo_h,
            mask="auto",
        )

    eyebrow = Paragraph(agent_name.upper(), _hero_eyebrow_style)
    eyebrow_y = logo_bottom - 0.30 * inch  # clear gap below the logo, no overlap
    eyebrow.wrap(_printable_width(), 0.3 * inch)
    eyebrow.drawOn(canvas_obj, MARGIN, eyebrow_y)

    canvas_obj.restoreState()


def _footer(canvas_obj, doc, scan_date=None):
    canvas_obj.saveState()
    canvas_obj.setFont(FONT_MONO, 8)
    canvas_obj.setFillColor(FG_PAPER_2)
    canvas_obj.drawString(MARGIN, 0.68 * inch, "Kiteworks Agents")
    canvas_obj.drawRightString(
        PAGE_W - MARGIN, 0.68 * inch, "Page %d" % canvas_obj.getPageNumber()
    )
    legal_footer = Paragraph(_resolve_legal_footer(scan_date), _legal_footer_style)
    legal_footer.wrapOn(canvas_obj, _printable_width(), 0.42 * inch)
    legal_footer.drawOn(canvas_obj, MARGIN, 0.16 * inch)
    canvas_obj.restoreState()


def build_branded_pdf(
    output_path,
    agent_name,
    report_title,
    sections,
    metadata=None,
    scope_caveat=None,
    fit_tier=None,
    operational_status=None,
    scope=None,
    limitations=None,
    recommended_next_steps=None,
    scan_date=None,
):
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
    Table cells and metadata values follow `safe_table()`'s cell formats, so
    `{"text": ..., "url": ...}` renders as a link. A malformed section, table
    or metadata row raises ValueError naming the expected shape.

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
    scan, not generic advice.

    `scan_date` (optional, ISO `YYYY-MM-DD` str): the day the scan ran, printed
    in the legal footer. Defaults to today, which is correct when the report is
    generated at the end of its own scan. Pass it when rebuilding a report from
    earlier results, so the footer keeps describing the scan and not the
    rebuild."""
    if not LEGAL_DISCLAIMER:
        raise RuntimeError(
            "legal disclaimer was not injected; publish this plugin before generating a PDF"
        )
    if not scope_caveat:
        raise ValueError("scope_caveat is required for every branded report")
    _validate_sections(sections)
    _validate_metadata(metadata)
    for name, value in (
        ("scope", scope),
        ("limitations", limitations),
        ("recommended_next_steps", recommended_next_steps),
    ):
        _validate_text_or_list(value, name)

    def _on_page(canvas_obj, doc_obj):
        _draw_hero(canvas_obj, agent_name)
        _footer(canvas_obj, doc_obj, scan_date)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=PAGE_SIZE,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=HERO_HEIGHT + 0.35 * inch,
        bottomMargin=1.05 * inch,
        title=report_title,
    )

    story = [Paragraph(_escape_report_text(report_title), _doc_title_style)]

    badge_row = _badge_row(fit_tier=fit_tier, operational_status=operational_status)
    if badge_row:
        story.append(badge_row)
        story.append(Spacer(1, 4))

    meta_table = _metadata_block(metadata)
    if meta_table:
        story.append(Paragraph("Report details", _section_title_style))
        story.append(meta_table)
        story.append(Spacer(1, 6))
        story.append(
            HRFlowable(
                width="100%",
                thickness=0.75,
                color=BORDER_PAPER,
                spaceBefore=6,
                spaceAfter=6,
            )
        )

    if scope:
        story.append(_note_box("Scope", scope))
        story.append(Spacer(1, 10))

    for section in sections:
        heading = section.get("heading")
        if heading:
            story.append(Paragraph(_escape_report_text(heading), _section_title_style))
        if "paragraph" in section:
            story.append(
                Paragraph(_escape_report_text(section["paragraph"]), _body_style)
            )
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

    story.append(
        HRFlowable(
            width="100%",
            thickness=0.5,
            color=BORDER_PAPER,
            spaceBefore=10,
            spaceAfter=6,
        )
    )
    story.append(Paragraph(_escape_report_text(scope_caveat), _disclaimer_style))

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return output_path


_BASE64_INVALID_RE = re.compile(r"[^A-Za-z0-9+/=]")


def _validate_base64_chunk(chunk):
    """Raise ValueError with a clear message if chunk contains any
    character outside the base64 alphabet (A-Z, a-z, 0-9, +, /, =).

    Every chunk shipped to spec-append is meant to be plain, shell-safe
    base64 -- no quotes, no angle brackets, no non-ASCII bytes -- precisely
    so a caller never has to quote report text for a shell. A stray
    non-base64 character means something (a literal, a stray newline, a
    mis-encoded chunk) slipped through un-encoded.
    """
    bad = sorted(set(_BASE64_INVALID_RE.findall(chunk)))
    if bad:
        raise ValueError(
            "chunk contains non-base64 characters (only A-Z, a-z, 0-9, +, /, "
            "= are allowed): %r" % "".join(bad)
        )


def _spec_append(spec_path, chunk):
    """Append one base64 chunk to spec_path, creating the file (and any
    missing parent directories) if it does not exist yet. Each chunk is
    validated and written on its own line; _decode_spec_file strips
    whitespace before decoding, so the line breaks are purely for human
    readability and are never treated as content."""
    _validate_base64_chunk(chunk)
    path = Path(spec_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="ascii", newline="\n") as f:
        f.write(chunk + "\n")


def _decode_spec_file(spec_path):
    """Join every chunk written by _spec_append, base64-decode the
    result, and parse it as UTF-8 JSON."""
    raw_text = Path(spec_path).read_text(encoding="ascii")
    joined = "".join(line.strip() for line in raw_text.splitlines())
    _validate_base64_chunk(joined)
    raw_bytes = base64.b64decode(joined, validate=True)
    return json.loads(raw_bytes.decode("utf-8"))


def _count_pdf_pages(pdf_path):
    """Best-effort page count for the printed build summary line. Prefers
    pypdf (already a companion dependency of reportlab in this project
    test and build environments) when it is importable, and otherwise
    falls back to counting /Type /Page object entries directly --
    reportlab always writes that exact entry (without a trailing s) once
    per page -- so this never hard-fails just because pypdf happens to be
    missing wherever this script runs."""
    try:
        from pypdf import PdfReader
    except ImportError:
        data = Path(pdf_path).read_bytes()
        return len(re.findall(rb"/Type\s*/Page(?!s)", data))
    return len(PdfReader(str(pdf_path)).pages)


def _spec_to_build_kwargs(spec, output_path):
    """The JSON spec keys map onto build_branded_pdf keyword arguments
    directly, except output_path, which always comes from the --out flag
    on the command line (so the spec never needs to duplicate a local
    filesystem path the caller already provided). Unknown or missing keys
    raise ValueError naming the allowed ones, so a typo never silently drops
    a section of the report."""
    if not isinstance(spec, dict):
        raise ValueError(
            "the spec must be one JSON object whose keys are %s; got %s"
            % (", ".join(SPEC_KEYS), _type_name(spec))
        )
    unknown = sorted(set(spec) - set(SPEC_KEYS))
    if unknown:
        raise ValueError(
            "unknown spec key(s) %s; allowed keys: %s"
            % (", ".join(unknown), ", ".join(SPEC_KEYS))
        )
    missing = [
        key for key in ("agent_name", "report_title", "sections") if key not in spec
    ]
    if missing:
        raise ValueError("the spec is missing required key(s) %s" % ", ".join(missing))
    return dict(
        output_path=str(output_path),
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
        scan_date=spec.get("scan_date"),
    )


def _cleanup_staging(dir_path):
    """Remove the staged files of one report run once they are uploaded.

    Only a folder named STAGING_DIR_NAME is touched, and in it only regular
    files with a STAGING_SUFFIXES extension; anything else (a subfolder, a
    link, a hand-written script) is kept and listed. The folder itself is
    removed with a plain rmdir once it is empty. Never recursive."""
    staging = Path(dir_path)
    is_junction = getattr(staging, "is_junction", lambda: False)
    if staging.name != STAGING_DIR_NAME:
        raise ValueError(
            "cleanup only empties a %s folder; refusing %s"
            % (STAGING_DIR_NAME, staging)
        )
    if staging.is_symlink() or is_junction() or not staging.is_dir():
        raise ValueError("%s is not a plain folder" % staging)
    removed, kept = [], []
    for entry in sorted(staging.iterdir()):
        if (
            entry.is_file()
            and not entry.is_symlink()
            and entry.suffix.lower() in STAGING_SUFFIXES
        ):
            entry.unlink()
            removed.append(str(entry))
        else:
            kept.append(str(entry))
    dir_removed = False
    if not kept:
        staging.rmdir()
        dir_removed = True
    return {"removed": removed, "kept": kept, "dir_removed": dir_removed}


def _build_cli_parser():
    parser = argparse.ArgumentParser(
        prog="branded_pdf.py",
        description=(
            "Build a Kiteworks-branded PDF report without hand-writing a "
            "Python build script or putting report text on a shell command "
            "line in raw form."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    append_parser = subparsers.add_parser(
        "spec-append",
        help="Append one shell-safe base64 chunk to a spec file, creating it if missing.",
    )
    append_parser.add_argument(
        "--spec",
        required=True,
        help="Path to the .json.b64 spec file being assembled.",
    )
    append_parser.add_argument(
        "--b64",
        required=True,
        help=(
            "One base64 chunk: plain ASCII A-Za-z0-9+/= only. Keep each "
            "chunk to roughly 6000 characters or fewer so it stays well "
            "under typical shell command-length limits."
        ),
    )

    build_parser = subparsers.add_parser(
        "build",
        help="Decode an assembled spec (or load a plain JSON file) and build the PDF.",
    )
    source = build_parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--spec",
        help="Path to a .json.b64 spec file assembled via spec-append.",
    )
    source.add_argument(
        "--json-file",
        help=(
            "Path to a plain UTF-8 JSON spec file, for callers that can "
            "safely write a UTF-8 file directly without going through a "
            "shell command line."
        ),
    )
    build_parser.add_argument("--out", required=True, help="Output PDF path.")
    build_parser.add_argument(
        "--keep-spec",
        action="store_true",
        help=(
            "Keep the spec file after a successful build. By default a spec "
            "read from a %s folder is removed once the PDF is built." % STAGING_DIR_NAME
        ),
    )

    cleanup_parser = subparsers.add_parser(
        "cleanup",
        help=(
            "After upload, remove the staged report files from a %s folder "
            "and the folder itself once empty." % STAGING_DIR_NAME
        ),
    )
    cleanup_parser.add_argument(
        "--dir", required=True, help="The %s folder to empty." % STAGING_DIR_NAME
    )

    return parser


def _run_cli(argv):
    parser = _build_cli_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "spec-append":
            _spec_append(args.spec, args.b64)
            return 0

        if args.command == "build":
            spec_path = Path(args.json_file or args.spec)
            if args.json_file:
                spec = json.loads(spec_path.read_text(encoding="utf-8"))
            else:
                spec = _decode_spec_file(args.spec)
            out_path = build_branded_pdf(**_spec_to_build_kwargs(spec, args.out))
            # The staged spec has served its purpose; a spec kept anywhere
            # else (a template, a test fixture) is never touched.
            spec_removed = False
            if not args.keep_spec and spec_path.parent.name == STAGING_DIR_NAME:
                spec_path.unlink()
                spec_removed = True
            print(
                json.dumps(
                    {
                        "pdf": str(out_path),
                        "pages": _count_pdf_pages(out_path),
                        "bytes": os.path.getsize(out_path),
                        "spec_removed": spec_removed,
                    }
                )
            )
            return 0

        if args.command == "cleanup":
            print(json.dumps(_cleanup_staging(args.dir)))
            return 0
    except (ValueError, OSError, RuntimeError, KeyError, TypeError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2

    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    sys.exit(_run_cli(sys.argv[1:]))
