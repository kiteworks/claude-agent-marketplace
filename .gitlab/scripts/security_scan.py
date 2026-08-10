#!/usr/bin/env python3
"""
Static (non-AI) checks for the Kiteworks Claude plugin marketplace repo.

This runs only the two checks that are genuinely mechanical -- literal file
comparison, not judgment -- and are therefore both cheap to run deterministically
and NOT well suited to an LLM:
  1. Drift between an agent's source directory and its shipped .zip bundle
     (the repo ships bundles unsigned, so this is the main tamper-evidence check)
  2. Quiet permission/capability changes in plugin.json / .claude-plugin/marketplace.json

Everything requiring semantic judgment -- prompt injection in skill/agent text,
obfuscated or malicious code, unsanctioned network calls or connectors -- is
handled by ai_review.py instead. A regex can be worded around; a byte-for-byte
file diff can't, so this script sticks to what it's actually reliable at.

Writes findings to static_findings.json for the aggregator step.
Exit code is always 0 -- this script only *reports*; blocking is decided
by the aggregator based on severity.
"""

import json
import os
import sys
import zipfile
import subprocess
from pathlib import Path

REPO = Path(os.environ.get("CI_PROJECT_DIR", "."))
BASE_REF = os.environ.get("BASE_SHA", "")
HEAD_REF = os.environ.get("HEAD_SHA", "")
OUT_PATH = Path(os.environ.get("STATIC_OUT", "static_findings.json"))

TEXT_EXTS = {".md", ".json", ".yaml", ".yml", ".txt", ".py", ".js", ".ts", ".sh", ".bash", ".ps1", ".rb"}
IGNORE_DIR_PREFIXES = (".git", ".gitlab-trusted-scripts")

# Documentation/metadata files that carry no runtime behavior. Their absence
# from a shipped bundle is expected packaging hygiene, not drift -- there's
# nothing for a missing file to hide, since it's a strict subset of source.
EXPECTED_BUNDLE_EXCLUSIONS = {
    "changelog.md", "readme.md", "license", "license.md",
    "contributing.md", ".gitignore", ".gitattributes",
}


def sev_rank(sev):
    return {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}.get(sev, 0)


def is_ignored(p: Path) -> bool:
    rel_parts = p.relative_to(REPO).parts
    return bool(rel_parts) and rel_parts[0].startswith(IGNORE_DIR_PREFIXES)


def changed_files():
    full_scan = os.environ.get("FULL_SCAN", "").lower() == "true"
    if full_scan or not BASE_REF or not HEAD_REF:
        if full_scan:
            print("FULL_SCAN=true — scanning every file in the repo, not just the diff.")
        return [str(p.relative_to(REPO)) for p in REPO.rglob("*") if p.is_file() and not is_ignored(p)]
    try:
        out = subprocess.run(
            ["git", "diff", "--name-only", f"{BASE_REF}...{HEAD_REF}"],
            cwd=REPO, capture_output=True, text=True, check=True,
        ).stdout
        return [line.strip() for line in out.splitlines() if line.strip()]
    except subprocess.CalledProcessError as e:
        print(f"::warning::git diff failed, falling back to full scan: {e}", file=sys.stderr)
        return [str(p.relative_to(REPO)) for p in REPO.rglob("*") if p.is_file() and not is_ignored(p)]


def normalize_for_compare(raw_bytes: bytes, is_text: bool) -> bytes:
    """
    Normalize known-benign packaging noise before comparing bundle vs source:
    - CRLF/CR -> LF line endings (checkout normalization via .gitattributes
      is a common, harmless cause of byte-level diffs that aren't tampering)
    - a single trailing newline at EOF is not significant
    Binary files are compared as raw bytes -- no normalization.
    """
    if not is_text:
        return raw_bytes
    text = raw_bytes.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return text.rstrip(b"\n")


def diff_dirs(src_dir: Path, bundle_dir: Path):
    """
    Compare two directory trees file-by-file. Returns (missing_in_bundle,
    extra_in_bundle, content_diffs) where content_diffs is a list of
    (rel_path, src_snippet, bundle_snippet) for files that differ after
    normalization.
    """
    src_files = {str(p.relative_to(src_dir)): p for p in src_dir.rglob("*") if p.is_file()}
    bundle_files = {str(p.relative_to(bundle_dir)): p for p in bundle_dir.rglob("*") if p.is_file()}

    missing_in_bundle = sorted(set(src_files) - set(bundle_files))
    extra_in_bundle = sorted(set(bundle_files) - set(src_files))
    content_diffs = []

    for rel in sorted(set(src_files) & set(bundle_files)):
        is_text = Path(rel).suffix.lower() in TEXT_EXTS
        src_bytes = src_files[rel].read_bytes()
        bundle_bytes = bundle_files[rel].read_bytes()
        if normalize_for_compare(src_bytes, is_text) != normalize_for_compare(bundle_bytes, is_text):
            src_snip = src_bytes[:150].decode(errors="replace")
            bundle_snip = bundle_bytes[:150].decode(errors="replace")
            content_diffs.append((rel, src_snip, bundle_snip))

    return missing_in_bundle, extra_in_bundle, content_diffs


def check_bundle_drift(findings):
    """
    For each <agent>.zip at repo root, verify its extracted contents match the
    committed <agent>/ source directory, file by file, after normalizing
    known-benign differences (line endings, trailing EOF newline). Only
    genuine missing/extra/differing files are flagged, and each finding names
    the specific file so it can actually be inspected -- not a single opaque
    pass/fail on the whole bundle.

    .plugin bundles are skipped here: per this repo's README they're byte-
    identical copies of the matching .zip, so checking both would just
    double-report the same drift (or lack of it).
    """
    import shutil

    for bundle in REPO.glob("*.zip"):
        agent_name = bundle.stem
        src_dir = REPO / agent_name
        if not src_dir.is_dir():
            continue  # no matching source dir to compare against; not this check's job

        extract_dir = REPO / f".__scan_extract_{agent_name}"
        try:
            if extract_dir.exists():
                shutil.rmtree(extract_dir)
            extract_dir.mkdir()
            with zipfile.ZipFile(bundle) as zf:
                zf.extractall(extract_dir)

            # bundles sometimes wrap contents in a top-level folder; flatten if so
            entries = list(extract_dir.iterdir())
            compare_root = entries[0] if len(entries) == 1 and entries[0].is_dir() else extract_dir

            missing, extra, diffs = diff_dirs(src_dir, compare_root)

            # Docs/metadata files (CHANGELOG.md, README.md, etc.) are routinely
            # left out of the installable bundle on purpose -- there's no runtime
            # behavior to hide in a file that's simply absent, so don't even
            # report these as findings.
            missing = [
                m for m in missing
                if Path(m).name.lower() not in EXPECTED_BUNDLE_EXCLUSIONS
            ]

            if missing:
                # "Missing" is the safe direction -- the bundle does strictly
                # less than the source, so nothing unreviewed can be hiding in
                # it. Worth knowing (could indicate a broken build), not worth
                # blocking a merge over, hence the low severity vs. "extra"
                # below, which is the direction that actually matters.
                findings.append({
                    "file": bundle.name, "line": 0, "severity": "low",
                    "category": "bundle-source-drift", "source": "static",
                    "description": (
                        f"{len(missing)} file(s) in {agent_name}/ are missing from the "
                        f"shipped bundle: {', '.join(missing[:5])}"
                        + (f" (+{len(missing) - 5} more)" if len(missing) > 5 else "")
                    ),
                    "snippet": "",
                })

            if extra:
                findings.append({
                    "file": bundle.name, "line": 0, "severity": "critical",
                    "category": "bundle-source-drift", "source": "static",
                    "description": (
                        f"{len(extra)} file(s) in the shipped bundle are NOT present in the "
                        f"committed {agent_name}/ source: {', '.join(extra[:5])}"
                        + (f" (+{len(extra) - 5} more)" if len(extra) > 5 else "")
                        + " -- reviewers never saw these."
                    ),
                    "snippet": "",
                })

            for rel, src_snip, bundle_snip in diffs:
                findings.append({
                    "file": f"{agent_name}/{rel}", "line": 0, "severity": "medium",
                    "category": "bundle-content-diff", "source": "static",
                    "description": (
                        f"Content of {rel} differs between source and shipped bundle "
                        f"beyond line-ending/whitespace normalization. Source starts: "
                        f"{src_snip!r} | Bundle starts: {bundle_snip!r}"
                    ),
                    "snippet": "",
                })

            shutil.rmtree(extract_dir, ignore_errors=True)
        except (zipfile.BadZipFile, OSError) as e:
            findings.append({
                "file": bundle.name, "line": 0, "severity": "high",
                "category": "bundle-unreadable", "source": "static",
                "description": f"Could not extract bundle to verify contents: {e}",
                "snippet": "",
            })
            shutil.rmtree(extract_dir, ignore_errors=True)


def check_marketplace_permissions(rel_path, old_content, new_content, findings):
    """Flag newly added permission/capability-looking keys in plugin/marketplace JSON."""
    if Path(rel_path).name not in {"plugin.json", "marketplace.json"} and not rel_path.endswith(".claude-plugin/marketplace.json"):
        return
    try:
        old_obj = json.loads(old_content) if old_content else {}
        new_obj = json.loads(new_content) if new_content else {}
    except json.JSONDecodeError:
        return

    def flatten_keys(obj, prefix=""):
        keys = set()
        if isinstance(obj, dict):
            for k, v in obj.items():
                path = f"{prefix}.{k}" if prefix else k
                keys.add(path)
                keys |= flatten_keys(v, path)
        elif isinstance(obj, list):
            for item in obj:
                keys |= flatten_keys(item, prefix)
        return keys

    old_keys = flatten_keys(old_obj)
    new_keys = flatten_keys(new_obj)
    added = new_keys - old_keys
    sensitive_terms = ("permission", "scope", "capabilit", "network", "filesystem", "credential", "connector", "url")
    for k in added:
        if any(t in k.lower() for t in sensitive_terms):
            findings.append({
                "file": rel_path, "line": 0, "severity": "medium",
                "category": "permission-change", "source": "static",
                "description": f"new permission/capability-looking field added: '{k}'",
                "snippet": "",
            })


def git_show(ref, path):
    try:
        return subprocess.run(
            ["git", "show", f"{ref}:{path}"], cwd=REPO, capture_output=True, text=True, check=True,
        ).stdout
    except subprocess.CalledProcessError:
        return ""


def main():
    findings = []
    files = changed_files()

    for rel_path in files:
        full = REPO / rel_path
        if BASE_REF and (Path(rel_path).name in {"plugin.json", "marketplace.json"} or rel_path.endswith("marketplace.json")):
            if not full.is_file():
                continue
            try:
                new_content = full.read_text(errors="ignore")
            except OSError:
                continue
            old_content = git_show(BASE_REF, rel_path)
            check_marketplace_permissions(rel_path, old_content, new_content, findings)

    check_bundle_drift(findings)

    findings.sort(key=lambda f: -sev_rank(f["severity"]))
    OUT_PATH.write_text(json.dumps(findings, indent=2))
    print(f"Static scan: {len(findings)} finding(s) written to {OUT_PATH}")


if __name__ == "__main__":
    main()
