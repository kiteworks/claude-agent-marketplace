#!/usr/bin/env python3
"""Parse owned files; parse and cleanup results are independent.

Generated from scratch-foundation, component 1.0.0. No prior-run discovery.
DOCX, PPTX and XLSX are read natively (stdlib zip + XML): pandoc drops
Title-styled DOCX paragraphs, PPTX speaker notes and grouped shapes, and cannot
open openpyxl workbooks, whose relationships use absolute part names. PDF uses
pdftotext. Images (JPEG, PNG, TIFF) and image-only PDFs are OCR'd with the
tesseract CLI (PDF pages rasterized one at a time by pdftoppm into owned
``ocr`` reservations). A missing OCR tool is reported per file in
``not_content_checked``, never skipped silently (#295).
"""

from __future__ import annotations

import argparse
import json
import os
import posixpath
import re
import shutil
import subprocess
import zipfile
import zlib
from pathlib import Path
from xml.etree import ElementTree as ET

from scratch_lifecycle import ScratchRun

PARSE_TIMEOUT_SECONDS = 300
NATIVE = "native"
OCR = "tesseract"
IMAGE_FORMATS = ("jpeg", "jpg", "png", "tif", "tiff")
PARSER_BY_FORMAT = {
    "pdf": "pdftotext",
    "docx": NATIVE,
    "pptx": NATIVE,
    "xlsx": NATIVE,
    **{fmt: OCR for fmt in IMAGE_FORMATS},
}
# A PDF whose text layer holds fewer non-space characters than this per page
# is image-only (a scan) and is OCR'd instead (same threshold as
# invoice-organizer's ocr_extract.py).
MIN_TEXT_PER_PAGE = 15
# Keeps one scanned PDF inside a 10-minute tool call (~5-15 s per page).
MAX_OCR_PAGES = 30
OCR_DPI = "300"
OCR_TIMEOUT_SECONDS = 120
# Checked when tesseract is not on PATH (the installers do not always add it).
WINDOWS_TESSERACT = (
    r"%ProgramFiles%\Tesseract-OCR\tesseract.exe",
    r"%ProgramFiles(x86)%\Tesseract-OCR\tesseract.exe",
    r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe",
)
OCR_UNAVAILABLE = "not content-checked: OCR unavailable (tesseract not found)"
RASTERIZER_UNAVAILABLE = (
    "not content-checked: OCR unavailable (pdftoppm not found to rasterize the PDF)"
)
OCR_PAGE_CAP = "not content-checked: OCR skipped (more than %d pages)" % MAX_OCR_PAGES
# Bound on the decompressed XML read per document (zip-bomb guard).
MAX_XML_BYTES = 256 * 1024 * 1024
PARSE_ERRORS = (
    OSError,
    ValueError,
    KeyError,
    IndexError,
    EOFError,
    MemoryError,
    RecursionError,
    RuntimeError,  # includes NotImplementedError (compression)
    zipfile.BadZipFile,
    zlib.error,
    ET.ParseError,
    subprocess.SubprocessError,
)

_IS_WINDOWS = os.name == "nt"
SML = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
WML = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
PML = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
DML = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
MCE = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"
PKG_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
DOC_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
# Strict OOXML (ISO/IEC 29500 Strict) uses other namespace URIs for the same
# vocabulary; tags are mapped to Transitional before matching.
STRICT_NAMESPACES = {
    "{http://purl.oclc.org/ooxml/spreadsheetml/main}": SML,
    "{http://purl.oclc.org/ooxml/wordprocessingml/main}": WML,
    "{http://purl.oclc.org/ooxml/presentationml/main}": PML,
    "{http://purl.oclc.org/ooxml/drawingml/main}": DML,
    "{http://purl.oclc.org/ooxml/officeDocument/relationships}": DOC_REL,
}


def long_path(path) -> str:
    """Absolute path with Windows 8.3 short names (``RICK~1.GOU``) expanded.

    Claude Code flags 8.3 names as a suspicious Windows path pattern. The
    longest existing prefix is expanded, so a not-yet-created tail survives.
    Elsewhere, and for paths without ``~``, this is ``os.path.abspath``.
    """
    absolute = os.path.abspath(path)
    if not _IS_WINDOWS or "~" not in absolute:
        return absolute
    import ctypes

    size = 32768
    buffer = ctypes.create_unicode_buffer(size)
    head, tail = absolute, []
    while True:
        length = ctypes.windll.kernel32.GetLongPathNameW(head, buffer, size)
        if 0 < length < size:
            return os.path.join(buffer.value, *reversed(tail))
        parent, name = os.path.split(head)
        if not name or parent == head:
            return absolute
        tail.append(name)
        head = parent


def find_tesseract() -> str | None:
    """tesseract on PATH, else in a standard Windows install folder."""
    found = shutil.which(OCR)
    if found or not _IS_WINDOWS:
        return found
    for candidate in WINDOWS_TESSERACT:
        path = os.path.expandvars(candidate)
        if "%" not in path and os.path.isfile(path):
            return path
    return None


def available(fmt):
    tool = PARSER_BY_FORMAT[fmt]
    if tool == NATIVE:
        return True
    if tool == OCR:
        return find_tesseract() is not None
    if not shutil.which(tool):
        return False
    if tool == "pandoc":
        try:
            result = subprocess.run(
                [tool, "--list-input-formats"],
                check=True,
                capture_output=True,
                timeout=10,
            )
            return fmt in result.stdout.decode("utf-8", errors="replace").split()
        except (OSError, subprocess.SubprocessError):
            return False
    return True


class _Package:
    """Read-only OOXML package with a decompressed-size budget."""

    def __init__(self, path: Path):
        self.archive = zipfile.ZipFile(path)
        self.names = set(self.archive.namelist())
        self.remaining = MAX_XML_BYTES

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.archive.close()

    def open(self, name: str):
        info = self.archive.getinfo(name)
        if info.file_size > self.remaining:
            raise ValueError("document XML exceeds the extraction budget")
        self.remaining -= info.file_size
        return self.archive.open(info)

    def parse(self, name: str):
        with self.open(name) as handle:
            return _transitional(ET.parse(handle).getroot())

    def relationships(self, part: str) -> dict[str, tuple[str, str]]:
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
            if target.startswith("/"):  # absolute part name (openpyxl)
                resolved = target.lstrip("/")
            else:
                resolved = posixpath.normpath(posixpath.join(base, target))
            result[rel.get("Id")] = (rel.get("Type", ""), resolved)
        return result

    def main_part(self, default: str) -> str:
        for kind, target in self.relationships("").values():
            if kind.endswith("/officeDocument"):
                return target
        return default


def _strict_to_transitional(name: str) -> str:
    if name.startswith("{http://purl.oclc.org/ooxml/"):
        namespace, _, local = name.partition("}")
        return STRICT_NAMESPACES.get(namespace + "}", namespace + "}") + local
    return name


def _transitional(root):
    for elem in root.iter():
        elem.tag = _strict_to_transitional(elem.tag)
        for key in [k for k in elem.attrib if k.startswith("{")]:
            elem.attrib[_strict_to_transitional(key)] = elem.attrib.pop(key)
    return root


def _require(root, tag: str) -> None:
    if root.tag != tag:
        raise ValueError("unrecognised main part vocabulary")


def _text(elem, text_tag, skip=()) -> str:
    parts = []
    for child in elem:
        if child.tag in skip:
            continue
        if child.tag == text_tag:
            parts.append(child.text or "")
        else:
            parts.append(_text(child, text_tag, skip))
    return "".join(parts)


def _column(ref: str | None) -> int | None:
    letters = re.match(r"[A-Z]+", ref or "")
    if not letters:
        return None
    number = 0
    for letter in letters.group():
        number = number * 26 + ord(letter) - ord("A") + 1
    return number - 1


def _cell_value(cell, shared: list[str]) -> str:
    kind = cell.get("t", "n")
    if kind == "inlineStr":
        inline = cell.find(SML + "is")
        return "" if inline is None else _text(inline, SML + "t", {SML + "rPh"})
    raw = cell.findtext(SML + "v") or ""
    if kind == "s":
        return shared[int(raw)] if raw else ""
    if kind == "b":
        return "TRUE" if raw.strip() == "1" else "FALSE"
    return raw


def extract_xlsx(path: Path) -> str:
    """Every sheet, in workbook order, as tab-separated rows."""
    with _Package(path) as package:
        workbook = package.main_part("xl/workbook.xml")
        rels = package.relationships(workbook)
        shared = []
        strings = [t for kind, t in rels.values() if kind.endswith("/sharedStrings")]
        for part in strings or ["xl/sharedStrings.xml"]:
            if part in package.names:
                root = package.parse(part)
                shared = [
                    _text(si, SML + "t", {SML + "rPh"}) for si in root.iter(SML + "si")
                ]
        book = package.parse(workbook)
        _require(book, SML + "workbook")
        blocks = []
        for sheet in book.iter(SML + "sheet"):
            _, part = rels[sheet.get(DOC_REL + "id")]
            lines = [f"## Sheet: {sheet.get('name', '')}"]
            with package.open(part) as handle:
                for _, row in ET.iterparse(handle):
                    if not row.tag.endswith("}row"):
                        continue
                    _transitional(row)
                    if row.tag != SML + "row":
                        continue
                    values: list[str] = []
                    for cell in row.iter(SML + "c"):
                        index = _column(cell.get("r"))
                        if index is not None and index > len(values):
                            values.extend([""] * (index - len(values)))
                        value = _cell_value(cell, shared)
                        values.append(" ".join(value.split("\n")))
                    while values and not values[-1]:
                        values.pop()
                    if values:
                        lines.append("\t".join(values))
                    row.clear()
            blocks.append("\n".join(lines))
        return "\n\n".join(blocks) + "\n"


# Properties hold tab-stop definitions (w:tab) and no text; the VML fallback
# repeats the DrawingML text box; field codes and deletions are not text.
_DOCX_SKIP = {
    MCE + "Fallback",
    WML + "pPr",
    WML + "rPr",
    WML + "instrText",
    WML + "delText",
}


def _docx_paragraphs(elem, buffer: list[str], lines: list[str]) -> None:
    for child in elem:
        tag = child.tag
        if tag in _DOCX_SKIP:
            continue
        if tag == WML + "p":
            inner: list[str] = []
            _docx_paragraphs(child, inner, lines)
            lines.append("".join(inner))
        elif tag == WML + "t":
            buffer.append(child.text or "")
        elif tag == WML + "tab":
            buffer.append("\t")
        elif tag in (WML + "br", WML + "cr"):
            buffer.append("\n")
        elif tag == WML + "noBreakHyphen":
            buffer.append("-")
        else:
            _docx_paragraphs(child, buffer, lines)


def _natural(name: str):
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", name)]


def extract_docx(path: Path) -> str:
    """Headers, body (Title/Subtitle included), notes and footers as lines."""
    with _Package(path) as package:
        document = package.main_part("word/document.xml")
        folder = posixpath.dirname(document)

        def matching(stem):
            pattern = re.compile(rf"{re.escape(folder)}/{stem}\d*\.xml")
            return sorted(filter(pattern.fullmatch, package.names), key=_natural)

        parts = [
            *matching("header"),
            document,
            *matching("footnotes"),
            *matching("endnotes"),
            *matching("footer"),
        ]
        lines: list[str] = []
        for part in parts:
            root = package.parse(part)
            if part == document:
                _require(root, WML + "document")
            _docx_paragraphs(root, [], lines)
        return "\n".join(line for line in lines if line.strip()) + "\n"


def _dml_paragraph(elem, buffer: list[str]) -> None:
    for child in elem:
        if child.tag == DML + "t":
            buffer.append(child.text or "")
        elif child.tag == DML + "br":
            buffer.append("\n")
        elif child.tag not in (DML + "pPr", DML + "rPr", DML + "endParaRPr"):
            _dml_paragraph(child, buffer)


def _placeholder_type(shape) -> str | None:
    for nv in shape:
        if nv.tag.startswith(PML + "nv"):
            ph = nv.find(f"{PML}nvPr/{PML}ph")
            return None if ph is None else ph.get("type", "body")
    return None


def _dml_lines(elem, lines: list[str], skip_placeholders=frozenset()) -> None:
    """DrawingML text in document order: shapes, groups, tables, text boxes.

    A table row becomes one tab-separated line. The ``mc:Fallback`` branch
    repeats its ``mc:Choice`` and is skipped.
    """
    for child in elem:
        tag = child.tag
        if tag == MCE + "Fallback":
            continue
        if tag == PML + "sp" and _placeholder_type(child) in skip_placeholders:
            continue
        if tag == DML + "p":
            buffer: list[str] = []
            _dml_paragraph(child, buffer)
            lines.append("".join(buffer))
        elif tag == DML + "tr":
            cells = []
            for cell in child.iter(DML + "tc"):
                inner: list[str] = []
                _dml_lines(cell, inner)
                cells.append(" ".join(t.strip() for t in inner if t.strip()))
            lines.append("\t".join(cells))
        else:
            _dml_lines(child, lines, skip_placeholders)


def extract_pptx(path: Path) -> str:
    """Every slide in presentation order, then its speaker notes.

    Titles, placeholders, text boxes, grouped shapes, tables, SmartArt text
    and slide footers are kept; hidden slides are included.
    """
    with _Package(path) as package:
        presentation = package.main_part("ppt/presentation.xml")
        rels = package.relationships(presentation)
        root = package.parse(presentation)
        _require(root, PML + "presentation")
        blocks = []
        for number, entry in enumerate(root.iter(PML + "sldId"), start=1):
            _, part = rels[entry.get(DOC_REL + "id")]
            slide = package.parse(part)
            _require(slide, PML + "sld")
            lines = [f"## Slide {number}"]
            _dml_lines(slide, lines)
            notes = []
            for kind, related in package.relationships(part).values():
                if related not in package.names:
                    continue
                if kind.endswith("/diagramData"):
                    _dml_lines(package.parse(related), lines)
                elif kind.endswith("/notesSlide"):
                    # The slide-number field repeats on every notes page.
                    _dml_lines(package.parse(related), notes, {"sldNum"})
            notes = [line for line in notes if line.strip()]
            if notes:
                lines += ["### Notes", *notes]
            blocks.append("\n".join(line for line in lines if line.strip()))
        return "\n\n".join(blocks) + "\n"


NATIVE_EXTRACTORS = {
    "docx": extract_docx,
    "pptx": extract_pptx,
    "xlsx": extract_xlsx,
}


def _tesseract(tesseract, image, env, cwd) -> str:
    """OCR one image; the text comes back on stdout, never as a file."""
    completed = subprocess.run(
        [tesseract, str(image), "stdout"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=OCR_TIMEOUT_SECONDS,
        env=env,
        cwd=cwd,
    )
    return completed.stdout.decode("utf-8", errors="replace")


def _ocr_pdf(scratch, source, pages, env, result) -> str | None:
    """Rasterize and OCR each page; ``None`` when OCR cannot run.

    Every page image is an owned ``ocr`` reservation, released in a
    ``finally`` as soon as its text is read.
    """
    tesseract = find_tesseract()
    reason = None
    if tesseract is None:
        reason = OCR_UNAVAILABLE
    elif not shutil.which("pdftoppm"):
        reason = RASTERIZER_UNAVAILABLE
    elif pages > MAX_OCR_PAGES:
        reason = OCR_PAGE_CAP
    if reason:
        result["not_content_checked"] = reason
        return None
    chunks = []
    for number in range(1, pages + 1):
        image = scratch.reserve("ocr", ".png")
        try:
            subprocess.run(
                [
                    "pdftoppm",
                    "-f",
                    str(number),
                    "-l",
                    str(number),
                    "-singlefile",
                    "-r",
                    OCR_DPI,
                    "-png",
                    str(source),
                    str(image.with_suffix("")),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=OCR_TIMEOUT_SECONDS,
                env=env,
                cwd=scratch.root,
            )
            scratch.check(image)
            chunks.append(_tesseract(tesseract, image, env, scratch.root))
        finally:
            result["cleanup"].append(scratch.release(image))
    result["ocr_pages"] = pages
    return "\n\n".join(chunks)


def run(scratch, source, fmt, out, *, keep_source=False, timeout=PARSE_TIMEOUT_SECONDS):
    scratch.check(source)
    scratch.check(out)
    if source == out or out.stat().st_size:
        raise ValueError("output must be a distinct empty reserved artifact")
    if scratch.data["artifacts"][out.name]["role"] not in {"text", "partial"}:
        raise ValueError("output must be registered as text")
    result = {
        "parse": "unavailable",
        "output": str(out),
        "cleanup": [],
        "cleanup_complete": False,
    }
    if not available(fmt):
        result["not_content_checked"] = (
            OCR_UNAVAILABLE
            if PARSER_BY_FORMAT[fmt] == OCR
            else "not content-checked: parser unavailable (%s not found)"
            % PARSER_BY_FORMAT[fmt]
        )
        return result  # source remains usable by a verified fallback
    result["parse"] = "failed"
    env = {
        **{k: v for k, v in os.environ.items() if k != "KITEWORKS_SCRATCH_KEY"},
        "TMPDIR": str(scratch.root),
        "TMP": str(scratch.root),
        "TEMP": str(scratch.root),
    }
    tool = PARSER_BY_FORMAT[fmt]
    command = (
        [tool, str(source), str(out)]
        if fmt == "pdf"
        else [tool, str(source), "-t", "plain", "-o", str(out)]
    )
    try:
        if source.stat().st_size == 0:
            raise ValueError("download is empty in parser environment")
        if tool == NATIVE:
            text = NATIVE_EXTRACTORS[fmt](source)
            with open(out, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
            result["method"] = "native"
        elif tool == OCR:
            text = _tesseract(find_tesseract(), source, env, scratch.root)
            with open(out, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
            result["method"] = "ocr_image"
        else:
            subprocess.run(
                command,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=timeout,
                env=env,
                cwd=scratch.root,
            )
            result["method"] = "text_layer"
            scratch.check(out)
            with open(out, encoding="utf-8", errors="replace") as handle:
                layer = handle.read()
            # pdftotext ends every page with a form feed.
            pages = max(layer.count("\f"), 1)
            chars = len("".join(layer.split()))
            if chars < MIN_TEXT_PER_PAGE * pages:
                text = _ocr_pdf(scratch, source, pages, env, result)
                if text is not None:
                    scratch.check(out)
                    with open(out, "w", encoding="utf-8", newline="\n") as handle:
                        handle.write(text)
                    result["method"] = "ocr_pdf"
                elif chars:
                    # A sparse but real text layer is still a result: keep
                    # it, and say the image content was not OCR'd.
                    result["warning"] = result.pop("not_content_checked").replace(
                        "not content-checked",
                        "sparse text layer only; images not content-checked",
                        1,
                    )
                else:
                    result["parse"] = "unavailable"
                    result.pop("method")
                    return result
        scratch.check(out)
        result["parse"] = "parsed"
    except PARSE_ERRORS as exc:
        result["error"] = type(exc).__name__
    finally:
        if result["parse"] != "parsed":
            # Partial text is untrusted; the source stays for a verified
            # fallback parser and is released by the caller or finalizer.
            result["cleanup"].append(scratch.release(out))
        elif not keep_source:
            result["cleanup"].append(scratch.release(source))
    # Successful text is still sensitive scratch: caller must release after use.
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--long-path",
        type=Path,
        help="print the host folder with Windows 8.3 short names expanded, then exit",
    )
    parser.add_argument("--root", type=Path)
    parser.add_argument("--downloaded-path", type=Path)
    parser.add_argument("--format", choices=sorted(PARSER_BY_FORMAT))
    parser.add_argument("--out", type=Path)
    parser.add_argument("--keep-source", action="store_true")
    args = parser.parse_args(argv)
    if args.long_path is not None:
        print(json.dumps({"path": long_path(args.long_path)}))
        return 0
    if not (args.root and args.downloaded_path and args.format and args.out):
        parser.error("--root, --downloaded-path, --format and --out are required")
    try:
        with ScratchRun.open(
            args.root, os.environ.get("KITEWORKS_SCRATCH_KEY", "")
        ) as scratch:
            result = run(
                scratch,
                args.downloaded_path,
                args.format,
                args.out,
                keep_source=args.keep_source,
            )
        print(json.dumps(result))
        if any(item["cleanup"] == "failed" for item in result["cleanup"]):
            return 3
        return {"parsed": 0, "failed": 1, "unavailable": 2}[result["parse"]]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(
            json.dumps(
                {
                    "parse": "not_started",
                    "cleanup_complete": False,
                    "error": type(exc).__name__,
                }
            )
        )
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
