"""User Account Reviewer findings engine: compact roster to review findings.

Pure and deterministic: stdlib only, no clock (the reference date is always a
parameter), no network. Roster contract v1 (one JSON object per line):

    id, email, external, profile_id, last_accessed, created, locked,
    unverified, password_reset, suspended, deactivated, admin_role,
    active_sessions, devices

Display names are deliberately not part of the roster (untrusted, not needed).
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import ipaddress
import json
import re
import sys
from collections import Counter
from collections.abc import Iterator
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

_SKILLS_DIR = Path(__file__).resolve().parents[2]
REVIEWER_TOOLS = frozenset(
    {
        "get_user_info_whoami",
        "search_users",
        "get_user_metadata",
        "find_user_by_email",
        "list_user_profiles",
        "get_profile",
        "list_profile_users",
        "get_profile_eligibility",
    }
)
MAX_ENRICH = 25
_ROW_LIST_KEYS = ("data", "users", "items", "results", "rows")

NEVER_SIGNED_IN_GRACE_DAYS = 14
DEFAULT_DORMANT_DAYS = 90
FINDING_TYPES = (
    "dormant",
    "never_signed_in",
    "locked",
    "unverified",
    "password_reset_pending",
    "suspended_with_sessions",
    "external",
    "admin_role",
    "licence_waste",
)
CSV_COLUMNS = (
    "email",
    "user_id",
    "profile_id",
    "external",
    "last_accessed",
    "finding_types",
    "detail",
)
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
# EU2 (#497): search_users returns `lastAccessed` empty for every account, the
# signed-in admin included, and get_user_metadata has no last-access field. A
# roster in which no account carries a last access says nothing about sign-ins:
# the rules that need it are not determinable, never zero.
LAST_ACCESS_UNREADABLE = (
    "last sign-in not readable: dormant, never signed in and licence waste "
    "not determinable"
)
NOT_DETERMINABLE = "not determinable"


def _first(raw: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in raw and raw[key] is not None:
            return raw[key]
    return None


def _flag(raw: dict[str, Any], keys: tuple[str, ...]) -> bool:
    return _first(raw, keys) is True


def _opt_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _opt_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, list):
        return len(value)
    return None


def normalize_user(raw: dict[str, Any]) -> dict[str, Any]:
    """Map one raw connector user to roster contract v1.

    The ONLY place that knows source field names. Assumed keys (unverified
    until probe P2; every miss degrades to None/False, never raises):
      id             <- id | userId
      email          <- email
      external       <- external | isExternal (bool), else None
      profile_id     <- profileId | profile_id | profile.id
      last_accessed  <- lastAccessed | last_accessed | lastAccess
      created        <- created | createdAt
      locked         <- locked
      unverified     <- unverified, or verified == false
      password_reset <- passwordResetNeeded | password_reset
      suspended      <- suspended
      deactivated    <- deactivated, or active/enabled == false
      admin_role     <- admin_role | isAdmin (bool), else None (unreadable)
      active_sessions<- activeSessions (int or list), else None
      devices        <- devices | deviceInstalls (int or list), else None
    """
    profile = raw.get("profile")
    profile_id = _first(raw, ("profileId", "profile_id"))
    if profile_id is None and isinstance(profile, dict):
        profile_id = profile.get("id")
    uid = _first(raw, ("id", "userId"))
    email = _first(raw, ("email",))
    verified = raw.get("verified")
    active = _first(raw, ("active", "enabled"))
    return {
        "id": "" if uid is None else str(uid),
        "email": "" if email is None else str(email),
        "external": _opt_bool(_first(raw, ("external", "isExternal"))),
        "profile_id": None if profile_id is None else str(profile_id),
        "last_accessed": _first(raw, ("lastAccessed", "last_accessed", "lastAccess")),
        "created": _first(raw, ("created", "createdAt")),
        "locked": _flag(raw, ("locked",)),
        "unverified": _flag(raw, ("unverified",)) or verified is False,
        "password_reset": _flag(raw, ("passwordResetNeeded", "password_reset")),
        "suspended": _flag(raw, ("suspended",)),
        "deactivated": _flag(raw, ("deactivated",)) or active is False,
        "admin_role": _opt_bool(_first(raw, ("admin_role", "isAdmin"))),
        "active_sessions": _opt_int(_first(raw, ("activeSessions", "active_sessions"))),
        "devices": _opt_int(_first(raw, ("devices", "deviceInstalls"))),
    }


def _to_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None


def _finding(kind: str, user: dict[str, Any], detail: str = "") -> dict[str, str]:
    return {
        "type": kind,
        "user_id": user["id"],
        "email": user["email"],
        "detail": detail,
    }


def find_issues(
    users: list[dict[str, Any]],
    *,
    reference_date: date,
    dormant_days: int = DEFAULT_DORMANT_DAYS,
    period_start: date | None = None,
    tier_order: list[str] | None = None,
) -> dict[str, Any]:
    """Return {"findings": [...], "summary": {...}} for normalized users."""
    reference_date = _to_date(reference_date) or reference_date
    cutoff = period_start or None
    period = _to_date(cutoff) if cutoff else None
    if period is None:
        # No explicit review period: use the dormancy window as the period.
        period = reference_date - timedelta(days=dormant_days)
    ranks = {pid: i for i, pid in enumerate(tier_order)} if tier_order else {}
    findings: list[dict[str, str]] = []
    admin_readable = any(u.get("admin_role") is not None for u in users)
    last_readable = any(_to_date(u.get("last_accessed")) is not None for u in users)

    for user in users:
        last = _to_date(user.get("last_accessed"))
        created = _to_date(user.get("created"))
        if not user.get("deactivated") and last is not None:
            days = (reference_date - last).days
            if days > dormant_days:
                findings.append(_finding("dormant", user, str(days)))
        if last_readable and last is None and created is not None:
            age = (reference_date - created).days
            if age > NEVER_SIGNED_IN_GRACE_DAYS:
                findings.append(_finding("never_signed_in", user, str(age)))
        if user.get("locked"):
            findings.append(_finding("locked", user))
        if user.get("unverified"):
            findings.append(_finding("unverified", user))
        if user.get("password_reset"):
            findings.append(_finding("password_reset_pending", user))
        if user.get("suspended"):
            sessions = user.get("active_sessions") or 0
            devices = user.get("devices") or 0
            if sessions > 0 or devices > 0:
                findings.append(
                    _finding(
                        "suspended_with_sessions",
                        user,
                        f"sessions={sessions}; devices={devices}",
                    )
                )
        if user.get("external") is True:
            findings.append(
                _finding("external", user, str(user.get("last_accessed") or ""))
            )
        if user.get("admin_role") is True:
            findings.append(_finding("admin_role", user))
        rank = ranks.get(user.get("profile_id") or "")
        waste = last_readable and (last is None or last < period)
        if rank is not None and rank > 0 and waste:
            findings.append(
                _finding("licence_waste", user, f"profile={user['profile_id']}")
            )

    limitations: list[str] = []
    not_determinable: set[str] = set()
    if not admin_readable:
        limitations.append("admin roles not readable")
        not_determinable.add("admin_role")
    if not tier_order:
        limitations.append("profile tier order unknown")
        not_determinable.add("licence_waste")
    if users and not last_readable:
        limitations.append(LAST_ACCESS_UNREADABLE)
        not_determinable |= {"dormant", "never_signed_in", "licence_waste"}
    counts = Counter(f["type"] for f in findings)
    summary = {
        "reference_date": reference_date.isoformat(),
        "dormant_days": dormant_days,
        "period_start": period.isoformat(),
        "total_users": len(users),
        "finding_counts": {k: counts.get(k, 0) for k in FINDING_TYPES},
        "profile_distribution": dict(
            sorted(Counter(u.get("profile_id") or "unknown" for u in users).items())
        ),
        "internal": sum(1 for u in users if u.get("external") is False),
        "external": sum(1 for u in users if u.get("external") is True),
        "external_unknown": sum(1 for u in users if u.get("external") is None),
        "not_determinable": [k for k in FINDING_TYPES if k in not_determinable],
        "limitations": limitations,
    }
    return {"findings": findings, "summary": summary}


def _safe_cell(value: Any) -> str:
    text = "" if value is None else str(value)
    if text.startswith(_FORMULA_PREFIXES):
        return "'" + text
    return text


PEOPLE_COLUMNS = ("email", "user_id")
AGGREGATE_COLUMNS = ("profile_id", "external", "finding_types", "accounts")
MIN_GROUP = 3


def write_access_review_csv(
    result: dict[str, Any],
    path: str | Path,
    users: list[dict[str, Any]] | None = None,
    *,
    include_people: bool = False,
) -> int:
    """Write the access-review CSV; return the row count.

    Without ``include_people`` (the people-data approval) the person-identifying
    columns (``email``, ``user_id``) are not written: rows are grouped by
    profile, external flag and finding types with an account count; groups
    of fewer than three accounts are folded into one ``other`` row. With it,
    one row per account with findings.

    `users` (normalized roster) supplies profile/external/last access; when
    omitted those columns come from the result's `users` key if present.
    """
    roster = users if users is not None else result.get("users", [])
    by_id = {u["id"]: u for u in roster}
    grouped: dict[str, list[dict[str, str]]] = {}
    for item in result["findings"]:
        grouped.setdefault(item["user_id"], []).append(item)
    rows = 0
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        if not include_people:
            writer.writerow(AGGREGATE_COLUMNS)
            tally: Counter[tuple[str, str, str]] = Counter()
            for uid, items in grouped.items():
                user = by_id.get(uid, {})
                key = (
                    _safe_cell(user.get("profile_id")),
                    _safe_cell(user.get("external")),
                    _safe_cell(";".join(sorted({i["type"] for i in items}))),
                )
                tally[key] += 1
            small = sum(n for n in tally.values() if n < MIN_GROUP)
            for key in sorted(tally):
                if tally[key] >= MIN_GROUP:
                    writer.writerow([*key, tally[key]])
                    rows += 1
            if small:
                writer.writerow(["other", "other", "other", small])
                rows += 1
            return rows
        writer.writerow(CSV_COLUMNS)
        for uid, items in grouped.items():
            user = by_id.get(uid, {})
            writer.writerow(
                [
                    _safe_cell(items[0]["email"]),
                    _safe_cell(uid),
                    _safe_cell(user.get("profile_id")),
                    _safe_cell(user.get("external")),
                    _safe_cell(user.get("last_accessed")),
                    _safe_cell(";".join(i["type"] for i in items)),
                    _safe_cell(
                        ";".join(
                            f"{i['type']}={i['detail']}" if i["detail"] else i["type"]
                            for i in items
                        )
                    ),
                ]
            )
            rows += 1
    return rows


def _read_roster(path: Path) -> list[dict[str, Any]]:
    users = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            users.append(json.loads(line))
    return users


def _sibling(skill: str, module: str, script: str):
    """Load a sibling skill's script by path (the plugin is self-contained)."""
    path = _SKILLS_DIR / skill / "scripts" / script
    spec = importlib.util.spec_from_file_location(module, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def extract_raw_users(payload: Any) -> list[dict[str, Any]]:
    """Users of one saved search_users answer (a list or a wrapper object)."""
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for key in _ROW_LIST_KEYS:
            if isinstance(payload.get(key), list):
                return extract_raw_users(payload[key])
        for value in payload.values():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                return extract_raw_users(value)
    return []


def _strings(value: Any, depth: int = 0) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif depth < 4 and isinstance(value, dict):
        for item in value.values():
            yield from _strings(item, depth + 1)
    elif depth < 4 and isinstance(value, list):
        for item in value:
            yield from _strings(item, depth + 1)


def user_looks_injected(raw: dict[str, Any]) -> bool:
    """data-fence heuristic over every string of a raw user (before it is dropped)."""
    looks = _sibling("data-fence", "_kw_fence", "fence.py").looks_like_instruction
    return any(looks(t, REVIEWER_TOOLS) for t in _strings(raw))


def _counter_path(out: Path) -> Path:
    return out.with_name(out.name + ".injection")


def _read_int(path: Path) -> int:
    try:
        return int(path.read_text(encoding="utf-8").strip() or 0)
    except (OSError, ValueError):
        return 0


def _enriched_path(out: Path) -> Path:
    return out.with_name(out.name + ".enriched")


def _read_enriched(out: Path) -> set[str]:
    try:
        return {str(x) for x in json.loads(_enriched_path(out).read_text("utf-8"))}
    except (OSError, ValueError, TypeError):
        return set()


def _read_counter(out: Path) -> int:
    return _read_int(_counter_path(out))


def _bump_counter(out: Path, suspected: int) -> int:
    total = _read_counter(out) + suspected
    _counter_path(out).write_text(f"{total}\n", encoding="utf-8")
    return total


def normalize_append(payload: Any, out: str | Path) -> dict[str, int]:
    """Append compact users (roster contract v1) for one saved answer to ``out``.

    Display names and every other field outside the contract are dropped
    before anything is written. A user id already in the file is skipped.
    """
    out_path = Path(out)
    known: set[str] = set()
    if out_path.exists():
        known = {r["id"] for r in _read_roster(out_path)}
    elif _counter_path(out_path).exists() or _enriched_path(out_path).exists():
        raise SystemExit(
            f"error: {out_path.name} is new but its counter files exist; "
            "use a fresh scratch directory"
        )
    raw_users = extract_raw_users(payload)
    kept: list[dict[str, Any]] = []
    suspected = 0
    for raw in raw_users:
        user = normalize_user(raw)
        if not user["id"] or user["id"] in known:
            continue
        suspected += user_looks_injected(raw)
        known.add(user["id"])
        kept.append(user)
    with open(out_path, "a", encoding="utf-8", newline="\n") as fh:
        for user in kept:
            fh.write(json.dumps(user, separators=(",", ":")) + "\n")
    total = _bump_counter(out_path, suspected)
    return {
        "read": len(raw_users),
        "appended": len(kept),
        "roster_total": len(known),
        "injection_suspected_count": total,
    }


def enrich_user(roster: str | Path, user_id: str, payload: Any) -> dict[str, Any]:
    """Merge one saved get_user_metadata answer into that user's roster line.

    Only sessions, devices, profile and the status flags may change; a field
    the answer does not carry keeps its roster value.
    """
    path = Path(roster)
    users = _read_roster(path)
    raw = payload if isinstance(payload, dict) else {}
    if isinstance(raw.get("data"), dict):
        raw = raw["data"]
    ids = _read_enriched(path)
    if user_id not in ids and len(ids) >= MAX_ENRICH:
        raise SystemExit(f"error: enrichment cap of {MAX_ENRICH} accounts reached")
    found = False
    for user in users:
        if user["id"] != user_id:
            continue
        found = True
        fresh = normalize_user({**raw, "id": user_id})
        for key in ("active_sessions", "devices", "profile_id"):
            if fresh[key] is not None:
                user[key] = fresh[key]
        for key in ("suspended", "locked", "unverified", "deactivated"):
            user[key] = bool(user[key] or fresh[key])
    if found:
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            for user in users:
                fh.write(json.dumps(user, separators=(",", ":")) + "\n")
    suspected = int(user_looks_injected(raw))
    if found:
        ids.add(user_id)
        _enriched_path(path).write_text(
            json.dumps(sorted(ids)) + "\n", encoding="utf-8"
        )
    return {
        "enriched": int(found),
        "enriched_total": len(ids),
        "injection_suspected_count": _bump_counter(path, suspected),
    }


def counts_view(
    result: dict[str, Any],
    reconciliation: dict[str, Any] | None = None,
    injection_suspected_count: int = 0,
    proposed_rows: int | None = None,
    enriched_accounts: int | None = None,
) -> dict[str, Any]:
    """The figures the reviewer copies into its return object (never counted by hand)."""
    summary = result.get("summary", {})
    # A finding type the data cannot decide is left out of the counts, never 0.
    unknown = set(summary.get("not_determinable") or [])
    counts: dict[str, int] = {
        k: v
        for k, v in (summary.get("finding_counts") or {}).items()
        if k not in unknown
    }
    for key in ("total_users", "internal", "external", "external_unknown"):
        counts[key] = int(summary.get(key, 0))
    if reconciliation:
        counts.update(
            {k: int(v) for k, v in (reconciliation.get("counts") or {}).items()}
        )
    if proposed_rows is not None:
        counts["proposed_rows"] = proposed_rows
    counts["flagged_accounts"] = len(
        {i["user_id"] for i in result.get("findings", []) if i.get("user_id")}
    )
    if enriched_accounts is not None:
        counts["enriched_accounts"] = enriched_accounts
    return {
        "reference_date": summary.get("reference_date"),
        "dormant_days": summary.get("dormant_days"),
        "counts": counts,
        "not_determinable": [k for k in FINDING_TYPES if k in unknown],
        "profile_distribution": summary.get("profile_distribution", {}),
        "limitations": list(summary.get("limitations", [])),
        "injection_suspected_count": injection_suspected_count,
    }


# --- report record (#439): the kw-pdf-report assessment for profile access-review ---

FENCE_MAX = 78
PROPOSAL_ONLY = (
    "Proposal only: a reviewer checks every row before any change, "
    "and nothing in your tenant changes"
)
ATTESTATION_STATEMENT = (
    "I reviewed the accounts listed in this report on the date above."
)
BLANK_FIELD = "_" * 32
REVIEW_STATUS = (
    "Automated assessment \u00b7 not reviewed by a person \u00b7 "
    "findings need owner validation"
)
COMPLIANCE_COLUMNS = (
    "framework",
    "control",
    "title",
    "observes",
    "cannot_show",
    "source",
    "verified",
)
_IPV4 = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
_IPV6_CANDIDATE = re.compile(
    r"(?<![0-9A-Za-z:])[0-9A-Fa-f:]*:[0-9A-Fa-f:]*(?![0-9A-Za-z:])"
)


def _ipv6_sub(match: re.Match[str]) -> str:
    """Replace a valid IPv6 literal; leave ``a::b`` style words and times alone."""
    text = match.group(0)
    try:
        ipaddress.IPv6Address(text)
    except ValueError:
        return text
    groups = text.split(":")
    if (
        text.count(":") >= 3
        or text.startswith("::")
        or any(len(g) == 4 for g in groups)
    ):
        return "[ip removed]"
    return text


_EMAIL_ANY = re.compile(r"[A-Za-z0-9._%+'-]+@[A-Za-z0-9.-]+")
FINDING_TEXT = {
    "dormant": "accounts not accessed within the dormancy threshold",
    "never_signed_in": "accounts that never signed in after the grace period",
    "locked": "locked accounts",
    "unverified": "accounts whose email is not verified",
    "password_reset_pending": "accounts with a pending password reset",
    "suspended_with_sessions": "suspended accounts that still hold sessions or devices",
    "external": "external accounts",
    "admin_role": "accounts with an admin role",
    "licence_waste": "accounts on a higher profile tier than their use suggests",
}
RECONCILE_TEXT = {
    "orphaned": "tenant accounts with no row in the HR list",
    "missing": "active HR rows with no tenant account",
    "mismatched": "accounts whose tenant state disagrees with the HR status",
    "unknown_status": "HR rows whose status is not recognised",
}


def _scrub(value: Any) -> Any:
    """Defence in depth: no IP literal and no email address survives in a report string."""
    if isinstance(value, str):
        value = _IPV6_CANDIDATE.sub(_ipv6_sub, _IPV4.sub("[ip removed]", value))
        return _EMAIL_ANY.sub("[email removed]", value)
    if isinstance(value, list):
        return [_scrub(v) for v in value]
    if isinstance(value, dict):
        return {k: _scrub(v) for k, v in value.items()}
    return value


def load_compliance_observations(path: str | Path) -> list[dict[str, str]]:
    """Rows of the compliance-observations.md table, one dict per control."""
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != len(COMPLIANCE_COLUMNS) or set(cells[0]) <= set("-: "):
            continue
        if cells[0].lower() == "framework":
            continue
        row = dict(zip(COMPLIANCE_COLUMNS, cells))
        row["source"] = " ".join(u.strip("<>") for u in row["source"].split())
        out.append(row)
    return out


def _n(value: Any) -> str:
    return "not available" if value is None else f"{int(value):,}"


def report_record(
    result: dict[str, Any],
    reconcile: dict[str, Any] | None,
    proposed: list[dict[str, Any]] | None,
    meta: dict[str, Any],
) -> dict[str, Any]:
    """Pure: reviewer outputs -> kw-pdf-report spec for profile ``access-review``.

    Reads only counts and ids; never an email, a display name, an IP address or
    a location. ``result`` is the ``review`` output, ``reconcile`` the
    reconciliation (or None), ``proposed`` the proposed-changes rows (or None;
    only counted). meta: operator, run_id, assessed_at, generated_at,
    roster_source, hr_file_label, people_data_approved (default false), tier_order_source, enriched_accounts,
    limitations, unvisited_scope, compliance (rows of
    ``load_compliance_observations``).
    """
    fence = _sibling("data-fence", "_kw_fence", "fence.py").fence
    summary = result.get("summary") or {}
    ref = summary.get("reference_date") or "unknown"
    dormant = summary.get("dormant_days")
    fcounts = summary.get("finding_counts") or {}
    total = int(summary.get("total_users") or 0)
    internal = int(summary.get("internal") or 0)
    external = int(summary.get("external") or 0)
    unknown_ext = int(summary.get("external_unknown") or 0)
    unknown_kinds = set(summary.get("not_determinable") or [])
    side_known = not (total and unknown_ext == total)
    flagged = len(
        {i.get("user_id") for i in result.get("findings", []) if i.get("user_id")}
    )
    dist = summary.get("profile_distribution") or {}
    rcounts = (reconcile or {}).get("counts") or {}
    prop_rows = len(proposed) if proposed is not None else 0
    tier_src = {
        "probe": "profile tier order read from the connector",
        "user_confirmed": "tier order confirmed by the user",
    }.get(str(meta.get("tier_order_source")), "tier order unknown")
    enriched = meta.get("enriched_accounts")
    approved = meta.get("people_data_approved") is True
    generated = meta.get("generated_at") or meta.get("assessed_at")
    compliance = meta.get("compliance") or []

    inventory: list[dict[str, Any]] = [
        {
            "id": "ALL",
            "name": "All accounts in the roster",
            "type": "roster",
            "checks": [{"id": "counts", "status": "checked", "method": "Engine count"}],
            "facts": {
                "accounts": total,
                "internal": internal if side_known else NOT_DETERMINABLE,
                "external": external if side_known else NOT_DETERMINABLE,
                "flagged accounts": flagged,
            },
        }
    ]
    findings: list[dict[str, Any]] = []

    def add(ident: str, label: str, kind: str, count: int, text: str) -> None:
        inventory.append(
            {
                "id": ident,
                "name": label,
                "type": kind,
                "checks": [
                    {"id": "counts", "status": "checked", "method": "Engine count"}
                ],
                "facts": {"accounts": count},
            }
        )
        findings.append(
            {
                "id": "F-" + ident,
                "title": f"Review candidates: {label.lower()}",
                "observation": f"{count} {text}.",
                "impact": "A review candidate; the cause and the right outcome are not established.",
                "confidence": "Rule-based observation",
                "priority": "info",
                "priority_reason": "Review candidate only; no decision has been made.",
                "recommendation": (
                    "Check each account in the CSV against what you know about the "
                    "person and the business need before any change."
                ),
                "object_ids": [ident],
                "check_ids": ["counts"],
            }
        )

    for kind in FINDING_TYPES:
        count = int(fcounts.get(kind) or 0)
        if count and kind not in unknown_kinds:
            label = kind.replace("_", " ").capitalize()
            add("T-" + kind, label, "finding type", count, FINDING_TEXT[kind])
    for kind, text in RECONCILE_TEXT.items():
        count = int(rcounts.get(kind) or 0)
        if count:
            label = kind.replace("_", " ").capitalize()
            add("R-" + kind, label, "reconciliation", count, text)

    dist_text = (
        "; ".join(
            f"{fence(str(k), FENCE_MAX)} {_n(v)}" for k, v in sorted(dist.items())
        )
        or "none"
    )
    by_type = "; ".join(
        f"{k.replace('_', ' ')} "
        + (NOT_DETERMINABLE if k in unknown_kinds else _n(fcounts.get(k)))
        for k in FINDING_TYPES
    )
    if reconcile:
        recon_text = (
            f"matched {_n(rcounts.get('matched'))}; orphaned {_n(rcounts.get('orphaned'))}; "
            f"missing {_n(rcounts.get('missing'))}; mismatched {_n(rcounts.get('mismatched'))}; "
            f"unknown HR status {_n(rcounts.get('unknown_status'))}; ambiguous "
            f"{_n(rcounts.get('ambiguous'))}; external not in HR "
            f"{_n(rcounts.get('external_not_in_hr'))}. Match basis: email, case-insensitive."
        )
    else:
        recon_text = "No HR list was supplied, so no reconciliation was run."
    hr_label = (
        fence(str(meta.get("hr_file_label")), FENCE_MAX)
        if meta.get("hr_file_label")
        else ""
    )
    method = (
        f"Roster source: {meta.get('roster_source') or 'Kiteworks connector user search'}. "
        f"Reference date {ref}; dormancy threshold {_n(dormant)} days; {tier_src}; "
        f"enrichment cap {MAX_ENRICH} accounts"
        + (f", {_n(enriched)} enriched" if enriched is not None else "")
        + (f"; HR list file {hr_label}" if hr_label else "")
        + ". Findings are review candidates, not decisions."
    )
    if compliance:
        rows_text = "; ".join(
            f"{r['framework']} {r['control']} ({r['title']}): observes "
            f"{r['observes']}. Cannot show {r['cannot_show']}. "
            f"verified: {r.get('verified', 'false')}"
            for r in compliance
        )
        compliance_text = (
            rows_text + ". These are observations about what this report can show, not "
            "statements about any control; the control wording is still to be "
            "verified by a person."
        )
    else:
        compliance_text = "No compliance observation table was supplied."
    details = {
        "Reference date and threshold": f"{ref}; dormant after {_n(dormant)} days",
        "Roster summary": (
            f"accounts {_n(total)}; "
            + (
                f"internal {_n(internal)}; external {_n(external)}; "
                if side_known
                else f"internal and external {NOT_DETERMINABLE}; "
            )
            + f"external unknown {_n(unknown_ext)}; profile distribution {dist_text}"
        ),
        "Findings by type": f"{by_type}; flagged accounts {_n(flagged)}",
        "Reconciliation": recon_text,
        "Proposed changes": (
            f"{_n(prop_rows)} proposed change(s) in proposed-changes.csv. {PROPOSAL_ONLY}."
            if approved
            else f"proposed-changes.csv not saved: needs people-data approval "
            f"({_n(prop_rows)} change(s) proposed). {PROPOSAL_ONLY}."
        ),
        "Method and limits": method,
        "Compliance observations": compliance_text,
        "Attestation: reviewer name": BLANK_FIELD,
        "Attestation: role": BLANK_FIELD,
        "Attestation: date": BLANK_FIELD,
        "Attestation: signature": BLANK_FIELD,
        "Attestation: statement": ATTESTATION_STATEMENT,
    }
    limitations = [
        "Findings are review candidates, not decisions.",
        "Only accounts and fields the connector returned were reviewed; display names are not part of this report.",
        "IP addresses and locations are never written to this report.",
        "The attestation page is for a human reviewer to complete; this agent never fills it.",
    ]
    limitations += [str(x) for x in summary.get("limitations") or []]
    limitations += [str(x) for x in meta.get("limitations") or []]
    unvisited = [str(x) for x in meta.get("unvisited_scope") or []]
    actions: list[dict[str, Any]] = []
    if prop_rows:
        actions.append(
            {
                "id": "A-proposed-changes",
                "action": (
                    f"Review {prop_rows} proposed change(s); make approved changes "
                    "in the Kiteworks admin console"
                ),
                "status": "proposed",
                "basis": PROPOSAL_ONLY,
                "target": "proposed-changes.csv" if approved else "none",
            }
        )
    conclusion = (
        f"{_n(total)} accounts were reviewed as of {ref}; {_n(flagged)} have at least "
        "one review candidate finding. Findings are review candidates, not decisions."
    )
    record = {
        "agent_name": "User Account Reviewer",
        "report_title": "User access review",
        "scan_date": str(meta.get("assessed_at") or generated)[:10],
        "scope_caveat": "Review candidates from the accounts the connector returned, not decisions.",
        "presentation": {"layout": "full", "page_size": "A4"},
        "assessment": {
            "schema_version": 2,
            "report_mode": {"inventory": "compact"},
            "cover": {
                "title": "User access review",
                "scope_label": "Kiteworks tenant accounts",
            },
            "profile": "access-review",
            "run": {
                "id": str(meta.get("run_id") or "uar-run"),
                "version": "1",
                "operator": str(meta.get("operator") or "unavailable"),
                "scope": "Kiteworks tenant user accounts",
                "assessed_at": meta.get("assessed_at"),
                "generated_at": generated,
                "review_status": REVIEW_STATUS,
                "enumeration_complete": not unvisited,
                "unvisited_scope": unvisited,
            },
            "executive": {
                "purpose": f"Support the periodic user access review as of {ref}.",
                "conclusion": conclusion,
                "key_points": [
                    f"{_n(flagged)} flagged account(s); counts by type are in the profile details.",
                    PROPOSAL_ONLY + ".",
                ],
                "decisions": [
                    "The reviewer completes the attestation page after reviewing the accounts listed in this report."
                ],
            },
            "checks": [
                {
                    "id": "counts",
                    "label": "Account counts",
                    "method": "Counted by the User Account Reviewer engine from the accounts the connector returned",
                    "kind": "metadata",
                }
            ],
            "inventory": inventory,
            "findings": findings,
            "actions": actions,
            "limitations": limitations,
            "profile_details": details,
        },
    }
    return _scrub(record)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    rev = sub.add_parser("review")
    rev.add_argument("--roster", required=True)
    rev.add_argument("--reference-date", required=True)
    rev.add_argument("--dormant-days", type=int, default=DEFAULT_DORMANT_DAYS)
    rev.add_argument("--period-start")
    rev.add_argument("--tier-order")
    rev.add_argument("--out", required=True)
    norm = sub.add_parser("normalize")
    norm.add_argument(
        "input", nargs="?", help="saved search_users answer; stdin if omitted"
    )
    norm.add_argument("--out", required=True, help="roster.jsonl")
    norm.add_argument("--append", action="store_true", required=True)
    enr = sub.add_parser("enrich")
    enr.add_argument(
        "input", nargs="?", help="saved get_user_metadata answer; stdin if omitted"
    )
    enr.add_argument("--roster", required=True)
    enr.add_argument("--id", required=True)
    cnt = sub.add_parser("counts")
    cnt.add_argument("--result", required=True)
    cnt.add_argument("--reconciliation")
    cnt.add_argument("--roster", help="roster.jsonl, for its injection counter")
    cnt.add_argument("--proposed", help="proposed-changes.csv, for its row count")
    csv_cmd = sub.add_parser("csv")
    csv_cmd.add_argument("--result", required=True)
    csv_cmd.add_argument("--out", required=True)
    csv_cmd.add_argument(
        "--approved",
        action="store_true",
        help="people-data approval given: write the email and user_id columns",
    )
    recd = sub.add_parser("record")
    recd.add_argument("--result", required=True)
    recd.add_argument("--reconcile")
    recd.add_argument("--proposed", help="proposed-changes.csv, counted only")
    recd.add_argument("--meta", required=True)
    recd.add_argument("--compliance", required=True)
    recd.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    if args.cmd in ("normalize", "enrich"):
        text = (
            Path(args.input).read_text(encoding="utf-8")
            if args.input
            else sys.stdin.read()
        )
        payload = json.loads(text)
        if args.cmd == "normalize":
            print(json.dumps(normalize_append(payload, args.out)))
        else:
            print(json.dumps(enrich_user(args.roster, args.id, payload)))
        return 0
    if args.cmd == "counts":
        result = json.loads(Path(args.result).read_text(encoding="utf-8"))
        rec = (
            json.loads(Path(args.reconciliation).read_text(encoding="utf-8"))
            if args.reconciliation
            else None
        )
        proposed = None
        if args.proposed:
            with open(args.proposed, encoding="utf-8", newline="") as fh:
                proposed = max(sum(1 for _ in csv.reader(fh)) - 1, 0)
        roster = Path(args.roster) if args.roster else None
        injected = _read_counter(roster) if roster else 0
        enriched = len(_read_enriched(roster)) if roster else None
        view = counts_view(result, rec, injected, proposed, enriched)
        print(json.dumps(view, sort_keys=True))
        return 0
    if args.cmd == "review":
        users = _read_roster(Path(args.roster))
        tiers = (
            json.loads(Path(args.tier_order).read_text(encoding="utf-8"))
            if args.tier_order
            else None
        )
        result = find_issues(
            users,
            reference_date=date.fromisoformat(args.reference_date),
            dormant_days=args.dormant_days,
            period_start=date.fromisoformat(args.period_start)
            if args.period_start
            else None,
            tier_order=tiers,
        )
        result["users"] = users
        Path(args.out).write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return 0
    if args.cmd == "record":
        result = json.loads(Path(args.result).read_text(encoding="utf-8"))
        rec = (
            json.loads(Path(args.reconcile).read_text(encoding="utf-8"))
            if args.reconcile
            else None
        )
        prop_rows: list[dict[str, Any]] | None = None
        if args.proposed:
            with open(args.proposed, encoding="utf-8", newline="") as fh:
                prop_rows = list(csv.DictReader(fh))
        meta = json.loads(Path(args.meta).read_text(encoding="utf-8"))
        meta["compliance"] = load_compliance_observations(args.compliance)
        spec = report_record(result, rec, prop_rows, meta)
        Path(args.out).write_text(
            json.dumps(spec, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return 0
    result = json.loads(Path(args.result).read_text(encoding="utf-8"))
    rows = write_access_review_csv(result, args.out, include_people=args.approved)
    print(f"{rows} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
