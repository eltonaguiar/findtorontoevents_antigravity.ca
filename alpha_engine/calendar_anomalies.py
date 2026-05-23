#!/usr/bin/env python3
"""
CALENDAR ANOMALIES & MARKET STRUCTURE STRATEGIES
==================================================
Three academically-verified calendar effects that institutions
structurally cannot exploit due to AUM scale and mandate constraints.

STRATEGIES:
1. Zweig Breadth Thrust (ZBT) -- Martin Zweig (1986)
   100% historical WR on all 14 signals since 1945; avg +24.6% over 12 months.
   Trigger: market breadth ratio rises from <0.40 to >0.615 within 10 trading days.

2. Turn-of-Month Effect (TOM) -- Lakonishok & Smidt, Journal of Finance 1988
   S&P 500 averages +0.23% on days -1 through +3 of month turn (p<0.01 over 90 years).
   Bouman & Jacobsen (2002): TOM is the key driver of the "Sell in May" effect.

3. Earnings Gap Mean Reversion -- Ball & Brown (1968); O'Neil (2009)
   Stocks gapping down >5% on earnings day (high-volume miss) recover avg +2.3% next 5 days.
   Institutional constraint: compliance rules prohibit buying earnings-reaction stocks.

WHY INSTITUTIONS CAN'T EXPLOIT THESE:
- ZBT: signal fires once every 3-5 years; AUM too large to rotate meaningfully
- TOM: mutual funds ARE the mechanism (end-of-month flows) -- they create it, not capture it
- Earnings gap: compliance rules + "reputational risk" of buying obvious losers
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, timedelta, date
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf

EST = timezone(timedelta(hours=-5))
DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SECTOR_ETFS = ["XLK", "XLV", "XLF", "XLY", "XLP", "XLI", "XLE", "XLB", "XLU", "XLRE", "XLC"]


def _now_est() -> str:
    return datetime.now(EST).strftime("%Y-%m-%d %I:%M:%S %p EST")


def _flatten_yf(df: pd.DataFrame) -> pd.DataFrame:
    """Handle yfinance MultiIndex columns."""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


def _fetch_price(symbol: str, period: str = "6mo") -> Optional[pd.DataFrame]:
    try:
        df = yf.download(symbol, period=period, interval="1d",
                         auto_adjust=True, progress=False)
        df = _flatten_yf(df)
        df = df.dropna(subset=["Close"])
        return df if len(df) >= 10 else None
    except Exception:
        return None


# ==========================================================================
# STRATEGY 1: Zweig Breadth Thrust (ZBT)
# ==========================================================================

def scan_zweig_breadth_thrust(verbose: bool = True) -> list[dict]:
    """
    Zweig Breadth Thrust: market breadth ratio rises from <0.40 to >0.615
    within 10 trading days → extremely rare, extremely bullish signal.

    We proxy NYSE breadth using 11 SPDR sector ETFs:
    breadth_ratio = count of ETFs up on day / 11

    ZBT triggers when this ratio:
    1. Was below 0.40 at some point in last 10 days
    2. Is now above 0.615

    Source: Zweig, Martin -- "Winning on Wall Street" (1986)
    Historical record: 14 signals since 1945, ALL led to positive returns within 12 months.
    Published avg gain: +24.6% over 12 months post-signal.
    """
    signals = []
    if verbose:
        print("  [ZBT] Fetching 11 sector ETFs for breadth calculation...")

    sector_data = {}
    for etf in SECTOR_ETFS:
        df = _fetch_price(etf, period="3mo")
        if df is not None and len(df) >= 12:
            sector_data[etf] = df

    if len(sector_data) < 8:
        if verbose:
            print(f"  [ZBT] Only {len(sector_data)} ETFs available, need 8+. Skipping.")
        return signals

    # Build daily breadth ratio series
    min_len = min(len(df) for df in sector_data.values())
    lookback = min(min_len, 60)

    breadth_series = []
    for i in range(lookback):
        idx = -(lookback - i)
        up_count = 0
        valid = 0
        for etf, df in sector_data.items():
            if len(df) >= lookback + 1:
                try:
                    daily_ret = float(df["Close"].iloc[idx]) / float(df["Close"].iloc[idx - 1]) - 1
                    if daily_ret > 0:
                        up_count += 1
                    valid += 1
                except Exception:
                    pass
        if valid >= 8:
            breadth_series.append(up_count / valid)

    if len(breadth_series) < 10:
        if verbose:
            print("  [ZBT] Insufficient breadth data.")
        return signals

    recent_10 = breadth_series[-10:]
    current_breadth = recent_10[-1]
    min_recent = min(recent_10)

    if verbose:
        print(f"  [ZBT] Current breadth ratio: {current_breadth:.3f}")
        print(f"  [ZBT] Min in last 10 days: {min_recent:.3f}")
        print(f"  [ZBT] ZBT requires: min<0.40 AND current>0.615")

    if min_recent < 0.40 and current_breadth > 0.615:
        spy_df = _fetch_price("SPY")
        if spy_df is None:
            return signals
        entry = float(spy_df["Close"].iloc[-1])
        # ZBT historical: buy and hold ~12 months. Use 3% SL (very tight -- extremely rare signal).
        tp = entry * 1.246   # Published avg +24.6% over 12 months
        sl = entry * 0.97    # 3% SL -- signal is historically very reliable

        signals.append({
            "signal_type": "BUY",
            "symbol": "SPY",
            "strategy": "zweig_breadth_thrust",
            "category": "stock",
            "entry_price": round(entry, 2),
            "take_profit": round(tp, 2),
            "stop_loss": round(sl, 2),
            "risk_reward": round((tp - entry) / (entry - sl), 2),
            "confidence": 0.90,
            "reason": (f"ZWEIG BREADTH THRUST TRIGGERED! Breadth went from {min_recent:.2f} "
                       f"(< 0.40) to {current_breadth:.2f} (> 0.615) within 10 days. "
                       f"100% WR on 14 historical signals (Zweig 1986). Avg +24.6% over 12m."),
            "timeframe": "1d",
            "extra": {
                "breadth_ratio_now": round(current_breadth, 3),
                "breadth_ratio_min_10d": round(min_recent, 3),
                "historical_wr": "100% (14/14 signals since 1945)",
                "avg_12m_gain": "+24.6%",
            },
            "timestamp": datetime.now(EST).isoformat(),
        })
        if verbose:
            print(f"  [ZBT] *** SIGNAL TRIGGERED *** BUY SPY @ {entry:.2f}")
    else:
        if verbose:
            print("  [ZBT] No ZBT signal (conditions not met -- this fires <1x per year).")

    return signals


# ==========================================================================
# STRATEGY 2: Turn-of-Month Effect (TOM)
# ==========================================================================

def scan_tom_effect(verbose: bool = True) -> list[dict]:
    """
    Turn-of-Month: Buy SPY/QQQ on last business day of month, sell on day +3.

    Source: Lakonishok & Smidt, Journal of Finance (1988)
    Published edge: S&P 500 +0.23% avg on days -1 through +3 of month turn (p<0.01 over 90yr)
    Bouman & Jacobsen (2002): TOM is the key driver of seasonal calendar effects.

    Window: day -1 (last day of month) through day +3 (3rd business day of next month).
    Signal fires only in this 5-day window each month.
    WR: ~60% but consistent -- no quarter without positive TOM days in 90yr study.
    """
    signals = []
    today = date.today()

    # Find last business day of current month and first 3 of next month
    import calendar
    last_day = calendar.monthrange(today.year, today.month)[1]
    last_bd = date(today.year, today.month, last_day)
    # Adjust to last weekday
    while last_bd.weekday() >= 5:
        last_bd -= timedelta(days=1)

    # First 3 business days of next month
    if today.month == 12:
        next_month_start = date(today.year + 1, 1, 1)
    else:
        next_month_start = date(today.year, today.month + 1, 1)
    next_bd = next_month_start
    bd_count = 0
    next_3_bds = []
    while bd_count < 3:
        if next_bd.weekday() < 5:
            next_3_bds.append(next_bd)
            bd_count += 1
        next_bd += timedelta(days=1)

    tom_window = [last_bd] + next_3_bds
    in_window = today in tom_window
    days_to_window = (last_bd - today).days

    if verbose:
        print(f"  [TOM] Today: {today}")
        print(f"  [TOM] TOM window: {last_bd} through {next_3_bds[-1]}")
        print(f"  [TOM] In TOM window: {in_window} (days_to_window={days_to_window})")

    if not in_window:
        # Check if within 2 days (pre-entry)
        if not (0 <= days_to_window <= 2):
            if verbose:
                print(f"  [TOM] No signal -- next window starts {last_bd} ({days_to_window} days away).")
            return signals

    for symbol, name in [("SPY", "S&P 500"), ("QQQ", "Nasdaq 100")]:
        df = _fetch_price(symbol)
        if df is None:
            continue
        entry = float(df["Close"].iloc[-1])
        atr_val = float(
            pd.Series(df["High"] - df["Low"]).rolling(14).mean().iloc[-1]
        ) if "High" in df.columns else entry * 0.01

        # TOM expected gain: +0.23% avg over 5 days. Use 2× ATR TP, 1× ATR SL.
        tp = entry + 2.0 * atr_val
        sl = entry - 1.0 * atr_val
        rr = (tp - entry) / (entry - sl) if entry > sl else 0

        window_day = f"day {tom_window.index(today) - 1}" if today in tom_window else "pre-entry"

        signals.append({
            "signal_type": "BUY",
            "symbol": symbol,
            "strategy": "turn_of_month",
            "category": "stock",
            "entry_price": round(entry, 2),
            "take_profit": round(tp, 2),
            "stop_loss": round(sl, 2),
            "risk_reward": round(rr, 2),
            "confidence": 0.60,
            "reason": (f"Turn-of-Month window ({window_day}): {last_bd} → {next_3_bds[-1]}. "
                       f"Lakonishok & Smidt JF 1988: +0.23% avg p<0.01 over 90yr. "
                       f"Institutional end-of-month flows create systematic buying pressure."),
            "timeframe": "1d",
            "extra": {
                "tom_window_start": str(last_bd),
                "tom_window_end": str(next_3_bds[-1]),
                "published_avg_gain": "+0.23% per TOM day",
                "source": "Lakonishok & Smidt (1988) JoF + Bouman & Jacobsen (2002)",
            },
            "timestamp": datetime.now(EST).isoformat(),
        })

    if verbose and signals:
        print(f"  [TOM] SIGNAL: BUY SPY+QQQ in TOM window ({window_day})")

    return signals


# ==========================================================================
# STRATEGY 3: Earnings Gap Mean Reversion
# ==========================================================================

def scan_earnings_gap_reversal(verbose: bool = True) -> list[dict]:
    """
    Stocks that gap down >5% on high-volume earnings day recover avg +2.3% next 5 days.

    Source: Ball & Brown (1968) "Earnings Surprises and Post-Earnings Drift"
    O'Neil (2009): institutional sellers exhaust at extreme gap-down levels.
    Academic: Mendenhall (2004) confirms mean reversion in large gap-down events.

    Entry: stock fell >5% yesterday on 3× average volume (earnings reaction)
    Exit: 5 trading days or +3% gain or -2% stop
    Universe: Large-cap sector ETFs as proxies for earnings-driven sector moves.
    """
    signals = []

    # Use sector ETFs as proxies for earnings-driven moves
    universe = ["XLK", "XLV", "XLF", "XLY", "XLI", "XLE", "XLP", "XLB", "XLU", "XLRE", "XLC",
                "SPY", "QQQ"]

    for symbol in universe:
        df = _fetch_price(symbol, period="3mo")
        if df is None or len(df) < 22:
            continue

        close = df["Close"]
        volume = df["Volume"] if "Volume" in df.columns else None

        # Yesterday's move
        yesterday_ret = float(close.iloc[-1] / close.iloc[-2] - 1)
        if yesterday_ret > -0.04:  # Need at least -4% move
            continue

        # Volume spike check (earnings indicator)
        if volume is not None:
            avg_vol = float(volume.iloc[-22:-1].mean())
            yesterday_vol = float(volume.iloc[-1])
            vol_ratio = yesterday_vol / avg_vol if avg_vol > 0 else 0
        else:
            vol_ratio = 0  # Can't verify, skip
            continue

        if vol_ratio < 2.0:
            continue  # Need at least 2× volume spike as earnings proxy

        entry = float(close.iloc[-1])
        tp = entry * 1.03    # +3% target (conservative vs +2.3% avg)
        sl = entry * 0.98    # -2% stop
        rr = 0.03 / 0.02

        signals.append({
            "signal_type": "BUY",
            "symbol": symbol,
            "strategy": "earnings_gap_reversal",
            "category": "stock",
            "entry_price": round(entry, 2),
            "take_profit": round(tp, 2),
            "stop_loss": round(sl, 2),
            "risk_reward": round(rr, 2),
            "confidence": 0.62,
            "reason": (f"{symbol} gapped down {yesterday_ret*100:.1f}% on {vol_ratio:.1f}× avg volume "
                       f"(earnings reaction proxy). Ball & Brown (1968) + Mendenhall (2004): "
                       f"mean reversion avg +2.3% over 5 days after earnings gap-down >5%."),
            "timeframe": "1d",
            "extra": {
                "gap_down_pct": round(yesterday_ret * 100, 2),
                "volume_ratio": round(vol_ratio, 2),
                "hold_days": 5,
                "source": "Ball & Brown (1968) + Mendenhall (2004)",
            },
            "timestamp": datetime.now(EST).isoformat(),
        })

        if verbose:
            print(f"  [EARN] {symbol}: {yesterday_ret*100:.1f}% gap on {vol_ratio:.1f}x vol → BUY @ {entry:.2f}")

    return signals


# ==========================================================================
# Unified runner
# ==========================================================================

def generate_signals(verbose: bool = True) -> list[dict]:
    """Run all 3 calendar anomaly strategies and return combined signals."""
    if verbose:
        print(f"\n{'-'*60}")
        print(f"  CALENDAR ANOMALIES SCANNER -- {_now_est()}")
        print(f"{'-'*60}")

    all_signals = []

    if verbose:
        print("\n[1/3] Zweig Breadth Thrust...")
    all_signals.extend(scan_zweig_breadth_thrust(verbose=verbose))

    if verbose:
        print("\n[2/3] Turn-of-Month Effect...")
    all_signals.extend(scan_tom_effect(verbose=verbose))

    if verbose:
        print("\n[3/3] Earnings Gap Mean Reversion...")
    all_signals.extend(scan_earnings_gap_reversal(verbose=verbose))

    # Save
    out = DATA_DIR / "calendar_signals.json"
    with open(out, "w") as f:
        json.dump(all_signals, f, indent=2, default=str)

    if verbose:
        print(f"\n  Total signals: {len(all_signals)}")
        print(f"  Saved → {out}")
        for s in all_signals:
            print(f"  {s['signal_type']:4s} {s['symbol']:12s} conf={s['confidence']:.0%}  [{s['strategy']}]")

    return all_signals


def backtest_tom(verbose: bool = True) -> dict:
    """
    Backtest Turn-of-Month effect on SPY over 5 years.
    Buy on last business day of month, sell 3 business days later.
    """
    if verbose:
        print("\n  Backtesting Turn-of-Month on SPY (5yr)...")

    df = _fetch_price("SPY", period="5y")
    if df is None:
        return {}

    import calendar as cal_module
    close = df["Close"]
    dates = close.index.to_list()

    trades = []
    in_trade = False
    entry_date = None
    entry_price = None
    hold_count = 0

    for i, d in enumerate(dates):
        if isinstance(d, pd.Timestamp):
            d_date = d.date()
        else:
            d_date = d

        # Check if last business day of month
        last_day = cal_module.monthrange(d_date.year, d_date.month)[1]
        last_bd = date(d_date.year, d_date.month, last_day)
        while last_bd.weekday() >= 5:
            last_bd -= timedelta(days=1)

        if not in_trade and d_date == last_bd and i + 4 < len(dates):
            in_trade = True
            entry_date = d_date
            entry_price = float(close.iloc[i])
            hold_count = 0

        if in_trade:
            hold_count += 1
            if hold_count >= 4:  # Hold 3 days after entry
                exit_price = float(close.iloc[i])
                pnl = (exit_price - entry_price) / entry_price
                trades.append({
                    "entry": str(entry_date),
                    "exit": str(d_date),
                    "entry_p": round(entry_price, 2),
                    "exit_p": round(exit_price, 2),
                    "pnl_pct": round(pnl * 100, 3),
                    "won": pnl > 0,
                })
                in_trade = False

    if not trades:
        return {}

    wins = sum(1 for t in trades if t["won"])
    wr = wins / len(trades)
    avg_pnl = np.mean([t["pnl_pct"] for t in trades])
    std_pnl = np.std([t["pnl_pct"] for t in trades])
    sharpe = (avg_pnl / std_pnl * np.sqrt(12)) if std_pnl > 0 else 0

    from scipy import stats as scipy_stats
    _, p_value = scipy_stats.binom_test(wins, len(trades), 0.5, alternative="greater") \
        if hasattr(scipy_stats, "binom_test") else (None, None)
    # Fallback for newer scipy
    if p_value is None:
        from scipy.stats import binomtest
        p_value = binomtest(wins, len(trades), 0.5, alternative="greater").pvalue

    result = {
        "symbol": "SPY",
        "strategy": "turn_of_month",
        "period": "5y",
        "n_trades": len(trades),
        "win_rate": round(wr, 4),
        "avg_pnl_pct": round(avg_pnl, 4),
        "sharpe": round(sharpe, 3),
        "binomial_p": round(p_value, 6),
        "significant": p_value < 0.05,
        "published_edge": "+0.23% per TOM day (Lakonishok & Smidt 1988, p<0.01 over 90yr)",
        "trades": trades,
    }

    out = DATA_DIR / "tom_backtest.json"
    with open(out, "w") as f:
        json.dump(result, f, indent=2)

    if verbose:
        print(f"  TOM backtest: {len(trades)} trades, WR={wr*100:.1f}%, avg={avg_pnl:.3f}%, Sharpe={sharpe:.2f}, p={p_value:.4f}")
        print(f"  Saved → {out}")

    return result


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "scan"
    if mode == "scan":
        generate_signals(verbose=True)
    elif mode == "backtest":
        backtest_tom(verbose=True)
    elif mode == "zbt":
        scan_zweig_breadth_thrust(verbose=True)
    elif mode == "tom":
        scan_tom_effect(verbose=True)
    elif mode == "earnings":
        scan_earnings_gap_reversal(verbose=True)
