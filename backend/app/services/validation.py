"""Configurable validation rules.

A failing rule that blocks loading quarantines the row. The row stays in the
cleaned silver layer so it can be reviewed. It is not copied into analytics.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from app.services.values import (
    is_email,
    looks_like_amount,
    looks_like_date,
    looks_like_email,
    looks_like_id,
    looks_like_qty,
    parse_date,
    parse_number,
)

RULE_TYPES = {
    "not_null",
    "unique",
    "numeric",
    "non_negative",
    "positive_integer",
    "non_negative_integer",
    "valid_date",
    "no_future_date",
    "email",
}


def default_rules(columns: list[str]) -> list[dict]:
    rules: list[dict] = []
    seen: set[tuple[str, str]] = set()

    def add(column: str, rule_type: str, blocks: bool, name: str | None = None) -> None:
        key = (column, rule_type)
        if key in seen:
            return
        seen.add(key)
        rules.append(
            {
                "name": name or f"{column} {rule_type.replace('_', ' ')}",
                "column_name": column,
                "rule_type": rule_type,
                "config": {},
                "enabled": True,
                "blocks_load": blocks,
            }
        )

    for column in columns:
        if looks_like_email(column):
            add(column, "not_null", True)
            add(column, "email", True)
        elif looks_like_date(column):
            add(column, "valid_date", True)
            add(column, "no_future_date", False)
        elif looks_like_id(column):
            add(column, "not_null", True)
            add(column, "unique", False)
        elif looks_like_qty(column):
            if "stock" in column.lower():
                add(column, "non_negative_integer", True)
            else:
                add(column, "positive_integer", True)
        elif looks_like_amount(column):
            add(column, "numeric", True)
            add(column, "non_negative", True)
    return rules


def evaluate(df: pd.DataFrame, rules: list[dict], today: date | None = None) -> dict:
    today = today or date.today()
    results = []
    reasons: list[list[str]] = [[] for _ in range(len(df))]

    for rule in rules:
        if not rule.get("enabled", True):
            continue
        column = rule["column_name"]
        rule_type = rule["rule_type"]
        if column not in df.columns:
            results.append(
                {
                    "rule_name": rule["name"],
                    "column_name": column,
                    "status": "warning",
                    "affected_count": 0,
                    "message": f"Column {column} is not in this dataset, so the rule was skipped.",
                }
            )
            continue
        failed_indexes = _failures(df, column, rule_type, today)
        affected = len(failed_indexes)
        status = "passed" if affected == 0 else ("warning" if not rule.get("blocks_load", True) else "failed")
        if rule_type == "no_future_date" and affected:
            status = "warning"
        results.append(
            {
                "rule_name": rule["name"],
                "column_name": column,
                "status": status,
                "affected_count": affected,
                "message": _message(rule, affected),
            }
        )
        if affected and rule.get("blocks_load", True) and rule_type != "no_future_date":
            for index in failed_indexes:
                reasons[index].append(f"{column}: {rule_type.replace('_', ' ')}")

    return {"results": results, "reasons": [" ; ".join(item) if item else "" for item in reasons]}


def _failures(df: pd.DataFrame, column: str, rule_type: str, today: date) -> list[int]:
    failed: list[int] = []
    values = df[column].tolist()
    if rule_type == "unique":
        seen: dict[str, int] = {}
        for index, value in enumerate(values):
            if value is None:
                continue
            if value in seen:
                failed.append(index)
                if seen[value] not in failed:
                    failed.append(seen[value])
            else:
                seen[value] = index
        return sorted(set(failed))

    for index, value in enumerate(values):
        if rule_type == "not_null":
            if value is None:
                failed.append(index)
            continue
        if value is None:
            continue
        if rule_type == "email" and not is_email(str(value)):
            failed.append(index)
        elif rule_type == "valid_date" and parse_date(str(value))[0] is None:
            failed.append(index)
        elif rule_type == "no_future_date":
            parsed, _ambiguous = parse_date(str(value))
            if parsed is not None and parsed > today:
                failed.append(index)
        elif rule_type in {"numeric", "non_negative", "positive_integer", "non_negative_integer"}:
            number = parse_number(str(value))
            if number is None:
                failed.append(index)
            elif rule_type == "non_negative" and number < 0:
                failed.append(index)
            elif rule_type == "positive_integer" and (number <= 0 or not float(number).is_integer()):
                failed.append(index)
            elif rule_type == "non_negative_integer" and (number < 0 or not float(number).is_integer()):
                failed.append(index)
    return failed


def _message(rule: dict, affected: int) -> str:
    if affected == 0:
        return f"{rule['name']} passed."
    if rule.get("blocks_load", True) and rule["rule_type"] != "no_future_date":
        return f"{affected} row(s) failed {rule['name']} and will be kept out of analytics until they are fixed."
    return f"{affected} row(s) raised a warning for {rule['name']}. They stay in analytics, but they need a look."
