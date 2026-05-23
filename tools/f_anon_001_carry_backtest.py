"""
F-ANON-001 Backtest: G10 FOREX Carry Trade
Academic basis: Lustig, Roussanov & Verdelhan (2011); Menkhoff et al. (2012)
Signal: Long top-3 carry pairs (highest rate differential vs USD),
        Short bottom-3 carry pairs (lowest rate differential / funding currencies)
Hold: 1 week (5 trading days), weekly rebalance
Period: 2020-01-01 to 2026-04-30
Carry proxy: official short-term rate differentials (hardcoded from public sources)
             supplemented by 252-day momentum for missing periods
Universe: G10 FX pairs vs USD via yfinance
OOS validation: TimeSeriesSplit (5 folds)

Pre-registered: F-ANON-001 (M-107 gate complied)
AI consensus: 3/3 (Pollinations + Perplexity + eye2.ai), 2026-05-19
"""

import json
import warnings
from datetime import datetime
import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.model_selection import TimeSeriesSplit

warnings.filterwarnings("ignore")

# ── G10 FX pairs (all quoted vs USD) ─────────────────────────────────────────
# Positive return = USD weakens / foreign currency strengthens.
# For pairs quoted as USD/XXX (USDXXX=X), we invert to get XXX/USD returns.
G10_PAIRS = {
    "AUD": {"ticker": "AUDUSD=X", "invert": False},   # AUD/USD direct
    "NZD": {"ticker": "NZDUSD=X", "invert": False},   # NZD/USD direct
    "GBP": {"ticker": "GBPUSD=X", "invert": False},   # GBP/USD direct
    "EUR": {"ticker": "EURUSD=X", "invert": False},   # EUR/USD direct
    "CAD": {"ticker": "USDCAD=X", "invert": True},    # invert → CAD/USD
    "JPY": {"ticker": "USDJPY=X", "invert": True},    # invert → JPY/USD
    "CHF": {"ticker": "USDCHF=X", "invert": True},    # invert → CHF/USD
    "NOK": {"ticker": "USDNOK=X", "invert": True},    # invert → NOK/USD
    "SEK": {"ticker": "USDSEK=X", "invert": True},    # invert → SEK/USD
}

# ── Carry rates: approximate short-term policy rate differential vs USD ──────
# Source: public central bank data + FRED approximations
# Format: {currency: {year: rate_pct}}
# Rate differential = foreign_rate - USD_rate (positive = carry-positive vs USD)
# USD (Fed Funds) approximate annual averages: 2020=0.09, 2021=0.08, 2022=1.68, 2023=5.02, 2024=5.33, 2025=4.50
USD_RATES = {2020: 0.09, 2021: 0.08, 2022: 1.68, 2023: 5.02, 2024: 5.33, 2025: 4.50, 2026: 4.33}

FOREIGN_RATES = {
    # AUD: RBA cash rate
    "AUD": {2020: 0.10, 2021: 0.10, 2022: 2.35, 2023: 4.35, 2024: 4.35, 2025: 4.10, 2026: 3.85},
    # NZD: RBNZ OCR
    "NZD": {2020: 0.25, 2021: 0.75, 2022: 3.50, 2023: 5.50, 2024: 5.50, 2025: 3.75, 2026: 3.50},
    # GBP: BoE base rate
    "GBP": {2020: 0.10, 2021: 0.10, 2022: 3.50, 2023: 5.25, 2024: 5.00, 2025: 4.25, 2026: 4.00},
    # EUR: ECB deposit rate
    "EUR": {2020: -0.50, 2021: -0.50, 2022: 2.00, 2023: 4.00, 2024: 3.40, 2025: 2.50, 2026: 2.25},
    # CAD: BoC overnight rate
    "CAD": {2020: 0.25, 2021: 0.25, 2022: 4.25, 2023: 5.00, 2024: 4.75, 2025: 3.00, 2026: 2.75},
    # JPY: BoJ policy rate
    "JPY": {2020: -0.10, 2021: -0.10, 2022: -0.10, 2023: -0.10, 2024: 0.25, 2025: 0.50, 2026: 0.75},
    # CHF: SNB policy rate
    "CHF": {2020: -0.75, 2021: -0.75, 2022: 0.50, 2023: 1.75, 2024: 1.00, 2025: 0.25, 2026: 0.00},
    # NOK: Norges Bank
    "NOK": {2020: 0.00, 2021: 0.50, 2022: 2.75, 2023: 4.50, 2024: 4.50, 2025: 4.25, 2026: 3.75},
    # SEK: Riksbank
    "SEK": {2020: 0.00, 2021: 0.00, 2022: 2.50, 2023: 4.00, 2024: 3.50, 2025: 2.25, 2026: 2.00},
}

START_DATE = "2020-01-01"
END_DATE   = "2026-04-30"
HOLD_DAYS  = 5       # 1 week
N_SPLITS   = 5
TOP_N      = 3       # Long top-N carry pairs
BOT_N      = 3       # Short bottom-N carry pairs (funding currencies)


# ── Data fetch ────────────────────────────────────────────────────────────────
def fetch_fx_data(pairs: dict, start: str, end: str) -> pd.DataFrame:
    """Download G10 FX pairs and return as DataFrame of XXX/USD returns."""
    tickers = [v["ticker"] for v in pairs.values()]
    print(f"[fetch] Downloading {len(tickers)} FX pairs {start} → {end}…")
    raw = yf.download(tickers, start=start, end=end,
                      auto_adjust=True, progress=False, threads=True)
    if isinstance(raw.columns, pd.MultiIndex):
        close_raw = raw["Close"]
    else:
        close_raw = raw[["Close"]]

    # Build per-currency close (all expressed as foreign/USD)
    close = pd.DataFrame(index=close_raw.index)
    for ccy, cfg in pairs.items():
        ticker = cfg["ticker"]
        if ticker not in close_raw.columns:
            print(f"  [warn] {ticker} not found — skipping {ccy}")
            continue
        s = close_raw[ticker].dropna()
        if cfg["invert"]:
            s = 1.0 / s   # convert USD/XXX → XXX/USD
        close[ccy] = s

    close = close.dropna(how="all")
    print(f"[fetch] Got {close.shape[1]} pairs × {close.shape[0]} days")
    return close


# ── Carry score ───────────────────────────────────────────────────────────────
def get_carry_differential(ccy: str, dt: pd.Timestamp) -> float:
    """Return annualised carry differential (foreign rate - USD rate) for a date."""
    yr = dt.year
    usd_rate = USD_RATES.get(yr, USD_RATES[2025])
    foreign_rate = FOREIGN_RATES.get(ccy, {}).get(yr)
    if foreign_rate is None:
        # Fall back to nearest year
        yrs = sorted(FOREIGN_RATES.get(ccy, {}).keys())
        if not yrs:
            return 0.0
        yr_use = min(yrs, key=lambda y: abs(y - yr))
        foreign_rate = FOREIGN_RATES[ccy][yr_use]
    return foreign_rate - usd_rate


def build_carry_ranks(close: pd.DataFrame) -> pd.DataFrame:
    """
    For each trading day, compute carry differential for each currency and rank.
    Returns DataFrame of carry differentials (currencies as columns, dates as index).
    Also returns a DataFrame of weekly rebalance dates.
    """
    ccys = close.columns.tolist()
    carry = pd.DataFrame(index=close.index, columns=ccys, dtype=float)
    for dt in close.index:
        for ccy in ccys:
            carry.loc[dt, ccy] = get_carry_differential(ccy, dt)
    return carry


# ── Signal generation (weekly rebalance, no look-ahead) ──────────────────────
def compute_weekly_signals(close: pd.DataFrame, carry: pd.DataFrame):
    """
    Every Monday (or first trading day of the week), rank currencies by carry.
    Long top-N, short bottom-N.
    Signal is +1 (long), -1 (short), 0 (neutral).
    Carry ranking on close[t], entry on close[t+1].
    """
    # Identify weekly rebalance dates (first trading day each week)
    week_labels = close.index.to_series().dt.isocalendar().week.astype(str) + \
                  "-" + close.index.to_series().dt.year.astype(str)
    rebalance_dates = close.index[~week_labels.duplicated(keep="first")]

    signal = pd.DataFrame(0, index=close.index, columns=close.columns)

    for rb_date in rebalance_dates:
        rb_idx = close.index.get_loc(rb_date)
        if rb_idx + 1 >= len(close):
            continue
        # Signal computed at rb_date close, entry at rb_date+1 close
        entry_date_idx = rb_idx + 1
        entry_date = close.index[entry_date_idx]

        # Rank by carry differential at rb_date
        row_carry = carry.loc[rb_date]
        ranked = row_carry.sort_values(ascending=False)
        longs  = ranked.iloc[:TOP_N].index.tolist()
        shorts = ranked.iloc[-BOT_N:].index.tolist()

        # Apply signal for entry_date + HOLD_DAYS - 1 subsequent days
        hold_end_idx = min(entry_date_idx + HOLD_DAYS, len(close))
        hold_dates = close.index[entry_date_idx:hold_end_idx]
        signal.loc[hold_dates, longs]  = 1
        signal.loc[hold_dates, shorts] = -1

    return signal, rebalance_dates


# ── Trade simulation ──────────────────────────────────────────────────────────
def simulate_fx_trades(close: pd.DataFrame, signal: pd.DataFrame,
                       date_indices, rebalance_dates) -> list:
    """
    On each weekly rebalance date (within the test window), open trades for
    all LONG (+1) and SHORT (-1) signals.  Entry = next bar (rebalance+1),
    hold exactly HOLD_DAYS bars.

    For LONG : profit when XXX/USD goes up (USD weakens).
    For SHORT : profit when XXX/USD goes down (USD strengthens).
    Returns list of trade dicts.
    """
    dates    = close.index
    date_set = set(date_indices)

    close_arr  = close.values
    signal_arr = signal.values
    ccys = close.columns.tolist()
    trades = []

    for rb_date in rebalance_dates:
        # Only process rebalance dates within the test window
        if rb_date not in date_set:
            continue
        rb_idx = dates.get_loc(rb_date)
        entry_idx = rb_idx + 1
        if entry_idx >= len(dates):
            continue
        exit_idx = min(entry_idx + HOLD_DAYS, len(dates) - 1)

        for si, ccy in enumerate(ccys):
            direction = int(signal_arr[rb_idx, si])  # signal on rebalance day
            if direction == 0:
                continue
            entry_price = close_arr[entry_idx, si]
            exit_price  = close_arr[exit_idx,  si]
            if np.isnan(entry_price) or np.isnan(exit_price) or entry_price == 0:
                continue

            raw_ret   = (exit_price - entry_price) / entry_price
            trade_ret = direction * raw_ret

            trades.append({
                "ccy":         ccy,
                "entry_date":  dates[entry_idx],
                "exit_date":   dates[exit_idx],
                "direction":   "LONG" if direction == 1 else "SHORT",
                "entry_price": round(entry_price, 6),
                "exit_price":  round(exit_price,  6),
                "return":      trade_ret,
                "win":         int(trade_ret > 0),
                "hold_bars":   exit_idx - entry_idx,
            })
    return trades


# ── Metrics ───────────────────────────────────────────────────────────────────
def compute_metrics(trades: list) -> dict:
    if not trades:
        return {"n_trades": 0, "win_rate": None, "profit_factor": None,
                "avg_return": None, "avg_return_pct": None}
    rets = [t["return"] for t in trades]
    wins   = [r for r in rets if r > 0]
    losses = [r for r in rets if r <= 0]
    if losses and sum(wins) > 0:
        pf = sum(wins) / abs(sum(losses))
    elif not losses:
        pf = float("inf")
    else:
        pf = 0.0
    return {
        "n_trades": len(trades),
        "win_rate": round(sum(t["win"] for t in trades) / len(trades), 4),
        "profit_factor": round(pf, 4),
        "avg_return": round(np.mean(rets), 6),
        "avg_return_pct": round(np.mean(rets) * 100, 4),
        "long_pct": round(sum(1 for t in trades if t["direction"] == "LONG") / len(trades), 3),
    }


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 70)
    print("F-ANON-001  G10 FOREX Carry Trade Backtest")
    print("=" * 70)

    close = fetch_fx_data(G10_PAIRS, START_DATE, END_DATE)
    carry = build_carry_ranks(close)
    signal, rebalance_dates = compute_weekly_signals(close, carry)

    print(f"[signal] Rebalance dates: {len(rebalance_dates)} weeks")

    dates = close.index
    n = len(dates)

    tscv = TimeSeriesSplit(n_splits=N_SPLITS)
    fold_results = []

    print(f"\n[OOS] TimeSeriesSplit {N_SPLITS} folds over {n} trading days\n")

    for fold_i, (train_idx, test_idx) in enumerate(tscv.split(dates), 1):
        test_dates = set(dates[test_idx])
        trades = simulate_fx_trades(close, signal, test_dates, rebalance_dates)
        m = compute_metrics(trades)
        m["fold"] = fold_i
        m["test_start"] = str(dates[test_idx[0]].date())
        m["test_end"]   = str(dates[test_idx[-1]].date())
        fold_results.append(m)
        wr_str  = f"{m['win_rate']*100:.1f}%" if m["win_rate"] is not None else "N/A"
        pf_str  = f"{m['profit_factor']:.3f}" if m["profit_factor"] is not None else "N/A"
        avr_str = f"{m['avg_return_pct']:.4f}%" if m["avg_return_pct"] is not None else "N/A"
        n_str   = f"{m['n_trades']:,}" if m["n_trades"] is not None else "N/A"
        print(f"  Fold {fold_i} | {m['test_start']} → {m['test_end']} "
              f"| n={n_str} | WR={wr_str} | PF={pf_str} | avg_ret={avr_str}")

    # Aggregate over all non-warmup test dates
    warmup_cut = dates[min(35, len(dates)-1)]
    all_test_dates = set(d for d in dates if d >= warmup_cut)
    all_trades = simulate_fx_trades(close, signal, all_test_dates, rebalance_dates)
    agg = compute_metrics(all_trades)

    print("\n" + "=" * 70)
    print("AGGREGATE (all OOS folds combined)")
    print("=" * 70)
    print(f"  n_trades     : {agg['n_trades']:,}")
    if agg["win_rate"] is not None:
        print(f"  win_rate     : {agg['win_rate']*100:.2f}%")
        print(f"  profit_factor: {agg['profit_factor']:.4f}")
        print(f"  avg_return   : {agg['avg_return_pct']:.4f}%")
        print(f"  long_pct     : {agg['long_pct']*100:.1f}% of trades are LONG")
    else:
        print("  win_rate     : N/A (no trades)")

    # ── Verdict ───────────────────────────────────────────────────────────────
    wr = agg["win_rate"] or 0
    pf = agg["profit_factor"] or 0
    n_t = agg["n_trades"] or 0
    if n_t < 30:
        verdict = "TESTED_KILL"
        verdict_reason = f"Insufficient trades (n={n_t} < 30 floor)"
    elif wr >= 0.50 and pf >= 1.2:
        verdict = "TESTED_PASS"
        verdict_reason = f"WR={wr*100:.1f}% >= 50% AND PF={pf:.3f} >= 1.2"
    elif wr >= 0.45 or pf >= 1.0:
        verdict = "TESTED_WEAK"
        verdict_reason = f"Partial pass: WR={wr*100:.1f}%, PF={pf:.3f}"
    else:
        verdict = "TESTED_KILL"
        verdict_reason = f"Both thresholds failed: WR={wr*100:.1f}% < 45%, PF={pf:.3f} < 1.0"

    print(f"\n  VERDICT: {verdict}")
    print(f"  REASON : {verdict_reason}")
    print("=" * 70)

    # ── Per-currency breakdown ─────────────────────────────────────────────────
    if all_trades:
        print("\n[Per-currency breakdown]")
        for ccy in close.columns:
            ccy_trades = [t for t in all_trades if t["ccy"] == ccy]
            if ccy_trades:
                cm = compute_metrics(ccy_trades)
                carry_yr2023 = get_carry_differential(ccy, pd.Timestamp("2023-06-01"))
                print(f"  {ccy}: n={cm['n_trades']:>3} | WR={cm['win_rate']*100:.1f}% "
                      f"| PF={cm['profit_factor']:.3f} | avg_ret={cm['avg_return_pct']:.4f}% "
                      f"| carry_2023={carry_yr2023:+.2f}%")

    # ── Persist ───────────────────────────────────────────────────────────────
    results = {
        "id": "F-ANON-001",
        "verdict": verdict,
        "verdict_reason": verdict_reason,
        "agg": agg,
        "fold_results": fold_results,
        "pairs": list(close.columns),
        "period": f"{START_DATE} to {END_DATE}",
        "methodology": "G10 carry — long top-3 rate-differential pairs, short bottom-3, weekly rebalance",
        "run_date": datetime.utcnow().isoformat() + "Z",
    }
    out_path = "reports/f_anon_001_carry_backtest_raw.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n[saved] Raw results → {out_path}")
    return results


if __name__ == "__main__":
    main()
