"""HTTP API. Metrics and answers come from stored data, not placeholders."""

from __future__ import annotations

import io
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import current_business, optional_token
from app.errors import AppError
from app.models import (
    ActivityEvent,
    Business,
    ChatMessage,
    ChatSession,
    CleaningOperation,
    Dataset,
    DatasetColumn,
    DatasetRecord,
    GoldRecord,
    LineageEdge,
    PipelineRun,
    PipelineStage,
    QualityIssue,
    QualityRule,
    QualitySnapshot,
    ValidationResult,
)
from app.services import analytics, copilot
from app.services.auth import (
    business_payload,
    login_business,
    logout_session,
    register_business,
)
from app.services.cleaning import STANDARD_OPERATIONS, apply_operations
from app.services.frames import records_frame
from app.services.ingest import CATEGORIES, create_dataset, delete_dataset, load_samples, sample_catalog
from app.services.mapping import suggest_mapping
from app.services.pipeline import refresh_references, run_pipeline
from app.services.repository import (
    get_dataset,
    load_layer,
    log_activity,
    mark_quarantine,
    replace_layer,
    rule_dicts,
    save_profile,
    store_validation,
)
from app.services.validation import RULE_TYPES, evaluate

router = APIRouter(prefix="/api/v1")


def _num(value):
    return None if value is None else float(value)


def _dt(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()


def _dataset_brief(dataset: Dataset) -> dict:
    return {
        "id": dataset.id,
        "name": dataset.name,
        "description": dataset.description,
        "category": dataset.category,
        "status": dataset.status,
        "is_sample": dataset.is_sample,
        "row_count": dataset.row_count,
        "column_count": dataset.column_count,
        "quality_score": _num(dataset.quality_score),
        "created_at": _dt(dataset.created_at),
        "updated_at": _dt(dataset.updated_at),
    }


def _issue(issue: QualityIssue) -> dict:
    return {
        "id": issue.id,
        "layer": issue.layer,
        "category": issue.category,
        "column_name": issue.column_name,
        "affected_count": issue.affected_count,
        "severity": issue.severity,
        "explanation": issue.explanation,
        "suggested_resolution": issue.suggested_resolution,
        "auto_fixable": issue.auto_fixable,
        "manual_review": issue.manual_review,
        "details": issue.details or {},
    }


def _column(column: DatasetColumn) -> dict:
    return {
        "name": column.name,
        "position": column.position,
        "inferred_type": column.inferred_type,
        "null_count": column.null_count,
        "unique_count": column.unique_count,
        "min_value": column.min_value,
        "max_value": column.max_value,
        "mean_value": column.mean_value,
        "sample_values": column.sample_values or [],
    }


def _run(run: PipelineRun) -> dict:
    return {
        "id": run.id,
        "dataset_id": run.dataset_id,
        "status": run.status,
        "started_at": _dt(run.started_at),
        "finished_at": _dt(run.finished_at),
        "records_processed": run.records_processed,
        "records_rejected": run.records_rejected,
        "records_loaded": run.records_loaded,
        "error_message": run.error_message,
        "duration_seconds": _duration(run.started_at, run.finished_at),
    }


def _duration(start: datetime | None, end: datetime | None) -> float | None:
    if start is None or end is None:
        return None
    return round((end - start).total_seconds(), 3)


def _rule(rule: QualityRule) -> dict:
    return {
        "id": rule.id,
        "dataset_id": rule.dataset_id,
        "name": rule.name,
        "column_name": rule.column_name,
        "rule_type": rule.rule_type,
        "enabled": rule.enabled,
        "blocks_load": rule.blocks_load,
        "config": rule.config or {},
    }


def _operations(body: dict) -> list[dict]:
    operations = body.get("operations")
    if not isinstance(operations, list) or not operations:
        raise AppError("Choose at least one cleaning step.")
    cleaned = []
    for item in operations:
        if not isinstance(item, dict) or not item.get("type"):
            raise AppError("Each cleaning step needs a type.")
        cleaned.append(item)
    return cleaned


def _owned(db: Session, dataset_id: int, business: Business) -> Dataset:
    return get_dataset(db, dataset_id, business_id=business.id)


def _owned_ids(db: Session, business: Business) -> list[int]:
    return [row.id for row in db.query(Dataset.id).filter_by(business_id=business.id).all()]


def _trusted_frame(db: Session, dataset: Dataset):
    success = db.query(PipelineRun).filter_by(dataset_id=dataset.id, status="success").count()
    partial = db.query(PipelineRun).filter_by(dataset_id=dataset.id, status="partial").count()
    if not success and not partial:
        raise AppError(
            "Run the pipeline before downloading the trusted file so quarantined rows stay out of the export.",
            409,
        )
    rows = (
        db.query(DatasetRecord)
        .filter_by(dataset_id=dataset.id, layer="silver", quarantined=False)
        .order_by(DatasetRecord.row_index)
        .all()
    )
    return records_frame([row.data for row in rows])


def _csv(frame, filename: str):
    import pandas as pd

    if not isinstance(frame, pd.DataFrame):
        frame = records_frame([])
    buffer = io.StringIO()
    frame.to_csv(buffer, index=False)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _xlsx(frame, filename: str):
    import pandas as pd

    if not isinstance(frame, pd.DataFrame):
        frame = pd.DataFrame()
    buffer = io.BytesIO()
    frame.to_excel(buffer, index=False)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _auth_response(business: Business, token: str) -> dict:
    return {"token": token, "business": business_payload(business)}


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    db.query(Dataset.id).limit(1).all()
    return {"status": "ok", "service": "msme-data-copilot"}


@router.post("/auth/register")
def register(body: dict, db: Session = Depends(get_db)) -> dict:
    business, token = register_business(
        db,
        business_name=str(body.get("business_name") or ""),
        owner_name=str(body.get("owner_name") or ""),
        email=str(body.get("email") or ""),
        password=str(body.get("password") or ""),
    )
    return _auth_response(business, token)


@router.post("/auth/login")
def login(body: dict, db: Session = Depends(get_db)) -> dict:
    business, token = login_business(
        db,
        email=str(body.get("email") or ""),
        password=str(body.get("password") or ""),
    )
    return _auth_response(business, token)


@router.post("/auth/logout")
def logout(
    db: Session = Depends(get_db),
    token: str | None = Depends(optional_token),
) -> dict:
    logout_session(db, token)
    return {"ok": True}


@router.get("/auth/me")
def me(business: Business = Depends(current_business)) -> dict:
    return {"business": business_payload(business)}


@router.get("/dashboard")
def dashboard(business: Business = Depends(current_business), db: Session = Depends(get_db)) -> dict:
    datasets = db.query(Dataset).filter_by(business_id=business.id).order_by(Dataset.created_at.desc()).all()
    scores = [_num(dataset.quality_score) for dataset in datasets if dataset.quality_score is not None]
    ids = [dataset.id for dataset in datasets]
    runs = db.query(PipelineRun).filter(PipelineRun.dataset_id.in_(ids)).all() if ids else []
    activity = (
        db.query(ActivityEvent)
        .filter_by(business_id=business.id)
        .order_by(ActivityEvent.created_at.desc())
        .limit(8)
        .all()
    )
    sales = analytics.sales_report(db, business.id)
    return {
        "business": business_payload(business),
        "total_datasets": len(datasets),
        "total_records": int(sum(dataset.row_count for dataset in datasets)),
        "quality_score": round(sum(scores) / len(scores), 1) if scores else None,
        "quality_note": None if scores else "Upload a dataset to calculate a quality score.",
        "pipeline_runs": len(runs),
        "successful_runs": sum(1 for run in runs if run.status == "success"),
        "failed_runs": sum(1 for run in runs if run.status == "failed"),
        "partial_runs": sum(1 for run in runs if run.status == "partial"),
        "recent_datasets": [_dataset_brief(dataset) for dataset in datasets[:5]],
        "recent_activity": [
            {
                "id": item.id,
                "dataset_id": item.dataset_id,
                "action": item.action,
                "message": item.message,
                "created_at": _dt(item.created_at),
            }
            for item in activity
        ],
        "business_metrics": analytics.overview(db, business.id),
        "revenue_by_month": sales.get("by_month") if sales.get("available") else [],
        "workflow": {
            "uploaded": len(datasets) > 0,
            "quality_checked": any(dataset.quality_score is not None for dataset in datasets),
            "cleaned": any(dataset.status in {"cleaned", "validated", "loaded"} for dataset in datasets),
            "analytics_ready": bool(sales.get("available"))
            or any(dataset.status == "loaded" for dataset in datasets),
        },
    }


@router.get("/datasets")
def list_datasets(business: Business = Depends(current_business), db: Session = Depends(get_db)) -> dict:
    datasets = db.query(Dataset).filter_by(business_id=business.id).order_by(Dataset.created_at.desc()).all()
    return {"items": [_dataset_brief(dataset) for dataset in datasets]}


@router.post("/datasets/upload")
async def upload_dataset(
    file: UploadFile = File(...),
    name: str = Form(...),
    category: str = Form(...),
    description: str = Form(""),
    business: Business = Depends(current_business),
    db: Session = Depends(get_db),
) -> dict:
    content = await file.read()
    dataset = create_dataset(
        db,
        name=name,
        description=description,
        category=category,
        filename=file.filename or "upload.csv",
        content=content,
        content_type=file.content_type,
        business_id=business.id,
    )
    return dataset_detail(dataset.id, business, db)


@router.get("/datasets/{dataset_id}")
def dataset_detail(
    dataset_id: int,
    business: Business = Depends(current_business),
    db: Session = Depends(get_db),
) -> dict:
    dataset = _owned(db, dataset_id, business)
    columns = (
        db.query(DatasetColumn)
        .filter_by(dataset_id=dataset.id)
        .order_by(DatasetColumn.layer, DatasetColumn.position)
        .all()
    )
    bronze_columns = [column.name for column in columns if column.layer == "bronze"]
    snapshots = (
        db.query(QualitySnapshot)
        .filter_by(dataset_id=dataset.id)
        .order_by(QualitySnapshot.created_at.desc())
        .limit(12)
        .all()
    )
    preview = (
        db.query(DatasetRecord)
        .filter_by(dataset_id=dataset.id, layer="bronze")
        .order_by(DatasetRecord.row_index)
        .limit(8)
        .all()
    )
    silver_count = db.query(func.count(DatasetRecord.id)).filter_by(dataset_id=dataset.id, layer="silver").scalar()
    latest_run = (
        db.query(PipelineRun)
        .filter_by(dataset_id=dataset.id)
        .order_by(PipelineRun.started_at.desc())
        .first()
    )
    return {
        **_dataset_brief(dataset),
        "files": [
            {
                "original_filename": item.original_filename,
                "size_bytes": item.size_bytes,
                "content_type": item.content_type,
                "checksum": item.checksum,
                "uploaded_at": _dt(item.created_at),
            }
            for item in dataset.files
        ],
        "columns": [_column(column) for column in columns],
        "suggested_mapping": suggest_mapping(bronze_columns),
        "preview": [row.data for row in preview],
        "silver_rows": int(silver_count or 0),
        "latest_pipeline": _run(latest_run) if latest_run else None,
        "history": [
            {
                "layer": item.layer,
                "score": _num(item.score),
                "completeness": _num(item.completeness),
                "validity": _num(item.validity),
                "uniqueness": _num(item.uniqueness),
                "consistency": _num(item.consistency),
                "issue_count": item.issue_count,
                "row_count": item.row_count,
                "created_at": _dt(item.created_at),
            }
            for item in snapshots
        ],
        "categories": sorted(CATEGORIES),
        "next_steps": _next_steps(dataset, int(silver_count or 0), latest_run),
    }


def _next_steps(dataset: Dataset, silver_rows: int, latest_run: PipelineRun | None) -> list[dict]:
    steps = [
        {
            "key": "quality",
            "label": "Review data quality",
            "href": f"/app/quality/{dataset.id}",
            "done": dataset.quality_score is not None,
        },
        {
            "key": "clean",
            "label": "Clean & save a trusted copy",
            "href": f"/app/cleaning/{dataset.id}",
            "done": silver_rows > 0 or dataset.status in {"cleaned", "validated", "loaded"},
        },
        {
            "key": "pipeline",
            "label": "Validate & load for analytics",
            "href": f"/app/datasets/{dataset.id}",
            "done": latest_run is not None and latest_run.status in {"success", "partial"},
        },
        {
            "key": "analytics",
            "label": "View business insights",
            "href": "/app/analytics",
            "done": dataset.status == "loaded",
        },
    ]
    return steps


@router.delete("/datasets/{dataset_id}", status_code=204, response_class=Response)
def remove_dataset(
    dataset_id: int,
    business: Business = Depends(current_business),
    db: Session = Depends(get_db),
) -> Response:
    delete_dataset(db, _owned(db, dataset_id, business))
    return Response(status_code=204)


@router.get("/datasets/{dataset_id}/records")
def dataset_records(
    dataset_id: int,
    layer: str = Query("bronze"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    q: str = Query(""),
    business: Business = Depends(current_business),
    db: Session = Depends(get_db),
) -> dict:
    if layer not in {"bronze", "silver"}:
        raise AppError("Layer must be bronze or silver.")
    _owned(db, dataset_id, business)
    query = db.query(DatasetRecord).filter_by(dataset_id=dataset_id, layer=layer)
    cleaned = q.replace("%", "").replace("_", "").strip().lower()
    if cleaned:
        query = query.filter(DatasetRecord.search_text.contains(cleaned))
    total = query.count()
    rows = query.order_by(DatasetRecord.row_index).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [
            {
                "row_index": row.row_index,
                "data": row.data,
                "quarantined": row.quarantined,
                "quarantine_reason": row.quarantine_reason,
            }
            for row in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/datasets/{dataset_id}/quality")
def dataset_quality(
    dataset_id: int,
    layer: str = Query("bronze"),
    business: Business = Depends(current_business),
    db: Session = Depends(get_db),
) -> dict:
    dataset = _owned(db, dataset_id, business)
    if layer not in {"bronze", "silver"}:
        raise AppError("Layer must be bronze or silver.")
    issues = (
        db.query(QualityIssue)
        .filter_by(dataset_id=dataset.id, layer=layer)
        .order_by(QualityIssue.affected_count.desc())
        .all()
    )
    snapshot = (
        db.query(QualitySnapshot)
        .filter_by(dataset_id=dataset.id, layer=layer)
        .order_by(QualitySnapshot.created_at.desc())
        .first()
    )
    return {
        "dataset": _dataset_brief(dataset),
        "layer": layer,
        "score": _num(snapshot.score) if snapshot else None,
        "completeness": _num(snapshot.completeness) if snapshot else None,
        "validity": _num(snapshot.validity) if snapshot else None,
        "uniqueness": _num(snapshot.uniqueness) if snapshot else None,
        "consistency": _num(snapshot.consistency) if snapshot else None,
        "issues": [_issue(issue) for issue in issues],
        "note": None if snapshot else "This layer has not been profiled yet.",
        "plain_summary": _quality_plain_summary(snapshot, issues),
    }


def _quality_plain_summary(snapshot, issues: list[QualityIssue]) -> str:
    if snapshot is None:
        return "Upload and open this dataset to generate a quality report."
    missing = sum(issue.affected_count for issue in issues if issue.category in {"missing_values", "completeness"})
    duplicates = sum(issue.affected_count for issue in issues if "duplicate" in (issue.category or ""))
    invalid = sum(
        issue.affected_count
        for issue in issues
        if issue.category in {"invalid_dates", "invalid_amounts", "validity", "invalid_values"}
    )
    return (
        f"Overall quality is {float(snapshot.score):.1f}%. "
        f"About {missing} missing-value findings, {duplicates} duplicate findings, "
        f"and {invalid} invalid-value findings need attention."
    )


@router.get("/quality/overview")
def quality_overview(business: Business = Depends(current_business), db: Session = Depends(get_db)) -> dict:
    datasets = db.query(Dataset).filter_by(business_id=business.id).order_by(Dataset.created_at.desc()).all()
    items = []
    for dataset in datasets:
        snapshot = (
            db.query(QualitySnapshot)
            .filter_by(dataset_id=dataset.id, layer="bronze")
            .order_by(QualitySnapshot.created_at.desc())
            .first()
        )
        issue_count = db.query(func.count(QualityIssue.id)).filter_by(dataset_id=dataset.id, layer="bronze").scalar()
        items.append(
            {
                **_dataset_brief(dataset),
                "issue_count": int(issue_count or 0),
                "dimensions": None
                if snapshot is None
                else {
                    "completeness": _num(snapshot.completeness),
                    "validity": _num(snapshot.validity),
                    "uniqueness": _num(snapshot.uniqueness),
                    "consistency": _num(snapshot.consistency),
                },
            }
        )
    return {"items": items}


@router.post("/datasets/{dataset_id}/cleaning/preview")
def preview_cleaning(
    dataset_id: int,
    body: dict,
    business: Business = Depends(current_business),
    db: Session = Depends(get_db),
) -> dict:
    dataset = _owned(db, dataset_id, business)
    operations = _operations(body)
    frame = load_layer(db, dataset.id, "bronze")
    try:
        _cleaned, summary = apply_operations(frame, operations)
    except ValueError as exc:
        raise AppError(str(exc)) from exc
    db.add(
        CleaningOperation(
            dataset_id=dataset.id,
            operation_type="preview",
            params={"operations": operations},
            status="preview",
            summary={key: value for key, value in summary.items() if key != "sample_before"},
        )
    )
    summary["dataset_id"] = dataset.id
    summary["saved"] = False
    return summary


@router.post("/datasets/{dataset_id}/cleaning/apply")
def apply_cleaning(
    dataset_id: int,
    body: dict,
    business: Business = Depends(current_business),
    db: Session = Depends(get_db),
) -> dict:
    dataset = _owned(db, dataset_id, business)
    operations = _operations(body)
    frame = load_layer(db, dataset.id, "bronze")
    try:
        cleaned, summary = apply_operations(frame, operations)
    except ValueError as exc:
        raise AppError(str(exc)) from exc
    replace_layer(db, dataset.id, "silver", cleaned)
    report = save_profile(db, dataset, "silver", cleaned)
    dataset.status = "cleaned"
    db.add(
        CleaningOperation(
            dataset_id=dataset.id,
            operation_type="recipe",
            params={"operations": operations},
            status="applied",
            summary={
                "rows_before": summary["rows_before"],
                "rows_after": summary["rows_after"],
                "cells_changed": summary["cells_changed"],
            },
        )
    )
    log_activity(
        db,
        "clean",
        f"Saved a cleaned copy of {dataset.name}. The upload itself was not changed.",
        dataset.id,
        business_id=business.id,
    )
    return {
        "saved": True,
        "silver_quality_score": report["score"],
        **{key: summary[key] for key in ("rows_before", "rows_after", "rows_removed", "cells_changed", "changed_cells")},
    }


@router.post("/datasets/{dataset_id}/cleaning/reject")
def reject_cleaning(
    dataset_id: int,
    business: Business = Depends(current_business),
    db: Session = Depends(get_db),
) -> dict:
    dataset = _owned(db, dataset_id, business)
    db.query(DatasetRecord).filter_by(dataset_id=dataset.id, layer="silver").delete()
    db.query(GoldRecord).filter_by(dataset_id=dataset.id).delete()
    db.query(CleaningOperation).filter_by(dataset_id=dataset.id, status="applied").update({"status": "rejected"})
    dataset.status = "profiled"
    log_activity(
        db,
        "clean_rejected",
        f"Removed the cleaned copy of {dataset.name}. Original rows are unchanged.",
        dataset.id,
        business_id=business.id,
    )
    return {"rejected": True, "status": dataset.status}


@router.get("/datasets/{dataset_id}/cleaning/operations")
def cleaning_operations(
    dataset_id: int,
    business: Business = Depends(current_business),
    db: Session = Depends(get_db),
) -> dict:
    _owned(db, dataset_id, business)
    rows = (
        db.query(CleaningOperation)
        .filter_by(dataset_id=dataset_id)
        .order_by(CleaningOperation.created_at.desc())
        .limit(20)
        .all()
    )
    return {
        "standard_recipe": STANDARD_OPERATIONS,
        "items": [
            {
                "id": row.id,
                "operation_type": row.operation_type,
                "status": row.status,
                "params": row.params,
                "summary": row.summary,
                "created_at": _dt(row.created_at),
            }
            for row in rows
        ],
    }


@router.get("/datasets/{dataset_id}/rules")
def list_rules(
    dataset_id: int,
    business: Business = Depends(current_business),
    db: Session = Depends(get_db),
) -> dict:
    _owned(db, dataset_id, business)
    rules = db.query(QualityRule).filter_by(dataset_id=dataset_id).order_by(QualityRule.id).all()
    return {"rule_types": sorted(RULE_TYPES), "items": [_rule(rule) for rule in rules]}


@router.post("/datasets/{dataset_id}/rules")
def create_rule(
    dataset_id: int,
    body: dict,
    business: Business = Depends(current_business),
    db: Session = Depends(get_db),
) -> dict:
    dataset = _owned(db, dataset_id, business)
    rule_type = body.get("rule_type")
    column = (body.get("column_name") or "").strip()
    if rule_type not in RULE_TYPES:
        raise AppError("That rule type is not supported.")
    if not column:
        raise AppError("Choose a column for the rule.")
    rule = QualityRule(
        dataset_id=dataset.id,
        name=(body.get("name") or f"{column} {rule_type}").strip()[:160],
        column_name=column,
        rule_type=rule_type,
        config=body.get("config") or {},
        enabled=bool(body.get("enabled", True)),
        blocks_load=bool(body.get("blocks_load", True)),
    )
    db.add(rule)
    db.flush()
    return _rule(rule)


@router.patch("/rules/{rule_id}")
def update_rule(
    rule_id: int,
    body: dict,
    business: Business = Depends(current_business),
    db: Session = Depends(get_db),
) -> dict:
    rule = db.get(QualityRule, rule_id)
    if rule is None:
        raise AppError("Rule not found.", 404)
    _owned(db, rule.dataset_id, business)
    if "enabled" in body:
        rule.enabled = bool(body["enabled"])
    if "blocks_load" in body:
        rule.blocks_load = bool(body["blocks_load"])
    if "name" in body and str(body["name"]).strip():
        rule.name = str(body["name"]).strip()[:160]
    db.flush()
    return _rule(rule)


@router.delete("/rules/{rule_id}", status_code=204, response_class=Response)
def delete_rule(
    rule_id: int,
    business: Business = Depends(current_business),
    db: Session = Depends(get_db),
) -> Response:
    rule = db.get(QualityRule, rule_id)
    if rule is None:
        raise AppError("Rule not found.", 404)
    _owned(db, rule.dataset_id, business)
    db.delete(rule)
    return Response(status_code=204)


@router.post("/datasets/{dataset_id}/validate")
def validate_dataset(
    dataset_id: int,
    business: Business = Depends(current_business),
    db: Session = Depends(get_db),
) -> dict:
    dataset = _owned(db, dataset_id, business)
    frame = load_layer(db, dataset.id, "silver")
    layer = "silver"
    if frame.empty:
        frame = load_layer(db, dataset.id, "bronze")
        layer = "bronze"
    if frame.empty:
        raise AppError("There are no rows to validate.")
    checked = evaluate(frame, rule_dicts(db, dataset.id))
    store_validation(db, dataset.id, None, checked["results"])
    if layer == "silver":
        mark_quarantine(db, dataset.id, checked["reasons"])
    return {"layer": layer, "results": checked["results"]}


@router.get("/datasets/{dataset_id}/validation")
def validation_results(
    dataset_id: int,
    business: Business = Depends(current_business),
    db: Session = Depends(get_db),
) -> dict:
    _owned(db, dataset_id, business)
    rows = db.query(ValidationResult).filter_by(dataset_id=dataset_id).order_by(ValidationResult.id).all()
    return {
        "items": [
            {
                "id": row.id,
                "rule_name": row.rule_name,
                "column_name": row.column_name,
                "status": row.status,
                "affected_count": row.affected_count,
                "message": row.message,
                "created_at": _dt(row.created_at),
            }
            for row in rows
        ]
    }


@router.post("/validation/references")
def run_reference_checks(business: Business = Depends(current_business), db: Session = Depends(get_db)) -> dict:
    return {"items": refresh_references(db, business.id)}


@router.get("/pipelines")
def list_pipelines(business: Business = Depends(current_business), db: Session = Depends(get_db)) -> dict:
    ids = _owned_ids(db, business)
    if not ids:
        return {"items": []}
    runs = (
        db.query(PipelineRun)
        .filter(PipelineRun.dataset_id.in_(ids))
        .order_by(PipelineRun.started_at.desc())
        .limit(100)
        .all()
    )
    names = {
        dataset.id: dataset.name
        for dataset in db.query(Dataset).filter(Dataset.id.in_(ids)).all()
    }
    return {"items": [{**_run(run), "dataset_name": names.get(run.dataset_id, "Removed dataset")} for run in runs]}


@router.get("/pipelines/{run_id}")
def pipeline_detail(
    run_id: int,
    business: Business = Depends(current_business),
    db: Session = Depends(get_db),
) -> dict:
    run = db.get(PipelineRun, run_id)
    if run is None:
        raise AppError("Pipeline run not found.", 404)
    dataset = _owned(db, run.dataset_id, business)
    stages = db.query(PipelineStage).filter_by(run_id=run.id).order_by(PipelineStage.id).all()
    friendly = {
        "extract": "Read uploaded file",
        "profile": "Check data quality",
        "clean": "Apply cleaning",
        "validate": "Validate & quarantine bad rows",
        "transform": "Map business fields",
        "load": "Load trusted analytics data",
    }
    return {
        **_run(run),
        "dataset_name": dataset.name,
        "stages": [
            {
                "name": stage.name,
                "label": friendly.get(stage.name, stage.name.replace("_", " ").title()),
                "status": stage.status,
                "started_at": _dt(stage.started_at),
                "finished_at": _dt(stage.finished_at),
                "records_in": stage.records_in,
                "records_out": stage.records_out,
                "warnings": stage.warnings or [],
                "error_message": stage.error_message,
                "details": stage.details or {},
                "duration_seconds": _duration(stage.started_at, stage.finished_at),
            }
            for stage in stages
        ],
    }


@router.post("/datasets/{dataset_id}/pipeline/run")
def start_pipeline(
    dataset_id: int,
    business: Business = Depends(current_business),
    db: Session = Depends(get_db),
) -> dict:
    _owned(db, dataset_id, business)
    run = run_pipeline(db, dataset_id)
    refresh_references(db, business.id)
    return pipeline_detail(run.id, business, db)


@router.get("/analytics/overview")
def analytics_overview(business: Business = Depends(current_business), db: Session = Depends(get_db)) -> dict:
    return {
        "sales": analytics.sales_report(db, business.id),
        "customers": analytics.customer_report(db, business.id),
        "inventory": analytics.inventory_report(db, business.id),
        "expenses": analytics.expense_report(db, business.id),
    }


@router.get("/analytics/sales")
def analytics_sales(business: Business = Depends(current_business), db: Session = Depends(get_db)) -> dict:
    return analytics.sales_report(db, business.id)


@router.get("/analytics/customers")
def analytics_customers(business: Business = Depends(current_business), db: Session = Depends(get_db)) -> dict:
    return analytics.customer_report(db, business.id)


@router.get("/analytics/inventory")
def analytics_inventory(business: Business = Depends(current_business), db: Session = Depends(get_db)) -> dict:
    return analytics.inventory_report(db, business.id)


@router.get("/analytics/expenses")
def analytics_expenses(business: Business = Depends(current_business), db: Session = Depends(get_db)) -> dict:
    return analytics.expense_report(db, business.id)


@router.get("/copilot/suggestions")
def copilot_suggestions(business: Business = Depends(current_business), db: Session = Depends(get_db)) -> dict:
    return {"items": copilot.suggestions(db)}


@router.get("/copilot/sessions")
def copilot_sessions(business: Business = Depends(current_business), db: Session = Depends(get_db)) -> dict:
    sessions = (
        db.query(ChatSession)
        .filter_by(business_id=business.id)
        .order_by(ChatSession.created_at.desc())
        .limit(30)
        .all()
    )
    return {"items": [{"id": item.id, "title": item.title, "created_at": _dt(item.created_at)} for item in sessions]}


@router.get("/copilot/sessions/{session_id}")
def copilot_session(
    session_id: int,
    business: Business = Depends(current_business),
    db: Session = Depends(get_db),
) -> dict:
    session = db.get(ChatSession, session_id)
    if session is None or session.business_id != business.id:
        raise AppError("Conversation not found.", 404)
    messages = db.query(ChatMessage).filter_by(session_id=session.id).order_by(ChatMessage.id).all()
    return {
        "id": session.id,
        "title": session.title,
        "messages": [
            {
                "id": item.id,
                "role": item.role,
                "content": item.content,
                "payload": item.payload or {},
                "created_at": _dt(item.created_at),
            }
            for item in messages
        ],
    }


@router.post("/copilot/ask")
def copilot_ask(
    body: dict,
    business: Business = Depends(current_business),
    db: Session = Depends(get_db),
) -> dict:
    return copilot.ask(
        db,
        str(body.get("question") or ""),
        body.get("session_id"),
        body.get("dataset_id"),
        business_id=business.id,
    )


@router.get("/lineage")
def lineage(business: Business = Depends(current_business), db: Session = Depends(get_db)) -> dict:
    datasets = db.query(Dataset).filter_by(business_id=business.id).order_by(Dataset.created_at).all()
    ids = [dataset.id for dataset in datasets]
    edges = db.query(LineageEdge).filter(LineageEdge.dataset_id.in_(ids)).order_by(LineageEdge.id).all() if ids else []
    grouped: dict[int, list] = {}
    for edge in edges:
        grouped.setdefault(edge.dataset_id, []).append(
            {
                "source": edge.source,
                "target": edge.target,
                "stage": edge.stage,
                "description": edge.description,
            }
        )
    return {
        "datasets": [
            {
                "id": dataset.id,
                "name": dataset.name,
                "category": dataset.category,
                "status": dataset.status,
                "is_sample": dataset.is_sample,
                "edges": grouped.get(dataset.id, []),
            }
            for dataset in datasets
        ]
    }


@router.get("/datasets/{dataset_id}/export/{kind}")
def export_dataset(
    dataset_id: int,
    kind: str,
    business: Business = Depends(current_business),
    db: Session = Depends(get_db),
):
    import pandas as pd

    dataset = _owned(db, dataset_id, business)
    if kind == "raw.csv":
        return _csv(load_layer(db, dataset.id, "bronze"), f"{dataset.name}-original.csv")
    if kind == "cleaned.csv":
        return _csv(_trusted_frame(db, dataset), f"{dataset.name}-cleaned.csv")
    if kind == "cleaned.xlsx":
        return _xlsx(_trusted_frame(db, dataset), f"{dataset.name}-cleaned.xlsx")
    if kind == "quarantine.csv":
        rows = (
            db.query(DatasetRecord)
            .filter_by(dataset_id=dataset.id, layer="silver", quarantined=True)
            .order_by(DatasetRecord.row_index)
            .all()
        )
        records = []
        for row in rows:
            item = dict(row.data)
            item["quarantine_reason"] = row.quarantine_reason
            records.append(item)
        return _csv(records_frame(records) if records else records_frame([]), f"{dataset.name}-quarantine.csv")
    if kind == "quality.csv":
        issues = db.query(QualityIssue).filter_by(dataset_id=dataset.id, layer="bronze").all()
        frame = pd.DataFrame(
            [
                {
                    "category": issue.category,
                    "column": issue.column_name,
                    "affected_count": issue.affected_count,
                    "severity": issue.severity,
                    "explanation": issue.explanation,
                    "suggested_resolution": issue.suggested_resolution,
                    "auto_fixable": issue.auto_fixable,
                    "manual_review": issue.manual_review,
                }
                for issue in issues
            ]
        )
        return _csv(frame, f"{dataset.name}-quality.csv")
    raise AppError("Unknown export.", 404)


@router.get("/pipelines/{run_id}/export.json")
def export_pipeline(
    run_id: int,
    business: Business = Depends(current_business),
    db: Session = Depends(get_db),
):
    return pipeline_detail(run_id, business, db)


@router.get("/analytics/export.csv")
def export_analytics(business: Business = Depends(current_business), db: Session = Depends(get_db)):
    import pandas as pd

    sales = analytics.sales_report(db, business.id)
    expenses = analytics.expense_report(db, business.id)
    inventory = analytics.inventory_report(db, business.id)
    customers = analytics.customer_report(db, business.id)
    rows = [
        {
            "metric": "Revenue",
            "value": sales.get("revenue") if sales.get("available") else None,
            "note": "" if sales.get("available") else sales.get("reason"),
        },
        {
            "metric": "Orders",
            "value": sales.get("orders") if sales.get("available") else None,
            "note": "" if sales.get("available") else sales.get("reason"),
        },
        {
            "metric": "Average order value",
            "value": sales.get("average_order_value") if sales.get("available") else None,
            "note": "",
        },
        {
            "metric": "Customers",
            "value": customers.get("total_customers") if customers.get("available") else None,
            "note": "" if customers.get("available") else customers.get("reason"),
        },
        {
            "metric": "Inventory value",
            "value": inventory.get("inventory_value") if inventory.get("available") else None,
            "note": "" if inventory.get("available") else inventory.get("reason"),
        },
        {
            "metric": "Expenses",
            "value": expenses.get("total") if expenses.get("available") else None,
            "note": "" if expenses.get("available") else expenses.get("reason"),
        },
    ]
    return _csv(pd.DataFrame(rows), "analytics-summary.csv")


@router.get("/samples")
def list_samples(business: Business = Depends(current_business)) -> dict:
    return {"items": sample_catalog()}


@router.get("/samples/{filename}")
def download_sample(filename: str, business: Business = Depends(current_business)):
    allowed = {item["filename"] for item in sample_catalog()}
    if filename not in allowed or "/" in filename or ".." in filename:
        raise AppError("Sample file not found.", 404)
    path = get_settings().sample_dir / filename
    return FileResponse(path, filename=filename, media_type="text/csv")


@router.post("/samples/load")
def load_sample_data(
    run_pipeline_flag: bool = Query(True, alias="run_pipeline"),
    business: Business = Depends(current_business),
    db: Session = Depends(get_db),
) -> dict:
    load_samples(db, business_id=business.id)
    loaded = []
    if run_pipeline_flag:
        order = ["Sample products", "Sample customers", "Sample inventory", "Sample expenses", "Sample sales"]
        datasets = db.query(Dataset).filter_by(is_sample=True, business_id=business.id).all()
        datasets.sort(key=lambda item: order.index(item.name) if item.name in order else 99)
        for dataset in datasets:
            run = run_pipeline(db, dataset.id)
            loaded.append(
                {
                    "dataset_id": dataset.id,
                    "name": dataset.name,
                    "run_id": run.id,
                    "status": run.status,
                    "loaded": run.records_loaded,
                    "rejected": run.records_rejected,
                }
            )
        refresh_references(db, business.id)
    return {"processed": loaded}
