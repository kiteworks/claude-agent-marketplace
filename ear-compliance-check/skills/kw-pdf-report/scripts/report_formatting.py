"""Shared size and percentage formatting for the report renderer.

Standard library only (``decimal``). All arithmetic is exact: sizes are
integers and are divided as ``Decimal`` values, so no binary floating point is
ever involved and ``2**53 + 1`` keeps its precision.

The renderer files are not a package, so load this module the same way
``branded_pdf.py`` loads ``report_model.py``::

    _FORMAT = runpy.run_path(str(Path(__file__).resolve().with_name("report_formatting.py")))
    format_size = _FORMAT["format_size"]

Do not use a bare ``import report_formatting``.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

NBSP = "\u00a0"
UNITS = ("B", "kB", "MB", "GB", "TB", "PB", "EB")
NOT_MEASURED = "Not measured"
_BASE = 1000


def _check_size(size_bytes: object) -> int:
    if isinstance(size_bytes, bool) or not isinstance(size_bytes, int):
        raise ValueError(f"size must be an int, got {type(size_bytes).__name__}")
    if size_bytes < 0:
        raise ValueError("size must not be negative")
    return size_bytes


def _trim(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _three_significant(value: Decimal) -> Decimal:
    if value >= 100:
        step = Decimal(1)
    elif value >= 10:
        step = Decimal("0.1")
    else:
        step = Decimal("0.01")
    return value.quantize(step, rounding=ROUND_HALF_UP)


def _auto_index(size_bytes: int) -> int:
    index = 0
    while index < len(UNITS) - 1 and size_bytes >= _BASE ** (index + 1):
        index += 1
    return index


def format_size(size_bytes: int | None) -> str:
    """Return a human readable decimal size, e.g. ``1.02 kB``."""
    if size_bytes is None:
        return NOT_MEASURED
    size = _check_size(size_bytes)
    if size < _BASE:
        return f"{size}{NBSP}B"
    index = _auto_index(size)
    last = len(UNITS) - 1
    exact = Decimal(size) / Decimal(_BASE**index)
    if index == last and exact >= _BASE:
        whole = exact.quantize(Decimal(1), rounding=ROUND_HALF_UP)
        return f"{int(whole):,}{NBSP}{UNITS[last]}"
    rounded = _three_significant(exact)
    if rounded >= _BASE and index < last:
        index += 1
        rounded = _three_significant(Decimal(size) / Decimal(_BASE**index))
    return f"{_trim(rounded)}{NBSP}{UNITS[index]}"


def format_size_in_unit(size_bytes: int, unit: str) -> str:
    """Return the size in a fixed unit with two decimals."""
    size = _check_size(size_bytes)
    if unit not in UNITS:
        raise ValueError(f"unknown unit: {unit!r}")
    value = Decimal(size) / Decimal(_BASE ** UNITS.index(unit))
    if 0 < value < Decimal("0.005"):
        return f"<0.01{NBSP}{unit}"
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}{NBSP}{unit}"


def common_unit(values: list[int]) -> str:
    """Return the auto unit of the largest value, or ``B`` if none is positive."""
    checked = [_check_size(v) for v in values]
    if not checked:
        return "B"
    return UNITS[_auto_index(max(checked))]


def format_percent(part: int, whole: int) -> str:
    """Return ``part / whole`` as a one-decimal percentage."""
    if isinstance(part, bool) or isinstance(whole, bool):
        raise ValueError("part and whole must be ints")
    if not isinstance(part, int) or not isinstance(whole, int):
        raise ValueError("part and whole must be ints")
    if whole == 0:
        raise ValueError("whole must not be zero")
    if part < 0 or whole < 0:
        raise ValueError("part and whole must not be negative")
    if 0 < part * 2000 < whole:
        return "<0.1%"
    value = (Decimal(part) * 100 / Decimal(whole)).quantize(
        Decimal("0.1"), rounding=ROUND_HALF_UP
    )
    return f"{value}%"
