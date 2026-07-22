#!/usr/bin/env python3
"""Deterministic masking for card/SSN-shaped numbers that show up in receipt
text, so a payment-method field never carries a full number into a CSV,
report, or chat -- the same discipline term-sweep's pii_patterns.py already
applies to sensitive-content-scanner (never surface the matched value, only
a masked/derived form), reused here because receipts routinely print a full
or near-full card number in the printed slip even when a business only cares
about "paid by card ending in 1234."

Uses the same real checksum validation as pii_patterns.py (Luhn for card
numbers) rather than naive digit-counting, to avoid masking ordinary long
numbers (invoice numbers, order IDs) that merely happen to be long.

Usage:
  python3 mask_sensitive_numbers.py "<text>"
  (or pipe text via stdin with no argument)

Prints the masked text to stdout. Deterministic, no LLM judgment involved --
this exists specifically so the model never has to be trusted to remember
not to paste a full number verbatim.
"""
import re
import sys

CARD_CANDIDATE = re.compile(r"\b(?:\d[ -]?){13,19}\b")
SSN_SHAPED = re.compile(r"\b(?!000|666|9\d{2})\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b")


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


def mask_all(text: str) -> str:
    return mask_ssns(mask_cards(text))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        src = " ".join(sys.argv[1:])
    else:
        src = sys.stdin.read()
    sys.stdout.write(mask_all(src))
