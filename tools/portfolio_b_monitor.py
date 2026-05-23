#!/usr/bin/env python3
"""Portfolio B position monitor.

Tracks the TV paper TESTER account limit orders placed on 2026-04-04 as
substitutes for the illiquid futures/FX picks in
`alpha_engine/data/joint_filtered_commodity_lean_2026-04-04.json`.

Placed orders (GTC, expire 2026-04-11):
  - AMEX:CPER BUY LIMIT 1sh @ 34.37, TP 36.54, SL 33.07
  - AMEX:SLV SELL LIMIT 1sh @ 65.79, TP 62.50, SL 67.76

CLI:
  python tools/portfolio_b_monitor.py [--fetch-quotes]
                                      [--output path/to/status.json]
                                      [--status-override path/to/overrides.json]

Always exits 0. Gracefully degrades if yfinance is unavailable.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = REPO_ROOT / "alpha_engine" / "data" / "joint_filtered_commodity_lean_2026-04-04.json"
DEFAULT_OUTPUT = REPO_ROOT / "alpha_engine" / "data" / "portfolio_b_status.json"

# Orders actually placed on TV paper TESTER account (these substitute for the
# futures/FX picks in the spec file, which aren't tradeable on that venue).
PLACED_ORDERS: list[dict[str, Any]] = [
    {
        "tv_symbol": "AMEX:CPER",
        "yf_symbol": "CPER",
        "asset_class": "COMMODITY",
        "substitute_for": "HG=F (Copper)",
        "direction": "LONG",
        "order_type": "BUY_LIMIT",
        "time_in_force": "GTC",
        "expires": "2026-04-11",
        "shares": 1,
        "limit_price": 34.37,
        "take_profit": 36.54,
        "stop_loss": 33.07,
    },
    {
        "tv_symbol": "AMEX:SLV",
        "yf_symbol": "SLV",
        "asset_class": "COMMODITY",
        "substitute_for": "SI=F (Silver)",
        "direction": "SHORT",
        "order_type": "SELL_LIMIT",
        "time_in_force": "GTC",
        "expires": "2026-04-11",
        "shares": 1,
        "limit_price": 65.79,
        "take_profit": 62.50,
        "stop_loss": 67.76,
    },
]


def _try_import_yfinance():
    try:
        import yfinance as yf  # type: ignore
        return yf
    except Exception:
        return None


def _fetch_quote(yf, symbol: str) -> dict[str, Any]:
    """Pull a snapshot quote for `symbol`. Returns dict with last/prev/source."""
    out: dict[str, Any] = {"symbol": symbol, "last": None, "prev_close": None, "error": None}
    try:
        t = yf.Ticker(symbol)
        # Try fast_info first (lightweight), fall back to history
        last = None
        prev = None
        try:
            fi = getattr(t, "fast_info", None)
            if fi is not None:
                last = fi.get("last_price") if hasattr(fi, "get") else getattr(fi, "last_price", None)
                prev = fi.get("previous_close") if hasattr(fi, "get") else getattr(fi, "previous_close", None)
        except Exception:
            pass
        if last is None or last != last:  # NaN check
            hist = t.history(period="5d", interval="1d", auto_adjust=False)
            if not hist.empty:
                last = float(hist["Close"].iloc[-1])
                if len(hist) >= 2:
                    prev = float(hist["Close"].iloc[-2])
        out["last"] = float(last) if last is not None else None
        out["prev_close"] = float(prev) if prev is not None else None
    except Exception as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def _classify(order: dict[str, Any], current: float | None,
              override: str | None) -> dict[str, Any]:
    """Determine working/filled/won/lost/expired state."""
    # Respect manual override first.
    if override:
        return {"state": override.upper(), "source": "override"}

    now = datetime.now(timezone.utc)
    try:
        exp = datetime.fromisoformat(order["expires"] + "T23:59:59+00:00")
    except Exception:
        exp = None
    if exp and now > exp:
        return {"state": "EXPIRED", "source": "expiry_check"}

    if current is None:
        return {"state": "WORKING_UNKNOWN",
                "source": "no_live_quote",
                "note": "Markets closed or quote unavailable; assume WORKING."}

    direction = order["direction"]
    lp = order["limit_price"]
    tp = order["take_profit"]
    sl = order["stop_loss"]

    # NB: a single snapshot cannot prove fill/TP/SL — real fill state lives in
    # TV. We report the *inferred* state based on whether price has traded
    # through each level at quote time. Mark as _INFERRED.
    if direction == "LONG":
        # BUY LIMIT fills when price <= limit
        if current <= sl:
            return {"state": "LOST_INFERRED", "source": "snapshot",
                    "note": "Price at/below SL — if filled earlier, would be stopped."}
        if current >= tp:
            return {"state": "WON_INFERRED", "source": "snapshot",
                    "note": "Price at/above TP — if filled earlier, would be TP-hit."}
        if current <= lp:
            return {"state": "FILLED_INFERRED", "source": "snapshot",
                    "note": "Price at/below limit — order likely filled."}
        return {"state": "WORKING", "source": "snapshot"}
    else:  # SHORT
        # SELL LIMIT fills when price >= limit
        if current >= sl:
            return {"state": "LOST_INFERRED", "source": "snapshot",
                    "note": "Price at/above SL — if filled earlier, would be stopped."}
        if current <= tp:
            return {"state": "WON_INFERRED", "source": "snapshot",
                    "note": "Price at/below TP — if filled earlier, would be TP-hit."}
        if current >= lp:
            return {"state": "FILLED_INFERRED", "source": "snapshot",
                    "note": "Price at/above limit — order likely filled."}
        return {"state": "WORKING", "source": "snapshot"}


def _distances(order: dict[str, Any], current: float | None) -> dict[str, Any]:
    if current is None:
        return {}
    lp = order["limit_price"]
    tp = order["take_profit"]
    sl = order["stop_loss"]

    def pct(target: float) -> float:
        return round((target - current) / current * 100.0, 3)

    return {
        "current": current,
        "to_fill_abs": round(lp - current, 4),
        "to_fill_pct": pct(lp),
        "to_tp_abs": round(tp - current, 4),
        "to_tp_pct": pct(tp),
        "to_sl_abs": round(sl - current, 4),
        "to_sl_pct": pct(sl),
    }


def _hypothetical_pnl(order: dict[str, Any], current: float | None) -> dict[str, Any]:
    """PnL if filled at limit and marked at current price."""
    if current is None:
        return {}
    lp = order["limit_price"]
    shares = order["shares"]
    if order["direction"] == "LONG":
        pnl = (current - lp) * shares
    else:
        pnl = (lp - current) * shares
    return {
        "fill_price_assumed": lp,
        "mark_price": current,
        "shares": shares,
        "pnl_usd": round(pnl, 4),
        "pnl_pct_of_notional": round(pnl / (lp * shares) * 100.0, 3),
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Portfolio B TV-paper position monitor")
    ap.add_argument("--fetch-quotes", action="store_true",
                    help="Pull live quotes via yfinance if available")
    ap.add_argument("--output", default=str(DEFAULT_OUTPUT),
                    help="Path to write status JSON (default: %(default)s)")
    ap.add_argument("--status-override", default=None,
                    help="Path to JSON mapping tv_symbol -> manual status")
    args = ap.parse_args(argv)

    overrides: dict[str, str] = {}
    if args.status_override:
        try:
            overrides = json.loads(Path(args.status_override).read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"[warn] could not read status override: {exc}", file=sys.stderr)

    yf = _try_import_yfinance() if args.fetch_quotes else None
    yfinance_available = yf is not None

    spec_summary: dict[str, Any] = {}
    if SPEC_PATH.exists():
        try:
            spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
            spec_summary = {
                "portfolio_name": spec.get("portfolio_name"),
                "generated_at_utc": spec.get("generated_at_utc"),
                "num_picks_in_spec": len(spec.get("picks", [])),
            }
        except Exception as exc:
            spec_summary = {"error": str(exc)}

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    positions: list[dict[str, Any]] = []
    print(f"Portfolio B monitor — {now_iso}")
    print(f"  spec: {SPEC_PATH.name}  yfinance={yfinance_available}")
    print("=" * 72)

    for order in PLACED_ORDERS:
        quote = None
        current = None
        if yf is not None:
            quote = _fetch_quote(yf, order["yf_symbol"])
            current = quote.get("last")

        status = _classify(order, current, overrides.get(order["tv_symbol"]))
        dists = _distances(order, current)
        pnl = _hypothetical_pnl(order, current)

        pos = {
            "tv_symbol": order["tv_symbol"],
            "yf_symbol": order["yf_symbol"],
            "direction": order["direction"],
            "order_type": order["order_type"],
            "time_in_force": order["time_in_force"],
            "expires": order["expires"],
            "levels": {
                "limit": order["limit_price"],
                "take_profit": order["take_profit"],
                "stop_loss": order["stop_loss"],
                "shares": order["shares"],
            },
            "quote": quote,
            "status": status,
            "distances": dists,
            "hypothetical_pnl": pnl,
        }
        positions.append(pos)

        print(f"\n{order['tv_symbol']}  {order['direction']}  {order['order_type']}")
        print(f"  entry={order['limit_price']}  TP={order['take_profit']}  SL={order['stop_loss']}  (GTC {order['expires']})")
        if current is not None:
            print(f"  current={current:.4f}  "
                  f"to_fill={dists['to_fill_pct']:+.3f}%  "
                  f"to_TP={dists['to_tp_pct']:+.3f}%  "
                  f"to_SL={dists['to_sl_pct']:+.3f}%")
            print(f"  hypothetical PnL if filled @ limit: ${pnl['pnl_usd']:+.4f} "
                  f"({pnl['pnl_pct_of_notional']:+.3f}%)")
        elif args.fetch_quotes:
            err = quote.get("error") if quote else "no quote"
            print(f"  [no quote] {err}")
        else:
            print("  (no quote — pass --fetch-quotes for live data)")
        print(f"  state={status['state']}  source={status['source']}")
        if "note" in status:
            print(f"  note: {status['note']}")

    report = {
        "generated_at_utc": now_iso,
        "spec_source": str(SPEC_PATH.relative_to(REPO_ROOT)),
        "spec_summary": spec_summary,
        "venue": "TradingView paper / TESTER account",
        "yfinance_available": yfinance_available,
        "fetch_quotes_requested": bool(args.fetch_quotes),
        "positions": positions,
        "manual_check_instructions": [
            "Open TradingView Desktop → TESTER paper account",
            "Orders tab: verify CPER BUY LIMIT 1@34.37 and SLV SELL LIMIT 1@65.79 still WORKING",
            "Positions tab: if filled, note entry fill price and mark-to-market",
            "Markets closed weekends; CPER/SLV resume Mon 09:30 ET",
        ],
    }

    out_path = Path(args.output)
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nwrote {out_path}")
    except Exception as exc:
        print(f"[warn] could not write output: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    try:
        rc = main(sys.argv[1:])
    except Exception as exc:
        print(f"[monitor-error] {type(exc).__name__}: {exc}", file=sys.stderr)
        rc = 0  # monitoring never breaks pipelines
    sys.exit(rc)
