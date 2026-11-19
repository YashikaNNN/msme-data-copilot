"""Business metrics computed only from gold rows.

If a required value was never loaded, the metric is null and the response
explains which field is missing. Totals are not filled in with guesses.
"""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from app.models import Dataset, GoldRecord, QualityIssue, QualitySnapshot


def _money(value) -> float | None:
    if value is None:
        return None
    return round(float(value), 2)


def _rows(db: Session, entity: str) -> list[GoldRecord]:
    return db.query(GoldRecord).filter_by(entity=entity).all()


def sales_report(db: Session) -> dict:
    rows = _rows(db, "sale")
    if not rows:
        return _missing(
            "sales",
            "No validated sales are loaded yet.",
            ["a sales file with order date, product, quantity, and amount"],
        )
    priced = [row for row in rows if row.amount is not None]
    dated = [row for row in rows if row.event_date is not None]
    revenue = round(sum(float(row.amount) for row in priced), 2) if priced else None
    average = round(revenue / len(priced), 2) if revenue is not None and priced else None
    by_month: dict[str, dict] = defaultdict(lambda: {"month": "", "revenue": 0.0, "orders": 0, "has_amount": False})
    for row in rows:
        key = row.event_date.strftime("%Y-%m") if row.event_date else "Unknown date"
        bucket = by_month[key]
        bucket["month"] = key
        bucket["orders"] += 1
        if row.amount is not None:
            bucket["revenue"] = round(bucket["revenue"] + float(row.amount), 2)
            bucket["has_amount"] = True
    for bucket in by_month.values():
        if not bucket["has_amount"]:
            bucket["revenue"] = None
        bucket.pop("has_amount", None)

    products: dict[str, dict] = {}
    categories: dict[str, dict] = {}
    for row in rows:
        product_key = row.product_name or row.product_id or "Unnamed product"
        product = products.setdefault(product_key, {"name": product_key, "product_id": row.product_id, "revenue": 0.0, "quantity": 0.0, "orders": 0, "has_amount": False})
        product["orders"] += 1
        if row.quantity is not None:
            product["quantity"] = round(product["quantity"] + float(row.quantity), 2)
        if row.amount is not None:
            product["revenue"] = round(product["revenue"] + float(row.amount), 2)
            product["has_amount"] = True
        category_key = row.category or "Uncategorised"
        category = categories.setdefault(category_key, {"category": category_key, "revenue": 0.0, "orders": 0, "has_amount": False})
        category["orders"] += 1
        if row.amount is not None:
            category["revenue"] = round(category["revenue"] + float(row.amount), 2)
            category["has_amount"] = True

    product_list = []
    for item in products.values():
        if not item.pop("has_amount"):
            item["revenue"] = None
        product_list.append(item)
    product_list.sort(key=lambda item: (-(item["revenue"] or -1), item["name"]))

    category_list = []
    for item in categories.values():
        if not item.pop("has_amount"):
            item["revenue"] = None
        category_list.append(item)
    category_list.sort(key=lambda item: (-(item["revenue"] or -1), item["category"]))

    notes = []
    if len(priced) != len(rows):
        notes.append(f"{len(rows) - len(priced)} sales have no usable amount, so revenue ignores them.")
    if len(dated) != len(rows):
        notes.append(f"{len(rows) - len(dated)} sales have no usable date, so they are not placed on the trend.")
    missing = []
    if revenue is None:
        missing.append("amount")
    if not any(row.product_name or row.product_id for row in rows):
        missing.append("product")
    if not dated:
        missing.append("order date")
    return {
        "available": True,
        "revenue": revenue,
        "orders": len(rows),
        "priced_orders": len(priced),
        "average_order_value": average,
        "by_month": sorted(by_month.values(), key=lambda item: item["month"]),
        "products": product_list,
        "categories": category_list,
        "missing_fields": missing,
        "notes": notes,
    }


def customer_report(db: Session) -> dict:
    people = _rows(db, "customer")
    sales = _rows(db, "sale")
    if not people and not sales:
        return _missing("customers", "No customer or sales rows are loaded.", ["customer id", "customer name", "sales amount"])
    names = {row.customer_id: row.name for row in people if row.customer_id}
    grouped: dict[str, dict] = {}
    for row in sales:
        if not row.customer_id:
            continue
        item = grouped.setdefault(
            row.customer_id,
            {"customer_id": row.customer_id, "name": names.get(row.customer_id), "revenue": 0.0, "orders": 0, "has_amount": False},
        )
        item["orders"] += 1
        if row.amount is not None:
            item["revenue"] = round(item["revenue"] + float(row.amount), 2)
            item["has_amount"] = True
    leaders = []
    for item in grouped.values():
        if not item.pop("has_amount"):
            item["revenue"] = None
        if not item["name"]:
            item["name"] = None
        leaders.append(item)
    leaders.sort(key=lambda item: (-(item["revenue"] or -1), item["customer_id"]))
    notes = []
    if sales and not people:
        notes.append("Customer names are unavailable because no customer dataset has been loaded. Totals use customer ids from sales.")
    if people and not sales:
        notes.append("Purchase patterns need a sales dataset. Only the customer list is available.")
    return {
        "available": True,
        "total_customers": len(people) if people else len(grouped),
        "customers_with_purchases": len(grouped),
        "top_customers": leaders[:10],
        "missing_fields": [] if sales else ["sales amount"],
        "notes": notes,
    }


def inventory_report(db: Session) -> dict:
    stock_rows = _rows(db, "inventory")
    if not stock_rows:
        return _missing("inventory", "No validated inventory rows are loaded.", ["product id", "stock quantity"])
    sales = _rows(db, "sale")
    sold: dict[str, float] = defaultdict(float)
    for row in sales:
        if row.product_id and row.quantity is not None:
            sold[row.product_id] += float(row.quantity)
    items = []
    valued = []
    for row in stock_rows:
        quantity = _money(row.quantity)
        cost = _money(row.amount)
        units_sold = round(sold.get(row.product_id, 0), 2) if row.product_id else None
        line_value = round(quantity * cost, 2) if quantity is not None and cost is not None else None
        if line_value is not None:
            valued.append(line_value)
        items.append(
            {
                "product_id": row.product_id,
                "product_name": row.product_name or row.name,
                "stock_qty": quantity,
                "unit_cost": cost,
                "inventory_value": line_value,
                "units_sold": units_sold if sales else None,
            }
        )
    low = [item for item in items if item["stock_qty"] is not None and item["stock_qty"] < 10]
    slow = []
    if sales:
        slow = [
            item
            for item in items
            if item["stock_qty"] is not None
            and item["stock_qty"] >= 40
            and (item["units_sold"] or 0) <= 3
        ]
    notes = [
        "Low stock means fewer than 10 units on hand.",
        "High stock and low sales means at least 40 units on hand and 3 or fewer units sold in the loaded sales.",
    ]
    if not sales:
        notes.append("Sales are not loaded, so products that are stocking up without selling cannot be identified yet.")
    missing = []
    if not any(item["stock_qty"] is not None for item in items):
        missing.append("stock quantity")
    if not valued:
        missing.append("unit cost")
    return {
        "available": True,
        "items": items,
        "low_stock": low,
        "high_stock_low_sales": slow,
        "inventory_value": round(sum(valued), 2) if valued else None,
        "missing_fields": missing,
        "notes": notes,
    }


def expense_report(db: Session) -> dict:
    rows = _rows(db, "expense")
    if not rows:
        return _missing("expenses", "No validated expenses are loaded.", ["expense date", "category", "amount"])
    priced = [row for row in rows if row.amount is not None]
    total = round(sum(float(row.amount) for row in priced), 2) if priced else None
    by_category: dict[str, float] = defaultdict(float)
    by_month_category: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    months = set()
    for row in priced:
        key = row.category or "Uncategorised"
        by_category[key] = round(by_category[key] + float(row.amount), 2)
        if row.event_date:
            month = row.event_date.strftime("%Y-%m")
            months.add(month)
            by_month_category[month][key] = round(by_month_category[month][key] + float(row.amount), 2)
    ordered_months = sorted(months)
    increase = None
    if len(ordered_months) >= 2:
        previous, latest = ordered_months[-2], ordered_months[-1]
        keys = set(by_month_category[previous]) | set(by_month_category[latest])
        deltas = []
        for key in keys:
            delta = round(by_month_category[latest].get(key, 0) - by_month_category[previous].get(key, 0), 2)
            deltas.append({"category": key, "previous_month": previous, "latest_month": latest, "change": delta})
        deltas.sort(key=lambda item: -item["change"])
        if deltas and deltas[0]["change"] > 0:
            increase = deltas[0]
    sales = sales_report(db)
    comparison = []
    if sales["available"]:
        expense_by_month = {
            month: round(sum(categories.values()), 2) for month, categories in by_month_category.items()
        }
        sales_by_month = {item["month"]: item["revenue"] for item in sales["by_month"]}
        for month in sorted(set(expense_by_month) | set(sales_by_month)):
            revenue = sales_by_month.get(month)
            expense = expense_by_month.get(month)
            profit = round(revenue - expense, 2) if revenue is not None and expense is not None else None
            comparison.append({"month": month, "revenue": revenue, "expenses": expense, "profit": profit})
    notes = []
    if len(priced) != len(rows):
        notes.append(f"{len(rows) - len(priced)} expenses have no usable amount and are excluded from totals.")
    if len(ordered_months) < 2:
        notes.append("At least two months of expenses are needed before a category increase can be compared.")
    return {
        "available": True,
        "total": total,
        "by_category": [{"category": key, "amount": value} for key, value in sorted(by_category.items(), key=lambda item: -item[1])],
        "by_month": [
            {"month": month, "amount": round(sum(categories.values()), 2)}
            for month, categories in sorted(by_month_category.items())
        ],
        "largest_increase": increase,
        "revenue_vs_expenses": comparison,
        "missing_fields": [] if total is not None else ["amount"],
        "notes": notes,
    }


def overview(db: Session) -> dict:
    sales = sales_report(db)
    customers = customer_report(db)
    inventory = inventory_report(db)
    expenses = expense_report(db)
    return {
        "sales": _card(sales, "revenue"),
        "customers": {"available": customers["available"], "total_customers": customers.get("total_customers"), "reason": customers.get("reason")},
        "inventory": {"available": inventory["available"], "inventory_value": inventory.get("inventory_value"), "low_stock": len(inventory.get("low_stock") or []), "reason": inventory.get("reason")},
        "expenses": {"available": expenses["available"], "total": expenses.get("total"), "reason": expenses.get("reason")},
    }


def quality_facts(db: Session) -> dict:
    datasets = db.query(Dataset).order_by(Dataset.created_at.desc()).all()
    issues = (
        db.query(QualityIssue)
        .filter_by(layer="bronze")
        .order_by(QualityIssue.affected_count.desc())
        .limit(8)
        .all()
    )
    snapshots = db.query(QualitySnapshot).order_by(QualitySnapshot.created_at.desc()).all()
    latest: dict[int, QualitySnapshot] = {}
    for snapshot in snapshots:
        latest.setdefault(snapshot.dataset_id, snapshot)
    return {
        "datasets": [
            {
                "id": dataset.id,
                "name": dataset.name,
                "category": dataset.category,
                "rows": dataset.row_count,
                "score": _money(dataset.quality_score),
                "latest_score": _money(latest[dataset.id].score) if dataset.id in latest else None,
                "latest_layer": latest[dataset.id].layer if dataset.id in latest else None,
            }
            for dataset in datasets
        ],
        "top_issues": [
            {
                "dataset_id": issue.dataset_id,
                "category": issue.category,
                "column": issue.column_name,
                "affected_count": issue.affected_count,
                "severity": issue.severity,
                "explanation": issue.explanation,
            }
            for issue in issues
        ],
    }


def _missing(kind: str, reason: str, fields: list[str]) -> dict:
    return {"available": False, "kind": kind, "reason": reason, "missing_fields": fields, "notes": [reason]}


def _card(report: dict, value_key: str) -> dict:
    if not report.get("available"):
        return {"available": False, "reason": report.get("reason"), "missing_fields": report.get("missing_fields", [])}
    return {"available": True, value_key: report.get(value_key), "orders": report.get("orders"), "notes": report.get("notes", [])}
