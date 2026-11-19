"""Database reads and writes for datasets. Routes and the pipeline share these."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import (
    ActivityEvent,
    Dataset,
    DatasetColumn,
    DatasetRecord,
    GoldRecord,
    LineageEdge,
    QualityIssue,
    QualityRule,
    QualitySnapshot,
    ValidationResult,
)
from app.services.frames import frame_records, records_frame, search_text
from app.services.quality import assess, profile_columns
from app.services.validation import default_rules

import pandas as pd


def get_dataset(db: Session, dataset_id: int, business_id: int | None = None) -> Dataset:
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise AppError("Dataset not found.", 404)
    if business_id is not None and dataset.business_id != business_id:
        raise AppError("Dataset not found.", 404)
    return dataset


def business_dataset_ids(db: Session, business_id: int) -> list[int]:
    return [row.id for row in db.query(Dataset.id).filter_by(business_id=business_id).all()]


def log_activity(
    db: Session,
    action: str,
    message: str,
    dataset_id: int | None = None,
    business_id: int | None = None,
) -> None:
    db.add(ActivityEvent(dataset_id=dataset_id, business_id=business_id, action=action, message=message))


def replace_layer(db: Session, dataset_id: int, layer: str, frame: pd.DataFrame) -> int:
    db.query(DatasetRecord).filter_by(dataset_id=dataset_id, layer=layer).delete()
    records = frame_records(frame)
    for index, record in enumerate(records):
        db.add(
            DatasetRecord(
                dataset_id=dataset_id,
                layer=layer,
                row_index=index,
                data=record,
                search_text=search_text(record),
                quarantined=False,
            )
        )
    db.flush()
    return len(records)


def load_layer(db: Session, dataset_id: int, layer: str) -> pd.DataFrame:
    rows = (
        db.query(DatasetRecord)
        .filter_by(dataset_id=dataset_id, layer=layer)
        .order_by(DatasetRecord.row_index)
        .all()
    )
    return records_frame([row.data for row in rows])


def save_profile(db: Session, dataset: Dataset, layer: str, frame: pd.DataFrame) -> dict:
    report = assess(frame)
    db.query(DatasetColumn).filter_by(dataset_id=dataset.id, layer=layer).delete()
    for column in profile_columns(frame):
        db.add(DatasetColumn(dataset_id=dataset.id, layer=layer, **column))
    db.query(QualityIssue).filter_by(dataset_id=dataset.id, layer=layer).delete()
    for issue in report["issues"]:
        db.add(QualityIssue(dataset_id=dataset.id, layer=layer, **issue))
    if report["score"] is not None:
        db.add(
            QualitySnapshot(
                dataset_id=dataset.id,
                layer=layer,
                score=report["score"],
                completeness=report["completeness"],
                validity=report["validity"],
                uniqueness=report["uniqueness"],
                consistency=report["consistency"],
                issue_count=len(report["issues"]),
                row_count=report["row_count"],
            )
        )
    if layer == "bronze":
        dataset.row_count = report["row_count"]
        dataset.column_count = report["column_count"]
        dataset.quality_score = report["score"]
        dataset.status = "profiled"
    db.flush()
    return report


def ensure_rules(db: Session, dataset_id: int, columns: list[str]) -> None:
    exists = db.query(QualityRule).filter_by(dataset_id=dataset_id).count()
    if exists:
        return
    for rule in default_rules(columns):
        db.add(QualityRule(dataset_id=dataset_id, **rule))
    db.flush()


def rule_dicts(db: Session, dataset_id: int) -> list[dict]:
    rules = db.query(QualityRule).filter_by(dataset_id=dataset_id).order_by(QualityRule.id).all()
    return [
        {
            "id": rule.id,
            "name": rule.name,
            "column_name": rule.column_name,
            "rule_type": rule.rule_type,
            "config": rule.config or {},
            "enabled": rule.enabled,
            "blocks_load": rule.blocks_load,
        }
        for rule in rules
    ]


def store_validation(db: Session, dataset_id: int, run_id: int | None, results: list[dict]) -> None:
    db.query(ValidationResult).filter_by(dataset_id=dataset_id).delete()
    for result in results:
        db.add(ValidationResult(dataset_id=dataset_id, run_id=run_id, **result))
    db.flush()


def mark_quarantine(db: Session, dataset_id: int, reasons: list[str]) -> int:
    rows = (
        db.query(DatasetRecord)
        .filter_by(dataset_id=dataset_id, layer="silver")
        .order_by(DatasetRecord.row_index)
        .all()
    )
    rejected = 0
    for row, reason in zip(rows, reasons):
        row.quarantined = bool(reason)
        row.quarantine_reason = reason or None
        if reason:
            rejected += 1
    if len(rows) != len(reasons):
        raise AppError("Quarantine results did not line up with the cleaned rows.")
    db.flush()
    return rejected


def replace_gold(db: Session, dataset_id: int, rows: list[GoldRecord]) -> None:
    db.query(GoldRecord).filter_by(dataset_id=dataset_id).delete()
    for row in rows:
        db.add(row)
    db.flush()


def replace_lineage(db: Session, dataset_id: int, run_id: int, edges: list[dict]) -> None:
    db.query(LineageEdge).filter_by(dataset_id=dataset_id).delete()
    for edge in edges:
        db.add(LineageEdge(dataset_id=dataset_id, run_id=run_id, **edge))
    db.flush()
