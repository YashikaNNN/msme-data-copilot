"""Bronze → silver → gold pipeline.

Original uploaded rows stay in bronze. Cleaning writes silver. Only rows that
pass blocking validation are loaded into gold for analytics.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import CleaningOperation, GoldRecord, PipelineRun, PipelineStage
from app.services.cleaning import STANDARD_OPERATIONS, apply_operations
from app.services.frames import frame_records
from app.services.mapping import canonical_row, entity_for, suggest_mapping
from app.services.repository import (
    ensure_rules,
    get_dataset,
    load_layer,
    log_activity,
    mark_quarantine,
    replace_gold,
    replace_layer,
    replace_lineage,
    rule_dicts,
    save_profile,
    store_validation,
)
from app.services.validation import evaluate
from app.services.values import parse_date, parse_number


STAGES = ["extract", "profile", "clean", "validate", "transform", "load"]


def run_pipeline(db: Session, dataset_id: int) -> PipelineRun:
    dataset = get_dataset(db, dataset_id)
    run = PipelineRun(dataset_id=dataset.id, status="running")
    db.add(run)
    db.flush()
    stages = {}
    for name in STAGES:
        stage = PipelineStage(run_id=run.id, name=name, status="pending")
        db.add(stage)
        stages[name] = stage
    db.flush()

    try:
        bronze = load_layer(db, dataset.id, "bronze")
        if bronze.empty:
            raise AppError("This dataset has no uploaded rows to process.")
        _start(stages["extract"], len(bronze))
        _finish(stages["extract"], len(bronze), {"source": "bronze records"})

        _start(stages["profile"], len(bronze))
        report = save_profile(db, dataset, "bronze", bronze)
        ensure_rules(db, dataset.id, list(bronze.columns))
        _finish(stages["profile"], len(bronze), {"quality_score": report["score"], "issues": len(report["issues"])})

        _start(stages["clean"], len(bronze))
        recipe = _cleaning_recipe(db, dataset.id)
        silver, summary = apply_operations(bronze, recipe)
        replace_layer(db, dataset.id, "silver", silver)
        silver_report = save_profile(db, dataset, "silver", silver)
        dataset.status = "cleaned"
        _finish(
            stages["clean"],
            len(silver),
            {
                "rows_removed": summary["rows_removed"],
                "cells_changed": summary["cells_changed"],
                "silver_quality_score": silver_report["score"],
            },
        )

        _start(stages["validate"], len(silver))
        checked = evaluate(silver, rule_dicts(db, dataset.id))
        store_validation(db, dataset.id, run.id, checked["results"])
        rejected = mark_quarantine(db, dataset.id, checked["reasons"])
        dataset.status = "validated"
        _finish(stages["validate"], len(silver) - rejected, {"rejected": rejected, "rules": len(checked["results"])})

        _start(stages["transform"], len(silver))
        mapping = suggest_mapping(list(silver.columns))
        entity = entity_for(dataset.category, list(silver.columns))
        gold_rows = _to_gold(dataset.id, entity, silver, mapping, checked["reasons"])
        _finish(stages["transform"], len(gold_rows), {"entity": entity, "mapping": {k: v for k, v in mapping.items() if v}})

        _start(stages["load"], len(gold_rows))
        replace_gold(db, dataset.id, gold_rows)
        _finish(stages["load"], len(gold_rows), {"table": "gold_records"})

        filename = dataset.files[0].original_filename if dataset.files else dataset.name
        replace_lineage(
            db,
            dataset.id,
            run.id,
            [
                {"source": filename, "target": f"bronze:{dataset.name}", "stage": "extract", "description": "Original rows stored without changes."},
                {"source": f"bronze:{dataset.name}", "target": f"silver:{dataset.name}", "stage": "clean", "description": "Trimmed, standardized copy. Bronze was not overwritten."},
                {"source": f"silver:{dataset.name}", "target": f"validated:{dataset.name}", "stage": "validate", "description": "Blocking rule failures were quarantined and kept for review."},
                {"source": f"validated:{dataset.name}", "target": f"gold:{entity}", "stage": "load", "description": "Trusted rows loaded for analytics."},
            ],
        )
        run.records_processed = len(bronze)
        run.records_rejected = rejected
        run.records_loaded = len(gold_rows)
        run.status = "success" if gold_rows else "partial"
        run.finished_at = datetime.now(timezone.utc)
        dataset.status = "loaded" if gold_rows else "validated"
        log_activity(
            db,
            "pipeline",
            f"Pipeline for {dataset.name} finished with {len(gold_rows)} trusted rows and {rejected} quarantined rows.",
            dataset.id,
            business_id=dataset.business_id,
        )
    except Exception as exc:
        message = exc.message if isinstance(exc, AppError) else "The pipeline stopped because of an unexpected error."
        run.status = "failed"
        run.error_message = message
        run.finished_at = datetime.now(timezone.utc)
        dataset.status = "failed"
        for stage in stages.values():
            if stage.status == "running":
                stage.status = "failed"
                stage.error_message = message
                stage.finished_at = datetime.now(timezone.utc)
        log_activity(
            db,
            "pipeline_failed",
            f"Pipeline for {dataset.name} failed: {message}",
            dataset.id,
            business_id=dataset.business_id,
        )
        if not isinstance(exc, AppError):
            raise
    db.flush()
    return run


def refresh_references(db: Session, business_id: int | None = None) -> list[dict]:
    """Flag sales that point at a product or customer id the workspace does not know.

    This runs only when a product or customer dataset has already been loaded.
    It does not invent a match.
    """

    from app.models import ValidationResult
    from app.services.repository import business_dataset_ids

    product_query = db.query(GoldRecord).filter_by(entity="product")
    customer_query = db.query(GoldRecord).filter_by(entity="customer")
    sales_query = db.query(GoldRecord).filter_by(entity="sale")
    if business_id is not None:
        ids = business_dataset_ids(db, business_id)
        if not ids:
            return []
        product_query = product_query.filter(GoldRecord.dataset_id.in_(ids))
        customer_query = customer_query.filter(GoldRecord.dataset_id.in_(ids))
        sales_query = sales_query.filter(GoldRecord.dataset_id.in_(ids))

    products = {row.product_id for row in product_query if row.product_id}
    customers = {row.customer_id for row in customer_query if row.customer_id}
    findings = []
    sales = sales_query.all()
    by_dataset: dict[int, list[GoldRecord]] = {}
    for row in sales:
        by_dataset.setdefault(row.dataset_id, []).append(row)

    for dataset_id, rows in by_dataset.items():
        db.query(ValidationResult).filter(
            ValidationResult.dataset_id == dataset_id,
            ValidationResult.rule_name.in_(["Known product", "Known customer"]),
        ).delete(synchronize_session=False)
        if products:
            missing = sorted({row.product_id for row in rows if row.product_id and row.product_id not in products})
            status = "passed" if not missing else "warning"
            message = "Every sales product id exists in the product dataset." if not missing else (
                f"{len(missing)} product id(s) in sales are not in the product dataset: {', '.join(missing[:8])}."
            )
            db.add(
                ValidationResult(
                    dataset_id=dataset_id,
                    rule_name="Known product",
                    column_name="product_id",
                    status=status,
                    affected_count=len(missing),
                    message=message,
                )
            )
            findings.append({"dataset_id": dataset_id, "check": "product", "status": status, "affected_count": len(missing), "message": message})
        if customers:
            missing = sorted({row.customer_id for row in rows if row.customer_id and row.customer_id not in customers})
            status = "passed" if not missing else "warning"
            message = "Every sales customer id exists in the customer dataset." if not missing else (
                f"{len(missing)} customer id(s) in sales are not in the customer dataset: {', '.join(missing[:8])}."
            )
            db.add(
                ValidationResult(
                    dataset_id=dataset_id,
                    rule_name="Known customer",
                    column_name="customer_id",
                    status=status,
                    affected_count=len(missing),
                    message=message,
                )
            )
            findings.append({"dataset_id": dataset_id, "check": "customer", "status": status, "affected_count": len(missing), "message": message})
    db.flush()
    return findings


def _to_gold(dataset_id: int, entity: str, frame, mapping: dict, reasons: list[str]) -> list[GoldRecord]:
    records = frame_records(frame)
    gold: list[GoldRecord] = []
    for index, record in enumerate(records):
        if index < len(reasons) and reasons[index]:
            continue
        canon = canonical_row(record, mapping)
        event_text = canon.get("order_date") or canon.get("expense_date") or canon.get("signup_date")
        parsed_date = parse_date(event_text)[0] if event_text else None
        quantity_text = canon.get("quantity")
        if quantity_text is None:
            quantity_text = canon.get("stock_qty")
        if entity == "inventory":
            amount_text = canon.get("unit_cost")
        elif entity == "product":
            amount_text = canon.get("unit_price")
        else:
            amount_text = canon.get("amount")
        product_name = canon.get("product_name")
        customer_name = canon.get("customer_name")
        gold.append(
            GoldRecord(
                dataset_id=dataset_id,
                entity=entity,
                event_date=parsed_date,
                customer_id=canon.get("customer_id"),
                product_id=canon.get("product_id"),
                product_name=product_name,
                category=canon.get("category") or canon.get("segment"),
                quantity=_number(quantity_text),
                amount=_number(amount_text),
                email=canon.get("email"),
                name=customer_name or (product_name if entity in {"product", "inventory"} else None),
                extra={key: value for key, value in canon.items()},
            )
        )
    return gold


def _cleaning_recipe(db: Session, dataset_id: int) -> list[dict]:
    applied = (
        db.query(CleaningOperation)
        .filter_by(dataset_id=dataset_id, status="applied")
        .order_by(CleaningOperation.id.desc())
        .first()
    )
    if applied and applied.params and applied.params.get("operations"):
        return applied.params["operations"]
    return STANDARD_OPERATIONS


def _number(value: str | None):
    if value is None:
        return None
    parsed = parse_number(str(value))
    if parsed is None:
        return None
    return round(parsed, 2)


def _start(stage: PipelineStage, records_in: int) -> None:
    stage.status = "running"
    stage.started_at = datetime.now(timezone.utc)
    stage.records_in = records_in


def _finish(stage: PipelineStage, records_out: int, details: dict) -> None:
    stage.status = "success"
    stage.finished_at = datetime.now(timezone.utc)
    stage.records_out = records_out
    stage.details = details
