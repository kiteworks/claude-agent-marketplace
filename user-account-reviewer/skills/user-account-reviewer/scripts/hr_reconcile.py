"""User Account Reviewer HR reconciliation and proposed changes (#437).

Pure and deterministic: stdlib only, no clock, no network. Input rows come
from the intake agent (intake-rows.v1: email, status, employee_id only); the
HR file is untrusted, so only a normalised status and the matched email ever
reach an output, never free text from it.

Proposed rows are PROPOSALS in the plan.v1 line format: a proposal for a
reviewer, who checks every row before any change.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import sys
import unicodedata
from pathlib import Path
from typing import Any

ACTIVE_WORDS = frozenset({"active", "employed", "current", "yes"})
INACTIVE_WORDS = frozenset({"terminated", "leaver", "left", "inactive", "no", "former"})
# Plan line fields in plan.v1.json schema order.
CSV_COLUMNS = (
    "action",
    "target_id",
    "email",
    "field",
    "old",
    "new",
    "direction",
    "custodian",
    "reason",
)
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
CUSTODIAN_REASON = "custodian required before apply"
# Normalised email must be plain ASCII; anything else is not matched or echoed.
_EMAIL = re.compile(r"[a-z0-9._%+'-]{1,64}@[a-z0-9.-]{1,253}")
# policy_tsv._ID: characters a plan target / new / custodian may carry.
# Output pattern keeps the tenant's own case.
_EMAIL_OUT = re.compile(r"[A-Za-z0-9._%+'-]{1,64}@[A-Za-z0-9.-]{1,253}")
_ID = re.compile(r"[A-Za-z0-9._@+-]+")
_DIGITS = re.compile(r"[0-9]{1,6}")


def normalize_status(value: Any) -> str:
    """active | inactive | unknown. Anything unrecognised is unknown."""
    if not isinstance(value, str):
        return "unknown"
    text = unicodedata.normalize("NFKC", value).strip().casefold()
    if text in ACTIVE_WORDS:
        return "active"
    if text in INACTIVE_WORDS:
        return "inactive"
    return "unknown"


def normalize_email(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    text = unicodedata.normalize("NFKC", value).strip()
    if not text.isascii():  # before casefold: no sharp-s to ss collisions
        return ""
    text = text.casefold()
    return text if _EMAIL.fullmatch(text) else ""


def _entry(user: dict[str, Any], **extra: str) -> dict[str, Any]:
    return {"id": str(user.get("id", "")), "email": str(user.get("email", "")), **extra}


def reconcile(
    users: list[dict[str, Any]], hr_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    """Categorise tenant users against HR rows (exact normalised email match)."""
    hr_by_email: dict[str, str] = {}
    duplicates = 0
    hr_invalid = 0
    for item in hr_rows:
        email = normalize_email(item.get("email") if isinstance(item, dict) else None)
        if not email:
            hr_invalid += 1
            continue
        if email in hr_by_email:
            duplicates += 1
            continue
        hr_by_email[email] = normalize_status(item.get("status"))

    matched: list[dict[str, Any]] = []
    mismatched: list[dict[str, Any]] = []
    orphaned: list[dict[str, Any]] = []
    unknown: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []
    external_not_in_hr = 0
    tenant_invalid = 0
    seen: set[str] = set()
    holders: dict[str, int] = {}
    for user in users:
        key = normalize_email(user.get("email"))
        if key:
            holders[key] = holders.get(key, 0) + 1
    for user in users:
        email = normalize_email(user.get("email"))
        if not email:
            tenant_invalid += 1
            continue
        if holders[email] > 1:
            seen.add(email)
            ambiguous.append({"id": str(user.get("id", ""))})
            continue
        blocked = bool(user.get("suspended") or user.get("deactivated"))
        status = hr_by_email.get(email)
        if status is None:
            if user.get("deactivated"):
                continue
            if user.get("external") is True:
                external_not_in_hr += 1
            else:
                orphaned.append(_entry(user))
            continue
        seen.add(email)
        if status == "unknown":
            unknown.append(_entry(user))
        elif status == "active" and not blocked:
            matched.append(_entry(user))
        elif status == "inactive" and blocked:
            matched.append(_entry(user))
        elif status == "inactive":
            mismatched.append(_entry(user, kind="hr_inactive_tenant_active"))
        else:
            mismatched.append(_entry(user, kind="hr_active_tenant_blocked"))
    missing = [
        {"id": "", "email": email}
        for email, status in hr_by_email.items()
        if status == "active" and email not in seen
    ]
    # Unknown HR status with no tenant account is reported by email too.
    unknown += [
        {"id": "", "email": email}
        for email, status in hr_by_email.items()
        if status == "unknown" and email not in seen
    ]
    counts = {
        "matched": len(matched),
        "orphaned": len(orphaned),
        "missing": len(missing),
        "mismatched": len(mismatched),
        "unknown_status": len(unknown),
        "ambiguous": len(ambiguous),
        "hr_invalid": hr_invalid,
        "tenant_email_invalid": tenant_invalid,
        "hr_duplicates": duplicates,
        "external_not_in_hr": external_not_in_hr,
        "hr_rows": len(hr_by_email),
    }
    return {
        "matched": matched,
        "orphaned": orphaned,
        "missing": missing,
        "mismatched": mismatched,
        "unknown_status": unknown,
        "ambiguous": ambiguous,
        "counts": counts,
    }


def _plan_safe(row: dict[str, str]) -> bool:
    """id, email and new must be plan-safe and never start a spreadsheet formula."""
    for col in ("target_id", "new"):
        if not _ID.fullmatch(row[col]):
            return False
    if not _EMAIL_OUT.fullmatch(row["email"]):
        return False
    return not any(row[c].startswith(_FORMULA_PREFIXES) for c in CSV_COLUMNS)


def _row(action: str, target: str, email: str, field: str, old: str, new: str) -> dict:
    return {
        "action": action,
        "target_id": target,
        "email": email,
        "field": field,
        "old": old,
        "new": new,
        "direction": "none",
        "custodian": "",
        "reason": "",
    }


def propose_changes(
    findings: dict[str, Any],
    reconciliation: dict[str, Any],
    tier_order: list[str] | None,
    dormant_days: int | None = None,
    stats: dict[str, int] | None = None,
) -> list[dict[str, str]]:
    """Proposal rows, at most one per account: suspend > deactivate > change_profile.

    Accounts sharing an email (reconciliation "ambiguous") get no row. A row
    whose id, email or new value is not plan-safe is skipped and counted in
    ``stats["rejected"]``.
    """
    stats = stats if stats is not None else {}
    stats.setdefault("rejected", 0)
    skip = {e.get("id") for e in reconciliation.get("ambiguous", [])}
    admins = {
        i.get("user_id")
        for i in findings.get("findings", [])
        if i.get("type") == "admin_role"
    }
    chosen: dict[str, tuple[int, dict[str, str]]] = {}

    def offer(priority: int, row: dict[str, str]) -> None:
        if row["target_id"] in skip:
            return
        if not _plan_safe(row):
            stats["rejected"] += 1
            return
        if priority < 2 and row["target_id"] in admins:
            row["reason"] += " (admin role)"
        current = chosen.get(row["target_id"])
        if current is None or priority < current[0]:
            chosen[row["target_id"]] = (priority, row)

    for entry in reconciliation.get("mismatched", []):
        if entry.get("kind") == "hr_inactive_tenant_active" and entry.get("id"):
            row = _row(
                "update_user", entry["id"], entry["email"], "suspended", "false", "true"
            )
            row["reason"] = "HR status inactive, tenant account active"
            offer(0, row)

    ranks = {pid: i for i, pid in enumerate(tier_order or [])}
    for item in findings.get("findings", []):
        uid = item.get("user_id") or ""
        if not uid:
            continue
        email = item.get("email", "")
        if item.get("type") == "dormant":
            row = _row("update_user", uid, email, "deactivated", "false", "true")
            days = str(item.get("detail", "")).strip()
            if not _DIGITS.fullmatch(days):
                stats["rejected"] += 1
                continue
            suffix = f" (threshold {dormant_days})" if dormant_days is not None else ""
            row["reason"] = f"dormant {days} days{suffix}"
            offer(1, row)
        elif item.get("type") == "licence_waste":
            detail = str(item.get("detail", ""))
            old = detail.removeprefix("profile=")
            rank = ranks.get(old)
            if rank is None or rank < 1:
                continue
            row = _row(
                "assign_user_profile",
                uid,
                email,
                "profileId",
                old,
                tier_order[rank - 1],  # type: ignore[index]
            )
            row["direction"] = "demote"
            row["reason"] = CUSTODIAN_REASON
            offer(2, row)
    return [
        row
        for _, row in sorted(chosen.values(), key=lambda p: (p[0], p[1]["target_id"]))
    ]


EXPORT_ACTIONS = frozenset({"update_user", "assign_user_profile"})


def validate_proposed_csv(path: str | Path) -> str | None:
    """None when the file is a plan-safe proposed-changes.csv, else the reason."""
    try:
        with Path(path).open(encoding="utf-8", newline="") as handle:
            table = list(csv.reader(handle))
    except (OSError, UnicodeDecodeError, csv.Error):
        return "unreadable file"
    if not table or tuple(table[0]) != CSV_COLUMNS:
        return "header is not the proposed-changes columns"
    for cells in table[1:]:
        if len(cells) != len(CSV_COLUMNS):
            return "row with the wrong number of cells"
        if cells[0] not in EXPORT_ACTIONS:
            return "action is not allowed"
        if any(c.startswith(_FORMULA_PREFIXES) for c in cells):
            return "cell starts a spreadsheet formula"
    return None


def write_proposed_changes_csv(rows: list[dict[str, str]], path: str | Path) -> int:
    """Write proposed-changes.csv (plan.v1 line fields in schema order).

    A row with any cell starting a spreadsheet formula (= + - @, TAB, CR) is
    not written; the count of written rows is returned.
    """
    written = 0
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(CSV_COLUMNS)
        for row in rows:
            cells = [str(row.get(col, "") or "") for col in CSV_COLUMNS]
            if any(c.startswith(_FORMULA_PREFIXES) for c in cells):
                continue
            writer.writerow(cells)
            written += 1
    return written


def _load_json(path: str) -> Any:
    if path == "-":  # quoted heredoc body: never raw JSON in an argument
        return json.loads(sys.stdin.read())
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    rec = sub.add_parser("reconcile")
    rec.add_argument("--roster", required=True, help="roster JSONL (access_review)")
    rec.add_argument(
        "--hr-rows", required=True, help="intake-rows.v1 JSON file, or - for stdin"
    )
    rec.add_argument("--out", required=True)
    prop = sub.add_parser("propose")
    prop.add_argument("--result", required=True, help="access_review review output")
    prop.add_argument("--reconciliation", required=True)
    prop.add_argument("--tier-order")
    prop.add_argument("--out", required=True)
    exp = sub.add_parser("export")
    exp.add_argument("--in", dest="src", required=True, help="proposed-changes.csv")
    exp.add_argument("--out", required=True)
    exp.add_argument(
        "--approved",
        action="store_true",
        help="people-data approval given; the file names accounts",
    )
    args = parser.parse_args(argv)

    if args.cmd == "export":
        if not args.approved:
            print("refused: proposed-changes.csv needs --approved", file=sys.stderr)
            return 2
        problem = validate_proposed_csv(args.src)
        if problem:
            print(f"refused: {problem}", file=sys.stderr)
            return 2
        shutil.copyfile(args.src, args.out)
        return 0
    if args.cmd == "reconcile":
        users = [
            json.loads(line)
            for line in Path(args.roster).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        hr_doc = _load_json(args.hr_rows)
        result = reconcile(users, hr_doc.get("rows", []))
        skipped = hr_doc.get("skipped")
        result["counts"]["intake_skipped"] = (
            skipped if isinstance(skipped, int) and skipped >= 0 else 0
        )
        Path(args.out).write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(json.dumps(result["counts"], sort_keys=True))
        return 0
    findings = _load_json(args.result)
    tiers = _load_json(args.tier_order) if args.tier_order else None
    days = (findings.get("summary") or {}).get("dormant_days")
    stats: dict[str, int] = {}
    rows = propose_changes(
        findings, _load_json(args.reconciliation), tiers, days, stats
    )
    written = write_proposed_changes_csv(rows, args.out)
    rejected = stats["rejected"] + len(rows) - written
    invalid = (_load_json(args.reconciliation).get("counts") or {}).get(
        "tenant_email_invalid", 0
    )
    print(
        f"{written} rows, {rejected} rejected, "
        f"{invalid} tenant accounts skipped (invalid email)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
