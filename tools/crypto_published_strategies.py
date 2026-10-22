"""Research-only BTC baselines with causal next-close fills and daily MTM.

Strategies:
1. 10-month SMA trend (above=long, below=cash)
2. 200-day SMA trend (above=long, below=cash)
3. Absolute momentum (BTC return >0; no relative-asset comparison)

Gates (GROK_20261022):
1. n >= 100 trades
2. PF >= 1.5
3. PF CI low >= 1.2 (unverified until a valid day-cluster adapter is supplied)
4. MDD <= 20%
5. Random-entry MC >= 95th percentile
6. DSR > 0.95 (with trials logged)
7. PF >= 1.3 at 2x costs
8. Top symbol <= 30% concentration
9. Profitable in both halves (walk-forward)
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "audit_dashboard/data/btcusd_daily.csv"
COST_PER_TRADE = 0.001  # 0.1% per side (taker fee + slippage)
TRIALS_LOG = ROOT / "audit_dashboard/data/trials.csv"

def validate_prices(df):
    if not isinstance(df.index, pd.DatetimeIndex) or df.empty or "close" not in df:
        raise ValueError("Expected a nonempty dated daily close price series")
    if not df.index.is_monotonic_increasing or df.index.has_duplicates:
        raise ValueError("Daily price timestamps must be sorted and unique")
    if len(df) > 1 and not (df.index.to_series().diff().iloc[1:] == pd.Timedelta(days=1)).all():
        raise ValueError("BTC daily path has missing or non-daily observations")
    close = df["close"].to_numpy(dtype=float)
    if not np.isfinite(close).all() or (close <= 0).any():
        raise ValueError("Daily prices must be finite and positive")


def load(path=DATA):
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    if "close" not in df.columns:
        for c in df.columns:
            if str(c).lower() == "close":
                df = df.rename(columns={c: "close"})
                break
    validate_prices(df)
    df = df[["close"]]
    return df

def backtest(df, entry_signal, label):
    """Signal at close t executes at close t+1, not at its own closing price."""
    validate_prices(df)
    close = df["close"].to_numpy(dtype=float)
    n = len(close)
    signal = entry_signal(df) if callable(entry_signal) else entry_signal
    if isinstance(signal, pd.Series) and not signal.index.equals(df.index):
        raise ValueError("Signal timestamps must match daily prices")
    sig = np.asarray(signal)
    if sig.shape != (n,) or not np.isin(sig, [0, 1]).all():
        raise ValueError("Signal must contain one binary long/cash value per day")
    trades = []
    in_pos = False
    entry_price = 0
    entry_day = None
    for i in range(1, n):
        if sig[i-1] == 1 and not in_pos and i < n-1:
            entry_price = close[i]
            entry_day = df.index[i]
            in_pos = True
        elif sig[i-1] == 0 and in_pos:
            exit_price = close[i]
            exit_day = df.index[i]
            ret = (exit_price - entry_price) / entry_price * 100
            trades.append({"entry_day": entry_day, "exit_day": exit_day,
                          "entry": entry_price, "exit": exit_price, "pnl_pct": ret})
            in_pos = False
    # Close open position at end
    if in_pos:
        exit_price = close[-1]
        ret = (exit_price - entry_price) / entry_price * 100
        trades.append({"entry_day": entry_day, "exit_day": df.index[-1],
                      "entry": entry_price, "exit": exit_price, "pnl_pct": ret})
    return trades

def daily_equity(df, trades, costs):
    validate_prices(df)
    held = np.zeros(len(df))
    turnover = np.zeros(len(df))
    previous_exit = -1
    for trade in trades:
        entry = df.index.get_indexer([pd.Timestamp(trade["entry_day"])])[0]
        exit_ = df.index.get_indexer([pd.Timestamp(trade["exit_day"])])[0]
        if entry < 0 or exit_ <= entry:
            raise ValueError("Trade dates must match a positive-duration daily path")
        if entry < previous_exit:
            raise ValueError("Trade overlap exceeds the single-position capital model")
        for field, index in (("entry", entry), ("exit", exit_)):
            if not np.isclose(float(trade[field]), float(df.close.iloc[index]), rtol=1e-10, atol=0):
                raise ValueError("Recorded fill does not match its daily close")
        held[entry+1:exit_+1] = 1
        turnover[entry] += 1
        turnover[exit_] += 1
        previous_exit = exit_
    returns = df.close.pct_change().fillna(0).to_numpy()
    factors = (1 + held * returns) * (1 - costs) ** turnover
    return pd.Series(np.cumprod(factors), index=df.index)


def profit_factor(pnls):
    gain = sum(p for p in pnls if p > 0)
    loss = -sum(p for p in pnls if p < 0)
    return float(gain / loss) if loss > 0 else None


def gates(trades, label, costs=COST_PER_TRADE, trials_so_far=0, prices=None):
    if not np.isfinite(costs) or not 0 <= costs < 1:
        raise ValueError("Per-side costs must be finite and in [0, 1)")
    curve = daily_equity(prices, trades, costs) if prices is not None else None
    if not trades:
        return {"label": label, "n": 0, "gate": "FAIL", "reason": "no trades"}
    for trade in trades:
        if any(not np.isfinite(float(trade[key])) or float(trade[key]) <= 0 for key in ("entry", "exit")):
            raise ValueError("Trade fill prices must be finite and positive")
    pnls = [(float(t["exit"]) / float(t["entry"]) - 1) * 100 for t in trades]
    n = len(pnls)
    pf = profit_factor(pnls)
    # Apply costs
    pnls_cost = [((1 + p/100) * (1-costs)**2 - 1) * 100 for p in pnls]
    w = sum(p > 0 for p in pnls_cost)
    l = sum(p < 0 for p in pnls_cost)
    pf_cost = profit_factor(pnls_cost)
    pf_2x = profit_factor([((1+p/100) * (1-2*costs)**2-1)*100 for p in pnls]) if costs < 0.5 else None
    mdd = compound = cagr = sharpe = None
    if curve is not None:
        mdd = float((1 - curve / curve.cummax().clip(lower=1)).max() * 100)
        compound = float((curve.iloc[-1]-1)*100)
        years = (curve.index[-1]-curve.index[0]).total_seconds() / (365.25*86400)
        cagr = float((curve.iloc[-1]**(1/years)-1)*100) if years > 0 else None
        returns = curve.div(curve.shift(1).fillna(1))-1
        std = returns.std(ddof=1)
        sharpe = float(returns.mean()/std*np.sqrt(365.25)) if len(returns)>1 and std>0 else None
    # These require independently validated adapters, not trade resampling or an ad hoc formula.
    ci_lo = pct = dsr = None
    # Walk-forward: first half vs second half
    half = n // 2
    first_half_pf = profit_factor(pnls_cost[:half])
    second_half_pf = profit_factor(pnls_cost[half:])
    # Gate results
    g1 = n >= 100
    g2 = pf_cost is not None and pf_cost >= 1.5
    g3 = False
    g4 = mdd is not None and mdd <= 20
    g5 = False
    g6 = False
    g7 = pf_2x is not None and pf_2x >= 1.3
    g8 = False  # This suite is 100% BTC; no unregistered single-asset exemption.
    g9 = first_half_pf is not None and second_half_pf is not None and first_half_pf > 1 and second_half_pf > 1
    all_pass = all([g1,g2,g3,g4,g5,g6,g7,g8,g9])
    return {
        "label": label, "n": n, "w": w, "l": l, "wr": w/n if n >= 20 else None,
        "pf_raw": pf, "pf_cost": pf_cost, "pf_2x": pf_2x,
        "compound_pct": compound, "cagr_pct": cagr, "top_symbol_pct": 100,
        "equity_basis": "daily_close_mtm" if curve is not None else "unverified",
        "execution": "signal_close_t_fill_close_t_plus_1",
        "per_side_cost_fraction": costs,
        "half_split_basis": "retrospective_completed_trades_not_independent_OOS",
        "unverified": {
            "bootstrap_ci_lo": "No validated day-cluster PF interval adapter",
            "mc_pct": "No matched random entries from actual market bars",
            "dsr": "No validated DSR with family trial history",
        },
        "mdd": mdd, "bootstrap_ci_lo": ci_lo, "mc_pct": pct,
        "dsr": dsr, "first_half_pf": first_half_pf, "second_half_pf": second_half_pf,
        "sharpe": sharpe, "gates": {"g1_n": g1, "g2_pf": g2, "g3_ci": g3, "g4_mdd": g4,
          "g5_mc": g5, "g6_dsr": g6, "g7_cost": g7, "g8_conc": g8, "g9_walkfwd": g9},
        "gate": "PASS" if all_pass else "FAIL",
        "gates_passed": sum([g1,g2,g3,g4,g5,g6,g7,g8,g9]),
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DATA)
    parser.add_argument("--output", type=Path, default=ROOT / "audit_dashboard/data/published_strategy_gates.json")
    parser.add_argument("--trials", type=Path, default=TRIALS_LOG)
    args = parser.parse_args()
    df = load(args.input)
    results = []
    trials = 0

    # Strategy 1: 10-month SMA (200 trading days ~ 10 months)
    sma200 = df["close"].rolling(200).mean()
    sig1 = (df["close"] > sma200).astype(int).fillna(0)
    t1 = backtest(df, sig1, "sma200")
    r1 = gates(t1, "BTC 200-day SMA trend", trials_so_far=trials, prices=df); trials += 1
    results.append(r1)

    # Strategy 2: 10-month SMA (300 calendar days ~ 10 months)
    sma300 = df["close"].rolling(300).mean()
    sig2 = (df["close"] > sma300).astype(int).fillna(0)
    t2 = backtest(df, sig2, "sma300")
    r2 = gates(t2, "BTC 10-month (300d) SMA trend", trials_so_far=trials, prices=df); trials += 1
    results.append(r2)

    # Strategy 3: Dual momentum (absolute: 12-month return > 0)
    ret12 = df["close"].pct_change(365)
    sig3 = (ret12 > 0).astype(int).fillna(0)
    t3 = backtest(df, sig3, "dual_momentum")
    r3 = gates(t3, "BTC 12-month absolute momentum", trials_so_far=trials, prices=df); trials += 1
    results.append(r3)


    # Strategy 4: 50/200 golden cross, long/cash.
    sma50 = df["close"].rolling(50).mean()
    sma200b = df["close"].rolling(200).mean()
    sig4 = ((sma50 > sma200b).astype(int)).fillna(0)
    t4 = backtest(df, sig4, "golden_cross")
    r4 = gates(t4, "BTC 50/200 golden cross", trials_so_far=trials, prices=df); trials += 1
    results.append(r4)

    # Strategy 5: RSI(14) mean reversion: buy RSI<30, sell RSI>70 (with 200d filter)
    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    above200 = df["close"] > df["close"].rolling(200).mean()
    sig5 = ((rsi < 30) & above200).astype(int)
    # Hold until RSI > 70 or 30 days
    sig5_hold = []
    in_pos = False
    days_held = 0
    for i in range(len(df)):
        r = rsi.iloc[i] if hasattr(rsi, 'iloc') else rsi[i]
        a = above200.iloc[i] if hasattr(above200, 'iloc') else above200[i]
        if not in_pos and (not pd.isna(r)) and r < 30 and a:
            in_pos = True; days_held = 0
        elif in_pos:
            days_held += 1
            if (not pd.isna(r) and r > 70) or days_held >= 30:
                in_pos = False
        sig5_hold.append(1 if in_pos else 0)
    sig5 = pd.Series(sig5_hold, index=df.index)
    t5 = backtest(df, sig5, "rsi_mr")
    r5 = gates(t5, "BTC RSI<30 mean reversion (200d filter, 30d time stop)", trials_so_far=trials, prices=df); trials += 1
    results.append(r5)

    # Strategy 6: both 12-month and 6-month returns positive, long/cash.
    ret6m = df["close"].pct_change(182)
    sig6 = ((ret12 > 0) & (ret6m > 0)).astype(int).fillna(0)
    t6 = backtest(df, sig6, "dual_momentum_12m_6m")
    r6 = gates(t6, "BTC 12m+6m dual momentum (both positive)", trials_so_far=trials, prices=df); trials += 1
    results.append(r6)

    source_hash = hashlib.sha256(args.input.read_bytes()).hexdigest()
    for result in results:
        result["input_sha256"] = source_hash
        result["data_first"] = df.index[0].isoformat()
        result["data_last"] = df.index[-1].isoformat()
    serialized = json.dumps(results, indent=2, allow_nan=False) + "\n"
    print(serialized)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(serialized)
    args.trials.parent.mkdir(parents=True, exist_ok=True)
    with args.trials.open("a", newline="") as f:
        w = csv.writer(f)
        for r in results:
            w.writerow([r["label"], r["n"], r.get("pf_cost"), r.get("mdd"), r["gate"], source_hash])

if __name__ == "__main__":
    main()
