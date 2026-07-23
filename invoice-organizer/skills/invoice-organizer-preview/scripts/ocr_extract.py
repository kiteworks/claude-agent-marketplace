#!/usr/bin/env python3
"""OCR fallback extraction for invoice-organizer, for files content-extract's
text-layer path can't handle: photographed/scanned receipts (jpg/png/tiff/
bmp/gif) and image-only PDFs (a PDF with no real text layer -- common for a
scanned receipt saved/printed to PDF).

This is invoice-organizer's own extension, not a change to the shared
content-extract skill -- kept local because it's heavier and lower-confidence
than content-extract's existing pdftotext/python-docx/openpyxl/python-pptx
paths, and only this agent currently needs it. Worth promoting into
content-extract later if another agent wants OCR too; not done pre-emptively.

Usage:
  python3 ocr_extract.py <path-to-file>

Decision logic:
  - .pdf: try `pdftotext` first (the same tool content-extract already uses).
    If the resulting text is suspiciously empty (fewer than ~15 non-whitespace
    characters per page on average -- a real heuristic, not a guess: a normal
    receipt/invoice PDF with a text layer has far more than that per page),
    treat it as image-only and rasterize each page via `pdftoppm` (300 DPI,
    PNG) then OCR each page image with tesseract, concatenating page text.
  - .jpg/.jpeg/.png/.tiff/.tif/.bmp/.gif: OCR directly via tesseract.
  - .heic/.heif: attempt decode via the `pillow_heif` library (not installed
    by default in this sandbox -- pip install pillow-heif --break-system-packages
    if the import fails, then retry once). If it still can't decode, report a
    clear, honest error rather than guessing -- this format is common from
    iPhone camera uploads and deserves a real message, not a silent skip.

Prints ONE JSON object to stdout, always, even on failure:
  {"ok": true, "method": "text_layer"|"ocr_image"|"ocr_pdf_rasterized",
   "pages": N, "text": "...", "warnings": ["..."]}
  {"ok": false, "error": "heic_unsupported"|"file_not_found"|"ocr_failed"|"...",
   "message": "human-readable explanation"}

Never fabricates text -- if OCR produces nothing usable, says so plainly in
"warnings" (near-empty result) rather than the caller assuming any output
is trustworthy.
"""
import json
import os
import subprocess
import sys
import tempfile

TEXT_LAYER_MIN_CHARS_PER_PAGE = 15
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".gif", ".webp"}
HEIC_EXTS = {".heic", ".heif"}


def _fail(error, message):
    print(json.dumps({"ok": False, "error": error, "message": message}))
    sys.exit(0)


def _pdf_page_count(path):
    try:
        out = subprocess.run(["pdfinfo", path], capture_output=True, text=True, timeout=30)
        for line in out.stdout.splitlines():
            if line.lower().startswith("pages:"):
                return int(line.split(":")[1].strip())
    except Exception:
        pass
    return None


def _ocr_image_file(path, warnings):
    from PIL import Image
    import pytesseract

    img = Image.open(path)
    text = pytesseract.image_to_string(img)
    if len(text.strip()) < 5:
        warnings.append("OCR produced almost no text -- likely a blank, blurry, or unreadable image.")
    return text


def _ocr_pdf_rasterized(path, warnings):
    pages = _pdf_page_count(path) or 1
    with tempfile.TemporaryDirectory() as td:
        prefix = os.path.join(td, "page")
        subprocess.run(
            ["pdftoppm", "-r", "300", "-png", path, prefix],
            check=True, capture_output=True, timeout=120,
        )
        page_files = sorted(f for f in os.listdir(td) if f.startswith("page"))
        if not page_files:
            warnings.append("pdftoppm produced no page images -- PDF may be corrupt or encrypted.")
            return "", 0
        from PIL import Image
        import pytesseract

        chunks = []
        for pf in page_files:
            img = Image.open(os.path.join(td, pf))
            chunks.append(pytesseract.image_to_string(img))
        text = "\n\n".join(chunks)
        if len(text.strip()) < 5 * len(page_files):
            warnings.append("OCR produced very little text across all pages -- likely a poor scan (faded thermal print, skewed photo, or blank pages).")
        return text, len(page_files)


def main():
    if len(sys.argv) != 2:
        _fail("bad_args", "Usage: ocr_extract.py <path-to-file>")
    path = sys.argv[1]
    if not os.path.isfile(path):
        _fail("file_not_found", f"No such file: {path}")

    ext = os.path.splitext(path)[1].lower()
    warnings = []

    if ext in HEIC_EXTS:
        try:
            import pillow_heif
            pillow_heif.register_heif_opener()
        except ImportError:
            _fail(
                "heic_unsupported",
                "HEIC/HEIF image -- the decoder isn't installed in this environment. "
                "Run: pip install pillow-heif --break-system-packages, then retry. "
                "If that's not possible here, ask the user to re-export/convert the "
                "file to JPG or PNG (common on iPhone Kiteworks uploads) and re-scan.",
            )
        try:
            text = _ocr_image_file(path, warnings)
            print(json.dumps({"ok": True, "method": "ocr_image", "pages": 1, "text": text, "warnings": warnings}))
        except Exception as e:
            _fail("ocr_failed", f"HEIC decoded but OCR failed: {e}")
        return

    if ext in IMAGE_EXTS:
        try:
            text = _ocr_image_file(path, warnings)
        except Exception as e:
            _fail("ocr_failed", f"OCR failed on image file: {e}")
        print(json.dumps({"ok": True, "method": "ocr_image", "pages": 1, "text": text, "warnings": warnings}))
        return

    if ext == ".pdf":
        # First try the real text layer, exactly like content-extract does.
        try:
            out = subprocess.run(["pdftotext", path, "-"], capture_output=True, text=True, timeout=60)
            text_layer = out.stdout or ""
        except Exception:
            text_layer = ""

        pages = _pdf_page_count(path) or 1
        avg_chars = len(text_layer.strip()) / max(pages, 1)

        if avg_chars >= TEXT_LAYER_MIN_CHARS_PER_PAGE:
            print(json.dumps({"ok": True, "method": "text_layer", "pages": pages, "text": text_layer, "warnings": warnings}))
            return

        # Fall back to rasterize + OCR -- this is the image-only-PDF case.
        try:
            text, page_count = _ocr_pdf_rasterized(path, warnings)
        except Exception as e:
            _fail("ocr_failed", f"PDF has no usable text layer and OCR rasterization failed: {e}")
        print(json.dumps({"ok": True, "method": "ocr_pdf_rasterized", "pages": page_count, "text": text, "warnings": warnings}))
        return

    _fail("unsupported_format", f"'{ext}' isn't a format this OCR fallback handles (images and PDFs only).")


if __name__ == "__main__":
    main()
