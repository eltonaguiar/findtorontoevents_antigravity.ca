#!/usr/bin/env python3
"""30-day forward paper pilot for G10 forex carry (forex_carry_g10).

Backtest UNLOCK_READY (2010-2026): n=197, WR=60.4%, PF=1.59.
See reports/forex_carry_backtest_extended_20260606.json.

Virtual monthly basket: LONG top-3 carry / SHORT bottom-3 vs USD.
FOREX_HARD_DISABLE=0 — production enabled. Pilot tracks until 30 forward closes for T2 promotion.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PILOT_DIR = Path(__file__).resolve().parent
LOG_PATH = PILOT_DIR / "forex_carry_g10_paper_log.jsonl"
STATE_PATH = PILOT_DIR / "forex_carry_g10_state.json"
STRATEGY_ID = "forex_carry_g10"
LAB_PF = 1.59
LAB_WR = 0.604
LAB_N = 197

CCY_TO_PAIR = {
    "EUR": "EURUSD=X",
    "GBP": "GBPUSD=X",
    "JPY": "JPYUSD=X",
    "AUD": "AUDUSD=X",
    "CAD": "CADUSD=X",
    "CHF": "CHFUSD=X",
    "NOK": "NOKUSD=X",
    "SEK": "SEKUSD=X",
    "NZD": "NZDUSD=X",
}


def _utc_today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {
        "strategy_id": STRATEGY_ID,
        "started_at": _utc_iso(),
        "started_at_date": _utc_today(),
        "day_count": 0,
        "n_closed": 0,
        "open_basket": None,
        "last_rebalance_month": None,
    }


def _save_state(state: dict) -> None:
    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _append_log(row: dict) -> None:
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, default=str) + "\n")


def _month_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _fetch_month_return(pair: str) -> float | None:
    import yfinance as yf

    try:
        px = yf.download(pair, period="3mo", interval="1mo", progress=False, auto_adjust=True)
    except Exception:
        return None
    if px is None or px.empty or len(px) < 2:
        return None
    col = "Close" if "Close" in px.columns else px.columns[0]
    s = px[col].dropna()
    if len(s) < 2:
        return None
    return float(s.iloc[-1] / s.iloc[-2] - 1.0)


def _basket_return(basket: dict) -> float | None:
    rets: list[float] = []
    for leg in basket.get("legs", []):
        pair = leg.get("pair")
        direction = leg.get("direction", "LONG")
        if not pair:
            continue
        r = _fetch_month_return(pair)
        if r is None:
            return None
        rets.append(r if direction == "LONG" else -r)
    if not rets:
        return None
    return sum(rets) / len(rets)


def run_one_shot() -> dict:
    from tools.research.forex_carry import build_signals, fetch_current_rates

    today = _utc_today()
    month = _month_key()
    state = _load_state()
    state["day_count"] = int(state.get("day_count", 0)) + 1

    rates = fetch_current_rates()
    signals = build_signals(rates)
    legs = []
    for s in signals:
        ccy = s.get("ccy")
        pair = CCY_TO_PAIR.get(str(ccy))
        if not pair:
            continue
        legs.append({
            "ccy": ccy,
            "pair": pair,
            "direction": s.get("direction"),
            "carry_bps": s.get("carry_bps"),
        })

    open_basket = state.get("open_basket")
    last_month = state.get("last_rebalance_month")

    if open_basket and last_month and last_month != month:
        pnl = _basket_return(open_basket)
        if pnl is not None:
            outcome = "WIN" if pnl > 0 else "LOSS"
            state["n_closed"] = int(state.get("n_closed", 0)) + 1
            _append_log({
                "date": today,
                "event": "CLOSE",
                "strategy": STRATEGY_ID,
                "month": last_month,
                "pnl_pct": round(pnl * 100, 4),
                "outcome": outcome,
                "legs": open_basket.get("legs"),
            })
        open_basket = None

    if open_basket is None:
        open_basket = {
            "month": month,
            "legs": legs,
            "opened_at": _utc_iso(),
        }
        state["last_rebalance_month"] = month
        _append_log({
            "date": today,
            "event": "OPEN",
            "strategy": STRATEGY_ID,
            "month": month,
            "legs": legs,
        })

    state["open_basket"] = open_basket
    state["last_run"] = _utc_iso()
    _save_state(state)

    return {
        "date": today,
        "strategy": STRATEGY_ID,
        "month": month,
        "n_closed": state.get("n_closed", 0),
        "open_legs": len(legs),
        "lab_reference": {"n": LAB_N, "wr": LAB_WR, "pf": LAB_PF},
        "forex_hard_disable": "0 — production enabled",
        "promotion_note": "Need 30 forward monthly closes + PF within 30% of lab",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--one-shot", action="store_true")
    ap.add_argument("--write-db", action="store_true", help="Write basket legs to trading_picks")
    args = ap.parse_args(argv)
    if not args.one_shot:
        ap.print_help()
        return 0
    result = run_one_shot()
    if args.write_db and result["basket"]:
        n = _write_basket_to_db(result["basket"])
        print(f"[DB] Inserted/updated {n} pick(s)", file=sys.stderr)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


def _write_basket_to_db(legs: list[dict]) -> int:
    """Write each leg of the carry basket to trading_picks with live yfinance prices."""
    import pymysql
    from tools.db_env import get_stocks_creds
    from datetime import datetime, timezone
    try:
        import yfinance as yf
    except ImportError:
        yf = None

    creds = get_stocks_creds()
    conn = pymysql.connect(**creds, cursorclass=pymysql.cursors.DictCursor)
    cur = conn.cursor()

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    inserted = 0

    for leg in legs:
        month = _month_key(); pick_id = f"fxcarry_{leg['ccy']}_{month}"
        pair = leg["pair"]

        # Fetch live price from yfinance
        entry_price = 1.0
        if yf is not None:
            try:
                ticker = yf.Ticker(pair)
                hist = ticker.history(period="1d")
                if not hist.empty:
                    entry_price = float(hist["Close"].iloc[-1])
            except Exception:
                pass  # fallback to 1.0 placeholder

        # Monthly carry: 1.5% TP / 1.0% SL (conservative for carry factor)
        if leg["direction"] == "LONG":
            take_profit = round(entry_price * 1.015, 6)
            stop_loss = round(entry_price * 0.990, 6)
        else:
            take_profit = round(entry_price * 0.985, 6)
            stop_loss = round(entry_price * 1.010, 6)

        row = {
            "id": pick_id,
            "symbol": pair,
            "direction": "LONG" if leg["direction"] == "LONG" else "SHORT",
            "strategy": STRATEGY_ID,
            "entry_price": entry_price,
            "take_profit": take_profit,
            "stop_loss": stop_loss,
            "confidence": 0.65,
            "elite_score": 70,
            "trust_score": 65,
            "category": "FOREX",
            "source_system": STRATEGY_ID,
            "status": "OPEN",
            "pnl_pct": None,
            "exit_price": None,
            "created_at": now,
            "closed_at": None,
            "exit_reason": None,
        }
        cur.execute("""
            INSERT INTO trading_picks
                (id, symbol, direction, strategy, entry_price, take_profit, stop_loss,
                 confidence, elite_score, trust_score, category, source_system,
                 status, pnl_pct, exit_price, created_at, closed_at, exit_reason)
            VALUES
                (%(id)s, %(symbol)s, %(direction)s, %(strategy)s, %(entry_price)s,
                 %(take_profit)s, %(stop_loss)s, %(confidence)s, %(elite_score)s,
                 %(trust_score)s, %(category)s, %(source_system)s, %(status)s,
                 %(pnl_pct)s, %(exit_price)s, %(created_at)s, %(closed_at)s, %(exit_reason)s)
            ON DUPLICATE KEY UPDATE
                status = VALUES(status), created_at = VALUES(created_at)
        """, row)
        inserted += 1

    conn.commit()
    conn.close()
    return inserted
