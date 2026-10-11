"""Admin-log window helper: split a period, build call arguments, pace, cap.

Stdlib only. No I/O at import; time is injected where it matters.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone

MAX_WINDOW_DAYS = 30
MAX_PERIOD_DAYS = 366
PAGE_LIMIT = 10000
PACE_SECONDS = 3.0
RETRY_WAIT_SECONDS = 5.0
ROW_CAP = 50000

_MAX_LIMIT = 10000
_TS_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def _to_utc(value: datetime, name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def split_windows(
    start: datetime,
    end: datetime,
    *,
    max_days: int = MAX_WINDOW_DAYS,
    max_period_days: int = MAX_PERIOD_DAYS,
) -> list[tuple[datetime, datetime]]:
    """Split [start, end] into adjacent windows, oldest first, in UTC."""
    start_utc = _to_utc(start, "start")
    end_utc = _to_utc(end, "end")
    if start_utc >= end_utc:
        raise ValueError("start must be before end")
    if end_utc - start_utc > timedelta(days=max_period_days):
        raise ValueError(f"period longer than {max_period_days} days")
    step = timedelta(days=max_days)
    windows: list[tuple[datetime, datetime]] = []
    cursor = start_utc
    while cursor < end_utc:
        stop = min(cursor + step, end_utc)
        windows.append((cursor, stop))
        cursor = stop
    return windows


def _stamp(value: datetime) -> str:
    return _to_utc(value, "timestamp").strftime(_TS_FORMAT)


def window_args(
    window: tuple[datetime, datetime],
    *,
    limit: int = PAGE_LIMIT,
    offset: int = 0,
    extra: dict | None = None,
) -> dict:
    """Arguments for one get_admin_activity page."""
    if not 1 <= limit <= _MAX_LIMIT:
        raise ValueError(f"limit must be 1..{_MAX_LIMIT}")
    if offset < 0:
        raise ValueError("offset must not be negative")
    extra = dict(extra or {})
    if "searchText" in extra:
        raise ValueError("searchText answers 403; filter client-side")
    args = {
        "startDateTime": _stamp(window[0]),
        "endDateTime": _stamp(window[1]),
        "limit": limit,
        "offset": offset,
    }
    args.update(extra)
    return args


def row_key(row: dict) -> tuple:
    """De-duplication key for a row that may sit on a window boundary."""
    return (
        row.get("created"),
        row.get("eventName"),
        row.get("userId"),
        row.get("description"),
    )


class Pacer:
    """Sleeps only the remainder of the interval since the last same-method call."""

    def __init__(self, interval_s=PACE_SECONDS, clock=time.monotonic, sleep=time.sleep):
        self.interval_s = interval_s
        self._clock = clock
        self._sleep = sleep
        self._last: dict[str, float] = {}

    def wait(self, method: str) -> float:
        slept = 0.0
        last = self._last.get(method)
        if last is not None:
            remaining = self.interval_s - (self._clock() - last)
            if remaining > 0:
                self._sleep(remaining)
                slept = remaining
        self._last[method] = self._clock()
        return slept


class RowBudget:
    """Row cap per run."""

    def __init__(self, cap=ROW_CAP):
        self.cap = cap
        self.used = 0
        self.hit = False

    def take(self, n: int) -> int:
        """Return how many of n rows may still be kept; flag the cap when reached."""
        allowed = max(0, min(n, self.cap - self.used))
        self.used += allowed
        if allowed < n or self.used >= self.cap:
            self.hit = True
        return allowed


def _parse_created(value) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def oldest_created(rows) -> str | None:
    """Original `created` string of the oldest parseable row, else None."""
    best: tuple[datetime, str] | None = None
    for row in rows:
        raw = row.get("created") if isinstance(row, dict) else None
        parsed = _parse_created(raw)
        if parsed is not None and (best is None or parsed < best[0]):
            best = (parsed, raw)
    return best[1] if best else None


def summary(
    *,
    windows_run,
    windows_partial,
    rows_read,
    cap,
    cap_hit,
    oldest,
    empty_data_rows,
) -> dict:
    """The "Method and limits" record the report prints."""
    return {
        "windows_run": windows_run,
        "windows_partial": windows_partial,
        "rows_read": rows_read,
        "row_cap": cap,
        "cap_hit": bool(cap_hit),
        "oldest_row": oldest,
        "rows_with_empty_data": empty_data_rows,
    }


def _parse_arg(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="admin_window")
    sub = parser.add_subparsers(dest="command", required=True)
    win = sub.add_parser("windows", help="print window_args for a period")
    win.add_argument("--start", required=True)
    win.add_argument("--end", required=True)
    win.add_argument("--limit", type=int, default=PAGE_LIMIT)
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code or 0)
    try:
        windows = split_windows(_parse_arg(args.start), _parse_arg(args.end))
        out = [window_args(w, limit=args.limit) for w in windows]
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
