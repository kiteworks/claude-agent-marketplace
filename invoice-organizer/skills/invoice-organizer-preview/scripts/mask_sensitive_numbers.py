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


def mask_all(text: str) -> str:
    # IBANs first: an all-digit BBAN can otherwise pass as a Luhn card number.
    return _mask_around_ibans(text, lambda rest: mask_ssns(mask_cards(rest)))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        src = " ".join(sys.argv[1:])
    else:
        src = sys.stdin.read()
    sys.stdout.write(mask_all(src))
