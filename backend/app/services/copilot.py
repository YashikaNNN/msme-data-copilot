"""Questions are answered by named analytics functions, then optionally narrated.

The model never receives a database connection and never writes SQL.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import ChatMessage, ChatSession, Dataset
from app.services import analytics
from app.services.llm import explain

INTENTS: list[tuple[str, tuple[str, ...]]] = [
    ("quality", ("quality", "missing value", "duplicate", "what is wrong", "data problem", "issues")),
    ("inventory_mismatch", ("high inventory", "low sales", "not selling", "overstock")),
    ("expense_increase", ("expense", "expenses")),
    ("best_month", ("which month", "highest sales", "best month", "busiest month")),
    ("revenue_trend", ("trend", "revenue trend")),
    ("top_customers", ("customer", "customers")),
    ("top_products", ("product", "products", "highest revenue", "best selling")),
    ("summary", ("summarize", "summary", "overview")),
]

SUGGESTIONS = [
    "Which products generated the highest revenue?",
    "Which products have high inventory but low sales?",
    "Which customers generate the most revenue?",
    "Which month had the highest sales?",
    "Which expense category increased the most?",
    "What are the major data-quality problems?",
    "Summarize this dataset.",
    "Explain the recent revenue trend.",
]


def ask(
    db: Session,
    question: str,
    session_id: int | None = None,
    dataset_id: int | None = None,
    business_id: int | None = None,
) -> dict:
    text = " ".join(question.strip().split())
    if not text:
        from app.errors import AppError

        raise AppError("Enter a question first.")
    if len(text) > 2000:
        from app.errors import AppError

        raise AppError("Questions are limited to 2000 characters.")

    session = db.get(ChatSession, session_id) if session_id else None
    if session is not None and business_id is not None and session.business_id != business_id:
        from app.errors import AppError

        raise AppError("Conversation not found.", 404)
    if session is None:
        session = ChatSession(title=text[:80], business_id=business_id)
        db.add(session)
        db.flush()

    if dataset_id is not None and business_id is not None:
        dataset = db.get(Dataset, dataset_id)
        if dataset is None or dataset.business_id != business_id:
            from app.errors import AppError

            raise AppError("Dataset not found.", 404)

    intent = _intent(text)
    facts, metrics, sources, answer = _answer(db, intent, dataset_id, business_id)
    narrative, provider, note = explain(text, {"intent": intent, "facts": facts})
    final = narrative or answer
    if narrative:
        final = f"{narrative}\n\nCalculated result: {answer}"

    db.add(ChatMessage(session_id=session.id, role="user", content=text, payload={}))
    message = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=final,
        payload={
            "intent": intent,
            "metrics": metrics,
            "sources": sources,
            "llm_used": bool(narrative),
            "llm_provider": provider,
            "llm_note": note,
            "facts": facts,
        },
    )
    db.add(message)
    db.flush()
    return {
        "session_id": session.id,
        "message_id": message.id,
        "answer": final,
        "intent": intent,
        "metrics": metrics,
        "sources": sources,
        "llm_used": bool(narrative),
        "llm_note": note,
    }


def suggestions(db: Session) -> list[str]:
    return SUGGESTIONS


def _intent(question: str) -> str:
    lowered = question.lower()
    for name, phrases in INTENTS:
        if any(phrase in lowered for phrase in phrases):
            return name
    return "unknown"


def _answer(
    db: Session,
    intent: str,
    dataset_id: int | None,
    business_id: int | None = None,
) -> tuple[dict, list[dict], list[str], str]:
    sales = analytics.sales_report(db, business_id)
    customers = analytics.customer_report(db, business_id)
    inventory = analytics.inventory_report(db, business_id)
    expenses = analytics.expense_report(db, business_id)
    quality = analytics.quality_facts(db, business_id)
    if dataset_id:
        quality["datasets"] = [item for item in quality["datasets"] if item["id"] == dataset_id]
        dataset = db.get(Dataset, dataset_id)
        scope = dataset.name if dataset else f"dataset {dataset_id}"
    else:
        scope = "all loaded datasets"

    if intent == "top_products":
        facts = {"sales": _public_sales(sales)}
        if not sales["available"]:
            return facts, [], ["gold sales"], sales["reason"]
        leaders = [item for item in sales["products"] if item["revenue"] is not None][:5]
        if not leaders:
            return facts, [], ["gold sales"], "Sales are loaded, but none of them have a usable amount, so product revenue cannot be ranked."
        metrics = [{"label": item["name"], "value": _rupee(item["revenue"])} for item in leaders]
        lines = ", ".join(f"{item['name']} ({_rupee(item['revenue'])}, {item['quantity']} units)" for item in leaders)
        return facts, metrics, ["gold sales records"], f"Highest revenue products in {scope}: {lines}."

    if intent == "inventory_mismatch":
        facts = {"inventory": {"available": inventory["available"], "high_stock_low_sales": inventory.get("high_stock_low_sales"), "notes": inventory.get("notes")}}
        if not inventory["available"]:
            return facts, [], ["gold inventory"], inventory["reason"]
        slow = inventory["high_stock_low_sales"]
        if not slow:
            return facts, [], ["gold inventory", "gold sales"], "No loaded product currently has at least 40 units in stock and 3 or fewer units sold."
        metrics = [{"label": item["product_name"] or item["product_id"], "value": f"{item['stock_qty']} in stock, {item['units_sold']} sold"} for item in slow]
        names = ", ".join(f"{item['product_name'] or item['product_id']} ({item['stock_qty']} on hand, {item['units_sold']} sold)" for item in slow)
        return facts, metrics, ["gold inventory", "gold sales"], f"Products with high stock and low sales: {names}."

    if intent == "top_customers":
        facts = {"customers": {key: customers.get(key) for key in ("available", "top_customers", "notes", "reason")}}
        if not customers["available"]:
            return facts, [], ["gold customers", "gold sales"], customers["reason"]
        leaders = customers["top_customers"][:5]
        if not leaders:
            return facts, [], ["gold sales"], "No sales with a customer id are loaded, so customers cannot be ranked."
        metrics = [{"label": item["name"] or item["customer_id"], "value": _rupee(item["revenue"]) if item["revenue"] is not None else "amount unavailable"} for item in leaders]
        lines = ", ".join(
            f"{item['name'] or item['customer_id']} ({_rupee(item['revenue']) if item['revenue'] is not None else 'amount unavailable'}, {item['orders']} orders)"
            for item in leaders
        )
        return facts, metrics, ["gold sales", "gold customers"], f"Customers with the most recorded revenue: {lines}."

    if intent == "best_month":
        facts = {"by_month": sales.get("by_month"), "available": sales["available"]}
        if not sales["available"]:
            return facts, [], ["gold sales"], sales["reason"]
        months = [item for item in sales["by_month"] if item["month"] != "Unknown date" and item["revenue"] is not None]
        if not months:
            return facts, [], ["gold sales"], "Sales do not have both a valid date and an amount, so the best month cannot be chosen."
        best = max(months, key=lambda item: item["revenue"])
        metrics = [{"label": best["month"], "value": _rupee(best["revenue"])}]
        return facts, metrics, ["gold sales"], f"The highest sales month in the loaded data is {best['month']} with {_rupee(best['revenue'])} across {best['orders']} orders."

    if intent == "expense_increase":
        facts = {"largest_increase": expenses.get("largest_increase"), "available": expenses["available"], "notes": expenses.get("notes")}
        if not expenses["available"]:
            return facts, [], ["gold expenses"], expenses["reason"]
        change = expenses.get("largest_increase")
        if not change:
            note = " ".join(expenses.get("notes") or [])
            return facts, [], ["gold expenses"], note or "No expense category increased between the two latest months."
        metrics = [{"label": change["category"], "value": _rupee(change["change"])}]
        return (
            facts,
            metrics,
            ["gold expenses"],
            f"{change['category']} increased the most, from {change['previous_month']} to {change['latest_month']}, by {_rupee(change['change'])}.",
        )

    if intent == "revenue_trend":
        facts = {"by_month": sales.get("by_month"), "revenue": sales.get("revenue"), "available": sales["available"]}
        if not sales["available"]:
            return facts, [], ["gold sales"], sales["reason"]
        months = [item for item in sales["by_month"] if item["month"] != "Unknown date" and item["revenue"] is not None]
        if len(months) < 2:
            return facts, [{"label": "Revenue", "value": _rupee(sales["revenue"])}], ["gold sales"], "There are not two dated months with amounts, so a trend cannot be compared yet."
        previous, latest = months[-2], months[-1]
        delta = round(latest["revenue"] - previous["revenue"], 2)
        direction = "up" if delta > 0 else "down" if delta < 0 else "flat"
        metrics = [
            {"label": previous["month"], "value": _rupee(previous["revenue"])},
            {"label": latest["month"], "value": _rupee(latest["revenue"])},
        ]
        return facts, metrics, ["gold sales"], f"Revenue moved {direction} from {previous['month']} ({_rupee(previous['revenue'])}) to {latest['month']} ({_rupee(latest['revenue'])}). The change is {_rupee(delta)}."

    if intent == "quality":
        issues = quality["top_issues"][:5]
        facts = {"datasets": quality["datasets"], "issues": issues}
        if not quality["datasets"]:
            return facts, [], ["quality issues"], "No datasets have been uploaded, so there is no quality report yet."
        if not issues:
            return facts, [], ["quality issues"], "No quality issues are stored for the current datasets."
        metrics = [{"label": f"{item['category']} · {item['column'] or 'rows'}", "value": f"{item['affected_count']} rows"} for item in issues]
        lines = "; ".join(item["explanation"] for item in issues)
        return facts, metrics, ["bronze quality profile"], f"The largest recorded quality problems are: {lines}"

    if intent == "summary":
        facts = {
            "sales": _public_sales(sales),
            "customers": {"available": customers["available"], "total_customers": customers.get("total_customers")},
            "inventory_value": inventory.get("inventory_value") if inventory["available"] else None,
            "expenses": expenses.get("total") if expenses["available"] else None,
            "datasets": quality["datasets"],
        }
        parts = [f"Workspace scope: {scope}."]
        parts.append(_sales_sentence(sales))
        parts.append(_simple("Customers", customers))
        parts.append(_simple("Inventory value", {"available": inventory["available"], "total": inventory.get("inventory_value"), "reason": inventory.get("reason")}))
        parts.append(_simple("Expenses", expenses if expenses["available"] else {"available": False, "reason": expenses.get("reason"), "total": None}))
        metrics = []
        if sales.get("available") and sales.get("revenue") is not None:
            metrics.append({"label": "Revenue", "value": _rupee(sales["revenue"])})
        if expenses.get("available") and expenses.get("total") is not None:
            metrics.append({"label": "Expenses", "value": _rupee(expenses["total"])})
        return facts, metrics, ["gold records", "dataset profiles"], " ".join(parts)

    facts = {"supported_questions": SUGGESTIONS, "sales_available": sales["available"], "datasets": len(quality["datasets"])}
    return (
        facts,
        [],
        [],
        "That question is not tied to a specific calculation yet. Ask about products, customers, months, expenses, stock, data quality, or a summary. I will only answer from loaded data.",
    )


def _public_sales(sales: dict) -> dict:
    if not sales["available"]:
        return {"available": False, "reason": sales["reason"]}
    return {
        "available": True,
        "revenue": sales["revenue"],
        "orders": sales["orders"],
        "average_order_value": sales["average_order_value"],
        "products": sales["products"][:5],
        "by_month": sales["by_month"],
        "notes": sales["notes"],
    }


def _sales_sentence(sales: dict) -> str:
    if not sales["available"]:
        return sales["reason"]
    if sales["revenue"] is None:
        return f"{sales['orders']} sales are loaded, but revenue is unavailable because no row has a usable amount."
    return f"Revenue is {_rupee(sales['revenue'])} from {sales['priced_orders']} priced orders (average {_rupee(sales['average_order_value'])})."


def _simple(label: str, report: dict) -> str:
    if not report.get("available"):
        return report.get("reason") or f"{label} is unavailable."
    total = report.get("total")
    if total is None and label == "Customers":
        return f"{report.get('total_customers', 0)} customers are on record."
    if total is None:
        return f"{label} is unavailable because the amount field is missing."
    return f"{label} is {_rupee(total)}."


def _rupee(value) -> str:
    if value is None:
        return "unavailable"
    return f"₹{float(value):,.2f}"
