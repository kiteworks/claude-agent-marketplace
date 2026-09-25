#!/usr/bin/env python3
"""Real structural accessibility check for Signal D
(section-508-compliance-check, wcag-compliance-check).

Replaces the previous non-functional heuristic: content-extract is a text
extractor (pdftotext for PDF, its own stdlib zip/XML reader for DOCX,
PPTX and XLSX), and none of those text paths can see
PDF tag structure, document language metadata, slide/document alt-text, or
HTML heading structure at all. This script actually executes what Signal D
has always described -- using pikepdf (PDF) and the standard library for
everything else: zipfile + xml.etree for DOCX and PPTX (the same approach
content-extract uses, #266 #267 #279) and html.parser for HTML. No
Java/veraPDF/browser dependency, and no python-docx/python-pptx (#293).

This is still a structural heuristic, not a full WCAG or PDF/UA conformance
test -- real conformance testing needs interactive tools (screen reader,
keyboard-navigation testing) and human review, which this cannot replace.
Say so every time this script's output is used in a report. What this DOES
check, for real, that a text-extraction-only heuristic could not:

  PDF (.pdf):
  - tagged_pdf:        PDF has MarkInfo.Marked=true AND a StructTreeRoot
                        (screen readers need both to determine reading
                        order and semantic structure)
  - language_metadata: document-level /Lang is set
  - title_metadata:    document Title metadata is set (not just the filename)
  - figures_total / figures_with_alt: walks the structure tree (only
                        possible if tagged) counting /Figure elements and
                        how many carry an /Alt entry

  DOCX (.docx):
  - language_metadata / title_metadata: dc:language / dc:title in the
                        package core properties (docProps/core.xml)
  - figures_total / figures_with_alt: each inline or floating (anchored)
                        drawing in the main document part, by its wp:docPr
                        descr/title attribute. Text boxes and shapes
                        (wordprocessingShape) are not figures, and the
                        mc:Fallback copy of a drawing is not counted twice.

  PPTX (.pptx):
  - language_metadata / title_metadata: dc:language / dc:title in the
                        package core properties (docProps/core.xml)
  - slides_total / slides_with_title: each slide's title (or centre-title)
                        placeholder text (screen readers and
                        slide-navigation tools rely on per-slide titles, not
                        just the deck title)
  - figures_total / figures_with_alt: each picture (p:pic) cNvPr descr/title
                        attribute (walked recursively into group shapes; the
                        mc:Fallback copy of a picture is not counted twice).
                        Video/audio shapes and the icon preview of an
                        embedded (OLE) object are not images.
                        Caveat: some authoring tools (including python-pptx,
                        when used to insert an image programmatically)
                        auto-populate descr with the source filename rather
                        than leaving it blank -- a non-empty descr means the
                        attribute is present, not that it is meaningful
                        alt text. Same class of limitation as the PDF/DOCX
                        checks above: presence, not quality, is what's tested.

  HTML (.html/.htm), parsed with the stdlib html.parser -- no browser or
  rendering engine, so this cannot see content injected by JavaScript:
  - language_metadata: <html lang="..."> (or xml:lang) attribute is set
  - title_metadata:    <title> element has non-empty text
  - heading_hierarchy_ok: heading levels (h1-h6) in document order never
                        skip a level going deeper (e.g. h1 -> h3 with no h2)
  - has_h1:            at least one <h1> element is present
  - figures_total / figures_with_alt: each <img> counted, "has alt" means
                        the alt attribute is present at all (including
                        alt="" for intentionally-decorative images, which is
                        valid under WCAG); a missing alt attribute entirely
                        is the failure this flags

Only .pdf, .docx, .pptx, .html, and .htm are supported today -- other formats
are reported as skipped, not silently ignored, so a report can say plainly
what wasn't checked.

Usage:
    python3 accessibility_check.py <path-to-file>
Prints a JSON result to stdout. DOCX, PPTX and HTML need only the standard
library. PDF needs pikepdf; when it is missing the PDF result carries one
error naming the package and the supported install path, and the exit status
is 2. The supported way to run PDF checks (pinned, and uv keeps the
environment in its own cache, never in the run folder):
    uv run --with pikepdf==10.13.0.post1 python accessibility_check.py <file>
"""

import json
import os
import posixpath
import sys
import zipfile
from xml.etree import ElementTree as ET

# Keep in step with the pinned command in the docstring above and in
# compliance-mapping/SKILL.md (a test pins all three together).
PIKEPDF_VERSION = "10.13.0.post1"
PIKEPDF_MISSING = (
    "pikepdf is not installed, so this PDF was not checked. Run the script "
    "with the supported, pinned install path instead: uv run --with "
    "pikepdf==%s python accessibility_check.py <file> -- uv keeps that "
    "environment in its own cache; never build a venv in the run folder."
    % PIKEPDF_VERSION
)


def check_pdf(path):
    result = {"file": path, "type": "pdf", "issues": [], "checks": {}}
    try:
        import pikepdf
    except ImportError:
        result["error"] = PIKEPDF_MISSING
        result["missing_dependency"] = "pikepdf"
        return result

    try:
        pdf = pikepdf.open(path)
    except Exception as e:
        result["error"] = "could not open PDF: %s" % e
        return result

    root = pdf.Root

    # -- Tagged?
    marked = False
    try:
        marked = bool(root.MarkInfo.Marked)
    except Exception:
        marked = False
    has_struct_tree = "/StructTreeRoot" in root
    tagged = marked and has_struct_tree
    result["checks"]["tagged_pdf"] = tagged
    if not tagged:
        result["issues"].append(
            "Not a tagged PDF (no MarkInfo.Marked + StructTreeRoot) -- screen "
            "readers cannot reliably determine reading order or semantic structure."
        )

    # -- Language
    lang = None
    try:
        if "/Lang" in root:
            lang = str(root.Lang)
    except Exception:
        lang = None
    result["checks"]["language_metadata"] = bool(lang)
    result["checks"]["language_value"] = lang
    if not lang:
        result["issues"].append(
            "No document-level /Lang entry -- assistive technology cannot "
            "determine the document's language."
        )

    # -- Title
    title = None
    try:
        if pdf.docinfo is not None and "/Title" in pdf.docinfo:
            title = str(pdf.docinfo["/Title"])
    except Exception:
        title = None
    result["checks"]["title_metadata"] = bool(title)
    if not title:
        result["issues"].append(
            "No document Title metadata set -- screen readers announce the "
            "filename instead of a meaningful title."
        )

    # -- Alt text on figures (only walkable if tagged)
    figures_total = 0
    figures_with_alt = 0
    if has_struct_tree:
        try:
            import pikepdf as pk

            def walk(node, depth=0):
                nonlocal figures_total, figures_with_alt
                if depth > 40 or node is None:
                    return
                try:
                    s_type = node.get("/S", None) if hasattr(node, "get") else None
                except Exception:
                    s_type = None
                if s_type is not None and str(s_type) == "/Figure":
                    figures_total += 1
                    try:
                        if "/Alt" in node:
                            figures_with_alt += 1
                    except Exception:
                        pass
                try:
                    kids = node.get("/K", None) if hasattr(node, "get") else None
                except Exception:
                    kids = None
                if kids is None:
                    return
                if isinstance(kids, pk.Array):
                    for k in kids:
                        walk(k, depth + 1)
                else:
                    walk(kids, depth + 1)

            struct_root = root.StructTreeRoot
            k = struct_root.get("/K", None) if "/K" in struct_root else None
            if isinstance(k, pk.Array):
                for item in k:
                    walk(item)
            elif k is not None:
                walk(k)
        except Exception as e:
            result["issues"].append(
                "Could not fully walk structure tree for alt-text check: %s" % e
            )

    result["checks"]["figures_total"] = figures_total
    result["checks"]["figures_with_alt"] = figures_with_alt
    if figures_total > 0 and figures_with_alt < figures_total:
        result["issues"].append(
            "%d of %d tagged figures have no /Alt text."
            % (figures_total - figures_with_alt, figures_total)
        )

    pdf.close()
    return result


# -- OOXML (DOCX/PPTX) via the standard library -----------------------------

# Bound on the decompressed XML read per document (zip-bomb guard).
MAX_XML_BYTES = 256 * 1024 * 1024
PKG_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
DOC_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
WML = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
WPD = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
DML = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
PML = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
MCE = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"
DC = "{http://purl.org/dc/elements/1.1/}"
WPS_URI = "http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
# A p:pic carrying one of these in its nvPr is a video/audio shape, not an image.
MEDIA_TAGS = frozenset(
    DML + name
    for name in ("videoFile", "audioFile", "quickTimeFile", "wavAudioFile", "audioCd")
)
# Strict OOXML (ISO/IEC 29500 Strict) uses other namespace URIs for the same
# vocabulary; tags are mapped to Transitional before matching.
STRICT_NAMESPACES = {
    "{http://purl.oclc.org/ooxml/wordprocessingml/main}": WML,
    "{http://purl.oclc.org/ooxml/drawingml/wordprocessingDrawing}": WPD,
    "{http://purl.oclc.org/ooxml/drawingml/main}": DML,
    "{http://purl.oclc.org/ooxml/presentationml/main}": PML,
    "{http://purl.oclc.org/ooxml/officeDocument/relationships}": DOC_REL,
}


def _transitional(name):
    if name.startswith("{http://purl.oclc.org/ooxml/"):
        namespace, _, local = name.partition("}")
        return STRICT_NAMESPACES.get(namespace + "}", namespace + "}") + local
    return name


class _Package:
    """Read-only OOXML package with a decompressed-size budget."""

    def __init__(self, path):
        self.archive = zipfile.ZipFile(path)
        self.names = set(self.archive.namelist())
        self.remaining = MAX_XML_BYTES

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.archive.close()

    def parse(self, name):
        info = self.archive.getinfo(name)
        if info.file_size > self.remaining:
            raise ValueError("document XML exceeds the read budget")
        self.remaining -= info.file_size
        with self.archive.open(info) as handle:
            root = ET.parse(handle).getroot()
        for elem in root.iter():
            elem.tag = _transitional(elem.tag)
            for key in [k for k in elem.attrib if k.startswith("{")]:
                elem.attrib[_transitional(key)] = elem.attrib.pop(key)
        return root

    def relationships(self, part):
        """``{rId: (type, resolved part name)}`` for one part."""
        base, leaf = posixpath.split(part)
        rels = posixpath.join(base, "_rels", leaf + ".rels")
        if rels not in self.names:
            return {}
        result = {}
        for rel in self.parse(rels).iter(PKG_REL + "Relationship"):
            if rel.get("TargetMode") == "External":
                continue
            target = rel.get("Target", "")
            if target.startswith("/"):
                resolved = target.lstrip("/")
            else:
                resolved = posixpath.normpath(posixpath.join(base, target))
            result[rel.get("Id")] = (rel.get("Type", ""), resolved)
        return result

    def related(self, part, suffix, default=None):
        for kind, target in self.relationships(part).values():
            if kind.endswith(suffix) and target in self.names:
                return target
        return default if default in self.names else None

    def core_properties(self):
        """``(title, language)`` from the core properties, blank as None."""
        part = self.related("", "/metadata/core-properties", "docProps/core.xml")
        if part is None:
            return None, None
        root = self.parse(part)
        title = (root.findtext(DC + "title") or "").strip()
        language = (root.findtext(DC + "language") or "").strip()
        return title or None, language or None


def _require(root, tag):
    if root.tag != tag:
        raise ValueError("unrecognised main part vocabulary")


def _walk(root, prune=()):
    """Every element in document order, minus ``mc:Fallback`` subtrees.

    A Fallback repeats its ``mc:Choice`` for older readers; counting both
    would count the same picture twice. Elements whose tag is in ``prune``
    are yielded but not descended into.
    """
    stack = [root]
    while stack:
        elem = stack.pop()
        yield elem
        if elem.tag in prune:
            continue
        stack.extend(c for c in reversed(list(elem)) if c.tag != MCE + "Fallback")


def _has_alt(elem):
    return elem is not None and bool(elem.get("descr") or elem.get("title"))


def _metadata_checks(result, title, lang):
    result["checks"]["title_metadata"] = bool(title)
    if not title:
        result["issues"].append("No document Title set in core properties.")
    result["checks"]["language_metadata"] = bool(lang)
    if not lang:
        result["issues"].append("No document language set in core properties.")


def _figure_checks(result, figures_total, figures_with_alt):
    result["checks"]["figures_total"] = figures_total
    result["checks"]["figures_with_alt"] = figures_with_alt
    if figures_total > 0 and figures_with_alt < figures_total:
        result["issues"].append(
            "%d of %d images have no alt text/description set."
            % (figures_total - figures_with_alt, figures_total)
        )


def check_docx(path):
    result = {"file": path, "type": "docx", "issues": [], "checks": {}}
    try:
        with _Package(path) as package:
            title, lang = package.core_properties()
            main = package.related("", "/officeDocument", "word/document.xml")
            if main is None:
                raise ValueError("no main document part")
            root = package.parse(main)
            _require(root, WML + "document")
    except Exception as e:
        result["error"] = "could not open DOCX: %s" % e
        return result

    _metadata_checks(result, title, lang)

    figures_total = 0
    figures_with_alt = 0
    for elem in _walk(root):
        if elem.tag not in (WPD + "inline", WPD + "anchor"):
            continue
        data = elem.find("%sgraphic/%sgraphicData" % (DML, DML))
        if data is not None and data.get("uri") == WPS_URI:
            continue  # a text box or shape, not a figure
        figures_total += 1
        if _has_alt(elem.find(WPD + "docPr")):
            figures_with_alt += 1

    _figure_checks(result, figures_total, figures_with_alt)
    return result


def check_pptx(path):
    result = {"file": path, "type": "pptx", "issues": [], "checks": {}}
    try:
        with _Package(path) as package:
            title, lang = package.core_properties()
            main = package.related("", "/officeDocument", "ppt/presentation.xml")
            if main is None:
                raise ValueError("no presentation part")
            rels = package.relationships(main)
            presentation = package.parse(main)
            _require(presentation, PML + "presentation")
            slides = []
            for entry in presentation.iter(PML + "sldId"):
                _, part = rels[entry.get(DOC_REL + "id")]
                slide = package.parse(part)
                _require(slide, PML + "sld")
                slides.append(slide)
    except Exception as e:
        result["error"] = "could not open PPTX: %s" % e
        return result

    _metadata_checks(result, title, lang)

    slides_with_title = 0
    figures_total = 0
    figures_with_alt = 0
    for slide in slides:
        title_seen = False
        # A graphic frame (chart, table, embedded object) carries its alt
        # text on its own cNvPr; an OLE icon preview inside it is not a figure.
        for elem in _walk(slide, prune={PML + "graphicFrame"}):
            if elem.tag == PML + "sp" and not title_seen:
                ph = elem.find("%snvSpPr/%snvPr/%sph" % (PML, PML, PML))
                if ph is not None and ph.get("type") in ("title", "ctrTitle"):
                    title_seen = True
                    words = "".join(t.text or "" for t in elem.iter(DML + "t"))
                    if words.strip():
                        slides_with_title += 1
            elif elem.tag == PML + "pic":
                nv_pr = elem.find("%snvPicPr/%snvPr" % (PML, PML))
                if nv_pr is not None and any(c.tag in MEDIA_TAGS for c in nv_pr):
                    continue  # video/audio, as python-pptx's shape_type MEDIA
                figures_total += 1
                if _has_alt(elem.find("%snvPicPr/%scNvPr" % (PML, PML))):
                    figures_with_alt += 1

    slides_total = len(slides)
    result["checks"]["slides_total"] = slides_total
    result["checks"]["slides_with_title"] = slides_with_title
    if slides_total > 0 and slides_with_title < slides_total:
        result["issues"].append(
            "%d of %d slides have no title placeholder text -- screen readers "
            "and slide-navigation tools rely on per-slide titles."
            % (slides_total - slides_with_title, slides_total)
        )

    _figure_checks(result, figures_total, figures_with_alt)
    return result


class _A11yHTMLParser:
    """Minimal, dependency-free HTML structure walker built on the stdlib
    html.parser. No rendering engine -- content injected by JavaScript after
    load is invisible to this, same limitation as every other check here
    that reads static file bytes rather than executing the document."""

    def __init__(self):
        from html.parser import HTMLParser

        class _Parser(HTMLParser):
            def __init__(self):
                super().__init__(convert_charrefs=True)
                self.lang = None
                self.title = ""
                self._in_title = False
                self.headings = []  # list of ints, document order
                self.images = []  # list of bool, has_alt

            def handle_starttag(self, tag, attrs):
                tag = tag.lower()
                attrs_d = {k.lower(): v for k, v in attrs}
                if tag == "html":
                    self.lang = attrs_d.get("lang") or attrs_d.get("xml:lang")
                elif tag == "title":
                    self._in_title = True
                elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                    self.headings.append(int(tag[1]))
                elif tag == "img":
                    self.images.append("alt" in attrs_d)

            def handle_startendtag(self, tag, attrs):
                # self-closing tags, e.g. <img ... />
                self.handle_starttag(tag, attrs)

            def handle_data(self, data):
                if self._in_title:
                    self.title += data

            def handle_endtag(self, tag):
                if tag.lower() == "title":
                    self._in_title = False

        self._parser = _Parser()

    def feed(self, text):
        self._parser.feed(text)

    @property
    def lang(self):
        return self._parser.lang

    @property
    def title(self):
        return self._parser.title

    @property
    def headings(self):
        return self._parser.headings

    @property
    def images(self):
        return self._parser.images


def check_html(path):
    result = {"file": path, "type": "html", "issues": [], "checks": {}}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except Exception as e:
        result["error"] = "could not open HTML: %s" % e
        return result

    parser = _A11yHTMLParser()
    try:
        parser.feed(text)
    except Exception as e:
        result["issues"].append("Could not fully parse HTML: %s" % e)

    lang = parser.lang
    result["checks"]["language_metadata"] = bool(lang)
    result["checks"]["language_value"] = lang
    if not lang:
        result["issues"].append(
            'No <html lang="..."> attribute -- assistive technology cannot '
            "determine the page's language."
        )

    title = (parser.title or "").strip()
    result["checks"]["title_metadata"] = bool(title)
    if not title:
        result["issues"].append(
            "No non-empty <title> element -- screen readers announce the URL "
            "instead of a meaningful title."
        )

    headings = parser.headings
    has_h1 = 1 in headings
    result["checks"]["has_h1"] = has_h1
    if headings and not has_h1:
        result["issues"].append("No <h1> element found on the page.")

    skips = []
    prev_level = 0
    for lvl in headings:
        if prev_level and lvl > prev_level + 1:
            skips.append((prev_level, lvl))
        prev_level = lvl
    result["checks"]["heading_hierarchy_ok"] = len(skips) == 0
    if skips:
        result["issues"].append(
            "Heading level(s) skipped: "
            + ", ".join("h%d -> h%d" % (a, b) for a, b in skips)
            + " -- screen reader users navigating by heading level will miss "
            "the skipped level(s)."
        )

    images = parser.images
    figures_total = len(images)
    figures_with_alt = sum(1 for has_alt in images if has_alt)
    result["checks"]["figures_total"] = figures_total
    result["checks"]["figures_with_alt"] = figures_with_alt
    if figures_total > 0 and figures_with_alt < figures_total:
        result["issues"].append(
            "%d of %d <img> elements have no alt attribute at all."
            % (figures_total - figures_with_alt, figures_total)
        )

    return result


def check_file(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return check_pdf(path)
    elif ext == ".docx":
        return check_docx(path)
    elif ext == ".pptx":
        return check_pptx(path)
    elif ext in (".html", ".htm"):
        return check_html(path)
    else:
        return {
            "file": path,
            "type": ext.lstrip("."),
            "checks": {},
            "issues": [],
            "skipped": (
                "unsupported file type for structural accessibility check "
                "(only .pdf, .docx, .pptx, .html, and .htm are checked today)"
            ),
        }


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: accessibility_check.py <path-to-file>", file=sys.stderr)
        return 1
    result = check_file(argv[0])
    print(json.dumps(result, indent=2))
    if result.get("missing_dependency"):
        print("accessibility_check: " + result["error"], file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
