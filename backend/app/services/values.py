"""Parsers and column classification shared by profiling, quality, and cleaning.

Dates prefer day-month-year when a value is ambiguous, because this product
is aimed at Indian MSMEs. Ambiguous values are flagged rather than hidden.
Invalid numbers are left unchanged. They are never silently turned into zero.
"""

from __future__ import annotations

import re
from datetime import date, datetime

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

SYNONYMS = {
    "elec": "Electronics",
    "electronic": "Electronics",
    "electronics": "Electronics",
    "cloth": "Apparel",
    "clothing": "Apparel",
    "apparel": "Apparel",
    "grocer": "Grocery",
    "grocery": "Grocery",
    "groceries": "Grocery",
    "stationery": "Stationery",
    "stationary": "Stationery",
    "rent": "Rent",
    "util": "Utilities",
    "utility": "Utilities",
    "utilities": "Utilities",
    "salary": "Payroll",
    "salaries": "Payroll",
    "payroll": "Payroll",
    "marketing": "Marketing",
    "travel": "Travel",
    "retail": "Retail",
    "wholesale": "Wholesale",
}

DATE_NAME_HINTS = ("date", "day")
ID_NAME_HINTS = ("id", "sku", "code")
AMOUNT_NAMES = {
    "amount",
    "total",
    "total amount",
    "grand total",
    "net amount",
    "bill amount",
    "invoice amount",
    "revenue",
    "price",
    "unit price",
    "cost",
    "unit cost",
    "expense",
    "expense amount",
    "line total",
    "order amount",
    "sale amount",
    "sales amount",
    "sales",
}
QTY_NAMES = {"qty", "quantity", "units", "stock", "stock qty", "quantity on hand", "qty on hand"}
CATEGORY_NAMES = {"category", "segment", "city", "vendor", "warehouse", "status", "expense category", "product category"}


def norm_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


def is_email(value: str) -> bool:
    return bool(EMAIL_RE.match(value.strip()))


def parse_number(value: str) -> float | None:
    text = value.strip()
    if not text:
        return None
    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1]
    text = text.replace(",", "").replace("₹", "").replace("$", "").replace(" ", "")
    if text.startswith("-"):
        negative = True
        text = text[1:]
    if not re.fullmatch(r"\d+(\.\d+)?", text):
        return None
    number = float(text)
    return -number if negative else number


def format_number(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def parse_date(value: str) -> tuple[date | None, bool]:
    """Return (parsed date, ambiguous). Ambiguous numeric dates use DMY."""

    text = value.strip()
    if not text:
        return None, False

    iso = re.fullmatch(r"(\d{4})[-/](\d{2})[-/](\d{2})", text)
    if iso:
        try:
            return date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3))), False
        except ValueError:
            return None, False

    numeric = re.fullmatch(r"(\d{1,2})[-/](\d{1,2})[-/](\d{4})", text)
    if numeric:
        first, second, year = int(numeric.group(1)), int(numeric.group(2)), int(numeric.group(3))
        dmy = _safe_date(year, second, first)
        mdy = _safe_date(year, first, second)
        if dmy and mdy and dmy != mdy:
            return dmy, True
        if dmy:
            return dmy, False
        if mdy:
            return mdy, False
        return None, False

    for fmt in ("%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).date(), False
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date(), False
    except ValueError:
        return None, False


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def canonical_id(value: str) -> str:
    return re.sub(r"[\s\-_]+", "", value.strip()).upper()


def category_key(value: str) -> str:
    base = re.sub(r"\s+", " ", value.strip()).casefold().rstrip(".")
    return SYNONYMS.get(base, base)


def canonical_category(value: str) -> str:
    base = re.sub(r"\s+", " ", value.strip()).casefold().rstrip(".")
    if base in SYNONYMS:
        return SYNONYMS[base]
    return value.strip()


def modal_category(values: list[str]) -> dict[str, str]:
    """Map each raw category to a canonical spelling when a synonym or case variant exists."""

    groups: dict[str, list[str]] = {}
    for value in values:
        if value is None:
            continue
        groups.setdefault(category_key(value), []).append(value)

    mapping: dict[str, str] = {}
    for key, members in groups.items():
        synonym = SYNONYMS.get(key)
        if synonym:
            chosen = synonym
        else:
            stripped = [re.sub(r"\s+", " ", item.strip()) for item in members]
            counts: dict[str, int] = {}
            for item in stripped:
                counts[item] = counts.get(item, 0) + 1
            chosen = sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))[0][0]
        for item in members:
            mapping[item] = chosen
    return mapping


def looks_like_id(header: str) -> bool:
    name = norm_header(header)
    if "email" in name:
        return False
    return any(part in name.split() for part in ("id", "sku", "code")) or name in {"sku"}


def looks_like_amount(header: str) -> bool:
    return norm_header(header) in AMOUNT_NAMES or norm_header(header).endswith(" amount")


def looks_like_qty(header: str) -> bool:
    name = norm_header(header)
    return name in QTY_NAMES or name.endswith(" qty")


def looks_like_date(header: str) -> bool:
    name = norm_header(header)
    return any(hint in name.split() for hint in DATE_NAME_HINTS) or name.endswith(" date")


def looks_like_category(header: str) -> bool:
    name = norm_header(header)
    return name in CATEGORY_NAMES or name.endswith(" category")


def looks_like_email(header: str) -> bool:
    return "email" in norm_header(header)


def severity_from_ratio(ratio: float) -> str:
    if ratio >= 0.2:
        return "high"
    if ratio >= 0.05:
        return "medium"
    return "low"
