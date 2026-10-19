"""JSON ledger of positions + monthly returns; records starting positions."""
from __future__ import annotations

import json
from pathlib import Path


def init_ledger(starting_positions, path, capital=100_000.0, date_closed="2026-09-30"):
    doc = {
        "currency": "USD",
        "capital": capital,
        "start_date": date_closed,
        "starting_positions": dict(starting_positions),
        "monthly_returns": [],
        "cash": capital,
        "positions": dict(starting_positions),
    }
    save_ledger(doc, path)
    return doc


def load_ledger(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def append_month_row(ledger, month_label, book_return, positions):
    ledger["monthly_returns"].append(
        {"month": month_label, "return": float(book_return)}
    )
    ledger["positions"] = dict(positions)
    total_ret = sum(r["return"] for r in ledger["monthly_returns"])
    ledger["cash"] = ledger["capital"] * (1.0 + total_ret)
    return ledger


def save_ledger(ledger, path):
    Path(path).write_text(json.dumps(ledger, indent=2), encoding="utf-8")
