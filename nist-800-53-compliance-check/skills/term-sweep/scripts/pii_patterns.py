#!/usr/bin/env python3
"""Built-in sensitive-pattern presets for term-sweep's content deep-scan,
plus an optional deterministic custom-regex mode for user-supplied patterns.

Checks extracted file text against a small set of high-confidence PII/secret
shapes, using real checksum validation (Luhn for card numbers, mod-97 for
IBAN, the Dutch elfproef for BSN, Verhoeff for Aadhaar, mod-11 for CPF/CNPJ)
rather than naive regex alone, to keep false positives low on ordinary
business documents full of unrelated numbers (scores, IDs, weights, etc.).

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
CATEGORY_SPECS, alongside its regex/validator/context-keywords. The general
categories (no `frameworks` tag) run by default -- there is no opt-in/opt-out
gate based on region. This is a deliberate reversal of an earlier version of
this design that made region-tied categories (ssn_shaped, bsn_shaped)
off-by-default: that made the scanner do less out of the box for no real
benefit. The actual complaint it was responding to was that a chat
narration naming every category (including country-specific ones) up
front reads as noisy, not that the categories themselves shouldn't run --
so the fix belongs in how a caller *presents* results (name only the
categories that got hits; keep the full per-category breakdown, including
zero-hit ones, in the exported report rather than reciting it in chat),
not in which categories execute. See term-sweep/SKILL.md.

Framework-gated categories (2026-09-24, #274): Aadhaar, CPF, CNPJ,
Vietnamese CCCD, email and lat/lon pairs are only meaningful signals under
specific privacy frameworks (an email address in a CMMC scan is noise, in a
GDPR scan it is personal data). Plaintext credential assignments (#291) are
the security-side counterpart: gated to soc2, cis-controls, iso27001,
nist-800-53 and sensitive-content-scanner, kept out of the privacy
frameworks. HIPAA identifiers (#292) -- NPI, medical record number,
health-plan member ID -- are gated to hipaa; SSN stays general. Each
carries a `frameworks` tuple and runs only when the caller passes
--framework=<slug> for one of them, or selects it explicitly by
key/region/type. Without either it is reported as skipped,
never silently missing.

The tag system exists so this can scale to dozens of categories without the
selector interface changing: --categories can select by exact category key,
by `region:<value>`, by `type:<value>`, any comma-mixed combination of
those, or `all` (the default: every category without a `frameworks` gate).
Adding a new built-in category later is purely additive -- one new
CATEGORY_SPECS entry with its own pattern/validator/tags, no change to
scan() or the CLI.

Usage:
  python3 pii_patterns.py <path-to-extracted-text-file>
  python3 pii_patterns.py <path-to-extracted-text-file> <path-to-custom-patterns.json>
  python3 pii_patterns.py <path-to-extracted-text-file> --categories=<selector>
  python3 pii_patterns.py <path-to-extracted-text-file> --framework=<slug>
  python3 pii_patterns.py <path-to-extracted-text-file> --categories=<selector> <path-to-custom-patterns.json>
  python3 pii_patterns.py --help

  --categories and --framework, if given, may appear anywhere in argv.
  Omit --categories (or pass --categories=all) to run every general
  built-in category -- the default. A <selector> is a comma-separated list
  where each item is one of:
    - an exact category key, e.g. bsn_shaped
    - region:<value>, e.g. region:US -- every category tagged that region
    - type:<value>, e.g. type:financial -- every category tagged that type
  Items are unioned together, e.g.
    --categories=region:US,region:NL,aws_access_key
  runs every US- and NL-tagged category plus aws_access_key specifically.
  --framework=<slug> (e.g. dpdpa, lgpd, vn-pdpl, ccpa, gdpr, iso27701,
  soc2, cis-controls, iso27001, nist-800-53, sensitive-content-scanner,
  hipaa) adds
  that framework's gated presets on top of the --categories selection.
  An unrecognized category key, region, type or framework is a hard error
  (exit 1, clear message naming the valid options) rather than a silent
  no-op.

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

import argparse
import json
import re
import signal
import sys

SSN_SHAPED = re.compile(r"\b(?!000|666|9\d{2})\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b")
BSN_SHAPED = re.compile(r"\b\d{9}\b")
CARD_CANDIDATE = re.compile(r"\b(?:\d[ -]?){13,19}\b")
IBAN_CANDIDATE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")
# Country code + two check digits, not glued to a preceding letter/digit.
# find_iban_spans() walks exactly the country's registered IBAN length from
# here, so an IBAN glued to the next field ("NL91ABNA0417164300BIC") or
# printed in groups of four ("NL91 ABNA 0417 1643 00") is still found.
IBAN_START = re.compile(r"(?<![A-Za-z0-9])([A-Z]{2})\d{2}")
# May sit between two printed groups of four (at most 3 in a row).
IBAN_SEPARATORS = " \u00a0\t\r\n-."
MAX_IBAN_SEPARATOR_RUN = 3

# Total IBAN length per country, from the SWIFT IBAN registry.
IBAN_LENGTHS = {
    "AD": 24, "AE": 23, "AL": 28, "AT": 20, "AZ": 28, "BA": 20, "BE": 16,
    "BG": 22, "BH": 22, "BR": 29, "BY": 28, "CH": 21, "CR": 22, "CY": 28,
    "CZ": 24, "DE": 22, "DK": 18, "DO": 28, "EE": 20, "EG": 29, "ES": 24,
    "FI": 18, "FO": 18, "FR": 27, "GB": 22, "GE": 22, "GI": 23, "GL": 18,
    "GR": 27, "GT": 28, "HR": 21, "HU": 28, "IE": 22, "IL": 23, "IQ": 23,
    "IS": 26, "IT": 27, "JO": 30, "KW": 30, "KZ": 20, "LB": 28, "LC": 32,
    "LI": 21, "LT": 20, "LU": 20, "LV": 21, "MC": 27, "MD": 24, "ME": 22,
    "MK": 19, "MR": 27, "MT": 31, "MU": 30, "NL": 18, "NO": 15, "PK": 24,
    "PL": 28, "PS": 29, "PT": 25, "QA": 29, "RO": 24, "RS": 22, "SA": 24,
    "SC": 31, "SE": 24, "SI": 19, "SK": 24, "SM": 27, "ST": 25, "SV": 28,
    "TL": 23, "TN": 24, "TR": 26, "UA": 29, "VA": 22, "VG": 24, "XK": 20,
    "BI": 27, "DJ": 27, "FK": 18, "HN": 28, "LY": 25, "MN": 20, "NI": 28,
    "OM": 23, "RU": 33, "SD": 18, "SO": 23, "YE": 30,
}  # fmt: skip
AWS_ACCESS_KEY = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
# A plaintext credential assignment: a password/secret/token/API-key name,
# then "=", ":" or ":=", then a value. The name may carry a prefix joined by
# "_" or "-" (DB_PASSWORD, client_secret, x-api-key, AWS_SECRET_ACCESS_KEY)
# and a closing quote (JSON keys), but must end there: max_tokens,
# token_count and password_hint are not credential names. An unquoted value
# is one run of non-space characters that ends the line or a field
# (& ; , # or //), so prose such as "Password: must be at least 12
# characters" does not match; the trade-off is that "password = x and more"
# is not counted either.
CREDENTIAL_ASSIGNMENT = re.compile(
    r"(?<![A-Za-z0-9])(?:[A-Za-z0-9]{1,32}[_-]){0,4}"
    r"(?:password|passwd|pwd|secret(?:[_-]?(?:access[_-]?)?key)?"
    r"|token|api[_-]?key)"
    r"""["']?[ \t]*(?::?=|:)[ \t]*"""
    r"""(?:"(?P<dq>[^"\r\n]*)"|'(?P<sq>[^'\r\n]*)'"""
    r"""|(?P<bare>[^\s"'=][^\s&;,]*)(?=[ \t]*(?:$|[\r&;,#]|//)))""",
    re.IGNORECASE | re.MULTILINE,
)
# An unquoted value that reads as a word, an identifier, a code reference or
# a path rather than a secret: "Secret: yes", "password=stored_hash",
# "api_key = config.api_key", "password = getpass()", "PWD=/home/rick", or a
# short number ("token: 17"). A quoted value is never discarded this way.
_CREDENTIAL_NOT_A_SECRET = re.compile(
    r"[A-Za-z][a-z]*|[a-z_]+|[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+(?:\(.*\))?"
    r"|[A-Za-z_][\w.]*\(.*\)|[/~].*|\d{1,5}"
)
# A credential value that is a placeholder, not a secret: a template
# variable, a masked or angle-bracketed stand-in, or a stock word. $VAR only
# in its environment-variable form (upper case, or a positional $1), so a
# real password such as "$ecret99" still counts.
_CREDENTIAL_PLACEHOLDER = re.compile(
    r"<[^<>]*>|\[[^\[\]]*\]|\$\{[^{}]*\}|(?-i:\$[A-Z_][A-Z0-9_]*)|\$\d+"
    r"|\{+[^{}]*\}+|%[A-Za-z_]\w*%|%\(\w+\)s|([*x.#_-])\1*|\*{3,}\w{0,4}"
    r"|your\W?\w*",
    re.IGNORECASE,
)
_CREDENTIAL_PLACEHOLDER_WORDS = frozenset(
    "changeme change_me change-me changeit redacted removed hidden masked "
    "todo tbd fixme none null nil empty unset n/a na placeholder example "
    "sample dummy required optional true false string str password passwd "
    "pwd secret token".split()
)
# Aadhaar: 12 digits, first digit 2-9 (UIDAI never issues 0 or 1), printed
# as 4-4-4 with one consistent separator (space, hyphen, or none).
# The lookarounds also refuse a digit group joined by a separator on either
# side, so 12 digits inside a space-grouped 16-digit card number never match.
AADHAAR_CANDIDATE = re.compile(
    r"(?<![\d-])(?<!\d[ -])[2-9]\d{3}([ -]?)\d{4}\1\d{4}(?![ -]?\d)(?!-)"
)
# CPF: 000.000.000-00, dots and dash optional.
# A trailing period is allowed (end of sentence) unless a digit follows it.
CPF_CANDIDATE = re.compile(r"(?<![\d./-])\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?![\d/-]|\.\d)")
# CNPJ: 00.000.000/0000-00, punctuation optional for the all-digit form. The
# alphanumeric CNPJ (Receita Federal, IN RFB 2.229/2024, issued from July
# 2026) is only matched in its punctuated form, so ordinary 14-character
# alphanumeric codes are not fed to the checksum.
CNPJ_CANDIDATE = re.compile(
    r"(?<![\w./-])(?:\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}"
    r"|[0-9A-Z]{2}\.[0-9A-Z]{3}\.[0-9A-Z]{3}/[0-9A-Z]{4}-\d{2})(?![\w/-]|\.\w)"
)
# Vietnamese CCCD (citizen identity card) personal ID number: 12 digits.
CCCD_CANDIDATE = re.compile(r"(?<![\d-])\d{12}(?![\d-])")
EMAIL_CANDIDATE = re.compile(
    r"(?<![\w.%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)*\.[A-Za-z]{2,}\b"
)
# A decimal-degree lat/lon pair with at least 3 decimals on both halves.
# 3 decimals is ~110 m, well inside the CCPA "precise geolocation" radius of
# 1,850 feet (Cal. Civ. Code 1798.140(w)); 2 decimals (~1.1 km) is not.
# Two alternatives, latitude first in both:
#   - labelled: key/value, query-string or JSON keys, e.g. "lat: 52.370,
#     lon: 4.895", "latitude=52.370 longitude=4.895", '"lat": 52.370,
#     "lng": 4.895' (values may be quoted);
#   - bare: "52.370, 4.895", which also covers a CSV row whose lat and lon
#     columns sit next to each other under a lat,lon header.
# One finditer pass over the alternation never counts a pair twice: the
# labelled match consumes both numbers, so the bare branch cannot reuse them.
_LATLON_NUM_LAT = r"-?\d{1,2}\.\d{3,}(?!\d|\.\d)"
_LATLON_NUM_LON = r"-?\d{1,3}\.\d{3,}(?!\d|\.\d)"
_LATLON_KV = r"""["']?\s*[:=]\s*["']?"""
LATLON_CANDIDATE = re.compile(
    r"(?<![A-Za-z0-9_])(?i:lat(?:itude)?)"
    + _LATLON_KV
    + _LATLON_NUM_LAT
    # One optional separator, one whitespace run: two adjacent \s* here would
    # backtrack quadratically on a long whitespace run after a lat value.
    + r"""["']?(?:\s*[,;&])?\s*["']?"""
    + r"(?i:lon(?:g(?:itude)?)?|lng)"
    + _LATLON_KV
    + _LATLON_NUM_LON
    + r"|(?<![\d.])"
    + _LATLON_NUM_LAT
    + r"\s*,\s*"
    + _LATLON_NUM_LON
)
_DECIMAL = re.compile(r"-?\d+\.\d+")

# HIPAA identifiers (#292). An NPI is 10 digits starting with 1 or 2; its
# check digit is a Luhn digit computed over the number prefixed with 80840.
# A hyphen after a label ("NPI-1234567893") is fine, one after a digit is not.
NPI_CANDIDATE = re.compile(r"(?<!\d)(?<!\d-)[12]\d{9}(?![\d-])")
# A medical record number or a health-plan member ID has no fixed shape or
# checksum, so only a value directly after its label counts ("MRN: 00482131",
# "Member ID: XKV123456789"). A number of that shape with no label, or a
# label with prose after it, never matches. The separator is one whitespace
# run, then at most "#:", ":", "#" or "=", then one whitespace run: two
# adjacent [ \t]* would backtrack quadratically on a long run of spaces.
_ID_SEPARATOR = r"[ \t]*(?:\([A-Za-z]{2,5}\)[ \t]*)?(?:(?:#:|[:#=])[ \t]*)?"
MRN_LABELLED = re.compile(
    r"(?i:\bmrn\b|\bmedical[ \t]+record(?:[ \t]+(?:number|no\.?))?"
    r"|\bpatient[ \t]+(?:id|identifier|number|no\.?))"
    + _ID_SEPARATOR
    + r"(?:[A-Za-z]{1,3}-?)?\d{5,12}(?![\w-])"
)
# "Policy" and "member" alone are too generic outside healthcare (an ISMS
# "Policy ID: POL-0012"), so a policy needs an insurance qualifier. An ISO
# date after the label is not an ID.
MEMBER_ID_LABELLED = re.compile(
    r"(?i:\b(?:health[ \t]+plan|health[ \t]+insurance|insurance(?:[ \t]+policy)?"
    r"|member|subscriber|beneficiary|medicare|medicaid)"
    r"[ \t]+(?:id|identifier|number|no\.?))"
    + _ID_SEPARATOR
    + r"(?!\d{4}-\d{2}-\d{2}(?![\w-]))"
    + r"(?=[A-Za-z0-9-]*\d)[A-Za-z0-9][A-Za-z0-9-]{4,18}[A-Za-z0-9](?![\w-])"
)
_HEALTH_CONTEXT = [
    "patient",
    "hospital",
    "clinic",
    "medical",
    "health",
    "diagnosis",
    "admission",
    "discharge",
    "physician",
    "provider",
    "insurance",
    "claim",
    "phi",
]

# Vietnamese province/city codes that form the first 3 digits of a CCCD
# number. Source: Circular 07/2016/TT-BCA (Thong tu 07/2016/TT-BCA), Annex I
# (Phu luc I), Ministry of Public Security of Viet Nam, as updated by
# Circular 16/2024/TT-BCA -- the 63 province-level codes 001 (Ha Noi) to
# 096 (Ca Mau). The 2025 province mergers kept existing numbers valid, so the
# 63 codes stay the complete set for numbers already issued. Codes outside
# this list (e.g. country codes for births registered abroad) are
# deliberately not accepted: only documented province codes count.
VN_PROVINCE_CODES = frozenset(
    "001 002 004 006 008 010 011 012 014 015 017 019 020 022 024 025 026 027 "
    "030 031 033 034 035 036 037 038 040 042 044 045 046 048 049 051 052 054 "
    "056 058 060 062 064 066 067 068 070 072 074 075 077 079 080 082 083 084 "
    "086 087 089 091 092 093 094 095 096".split()
)

# Verhoeff dihedral-group tables (Verhoeff 1969), as used by UIDAI.
_VERHOEFF_D = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
    (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
    (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
    (4, 0, 1, 2, 3, 9, 5, 6, 7, 8),
    (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
    (6, 5, 9, 8, 7, 1, 0, 4, 3, 2),
    (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
    (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
    (9, 8, 7, 6, 5, 4, 3, 2, 1, 0),
)
_VERHOEFF_P = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
    (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
    (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
    (9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
    (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
    (2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
    (7, 0, 4, 6, 9, 1, 3, 2, 5, 8),
)


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


def iban_mod97_valid(compact: str) -> bool:
    """ISO 13616 mod-97 check on a compact IBAN (letters count as 10..35)."""
    rearranged = compact[4:] + compact[:4]
    try:
        numeric = "".join(str(int(ch, 36)) for ch in rearranged)
    except ValueError:
        return False
    return int(numeric) % 97 == 1


def _iban_prefix_end(text: str, start: int, length: int):
    """Index just past `length` IBAN characters from `start`, or None.

    Separators may only sit between groups of four, as IBANs are printed.
    Whatever follows is not inspected: the mod-97 check decides.
    """
    count = 0
    i = start
    n = len(text)
    while count < length:
        if i >= n:
            return None
        ch = text[i]
        if ch.isascii() and ch.isalnum():
            count += 1
            i += 1
            continue
        if ch not in IBAN_SEPARATORS or count % 4:
            return None
        j = i
        while j < n and text[j] in IBAN_SEPARATORS:
            j += 1
        if j - i > MAX_IBAN_SEPARATOR_RUN:
            return None
        i = j
    return i


def find_iban_spans(text: str) -> list:
    """(start, end, candidate) for every IBAN candidate in `text`, in order.

    Registered countries: exactly the country's IBAN length, compact or in
    printed groups, glued to further characters or not, kept only when
    mod-97 valid. Plus every IBAN_CANDIDATE match not overlapping one of
    those (e.g. a country missing from IBAN_LENGTHS), which the category's
    validator then checks as before.
    """
    spans = []
    pos = 0
    for m in IBAN_START.finditer(text):
        if m.start() < pos:
            continue
        length = IBAN_LENGTHS.get(m.group(1))
        if length is None:
            continue
        end = _iban_prefix_end(text, m.start(), length)
        if end is None:
            continue
        compact = "".join(
            ch for ch in text[m.start() : end] if ch not in IBAN_SEPARATORS
        ).upper()
        if not iban_mod97_valid(compact):
            continue
        spans.append((m.start(), end, compact))
        pos = end
    found = list(spans)
    for m in IBAN_CANDIDATE.finditer(text):
        if any(s < m.end() and m.start() < e for s, e, _ in found):
            continue
        spans.append((m.start(), m.end(), m.group()))
    spans.sort()
    return spans


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


def verhoeff_valid(number: str) -> bool:
    """Verhoeff check over a digit string whose last digit is the check digit."""
    if not number.isdigit():
        return False
    c = 0
    for i, ch in enumerate(reversed(number)):
        c = _VERHOEFF_D[c][_VERHOEFF_P[i % 8][int(ch)]]
    return c == 0


def aadhaar_valid(candidate: str) -> bool:
    """India Aadhaar: 12 digits, first digit 2-9, Verhoeff check digit last."""
    digits = re.sub(r"[ -]", "", candidate)
    if len(digits) != 12 or not digits.isdigit() or digits[0] in "01":
        return False
    return verhoeff_valid(digits)


def _mod11_check_digit(values, weights) -> int:
    remainder = sum(v * w for v, w in zip(values, weights)) % 11
    return 0 if remainder < 2 else 11 - remainder


def cpf_valid(candidate: str) -> bool:
    """Brazil CPF: 9 base digits + 2 mod-11 check digits (weights 10..2, then
    11..2). A repeated single digit (111.111.111-11) passes the arithmetic
    but is never issued, so it is rejected."""
    digits = re.sub(r"[.-]", "", candidate)
    if len(digits) != 11 or not digits.isdigit() or len(set(digits)) == 1:
        return False
    values = [int(d) for d in digits]
    first = _mod11_check_digit(values[:9], range(10, 1, -1))
    second = _mod11_check_digit(values[:10], range(11, 1, -1))
    return values[9] == first and values[10] == second


def cnpj_valid(candidate: str) -> bool:
    """Brazil CNPJ: 12 base characters + 2 mod-11 check digits (weights
    5,4,3,2,9..2 then 6,5,4,3,2,9..2). Base characters may be letters in the
    alphanumeric CNPJ; each counts as its ASCII code minus 48, which leaves
    digits at their face value (IN RFB 2.229/2024)."""
    chars = re.sub(r"[./-]", "", candidate).upper()
    if not re.fullmatch(r"[0-9A-Z]{12}\d{2}", chars) or len(set(chars)) == 1:
        return False
    values = [ord(ch) - 48 for ch in chars]
    first = _mod11_check_digit(values[:12], (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2))
    second = _mod11_check_digit(values[:13], (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2))
    return values[12] == first and values[13] == second


def cccd_valid(candidate: str) -> bool:
    """Vietnamese CCCD number: 12 digits whose first 3 are a documented
    province code. The number has no check digit, so the province prefix is
    the only structural test -- the context keyword carries more weight here."""
    return (
        len(candidate) == 12
        and candidate.isdigit()
        and candidate[:3] in VN_PROVINCE_CODES
    )


def latlon_valid(candidate: str) -> bool:
    """A lat/lon pair in range: latitude within +-90, longitude within +-180.
    Accepts the bare "lat, lon" form and the labelled forms LATLON_CANDIDATE
    matches; the labels carry no digits, so the two decimals are the pair."""
    numbers = _DECIMAL.findall(candidate)
    if len(numbers) != 2:
        return False
    lat, lon = (float(n) for n in numbers)
    return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0


def find_credential_spans(text: str) -> list:
    """(start, end, value) for every credential assignment in `text`. The
    value, not the whole assignment, goes to the validator; it is never
    printed."""
    spans = []
    for m in CREDENTIAL_ASSIGNMENT.finditer(text):
        bare = m.group("bare")
        if bare is not None and _CREDENTIAL_NOT_A_SECRET.fullmatch(bare):
            continue
        value = next(v for v in m.group("dq", "sq", "bare") if v is not None)
        spans.append((m.start(), m.end(), value))
    return spans


def credential_value_real(value: str) -> bool:
    """False for an empty value or a placeholder (changeme, <redacted>,
    ${VAR}, ***, xxx, TODO, ...): only a value that looks like a real secret
    counts."""
    v = value.strip()
    if not v or v.lower() in _CREDENTIAL_PLACEHOLDER_WORDS:
        return False
    return _CREDENTIAL_PLACEHOLDER.fullmatch(v) is None


def npi_valid(candidate: str) -> bool:
    """US National Provider Identifier: 10 digits, first digit 1 or 2, Luhn
    check digit over "80840" + the 10 digits (the ISO 7812 health-industry
    prefix, per the CMS NPI check-digit specification)."""
    if len(candidate) != 10 or not candidate.isdigit() or candidate[0] not in "12":
        return False
    return luhn_valid("80840" + candidate)


def _card_valid(raw: str) -> bool:
    digits = re.sub(r"[ -]", "", raw)
    return 13 <= len(digits) <= 19 and luhn_valid(digits)


# Privacy frameworks that treat a plain email address as personal data.
_EMAIL_FRAMEWORKS = ("gdpr", "ccpa", "lgpd", "dpdpa", "vn-pdpl", "iso27701")
# Security frameworks (and the sensitive-content scanner) that treat a
# plaintext credential as a finding. Privacy frameworks deliberately do not.
_CREDENTIAL_FRAMEWORKS = (
    "soc2",
    "cis-controls",
    "iso27001",
    "nist-800-53",
    "sensitive-content-scanner",
)

# Single source of truth: every built-in category's matching logic AND its
# selector tags live together. Adding a category is one new entry here --
# scan() and the CLI never need to change.
#
# validator=None means "every regex match counts" (the regex itself already
# encodes the validity rule, e.g. SSN_SHAPED's negative lookaheads, or
# AWS_ACCESS_KEY's exact prefix+length shape). Otherwise validator(raw_match)
# -> bool does real checksum/shape validation beyond what the regex alone
# can express.
#
# frameworks=None means the category runs by default. A tuple of framework
# slugs means it runs only for those frameworks (--framework=<slug>) or when
# selected explicitly -- see the module docstring.
CATEGORY_SPECS = {
    "ssn_shaped": {
        "label": "US Social Security Number shape (area/group/serial validity rules applied, not government-verified)",
        "region": "US",
        "type": "national_id",
        "frameworks": None,
        "pattern": SSN_SHAPED,
        "validator": None,
        "context_keywords": ["ssn", "social security"],
    },
    "bsn_shaped": {
        "label": "Dutch BSN (Burgerservicenummer) shape, elfproef (11-test) checksum valid",
        "region": "NL",
        "type": "national_id",
        "frameworks": None,
        "pattern": BSN_SHAPED,
        "validator": bsn_valid,
        "context_keywords": ["bsn", "burgerservicenummer", "sofinummer"],
    },
    "credit_card_luhn_valid": {
        "label": "13-19 digit number, Luhn checksum valid (real card-number validation, not just digit count)",
        "region": None,
        "type": "financial",
        "frameworks": None,
        "pattern": CARD_CANDIDATE,
        "validator": _card_valid,
        "context_keywords": [
            "credit card",
            "card number",
            "cvv",
            "visa",
            "mastercard",
            "amex",
            "discover",
        ],
    },
    "iban_checksum_valid": {
        "label": "IBAN shape, mod-97 checksum valid (real IBAN validation)",
        "region": None,
        "type": "financial",
        "frameworks": None,
        "pattern": IBAN_CANDIDATE,
        "finder": find_iban_spans,
        "validator": iban_valid,
        "context_keywords": [
            "iban",
            "bank account",
            "rekeningnummer",
            "account number",
        ],
    },
    "aws_access_key": {
        "label": "AWS access key ID shape (AKIA prefix + 16 chars) -- a leaked-credential signal, not classic PII",
        "region": None,
        "type": "credential",
        "frameworks": None,
        "pattern": AWS_ACCESS_KEY,
        "validator": None,
        "context_keywords": ["aws", "access key", "secret key"],
    },
    "plaintext_credential": {
        "label": "Plaintext credential assignment (password/passwd/pwd/secret/token/api_key = value; placeholder values such as changeme, <redacted>, ${VAR} excluded)",
        "region": None,
        "type": "credential",
        "frameworks": _CREDENTIAL_FRAMEWORKS,
        "pattern": CREDENTIAL_ASSIGNMENT,
        "finder": find_credential_spans,
        "validator": credential_value_real,
        # The name itself (bind_password, DB_ACCOUNT_PASSWORD) must not
        # confirm its own match: look for keywords around it, not inside it.
        "context_outside_match": True,
        "context_keywords": [
            "username",
            "user=",
            "user:",
            "user =",
            "login",
            "credential",
            "bind",
            "account",
            "connection",
            "dsn",
        ],
    },
    "aadhaar_verhoeff_valid": {
        "label": "India Aadhaar number shape (12 digits, first digit 2-9), Verhoeff checksum valid",
        "region": "IN",
        "type": "national_id",
        "frameworks": ("dpdpa",),
        "pattern": AADHAAR_CANDIDATE,
        "validator": aadhaar_valid,
        "context_keywords": ["aadhaar", "aadhar", "uidai", "kyc"],
    },
    "cpf_mod11_valid": {
        "label": "Brazil CPF (individual taxpayer number), mod-11 check digits valid",
        "region": "BR",
        "type": "national_id",
        "frameworks": ("lgpd",),
        "pattern": CPF_CANDIDATE,
        "validator": cpf_valid,
        "context_keywords": ["cpf", "cadastro de pessoas", "contribuinte"],
    },
    "cnpj_mod11_valid": {
        "label": "Brazil CNPJ (company registry number, numeric or alphanumeric), mod-11 check digits valid",
        "region": "BR",
        "type": "business_id",
        "frameworks": ("lgpd",),
        "pattern": CNPJ_CANDIDATE,
        "validator": cnpj_valid,
        "context_keywords": [
            "cnpj",
            "cadastro nacional",
            "pessoa juridica",
            "pessoa jur\u00eddica",
        ],
    },
    "vn_cccd_shaped": {
        "label": "Viet Nam CCCD citizen ID number shape (12 digits, documented province-code prefix; no check digit exists)",
        "region": "VN",
        "type": "national_id",
        "frameworks": ("vn-pdpl",),
        "pattern": CCCD_CANDIDATE,
        "validator": cccd_valid,
        "context_keywords": [
            "cccd",
            "c\u0103n c\u01b0\u1edbc",
            "can cuoc",
            "cmnd",
            "citizen id",
            "identity card",
            "s\u1ed1 \u0111\u1ecbnh danh",
        ],
    },
    "email_address": {
        "label": "Email address shape (personal data under the privacy frameworks that enable it)",
        "region": None,
        "type": "contact",
        "frameworks": _EMAIL_FRAMEWORKS,
        "pattern": EMAIL_CANDIDATE,
        "validator": None,
        "context_keywords": ["email", "e-mail", "contact", "mailto"],
    },
    "npi_luhn_valid": {
        "label": "US National Provider Identifier (10 digits, Luhn check digit with the 80840 prefix), counted only near an NPI keyword",
        "region": "US",
        "type": "health_id",
        "frameworks": ("hipaa",),
        "pattern": NPI_CANDIDATE,
        "validator": npi_valid,
        "context_keywords": ["npi", "national provider"],
        # One in ten 10-digit numbers passes the check digit, so a match
        # with no NPI keyword nearby is not counted at all -- and the
        # keyword must be a whole word ("unpinned" is not an NPI label).
        "context_required": True,
        "context_whole_word": True,
    },
    "medical_record_number": {
        "label": "Medical record number directly after its label (MRN, medical record number, patient ID); no checksum exists",
        "region": None,
        "type": "health_id",
        "frameworks": ("hipaa",),
        "pattern": MRN_LABELLED,
        "validator": None,
        # The label is part of the match, so context is looked for around
        # it: a health-care setting nearby, not the label confirming itself.
        "context_keywords": _HEALTH_CONTEXT,
        "context_outside_match": True,
    },
    "health_plan_member_id": {
        "label": "Health-plan / insurance / member / subscriber / beneficiary / Medicare / Medicaid ID directly after its label; no checksum exists",
        "region": None,
        "type": "health_id",
        "frameworks": ("hipaa",),
        "pattern": MEMBER_ID_LABELLED,
        "validator": None,
        "context_keywords": _HEALTH_CONTEXT,
        "context_outside_match": True,
    },
    "geolocation_latlon": {
        "label": "Decimal lat/lon pair, bare or labelled (lat/latitude then lon/lng/longitude), 3+ decimals, in range (CCPA precise geolocation)",
        "region": None,
        "type": "geolocation",
        "frameworks": ("ccpa",),
        "pattern": LATLON_CANDIDATE,
        "validator": latlon_valid,
        "context_keywords": [
            "latitude",
            "longitude",
            "lat/lon",
            "gps",
            "coordinates",
            "geolocation",
        ],
    },
}

DEFAULT_ENABLED_CATEGORIES = frozenset(
    k for k, v in CATEGORY_SPECS.items() if v["frameworks"] is None
)

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


def known_frameworks():
    return sorted({f for v in CATEGORY_SPECS.values() for f in (v["frameworks"] or ())})


def _framework_categories(framework: str):
    return {
        k for k, v in CATEGORY_SPECS.items() if framework in (v["frameworks"] or ())
    }


def resolve_categories(arg=None, framework=None):
    """Turn a --categories selector (None, 'all', or a comma-separated list
    of exact keys / region:<value> / type:<value>) into the set of category
    keys to actually run, then add the gated presets of `framework` (a slug
    such as "dpdpa") on top. Items are unioned. Raises ValueError with a
    plain-language message (naming the valid options) on any unrecognized
    category key, region, type or framework -- a typo should never silently
    no-op."""
    errors = []
    extra = set()
    if framework is not None:
        slug = framework.strip().lower()
        extra = _framework_categories(slug)
        if not extra:
            errors.append(
                "unknown framework '%s' -- frameworks with gated presets: %s"
                % (framework, ", ".join(known_frameworks()))
            )

    if arg is None or arg.strip().lower() == "all":
        if errors:
            raise ValueError("; ".join(errors))
        return frozenset(DEFAULT_ENABLED_CATEGORIES | extra)

    selected = set()
    for token in (t.strip() for t in arg.split(",") if t.strip()):
        lowered = token.lower()
        if lowered.startswith("region:"):
            region = token.split(":", 1)[1].strip()
            matches = {k for k, v in CATEGORY_SPECS.items() if v["region"] == region}
            if not matches:
                errors.append(
                    "unknown region '%s' -- known regions: %s"
                    % (region, ", ".join(_known_regions()))
                )
            selected |= matches
        elif lowered.startswith("type:"):
            type_ = token.split(":", 1)[1].strip()
            matches = {k for k, v in CATEGORY_SPECS.items() if v["type"] == type_}
            if not matches:
                errors.append(
                    "unknown type '%s' -- known types: %s"
                    % (type_, ", ".join(_known_types()))
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
    return frozenset(selected | extra)


def _skip_entry(category: str) -> dict:
    spec = CATEGORY_SPECS[category]
    entry = {
        "skipped": True,
        "region": spec["region"],
        "type": spec["type"],
        "reason": "not included in this scan's --categories selection",
    }
    if spec["frameworks"]:
        entry["frameworks"] = list(spec["frameworks"])
        entry["reason"] = (
            "framework-gated preset; runs with --framework=%s or when selected explicitly"
            % "|".join(spec["frameworks"])
        )
    return entry


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


def context_hit(
    text: str,
    start: int,
    end: int,
    keywords,
    outside_match: bool = False,
    whole_word: bool = False,
) -> bool:
    if outside_match:
        window = (
            text[max(0, start - CONTEXT_WINDOW) : start]
            + "\n"
            + text[end : end + CONTEXT_WINDOW]
        ).lower()
    else:
        window = text[max(0, start - CONTEXT_WINDOW) : end + CONTEXT_WINDOW].lower()
    if whole_word:
        return any(
            re.search(
                r"(?<![a-z0-9])" + re.escape(kw.lower()) + r"(?![a-z0-9])", window
            )
            for kw in keywords
        )
    return any(kw.lower() in window for kw in keywords)


def scan(text: str, enabled=None) -> dict:
    """enabled: iterable of category keys to actually run (see
    resolve_categories). Defaults to every category without a framework gate
    when not given -- the general built-in categories run unless the caller
    narrows scope explicitly. A category not in `enabled` still appears in
    the result, as a {"skipped": true, ...} entry -- never just missing."""
    enabled = frozenset(enabled) if enabled is not None else DEFAULT_ENABLED_CATEGORIES
    result = {}
    for key, spec in CATEGORY_SPECS.items():
        if key not in enabled:
            result[key] = _skip_entry(key)
            continue
        pattern = spec["pattern"]
        validator = spec.get("validator")
        keywords = spec.get("context_keywords") or []
        finder = spec.get("finder")
        outside = spec.get("context_outside_match", False)
        whole_word = spec.get("context_whole_word", False)
        if finder is not None:
            candidates = finder(text)
        else:
            candidates = (
                (m.start(), m.end(), m.group()) for m in pattern.finditer(text)
            )
        required = spec.get("context_required", False)
        valid = context = 0
        for start, end, raw in candidates:
            if validator is None or validator(raw):
                confirmed = bool(keywords) and context_hit(
                    text, start, end, keywords, outside, whole_word
                )
                if required and not confirmed:
                    continue
                valid += 1
                context += int(confirmed)
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
            result[label] = {
                "valid": 0,
                "context_confirmed": 0,
                "error": "invalid regex: " + str(e),
            }
            continue

        try:
            matches = _finditer_with_timeout(
                compiled, scan_text, CUSTOM_REGEX_TIMEOUT_SECONDS
            )
        except _RegexTimeout:
            result[label] = {
                "valid": 0,
                "context_confirmed": 0,
                "error": "regex timed out after "
                + str(CUSTOM_REGEX_TIMEOUT_SECONDS)
                + "s -- likely catastrophic backtracking, simplify the pattern",
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
            entry["note"] = (
                "input text truncated to "
                + str(CUSTOM_MAX_TEXT_CHARS)
                + " chars before evaluation"
            )
        result[label] = entry

    return result


class _Parser(argparse.ArgumentParser):
    """Usage errors exit 1, the exit code callers have always relied on
    (argparse's own default is 2). --help still exits 0."""

    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(1, "%s: error: %s\n" % (self.prog, message))


def _build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="pii_patterns.py",
        description=(
            "Count built-in PII/secret pattern matches (and optional custom "
            "regexes) in an extracted-text file. Prints only JSON counts, "
            "never the matched values."
        ),
    )
    parser.add_argument("text_file", help="path to the extracted-text file to scan")
    parser.add_argument(
        "custom_patterns",
        nargs="?",
        default=None,
        help='optional JSON array of {"label", "regex", "context_keywords"?} objects',
    )
    parser.add_argument(
        "--categories",
        default=None,
        metavar="SELECTOR",
        help=(
            "comma-separated category keys, region:<value>, type:<value>, or "
            "'all' (default: every general category). Known categories: "
            + ", ".join(sorted(CATEGORY_SPECS))
        ),
    )
    parser.add_argument(
        "--framework",
        default=None,
        metavar="SLUG",
        help=(
            "add a framework's gated presets on top of --categories. Known: "
            + ", ".join(known_frameworks())
        ),
    )
    return parser


def main(argv=None) -> int:
    parser = _build_parser()
    # Intermixed: --categories may sit between the two positionals, as the
    # documented `<text> --categories=... <custom.json>` form requires.
    args = parser.parse_intermixed_args(argv)

    try:
        enabled_categories = resolve_categories(
            args.categories, framework=args.framework
        )
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1

    try:
        with open(args.text_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except OSError as e:
        parser.error("cannot read text file: %s" % e.strerror)

    output = scan(content, enabled=enabled_categories)

    if args.custom_patterns is not None:
        try:
            with open(
                args.custom_patterns, "r", encoding="utf-8", errors="ignore"
            ) as f:
                custom_patterns = json.load(f)
        except OSError as e:
            parser.error("cannot read custom-patterns file: %s" % e.strerror)
        except ValueError as e:
            parser.error("custom-patterns file is not valid JSON: %s" % e)
        if not isinstance(custom_patterns, list):
            print("custom-patterns.json must be a JSON array", file=sys.stderr)
            return 1
        output["custom"] = scan_custom(content, custom_patterns)

    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
