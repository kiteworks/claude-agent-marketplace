#!/usr/bin/env python3
"""Invoice-specific OCR using pre-reserved artifacts and the shared lifecycle.

Usage: ocr_extract.py --root RUN --source OWNED --out OWNED_TEXT
Requires KITEWORKS_SCRATCH_KEY. Stdout contains metadata, never document text.
pdftoppm writes one pre-reserved page at a time; tesseract uses stdout, avoiding
pytesseract's uncontrolled temporary files. Uncontrolled third-party caches must
still be disclosed. Original survives text-layer/OCR fallback until finally.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
from pathlib import Path

HELPER = (
    Path(__file__).resolve().parents[2] / "content-extract/scripts/scratch_lifecycle.py"
)
spec = importlib.util.spec_from_file_location("invoice_scratch", HELPER)
lifecycle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lifecycle)

MAX_PAGES = 100
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".gif", ".webp"}


def _command(command, run, timeout=120):
    env = {k: v for k, v in os.environ.items() if k != "KITEWORKS_SCRATCH_KEY"}
    env.update(TMPDIR=str(run.root), TMP=str(run.root), TEMP=str(run.root))
    return subprocess.run(
        command,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=timeout,
        env=env,
        cwd=run.root,
    ).stdout.decode("utf-8", errors="replace")


def extract(run, source, out):
    run.check(source)
    run.check(out)
    if (
        source == out
        or out.stat().st_size
        or run.data["artifacts"][out.name]["role"] != "text"
    ):
        raise ValueError("OCR output must be a distinct empty reserved text artifact")
    result = {
        "parse": "failed",
        "output": str(out),
        "cleanup": [],
        "cleanup_complete": False,
        "warnings": [],
    }
    try:
        ext = source.suffix.lower()
        if ext not in IMAGE_EXTS | {".pdf", ".heic", ".heif"}:
            result["parse"] = "unavailable"
            result["error"] = "unsupported_format"
            return result
        required = ["pdftotext"] if ext == ".pdf" else ["tesseract"]
        if any(shutil.which(tool) is None for tool in required):
            result["parse"] = "unavailable"
            result["error"] = "missing_parser"
            return result
        if not source.stat().st_size:
            raise ValueError("empty source")
        text = ""
        pages = 1
        if ext == ".pdf":
            pages = None
            if shutil.which("pdfinfo"):
                try:
                    info = _command(["pdfinfo", str(source)], run, 30)
                    pages = next(
                        int(line.split(":", 1)[1])
                        for line in info.splitlines()
                        if line.lower().startswith("pages:")
                    )
                except (OSError, ValueError, StopIteration, subprocess.SubprocessError):
                    pages = None
            if pages is not None and not 1 <= pages <= MAX_PAGES:
                raise ValueError("page cap exceeded")
            try:
                text = _command(["pdftotext", str(source), "-"], run, 60)
            except subprocess.CalledProcessError:
                text = ""  # original is still needed for OCR fallback
            if len(text.strip()) >= 15 * (pages or 1):
                result["method"] = "text_layer"
            else:
                if pages is None or any(
                    not shutil.which(tool) for tool in ["pdftoppm", "tesseract"]
                ):
                    result.update(
                        parse="unavailable", error="missing_ocr_parser_or_page_count"
                    )
                    return result
                chunks = []
                for number in range(1, pages + 1):
                    image = run.reserve("ocr", ".png")
                    try:
                        _command(
                            [
                                "pdftoppm",
                                "-f",
                                str(number),
                                "-l",
                                str(number),
                                "-singlefile",
                                "-r",
                                "300",
                                "-png",
                                str(source),
                                str(image.with_suffix("")),
                            ],
                            run,
                        )
                        run.check(image)
                        chunks.append(
                            _command(["tesseract", str(image), "stdout"], run)
                        )
                    finally:
                        result["cleanup"].append(run.release(image))
                text = "\n\n".join(chunks)
                result["method"] = "ocr_pdf_rasterized"
        elif ext in {".heic", ".heif"}:
            try:
                import pillow_heif
                from PIL import Image
            except ImportError:
                result.update(parse="unavailable", error="heic_unsupported")
                return result
            image = run.reserve("ocr", ".png")
            try:
                pillow_heif.register_heif_opener()
                with Image.open(source) as decoded:
                    decoded.save(image, format="PNG")
                run.check(image)
                text = _command(["tesseract", str(image), "stdout"], run)
                result["method"] = "ocr_image"
            finally:
                result["cleanup"].append(run.release(image))
        else:
            text = _command(["tesseract", str(source), "stdout"], run)
            result["method"] = "ocr_image"
        run.check(out)
        out.write_text(text, encoding="utf-8")
        result.update(parse="parsed", pages=pages)
        if len(text.strip()) < 5 * (pages or 1):
            result["warnings"].append("near-empty result; manual review required")
    except (OSError, ValueError, StopIteration, subprocess.SubprocessError) as exc:
        result["error"] = type(exc).__name__
    finally:
        if result["parse"] != "parsed":
            result["cleanup"].append(run.release(out))
        if result["parse"] != "unavailable":
            result["cleanup"].append(run.release(source))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        with lifecycle.ScratchRun.open(
            args.root, os.environ.get("KITEWORKS_SCRATCH_KEY", "")
        ) as run:
            result = extract(run, args.source, args.out)
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
