"""Neutralise and truncate untrusted tenant text (stdlib only, pure).

Tenant text (file and folder names, descriptions, display names, mail
subjects, CSV cells) is attacker-controlled. ``fence`` wraps a cleaned,
truncated copy in U+27E6 / U+27E7 so it can be shown to a model as data.
"""

import re
import unicodedata

OPEN, CLOSE = "\u27e6", "\u27e7"
NAME_MAX = 120
TEXT_MAX = 200
ELLIPSIS = "\u2026"

# C0/C1 controls (tab/newline become spaces first), bidi controls,
# zero-width characters and the BOM.
_DROP = re.compile(
    "[\x00-\x08\x0b-\x1f\x7f-\x9f\u200b-\u200f\u202a-\u202e\u2060\u2066-\u2069\ufeff]"
)
_WS = re.compile(r"\s+")

_PHRASES = re.compile(
    r"ignore\s+(?:all|previous|prior)\s+instructions"
    r"|you\s+are\s+now\b"
    r"|\bsystem\s*:"
    r"|\bassistant\s*:"
    r'|\{\s*"',
    re.IGNORECASE,
)


def clean(value) -> str:
    """Return ``value`` as a single-line string free of control/invisible chars."""
    if value is None:
        return ""
    text = value if isinstance(value, str) else str(value)
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\t", " ").replace("\n", " ").replace("\r", " ")
    text = _DROP.sub("", text)
    text = text.replace(OPEN, "[").replace(CLOSE, "]")
    return _WS.sub(" ", text).strip()


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    if max_len <= 0:
        return ""
    return text[: max_len - 1].rstrip() + ELLIPSIS


def fence(value, max_len: int = TEXT_MAX) -> str:
    """Return the cleaned, truncated value wrapped in the fence characters."""
    return OPEN + _truncate(clean(value), max_len) + CLOSE


def looks_like_instruction(value, tools: frozenset[str] = frozenset()) -> bool:
    """Heuristic: does the text read like an instruction to a model?

    Sets ``injection_suspected``; never blocks. Tool names are matched as
    whole words, and only names containing an underscore, so plain English
    tool names such as ``search`` do not flag ordinary file names.
    """
    text = clean(value)
    if not text:
        return False
    if _PHRASES.search(text):
        return True
    lowered = text.lower()
    for name in tools:
        if "_" not in name:
            continue
        if re.search(rf"(?<![a-z0-9_]){re.escape(name.lower())}(?![a-z0-9_])", lowered):
            return True
    return False


def fence_record(record: dict, fields: dict[str, int], tools: frozenset[str]) -> dict:
    """Return a copy of ``record`` with ``fields`` fenced to their max lengths.

    Adds ``injection_suspected: True`` when any listed field looks like an
    instruction. Other keys are copied untouched; the input is not mutated.
    """
    out = dict(record)
    suspected = False
    for key, max_len in fields.items():
        if key not in record:
            continue
        if looks_like_instruction(record[key], tools):
            suspected = True
        out[key] = fence(record[key], max_len)
    if suspected:
        out["injection_suspected"] = True
    return out
