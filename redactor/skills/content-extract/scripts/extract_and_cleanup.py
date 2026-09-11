#!/usr/bin/env python3
"""Parse owned files; parse and cleanup results are independent.

Generated from scratch-foundation, component 1.0.0. No prior-run discovery.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

from scratch_lifecycle import ScratchRun

PARSE_TIMEOUT_SECONDS = 300
CLI_TOOL_BY_FORMAT = {
    "pdf": "pdftotext",
    "docx": "pandoc",
    "pptx": "pandoc",
    "xlsx": "pandoc",
}


def available(fmt):
    tool = CLI_TOOL_BY_FORMAT[fmt]
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
        return result  # source remains usable by a verified fallback
    result["parse"] = "failed"
    env = {
        **{k: v for k, v in os.environ.items() if k != "KITEWORKS_SCRATCH_KEY"},
        "TMPDIR": str(scratch.root),
        "TMP": str(scratch.root),
        "TEMP": str(scratch.root),
    }
    tool = CLI_TOOL_BY_FORMAT[fmt]
    command = (
        [tool, str(source), str(out)]
        if fmt == "pdf"
        else [tool, str(source), "-t", "plain", "-o", str(out)]
    )
    try:
        if source.stat().st_size == 0:
            raise ValueError("download is empty in parser environment")
        subprocess.run(
            command,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
            env=env,
            cwd=scratch.root,
        )
        scratch.check(out)
        result["parse"] = "parsed"
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        result["error"] = type(exc).__name__
    finally:
        if result["parse"] != "parsed":
            result["cleanup"].append(scratch.release(out))
        if not keep_source:
            result["cleanup"].append(scratch.release(source))
    # Successful text is still sensitive scratch: caller must release after use.
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--downloaded-path", type=Path, required=True)
    parser.add_argument("--format", choices=sorted(CLI_TOOL_BY_FORMAT), required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--keep-source", action="store_true")
    args = parser.parse_args(argv)
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
