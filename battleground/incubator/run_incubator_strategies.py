#!/usr/bin/env python3
"""
Incubator Strategy Runner
==========================

Runs all registered incubator strategies, collects their signals, tracks them
over time in a persistent JSON ledger, and writes outputs compatible with the
baby-strat-forward-paper pipeline.

Outputs:
  - battleground/data/incubator_signals.json   (latest signals from this run)
  - battleground/data/incubator_ledger.json    (cumulative trade tracker — persists across runs)

The ledger accumulates picks over multiple hourly runs.  Each pick is tracked
until its TP or SL is hit (checked against live prices), at which point it
moves from "open" to "closed" with a WIN/LOSS status.  Once a strategy
accumulates enough closed trades, it can pass the quality gates in
export_top_picks.py (10+ trades, 55-95% WR).

Integration:
  The workflow step that runs this script should execute BEFORE
  `generate_baby_strats_dashboard.py` and `export_top_picks.py`.
  After this script writes the ledger, a merge step injects incubator
  strategy entries into the dashboard JSON so the exporter can see them.

Run standalone:
    python battleground/incubator/run_incubator_strategies.py
"""

from __future__ import annotations

import json
import logging
import sys
import traceback
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Allow imports from repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

try:
    import requests
except ImportError:
    requests = None  # type: ignore

from battleground.incubator.strategies import STRATEGY_REGISTRY

# ── Paths ────────────────────────────────────────────────────────────
DATA_DIR = REPO_ROOT / "battleground" / "data"
SIGNALS_OUT = DATA_DIR / "incubator_signals.json"
LEDGER_PATH = DATA_DIR / "incubator_ledger.json"
DASHBOARD_JSON = DATA_DIR / "baby_strats_dashboard.json"

# ── Logging ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("incubator_runner")


# ── Price Fetching ───────────────────────────────────────────────────

def fetch_current_price(symbol: str) -> Optional[float]:
    """Fetch current price from OKX (no geo-block) or CoinGecko fallback."""
    if requests is None:
        return None
    # OKX
    try:
        inst = symbol.replace("USDT", "-USDT")
        r = requests.get(
            f"https://www.okx.com/api/v5/market/ticker?instId={inst}",
            timeout=8,
        )
        if r.status_code == 200:
            data = r.json().get("data", [])
            if data:
                return float(data[0]["last"])
    except Exception:
        pass
    # CoinGecko fallback
    try:
        cg_map = {
            "BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "SOLUSDT": "solana",
            "XRPUSDT": "ripple", "BNBUSDT": "binancecoin", "DOGEUSDT": "dogecoin",
        }
        cg_id = cg_map.get(symbol)
        if cg_id:
            r = requests.get(
                f"https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd",
                timeout=8,
            )
            if r.status_code == 200:
                return float(r.json()[cg_id]["usd"])
    except Exception:
        pass
    return None


# ── Ledger Management ────────────────────────────────────────────────

def load_ledger() -> Dict[str, Any]:
    """Load the persistent incubator ledger."""
    if LEDGER_PATH.exists():
        try:
            return json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("Failed to load ledger, starting fresh: %s", e)
    return {"strategies": {}, "updated_at": None}


def save_ledger(ledger: Dict[str, Any]) -> None:
    """Save the ledger to disk."""
    ledger["updated_at"] = datetime.now(timezone.utc).isoformat()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LEDGER_PATH.write_text(json.dumps(ledger, indent=2, default=str), encoding="utf-8")


def _ensure_strategy_entry(ledger: Dict[str, Any], name: str) -> Dict[str, Any]:
    """Ensure a strategy has an entry in the ledger."""
    if name not in ledger["strategies"]:
        ledger["strategies"][name] = {
            "open_picks": [],
            "closed_trades": [],
            "total_signals_generated": 0,
            "first_seen": datetime.now(timezone.utc).isoformat(),
        }
    return ledger["strategies"][name]


def _check_open_picks(ledger: Dict[str, Any]) -> int:
    """Check all open picks against live prices. Close any that hit TP/SL.
    Returns count of newly closed trades."""
    closed_count = 0

    for strat_name, strat_data in ledger["strategies"].items():
        still_open = []
        for pick in strat_data.get("open_picks", []):
            symbol = pick.get("symbol", "BTCUSDT")
            price = fetch_current_price(symbol)
            if price is None:
                still_open.append(pick)
                continue

            direction = pick.get("direction", "BUY")
            tp = pick.get("take_profit")
            sl = pick.get("stop_loss")
            entry = pick.get("entry_price")

            hit_tp = False
            hit_sl = False

            if direction == "BUY":
                if tp and price >= tp:
                    hit_tp = True
                elif sl and price <= sl:
                    hit_sl = True
            else:  # SELL
                if tp and price <= tp:
                    hit_tp = True
                elif sl and price >= sl:
                    hit_sl = True

            if hit_tp or hit_sl:
                pnl_pct = 0.0
                if entry and entry > 0:
                    if direction == "BUY":
                        pnl_pct = ((price - entry) / entry) * 100
                    else:
                        pnl_pct = ((entry - price) / entry) * 100

                trade = {
                    "symbol": symbol,
                    "direction": direction,
                    "entry_price": entry,
                    "exit_price": round(price, 2),
                    "take_profit": tp,
                    "stop_loss": sl,
                    "pnl_pct": round(pnl_pct, 4),
                    "exit_reason": "TP_HIT" if hit_tp else "SL_HIT",
                    "entry_time": pick.get("generated_at", ""),
                    "exit_time": datetime.now(timezone.utc).isoformat(),
                    "strategy": strat_name,
                }
                strat_data.setdefault("closed_trades", []).append(trade)
                closed_count += 1
                logger.info(
                    "  [CLOSED] %s %s %s @ %.2f -> %.2f (%.2f%%) %s",
                    strat_name, direction, symbol, entry, price,
                    pnl_pct, trade["exit_reason"],
                )
            else:
                still_open.append(pick)

        strat_data["open_picks"] = still_open

    return closed_count


def _deduplicate_pick(open_picks: List[Dict], new_pick: Dict) -> bool:
    """Return True if this pick is a duplicate of an existing open pick
    (same symbol + direction within a reasonable time window)."""
    for existing in open_picks:
        if (existing.get("symbol") == new_pick.get("symbol")
                and existing.get("direction") == new_pick.get("direction")):
            return True
    return False


# ── Dashboard Injection ──────────────────────────────────────────────

def inject_into_dashboard(ledger: Dict[str, Any]) -> None:
    """Inject incubator strategy entries into the baby_strats_dashboard.json
    so that export_top_picks.py can see them and apply quality gates."""
    if not DASHBOARD_JSON.exists():
        logger.warning("Dashboard JSON not found at %s — skipping injection", DASHBOARD_JSON)
        return

    try:
        dashboard = json.loads(DASHBOARD_JSON.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error("Failed to read dashboard: %s", e)
        return

    strategies = dashboard.get("strategies", [])
    existing_names = {s["name"] for s in strategies}

    injected = 0
    for strat_name, strat_data in ledger["strategies"].items():
        closed = strat_data.get("closed_trades", [])
        open_picks = strat_data.get("open_picks", [])

        # Compute forward metrics from closed trades
        total_trades = len(closed)
        wins = sum(1 for t in closed if t.get("pnl_pct", 0) > 0)
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0

        # Build a dashboard-compatible strategy entry
        entry = {
            "name": strat_name,
            "agent_id": "incubator",
            "category": "incubator_live",
            "status": "paper_trading",
            "stage": 2,
            "backtest_metrics": {
                "win_rate": None,
                "sharpe": None,
                "max_drawdown": None,
                "total_trades": 0,
                "profit_factor": None,
                "total_return": None,
                "period_days": 0,
                "data_source": "incubator_live",
                "updated_from": "incubator_runner",
            },
            "unique_value": f"Incubator strategy: {strat_name}",
            "verification": {
                "real_data_verified": True,
                "verification_level": "live_forward",
                "market_data_basis": "live_binance_okx",
                "auxiliary_data_basis": "not_used",
                "note": "Live forward signals from incubator runner.",
            },
            "forward_metrics": {
                "win_rate": round(win_rate, 2),
                "sharpe": None,
                "max_drawdown": None,
                "total_trades": total_trades,
            },
            "forward_live_pick_count": len(open_picks),
            "forward_live_picks": [
                {
                    "symbol": p.get("symbol", "BTCUSDT"),
                    "side": p.get("direction", "BUY"),
                    "entry_price": p.get("entry_price"),
                    "take_profit": p.get("take_profit"),
                    "stop_loss": p.get("stop_loss"),
                    "generated_at": p.get("generated_at", ""),
                    "source": "incubator_live",
                }
                for p in open_picks
            ],
            "forward_trades": closed,
        }

        if strat_name in existing_names:
            # Update existing entry
            for i, s in enumerate(strategies):
                if s["name"] == strat_name:
                    strategies[i] = entry
                    break
        else:
            strategies.append(entry)
            injected += 1

    dashboard["strategies"] = strategies
    dashboard["total_strategies"] = len(strategies)
    DASHBOARD_JSON.write_text(json.dumps(dashboard, indent=2, default=str), encoding="utf-8")
    logger.info(
        "Injected %d new incubator strategies into dashboard (%d total strategies)",
        injected, len(strategies),
    )


# ── Signal Serialization ─────────────────────────────────────────────

def signal_to_dict(sig: Any) -> Dict[str, Any]:
    """Convert a Signal dataclass to dict, handling both dataclass and plain dict."""
    if hasattr(sig, "__dataclass_fields__"):
        return {k: v for k, v in asdict(sig).items()}
    if isinstance(sig, dict):
        return sig
    # Fallback: try common attributes
    return {
        "symbol": getattr(sig, "symbol", "UNKNOWN"),
        "direction": getattr(sig, "direction", "BUY"),
        "confidence": getattr(sig, "confidence", 0),
        "entry_price": getattr(sig, "entry_price", 0),
        "take_profit": getattr(sig, "take_profit", 0),
        "stop_loss": getattr(sig, "stop_loss", 0),
        "reason": getattr(sig, "reason", ""),
        "strategy": getattr(sig, "strategy", "unknown"),
        "timeframe": getattr(sig, "timeframe", ""),
    }


# ── Main Runner ──────────────────────────────────────────────────────

def run_all_strategies() -> Dict[str, Any]:
    """Run all registered incubator strategies and return results summary."""
    now = datetime.now(timezone.utc)
    results = {
        "run_at": now.isoformat(),
        "strategies_run": 0,
        "strategies_with_signals": 0,
        "strategies_failed": 0,
        "total_signals": 0,
        "signals": [],
        "errors": [],
    }

    logger.info("=" * 60)
    logger.info("INCUBATOR STRATEGY RUNNER  |  %s", now.strftime("%Y-%m-%d %H:%M UTC"))
    logger.info("Registered strategies: %d", len(STRATEGY_REGISTRY))
    logger.info("=" * 60)

    # Load persistent ledger
    ledger = load_ledger()

    # First, check existing open picks against live prices
    logger.info("Checking open picks against live prices...")
    closed_count = _check_open_picks(ledger)
    logger.info("Closed %d picks from previous runs", closed_count)

    # Run each strategy
    for strat_name, strat_cls in STRATEGY_REGISTRY.items():
        logger.info("-" * 40)
        logger.info("Running: %s", strat_name)
        results["strategies_run"] += 1

        try:
            strategy = strat_cls()
            signals = strategy.generate_signals()

            if signals:
                results["strategies_with_signals"] += 1
                logger.info("  -> %d signal(s) generated", len(signals))

                strat_entry = _ensure_strategy_entry(ledger, strat_name)
                strat_entry["total_signals_generated"] = (
                    strat_entry.get("total_signals_generated", 0) + len(signals)
                )
                strat_entry["last_signal_at"] = now.isoformat()

                for sig in signals:
                    sig_dict = signal_to_dict(sig)
                    sig_dict["generated_at"] = now.isoformat()
                    results["signals"].append(sig_dict)
                    results["total_signals"] += 1

                    # Add to open picks (avoid duplicates)
                    pick = {
                        "symbol": sig_dict.get("symbol", "BTCUSDT"),
                        "direction": sig_dict.get("direction", "BUY"),
                        "entry_price": sig_dict.get("entry_price"),
                        "take_profit": sig_dict.get("take_profit"),
                        "stop_loss": sig_dict.get("stop_loss"),
                        "confidence": sig_dict.get("confidence"),
                        "reason": sig_dict.get("reason", ""),
                        "generated_at": now.isoformat(),
                    }

                    if not _deduplicate_pick(strat_entry["open_picks"], pick):
                        strat_entry["open_picks"].append(pick)
                        logger.info(
                            "  [NEW PICK] %s %s %s @ %.2f  TP=%.2f  SL=%.2f",
                            strat_name, pick["direction"], pick["symbol"],
                            pick["entry_price"], pick["take_profit"], pick["stop_loss"],
                        )
                    else:
                        logger.info(
                            "  [DUPLICATE] %s %s %s — already tracked",
                            strat_name, pick["direction"], pick["symbol"],
                        )
            else:
                logger.info("  -> No signals (threshold not met or data unavailable)")
                # Still ensure ledger entry exists for tracking
                _ensure_strategy_entry(ledger, strat_name)

        except Exception as e:
            results["strategies_failed"] += 1
            error_msg = f"{strat_name}: {type(e).__name__}: {e}"
            results["errors"].append(error_msg)
            logger.error("  FAILED: %s", error_msg)
            logger.debug(traceback.format_exc())
            # Ensure ledger entry exists even on failure
            _ensure_strategy_entry(ledger, strat_name)

    # Save ledger
    save_ledger(ledger)
    logger.info("Ledger saved: %s", LEDGER_PATH)

    # Inject into dashboard
    inject_into_dashboard(ledger)

    # Write latest signals output
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SIGNALS_OUT.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    logger.info("Signals output: %s", SIGNALS_OUT)

    # Summary
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("  Strategies run:         %d", results["strategies_run"])
    logger.info("  With signals:           %d", results["strategies_with_signals"])
    logger.info("  Failed:                 %d", results["strategies_failed"])
    logger.info("  Total new signals:      %d", results["total_signals"])
    logger.info("  Picks closed this run:  %d", closed_count)

    # Per-strategy ledger summary
    for name, data in ledger["strategies"].items():
        open_ct = len(data.get("open_picks", []))
        closed_ct = len(data.get("closed_trades", []))
        total_sigs = data.get("total_signals_generated", 0)
        wins = sum(1 for t in data.get("closed_trades", []) if t.get("pnl_pct", 0) > 0)
        wr = (wins / closed_ct * 100) if closed_ct > 0 else 0
        logger.info(
            "  %-40s  open=%d  closed=%d  WR=%.1f%%  total_sigs=%d",
            name, open_ct, closed_ct, wr, total_sigs,
        )

    logger.info("=" * 60)

    return results


def main():
    results = run_all_strategies()
    # Exit 0 even if some strategies failed (individual failures are non-fatal)
    if results["strategies_failed"] == results["strategies_run"]:
        logger.error("ALL strategies failed — exiting with error")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
