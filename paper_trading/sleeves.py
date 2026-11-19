"""Deterministic paper sleeves for the $2k allocation plan.

A sleeve is a small, independently-accounted paper portfolio. This module keeps it in
two JSON files (config + state) instead of the MySQL paper-trading schema, for three
reasons: the $2k plan is file-sized, every mark is reproducible from a committed
state file, and a broken DB cannot silently change a sleeve's equity.

Structure:
    config: {"sleeves": [{"id", "kind", "symbol", "asset_class", "capital"}]}
    state:  {"schema", "sleeves": {id: {symbol, shares, entry_price, entry_date,
                                        history: [{date, equity}]}}}

Only `kind == "buy_hold"` is implemented here. Signal sleeves (etf-rotation) need a
rebalance schedule and their own pre-registered rules; they are added separately so
this module never invents a signal.

CLI::

    python3 -m paper_trading.sleeves --init --date 2026-11-19
    python3 -m paper_trading.sleeves --mark --date 2026-11-19
    python3 -m paper_trading.sleeves --report --date 2026-11-19 \
        --out audit_dashboard/data/sleeve_daily.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

REPO = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO / "paper_trading" / "sleeves.json"
DEFAULT_STATE = REPO / "paper_trading" / "data" / "sleeves_state.json"
SCHEMA = "paper.sleeves.v1"

PriceFn = Callable[[str, str], float | None]


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def load_config(path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    return json.loads(Path(path).read_text())


def load_state(path: str | Path = DEFAULT_STATE) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {"schema": SCHEMA, "sleeves": {}}
    return json.loads(p.read_text())


def save_state(state: dict[str, Any], path: str | Path = DEFAULT_STATE) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=1, sort_keys=True) + "\n")


def init_sleeve(state: dict[str, Any], cfg: dict[str, Any], price: float,
                day: str | None = None) -> dict[str, Any]:
    """Buy the sleeve's instrument once, at ``price``, with the whole allocation."""
    day = day or _today()
    sid = cfg["id"]
    if sid in state["sleeves"]:
        return state["sleeves"][sid]
    if not price or price <= 0:
        raise ValueError(f"{sid}: cannot init without a positive price")
    capital = float(cfg["capital"])
    state["sleeves"][sid] = {
        "kind": cfg.get("kind", "buy_hold"),
        "symbol": cfg["symbol"],
        "asset_class": cfg.get("asset_class", ""),
        "capital": capital,
        "shares": capital / price,
        "entry_price": float(price),
        "entry_date": day,
        "history": [{"date": day, "equity": round(capital, 2)}],
    }
    return state["sleeves"][sid]


def mark(state: dict[str, Any], sid: str, price: float, day: str | None = None) -> float:
    """Append today's mark. Idempotent: re-marking a date replaces that date's row."""
    day = day or _today()
    s = state["sleeves"][sid]
    if not price or price <= 0:
        raise ValueError(f"{sid}: cannot mark without a positive price")
    equity = round(float(s["shares"]) * float(price), 2)
    hist = [h for h in s["history"] if h["date"] != day]
    hist.append({"date": day, "equity": equity})
    s["history"] = sorted(hist, key=lambda h: h["date"])
    return equity


def sleeve_report(state: dict[str, Any], cfg: dict[str, Any], price: float | None,
                  day: str | None = None) -> dict[str, Any]:
    """One sleeve's current numbers, in the shape the daily summary job publishes."""
    day = day or _today()
    sid = cfg["id"]
    s = state["sleeves"].get(sid)
    if not s:
        return {"id": sid, "status": "not_initialised", "capital": cfg.get("capital")}
    equity = round(float(s["shares"]) * float(price), 2) if price else s["history"][-1]["equity"]
    capital = float(s["capital"])
    ret_pct = (equity / capital - 1.0) * 100.0 if capital else 0.0
    peak = max(h["equity"] for h in s["history"])
    dd_pct = (equity / peak - 1.0) * 100.0 if peak else 0.0
    return {
        "id": sid,
        "status": "live_paper",
        "symbol": s["symbol"],
        "asset_class": s.get("asset_class", ""),
        "capital": capital,
        "entry_date": s["entry_date"],
        "entry_price": s["entry_price"],
        "price": price,
        "equity": equity,
        "return_pct": round(ret_pct, 4),
        "drawdown_pct": round(dd_pct, 4),
        "n_marks": len(s["history"]),
        "as_of": day,
    }


def random_arm_applicable(cfg: dict[str, Any]) -> bool:
    """A buy-and-hold sleeve *is* the benchmark; a random arm adds nothing.

    Only signal sleeves (rotation, breakout) need the random-entry control, because
    only they make a timing claim.
    """
    return cfg.get("kind") != "buy_hold"


def _db_price(symbol: str, day: str) -> float | None:
    """Last close for ``symbol`` on ``day`` from the canonical bar fetcher."""
    import tools.stamp_entry_conditions as S  # local import: keeps tests offline

    d = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    lo = int(d.timestamp() * 1000)
    hi = lo + 86_400_000
    table = "crypto_ohlcv" if symbol.upper().endswith(("USDT", "USD")) else "stock_ohlcv"
    bars = S.fetch_bars({table: {symbol: (lo, hi)}}) or {}
    series = bars.get(symbol) or []
    return float(series[-1][1]) if series else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Deterministic paper sleeves ($2k plan)")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    ap.add_argument("--state", default=str(DEFAULT_STATE))
    ap.add_argument("--date", default=_today())
    ap.add_argument("--init", action="store_true", help="open any uninitialised sleeve")
    ap.add_argument("--mark", action="store_true", help="append today's marks")
    ap.add_argument("--report", action="store_true", help="write the daily sleeve report")
    ap.add_argument("--out", default=None)
    ap.add_argument("--price", action="append", default=[],
                    metavar="SYMBOL=PX", help="offline price override (repeatable)")
    args = ap.parse_args(argv)

    overrides = dict(p.split("=", 1) for p in args.price)
    price_of: PriceFn = lambda sym, day: (float(overrides[sym]) if sym in overrides
                                          else _db_price(sym, day))

    cfg = load_config(args.config)
    state = load_state(args.state)
    rows = []
    for sleeve in cfg["sleeves"]:
        px = price_of(sleeve["symbol"], args.date)
        if args.init:
            init_sleeve(state, sleeve, px, args.date)
        if args.mark and sleeve["id"] in state["sleeves"]:
            mark(state, sleeve["id"], px, args.date)
        rows.append(sleeve_report(state, sleeve, px, args.date))
    save_state(state, args.state)

    out = {
        "schema": "paper.sleeve_daily.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "as_of": args.date,
        "sleeves": rows,
    }
    text = json.dumps(out, indent=1)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
