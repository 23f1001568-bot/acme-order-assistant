
from fastapi import FastAPI
from pydantic import BaseModel
from pathlib import Path
import json

app = FastAPI(title="Acme Appliances Order Assistant")

BASE_DIR = Path(__file__).parent

with open(BASE_DIR / "orders.json", encoding="utf-8-sig") as f:
    ORDERS = json.load(f)

with open(BASE_DIR / "rates.json", encoding="utf-8-sig") as f:
    RATES = json.load(f)["usd_per_unit"]


class Question(BaseModel):
    question: str


@app.get("/")
def home():
    return {"message": "Acme Appliances Order Assistant is running"}


@app.get("/health")
def health():
    return {"status": "ok", "orders_loaded": len(ORDERS)}


@app.post("/ask")
def ask(data: Question):
    q = data.question.lower()

    # Count refunded Central orders created in May 2026
 
from fastapi import FastAPI
from pydantic import BaseModel
from pathlib import Path
from collections import defaultdict
import json
import re

app = FastAPI(title="Acme Appliances Order Assistant")

BASE_DIR = Path(__file__).parent


def load_json(filename):
    with open(BASE_DIR / filename, encoding="utf-8-sig") as f:
        return json.load(f)


ORDERS_DATA = load_json("orders.json")
RATES_DATA = load_json("rates.json")

# Support either a direct list or a dictionary containing orders.
if isinstance(ORDERS_DATA, list):
    ORDERS = ORDERS_DATA
elif isinstance(ORDERS_DATA, dict):
    ORDERS = ORDERS_DATA.get("orders", [])
else:
    ORDERS = []

if isinstance(RATES_DATA, dict):
    RATES = RATES_DATA.get("usd_per_unit", RATES_DATA)
else:
    RATES = {}


class Question(BaseModel):
    question: str


@app.get("/")
def home():
    return {
        "message": "Acme Appliances Order Assistant is running"
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "orders_loaded": len(ORDERS)
    }


def normalize(value):
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def get_latest_orders():
    """Keep the latest record for each order ID."""
    latest = {}

    for order in ORDERS:
        order_id = str(order.get("id", ""))

        if not order_id:
            continue

        if (
            order_id not in latest
            or str(order.get("updated_at", ""))
            > str(latest[order_id].get("updated_at", ""))
        ):
            latest[order_id] = order

    return list(latest.values())


def is_paid(order):
    return normalize(order.get("status")) == "paid"


@app.post("/ask")
def ask(data: Question):
    q = normalize(data.question)
    orders = get_latest_orders()

    # Count distinct customers with at least one paid Mixer order.
    if (
        "mixer" in q
        and "paid" in q
        and ("customer" in q or "customers" in q)
        and ("how many" in q or "count" in q or "different" in q)
    ):
        customers = {
            normalize(order.get("customer"))
            for order in orders
            if is_paid(order)
            and normalize(order.get("product")) == "mixer"
            and normalize(order.get("customer"))
        }

        return {"answer": len(customers)}

    # Count refunded orders in the Central region placed in May 2026.
    if (
        "count" in q
        and "refunded" in q
        and "central" in q
        and ("may 2026" in q or "2026-05" in q)
    ):
        count = sum(
            1
            for order in orders
            if normalize(order.get("status")) == "refunded"
            and normalize(order.get("region")) == "central"
            and str(order.get("created_at", ""))[:7] == "2026-05"
        )

        return {"answer": count}

    # Filter orders using details mentioned in the question.
    matches = []

    product_names = {
        "mixer",
        "refrigerator",
        "fridge",
        "washer",
        "washing machine",
        "oven",
        "dishwasher",
        "microwave",
        "blender",
        "dryer",
        "air conditioner",
        "ac",
        "television",
        "tv",
    }

    mentioned_products = [
        product for product in product_names if product in q
    ]

    status_names = {
        "paid",
        "refunded",
        "pending",
        "cancelled",
        "canceled",
        "shipped",
        "delivered",
    }

    mentioned_statuses = [
        status for status in status_names if status in q
    ]

    for order in orders:
        product = normalize(order.get("product"))
        status = normalize(order.get("status"))
        searchable = normalize(" ".join(str(v) for v in order.values()))

        if mentioned_products:
            product_match = any(
                normalize(p) in product or product in normalize(p)
                for p in mentioned_products
            )
            if not product_match:
                continue

        if mentioned_statuses:
            if not any(
                normalize(s) == status for s in mentioned_statuses
            ):
                continue

        # Match an explicitly mentioned order ID or customer value.
        tokens = re.findall(r"[a-zA-Z0-9_-]+", q)
        identifiers = [
            token for token in tokens
            if any(ch.isdigit() for ch in token)
        ]

        if identifiers and not any(
            identifier.lower() in searchable
            for identifier in identifiers
        ):
            # Do not apply identifier filtering to generic count queries.
            if not any(
                phrase in q
                for phrase in ("how many", "count", "total", "average")
            ):
                continue

        matches.append(order)

    # Return a count for simple "how many" questions.
    if any(phrase in q for phrase in ("how many", "count the", "count all")):
        return {"answer": len(matches)}

    if not matches:
        return {
            "answer": "No matching orders found. Try an order ID, customer, product, region, or status."
        }

    # Convert amounts to USD where rates are available.
    results = []

    for original in matches[:20]:
        order = original.copy()
        currency = str(order.get("currency", "USD")).upper()

        try:
            amount = float(order.get("amount", 0))
            rate = float(RATES.get(currency, 1))
            order["amount_usd"] = round(amount * rate, 2)
        except (TypeError, ValueError):
            order["amount_usd"] = None

        results.append(order)

    return {
        "answer": f"Found {len(matches)} matching order(s). Showing up to 20.",
        "orders": results,
    }

