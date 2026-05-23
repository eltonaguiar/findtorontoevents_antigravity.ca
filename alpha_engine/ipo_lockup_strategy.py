"""
IPO Lock-Up Expiry Strategy — Backtester + Signal Generator.

STATUS — OPT-IN RESEARCH SIDECAR (added 2026-05-17)
  NOT wired into production. Companion to `ipo_data_pipeline.py`. See that
  module's `## Wiring Plan`: signals reach `passes_active_gate` only after a
  >=2yr backtest clears the §23 universal 5-gate (DSR>=0.95, PBO<0.05, WF
  decay>=0, n>=100, 30-day rolling-clean). WR estimates below are LITERATURE,
  not verified on this system.

EDGE:
  When insiders' lock-up expires (typically 180 days post-IPO), they sell.
  This creates predictable downward pressure. Short 5 days before expiry,
  cover 10 days after.

DOCUMENTED:
  - Field & Hanka (2001): -1.5% abnormal return at lock-up expiry
  - Brav & Gompers (2003): effect persists, stronger for VC-backed
  - Bradley et al. (2001): -30% cumulative return from IPO to 1yr post-lockup

RISK:
  - Borrow availability required
  - Short squeeze risk (check short interest >20% = skip)
  - Wider stops needed (15%) due to volatility
  - Max 2% position per trade

USAGE:
  python3 -m alpha_engine.ipo_lockup_strategy --backtest
  python3 -m alpha_engine.ipo_lockup_strategy --signals
  python3 -m alpha_engine.ipo_lockup_strategy --run
"""

from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

LOG = logging.getLogger(__name__)
DATA_DIR = Path(__file__).parent / "data"

# Strategy parameters
ENTRY_DAYS_BEFORE_LOCKUP = 5   # Short N days before lock-up expiry
EXIT_DAYS_AFTER_LOCKUP = 10    # Cover N days after lock-up expiry
STOP_LOSS_PCT = 0.15           # 15% stop-loss
TAKE_PROFIT_PCT = 0.10         # 10% take-profit
MAX_SHORT_INTEREST_PCT = 20.0  # Skip if short interest > 20%
SLIPPAGE_PCT = 0.02            # 2% slippage assumption for small caps
COMMISSION_PCT = 0.001         # 0.1% commission

# Minimum filters
MIN_MARKET_CAP = 100_000_000   # $100M minimum
MIN_AVG_VOLUME = 500_000       # 500K shares/day minimum
MIN_PRICE = 5.0                # $5 minimum (avoid true penny stocks)


# ipo_data_pipeline helpers — dual import so the module works both as
# `python -m alpha_engine.ipo_lockup_strategy` and inside the package.
try:
    from alpha_engine.ipo_data_pipeline import (
        load_ipo_calendar,
        generate_lockup_signals,
        fetch_price_data,
        get_short_interest,
        run_pipeline,
    )
except ImportError:  # pragma: no cover - fallback for direct execution
    from ipo_data_pipeline import (  # type: ignore
        load_ipo_calendar,
        generate_lockup_signals,
        fetch_price_data,
        get_short_interest,
        run_pipeline,
    )


def load_price_history(symbol: str) -> Optional[list[dict]]:
    """Load cached price history for a symbol."""
    path = DATA_DIR / "price_cache" / f"{symbol.replace('=', '_')}.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def get_price_on_date(prices: list[dict], target_date: str) -> Optional[float]:
    """Get closing price on or nearest to target date."""
    if not prices:
        return None

    best = None
    best_diff = float('inf')
    for p in prices:
        diff = abs((datetime.strptime(p["date"], "%Y-%m-%d") -
                     datetime.strptime(target_date, "%Y-%m-%d")).days)
        if diff < best_diff:
            best_diff = diff
            best = p

    if best and best_diff <= 5:  # Within 5 trading days
        return best.get("close")
    return None


# =========================================================================
# Backtester
# =========================================================================

def backtest_lockup_strategy(
    ipos: list[dict],
    price_data: dict[str, list[dict]],
    start_date: str = "2020-01-01",
    end_date: str = None,
) -> dict:
    """
    Backtest the IPO lock-up expiry short strategy.

    For each IPO: find lock-up expiry, short ENTRY_DAYS_BEFORE_LOCKUP days
    before, cover EXIT_DAYS_AFTER_LOCKUP days after (or on stop-loss / TP).
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    trades = []
    skipped = {"no_price": 0, "no_lockup": 0, "too_early": 0, "filters": 0}

    for ipo in ipos:
        symbol = ipo.get("symbol", "")
        lockup_str = ipo.get("lockup_expiry")
        ipo_date = ipo.get("ipo_date", "")

        if not lockup_str or not symbol:
            skipped["no_lockup"] += 1
            continue

        try:
            lockup_date = datetime.strptime(lockup_str, "%Y-%m-%d")
        except ValueError:
            skipped["no_lockup"] += 1
            continue

        entry_date = lockup_date - timedelta(days=ENTRY_DAYS_BEFORE_LOCKUP)
        entry_str = entry_date.strftime("%Y-%m-%d")

        if entry_str < start_date or entry_str > end_date:
            skipped["too_early"] += 1
            continue

        prices = price_data.get(symbol)
        if not prices:
            skipped["no_price"] += 1
            continue

        entry_price = get_price_on_date(prices, entry_str)
        if not entry_price or entry_price < MIN_PRICE:
            skipped["filters"] += 1
            continue

        exit_date = lockup_date + timedelta(days=EXIT_DAYS_AFTER_LOCKUP)
        exit_str = exit_date.strftime("%Y-%m-%d")

        trade_open = True
        actual_exit_date = exit_str
        actual_exit_price = None

        for p in prices:
            p_date = p["date"]
            if p_date < entry_str or p_date > exit_str:
                continue

            # For a SHORT: stop-loss if price rises above entry * (1 + stop)
            if p.get("high", 0) >= entry_price * (1 + STOP_LOSS_PCT):
                actual_exit_price = entry_price * (1 + STOP_LOSS_PCT)
                actual_exit_date = p_date
                trade_open = False
                break

            # Take-profit if price falls below entry * (1 - tp)
            if p.get("low", 999) <= entry_price * (1 - TAKE_PROFIT_PCT):
                actual_exit_price = entry_price * (1 - TAKE_PROFIT_PCT)
                actual_exit_date = p_date
                trade_open = False
                break

        if trade_open:
            actual_exit_price = get_price_on_date(prices, exit_str) or entry_price

        # Calculate PnL (SHORT position)
        pnl_gross = (entry_price - actual_exit_price) / entry_price
        pnl_net = pnl_gross - SLIPPAGE_PCT * 2 - COMMISSION_PCT * 2

        trades.append({
            "symbol": symbol,
            "company_name": ipo.get("company_name", ""),
            "ipo_date": ipo_date,
            "lockup_expiry": lockup_str,
            "entry_date": entry_str,
            "exit_date": actual_exit_date,
            "entry_price": round(entry_price, 2),
            "exit_price": round(actual_exit_price, 2),
            "pnl_pct": round(pnl_net * 100, 4),
            "pnl_gross_pct": round(pnl_gross * 100, 4),
            "outcome": "WIN" if pnl_net > 0 else "LOSS",
            "exit_reason": (
                "STOP" if not trade_open and actual_exit_price == entry_price * (1 + STOP_LOSS_PCT)
                else "TP" if not trade_open else "EXPIRY"
            ),
        })

    if not trades:
        return {"error": "No trades", "skipped": skipped}

    wins = [t for t in trades if t["outcome"] == "WIN"]
    losses = [t for t in trades if t["outcome"] == "LOSS"]
    n = len(trades)
    wr = len(wins) / n * 100
    avg_win = sum(t["pnl_pct"] for t in wins) / len(wins) if wins else 0
    avg_loss = abs(sum(t["pnl_pct"] for t in losses) / len(losses)) if losses else 0
    pf = (sum(t["pnl_pct"] for t in wins) /
          abs(sum(t["pnl_pct"] for t in losses))) if losses and sum(t["pnl_pct"] for t in losses) != 0 else 999.0
    total_pnl = sum(t["pnl_pct"] for t in trades)

    by_year = {}
    for t in trades:
        year = t["entry_date"][:4]
        by_year.setdefault(year, []).append(t)

    yearly_stats = {}
    for year, year_trades in sorted(by_year.items()):
        y_wins = [t for t in year_trades if t["outcome"] == "WIN"]
        y_n = len(year_trades)
        y_wr = len(y_wins) / y_n * 100 if y_n > 0 else 0
        y_pnl = sum(t["pnl_pct"] for t in year_trades)
        yearly_stats[year] = {"n": y_n, "wr": round(y_wr, 1), "pnl": round(y_pnl, 2)}

    return {
        "strategy": "ipo_lockup_expiry",
        "total_trades": n,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(wr, 1),
        "profit_factor": round(pf, 2),
        "total_pnl_pct": round(total_pnl, 2),
        "avg_win_pct": round(avg_win, 2),
        "avg_loss_pct": round(avg_loss, 2),
        "avg_pnl_pct": round(total_pnl / n, 4),
        "yearly": yearly_stats,
        "skipped": skipped,
        "trades": trades,
        "params": {
            "entry_days_before": ENTRY_DAYS_BEFORE_LOCKUP,
            "exit_days_after": EXIT_DAYS_AFTER_LOCKUP,
            "stop_loss": STOP_LOSS_PCT,
            "take_profit": TAKE_PROFIT_PCT,
            "slippage": SLIPPAGE_PCT,
            "min_price": MIN_PRICE,
            "min_market_cap": MIN_MARKET_CAP,
        },
    }


# =========================================================================
# Signal Generator (live)
# =========================================================================

def generate_live_signals() -> list[dict]:
    """
    Generate live lock-up expiry signals for today.

    Returns list of signal dicts ready for quality_gates. NOTE: research-only
    until the §23 5-gate clears — `passes_active_gate` must not admit
    `source_system='ipo_pipeline'` before then.
    """
    ipos = load_ipo_calendar()
    if not ipos:
        LOG.warning("No IPO calendar data. Run ipo_data_pipeline.py first.")
        return []

    signals = generate_lockup_signals(ipos)

    enriched = []
    for sig in signals:
        symbol = sig["symbol"]

        si = get_short_interest(symbol)
        if si is not None and si > (MAX_SHORT_INTEREST_PCT / 100.0):
            LOG.info("Skipping %s: short interest %.1f%% > %.1f%%",
                     symbol, si * 100, MAX_SHORT_INTEREST_PCT)
            continue

        prices = fetch_price_data(symbol, "1mo")
        if prices:
            current_price = prices[-1].get("close")
            if current_price and current_price < MIN_PRICE:
                LOG.info("Skipping %s: price $%.2f < $%.2f", symbol, current_price, MIN_PRICE)
                continue
            if current_price:
                sig["entry_price"] = current_price
                sig["take_profit"] = round(current_price * (1 - TAKE_PROFIT_PCT), 2)
                sig["stop_loss"] = round(current_price * (1 + STOP_LOSS_PCT), 2)

        sig["short_interest_pct"] = si
        enriched.append(sig)

    return enriched


# =========================================================================
# CLI
# =========================================================================

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    if "--backtest" in sys.argv:
        ipos = load_ipo_calendar()
        if not ipos:
            print("No IPO data. Run: python3 -m alpha_engine.ipo_data_pipeline first")
            sys.exit(1)

        price_data = {}
        price_dir = DATA_DIR / "price_cache"
        if price_dir.exists():
            for f in price_dir.glob("*.json"):
                symbol = f.stem.replace("_", "=")
                with open(f) as fh:
                    price_data[symbol] = json.load(fh)

        if not price_data:
            print("No price data cached. Fetch prices first.")
            sys.exit(1)

        result = backtest_lockup_strategy(ipos, price_data)
        print(json.dumps({k: v for k, v in result.items() if k != "trades"}, indent=2))

        with open(DATA_DIR / "ipo_backtest_results.json", "w") as f:
            json.dump(result, f, indent=2)
        print(f"\nResults saved to: {DATA_DIR / 'ipo_backtest_results.json'}")

    elif "--signals" in sys.argv:
        signals = generate_live_signals()
        print(json.dumps(signals, indent=2))

    elif "--run" in sys.argv:
        run_pipeline("full")
        signals = generate_live_signals()
        print(f"\n{len(signals)} live signals:")
        print(json.dumps(signals, indent=2))

    else:
        print("Usage:")
        print("  python3 -m alpha_engine.ipo_lockup_strategy --backtest")
        print("  python3 -m alpha_engine.ipo_lockup_strategy --signals")
        print("  python3 -m alpha_engine.ipo_lockup_strategy --run")
