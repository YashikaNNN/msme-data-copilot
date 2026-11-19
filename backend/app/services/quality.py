"""Calculate data-quality scores and issues from the rows actually uploaded.

Nothing here is a fixed demo score. Empty data scores as None so the UI can
say that a score is unavailable instead of showing a fake 100.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

import pandas as pd

from app.services.values import (
    canonical_category,
    canonical_id,
    category_key,
    is_email,
    looks_like_amount,
    looks_like_category,
    looks_like_date,
    looks_like_email,
    looks_like_id,
    looks_like_qty,
    parse_date,
    parse_number,
    severity_from_ratio,
)


def _issue(
    category: str,
    column: str | None,
    affected: int,
    severity: str,
    explanation: str,
    resolution: str,
    auto_fixable: bool,
    manual_review: bool,
    details: dict | None = None,
) -> dict:
    return {
        "category": category,
        "column_name": column,
        "affected_count": int(affected),
        "severity": severity,
        "explanation": explanation,
        "suggested_resolution": resolution,
        "auto_fixable": auto_fixable,
        "manual_review": manual_review,
        "details": details or {},
    }


def assess(df: pd.DataFrame, today: date | None = None) -> dict:
    today = today or date.today()
    rows = int(len(df))
    columns = [str(column) for column in df.columns if column != "__row_id"]
    if rows == 0 or not columns:
        return {
            "score": None,
            "completeness": None,
            "validity": None,
            "uniqueness": None,
            "consistency": None,
            "issues": [],
            "row_count": rows,
            "column_count": len(columns),
            "null_cells": 0,
            "duplicate_rows": 0,
        }

    issues: list[dict] = []
    null_cells = 0
    total_cells = rows * len(columns)
    invalid_cells = 0
    checked_cells = 0
    inconsistent_cells = 0
    consistency_cells = 0

    for column in columns:
        values = df[column].tolist()
        null_count = sum(value is None for value in values)
        null_cells += null_count
        if null_count:
            ratio = null_count / rows
            issues.append(
                _issue(
                    "missing",
                    column,
                    null_count,
                    severity_from_ratio(ratio),
                    f"{null_count} of {rows} values in {column} are empty.",
                    "Fill the blanks with a real value, or drop only the rows you have reviewed.",
                    True,
                    ratio >= 0.2,
                    {"null_count": null_count, "row_count": rows},
                )
            )

        present = [value for value in values if value is not None]
        if looks_like_date(column):
            invalid = 0
            ambiguous = 0
            future = 0
            for value in present:
                parsed, is_ambiguous = parse_date(value)
                checked_cells += 1
                if parsed is None:
                    invalid += 1
                elif is_ambiguous:
                    ambiguous += 1
                elif parsed > today:
                    future += 1
            invalid_cells += invalid
            if invalid:
                issues.append(
                    _issue(
                        "invalid_date",
                        column,
                        invalid,
                        "high" if invalid else "low",
                        f"{invalid} values in {column} are not real dates.",
                        "Correct these dates by hand. The cleaner only rewrites values it can parse.",
                        False,
                        True,
                    )
                )
            if ambiguous:
                issues.append(
                    _issue(
                        "ambiguous_date",
                        column,
                        ambiguous,
                        "medium",
                        f"{ambiguous} values in {column} could be read as either day/month or month/day.",
                        "They will be read as day/month/year. Reject that cleaning step if your file is month/day/year.",
                        True,
                        True,
                    )
                )
            if future:
                issues.append(
                    _issue(
                        "future_date",
                        column,
                        future,
                        "medium",
                        f"{future} dates in {column} are after today ({today.isoformat()}).",
                        "Confirm whether those dates are intentional. They are kept and marked as a warning.",
                        False,
                        True,
                    )
                )

        if looks_like_amount(column) or looks_like_qty(column):
            invalid = 0
            negative = 0
            for value in present:
                parsed = parse_number(value)
                checked_cells += 1
                if parsed is None:
                    invalid += 1
                elif parsed < 0:
                    negative += 1
            invalid_cells += invalid
            if invalid:
                kind = "invalid_amount" if looks_like_amount(column) else "invalid_number"
                issues.append(
                    _issue(
                        kind,
                        column,
                        invalid,
                        "high",
                        f"{invalid} values in {column} are not numbers.",
                        "Fix the text in those cells. They are not converted to zero.",
                        False,
                        True,
                    )
                )
            if negative:
                invalid_cells += negative
                issues.append(
                    _issue(
                        "invalid_amount" if looks_like_amount(column) else "invalid_number",
                        column,
                        negative,
                        "high",
                        f"{negative} values in {column} are negative.",
                        "Review them. Negative money or stock is quarantined during validation and is not used in KPIs.",
                        False,
                        True,
                    )
                )

        if looks_like_email(column):
            invalid = sum(1 for value in present if not is_email(value))
            checked_cells += len(present)
            invalid_cells += invalid
            if invalid:
                issues.append(
                    _issue(
                        "invalid_email",
                        column,
                        invalid,
                        "medium",
                        f"{invalid} values in {column} are not email addresses.",
                        "Correct the addresses, or leave them out of customer analytics.",
                        False,
                        True,
                    )
                )

        if looks_like_category(column) and present:
            consistency_cells += len(present)
            grouped: dict[str, set[str]] = defaultdict(set)
            for value in present:
                grouped[category_key(value)].add(value.strip())
            preferred: dict[str, str] = {}
            for key, members in grouped.items():
                if key in _synonym_keys() or any(canonical_category(item) != item.strip() for item in members):
                    synonym_target = canonical_category(next(iter(members)))
                    preferred[key] = synonym_target if synonym_target != next(iter(members)).strip() or key in _synonym_keys() else _most_common(present, members)
                else:
                    preferred[key] = _most_common(present, members)
            messy_values = [value for value in present if value.strip() != preferred[category_key(value)]]
            messy = len(messy_values)
            inconsistent_cells += messy
            if messy:
                issues.append(
                    _issue(
                        "inconsistent_category",
                        column,
                        messy,
                        severity_from_ratio(messy / rows),
                        f"{messy} values in {column} use a different spelling for the same category.",
                        "Standardize categories. Review the spelling that will be kept.",
                        True,
                        True,
                        {"examples": messy_values[:8]},
                    )
                )

        if looks_like_id(column) and present:
            consistency_cells += len(present)
            changed = [value for value in present if canonical_id(value) != value.strip()]
            inconsistent_cells += len(changed)
            if changed:
                issues.append(
                    _issue(
                        "inconsistent_id",
                        column,
                        len(changed),
                        severity_from_ratio(len(changed) / rows),
                        f"{len(changed)} identifiers in {column} mix spaces, dashes, or letter case.",
                        "Normalize identifiers so C-001 and c 001 can match. Review the preview before you trust the merge.",
                        True,
                        True,
                        {"examples": changed[:8]},
                    )
                )
            buckets: dict[str, set[str]] = defaultdict(set)
            for value in present:
                buckets[canonical_id(value)].add(value.strip())
            collisions = {key: sorted(members) for key, members in buckets.items() if len(members) > 1}
            if collisions:
                affected = sum(1 for value in present if len(buckets[canonical_id(value)]) > 1)
                issues.append(
                    _issue(
                        "id_collision",
                        column,
                        affected,
                        "high",
                        f"{len(collisions)} identifier groups in {column} look like the same id written differently.",
                        "Confirm they are the same business entity before analytics joins on them.",
                        True,
                        True,
                        {"examples": list(collisions.values())[:6]},
                    )
                )

    comparable = df[columns].fillna("__NULL__")
    duplicate_rows = int(comparable.duplicated(keep="first").sum()) if rows else 0
    if duplicate_rows:
        issues.append(
            _issue(
                "duplicate",
                None,
                duplicate_rows,
                severity_from_ratio(duplicate_rows / rows),
                f"{duplicate_rows} extra rows repeat an earlier row exactly.",
                "Drop exact duplicates and keep the first copy. This does not delete similar-but-different rows.",
                True,
                False,
            )
        )

    completeness = 1 - (null_cells / total_cells)
    uniqueness = 1 - (duplicate_rows / rows)
    validity = 1.0 if checked_cells == 0 else 1 - (invalid_cells / checked_cells)
    consistency = 1.0 if consistency_cells == 0 else 1 - (inconsistent_cells / consistency_cells)
    for name, value in {
        "completeness": completeness,
        "validity": validity,
        "uniqueness": uniqueness,
        "consistency": consistency,
    }.items():
        if value < 0:
            if name == "completeness":
                completeness = 0
            elif name == "validity":
                validity = 0
            elif name == "uniqueness":
                uniqueness = 0
            else:
                consistency = 0
    validity = max(0.0, min(1.0, validity))
    consistency = max(0.0, min(1.0, consistency))
    completeness = max(0.0, min(1.0, completeness))
    uniqueness = max(0.0, min(1.0, uniqueness))
    score = 100 * (0.35 * completeness + 0.25 * uniqueness + 0.25 * validity + 0.15 * consistency)

    return {
        "score": round(score, 1),
        "completeness": round(completeness * 100, 1),
        "validity": round(validity * 100, 1),
        "uniqueness": round(uniqueness * 100, 1),
        "consistency": round(consistency * 100, 1),
        "issues": issues,
        "row_count": rows,
        "column_count": len(columns),
        "null_cells": null_cells,
        "duplicate_rows": duplicate_rows,
        "null_percent": round(100 * null_cells / total_cells, 1),
        "duplicate_percent": round(100 * duplicate_rows / rows, 1),
    }


def _synonym_keys() -> set[str]:
    from app.services.values import SYNONYMS

    return set(SYNONYMS)


def _most_common(present: list[str], members: set[str]) -> str:
    counts: dict[str, int] = {}
    allowed = {member.strip() for member in members}
    for value in present:
        text = value.strip()
        if text in allowed:
            counts[text] = counts.get(text, 0) + 1
    return sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))[0][0]


def _preferred(members: set[str], value: str) -> str:
    return canonical_category(value)


def profile_columns(df: pd.DataFrame) -> list[dict]:
    profiles = []
    for position, column in enumerate(df.columns):
        if column == "__row_id":
            continue
        values = df[column].tolist()
        present = [value for value in values if value is not None]
        null_count = len(values) - len(present)
        unique_count = len(set(present))
        inferred = _infer_type(column, present)
        numbers = [parse_number(value) for value in present]
        numbers = [value for value in numbers if value is not None]
        dates = [parse_date(value)[0] for value in present]
        dates = [value for value in dates if value is not None]
        min_value = max_value = mean_value = None
        if inferred in {"number", "integer"} and numbers:
            min_value = _num(min(numbers))
            max_value = _num(max(numbers))
            mean_value = _num(sum(numbers) / len(numbers))
        elif inferred == "date" and dates:
            min_value = min(dates).isoformat()
            max_value = max(dates).isoformat()
        samples = []
        for value in present:
            if value not in samples:
                samples.append(value)
            if len(samples) == 5:
                break
        profiles.append(
            {
                "name": column,
                "position": position,
                "inferred_type": inferred,
                "null_count": null_count,
                "unique_count": unique_count,
                "min_value": min_value,
                "max_value": max_value,
                "mean_value": mean_value,
                "sample_values": samples,
            }
        )
    return profiles


def _infer_type(column: str, present: list[str]) -> str:
    if not present:
        return "empty"
    if looks_like_email(column) or sum(is_email(value) for value in present) / len(present) >= 0.8:
        if sum(is_email(value) for value in present) / len(present) >= 0.6:
            return "email"
    number_hits = [parse_number(value) for value in present]
    parsed_numbers = [value for value in number_hits if value is not None]
    if len(parsed_numbers) / len(present) >= 0.6:
        if all(float(value).is_integer() for value in parsed_numbers):
            return "integer"
        return "number"
    date_hits = [parse_date(value)[0] for value in present]
    if sum(value is not None for value in date_hits) / len(present) >= 0.6:
        return "date"
    return "string"


def _num(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}"
