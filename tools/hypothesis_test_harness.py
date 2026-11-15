#!/usr/bin/env python3
"""
HYPOTHESIS-TEST HARNESS — signal vs baseline on untouched out-of-sample data
============================================================================
Fills the protocol: for each asset class, form a testable hypothesis, test it
against a BASELINE on data NOT used to design the signal, keep only robust
improvements.

Design rules (anti-overfit):
  - Baseline is buy-and-hold of the class benchmark (SPY / BTC-USD / GLD /
    BND / ^DXY), NOT a tuned strategy.
  - The signal is applied to a held-out slice (walk-forward: train on first
    60%, TEST on last 40% — untouched).
  - Only a signal that beats baseline on the TEST slice (Sharpe, maxDD) and
    is cost-inclusive is kept.

Usage:
    python3 tools/hypothesis_test_harness.py --cfg hypothesis_cfg.json
Config schema:
    {"hypotheses": [{
        "id": "h1", "asset_class": "EQUITY", "ticker": "SPY",
        "signal": "sma200",           # sma200 | momentum | sma50cross | mom6
        "direction": "long"            # long | short
    }]}
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

REPO = Path(__file__).resolve().parents[1]
TRAIN_FRAC = 0.60
COST_PCT = 0.10      # round-trip % per trade
EXIT_HORIZON = 21    # days held per signal week


def fetch(ticker: str) -> pd.Series:
    px = yf.download(ticker, start="2015-01-01", progress=False, auto_adjust=True)
    return px["Close"].squeeze().dropna()


def apply_signal(close: pd.Series, signal: str) -> pd.Series:
    if signal == "sma200":
        sma = close.rolling(200).mean()
        return (close > sma).astype(float)
    if signal == "sma50cross":
        fast, slow = close.rolling(50).mean(), close.rolling(200).mean()
        sig = (fast > slow).astype(float)
        return sig
    if signal == "momentum":
        return (close.pct_change(126) > 0).astype(float)
    if signal == "mom6":
        return (close.pct_change(6 * 21) > 0).astype(float)
    if signal == "buyhold":
        return pd.Series(1.0, index=close.index)
    raise ValueError(f"unknown signal {signal}")


def evaluate(close: pd.Series, sig: pd.Series) -> dict:
    # weekly sampling
    df = pd.DataFrame({"close": close, "sig": sig}).resample("W").last()
    sig_shift = df["sig"].shift(1).fillna(0)
    strat_ret = sig_shift * df["close"].pct_change().fillna(0)
    bh_ret = df["close"].pct_change().fillna(0)
    # cost on position changes
    strat_ret = strat_ret - COST_PCT / 100 * sig_shift.diff().abs().fillna(0)
    for name, ret in (("strategy", strat_ret), ("baseline", bh_ret)):
        eq = (1 + ret).cumprod()
        sharpe = ret.mean() / ret.std() * np.sqrt(52) if ret.std() > 0 else 0.0
        dd = (eq / eq.cummax() - 1).min()
        if name == "strategy":
            sr, mdd, final = sharpe, dd, eq.iloc[-1]
        else:
            br, bdd, bfinal = sharpe, dd, eq.iloc[-1]
    return {"sharpe": float(sr), "max_dd": float(mdd), "final": float(final),
            "baseline_sharpe": float(br), "baseline_max_dd": float(bdd),
            "baseline_final": float(bfinal)}


def run(cfg: dict) -> list:
    out = []
    for h in cfg["hypotheses"]:
        ticker = h["ticker"]
        close = fetch(ticker)
        if len(close) < 300:
            out.append({**h, "verdict": "INSUFFICIENT_DATA", "n_days": int(len(close))})
            continue
        sig = apply_signal(close, h["signal"])
        split = int(len(close) * TRAIN_FRAC)
        test_close, test_sig = close.iloc[split:], sig.iloc[split:]
        r = evaluate(test_close, test_sig)   # ONLY the untouched test slice
        # robust = beats baseline Sharpe on the TEST slice
        robust = r["sharpe"] > r["baseline_sharpe"] and r["max_dd"] > r["baseline_max_dd"]
        out.append({**h, "verdict": "ROBUST" if robust else "REJECTED",
                    **{f"test_{k}": v for k, v in r.items()},
                    "n_test_days": int(len(test_close))})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cfg", required=True)
    ap.add_argument("--json", default=str(REPO / "reports/hypothesis_test_results.json"))
    a = ap.parse_args()
    cfg = json.loads(Path(a.cfg).read_text())
    results = run(cfg)
    Path(a.json).parent.mkdir(parents=True, exist_ok=True)
    Path(a.json).write_text(json.dumps(results, indent=2))
    for r in results:
        print(f"[{r['verdict']:12}] {r['id']:8} {r['asset_class']:12} "
              f"{r['signal']:8} test_sharpe={r.get('test_sharpe','-'):>6} "
              f"vs_base={r.get('test_baseline_sharpe','-'):>6} "
              f"test_maxDD={r.get('test_max_dd','-'):>6}")
    print(f"wrote {a.json}")


if __name__ == "__main__":
    main()
