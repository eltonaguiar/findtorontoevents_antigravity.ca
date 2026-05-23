#!/usr/bin/env python3
"""Piotroski F-Score (9 factors) backtest.

Per growth/breakout swarm consensus 2026-05-13 (4/4 engines): Piotroski 2000
"Value Investing: The Use of Historical Financial Statement Information"
classic 9-criteria quality score for low-P/B value stocks.

Spec:
  F-Score = sum of 9 binary criteria across 3 categories:
  PROFITABILITY (4):
    1. Net income > 0
    2. Operating cash flow > 0
    3. ROA(t) > ROA(t-1)
    4. CFO > Net income (quality of earnings)
  LEVERAGE/LIQUIDITY/SOURCE OF FUNDS (3):
    5. Long-term debt(t) < long-term debt(t-1)
    6. Current ratio(t) > current ratio(t-1)
    7. Shares outstanding(t) <= shares outstanding(t-1) (no dilution)
  OPERATING EFFICIENCY (2):
    8. Gross margin(t) > gross margin(t-1)
    9. Asset turnover(t) > asset turnover(t-1)

  Long stocks with F-score >= 7. Annual rebalance.

Free data path: yfinance .info + .financials + .cashflow + .balance_sheet
  (limited to most-recent vs prior-year — quarterly history available but noisy)

Universe: 50 large-cap US stocks (same as low-vol compounder for comparability).

NFA - hindsight backtest. Note: yfinance fundamentals data is point-in-time
TODAY, not point-in-time historical — survivorship bias risk.
"""
from __future__ import annotations
import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path
try:
    import numpy as np
    import pandas as pd
    import yfinance as yf
except ImportError as exc:
    print(f"ERROR: {exc}", file=sys.stderr); sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent
UNIVERSE = [
    "JNJ","PFE","UNH","ABBV","LLY","MRK","ABT","BMY","CVS","TMO",
    "WMT","HD","COST","KO","MCD","PG","PEP","CL","KMB","MO",
    "JPM","BAC","WFC","GS","MS","BLK","V","MA","AXP","C",
    "XOM","CVX","COP","SLB","MPC",
    "BRK-B","SO","DUK","NEE","D","AEP","XEL","SRE",
    "AAPL","MSFT","GOOGL","ORCL","CSCO","IBM","INTC",
]


def compute_fscore(ticker: str) -> tuple[int, dict]:
    """Compute Piotroski F-score from yfinance fundamentals. Returns (score, breakdown)."""
    try:
        t = yf.Ticker(ticker)
        fin = t.financials  # annual income statement
        bs = t.balance_sheet  # annual balance sheet
        cf = t.cashflow  # annual cash flow
        info = t.info
    except Exception as exc:
        return -1, {"error": str(exc)}

    if fin.empty or bs.empty or cf.empty:
        return -1, {"error": "missing financial statements"}

    # Get most-recent and prior-year columns
    if len(fin.columns) < 2 or len(bs.columns) < 2 or len(cf.columns) < 2:
        return -1, {"error": "need >= 2 years history"}

    def _get(df, key, idx):
        try:
            for k in df.index:
                if key.lower() in str(k).lower():
                    return float(df.loc[k].iloc[idx])
        except Exception: pass
        return None

    # Most-recent (col 0), prior-year (col 1)
    net_income_now = _get(fin, "Net Income", 0)
    net_income_prev = _get(fin, "Net Income", 1)
    cfo_now = _get(cf, "Operating Cash Flow", 0) or _get(cf, "Cash Flow From Continuing Operating", 0)
    cfo_prev = _get(cf, "Operating Cash Flow", 1) or _get(cf, "Cash Flow From Continuing Operating", 1)
    total_assets_now = _get(bs, "Total Assets", 0)
    total_assets_prev = _get(bs, "Total Assets", 1)
    lt_debt_now = _get(bs, "Long Term Debt", 0)
    lt_debt_prev = _get(bs, "Long Term Debt", 1)
    current_assets_now = _get(bs, "Current Assets", 0)
    current_liab_now = _get(bs, "Current Liabilities", 0)
    current_assets_prev = _get(bs, "Current Assets", 1)
    current_liab_prev = _get(bs, "Current Liabilities", 1)
    shares_now = _get(bs, "Share Issued", 0) or _get(bs, "Ordinary Shares Number", 0)
    shares_prev = _get(bs, "Share Issued", 1) or _get(bs, "Ordinary Shares Number", 1)
    gross_profit_now = _get(fin, "Gross Profit", 0)
    gross_profit_prev = _get(fin, "Gross Profit", 1)
    revenue_now = _get(fin, "Total Revenue", 0) or _get(fin, "Revenue", 0)
    revenue_prev = _get(fin, "Total Revenue", 1) or _get(fin, "Revenue", 1)

    score = 0
    breakdown = {}

    # 1. Net income > 0
    if net_income_now is not None and net_income_now > 0:
        score += 1; breakdown["ni_positive"] = 1
    else: breakdown["ni_positive"] = 0
    # 2. CFO > 0
    if cfo_now is not None and cfo_now > 0:
        score += 1; breakdown["cfo_positive"] = 1
    else: breakdown["cfo_positive"] = 0
    # 3. ROA(t) > ROA(t-1)
    if (net_income_now is not None and total_assets_now and total_assets_now > 0
        and net_income_prev is not None and total_assets_prev and total_assets_prev > 0):
        roa_now = net_income_now / total_assets_now
        roa_prev = net_income_prev / total_assets_prev
        if roa_now > roa_prev:
            score += 1; breakdown["roa_up"] = 1
        else: breakdown["roa_up"] = 0
    # 4. CFO > Net income
    if cfo_now is not None and net_income_now is not None and cfo_now > net_income_now:
        score += 1; breakdown["cfo_gt_ni"] = 1
    else: breakdown["cfo_gt_ni"] = 0
    # 5. LT debt decrease
    if lt_debt_now is not None and lt_debt_prev is not None and lt_debt_now < lt_debt_prev:
        score += 1; breakdown["lt_debt_down"] = 1
    else: breakdown["lt_debt_down"] = 0
    # 6. Current ratio increase
    if (current_assets_now is not None and current_liab_now and current_liab_now > 0
        and current_assets_prev is not None and current_liab_prev and current_liab_prev > 0):
        cr_now = current_assets_now / current_liab_now
        cr_prev = current_assets_prev / current_liab_prev
        if cr_now > cr_prev:
            score += 1; breakdown["current_ratio_up"] = 1
        else: breakdown["current_ratio_up"] = 0
    # 7. No share dilution
    if shares_now is not None and shares_prev is not None and shares_now <= shares_prev:
        score += 1; breakdown["no_dilution"] = 1
    else: breakdown["no_dilution"] = 0
    # 8. Gross margin increase
    if (gross_profit_now is not None and revenue_now and revenue_now > 0
        and gross_profit_prev is not None and revenue_prev and revenue_prev > 0):
        gm_now = gross_profit_now / revenue_now
        gm_prev = gross_profit_prev / revenue_prev
        if gm_now > gm_prev:
            score += 1; breakdown["gross_margin_up"] = 1
        else: breakdown["gross_margin_up"] = 0
    # 9. Asset turnover increase
    if (revenue_now and total_assets_now and total_assets_now > 0
        and revenue_prev and total_assets_prev and total_assets_prev > 0):
        at_now = revenue_now / total_assets_now
        at_prev = revenue_prev / total_assets_prev
        if at_now > at_prev:
            score += 1; breakdown["asset_turnover_up"] = 1
        else: breakdown["asset_turnover_up"] = 0

    return score, breakdown


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", default="2020-01-01")
    p.add_argument("--end", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    p.add_argument("--out", default="audit_dashboard/data/piotroski_fscore_backtest.json")
    p.add_argument("--score-threshold", type=int, default=7)
    args = p.parse_args()

    print(f"# computing Piotroski F-score for {len(UNIVERSE)} tickers", file=sys.stderr)
    scores = {}
    for sym in UNIVERSE:
        s, br = compute_fscore(sym)
        scores[sym] = {"score": s, "breakdown": br}
        if s >= 0:
            print(f"  {sym:8}  F-score={s}/9", file=sys.stderr)

    high_quality = {s: v for s, v in scores.items() if v["score"] >= args.score_threshold}
    print(f"\n## High-quality (F-score >= {args.score_threshold}): {len(high_quality)} of {len(UNIVERSE)}",
          file=sys.stderr)
    for sym in sorted(high_quality.keys()):
        print(f"  {sym}  F-score={high_quality[sym]['score']}", file=sys.stderr)

    if not high_quality:
        print("\nNo tickers meet F-score threshold — exiting", file=sys.stderr)
        return

    # Backtest: equal-weight buy-and-hold the high-F-score basket vs SPY
    tickers_to_test = list(high_quality.keys())
    df = yf.download(tickers_to_test + ["SPY"], start=args.start, end=args.end,
                     interval="1d", progress=False, auto_adjust=True)
    closes = df["Close"] if isinstance(df.columns, pd.MultiIndex) else df

    if closes.empty:
        print("No price data", file=sys.stderr); return

    basket_rets = closes[tickers_to_test].pct_change().mean(axis=1).dropna()
    spy_rets = closes["SPY"].pct_change().dropna() if "SPY" in closes.columns else None

    eq_basket = (1 + basket_rets).cumprod()
    eq_spy = (1 + spy_rets).cumprod() if spy_rets is not None else None

    basket_total = (eq_basket.iloc[-1] - 1) * 100 if not eq_basket.empty else 0
    spy_total = (eq_spy.iloc[-1] - 1) * 100 if eq_spy is not None and not eq_spy.empty else 0
    basket_sharpe = (basket_rets.mean() / basket_rets.std() * np.sqrt(252)) if basket_rets.std() > 0 else 0
    spy_sharpe = (spy_rets.mean() / spy_rets.std() * np.sqrt(252)) if spy_rets is not None and spy_rets.std() > 0 else 0
    # MDD
    peak = eq_basket.cummax()
    mdd_basket = ((peak - eq_basket) / peak).max() * 100
    peak_spy = eq_spy.cummax() if eq_spy is not None else None
    mdd_spy = ((peak_spy - eq_spy) / peak_spy).max() * 100 if peak_spy is not None else 0

    print(f"\n## Buy-and-hold {len(tickers_to_test)} F-score>={args.score_threshold} basket", file=sys.stderr)
    print(f"  Total return: {basket_total:+.1f}%", file=sys.stderr)
    print(f"  Sharpe (daily ann.): {basket_sharpe:.2f}", file=sys.stderr)
    print(f"  MDD: {mdd_basket:.1f}%", file=sys.stderr)
    print(f"\n## SPY benchmark", file=sys.stderr)
    print(f"  Total return: {spy_total:+.1f}%", file=sys.stderr)
    print(f"  Sharpe: {spy_sharpe:.2f}", file=sys.stderr)
    print(f"  MDD: {mdd_spy:.1f}%", file=sys.stderr)
    print(f"\n## Excess vs SPY: {basket_total - spy_total:+.1f}%", file=sys.stderr)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spec": "Piotroski F-score (9 factors) buy-and-hold high-quality basket vs SPY",
        "universe": UNIVERSE,
        "config": {"score_threshold": args.score_threshold,
                   "start": args.start, "end": args.end,
                   "rebalance": "buy-and-hold (yfinance .info is point-in-time today only)"},
        "fscores": scores,
        "high_quality_basket": tickers_to_test,
        "results": {
            "basket_total_pct": round(float(basket_total), 2),
            "basket_sharpe": round(float(basket_sharpe), 4),
            "basket_mdd_pct": round(float(mdd_basket), 2),
            "spy_total_pct": round(float(spy_total), 2),
            "spy_sharpe": round(float(spy_sharpe), 4),
            "spy_mdd_pct": round(float(mdd_spy), 2),
            "excess_vs_spy_pct": round(float(basket_total - spy_total), 2),
        },
        "caveat": "yfinance .info is current snapshot — survivorship bias unfixable without paid Compustat/CRSP point-in-time.",
        "nfa": "Hindsight backtest.",
    }
    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"\n# wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
