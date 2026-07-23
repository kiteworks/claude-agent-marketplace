#!/usr/bin/env python3
"""Built-in sensitive-pattern presets for term-sweep's content deep-scan,
plus an optional deterministic custom-regex mode for user-supplied patterns.

Checks extracted file text against a small set of high-confidence PII/secret
shapes, using real checksum validation (Luhn for card numbers, mod-97 for
IBAN, the Dutch elfproef for BSN) rather than naive regex alone, to keep
false positives low on ordinary business documents full of unrelated
numbers (scores, IDs, weights, etc.).

Every built-in category also gets a second, independent signal: whether a
relevant keyword (e.g. "BSN", "IBAN", "social security") appears within a
small window of characters around the match. Checksum validation catches
numbers that are shaped right; context catches numbers that are shaped
right AND appear where you'd actually expect that kind of data. Neither
alone is proof -- together they're a much stronger signal than either.

Custom-regex mode (2026-07-13): a user can supply their own regex(es) --
e.g. an internal employee-ID shape like "EMP-\\d{6}" -- and have them
evaluated the same deterministic way, instead of the agent having to read
raw extracted text into its own reasoning to "look for" the pattern, which
would defeat the whole point of keeping sensitive content out of the
conversation. A bad regex is reported as an error per-pattern, never
crashes the run. Text is length-capped before evaluation and each pattern
gets a wall-clock timeout guard, since an arbitrary user-supplied regex can
pathologically backtrack (ReDoS) on adversarial input.

Tag-based category system (2026-07-15, revised): every built-in category
carries a `region` (e.g. "US", "NL", or None if not tied to any one
country) and a `type` (e.g. "national_id", "financial", "credential") in
CATEGORY_SPECS, alongside its regex/validator/context-keywords. ALL
built-in categories run by default -- there is no opt-in/opt-out gate
based on region. This is a deliberate reversal of an earlier version of
this design that made region-tied categories (ssn_shaped, bsn_shaped)
off-by-default: that made the scanner do less out of the box for no real
benefit. The actual complaint it was responding to was that a chat
narration naming every category (including country-specific ones) up
front reads as noisy, not that the categories themselves shouldn't run --
so the fix belongs in how a caller *presents* results (name only the
categories that got hits; keep the full per-category breakdown, including
zero-hit ones, in the exported report rather than reciting it in chat),
not in which categories execute. See term-sweep/SKILL.md.

The tag system exists so this can scale past 5 categories to dozens more
without the selector interface changing: --categories can select by exact
category key, by `region:<value>`, by `type:<value>`, any comma-mixed
combination of those, or `all` (the default). Adding a new built-in
category later is purely additive -- one new CATEGORY_SPECS entry with its
own pattern/validator/tags, no change to scan() or the CLI.

Usage:
  python3 pii_patterns.py <path-to-extracted-text-file>
  python3 pii_patterns.py <path-to-extracted-text-file> <path-to-custom-patterns.json>
  python3 pii_patterns.py <path-to-extracted-text-file> --categories=<selector>
  python3 pii_patterns.py <path-to-extracted-text-file> --categories=<selector> <path-to-custom-patterns.json>

  --categories, if given, may appear anywhere in argv. Omit it (or pass
  --categories=all) to run every built-in category -- the default. A
  <selector> is a comma-separated list where each item is one of:
    - an exact category key, e.g. bsn_shaped
    - region:<value>, e.g. region:US -- every category tagged that region
    - type:<value>, e.g. type:financial -- every category tagged that type
  Items are unioned together, e.g.
    --categories=region:US,region:NL,aws_access_key
  runs every US- and NL-tagged category plus aws_access_key specifically.
  An unrecognized category key, region, or type is a hard error (exit 1,
  clear message naming the valid options) rather than a silent no-op.

  custom-patterns.json is a JSON array of objects:
    [{"label": "employee_id", "regex": "EMP-\\d{6}", "context_keywords": ["employee id"]}, ...]
  "context_keywords" is optional.

Prints ONLY a JSON object of counts per category/label, split into the raw
match count and the context-confirmed subset of it, e.g.
{"ssn_shaped": {"valid": 2, "context_confirmed": 1},
 "bsn_shaped": {"skipped": true, "region": "NL", "type": "national_id", "reason": "..."},
 "credit_card_luhn_valid": {"valid": 0, "context_confirmed": 0}, ...,
 "custom": {"employee_id": {"valid": 3, "context_confirmed": 3, "error": null}}}

Never prints the matched values themselves -- per this plugin's privacy rule
(term-sweep / content-extract), only counts and categories are safe to surface.
"""
import json
import re
import signal
import sys

SSN_SHAPED = re.compile(r"\b(?!000|666|9\d{2})\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b")
BSN_SHAPED = re.compile(r"\b\d{9}\b")
CARD_CANDIDATE = re.compile(r"\b(?:\d[ -]?){13,19}\b")
IBAN_CANDIDATE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")
AWS_ACCESS_KEY = re.compile(r"\bAKIA[0-9A-Z]{16}\b")


def luhn_valid(number: str) -> bool:
    digits = [int(d) for d in number]
    checksum = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


def iban_valid(candidate: str) -> bool:
    c = candidate.replace(" ", "").upper()
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{11,30}", c):
        return False
    rearranged = c[4:] + c[:4]
    numeric = "".join(str(int(ch, 36)) if ch.isalpha() else ch for ch in rearranged)
    try:
        return int(numeric) % 97 == 1
    except ValueError:
        return False


def bsn_valid(candidate: str) -> bool:
    """Dutch elfproef: weights 9,8,7,6,5,4,3,2,-1 over the 9 digits, sum % 11 == 0.
    All-zero excluded explicitly -- it passes the arithmetic but was never issued."""
    if len(candidate) != 9 or not candidate.isdigit():
        return False
    if candidate == "000000000":
        return False
    weights = [9, 8, 7, 6, 5, 4, 3, 2, -1]
    total = sum(int(d) * w for d, w in zip(candidate, weights))
    return total % 11 == 0


def _card_valid(raw: str) -> bool:
    digits = re.sub(r"[ -]", "", raw)
    return 13 <= len(digits) <= 19 and luhn_valid(digits)


# Single source of truth: every built-in category's matching logic AND its
# selector tags live together. Adding category #6 (or #56) is one new entry
# here -- scan() and the CLI never need to change.
#
# validator=None means "every regex match counts" (the regex itself already
# encodes the validity rule, e.g. SSN_SHAPED's negative lookaheads, or
# AWS_ACCESS_KEY's exact prefix+length shape). Otherwise validator(raw_match)
# -> bool does real checksum/shape validation beyond what the regex alone
# can express.
CATEGORY_SPECS = {
    "ssn_shaped": {
        "label": "US Social Security Number shape (area/group/serial validity rules applied, not government-verified)",
        "region": "US",
        "type": "national_id",
        "pattern": SSN_SHAPED,
        "validator": None,
        "context_keywords": ["ssn", "social security"],
    },
    "bsn_shaped": {
        "label": "Dutch BSN (Burgerservicenummer) shape, elfproef (11-test) checksum valid",
        "region": "NL",
        "type": "national_id",
        "pattern": BSN_SHAPED,
        "validator": bsn_valid,
        "context_keywords": ["bsn", "burgerservicenummer", "sofinummer"],
    },
    "credit_card_luhn_valid": {
        "label": "13-19 digit number, Luhn checksum valid (real card-number validation, not just digit count)",
        "region": None,
        "type": "financial",
        "pattern": CARD_CANDIDATE,
        "validator": _card_valid,
        "context_keywords": ["credit card", "card number", "cvv", "visa", "mastercard", "amex", "discover"],
    },
    "iban_checksum_valid": {
        "label": "IBAN shape, mod-97 checksum valid (real IBAN validation)",
        "region": None,
        "type": "financial",
        "pattern": IBAN_CANDIDATE,
        "validator": iban_valid,
        "context_keywords": ["iban", "bank account", "rekeningnummer", "account number"],
    },
    "aws_access_key": {
        "label": "AWS access key ID shape (AKIA prefix + 16 chars) -- a leaked-credential signal, not classic PII",
        "region": None,
        "type": "credential",
        "pattern": AWS_ACCESS_KEY,
        "validator": None,
        "context_keywords": ["aws", "access key", "secret key"],
    },
}

DEFAULT_ENABLED_CATEGORIES = frozenset(CATEGORY_SPECS)

# Keywords checked within CONTEXT_WINDOW characters of a match, case-insensitive.
# A second, independent confirmation signal on top of checksum/shape validity --
# not required to count a hit at all, but raises confidence a lot when present.
CONTEXT_WINDOW = 60

# Safety caps for custom user-supplied regexes -- built-in patterns above are
# fixed and already known-safe, these caps only apply to the custom mode.
CUSTOM_MAX_TEXT_CHARS = 2_000_000
CUSTOM_REGEX_TIMEOUT_SECONDS = 3


def _known_regions():
    return sorted({v["region"] for v in CATEGORY_SPECS.values() if v["region"]})


def _known_types():
    return sorted({v["type"] for v in CATEGORY_SPECS.values()})


def resolve_categories(arg=None):
    """Turn a --categories selector (None, 'all', or a comma-separated list
    of exact keys / region:<value> / type:<value>) into the set of category
    keys to actually run. Items are unioned. Raises ValueError with a
    plain-language message (naming the valid options) on any unrecognized
    category key, region, or type -- a typo should never silently no-op."""
    if arg is None or arg.strip().lower() == "all":
        return DEFAULT_ENABLED_CATEGORIES

    selected = set()
    errors = []
    for token in (t.strip() for t in arg.split(",") if t.strip()):
        lowered = token.lower()
        if lowered.startswith("region:"):
            region = token.split(":", 1)[1].strip()
            matches = {k for k, v in CATEGORY_SPECS.items() if v["region"] == region}
            if not matches:
                errors.append(
                    "unknown region '%s' -- known regions: %s" % (region, ", ".join(_known_regions()))
                )
            selected |= matches
        elif lowered.startswith("type:"):
            type_ = token.split(":", 1)[1].strip()
            matches = {k for k, v in CATEGORY_SPECS.items() if v["type"] == type_}
            if not matches:
                errors.append(
                    "unknown type '%s' -- known types: %s" % (type_, ", ".join(_known_types()))
                )
            selected |= matches
        elif token in CATEGORY_SPECS:
            selected.add(token)
        else:
            errors.append(
                "unknown category '%s' -- valid categories: %s, or region:<region>/type:<type>/all"
                % (token, ", ".join(sorted(CATEGORY_SPECS)))
            )

    if errors:
        raise ValueError("; ".join(errors))
    return frozenset(selected)


def _skip_entry(category: str) -> dict:
    spec = CATEGORY_SPECS[category]
    return {
        "skipped": True,
        "region": spec["region"],
        "type": spec["type"],
        "reason": "not included in this scan's --categories selection",
    }


class _RegexTimeout(Exception):
    pass


def _alarm_handler(signum, frame):
    raise _RegexTimeout()


def _finditer_with_timeout(compiled, text, timeout_seconds):
    """Best-effort wall-clock guard against catastrophic backtracking in a
    user-supplied regex. SIGALRM is Unix-only and process-wide (not safe to
    nest), which is fine here since this script runs each pattern serially
    in its own process invocation. Falls back to no timeout if SIGALRM isn't
    available (e.g. non-Unix) rather than failing the whole run."""
    has_alarm = hasattr(signal, "SIGALRM")
    if has_alarm:
        old_handler = signal.signal(signal.SIGALRM, _alarm_handler)
        signal.alarm(timeout_seconds)
    try:
        return list(compiled.finditer(text))
    finally:
        if has_alarm:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)


def context_hit(text: str, start: int, end: int, keywords) -> bool:
    window = text[max(0, start - CONTEXT_WINDOW): end + CONTEXT_WINDOW].lower()
    return any(kw.lower() in window for kw in keywords)


def scan(text: str, enabled=None) -> dict:
    """enabled: iterable of category keys to actually run (see
    resolve_categories). Defaults to every category in CATEGORY_SPECS when
    not given -- all built-in categories run unless the caller narrows
    scope explicitly. A category not in `enabled` still appears in the
    result, as a {"skipped": true, ...} entry -- never just missing."""
    enabled = frozenset(enabled) if enabled is not None else DEFAULT_ENABLED_CATEGORIES
    result = {}
    for key, spec in CATEGORY_SPECS.items():
        if key not in enabled:
            result[key] = _skip_entry(key)
            continue
        pattern = spec["pattern"]
        validator = spec.get("validator")
        keywords = spec.get("context_keywords") or []
        valid = context = 0
        for m in pattern.finditer(text):
            raw = m.group()
            if validator is None or validator(raw):
                valid += 1
                if keywords and context_hit(text, m.start(), m.end(), keywords):
                    context += 1
        result[key] = {"valid": valid, "context_confirmed": context}
    return result


def scan_custom(text: str, patterns: list) -> dict:
    """patterns: list of {"label": str, "regex": str, "context_keywords": [str, ...]?}.
    Returns {label: {"valid": int, "context_confirmed": int, "error": str|None}}.
    A pattern that fails to compile, times out, or is otherwise invalid gets
    valid=0, context_confirmed=0, and a plain-language error -- it never
    crashes the rest of the run."""
    result = {}
    truncated = len(text) > CUSTOM_MAX_TEXT_CHARS
    scan_text = text[:CUSTOM_MAX_TEXT_CHARS] if truncated else text

    for p in patterns:
        label = p.get("label", "unnamed_pattern")
        pattern_str = p.get("regex", "")
        keywords = p.get("context_keywords") or []

        try:
            compiled = re.compile(pattern_str)
        except re.error as e:
            result[label] = {"valid": 0, "context_confirmed": 0, "error": "invalid regex: " + str(e)}
            continue

        try:
            matches = _finditer_with_timeout(compiled, scan_text, CUSTOM_REGEX_TIMEOUT_SECONDS)
        except _RegexTimeout:
            result[label] = {
                "valid": 0,
                "context_confirmed": 0,
                "error": "regex timed out after " + str(CUSTOM_REGEX_TIMEOUT_SECONDS) + "s -- likely catastrophic backtracking, simplify the pattern",
            }
            continue

        valid = len(matches)
        context_confirmed = 0
        if keywords:
            for m in matches:
                if context_hit(scan_text, m.start(), m.end(), keywords):
                    context_confirmed += 1

        entry = {"valid": valid, "context_confirmed": context_confirmed, "error": None}
        if truncated:
            entry["note"] = "input text truncated to " + str(CUSTOM_MAX_TEXT_CHARS) + " chars before evaluation"
        result[label] = entry

    return result


if __name__ == "__main__":
    # --categories=<...> may appear anywhere in argv; pull it out first so the
    # remaining positional args (text file, optional custom-patterns.json)
    # parse exactly as before.
    raw_args = sys.argv[1:]
    categories_arg = None
    positional = []
    for a in raw_args:
        if a.startswith("--categories="):
            categories_arg = a[len("--categories="):]
        else:
            positional.append(a)

    if len(positional) not in (1, 2):
        print(
            "usage: pii_patterns.py <path-to-extracted-text-file> [--categories=<selector>] [path-to-custom-patterns.json]",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        enabled_categories = resolve_categories(categories_arg)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    with open(positional[0], "r", errors="ignore") as f:
        content = f.read()

    output = scan(content, enabled=enabled_categories)

    if len(positional) == 2:
        with open(positional[1], "r", errors="ignore") as f:
            custom_patterns = json.load(f)
        if not isinstance(custom_patterns, list):
            print("custom-patterns.json must be a JSON array", file=sys.stderr)
            sys.exit(1)
        output["custom"] = scan_custom(content, custom_patterns)

    print(json.dumps(output))
