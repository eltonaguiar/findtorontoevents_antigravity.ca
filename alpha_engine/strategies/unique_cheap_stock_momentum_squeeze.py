#!/usr/bin/env python3
"""Cheap Stocks asset class — delegates to backtest-validated winner (no placeholder prices)."""
from __future__ import annotations

from typing import Any

from alpha_engine.winners.cheap_stock_momentum_winner import generate_cheap_stock_momentum_winner_picks


def generate_cheap_stock_momentum_squeeze_picks() -> list[dict[str, Any]]:
    return generate_cheap_stock_momentum_winner_picks()


if __name__ == "__main__":
    picks = generate_cheap_stock_momentum_squeeze_picks()
    print(f"Generated {len(picks)} CHEAP_STOCKS picks (live yfinance, backtest PF 2.79)")
