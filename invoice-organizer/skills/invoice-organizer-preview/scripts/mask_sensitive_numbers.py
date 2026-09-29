#!/usr/bin/env python3
"""Deterministic masking for card/SSN-shaped numbers and IBANs that show up
in receipt and invoice text, so a payment-method or bank-details field never
carries a full number into a CSV, report, or chat -- the same discipline
term-sweep's pii_patterns.py already applies to sensitive-content-scanner
(never surface the matched value, only a masked/derived form), reused here
because receipts routinely print a full or near-full card number in the
printed slip even when a business only cares about "paid by card ending in
1234," and invoices print the supplier's full IBAN.

Uses the same real checksum validation as pii_patterns.py (Luhn for card
numbers) rather than naive digit-counting, to avoid masking ordinary long
numbers (invoice numbers, order IDs) that merely happen to be long.

IBANs (printed in groups of four, compact, or lowercase) are masked to
country code + last 4, e.g. "NL91 ABNA 0417 1643 00" -> "NL•• •••• 4300",
whenever a known country code and two check digits start a run of exactly
that country's registered IBAN length, not glued to further letters/digits.
The mod-97 check is deliberately NOT required there: this is a display mask
and fails closed, so an OCR-garbled IBAN (one wrong character) is still
masked rather than printed in full. The length table, the group-of-four
printed layout and the boundary rules keep ordinary identifiers and prose out.
An IBAN glued straight onto the next field ("NL91ABNA0417164300BIC",
"...1643001234") is masked too, but only when its exact country-length
prefix passes mod-97; the glued-on rest ("BIC") is left as it is, and a
random long token whose prefix fails mod-97 is not masked.
IBANs are masked before cards, so an all-digit BBAN (e.g. German) is never
half-masked as a card number, and cards are masked only in the text between
IBANs, so a masked IBAN's last 4 cannot hide a card that follows it.

A second, fail-closed pass looks for one of a short list of keywords
("iban", "rekeningnummer", "bank account", "account number",
"kontonummer") and, within about 40 characters after it, a candidate
shaped like an IBAN -- two letters, two digit-or-OCR-lookalike
characters, then at least ten more alphanumerics, with a single space
optionally sitting between any two of those characters (#306). It runs
after the checksum-based pass above and needs no checksum at all, so it
catches an IBAN OCR has corrupted badly enough that its country code or
check digits no longer look like two letters and two digits (e.g. "NL2O"
for "NL20"), which the checksum-based pass's own regex cannot even
anchor on. It is restricted to that short window so it never touches an
ordinary reference number or prose that merely follows one of those
keywords, and it skips any span the checksum-based pass already masked.

When that keyword pass finds nothing, a last fallback looks in the same
window for a single token (letters, digits and the OCR debris "@", "|",
"!", "$"; no spaces, dots, slashes or hyphens) that starts with a known
IBAN country code, is within one character short or two long of that
country's IBAN length, and holds at least 8 real digits. It catches what
tesseract really made of a Dutch IBAN, "NL2@INGBQ@Q01234567": zeros read
as "@" and "Q", and one character too many, so no exact-length walk fits.
A token longer than that is cut to two above the country's length and
back to its last digit, so a glued-on BIC ("...4567INGBNL2A") or table
cell ("...4567|12") stays visible while the account number is masked.
URLs, e-mail addresses and dashed references never form one such token,
which keeps them out.

Usage:
  python3 mask_sensitive_numbers.py "<text>"
  (or pipe text via stdin with no argument)

Prints the masked text to stdout. Deterministic, no LLM judgment involved --
this exists specifically so the model never has to be trusted to remember
not to paste a full number verbatim.
"""

from __future__ import annotations

import re
import sys

CARD_CANDIDATE = re.compile(r"\b(?:\d[ -]?){13,19}\b")
SSN_SHAPED = re.compile(r"\b(?!000|666|9\d{2})\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b")


# Country code + two check digits, not glued to a preceding letter/digit.
# Case-insensitive: the length table, group-of-four layout and boundary rules
# keep false positives out.
IBAN_START = re.compile(r"(?<![A-Za-z0-9])([A-Za-z]{2})\d{2}")

# Characters that may sit between two printed groups of four: spaces
# (U+00A0 is what pdftotext often emits; -layout doubles them), tabs, line
# breaks, hyphens and dots.
IBAN_SEPARATORS = " \u00a0\t\r\n-."
MAX_SEPARATOR_RUN = 3  # e.g. " - " or a CRLF plus a space

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


def iban_mod97_valid(compact: str) -> bool:
    """ISO 13616 mod-97 check on a compact IBAN (letters count as 10..35)."""
    rearranged = compact[4:] + compact[:4]
    try:
        numeric = "".join(str(int(ch, 36)) for ch in rearranged)
    except ValueError:
        return False
    return int(numeric) % 97 == 1


def _luhn_valid(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def mask_cards(text: str) -> str:
    def repl(m):
        raw = m.group(0)
        digits = re.sub(r"[ -]", "", raw)
        if 13 <= len(digits) <= 19 and _luhn_valid(digits):
            return f"•••• {digits[-4:]}"
        return raw  # not a Luhn-valid card number -- leave alone (e.g. an invoice #)

    return CARD_CANDIDATE.sub(repl, text)


def mask_ssns(text: str) -> str:
    def repl(m):
        digits = m.group(0).replace("-", "")
        return f"***-**-{digits[-4:]}"

    return SSN_SHAPED.sub(repl, text)


def _iban_end(
    text: str, start: int, length: int, *, allow_glued: bool = False
) -> int | None:
    """End index of an IBAN of `length` characters starting at `start`.

    Accepts the compact form and the printed form, where a short run of
    IBAN_SEPARATORS (at most MAX_SEPARATOR_RUN characters) may sit only
    between groups of four, as IBANs are printed. Returns None when the run
    is too short, is grouped some other way, or carries on as a longer token
    (a letter/digit glued on, or a hyphen/dot and more letters/digits).
    With `allow_glued`, whatever follows the IBAN is not inspected; the
    caller then has to prove the prefix is an IBAN (mod-97).
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
        if j - i > MAX_SEPARATOR_RUN:
            return None
        i = j
    if allow_glued:
        return i
    if i < n and text[i].isascii() and text[i].isalnum():
        return None
    j = i
    while j < n and text[j] in "-.":
        j += 1
    if j > i and j < n and text[j].isascii() and text[j].isalnum():
        return None
    return i


def _iban_spans(text: str) -> list[tuple[int, int, str]]:
    """(start, end, masked form) for every IBAN-shaped run in `text`, in order.

    No mod-97 check on a cleanly bounded run (fail closed, see the module
    docstring); a run glued to further characters must pass mod-97.
    """
    spans = []
    pos = 0
    for m in IBAN_START.finditer(text):
        if m.start() < pos:
            continue  # inside an IBAN already found
        length = IBAN_LENGTHS.get(m.group(1).upper())
        if length is None:
            continue
        end = _iban_end(text, m.start(), length)
        glued = end is None
        if glued:
            # Glued to the next field ("...164300BIC"): only a mod-97 valid
            # exact-length prefix counts, so random long tokens stay unmasked.
            end = _iban_end(text, m.start(), length, allow_glued=True)
            if end is None:
                continue
        raw = text[m.start() : end]
        iban = "".join(ch for ch in raw if ch not in IBAN_SEPARATORS).upper()
        if glued and not iban_mod97_valid(iban):
            continue
        spans.append((m.start(), end, f"{iban[:2]}•• •••• {iban[-4:]}"))
        pos = end
    return spans


def _mask_around_ibans(text: str, mask_rest) -> str:
    """Mask IBANs, and run `mask_rest` over each stretch of text between them.

    The stretches are masked separately so the last four digits kept in a
    masked IBAN can never join a following card number into one digit run
    that then fails Luhn and prints the card in full.
    """
    out = []
    pos = 0
    for start, end, masked in _iban_spans(text):
        out.append(mask_rest(text[pos:start]))
        out.append(masked)
        pos = end
    out.append(mask_rest(text[pos:]))
    return "".join(out)


def mask_ibans(text: str) -> str:
    return _mask_around_ibans(text, lambda rest: rest)


# --- Keyword-anchored fail-closed pass, for an IBAN OCR corrupts beyond
# the checksum-based pass's reach (#306) ---------------------------------

# Keywords that precede a bank account number closely enough in invoice
# text that whatever follows is worth masking even without a checksum.
IBAN_KEYWORD_RE = re.compile(
    r"\b(?:iban|rekeningnummer|bank account|account number|kontonummer)\b",
    re.IGNORECASE,
)

# Digits and their OCR lookalikes for the two check-digit positions, per
# the character set the issue specifies (O/o for 0, I/l for 1, S for 5,
# B for 8).
_IBAN_KEYWORD_DIGIT_CLASS = "0-9OoIlSB"

# The anchor: two letters (the country code) then two digit-or-lookalike
# characters (the check digits, not inspected here), with a single space
# optionally sitting between any two of those four characters, the way
# OCR or a printed layout breaks one up. Not glued to a preceding
# letter/digit, so it never starts mid-word (an ordinary word can
# otherwise supply two letters and, via the lookalike classes, two more
# characters that pass for check digits).
IBAN_KEYWORD_ANCHOR_RE = re.compile(
    r"(?<![A-Za-z0-9])[A-Za-z] ?[A-Za-z] ?"
    rf"[{_IBAN_KEYWORD_DIGIT_CLASS}] ?[{_IBAN_KEYWORD_DIGIT_CLASS}]"
)

# How far past a keyword to look for an anchor.
IBAN_KEYWORD_WINDOW = 40


def _iban_keyword_end(text: str, start: int, length: int, limit: int) -> int | None:
    """End index of a `length`-alphanumeric-character run from `start`.

    A single space may optionally sit between any two of those characters,
    as the candidate shape allows; the walk never reads past `limit` (the
    end of the keyword window). Unlike `_iban_end`, nothing past the run
    is inspected -- this pass has no checksum to fall back on, so it stops
    at exactly the target length instead of trying to prove a boundary,
    which is also what keeps it from reading into whatever follows (a
    card number, more prose) as though it were part of the account number.
    """
    count = 0
    i = start
    n = min(len(text), limit)
    while count < length:
        if i >= n:
            return None
        ch = text[i]
        if ch.isascii() and ch.isalnum():
            count += 1
            i += 1
            continue
        if ch == " " and i + 1 < n and text[i + 1].isascii() and text[i + 1].isalnum():
            i += 1  # a single space separating two characters
            continue
        return None
    return i


def _iban_keyword_spans(
    text: str, taken: list[tuple[int, int, str]]
) -> list[tuple[int, int, str]]:
    """(start, end, masked form) for a candidate found near a keyword.

    Only an anchor whose two letters are a known IBAN country (the same
    `IBAN_LENGTHS` table the checksum-based pass uses) is followed up --
    that both keeps ordinary prose out and gives an exact target length,
    so the run stops where the account number actually ends instead of
    swallowing whatever comes right after it. A candidate also needs at
    least 8 real ASCII digits in its full length -- a garbled IBAN body
    is still mostly digits, so this rejects the run of ordinary letters
    (with a few lookalike characters sprinkled in) that plain prose after
    a keyword can otherwise supply. `taken` holds the spans the
    checksum-based pass (`_iban_spans`) already masked; a candidate
    overlapping one of those is skipped, so the two passes never
    double-mask one run.
    """
    spans: list[tuple[int, int, str]] = []
    pos = 0
    taken = sorted(taken)
    ti = 0
    for km in IBAN_KEYWORD_RE.finditer(text):
        window_start = km.end()
        window_end = min(len(text), window_start + IBAN_KEYWORD_WINDOW)
        am = IBAN_KEYWORD_ANCHOR_RE.search(text, window_start, window_end)
        if am is None or am.start() < pos:
            continue
        anchor = "".join(ch for ch in am.group(0) if ch != " ").upper()
        length = IBAN_LENGTHS.get(anchor[:2])
        if length is None:
            continue
        start = am.start()
        end = _iban_keyword_end(text, start, length, window_end)
        if end is None:
            continue
        compact = "".join(ch for ch in text[start:end] if ch != " ").upper()
        digit_count = sum(1 for ch in compact if ch in "0123456789")
        if digit_count < 8:
            continue  # too few real digits to be a garbled IBAN body
        while ti < len(taken) and taken[ti][1] <= start:
            ti += 1
        if ti < len(taken) and start < taken[ti][1] and end > taken[ti][0]:
            continue  # overlaps a span the checksum-based pass already masked
        masked = f"{compact[:2]}\u2022\u2022 \u2022\u2022\u2022\u2022 {compact[-4:]}"
        spans.append((start, end, masked))
        pos = end
    return spans


# A token the fallback may consider: two letters, then letters, digits and
# the characters OCR turns a digit into. Not glued to a preceding
# character that would make it part of a URL, e-mail address or dashed
# reference.
IBAN_KEYWORD_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9@./\-_])[A-Za-z]{2}[A-Za-z0-9@|!$]+")

# Whatever follows the last digit of an over-long token's IBAN-length
# prefix is glued-on text (a BIC, a table cell), not IBAN body.
IBAN_TOKEN_TRAILING_NON_DIGITS_RE = re.compile(r"[^0-9]+$")


def _iban_keyword_token_spans(
    text: str, taken: list[tuple[int, int, str]]
) -> list[tuple[int, int, str]]:
    """(start, end, masked form) for an OCR-garbled token near a keyword.

    Takes, per keyword, the first token starting in its window that does
    not overlap a span in `taken` (the checksum-based and keyword-anchored
    spans) and passes the guards: a known country code, a length from one
    below to two above that country's IBAN length (OCR drops or inserts
    characters), and at least 8 real ASCII digits. A longer token is first
    cut to that maximum and back to its last digit (glued-on BIC or table
    cell). The token may run past the window, so its last 4 are the real
    last 4.
    """
    spans: list[tuple[int, int, str]] = []
    covered = sorted(taken)
    pos = 0
    for km in IBAN_KEYWORD_RE.finditer(text):
        window_start = km.end()
        window_end = min(len(text), window_start + IBAN_KEYWORD_WINDOW)
        for tm in IBAN_KEYWORD_TOKEN_RE.finditer(text, window_start):
            start = tm.start()
            if start >= window_end:
                break
            if start < pos:
                continue
            token = tm.group(0)
            length = IBAN_LENGTHS.get(token[:2].upper())
            if length is None:
                continue
            if len(token) > length + 2:
                token = IBAN_TOKEN_TRAILING_NON_DIGITS_RE.sub("", token[: length + 2])
            if len(token) < length - 1:
                continue
            if sum(1 for ch in token if ch in "0123456789") < 8:
                continue
            end = start + len(token)
            if any(start < e and end > s for s, e, _ in covered):
                continue
            masked = (
                f"{token[:2].upper()}\u2022\u2022 \u2022\u2022\u2022\u2022 "
                f"{token[-4:].upper()}"
            )
            spans.append((start, end, masked))
            pos = end
            break
    return spans


def _mask_around_all_ibans(text: str, mask_rest) -> str:
    """Like `_mask_around_ibans`, but over both IBAN-masking passes.

    Combines the checksum-based spans with the keyword-anchored and
    keyword-token fail-closed spans (#306) into one ordered list before slicing, so `mask_rest` never
    sees a stretch of text crossing either kind of masked span -- the same
    reason `_mask_around_ibans` keeps the last four digits of a masked IBAN
    from joining a following card number into one Luhn-failing run.
    """
    checksum_spans = _iban_spans(text)
    keyword_spans = _iban_keyword_spans(text, checksum_spans)
    token_spans = _iban_keyword_token_spans(text, checksum_spans + keyword_spans)
    spans = sorted(checksum_spans + keyword_spans + token_spans, key=lambda s: s[0])
    out = []
    pos = 0
    for start, end, masked in spans:
        out.append(mask_rest(text[pos:start]))
        out.append(masked)
        pos = end
    out.append(mask_rest(text[pos:]))
    return "".join(out)


def mask_all(text: str) -> str:
    # IBANs first: an all-digit BBAN can otherwise pass as a Luhn card number.
    return _mask_around_all_ibans(text, lambda rest: mask_ssns(mask_cards(rest)))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        src = " ".join(sys.argv[1:])
    else:
        src = sys.stdin.read()
    sys.stdout.write(mask_all(src))
