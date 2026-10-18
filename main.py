
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
    matches = []

    for order in ORDERS:
        searchable = " ".join(str(order.get(k, "")) for k in order).lower()
        if any(word in searchable for word in q.split()):
            matches.append(order)

    if not matches:
        return {
            "answer": "I could not find a matching order. Try an order ID, customer ID, product, region, or status."
        }

    results = []
    for order in matches[:20]:
        order = order.copy()
        currency = order.get("currency", "USD")
        amount = float(order.get("amount", 0))
        order["amount_usd"] = round(amount * RATES.get(currency, 1), 2)
        results.append(order)

    return {
        "answer": f"Found {len(matches)} matching order(s). Showing up to 20.",
        "orders": results
    }
