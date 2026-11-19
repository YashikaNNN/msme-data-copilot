"""File upload and sample-data loading.

Files are stored under a generated name. The original filename is only a label.
"""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.errors import AppError
from app.models import Dataset, DatasetFile
from app.services.frames import ALLOWED_EXTENSIONS, read_table
from app.services.repository import ensure_rules, log_activity, replace_layer, save_profile

CATEGORIES = {"sales", "customers", "products", "inventory", "expenses", "orders", "other"}
SAMPLE_ORDER = [
    ("products.csv", "Sample products", "products", "Product catalogue with a duplicate and a negative price."),
    ("customers.csv", "Sample customers", "customers", "Customer list with duplicate ids, a bad email, and a missing name."),
    ("inventory.csv", "Sample inventory", "inventory", "Stock file with low stock, missing quantity, and an unknown product."),
    ("expenses.csv", "Sample expenses", "expenses", "Expenses with mixed category spellings, a bad date, and a negative amount."),
    ("sales.csv", "Sample sales", "sales", "Sales file with mixed dates, duplicate rows, invalid amounts, and inconsistent ids."),
]


def create_dataset(
    db: Session,
    *,
    name: str,
    description: str,
    category: str,
    filename: str,
    content: bytes,
    content_type: str | None,
    is_sample: bool = False,
) -> Dataset:
    clean_name = " ".join(name.split())
    if not clean_name or len(clean_name) > 160:
        raise AppError("Give the dataset a name of 1 to 160 characters.")
    if len(description or "") > 2000:
        raise AppError("The description is too long.")
    if category not in CATEGORIES:
        raise AppError("Choose a category: sales, customers, products, inventory, expenses, orders, or other.")
    suffix = Path(filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise AppError("Upload a .csv, .xlsx, or .json file.")
    settings = get_settings()
    if not content:
        raise AppError("The file is empty.")
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise AppError(f"The file is larger than {settings.max_upload_mb} MB.")
    if suffix == ".xlsx" and not content.startswith(b"PK"):
        raise AppError("This file does not look like an Excel workbook.")
    if suffix in {".csv", ".json"} and b"\x00" in content[:4096]:
        raise AppError("This file looks binary. CSV and JSON uploads must be text.")

    temp_path = settings.storage_path / f"incoming-{uuid.uuid4().hex}{suffix}"
    temp_path.write_bytes(content)
    try:
        frame, notes = read_table(temp_path, settings.max_rows)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise

    dataset = Dataset(
        name=clean_name,
        description=description.strip(),
        category=category,
        status="uploaded",
        is_sample=is_sample,
        row_count=len(frame),
        column_count=len(frame.columns),
    )
    db.add(dataset)
    db.flush()
    stored = f"{uuid.uuid4().hex}{suffix}"
    folder = settings.storage_path / str(dataset.id)
    folder.mkdir(parents=True, exist_ok=True)
    final_path = folder / stored
    temp_path.replace(final_path)
    db.add(
        DatasetFile(
            dataset_id=dataset.id,
            original_filename=Path(filename).name[:255],
            stored_name=stored,
            content_type=content_type or "application/octet-stream",
            size_bytes=len(content),
            checksum=hashlib.sha256(content).hexdigest(),
        )
    )
    replace_layer(db, dataset.id, "bronze", frame)
    save_profile(db, dataset, "bronze", frame)
    ensure_rules(db, dataset.id, list(frame.columns))
    note = f" Uploaded with {len(notes)} schema note(s)." if notes else ""
    log_activity(db, "upload", f"Uploaded {dataset.name} ({dataset.row_count} rows).{note}", dataset.id)
    db.flush()
    return dataset


def load_samples(db: Session, replace_existing: bool = False) -> list[Dataset]:
    settings = get_settings()
    created: list[Dataset] = []
    for filename, name, category, description in SAMPLE_ORDER:
        path = settings.sample_dir / filename
        if not path.exists():
            raise AppError(f"Sample file {filename} is missing from the server.")
        if replace_existing:
            existing = db.query(Dataset).filter_by(name=name, is_sample=True).all()
            for dataset in existing:
                delete_dataset(db, dataset)
        elif db.query(Dataset).filter_by(name=name, is_sample=True).first():
            continue
        created.append(
            create_dataset(
                db,
                name=name,
                description=description + " This is labelled sample data.",
                category=category,
                filename=filename,
                content=path.read_bytes(),
                content_type="text/csv",
                is_sample=True,
            )
        )
    return created


def delete_dataset(db: Session, dataset: Dataset) -> None:
    settings = get_settings()
    folder = settings.storage_path / str(dataset.id)
    if folder.exists():
        for child in folder.iterdir():
            if child.is_file():
                child.unlink()
        folder.rmdir()
    db.delete(dataset)
    db.flush()


def sample_catalog() -> list[dict]:
    settings = get_settings()
    items = []
    for filename, name, category, description in SAMPLE_ORDER:
        path = settings.sample_dir / filename
        items.append(
            {
                "filename": filename,
                "name": name,
                "category": category,
                "description": description,
                "available": path.exists(),
                "size_bytes": path.stat().st_size if path.exists() else 0,
            }
        )
    return items
