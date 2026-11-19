#!/usr/bin/env python3
"""Isolated forward paper pilot for ETF Faber Tactical Allocation (GTAA-5).

Strategy: Mebane Faber (2007) 10-month (SMA200) trend timing, LONG-only,
binary long/cash. LONG a symbol when Close > SMA200; exit to cash the day
Close drops below SMA200. This is the ONE active rule that buffy's
tools/sim_path_forward.py backtest showed is IS/OOS-stable and cost-
insensitive (drawdown ~halved at equal Sharpe) -- see
2026-11-15_1233AM_winning-strategies/buffy/10_simulations/BACKTEST_PROOF.md.

This pilot does NOT enable production sizing. It only paper-logs signals,
opens virtual positions, and closes them on the documented SMA-cross exit,
so the forward record grows in git history instead of rotting.

Reuses the deployed alpha_engine.etf_strategies.etf_faber_tactical so the
paper signal is identical to the live strategy definition.

Outputs (both consumed by .github/workflows/verified-pilot-daily.yml):
  verified_strategies/paper_pilot/faber_taa_paper_log.jsonl
  verified_strategies/paper_pilot/faber_taa_positions.json
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
# alpha_engine/etf_strategies.py does `from config import ...`; put alpha_engine
# on the path front (same trick as alpha_engine/etf_scanner.py) so it resolves
# to alpha_engine/config.py rather than the repo-root config/ package.
_AE = str(ROOT / "alpha_engine")
if _AE not in sys.path:
    sys.path.insert(0, _AE)

PILOT_DIR = Path(__file__).resolve().parent
LOG_PATH = PILOT_DIR / "faber_taa_paper_log.jsonl"
POSITIONS_PATH = PILOT_DIR / "faber_taa_positions.json"
STRATEGY_ID = "faber_taa_paper_pilot"
UNIVERSE = ["SPY", "QQQ", "EFA", "IEF", "GLD"]  # matches etf_faber_tactical faber_universe


def _utc_today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load_positions() -> dict:
    if POSITIONS_PATH.exists():
        try:
            return json.loads(POSITIONS_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {
        "strategy_id": STRATEGY_ID,
        "started_at": _utc_iso(),
        "started_at_date": _utc_today(),
        "day_count": 0,
        "last_run": None,
        "open": {},
        "closed": [],
    }


def _save_positions(pos: dict) -> None:
    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    POSITIONS_PATH.write_text(json.dumps(pos, indent=2, default=str), encoding="utf-8")


def _append_log(row: dict) -> None:
    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, default=str) + "\n")


def _append_forward_observation(rec: dict, sym: str, entry: float, exit_px: float,
                                today: str) -> None:
    """Append a closed Faber TAA trade to reports/forward_observations.jsonl.

    Uses the contract defined in alpha_engine/forward_observations.py.  Faber TAA
    is daily-resolution (not intrabar), so intrabar_first_touch=False — this
    means it can accrue forward rows for observation but cannot promote to
    PROVEN_T2 (which requires 100% intrabar first-touch).
    """
    import hashlib
    from datetime import datetime, timezone

    ledger = ROOT / "reports" / "forward_observations.jsonl"
    entry_date = rec.get("entry_date") or today
    # Convert dates to ISO-8601
    opened_at = f"{entry_date}T00:00:00+00:00" if "T" not in str(entry_date) else str(entry_date)
    closed_at = f"{today}T00:00:00+00:00"
    side = "LONG"
    # Direction-adjusted buy-and-hold benchmark leg (same window)
    # Approximate: use the price ratio as a proxy for the benchmark leg
    bench = (exit_px / entry - 1.0) if entry > 0 else None
    # Generate deterministic id
    basis = f"POD-FABER-TAA|{sym.upper()}|{side}|{opened_at}"
    row_id = "fwd_" + hashlib.sha256(basis.encode("utf-8")).hexdigest()[:20]
    row = {
        "id": row_id,
        "hypothesis_id": "H-2026-11-19-03",
        "opened_at": opened_at,
        "closed_at": closed_at,
        "symbol": sym.upper(),
        "asset_class": "ETF",
        "side": side,
        "entry_px": round(entry, 4),
        "exit_px": round(exit_px, 4),
        "qty": 1.0,
        "fees": 0.0,
        "funding": 0.0,
        "slippage_bps": 3.0,
        "resolver_version": "faber_taa_pilot.daily.v1",
        "intrabar_first_touch": False,
        "benchmark_leg_ret": round(bench, 6) if bench is not None else None,
        "regime_ok": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        ledger.parent.mkdir(parents=True, exist_ok=True)
        with ledger.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, default=str) + "\n")
    except Exception as exc:
        # Fail open — don't break the pilot
        pass


def _fetch_data() -> dict:
    """Daily closes for the GTAA-5 universe. auto_adjust handles dividends/splits."""
    import pandas as pd
    import yfinance as yf

    data: dict = {}
    for sym in UNIVERSE:
        try:
            df = yf.download(sym, period="2y", interval="1d", progress=False, auto_adjust=True)
        except Exception:
            continue
        if df is None or df.empty or len(df) < 210:
            continue
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        df = df.rename(columns=str.title)
        if "Close" in df.columns and len(df) > 200:
            data[sym] = df
    return data


def _latest_price(data: dict, sym: str) -> float | None:
    df = data.get(sym)
    if df is None or df.empty:
        return None
    try:
        v = df["Close"].iloc[-1]
        if hasattr(v, "item"):
            v = v.item()
        return float(v)
    except Exception:
        return None


def _stats(pos: dict) -> dict:
    closed = pos.get("closed", [])
    pnls = [float(c.get("pnl_pct", 0.0)) for c in closed]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    gw = sum(wins)
    gl = abs(sum(losses))
    return {
        "n_closed": len(pnls),
        "win_rate": round(len(wins) / len(pnls), 4) if pnls else 0.0,
        "profit_factor": round(gw / gl, 4) if gl > 0 else (float("inf") if gw > 0 else 0.0),
        "avg_pnl_pct": round(sum(pnls) / len(pnls), 4) if pnls else 0.0,
        "open_count": len(pos.get("open", {})),
    }


def run_one_shot() -> dict:
    from alpha_engine.etf_strategies import etf_faber_tactical

    today = _utc_today()
    pos = _load_positions()
    pos["day_count"] = int(pos.get("day_count", 0)) + 1
    pos.setdefault("open", {})
    pos.setdefault("closed", [])

    data = _fetch_data()
    if not data:
        pos["last_run"] = _utc_iso()
        pos["last_error"] = "no price data (yfinance unreachable)"
        _save_positions(pos)
        return {"date": today, "strategy": STRATEGY_ID, "error": "no price data", "day_count": pos["day_count"]}

    # 1) Close any open position whose symbol has crossed back below SMA200
    #    (the documented Faber exit rule). We recompute SMA200 from the same feed.
    import pandas as pd
    for sym in list(pos["open"].keys()):
        df = data.get(sym)
        if df is None:
            continue
        close = df["Close"]
        sma = close.rolling(200).mean()
        try:
            price = float(close.iloc[-1].item() if hasattr(close.iloc[-1], "item") else close.iloc[-1])
            sma_v = float(sma.iloc[-1].item() if hasattr(sma.iloc[-1], "item") else sma.iloc[-1])
        except Exception:
            continue
        if pd.isna(sma_v):
            continue
        if price < sma_v:  # exit to cash
            entry = float(pos["open"][sym]["entry_price"])
            pnl_pct = round((price / entry - 1.0) * 100.0, 4) if entry > 0 else 0.0
            rec = {
                "symbol": sym,
                "entry_price": entry,
                "exit_price": round(price, 4),
                "entry_date": pos["open"][sym].get("entry_date"),
                "exit_date": today,
                "pnl_pct": pnl_pct,
                "reason": "close_below_sma200",
            }
            pos["closed"].append(rec)
            _append_log({"date": today, "event": "CLOSE", "strategy": STRATEGY_ID, **rec})
            # Also write to the forward_observations ledger (contract format) so
            # POD-FABER-TAA accrues forward rows against the hold benchmark.
            _append_forward_observation(rec, sym, entry, price, today)
            del pos["open"][sym]

    # 2) Evaluate live Faber signals; open new virtual positions.
    signals = []
    try:
        signals = etf_faber_tactical(data)
    except Exception as exc:
        pos["last_error"] = f"strategy error: {exc}"
    opened = []
    for sig in signals:
        sym = sig.get("symbol")
        entry = float(sig.get("entry_price") or 0)
        if not sym or entry <= 0:
            continue
        _append_log({
            "date": today, "event": "SIGNAL", "strategy": STRATEGY_ID,
            "symbol": sym, "entry_price": entry,
            "take_profit": sig.get("take_profit"), "stop_loss": sig.get("stop_loss"),
            "confidence": sig.get("confidence"), "extra": sig.get("extra"),
        })
        if sym not in pos["open"]:
            pos["open"][sym] = {
                "symbol": sym,
                "direction": "LONG",
                "entry_price": round(entry, 4),
                "entry_date": today,
                "take_profit": sig.get("take_profit"),
                "stop_loss": sig.get("stop_loss"),
                "confidence": sig.get("confidence"),
                "sma200": (sig.get("extra") or {}).get("sma200"),
                "status": "OPEN",
            }
            opened.append(sym)
            _append_log({"date": today, "event": "OPEN", "strategy": STRATEGY_ID,
                         "symbol": sym, "entry_price": round(entry, 4)})

    st = _stats(pos)
    pos.update(st)
    pos["last_run"] = _utc_iso()
    _save_positions(pos)

    return {
        "date": today,
        "strategy": STRATEGY_ID,
        "day_count": pos["day_count"],
        "signals": len(signals),
        "opened": opened,
        "open_positions": sorted(pos["open"].keys()),
        **st,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--one-shot", action="store_true")
    args = ap.parse_args(argv)
    if not args.one_shot:
        ap.print_help()
        return 0
    print(json.dumps(run_one_shot(), indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
