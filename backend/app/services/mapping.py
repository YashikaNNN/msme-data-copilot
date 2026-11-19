"""Map messy spreadsheet headers onto a small business vocabulary.

The pipeline uses this map when it builds analytics rows. Unknown headers stay
in the cleaned file, but they are not treated as revenue or stock.
"""

from __future__ import annotations

from app.services.values import norm_header

# First matching alias wins, and each canonical name is used once.
CANONICAL_FIELDS: list[tuple[str, list[str]]] = [
    ("order_id", ["order id", "orderid", "order no", "order number", "invoice", "invoice id", "invoice no"]),
    ("order_date", ["order date", "invoice date", "sale date", "sales date", "order dt"]),
    ("expense_id", ["expense id", "expense no"]),
    ("expense_date", ["expense date"]),
    ("signup_date", ["signup date", "joined", "created date"]),
    ("customer_id", ["customer id", "cust id", "client id", "customer code", "custid"]),
    ("product_id", ["product id", "sku", "item id", "product code", "item code"]),
    ("product_name", ["product name", "item name", "product", "item"]),
    ("customer_name", ["customer name", "client name", "name"]),
    ("email", ["email", "email address", "customer email", "client email"]),
    ("city", ["city"]),
    ("segment", ["segment"]),
    ("category", ["category", "product category", "expense category"]),
    ("quantity", ["qty", "quantity", "units"]),
    ("stock_qty", ["stock qty", "quantity on hand", "qty on hand", "stock"]),
    ("unit_price", ["unit price", "price", "rate", "selling price"]),
    ("unit_cost", ["unit cost", "cost", "purchase price"]),
    (
        "amount",
        [
            "amount",
            "total",
            "total amount",
            "grand total",
            "net amount",
            "bill amount",
            "invoice amount",
            "revenue",
            "line total",
            "order amount",
            "sale amount",
            "sales amount",
            "sales",
            "expense",
            "expense amount",
        ],
    ),
    ("vendor", ["vendor", "supplier"]),
    ("warehouse", ["warehouse"]),
]

ENTITY_BY_CATEGORY = {
    "sales": "sale",
    "orders": "sale",
    "customers": "customer",
    "products": "product",
    "inventory": "inventory",
    "expenses": "expense",
}


def suggest_mapping(columns: list[str]) -> dict[str, str | None]:
    used: set[str] = set()
    result: dict[str, str | None] = {}
    normalized = {column: norm_header(column) for column in columns}
    for column, name in normalized.items():
        match = None
        for canonical, aliases in CANONICAL_FIELDS:
            if canonical in used:
                continue
            compact = name.replace(" ", "")
            alias_compact = {alias.replace(" ", "") for alias in aliases}
            if name in aliases or compact in alias_compact:
                match = canonical
                used.add(canonical)
                break
        result[column] = match
    return result


def entity_for(category: str, columns: list[str]) -> str:
    if category in ENTITY_BY_CATEGORY:
        return ENTITY_BY_CATEGORY[category]
    mapping = {value for value in suggest_mapping(columns).values() if value}
    if {"amount", "product_name"} & mapping and ("order_date" in mapping or "order_id" in mapping):
        return "sale"
    if "expense_date" in mapping or (category == "expenses"):
        return "expense"
    if "stock_qty" in mapping:
        return "inventory"
    if "email" in mapping and "customer_name" in mapping:
        return "customer"
    if "unit_price" in mapping and "product_name" in mapping:
        return "product"
    return "other"


def canonical_row(row: dict, mapping: dict[str, str | None]) -> dict:
    canon: dict[str, str | None] = {}
    for source, target in mapping.items():
        if target and source in row:
            canon[target] = row.get(source)
    return canon
