#!/usr/bin/env python3
"""Activity Explorer engine: row normalisation, taxonomy, aggregation, CSVs.

Stdlib only. Compact rows (contract v1) are one JSON object per line:
{"event", "user_id", "client", "ok", "at", "object_id", "has_data"}.
IP addresses, geolocation, descriptions and user names never survive
normalisation, so no output of this module can contain them.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import io
import json
import re
import statistics
import sys
import zoneinfo
from bisect import bisect_right
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator
from datetime import date, datetime, timedelta, timezone, tzinfo
from pathlib import Path
from typing import Any

AI_CLIENT = "Kiteworks MCP"
OTHER = "other"
MAX_ASK_ROWS = 50
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
_OBJECT_ID_KEYS = ("objectId", "objectID", "object_id")


def _iso_utc(value: Any) -> str | None:
    if value is None or value == "":
        return None
    text = str(value)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _text(value: Any) -> str | None:
    return None if value is None or value == "" else str(value)


def normalize_row(raw: dict) -> dict:
    """Raw get_admin_activity row -> compact row; everything else is dropped."""
    data = raw.get("data")
    object_id = None
    for key in _OBJECT_ID_KEYS:
        object_id = _text(raw.get(key))
        if object_id is None and isinstance(data, dict):
            object_id = _text(data.get(key))
        if object_id is not None:
            break
    ok = raw.get("successful")
    return {
        "event": str(raw.get("eventName") or ""),
        "user_id": _text(raw.get("userId")),
        "client": _text(raw.get("clientName")),
        "ok": ok if isinstance(ok, bool) else None,
        "at": _iso_utc(raw.get("created")),
        "object_id": object_id,
        "has_data": bool(data),
    }


def load_taxonomy(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def categorize(event: str, taxonomy: dict) -> tuple[str, str]:
    """Return (category id, "exact" | "keyword" | "unknown"). Exact beats keyword."""
    exact = taxonomy.get("exact") or {}
    if event in exact:
        return exact[event], "exact"
    lowered = event.lower()
    for needle, category in taxonomy.get("keywords") or []:
        if needle.lower() in lowered:
            return category, "keyword"
    return OTHER, "unknown"


def _labels(taxonomy: dict) -> dict[str, str]:
    return {c["id"]: c["label"] for c in taxonomy.get("categories", [])}


def aggregate(
    rows: Iterable[dict], taxonomy: dict, users: dict[str, dict] | None = None
) -> dict:
    """Single streaming pass over compact rows; only counters are held."""
    users = users or {}
    labels = _labels(taxonomy)
    events = failed = known_outcome = ai_events = ai_failed = 0
    external = known_type = no_data = 0
    people: set[str] = set()
    cat: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    ev: dict[str, list] = {}
    ai_ev: dict[str, list] = {}
    clients: Counter[str] = Counter()
    outcome: Counter[str] = Counter()
    user_type: Counter[str] = Counter()
    profile: Counter[str] = Counter()
    by_day: dict[str, Counter[str]] = defaultdict(Counter)
    hours = [0] * 24
    unknown: Counter[str] = Counter()
    oldest = newest = None

    for row in rows:
        events += 1
        name = row.get("event") or ""
        category, how = categorize(name, taxonomy)
        if how == "unknown":
            unknown[name] += 1
        ok = row.get("ok")
        is_fail = ok is False
        uid = row.get("user_id")
        client = row.get("client")
        if uid is not None:
            people.add(uid)
        if ok is not None:
            known_outcome += 1
        outcome["unknown" if ok is None else "failed" if is_fail else "success"] += 1
        failed += is_fail
        cat[category][0] += 1
        cat[category][1] += is_fail
        entry = ev.setdefault(name, [category, 0, 0])
        entry[1] += 1
        entry[2] += is_fail
        clients[client or "unknown"] += 1
        info = users.get(uid) if uid is not None else None
        ext = info.get("external") if info else None
        if isinstance(ext, bool):
            known_type += 1
            external += ext
            user_type["external" if ext else "internal"] += 1
        else:
            user_type["unknown"] += 1
        profile[(info or {}).get("profile") or "unknown"] += 1
        if not row.get("has_data"):
            no_data += 1
        if client == AI_CLIENT:
            ai_events += 1
            ai_failed += is_fail
            a = ai_ev.setdefault(name, [category, 0, 0])
            a[1] += 1
            a[2] += is_fail
        at = row.get("at")
        if at:
            if oldest is None or at < oldest:
                oldest = at
            if newest is None or at > newest:
                newest = at
            by_day[at[:10]][category] += 1
            try:
                hours[int(at[11:13])] += 1
            except (ValueError, IndexError):
                pass

    def event_list(table: dict[str, list]) -> list[dict]:
        out = [
            {"event": n, "category": c, "count": k, "failed": f}
            for n, (c, k, f) in table.items()
        ]
        return sorted(out, key=lambda e: (-e["count"], e["event"]))

    return {
        "headline": {
            "events": events,
            "active_users": len(people),
            "failure_rate": failed / known_outcome if known_outcome else None,
            "external_share": external / known_type if known_type else None,
            "ai_share": ai_events / events if events else None,
        },
        "by_category": {
            c: {"label": labels.get(c, c), "events": n, "failed": f}
            for c, (n, f) in sorted(cat.items(), key=lambda kv: -kv[1][0])
        },
        "by_event": event_list(ev),
        "by_client": dict(clients.most_common()),
        "by_outcome": dict(outcome),
        "by_user_type": dict(user_type),
        "by_profile": dict(profile),
        "by_day": {d: dict(by_day[d]) for d in sorted(by_day)},
        "by_hour": hours,
        "ai": {
            "events": ai_events,
            "failures": ai_failed,
            "by_event": event_list(ai_ev),
        },
        "unknown_events": dict(unknown.most_common()),
        "rows_without_data": no_data,
        "oldest_at": oldest,
        "newest_at": newest,
    }


def ask_view(agg: dict, question_kind: str, max_rows: int = MAX_ASK_ROWS) -> list[dict]:
    """Aggregated rows for chat. Capped at 50, never per-person."""
    limit = max(0, min(int(max_rows), MAX_ASK_ROWS))
    if question_kind == "by_category":
        rows = [{"category": c, **v} for c, v in agg["by_category"].items()]
    elif question_kind == "by_event":
        rows = list(agg["by_event"])
    elif question_kind == "by_client":
        rows = [{"client": c, "events": n} for c, n in agg["by_client"].items()]
    elif question_kind == "failures":
        rows = [e for e in agg["by_event"] if e["failed"]]
        rows.sort(key=lambda e: (-e["failed"], e["event"]))
    elif question_kind == "ai":
        rows = list(agg["ai"]["by_event"])
    else:
        raise ValueError(f"unknown question kind: {question_kind}")
    return rows[:limit]


def _safe(value: Any) -> Any:
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value


def _write_csv(path: str | Path, header: list[str], table: Iterable[list]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        for row in table:
            writer.writerow([_safe(v) for v in row])


def write_by_category_csv(agg: dict, path: str | Path) -> None:
    total = agg["headline"]["events"] or 0
    _write_csv(
        path,
        ["category", "label", "events", "failed", "share"],
        (
            [
                c,
                v["label"],
                v["events"],
                v["failed"],
                round(v["events"] / total, 4) if total else 0,
            ]
            for c, v in agg["by_category"].items()
        ),
    )


def write_by_day_csv(agg: dict, path: str | Path) -> None:
    _write_csv(
        path,
        ["date", "category", "events"],
        ([d, c, n] for d, cats in agg["by_day"].items() for c, n in cats.items()),
    )


ANOMALY_COLUMNS = [
    "rule_id",
    "rule",
    "window_start",
    "window_end",
    "category",
    "account_id",
    "count",
    "threshold",
]


def write_anomalies_csv(
    flags: Iterable[dict], path: str | Path, *, include_accounts: bool = False
) -> None:
    """Aggregated by default: the account_id column (people data) is omitted."""
    columns = [c for c in ANOMALY_COLUMNS if include_accounts or c != "account_id"]
    _write_csv(path, columns, ([f.get(c) for c in columns] for f in flags))


def write_detail_csv(
    rows: Iterable[dict],
    path: str | Path,
    *,
    mode: str,
    approved: bool,
    taxonomy: dict | None = None,
) -> None:
    """Row-level export: person or object view only, after explicit approval."""
    if mode not in {"person", "object"} or approved is not True:
        raise PermissionError(
            "row-level CSV needs mode person or object and approved=True"
        )
    tax = taxonomy or {}
    _write_csv(
        path,
        ["at", "event", "category", "client", "ok", "user_id", "object_id"],
        (
            [
                r.get("at"),
                r.get("event"),
                categorize(r.get("event") or "", tax)[0],
                r.get("client"),
                r.get("ok"),
                r.get("user_id"),
                r.get("object_id"),
            ]
            for r in rows
        ),
    )


# --- anomaly rules (#428): explainable, rule-based, never scores or ranks ---

DEFAULT_TAXONOMY = Path(__file__).resolve().parent.parent / "event-taxonomy.json"
FAILURE_BURST_COUNT = 10
FAILURE_BURST_WINDOW = timedelta(minutes=60)
DEFAULT_BULK_DOWNLOAD_THRESHOLD = 100
_DAY_END = timedelta(hours=23, minutes=59, seconds=59)
_DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
_WORKING_HOURS = re.compile(
    r"^\s*(mon|tue|wed|thu|fri|sat|sun)(?:\s*-\s*(mon|tue|wed|thu|fri|sat|sun))?"
    r"\s+(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})\s+(\S+)\s*$",
    re.IGNORECASE,
)
_FIXED_OFFSET = re.compile(r"^UTC(?:([+-])(\d{1,2}):(\d{2}))?$", re.IGNORECASE)


def _parse_at(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _fmt(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _num(value: float) -> int | float:
    return int(value) if float(value).is_integer() else value


def _flag(
    rule_id: str,
    rule: str,
    start: datetime,
    end: datetime,
    count: int,
    threshold: int | float | None,
    category: str | None = None,
    account_id: str | None = None,
) -> dict:
    return {
        "rule_id": rule_id,
        "rule": rule,
        "window_start": _fmt(start),
        "window_end": _fmt(end),
        "category": category,
        "account_id": account_id,
        "count": count,
        "threshold": threshold,
    }


def _order(flags: list[dict]) -> list[dict]:
    """Time order only; never by count (no ranking of anything)."""
    return sorted(
        flags,
        key=lambda f: (
            f["window_start"],
            f["rule_id"],
            f["account_id"] or "",
            f["category"] or "",
        ),
    )


def _period_days(
    agg: dict, period_start: str | None, period_end: str | None
) -> list[str]:
    """Every UTC day of the period (inclusive), empty days included."""
    if period_start and period_end:
        first, last = str(period_start)[:10], str(period_end)[:10]
        if len(str(period_end)) > 10:
            # Half-open end (previous_period): the instant itself is not in it.
            end_at = _parse_at(period_end)
            if end_at is not None:
                last = (end_at - timedelta(microseconds=1)).date().isoformat()
    else:
        first, last = (
            (agg.get("oldest_at") or "")[:10],
            (agg.get("newest_at") or "")[:10],
        )
    if not first or not last:
        return []
    try:
        day, stop = date.fromisoformat(first), date.fromisoformat(last)
    except ValueError:
        return []
    out = []
    while day <= stop:
        out.append(day.isoformat())
        day += timedelta(days=1)
    return out


def flag_volume_spikes(
    agg: dict, period_start: str | None = None, period_end: str | None = None
) -> list[dict]:
    """Day count above 3 x max(median, 1), per category (days with 0 count)."""
    days = _period_days(agg, period_start, period_end)
    by_day = agg.get("by_day") or {}
    flags = []
    for category, info in sorted((agg.get("by_category") or {}).items()):
        counts = [(by_day.get(d) or {}).get(category, 0) for d in days]
        if not counts:
            continue
        median = _num(statistics.median(counts))
        limit = _num(3 * max(median, 1))
        label = info.get("label", category)
        rule = f"Daily {label} events above 3 times the period median ({median})"
        for day, count in zip(days, counts, strict=True):
            if count > limit:
                start = datetime.fromisoformat(day).replace(tzinfo=timezone.utc)
                flags.append(
                    _flag(
                        "volume_spike",
                        rule,
                        start,
                        start + _DAY_END,
                        count,
                        limit,
                        category,
                    )
                )
    return _order(flags)


def flag_failure_bursts(rows: Iterable[dict]) -> list[dict]:
    """10+ failed rows of one account within any 60 minutes, merged per run."""
    times: dict[str, list[datetime]] = defaultdict(list)
    for r in rows:
        moment = _parse_at(r.get("at"))
        if r.get("ok") is False and r.get("user_id") is not None and moment:
            times[r["user_id"]].append(moment)
    rule = "10 or more failed actions by one account within one hour"
    flags = []
    for account, stamps in times.items():
        stamps.sort()
        spans: list[list[int]] = []  # [first index, last index] per merged run
        for i in range(len(stamps) - FAILURE_BURST_COUNT + 1):
            j = i + FAILURE_BURST_COUNT - 1
            if stamps[j] - stamps[i] > FAILURE_BURST_WINDOW:
                continue
            if spans and stamps[i] <= stamps[spans[-1][1]]:
                spans[-1][1] = j
            else:
                spans.append([i, j])
        for i0, j in spans:
            first, last = stamps[i0], stamps[j]
            n = bisect_right(stamps, last) - i0
            flags.append(
                _flag("failure_burst", rule, first, last, n, FAILURE_BURST_COUNT,
                      account_id=account)
            )  # fmt: skip
    return _order(flags)


def flag_bulk_downloads(
    rows: Iterable[dict],
    taxonomy: dict,
    threshold: int = DEFAULT_BULK_DOWNLOAD_THRESHOLD,
) -> list[dict]:
    """More than `threshold` content_transfer download rows per account per UTC day."""
    counts: Counter[tuple[str, str]] = Counter()
    for r in rows:
        name = r.get("event") or ""
        moment = _parse_at(r.get("at"))
        if r.get("user_id") is None or moment is None or "download" not in name.lower():
            continue
        if categorize(name, taxonomy)[0] == "content_transfer":
            counts[(r["user_id"], moment.strftime("%Y-%m-%d"))] += 1
    rule = f"More than {threshold} downloads by one account in one day"
    flags = []
    for (account, day), n in counts.items():
        if n > threshold:
            start = datetime.fromisoformat(day).replace(tzinfo=timezone.utc)
            flags.append(
                _flag("bulk_download", rule, start, start + _DAY_END, n, threshold,
                      "content_transfer", account)
            )  # fmt: skip
    return _order(flags)


def _skipped(zone: str) -> str:
    return f"Working-hours rule skipped: time zone {zone} unavailable on this host"


def flag_outside_hours(
    rows: Iterable[dict], taxonomy: dict, working_hours: str | None
) -> tuple[list[dict], list[str]]:
    """Events outside "Mon-Fri 08:00-18:00 <IANA zone | UTC+02:00>", per day and
    category (never per person). Off without config; degrades with a limitation."""
    if not working_hours:
        return [], []
    match = _WORKING_HOURS.match(working_hours)
    if not match:
        return [], [f"Working-hours rule skipped: cannot parse {working_hours!r}"]
    d1, d2, h1, m1, h2, m2, zone_name = match.groups()
    start_min, end_min = int(h1) * 60 + int(m1), int(h2) * 60 + int(m2)
    if not (0 <= start_min < end_min <= 24 * 60):
        return [], [f"Working-hours rule skipped: cannot parse {working_hours!r}"]
    first = _DAYS.index(d1.lower())
    last = _DAYS.index((d2 or d1).lower())
    workdays = {(first + k) % 7 for k in range((last - first) % 7 + 1)}
    offset = _FIXED_OFFSET.match(zone_name)
    if offset:
        sign, hh, mm = offset.groups()
        delta = timedelta(hours=int(hh or 0), minutes=int(mm or 0))
        try:
            zone: tzinfo = timezone(-delta if sign == "-" else delta)
        except ValueError:
            return [], [f"Working-hours rule skipped: cannot parse {working_hours!r}"]
    else:
        try:
            zone = zoneinfo.ZoneInfo(zone_name)
        except Exception:
            return [], [_skipped(zone_name)]
    rule = f"Activity outside the configured working hours ({working_hours})"
    groups: dict[tuple[str, str], list] = {}
    for r in rows:
        moment = _parse_at(r.get("at"))
        if moment is None:
            continue
        local = moment.astimezone(zone)
        minute = local.hour * 60 + local.minute
        if local.weekday() in workdays and start_min <= minute < end_min:
            continue
        key = (
            local.strftime("%Y-%m-%d"),
            categorize(r.get("event") or "", taxonomy)[0],
        )
        g = groups.setdefault(key, [0, moment, moment])
        g[0] += 1
        g[1], g[2] = min(g[1], moment), max(g[2], moment)
    flags = [
        _flag("outside_hours", rule, lo, hi, n, None, category)
        for (_, category), (n, lo, hi) in groups.items()
    ]
    return _order(flags), []


def run_rules(
    rows: Iterable[dict], agg: dict, config: dict | None
) -> tuple[list[dict], list[str]]:
    """All four rules. config: taxonomy, working_hours, bulk_download_threshold,
    period_start, period_end. Returns (flags in time order, limitations)."""
    config = config or {}
    rows = list(rows)
    taxonomy = config.get("taxonomy")
    flags = flag_volume_spikes(
        agg, config.get("period_start"), config.get("period_end")
    )
    flags += flag_failure_bursts(rows)
    limitations: list[str] = []
    if taxonomy is None:
        limitations.append(
            "Outside-hours and bulk-download rules skipped: no taxonomy supplied"
        )
    else:
        threshold = config.get("bulk_download_threshold")
        flags += flag_bulk_downloads(
            rows,
            taxonomy,
            DEFAULT_BULK_DOWNLOAD_THRESHOLD if threshold is None else int(threshold),
        )
        extra, limits = flag_outside_hours(rows, taxonomy, config.get("working_hours"))
        flags += extra
        limitations += limits
    return _order(flags), limitations


def previous_period(start: datetime, end: datetime) -> tuple[datetime, datetime]:
    """The period of equal length that ends where this one starts."""
    return start - (end - start), start


def _change(now: Any, prev: Any) -> dict:
    delta = None
    if now is not None and prev is not None:
        delta = now - prev
        if isinstance(delta, float):
            delta = round(delta, 6)
    pct = None
    if delta is not None and prev:
        pct = round(delta / prev * 100, 2)
    return {"now": now, "previous": prev, "delta": delta, "delta_pct": pct}


def compare(agg_now: dict, agg_prev: dict) -> dict:
    """Per headline figure and per category: now, previous, delta, delta_pct."""
    head_now, head_prev = agg_now.get("headline") or {}, agg_prev.get("headline") or {}
    keys = list(head_now) + [k for k in head_prev if k not in head_now]
    cats_now, cats_prev = (
        agg_now.get("by_category") or {},
        agg_prev.get("by_category") or {},
    )
    cat_keys = list(cats_now) + [k for k in cats_prev if k not in cats_now]
    by_category = {}
    for c in cat_keys:
        label = (cats_now.get(c) or cats_prev.get(c) or {}).get("label", c)
        by_category[c] = {
            "label": label,
            **_change(
                (cats_now.get(c) or {}).get("events", 0),
                (cats_prev.get(c) or {}).get("events", 0),
            ),
        }
    return {
        "headline": {k: _change(head_now.get(k), head_prev.get(k)) for k in keys},
        "by_category": by_category,
    }


# --- report record (#430): the kw-pdf-report assessment for profile audit-activity ---

NOT_FORENSIC = "Observations from your audit log, not forensic evidence."
AI_EMPTY = "No actions by AI agents in this period"
REVIEW_STATUS = (
    "Automated assessment \u00b7 not reviewed by a person \u00b7 "
    "findings need owner validation"
)
AI_FRAMEWORKS = ("EU AI Act", "ISO 42001", "NIST AI RMF")
_IPV4 = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
_IPV6 = re.compile(r"\b(?:[0-9A-Fa-f]{1,4}:){2,7}[0-9A-Fa-f]{0,4}\b|::[0-9A-Fa-f:]+")
_ID_UNSAFE = re.compile(r"[^A-Za-z0-9_-]+")
COMPLIANCE_COLUMNS = (
    "framework",
    "control",
    "title",
    "observes",
    "cannot_show",
    "source",
    "verified",
)


def _no_ip(value: Any) -> Any:
    """Defence in depth: no IPv4/IPv6 literal survives in any report string."""
    if isinstance(value, str):
        return _IPV6.sub("[ip removed]", _IPV4.sub("[ip removed]", value))
    if isinstance(value, list):
        return [_no_ip(v) for v in value]
    if isinstance(value, dict):
        return {k: _no_ip(v) for k, v in value.items()}
    return value


def _pct(value: Any) -> str:
    return "not available" if value is None else f"{value * 100:.1f}%"


def _n(value: Any) -> str:
    return "not available" if value is None else f"{value:,}"


def _signed(change: dict, pct: bool = False) -> str:
    now, prev = change.get("now"), change.get("previous")
    if now is None or prev is None:
        return "not comparable"
    if pct:
        return f"{_pct(now)} vs {_pct(prev)}"
    delta = change.get("delta_pct")
    tail = f", {delta:+.1f}%" if delta is not None else ""
    return f"{_n(now)} vs {_n(prev)}{tail}"


def load_compliance_observations(path: str | Path) -> list[dict]:
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
        row["source"] = row["source"].strip("<>")
        out.append(row)
    return out


def report_record(
    agg: dict, flags: Iterable[dict], cmp: dict | None, meta: dict
) -> dict:
    """Pure: engine outputs -> kw-pdf-report spec for profile ``audit-activity``.

    Reads only aggregated figures; never raw rows, IP addresses or locations.
    meta: mode (report|person|object), period {start,end}, windows_run, row_cap,
    row_cap_hit, rows, oldest_at, taxonomy_version, purpose, object {id,name},
    operator, run_id, assessed_at, generated_at, timezone, compliance (rows of
    ``load_compliance_observations``), limitations, previous_period.
    """
    mode = meta.get("mode") or "report"
    flags = list(flags)
    head = agg.get("headline") or {}
    period = meta.get("period") or {}
    start, end = period.get("start", "?"), period.get("end", "?")
    purpose = _text(meta.get("purpose"))
    if mode == "person" and not purpose:
        raise ValueError("person view needs the typed purpose")
    fence = _sibling("data-fence", "_kw_fence", "fence.py").fence
    obj = meta.get("object") or {}
    if mode == "object" and not obj.get("id"):
        raise ValueError("object history needs the object id")
    if mode == "person":
        scope = f"Person view \u00b7 Purpose: {fence(purpose, FENCE_MAX)}"
    elif mode == "object":
        scope = (
            f"Object history \u00b7 {fence(str(obj['id']), FENCE_MAX)} "
            f"{fence(str(obj.get('name') or ''), FENCE_MAX)}".strip()
        )
    else:
        scope = "Kiteworks tenant audit log"
    tz = meta.get("timezone") or "UTC"
    cats = agg.get("by_category") or {}
    ai = agg.get("ai") or {"events": 0, "failures": 0, "by_event": []}

    inventory = [
        {
            "id": "ALL",
            "name": "All events in the period",
            "type": "period",
            "checks": [{"id": "counts", "status": "checked", "method": "Engine count"}],
            "facts": {
                "events": head.get("events") or 0,
                "active users": head.get("active_users") or 0,
            },
        }
    ]
    cat_ids = {"ALL"}
    for key, val in cats.items():
        ident = "CAT-" + _ID_UNSAFE.sub("-", key)[:70]
        cat_ids.add(ident)
        inventory.append(
            {
                "id": ident,
                "name": str(val.get("label") or key),
                "type": "event category",
                "checks": [
                    {"id": "counts", "status": "checked", "method": "Engine count"}
                ],
                "facts": {
                    "events": val.get("events") or 0,
                    "failed events": val.get("failed") or 0,
                },
            }
        )

    findings = []
    by_rule: dict[str, list[dict]] = defaultdict(list)
    for f in flags:
        by_rule[str(f.get("rule_id") or "rule")].append(f)
    for rule_id, group in by_rule.items():
        targets = sorted(
            {
                "CAT-" + _ID_UNSAFE.sub("-", f["category"])[:70]
                for f in group
                if f.get("category")
            }
            & cat_ids
        ) or ["ALL"]
        accounts = len({f["account_id"] for f in group if f.get("account_id")})
        windows = sorted({(f.get("window_start"), f.get("window_end")) for f in group})
        first = windows[0] if windows else ("?", "?")
        findings.append(
            {
                "id": "ANOM-" + _ID_UNSAFE.sub("-", rule_id)[:70],
                "title": f"Rule observed: {rule_id.replace('_', ' ')}",
                "observation": (
                    f"{group[0].get('rule')} Observed in {len(windows)} window(s)"
                    f" across {len(group)} flag(s), first window starting {first[0]}"
                    + (f"; {accounts} account(s) involved" if accounts else "")
                    + "."
                ),
                "impact": "A pattern the rule describes; its cause is not established.",
                "confidence": "Rule-based observation",
                "priority": "info",
                "priority_reason": "Rule match only; no impact has been assessed.",
                "recommendation": (
                    "Compare with known events such as releases, migrations or "
                    "audits before drawing conclusions."
                ),
                "object_ids": targets,
                "check_ids": ["counts"],
            }
        )

    ordered = [(c, v) for c, v in cats.items()]
    trend = "; ".join(f"{v['label']} {_n(v['events'])}" for c, v in ordered) or "none"
    events_top = (agg.get("by_event") or [])[:10]
    top_events = (
        "; ".join(f"{e['event']} {_n(e['count'])}" for e in events_top) or "none"
    )
    apps = "; ".join(
        f"{c} {_n(n)}" for c, n in list((agg.get("by_client") or {}).items())[:10]
    )
    failing = sorted(
        (e for e in agg.get("by_event") or [] if e.get("failed")),
        key=lambda e: (-e["failed"], e["event"]),
    )[:10]
    failures = (
        "; ".join(
            f"{e['event']} {_n(e['failed'])} of {_n(e['count'])}" for e in failing
        )
        or "no failed events"
    )
    if ai.get("events"):
        ai_text = (
            f"{_n(ai['events'])} event(s) by AI agents (client Kiteworks MCP), "
            f"{_n(ai.get('failures'))} failed. By event: "
            + "; ".join(f"{e['event']} {_n(e['count'])}" for e in ai["by_event"][:10])
        )
    else:
        ai_text = AI_EMPTY
    if cmp:
        ch = cmp.get("headline") or {}
        prev = meta.get("previous_period") or {}
        label = (
            f"previous period {prev.get('start')} to {prev.get('end')}"
            if prev
            else "previous period of equal length"
        )
        comparison = (
            f"Against the {label}: events {_signed(ch.get('events', {}))}; "
            f"active users {_signed(ch.get('active_users', {}))}; "
            f"failure rate {_signed(ch.get('failure_rate', {}), pct=True)}; "
            f"external share {_signed(ch.get('external_share', {}), pct=True)}; "
            f"AI share {_signed(ch.get('ai_share', {}), pct=True)}."
        )
    else:
        comparison = "No previous period was read, so no comparison is shown."
    unknown = agg.get("unknown_events") or {}
    unknown_text = (
        "; ".join(f"{fence(n, FENCE_MAX)} {c}" for n, c in list(unknown.items())[:20])
        or "none"
    )
    compliance = meta.get("compliance") or []

    def render(rows: list[dict]) -> str:
        return "; ".join(
            f"{r['framework']} {r['control']} ({r['title']}): observes "
            f"{r['observes']}. Cannot show {r['cannot_show']}. "
            f"verified: {r.get('verified', 'false')}"
            for r in rows
        )

    ai_rows = [r for r in compliance if r["framework"] in AI_FRAMEWORKS]
    obs_rows = render([r for r in compliance if r["framework"] not in AI_FRAMEWORKS])
    if ai_rows:
        ai_text += ". Observations for the AI frameworks: " + render(ai_rows)
    details = {
        "Period and time zone": f"{start} to {end}; time zone {tz}",
        "Headline figures": (
            f"events {_n(head.get('events'))}; active users {_n(head.get('active_users'))}; "
            f"failure rate {_pct(head.get('failure_rate'))}; external share "
            f"{_pct(head.get('external_share'))}; AI share {_pct(head.get('ai_share'))}"
        ),
        "Trend by category": trend,
        "Top event types": top_events,
        "Top apps": apps or "none",
        "Failures": failures,
        "AI-client section": ai_text,
        "Comparison with the previous period": comparison,
        "Method and limits": (
            f"{meta.get('windows_run', 0)} window(s) of at most 30 days run; row cap "
            f"{meta.get('row_cap', 0)}, {'hit' if meta.get('row_cap_hit') else 'not hit'}; "
            f"{meta.get('rows', head.get('events') or 0)} row(s) read; oldest row returned "
            f"{meta.get('oldest_at') or agg.get('oldest_at') or 'not available'}; "
            f"{agg.get('rows_without_data', 0)} row(s) with empty object data; taxonomy "
            f"version {meta.get('taxonomy_version') or 'unknown'}; unknown event names: "
            f"{unknown_text}. {NOT_FORENSIC}"
        ),
        "Anomaly rules": (
            "Rule-based and explainable; nothing is scored and nobody is ranked. "
            f"{len(flags)} flag(s) raised."
        ),
        "Compliance observations": (
            (
                obs_rows + ". These are observations about what this log can show, "
                "not statements about any control; the control wording is still "
                "to be verified by a person."
            )
            if obs_rows
            else "No compliance observation table was supplied."
        ),
    }
    if mode == "person":
        details["Purpose"] = fence(purpose, FENCE_MAX)
    if mode == "object":
        details["Object"] = scope.removeprefix("Object history \u00b7 ")
    limitations = [
        NOT_FORENSIC,
        "Login and settings events are not confirmed to be covered.",
        "IP addresses and locations are never written to this report.",
    ] + [str(x) for x in meta.get("limitations") or []]
    if meta.get("row_cap_hit"):
        limitations.append(
            "The run stopped at the row cap; later rows are not counted."
        )
    title = {
        "report": "Activity Explorer report",
        "person": "Activity Explorer person view",
        "object": "Activity Explorer object history",
    }[mode]
    generated = meta.get("generated_at") or meta.get("assessed_at")
    record = {
        "agent_name": "Activity Explorer",
        "report_title": title,
        "scan_date": str(meta.get("assessed_at") or generated)[:10],
        "scope_caveat": NOT_FORENSIC,
        "presentation": {"layout": "full", "page_size": "A4"},
        "assessment": {
            "schema_version": 2,
            "report_mode": {"inventory": "compact"},
            "cover": {"title": title, "scope_label": scope[:160]},
            "profile": "audit-activity",
            "run": {
                "id": str(meta.get("run_id") or "activity-run"),
                "version": "1",
                "operator": str(meta.get("operator") or "unavailable"),
                "scope": scope,
                "assessed_at": meta.get("assessed_at"),
                "generated_at": generated,
                "review_status": REVIEW_STATUS,
                "enumeration_complete": not meta.get("row_cap_hit"),
                "unvisited_scope": (
                    ["Rows after the row cap"] if meta.get("row_cap_hit") else []
                ),
            },
            "executive": {
                "purpose": (
                    f"Show what the audit log recorded from {start} to {end}."
                    + (
                        f" Purpose given: {fence(purpose, FENCE_MAX)}."
                        if purpose
                        else ""
                    )
                ),
                "conclusion": (
                    f"{_n(head.get('events'))} events by {_n(head.get('active_users'))} "
                    f"active users were read; failure rate {_pct(head.get('failure_rate'))}. "
                    f"{NOT_FORENSIC}"
                ),
                "key_points": [
                    f"{len(flags)} rule observation(s); each is explained by its rule text.",
                    ai_text
                    if not ai.get("events")
                    else f"AI agents: {_n(ai['events'])} event(s).",
                ],
                "decisions": [
                    "No decision is needed from this report; review the observations "
                    "against what you already know."
                ],
            },
            "checks": [
                {
                    "id": "counts",
                    "label": "Event counts",
                    "method": "Counted by the Activity Explorer engine from the audit log rows returned",
                    "kind": "metadata",
                }
            ],
            "inventory": inventory,
            "findings": findings,
            "actions": [],
            "limitations": limitations,
            "profile_details": details,
        },
    }
    return _no_ip(record)


def read_jsonl(path: str | Path) -> Iterator[dict]:
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


_SKILLS_DIR = Path(__file__).resolve().parents[2]
FENCE_MAX = 78
_ROW_LIST_KEYS = ("rows", "items", "results", "activities", "data")


def _sibling(skill: str, module: str, script: str):
    """Load a sibling skill's script by path (the plugin is self-contained)."""
    path = _SKILLS_DIR / skill / "scripts" / script
    spec = importlib.util.spec_from_file_location(module, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def extract_raw_rows(payload: Any) -> list[dict]:
    """Rows of one saved get_admin_activity answer (a list or a wrapper object)."""
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for key in _ROW_LIST_KEYS:
            if isinstance(payload.get(key), list):
                return extract_raw_rows(payload[key])
        for value in payload.values():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                return extract_raw_rows(value)
    return []


def _compact_key(row: dict) -> tuple:
    return tuple(
        row.get(k) for k in ("at", "event", "user_id", "client", "ok", "object_id")
    )


EXPLORER_TOOLS = frozenset(
    {
        "get_admin_activity",
        "search_users",
        "find_user_by_email",
        "get_user_metadata",
        "get_file_metadata",
        "search_files",
        "search_folders",
        "get_user_info_whoami",
    }
)


def _strings(value: Any, depth: int = 0) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif depth < 4 and isinstance(value, dict):
        for item in value.values():
            yield from _strings(item, depth + 1)
    elif depth < 4 and isinstance(value, list):
        for item in value:
            yield from _strings(item, depth + 1)


def row_looks_injected(raw: dict) -> bool:
    """data-fence heuristic over every string of a raw row (before it is dropped)."""
    looks = _sibling("data-fence", "_kw_fence", "fence.py").looks_like_instruction
    return any(looks(t, EXPLORER_TOOLS) for t in _strings(raw))


def normalize_append(
    payload: Any, out: str | Path, boundary: str | None = None
) -> dict:
    """Append compact rows for one saved tool answer to ``out``.

    description, ipAddress, geolocationId and userName are dropped before
    anything is written. Duplicates inside one answer are removed with the
    admin-window row key; rows at the window ``boundary`` instant are also
    removed when the file already holds the same compact row.
    """
    row_key = _sibling("admin-window", "_kw_admin_window", "admin_window.py").row_key
    out_path = Path(out)
    existing: set[tuple] = set()
    wanted = _iso_utc(boundary) if boundary else None
    if wanted and out_path.exists():
        existing = {
            _compact_key(r) for r in read_jsonl(out_path) if r.get("at") == wanted
        }
    seen: set[tuple] = set()
    kept: list[dict] = []
    suspected = 0
    raw_rows = extract_raw_rows(payload)
    for raw in raw_rows:
        key = row_key(raw)
        if key in seen:
            continue
        seen.add(key)
        row = normalize_row(raw)
        if wanted and row["at"] == wanted and _compact_key(row) in existing:
            continue
        kept.append(row)
        suspected += row_looks_injected(raw)
    with open(out_path, "a", encoding="utf-8", newline="\n") as fh:
        for row in kept:
            fh.write(json.dumps(row, separators=(",", ":")) + "\n")
    counter = out_path.with_name(out_path.name + ".injection")
    try:
        total = int(counter.read_text(encoding="utf-8").strip() or 0)
    except (OSError, ValueError):
        total = 0
    total += suspected
    counter.write_text(f"{total}\n", encoding="utf-8")
    return {
        "read": len(raw_rows),
        "appended": len(kept),
        "injection_suspected_count": total,
    }


def fenced_ask_rows(agg: dict, kind: str, max_rows: int = MAX_ASK_ROWS) -> list[dict]:
    """``ask_view`` rows with every string fenced (data-fence) and truncated."""
    fence = _sibling("data-fence", "_kw_fence", "fence.py").fence
    return [
        {k: fence(v, FENCE_MAX) if isinstance(v, str) else v for k, v in row.items()}
        for row in ask_view(agg, kind, max_rows)
    ]


def fenced_unknown_events(agg: dict, limit: int = 50) -> list[dict]:
    """Unknown event names with counts, fenced and truncated, never dropped."""
    fence = _sibling("data-fence", "_kw_fence", "fence.py").fence
    items = (agg.get("unknown_events") or {}).items()
    return [{"name": fence(n, FENCE_MAX), "count": c} for n, c in list(items)[:limit]]


def _utf8_stdout() -> None:
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")


def read_payload(path: str | None) -> Any:
    text = Path(path).read_text(encoding="utf-8") if path else sys.stdin.read()
    return json.loads(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("aggregate")
    a.add_argument("--rows", required=True)
    a.add_argument("--taxonomy", required=True)
    a.add_argument("--users")
    a.add_argument("--out", required=True)
    c = sub.add_parser("csv")
    c.add_argument("--agg", required=True)
    c.add_argument("--kind", choices=["by-category", "by-day"], required=True)
    c.add_argument("--out", required=True)
    d = sub.add_parser("detail")
    d.add_argument("--rows", required=True)
    d.add_argument("--taxonomy", required=True)
    d.add_argument("--mode", required=True)
    d.add_argument("--approved", action="store_true")
    d.add_argument("--out", required=True)
    r = sub.add_parser("rules")
    r.add_argument("--rows", required=True)
    r.add_argument("--agg", required=True)
    r.add_argument("--taxonomy", default=str(DEFAULT_TAXONOMY))
    r.add_argument("--working-hours")
    r.add_argument("--bulk-threshold", type=int)
    r.add_argument("--period-start")
    r.add_argument("--period-end")
    r.add_argument("--out", required=True)
    an = sub.add_parser("anomalies")
    an.add_argument("--flags", required=True)
    an.add_argument("--out", required=True)
    an.add_argument("--with-accounts", action="store_true")
    an.add_argument("--approved", action="store_true")
    rc = sub.add_parser("record")
    rc.add_argument("--agg", required=True)
    rc.add_argument("--flags", required=True)
    rc.add_argument("--compare")
    rc.add_argument("--meta", required=True)
    rc.add_argument("--compliance")
    rc.add_argument("--out", required=True)
    p = sub.add_parser("compare")
    p.add_argument("--now", required=True)
    p.add_argument("--prev", required=True)
    p.add_argument("--out", required=True)
    n = sub.add_parser("normalize")
    n.add_argument(
        "input", nargs="?", help="saved tool-result JSON file; stdin if omitted"
    )
    n.add_argument("--out", required=True)
    n.add_argument("--append", action="store_true", required=True)
    n.add_argument(
        "--boundary", help="window boundary instant (ISO) for cross-call de-dup"
    )
    q = sub.add_parser("ask-view")
    q.add_argument("--agg", required=True)
    q.add_argument(
        "--kind",
        required=True,
        choices=["by_category", "by_event", "by_client", "failures", "ai"],
    )
    u = sub.add_parser("unknown-events")
    u.add_argument("--agg", required=True)
    args = parser.parse_args(argv)

    if args.cmd == "aggregate":
        users = (
            json.loads(Path(args.users).read_text(encoding="utf-8"))
            if args.users
            else None
        )
        agg = aggregate(read_jsonl(args.rows), load_taxonomy(args.taxonomy), users)
        Path(args.out).write_text(json.dumps(agg, indent=2) + "\n", encoding="utf-8")
    elif args.cmd == "rules":
        agg = json.loads(Path(args.agg).read_text(encoding="utf-8"))
        config = {
            "taxonomy": load_taxonomy(args.taxonomy) if args.taxonomy else None,
            "working_hours": args.working_hours,
            "bulk_download_threshold": args.bulk_threshold,
            "period_start": args.period_start,
            "period_end": args.period_end,
        }
        flags, limits = run_rules(read_jsonl(args.rows), agg, config)
        result = {"flags": flags, "limitations": limits}
        Path(args.out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    elif args.cmd == "anomalies":
        if args.with_accounts and not args.approved:
            print("refused: account ids need --approved", file=sys.stderr)
            return 2
        loaded = json.loads(Path(args.flags).read_text(encoding="utf-8"))
        flags = loaded["flags"] if isinstance(loaded, dict) else loaded
        write_anomalies_csv(flags, args.out, include_accounts=args.with_accounts)
    elif args.cmd == "record":
        agg = json.loads(Path(args.agg).read_text(encoding="utf-8"))
        loaded = json.loads(Path(args.flags).read_text(encoding="utf-8"))
        flags = loaded["flags"] if isinstance(loaded, dict) else loaded
        cmp = (
            json.loads(Path(args.compare).read_text(encoding="utf-8"))
            if args.compare
            else None
        )
        meta = json.loads(Path(args.meta).read_text(encoding="utf-8"))
        if args.compliance:
            meta["compliance"] = load_compliance_observations(args.compliance)
        record = report_record(agg, flags, cmp, meta)
        Path(args.out).write_text(
            json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    elif args.cmd == "compare":
        now = json.loads(Path(args.now).read_text(encoding="utf-8"))
        prev = json.loads(Path(args.prev).read_text(encoding="utf-8"))
        out = json.dumps(compare(now, prev), indent=2) + "\n"
        Path(args.out).write_text(out, encoding="utf-8")
    elif args.cmd == "normalize":
        result = normalize_append(read_payload(args.input), args.out, args.boundary)
        print(json.dumps(result))
    elif args.cmd == "ask-view":
        agg = json.loads(Path(args.agg).read_text(encoding="utf-8"))
        _utf8_stdout()
        print(json.dumps(fenced_ask_rows(agg, args.kind), ensure_ascii=False))
    elif args.cmd == "unknown-events":
        agg = json.loads(Path(args.agg).read_text(encoding="utf-8"))
        _utf8_stdout()
        print(json.dumps(fenced_unknown_events(agg), ensure_ascii=False))
    elif args.cmd == "csv":
        agg = json.loads(Path(args.agg).read_text(encoding="utf-8"))
        (write_by_category_csv if args.kind == "by-category" else write_by_day_csv)(
            agg, args.out
        )
    else:
        try:
            write_detail_csv(
                read_jsonl(args.rows),
                args.out,
                mode=args.mode,
                approved=args.approved,
                taxonomy=load_taxonomy(args.taxonomy),
            )
        except PermissionError as exc:
            print(f"refused: {exc}", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
