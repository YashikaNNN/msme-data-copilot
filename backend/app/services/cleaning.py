"""Cleaning operations run on a copy. Callers decide whether to store the result.

Bronze rows are never passed back as a mutation of the original frame.
"""

from __future__ import annotations

from app.services.values import (
    canonical_category,
    canonical_id,
    format_number,
    looks_like_amount,
    looks_like_category,
    looks_like_date,
    looks_like_id,
    looks_like_qty,
    modal_category,
    parse_date,
    parse_number,
)

import pandas as pd

STANDARD_OPERATIONS = [
    {"type": "trim_strings"},
    {"type": "normalize_ids"},
    {"type": "normalize_dates"},
    {"type": "coerce_numbers"},
    {"type": "standardize_categories"},
    {"type": "drop_duplicates"},
]


def apply_operations(df: pd.DataFrame, operations: list[dict]) -> tuple[pd.DataFrame, dict]:
    working = df.copy()
    if "__row_id" not in working.columns:
        working.insert(0, "__row_id", list(range(len(working))))
    before = working.copy()
    steps = []
    for operation in operations:
        working, step = _apply_one(working, operation)
        steps.append(step)
    summary = {
        "rows_before": int(len(before)),
        "rows_after": int(len(working)),
        "rows_removed": int(len(before) - len(working)),
        "cells_changed": _changed_cells(before, working),
        "changed_cells": _change_preview(before, working),
        "steps": steps,
        "sample_before": _sample(before),
        "sample_after": _sample(working),
    }
    return working, summary


def _apply_one(df: pd.DataFrame, operation: dict) -> tuple[pd.DataFrame, dict]:
    kind = operation.get("type") or operation.get("operation_type")
    column = operation.get("column") or operation.get("column_name")
    params = operation.get("params") or {}
    if kind == "trim_strings":
        return _trim(df)
    if kind == "drop_duplicates":
        return _drop_duplicates(df)
    if kind == "fill_missing":
        return _fill_missing(df, column, params)
    if kind == "normalize_dates":
        return _normalize_dates(df, column)
    if kind == "coerce_numbers":
        return _coerce_numbers(df, column)
    if kind == "standardize_categories":
        return _standardize_categories(df, column)
    if kind == "normalize_ids":
        return _normalize_ids(df, column)
    if kind == "rename_column":
        return _rename(df, params.get("from") or column, params.get("to"))
    if kind == "null_invalid":
        return _null_invalid(df, column)
    raise ValueError(f"Unknown cleaning operation: {kind}")


def _data_columns(df: pd.DataFrame) -> list[str]:
    return [column for column in df.columns if column != "__row_id"]


def _trim(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    out = df.copy()
    changed = 0
    for column in _data_columns(out):
        def _clean(value, column=column):
            nonlocal changed
            if value is None:
                return None
            text = " ".join(str(value).split())
            if text != value:
                changed += 1
            return text or None

        out[column] = out[column].map(_clean)
    return out, {"type": "trim_strings", "cells_changed": changed}


def _drop_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    columns = _data_columns(df)
    before = len(df)
    out = df.drop_duplicates(subset=columns, keep="first")
    return out, {"type": "drop_duplicates", "rows_removed": before - len(out)}


def _fill_missing(df: pd.DataFrame, column: str | None, params: dict) -> tuple[pd.DataFrame, dict]:
    if not column or column not in df.columns:
        raise ValueError("Choose a column before filling missing values.")
    strategy = params.get("strategy", "constant")
    out = df.copy()
    missing = out[column].isna() | out[column].eq(None)
    # None does not always count as NA in pandas object columns.
    mask = out[column].map(lambda value: value is None)
    count = int(mask.sum())
    if strategy == "drop_rows":
        out = out.loc[~mask]
        return out, {"type": "fill_missing", "column": column, "strategy": strategy, "rows_removed": count}
    if strategy == "constant":
        fill = params.get("value")
        if fill is None or str(fill).strip() == "":
            raise ValueError("A constant fill needs a value.")
        out.loc[mask, column] = str(fill)
        return out, {"type": "fill_missing", "column": column, "strategy": strategy, "cells_changed": count}
    present = [value for value in out[column].tolist() if value is not None]
    if strategy == "mode":
        if not present:
            raise ValueError(f"{column} has no value that can be used as the most common fill.")
        counts: dict[str, int] = {}
        for value in present:
            counts[value] = counts.get(value, 0) + 1
        chosen = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
        out.loc[mask, column] = chosen
        return out, {"type": "fill_missing", "column": column, "strategy": strategy, "value": chosen, "cells_changed": count}
    if strategy == "median":
        numbers = [parse_number(value) for value in present]
        numbers = sorted(value for value in numbers if value is not None)
        if not numbers:
            raise ValueError(f"{column} has no numbers, so a median cannot be calculated.")
        mid = numbers[len(numbers) // 2]
        out.loc[mask, column] = format_number(mid)
        return out, {"type": "fill_missing", "column": column, "strategy": strategy, "value": format_number(mid), "cells_changed": count}
    raise ValueError("Fill strategy must be constant, median, mode, or drop_rows.")


def _normalize_dates(df: pd.DataFrame, column: str | None) -> tuple[pd.DataFrame, dict]:
    out = df.copy()
    columns = [column] if column else [name for name in _data_columns(out) if looks_like_date(name)]
    changed = 0
    unparsed = 0
    for name in columns:
        if name not in out.columns:
            raise ValueError(f"Column {name} was not found.")

        def _convert(value):
            nonlocal changed, unparsed
            if value is None:
                return None
            parsed, _ambiguous = parse_date(str(value))
            if parsed is None:
                unparsed += 1
                return value
            iso = parsed.isoformat()
            if iso != value:
                changed += 1
            return iso

        out[name] = out[name].map(_convert)
    return out, {"type": "normalize_dates", "columns": columns, "cells_changed": changed, "left_unchanged": unparsed}


def _coerce_numbers(df: pd.DataFrame, column: str | None) -> tuple[pd.DataFrame, dict]:
    out = df.copy()
    columns = [column] if column else [
        name for name in _data_columns(out) if looks_like_amount(name) or looks_like_qty(name)
    ]
    changed = 0
    left = 0
    for name in columns:
        if name not in out.columns:
            raise ValueError(f"Column {name} was not found.")

        def _convert(value):
            nonlocal changed, left
            if value is None:
                return None
            parsed = parse_number(str(value))
            if parsed is None:
                left += 1
                return value
            text = format_number(parsed)
            if text != value:
                changed += 1
            return text

        out[name] = out[name].map(_convert)
    return out, {"type": "coerce_numbers", "columns": columns, "cells_changed": changed, "left_unchanged": left}


def _standardize_categories(df: pd.DataFrame, column: str | None) -> tuple[pd.DataFrame, dict]:
    out = df.copy()
    columns = [column] if column else [name for name in _data_columns(out) if looks_like_category(name)]
    changed = 0
    for name in columns:
        if name not in out.columns:
            raise ValueError(f"Column {name} was not found.")
        present = [value for value in out[name].tolist() if value is not None]
        mapping = modal_category(present)

        def _convert(value, mapping=mapping):
            nonlocal changed
            if value is None:
                return None
            new = mapping.get(value, canonical_category(value))
            if new != value:
                changed += 1
            return new

        out[name] = out[name].map(_convert)
    return out, {"type": "standardize_categories", "columns": columns, "cells_changed": changed}


def _normalize_ids(df: pd.DataFrame, column: str | None) -> tuple[pd.DataFrame, dict]:
    out = df.copy()
    columns = [column] if column else [name for name in _data_columns(out) if looks_like_id(name)]
    changed = 0
    for name in columns:
        if name not in out.columns:
            raise ValueError(f"Column {name} was not found.")

        def _convert(value):
            nonlocal changed
            if value is None:
                return None
            new = canonical_id(str(value))
            if new != value:
                changed += 1
            return new or None

        out[name] = out[name].map(_convert)
    return out, {"type": "normalize_ids", "columns": columns, "cells_changed": changed}


def _rename(df: pd.DataFrame, source: str | None, target: str | None) -> tuple[pd.DataFrame, dict]:
    if not source or not target:
        raise ValueError("Renaming a column needs both the current name and the new name.")
    if source not in df.columns:
        raise ValueError(f"Column {source} was not found.")
    if target in df.columns and target != source:
        raise ValueError(f"A column named {target} already exists.")
    out = df.rename(columns={source: target})
    return out, {"type": "rename_column", "from": source, "to": target}


def _null_invalid(df: pd.DataFrame, column: str | None) -> tuple[pd.DataFrame, dict]:
    if not column or column not in df.columns:
        raise ValueError("Choose a column before clearing invalid values.")
    out = df.copy()
    changed = 0

    def _convert(value):
        nonlocal changed
        if value is None:
            return None
        if looks_like_date(column):
            parsed, _ambiguous = parse_date(str(value))
            if parsed is None:
                changed += 1
                return None
            return value
        if looks_like_amount(column) or looks_like_qty(column):
            if parse_number(str(value)) is None:
                changed += 1
                return None
        return value

    out[column] = out[column].map(_convert)
    return out, {"type": "null_invalid", "column": column, "cells_changed": changed}


def _sample(df: pd.DataFrame, limit: int = 5) -> list[dict]:
    columns = _data_columns(df)
    return df[columns].head(limit).to_dict(orient="records")


def _changed_cells(before: pd.DataFrame, after: pd.DataFrame) -> int:
    after_by_id = {row["__row_id"]: row for row in after.to_dict(orient="records")}
    changed = 0
    removed = 0
    for row in before.to_dict(orient="records"):
        match = after_by_id.get(row["__row_id"])
        if match is None:
            removed += 1
            continue
        for column in _data_columns(before):
            if row.get(column) != match.get(column):
                changed += 1
    return changed


def _change_preview(before: pd.DataFrame, after: pd.DataFrame, limit: int = 40) -> list[dict]:
    after_by_id = {row["__row_id"]: row for row in after.to_dict(orient="records")}
    preview = []
    for row in before.to_dict(orient="records"):
        match = after_by_id.get(row["__row_id"])
        if match is None:
            preview.append({"row": int(row["__row_id"]) + 1, "column": "*", "before": "entire row", "after": "removed as a duplicate"})
        else:
            for column in _data_columns(before):
                if row.get(column) != match.get(column):
                    preview.append(
                        {
                            "row": int(row["__row_id"]) + 1,
                            "column": column,
                            "before": row.get(column),
                            "after": match.get(column),
                        }
                    )
        if len(preview) >= limit:
            break
    return preview
