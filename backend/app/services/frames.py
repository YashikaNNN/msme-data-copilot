"""Safe table reading. Uploaded files are data, never code."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from app.errors import AppError

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".json"}


def normalize_frame(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    notes: list[str] = []
    columns: list[str] = []
    seen: dict[str, int] = {}
    for raw in df.columns:
        name = str(raw).strip() or "unnamed"
        if name in seen:
            seen[name] += 1
            renamed = f"{name}_{seen[name]}"
            notes.append(f"Duplicate column '{name}' was renamed to '{renamed}' so both can be profiled.")
            name = renamed
        else:
            seen[name] = 1
        columns.append(name)

    out = df.copy()
    out.columns = columns

    def clean_cell(value):
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        text = str(value).strip()
        if text == "" or text.lower() in {"nan", "none", "null", "nat"}:
            return None
        return text

    for column in out.columns:
        out[column] = out[column].map(clean_cell)
    return out, notes


def read_table(path: Path, max_rows: int) -> tuple[pd.DataFrame, list[str]]:
    ext = path.suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise AppError("Only CSV, XLSX, and JSON files can be uploaded.")

    try:
        if ext == ".csv":
            frame = pd.read_csv(path, dtype=str, keep_default_na=True)
        elif ext == ".xlsx":
            frame = pd.read_excel(path, dtype=str, engine="openpyxl")
        else:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                payload = payload.get("data", payload.get("records"))
            if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
                raise AppError("JSON files must contain a list of objects, or an object with a data list.")
            frame = pd.DataFrame(payload)
    except AppError:
        raise
    except Exception as exc:
        raise AppError(f"The file could not be read as a table: {exc}") from exc

    if frame.shape[1] == 0:
        raise AppError("The file has no columns.")
    if len(frame) > max_rows:
        raise AppError(f"This file has {len(frame)} rows. The limit is {max_rows}.")

    return normalize_frame(frame)


def frame_records(df: pd.DataFrame) -> list[dict]:
    columns = [column for column in df.columns if column != "__row_id"]
    records = []
    for row in df[columns].to_dict(orient="records"):
        records.append({key: (None if value is None else str(value)) for key, value in row.items()})
    return records


def records_frame(records: list[dict]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame()
    frame, _notes = normalize_frame(pd.DataFrame(records))
    return frame


def search_text(record: dict) -> str:
    return " ".join(str(value).lower() for value in record.values() if value is not None)
