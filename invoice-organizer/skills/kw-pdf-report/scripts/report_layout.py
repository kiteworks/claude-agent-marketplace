"""Executive report page layout, independent of assessment validation."""

import unicodedata
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfdoc import PDFString
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.doctemplate import IndexingFlowable
from reportlab.platypus.tableofcontents import TableOfContents


def register_fonts(font_dir):
    """Require bundled fonts rather than silently substituting missing glyphs."""
    for name, filename in (
        ("KWReport", "NotoSans-Regular.ttf"),
        ("KWReportBold", "NotoSans-Bold.ttf"),
    ):
        path = Path(font_dir) / filename
        if not path.is_file():
            raise ValueError(
                f"Report font is missing: {filename}; reinstall the plugin"
            )
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(path)))
    pdfmetrics.registerFontFamily(
        "KWReport",
        normal="KWReport",
        bold="KWReportBold",
        italic="KWReport",
        boldItalic="KWReportBold",
    )


def validate_glyphs(value):
    """Fail explicitly for scripts this font/layout does not yet support."""
    if isinstance(value, dict):
        for key, item in value.items():
            # URLs are destinations, not displayed prose; Unicode URLs are valid.
            if key != "url":
                validate_glyphs(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            validate_glyphs(item)
    elif isinstance(value, str):
        fonts = [
            pdfmetrics.getFont(name).face.charToGlyph
            for name in ("KWReport", "KWReportBold")
        ]
        missing = sorted(
            {
                ord(c)
                for c in value
                if not c.isspace()
                and (
                    any(ord(c) not in font for font in fonts)
                    or unicodedata.bidirectional(c) in ("R", "AL")
                )
            }
        )
        if missing:
            codes = ", ".join(f"U+{c:04X}" for c in missing[:12])
            raise ValueError(
                f"Unsupported report characters ({codes}); use the authorized UTF-8 text/CSV output. Do not remove or transliterate evidence."
            )


def _rendered_strings(prepared, report_title, agent_name, scope_caveat, presentation):
    """Strings the new-mode PDF actually draws, for glyph validation."""
    out = [report_title, agent_name, scope_caveat, prepared.get("status")]
    if "classification" in presentation:
        out.append(presentation["classification"])
    out.extend((prepared.get("cover") or {}).values())
    for key in ("summary", "body", "appendix"):
        for section in prepared[key]:
            out.append(section.get("heading"))
            out.append(section.get("paragraph"))
            out.extend(section.get("bullets", []))
            for row in section.get("table", {}).get("data", []):
                for cell in row:
                    out.append(cell.get("text") if isinstance(cell, dict) else cell)
    return [s if isinstance(s, str) else str(s) for s in out if s is not None]


def _fit_lines(text, style, width, max_lines, escape_text):
    """Drop trailing words until the text fits max_lines; never shrink the font."""

    def lines(candidate):
        p = Paragraph(escape_text(candidate), style)
        p.wrap(width, 10**6)
        return len(p.blPara.lines)

    if lines(text) <= max_lines:
        return text
    words = text.split()
    while len(words) > 1:
        words.pop()
        candidate = " ".join(words) + "\u2026"
        if lines(candidate) <= max_lines:
            return candidate
    single = words[0] if words else ""
    while single and lines(single + "\u2026") > max_lines:
        single = single[:-1]
    return single + "\u2026"


def _fit_width(text, font, size, max_width):
    """Truncate at a word boundary so the text fits one line of max_width."""
    if pdfmetrics.stringWidth(text, font, size) <= max_width:
        return text
    words = text.split()
    while words:
        candidate = " ".join(words) + "\u2026"
        if pdfmetrics.stringWidth(candidate, font, size) <= max_width:
            return candidate
        words.pop()
    return "\u2026"


class _PageCount(IndexingFlowable):
    def __init__(self, doc):
        super().__init__()
        self.doc = doc
        self.previous = 0
        self.current = 0

    def beforeBuild(self):
        self.previous = self.current

    def afterBuild(self):
        self.current = self.doc.page

    def isSatisfied(self):
        return self.previous == self.current

    def wrap(self, width, height):
        return 0, 0

    def draw(self):
        pass


class _ReportDocument(BaseDocTemplate):
    def afterFlowable(self, flowable):
        bookmark = getattr(flowable, "report_bookmark", None)
        if bookmark:
            level, key, title = bookmark
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(title, key, level=level, closed=level > 0)
            # Object/finding subsections remain in the PDF outline, while the
            # printed contents stays focused on major sections.
            if level == 0:
                self.notify("TOCEntry", (0, escape(title), self.page, key))


def build_assessment_pdf(
    output_path,
    *,
    agent_name,
    report_title,
    assessment,
    prepared,
    presentation,
    scope_caveat,
    legal_footer,
    theme,
):
    register_fonts(Path(__file__).resolve().parent.parent / "assets/fonts")
    if not isinstance(presentation, dict):
        raise ValueError("presentation must be an object")
    if "classification" in presentation and not isinstance(
        presentation["classification"], str
    ):
        raise ValueError("presentation.classification must be text")
    new_mode = "report_mode" in assessment
    if new_mode:
        validate_glyphs(
            _rendered_strings(
                prepared, report_title, agent_name, scope_caveat, presentation
            )
        )
    else:
        validate_glyphs(
            [assessment, prepared, report_title, agent_name, scope_caveat, presentation]
        )
    layout = presentation.get("layout", "full")
    if layout not in ("full", "brief"):
        raise ValueError("presentation.layout must be full or brief")
    size = presentation.get("page_size", "A4")
    if size not in ("A4", "Letter"):
        raise ValueError("presentation.page_size must be A4 or Letter")
    language = presentation.get("language", "en-US")
    if not isinstance(language, str) or not language.strip():
        raise ValueError("presentation.language must be non-empty text")
    unknown = set(presentation) - {"layout", "page_size", "language", "classification"}
    if unknown:
        raise ValueError("unknown presentation fields: " + ", ".join(sorted(unknown)))
    page_width, page_height = A4 if size == "A4" else letter
    margin = 48
    width = page_width - 2 * margin
    escaped = theme.escape_text
    body = ParagraphStyle(
        "ReportBody",
        fontName="KWReport",
        fontSize=10.5,
        leading=15,
        textColor=theme.FG_PAPER_1,
        spaceAfter=8,
    )
    heading = ParagraphStyle(
        "ReportHeading",
        parent=body,
        fontName="KWReportBold",
        fontSize=17,
        leading=22,
        spaceBefore=16,
        spaceAfter=8,
        keepWithNext=True,
    )
    subheading = ParagraphStyle(
        "ReportSubheading", parent=heading, fontSize=12, leading=17, spaceBefore=9
    )
    title_style = ParagraphStyle("ReportTitle", parent=heading, fontSize=27, leading=34)
    cell_style = ParagraphStyle(
        "ReportCell", parent=body, fontSize=9, leading=13, spaceAfter=0
    )
    header_style = ParagraphStyle(
        "ReportHeaderCell", parent=cell_style, fontName="KWReportBold"
    )
    bullet_style = ParagraphStyle(
        "ReportBullet", parent=body, leftIndent=14, firstLineIndent=-10
    )
    footer_style = ParagraphStyle("ReportFooter", parent=body, fontSize=6.5, leading=8)
    scope_style = ParagraphStyle(
        "ReportScope", parent=heading, spaceBefore=0, keepWithNext=False
    )
    org_style = ParagraphStyle("ReportOrg", parent=body, fontSize=12, leading=16)
    meta_style = ParagraphStyle("ReportMeta", parent=body, fontSize=11, leading=15)
    brief_meta_style = ParagraphStyle(
        "ReportBriefMeta", parent=body, fontSize=10.5, leading=15, spaceAfter=4
    )
    cell_padding = 7
    if new_mode:
        # Executive density: same type family and body size, tighter rhythm,
        # so a short report is not stretched over half-empty pages.
        body.leading, body.spaceAfter = 14, 6
        bullet_style.leading, bullet_style.spaceAfter = 14, 4
        heading.fontSize, heading.leading = 15, 19
        heading.spaceBefore, heading.spaceAfter = 12, 6
        subheading.fontSize, subheading.leading = 11.5, 15
        subheading.spaceBefore, subheading.spaceAfter = 6, 4
        for style in (cell_style, header_style):
            style.fontSize, style.leading = 8.5, 11
        cell_padding = 4
    run = assessment["run"]
    cover_data = prepared.get("cover") or {}
    meta_title = (cover_data.get("title") or report_title) if new_mode else report_title
    if new_mode:
        header_text = _fit_width(
            "Kiteworks | " + meta_title, "KWReport", 8, width - 120
        )
    else:
        header_text = "Kiteworks | " + report_title[:85]

    def make_doc(target):
        document = _ReportDocument(
            target,
            pagesize=(page_width, page_height),
            title=meta_title,
            author=run["operator"],
            subject=prepared["status"],
            leftMargin=margin,
            rightMargin=margin,
            topMargin=65,
            bottomMargin=78,
            lang=language,
        )
        counter = _PageCount(document)
        document.addPageTemplates(make_templates(counter))
        if layout == "brief":
            document.pageTemplates.reverse()
        return document, counter

    def make_templates(page_count):
        def on_page(canvas, document):
            draw_page(canvas, document, page_count)

        return [
            PageTemplate(
                id="cover",
                frames=[
                    Frame(
                        margin,
                        78,
                        width,
                        page_height - 255,
                        leftPadding=0,
                        rightPadding=0,
                        topPadding=0,
                        bottomPadding=0,
                    )
                ],
                onPage=on_page,
            ),
            PageTemplate(
                id="body",
                frames=[
                    Frame(
                        margin,
                        78,
                        width,
                        page_height - 143,
                        leftPadding=0,
                        rightPadding=0,
                        topPadding=0,
                        bottomPadding=0,
                    )
                ],
                onPage=on_page,
            ),
        ]

    def draw_page(canvas, document, page_count):
        canvas.setTitle(meta_title)
        canvas.setAuthor(run["operator"])
        canvas.setViewerPreference("DisplayDocTitle", "true")
        canvas._doc.Catalog.Lang = PDFString(language)
        canvas.saveState()
        cover = document.page == 1 and layout == "full"
        if cover:
            canvas.setFillColor(theme.DEEP_SPACE)
            canvas.rect(0, page_height - 145, page_width, 145, fill=1, stroke=0)
            if Path(theme.HERO_BG_PATH).is_file():
                canvas.drawImage(
                    theme.HERO_BG_PATH,
                    0,
                    page_height - 145,
                    width=page_width,
                    height=145,
                    mask="auto",
                )
            if Path(theme.LOGO_WHITE_PATH).is_file():
                canvas.drawImage(
                    theme.LOGO_WHITE_PATH,
                    margin,
                    page_height - 70,
                    width=155,
                    height=30,
                    preserveAspectRatio=True,
                    anchor="sw",
                    mask="auto",
                )
            label = Paragraph(
                escaped(agent_name),
                ParagraphStyle(
                    "CoverLabel", parent=body, textColor=colors.white, fontSize=10
                ),
            )
            label.wrapOn(canvas, width, 50)
            label.drawOn(canvas, margin, page_height - 115)
        else:
            canvas.setFillColor(theme.DEEP_SPACE)
            canvas.rect(0, page_height - 42, page_width, 42, fill=1, stroke=0)
            canvas.setFillColor(colors.white)
            canvas.setFont("KWReport", 8)
            canvas.drawString(margin, page_height - 26, header_text)
        canvas.setFillColor(theme.FG_PAPER_2)
        canvas.setFont("KWReport", 8)
        canvas.drawString(margin, 60, run["id"] + " / " + run["version"])
        canvas.drawRightString(
            page_width - margin,
            60,
            f"Page {document.page} of {page_count.previous or '…'}",
        )
        notice = Paragraph(legal_footer, footer_style)
        _, height = notice.wrapOn(canvas, width, 45)
        if height > 44:
            raise ValueError("Legal footer exceeds its reserved area")
        notice.drawOn(canvas, margin, 48 - height)
        canvas.restoreState()

    if new_mode:
        title_text = _fit_lines(meta_title, title_style, width, 2, escaped)
        scope_text = _fit_lines(
            cover_data.get("scope_label") or run["scope"],
            scope_style,
            width,
            2,
            escaped,
        )

    classification = presentation.get(
        "classification", "Distribution: designated report recipients"
    )

    def make_story(include_contents, page_count):
        story = [page_count]
        if layout == "full" and new_mode:
            story.extend(
                [
                    Spacer(1, 24),
                    Paragraph(escaped(title_text), title_style),
                    Spacer(1, 10),
                    Paragraph(escaped(scope_text), scope_style),
                ]
            )
            if cover_data.get("organization_label"):
                story.append(
                    Paragraph(escaped(cover_data["organization_label"]), org_style)
                )
            story.append(Spacer(1, 10))
            for key in ("date_label", "count_line", "review_line"):
                story.append(Paragraph(escaped(cover_data[key]), meta_style))
            story.extend(
                [
                    Paragraph(escaped(classification), body),
                    Paragraph(escaped(scope_caveat), body),
                    NextPageTemplate("body"),
                    PageBreak(),
                ]
            )
        elif layout == "full":
            story.extend(
                [
                    Spacer(1, 24),
                    Paragraph(escaped(report_title), title_style),
                    Spacer(1, 14),
                    Paragraph(escaped(run["scope"]), heading),
                    Paragraph(escaped(prepared["status"]), body),
                    Paragraph(escaped("Assessed: " + prepared["assessed_label"]), body),
                    Paragraph(
                        escaped("Generated: " + prepared["generated_label"]), body
                    ),
                    Paragraph(escaped(run["review_status"]), body),
                    Paragraph(escaped(classification), body),
                    Paragraph(escaped(scope_caveat), body),
                    NextPageTemplate("body"),
                    PageBreak(),
                ]
            )
        elif new_mode:
            story.extend(
                [
                    Paragraph(escaped(title_text), title_style),
                    Paragraph(escaped(scope_text), scope_style),
                    Paragraph(
                        escaped(
                            cover_data["date_label"]
                            + " \u00b7 "
                            + cover_data["count_line"]
                        ),
                        brief_meta_style,
                    ),
                    Paragraph(escaped(cover_data["review_line"]), brief_meta_style),
                ]
            )
        else:
            story.append(Paragraph(escaped(report_title), title_style))
        sequence = 0

        def append_sections(sections):
            nonlocal sequence
            for section in sections:
                if section.get("page_break"):
                    story.append(PageBreak())
                if section.get("heading"):
                    sequence += 1
                    level = section.get("level", 1) - 1
                    p = Paragraph(
                        escaped(section["heading"]),
                        heading if level == 0 else subheading,
                    )
                    if section.get("outline") is not False:
                        p.report_bookmark = (
                            level,
                            section.get("id", f"section-{sequence}"),
                            section["heading"],
                        )
                    story.append(p)
                if "paragraph" in section:
                    story.append(Paragraph(escaped(section["paragraph"]), body))
                for bullet in section.get("bullets", []):
                    story.append(Paragraph("• " + escaped(bullet), bullet_style))
                if "table" in section:
                    table = section["table"]
                    rows = [
                        [
                            Paragraph(
                                theme.cell_markup(cell)
                                if isinstance(cell, dict)
                                else escaped(str(cell)),
                                header_style if row == 0 else cell_style,
                            )
                            for cell in values
                        ]
                        for row, values in enumerate(table["data"])
                    ]
                    fractions = table.get("col_widths_frac", [1] * len(rows[0]))
                    widths = [width * f / sum(fractions) for f in fractions]
                    t = Table(
                        rows,
                        colWidths=widths,
                        repeatRows=1,
                        splitInRow=1,
                        hAlign="LEFT",
                    )
                    t.setStyle(
                        TableStyle(
                            [
                                ("BACKGROUND", (0, 0), (-1, 0), theme.MIST),
                                (
                                    "LINEBELOW",
                                    (0, 0),
                                    (-1, 0),
                                    1,
                                    theme.ELECTRIC_INDIGO,
                                ),
                                (
                                    "ROWBACKGROUNDS",
                                    (0, 1),
                                    (-1, -1),
                                    [colors.white, theme.BG_PAPER_SOFT],
                                ),
                                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                ("LEFTPADDING", (0, 0), (-1, -1), cell_padding),
                                ("RIGHTPADDING", (0, 0), (-1, -1), cell_padding),
                                ("TOPPADDING", (0, 0), (-1, -1), cell_padding),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), cell_padding),
                            ]
                        )
                    )
                    story.extend([t, Spacer(1, 10)])

        append_sections(prepared["summary"])
        if layout == "full" and include_contents:
            story.extend([PageBreak(), Paragraph("Contents", heading)])
            toc = TableOfContents()
            toc.levelStyles = [
                ParagraphStyle(
                    "ContentsEntry",
                    parent=body,
                    leftIndent=0,
                    firstLineIndent=0,
                    leading=19,
                    spaceBefore=5,
                )
            ]
            story.extend([toc, PageBreak()])
        append_sections(prepared["body"])
        story.append(Spacer(1, 18) if new_mode else PageBreak())
        append_sections(prepared["appendix"])
        story.append(Paragraph(escaped(scope_caveat), body))
        return story

    include_contents = True
    if new_mode and layout == "full":
        trial, trial_count = make_doc(BytesIO())
        trial.multiBuild(make_story(False, trial_count))
        include_contents = trial.page - 1 > 5
    buffer = BytesIO()
    doc, page_count = make_doc(buffer)
    doc.multiBuild(make_story(include_contents, page_count))
    Path(output_path).write_bytes(buffer.getvalue())
    return output_path
