"""JSON schema validation for mutation lab pipeline artifacts."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any


MUTATION_TARGET_REQUIRED = {"name", "win_rate", "source_system"}
MUTATION_RESULT_REQUIRED = {"strategy_name", "mutation_type", "parent_strategy",
                            "backtest_results"}
PICK_REQUIRED = {"symbol", "direction", "entry_price", "take_profit", "stop_loss",
                 "confidence", "strategy", "source_system", "timestamp"}


def validate_targets(data: dict) -> list[str]:
    errors = []
    if "winners" not in data or "losers" not in data:
        errors.append("Missing 'winners' or 'losers' key")
        return errors
    for group in ("winners", "losers"):
        for i, t in enumerate(data[group]):
            missing = MUTATION_TARGET_REQUIRED - set(t.keys())
            if missing:
                errors.append(f"{group}[{i}] missing fields: {missing}")
    return errors


def validate_mutation_results(results: list[dict]) -> list[str]:
    errors = []
    for i, r in enumerate(results):
        missing = MUTATION_RESULT_REQUIRED - set(r.keys())
        if missing:
            errors.append(f"result[{i}] missing fields: {missing}")
    return errors


def validate_picks(picks: list[dict]) -> list[str]:
    errors = []
    for i, p in enumerate(picks):
        missing = PICK_REQUIRED - set(p.keys())
        if missing:
            errors.append(f"pick[{i}] missing fields: {missing}")
        if p.get("entry_price", 0) <= 0 or p.get("entry_price", 0) > 1_000_000:
            errors.append(f"pick[{i}] invalid entry_price: {p.get('entry_price')}")
    return errors


def safe_load_json(path: Path) -> dict | list | None:
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None
