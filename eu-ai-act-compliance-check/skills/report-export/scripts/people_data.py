#!/usr/bin/env python3
"""People-data approval helpers for report-export (stdlib only, pure functions).

Computes row and distinct-people counts, strips IP/geolocation fields, checks a
destination folder's members against internal domains, and renders/parses the
approval block the main conversation hands to the report agent.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
import sys
from pathlib import Path
from typing import Any

UNKNOWN_MEMBER = "<unknown member>"
HEADER = "People-data approval (asked of the user after the scan):"
IP_MASK = "[ip removed]"

_FORBIDDEN_EXACT = frozenset({"ip", "lat", "lon", "lng"})
_FORBIDDEN_PARTS = (
    "ipaddr",
    "addr",
    "forwardedfor",
    "geo",
    "location",
    "latitude",
    "longitude",
    "city",
    "country",
    "region",
    "zip",
    "postal",
    "coord",
    "timezone",
)
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_TEXT_EMAIL_RE = re.compile(r"[\w.+\-]+@[\w\-]+(?:\.[\w\-]+)+")
_IPV4_RE = re.compile(r"(?<![\w.])\d{1,3}(?:\.\d{1,3}){3}(?![\w])")
_IPV6_RE = re.compile(r"[0-9A-Fa-f:.]{2,}")


def _norm(key: Any) -> str:
    return re.sub(r"[\s_\-]", "", str(key).lower())


def is_forbidden_key(key: Any) -> bool:
    """True for keys that carry an IP address or geolocation (by normalised name)."""
    n = _norm(key)
    if n in _FORBIDDEN_EXACT:
        return True
    if n.endswith("ip") and not n.endswith("ship"):
        return True
    if "mail" in n:  # emailAddress is a person field, not a network address
        return False
    return any(part in n for part in _FORBIDDEN_PARTS)


def mask_ips(text: str) -> str:
    """Replace IPv4/IPv6 literals inside a string with a fixed marker."""

    def v4(m: re.Match[str]) -> str:
        try:
            ipaddress.IPv4Address(m.group(0))
        except ValueError:
            return m.group(0)
        return IP_MASK

    def v6(m: re.Match[str]) -> str:
        token = m.group(0)
        if ":" not in token:
            return token
        core = token.rstrip(".:") if not token.endswith("::") else token
        try:
            ipaddress.IPv6Address(core)
        except ValueError:
            return token
        return IP_MASK + token[len(core) :]

    return _IPV6_RE.sub(v6, _IPV4_RE.sub(v4, text))


def _strip(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _strip(v) for k, v in value.items() if not is_forbidden_key(k)}
    if isinstance(value, list):
        return [_strip(v) for v in value]
    if isinstance(value, str):
        probe = value.strip()
        if probe[:1] in ("{", "["):
            try:
                parsed = json.loads(probe)
            except ValueError:
                parsed = None
            if isinstance(parsed, (dict, list)):
                return json.dumps(_strip(parsed))
        return mask_ips(value)
    return value


def strip_forbidden(rows: list[dict]) -> list[dict]:
    """Return copies of rows without IP/geolocation keys or IP literals."""
    return [_strip(r) for r in rows]


_ID_KEYS = frozenset(
    {
        "userid",
        "actorid",
        "targetid",
        "recipientid",
        "ownerid",
        "memberid",
        "creatorid",
        "authorid",
    }
)
_NAME_KEYS = frozenset(
    {
        "username",
        "actorname",
        "targetname",
        "recipientname",
        "ownername",
        "membername",
        "creatorname",
        "authorname",
        "displayname",
        "fullname",
        "user",
        "actor",
        "owner",
        "recipient",
        "target",
    }
)


def _dict_tokens(d: dict) -> list[str]:
    emails: list[str] = []
    ids: list[str] = []
    names: list[str] = []
    loose_name: list[str] = []
    for k, v in d.items():
        n = _norm(k)
        if isinstance(v, (dict, list)):
            continue
        if v is None or (isinstance(v, str) and not v.strip()):
            continue
        sv = str(v).strip()
        if (
            isinstance(v, str)
            and _EMAIL_RE.match(sv)
            and ("mail" in n or n in _NAME_KEYS or n in _ID_KEYS)
        ):
            emails.append("email:" + sv.lower())
        elif n in _ID_KEYS:
            ids.append("id:" + sv)
        elif n in _NAME_KEYS and isinstance(v, str):
            names.append("name:" + sv.lower())
        elif n == "name" and isinstance(v, str):
            loose_name.append("name:" + sv.lower())
    toks = emails + ids + names
    if loose_name and toks:
        toks += loose_name
    return toks


def _walk(value: Any, out: list[list[str]]) -> None:
    if isinstance(value, str):
        for m in _TEXT_EMAIL_RE.findall(value):
            out.append(["email:" + m.lower()])
    elif isinstance(value, dict):
        toks = _dict_tokens(value)
        if toks:
            out.append(toks)
        for v in value.values():
            _walk(v, out)
    elif isinstance(value, list):
        for v in value:
            _walk(v, out)


def person_key(row: dict) -> str | None:
    """Primary identity of a row: email, else user id, else name; None if nobody."""
    groups: list[list[str]] = []
    _walk(row, groups)
    toks = [t for g in groups for t in g]
    for prefix in ("email:", "id:", "name:"):
        for t in toks:
            if t.startswith(prefix):
                return t[len(prefix) :]
    return None


def count(rows: list[dict]) -> dict[str, int]:
    """Rows and distinct people, folding id/email/name seen together into one person."""
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for row in rows:
        groups: list[list[str]] = []
        _walk(row, groups)
        for g in groups:
            root = find(g[0])
            for t in g[1:]:
                parent[find(t)] = root
    return {
        "rows": len(rows),
        "distinct_people": len({find(t) for t in list(parent)}),
    }


def _member_email(member: Any) -> str | None:
    if not isinstance(member, dict):
        return None
    user = member.get("user")
    nested = user.get("email") if isinstance(user, dict) else None
    for candidate in (member.get("email"), nested):
        if isinstance(candidate, str) and _EMAIL_RE.match(candidate.strip()):
            return candidate.strip()
    return None


def destination_check(members: Any, internal_domains: set[str]) -> dict:
    """Fail closed: unknown, empty or non-internal sharing makes ok false."""
    domains = {d.strip().lower().lstrip("@") for d in internal_domains}
    domains.discard("")
    if not domains:
        return {
            "members": 0,
            "external": [],
            "ok": False,
            "reason": "no internal domains given",
        }
    if not isinstance(members, list):
        return {
            "members": 0,
            "external": [],
            "ok": False,
            "reason": "member list unreadable",
        }
    if not members:
        return {
            "members": 0,
            "external": [],
            "ok": False,
            "reason": "sharing undeterminable (empty member list)",
        }
    external: list[str] = []
    for m in members:
        email = _member_email(m)
        if email is None:
            external.append(UNKNOWN_MEMBER)
        elif email.rsplit("@", 1)[1].lower() not in domains:
            external.append(email)
    return {
        "members": len(members),
        "external": external,
        "ok": not external,
        "reason": None if not external else "member outside internal domains",
    }


def _yn(flag: bool) -> str:
    return "yes" if flag else "no"


def render_block(
    *,
    rows: int,
    distinct_people: int,
    destination: str,
    members: int,
    domains: list[str],
    row_level_csv: bool,
    approved: bool,
) -> str:
    return "\n".join(
        [
            HEADER,
            f"- rows: {rows}",
            f"- distinct people: {distinct_people}",
            f"- destination: {destination}",
            f"- destination shared with: {members} members, "
            f"all in {', '.join(domains)}",
            f"- row-level csv: {_yn(row_level_csv)}",
            f"- approved: {_yn(approved)}",
        ]
    )


def parse_block(text: str) -> dict | None:
    """Parse the block out of surrounding prose; None when malformed or repeated."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    starts = [i for i, ln in enumerate(lines) if ln.strip() == HEADER]
    if len(starts) != 1:
        return None
    fields: dict[str, str] = {}
    for ln in lines[starts[0] + 1 :]:
        m = re.match(r"^- ([a-z -]+): (.*)$", ln.rstrip())
        if not m:
            break
        fields[m.group(1)] = m.group(2).strip()
    required = (
        "rows",
        "distinct people",
        "destination",
        "destination shared with",
        "row-level csv",
        "approved",
    )
    if any(k not in fields for k in required):
        return None
    try:
        rows = int(fields["rows"])
        people = int(fields["distinct people"])
    except ValueError:
        return None
    flags = (fields["row-level csv"], fields["approved"])
    if any(f not in ("yes", "no") for f in flags):
        return None
    if rows < 0 or people < 0 or not fields["destination"]:
        return None
    return {
        "rows": rows,
        "distinct_people": people,
        "destination": fields["destination"],
        "row_level_csv": flags[0] == "yes",
        "approved": flags[1] == "yes",
    }


def verify(
    approved: dict | None,
    actual_counts: dict,
    destination: str,
    check: dict,
    row_level: bool = False,
) -> list[str]:
    """Reasons to refuse writing; an empty list means the agent may write."""
    if not approved:
        return ["no people-data approval block"]
    reasons: list[str] = []
    if not approved.get("approved"):
        reasons.append("the user did not approve")
    if actual_counts["rows"] > approved["rows"]:
        reasons.append(
            f"rows {actual_counts['rows']} exceed approved {approved['rows']}"
        )
    if actual_counts["distinct_people"] > approved["distinct_people"]:
        reasons.append(
            f"distinct people {actual_counts['distinct_people']} exceed "
            f"approved {approved['distinct_people']}"
        )
    if destination != approved["destination"]:
        reasons.append("destination differs from the approved one")
    if not check.get("ok"):
        reasons.append(
            "destination sharing not confirmed internal: "
            + "; ".join(
                [*(check.get("external") or []), check.get("reason") or "unknown"]
            )
        )
    if row_level and not approved.get("row_level_csv"):
        reasons.append("row-level csv was not approved")
    return reasons


def _load(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load_rows(path: str) -> list[dict]:
    """Rows from a JSON array file or a JSONL file; raises ValueError if neither."""
    text = Path(path).read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except ValueError:
        data = [json.loads(ln) for ln in text.splitlines() if ln.strip()]
    if not isinstance(data, list) or not all(isinstance(r, dict) for r in data):
        raise ValueError("rows must be a JSON array or JSONL of objects")
    return data


def _verify_cli(args: argparse.Namespace) -> int:
    """Exit 0 only when every check passes; any unreadable input fails closed."""
    try:
        rows = _load_rows(args.rows)
        text = Path(args.block).read_text(encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(f"refused: unreadable input ({exc})")
        return 2
    approved = parse_block(text)
    if approved is None:
        print("refused: no people-data approval block")
        return 2
    try:
        members = _load(args.destination_members) if args.destination_members else None
    except (OSError, ValueError):
        members = None
    domains = {d for d in (args.domains or "").split(",") if d.strip()}
    reasons = verify(
        approved,
        count(rows),
        approved["destination"],
        destination_check(members, domains),
        row_level=False,
    )
    actual = count(rows)
    if approved["approved"] and (
        actual["rows"] != approved["rows"]
        or actual["distinct_people"] != approved["distinct_people"]
    ):
        reasons.append("counts do not match the approval block")
    if reasons:
        print("refused: " + "; ".join(dict.fromkeys(reasons)))
        return 2
    print("ok")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--rows", required=True)
    p.add_argument("--members", required=True)
    p.add_argument("--domain", action="append", required=True)
    p.add_argument("--destination", required=True)
    p.add_argument("--row-level-csv", action="store_true")
    p.add_argument(
        "--approved",
        action="store_true",
        help="set only after the user said yes to the question; default is no",
    )
    s = sub.add_parser("strip")
    s.add_argument("--in", dest="src", required=True)
    s.add_argument("--out", required=True)
    c = sub.add_parser("count")
    c.add_argument("--rows", required=True)
    v = sub.add_parser("verify")
    v.add_argument("--block", required=True)
    v.add_argument("--rows", required=True)
    v.add_argument("--destination-members")
    v.add_argument("--domains")
    args = ap.parse_args(argv)
    if args.cmd == "count":
        try:
            print(json.dumps(count(_load_rows(args.rows))))
        except (OSError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        return 0
    if args.cmd == "verify":
        return _verify_cli(args)
    if args.cmd == "strip":
        clean = strip_forbidden(_load(args.src))
        Path(args.out).write_text(
            json.dumps(clean, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        return 0
    if not args.destination.strip():
        print("error: --destination must not be empty", file=sys.stderr)
        return 2
    counts = count(_load(args.rows))
    check = destination_check(_load(args.members), set(args.domain))
    block = (
        render_block(
            rows=counts["rows"],
            distinct_people=counts["distinct_people"],
            destination=args.destination,
            members=check["members"],
            domains=sorted({d.strip().lower() for d in args.domain}),
            row_level_csv=args.row_level_csv,
            approved=args.approved,
        )
        if check["ok"]
        else None
    )
    print(
        json.dumps(
            {"counts": counts, "destination_check": check, "block": block}, indent=2
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
