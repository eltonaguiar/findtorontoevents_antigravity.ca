"""
C3 VVIX / VIX Mean Reversion -- S1 Backtest
===========================================
Hypothesis: VVIX overshoots when VIX spikes; VVIX/VIX ratio reverts. Short
vol-of-vol via SVXY long (can't trade VVIX directly). Implementation per
spec: trade SVXY (inverse VIX futures ETF) as the short-vol-of-vol proxy.

Signal: r_t = VVIX/VIX. When r_t > 90d rolling 90th pctile -> long SVXY.
Exit: ratio <= 90d rolling median, OR 20-day max hold.
Costs: 10bps per side (=20bps round-trip).
Window: 2020-01-01 .. 2026-04-17 daily closes via yfinance.

Pass criteria mirror CR-1/EQ-1/B1:
  n>=200, Sharpe>1.0 post-cost, WR>55%, W/L>1.0,
  OOS Sharpe>=0.7*IS, Sharpe>0.5 in >=2 of {2022,2023,2024,2025}.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
OUT_JSON = ROOT / "backtest_results" / "s1_vvix_vix.json"
OUT_MD = ROOT / "docs" / "backtests" / "S1_VVIX_VIX_RESULTS.md"
OUT_MD.parent.mkdir(parents=True, exist_ok=True)

LOOKBACK = 90
ENTRY_Q = 0.90
MAX_HOLD_D = 20
LEG_COST_BPS = 10.0
CAPITAL = 10_000.0


def load():
    df = yf.download(["^VIX","^VVIX","SVXY"], start="2020-01-01",
                     end="2026-04-18", progress=False, auto_adjust=True)["Close"]
    df = df.dropna()
    df.columns.name = None
    return df


def simulate(df):
    df = df.copy()
    df["ratio"] = df["^VVIX"] / df["^VIX"]
    df["q90"] = df["ratio"].rolling(LOOKBACK).quantile(ENTRY_Q)
    df["med"] = df["ratio"].rolling(LOOKBACK).median()
    df = df.dropna()
    trades = []
    i = 0
    idx = df.index
    r = df["ratio"].to_numpy(); q90 = df["q90"].to_numpy(); med = df["med"].to_numpy()
    svxy = df["SVXY"].to_numpy()
    n = len(df)
    while i < n-1:
        if r[i] <= q90[i]:
            i += 1; continue
        entry = svxy[i]; t0 = idx[i]
        exit_j = min(i + MAX_HOLD_D, n-1)
        for j in range(i+1, min(i+MAX_HOLD_D+1, n)):
            if r[j] <= med[j]:
                exit_j = j; break
        exit_p = svxy[exit_j]
        gross_bps = (exit_p - entry)/entry * 1e4
        net_bps = gross_bps - 2*LEG_COST_BPS
        trades.append(dict(t_entry=t0.isoformat(), t_exit=idx[exit_j].isoformat(),
                           ratio_entry=float(r[i]), ratio_exit=float(r[exit_j]),
                           hold_d=int((idx[exit_j]-t0).days),
                           gross_bps=float(gross_bps), net_bps=float(net_bps),
                           year=int(t0.year)))
        i = exit_j + 1
    return trades


def summarize(label, trades):
    if not trades: return {"label":label,"n":0}
    pnl = np.array([t["net_bps"] for t in trades])
    wins = pnl[pnl>0]; losses = pnl[pnl<=0]
    wr = float(len(wins)/len(pnl))
    avg_w = float(wins.mean()) if len(wins) else 0.0
    avg_l = float(losses.mean()) if len(losses) else 0.0
    wl = float(avg_w/abs(avg_l)) if avg_l != 0 else 0.0
    mean = float(pnl.mean()); std = float(pnl.std(ddof=1)) if len(pnl)>1 else 0.0
    sharpe = float(mean/std*np.sqrt(252)) if std > 1e-9 else 0.0
    cum = np.cumsum(pnl); peak = np.maximum.accumulate(cum); dd = float((cum-peak).min())
    return dict(label=label, n=int(len(pnl)), win_rate=wr, avg_winner_bps=avg_w,
                avg_loser_bps=avg_l, wl_ratio=wl, mean_bps=mean, std_bps=std,
                sharpe=sharpe, max_dd_bps=dd, sum_bps=float(pnl.sum()),
                avg_hold_d=float(np.mean([t["hold_d"] for t in trades])))


def main():
    df = load()
    print(f"[C3] rows={len(df)}   VIX range {df['^VIX'].min():.2f}..{df['^VIX'].max():.2f}")
    trades = simulate(df)
    print(f"[C3] trades={len(trades)}")
    combined = summarize("combined_all", trades)
    by_year = {str(y): summarize(f"y{y}", [t for t in trades if t["year"]==y])
               for y in sorted({t["year"] for t in trades})}
    trades_sorted = sorted(trades, key=lambda t: t["t_entry"])
    n = len(trades_sorted); i1,i2 = int(n*0.7), int(n*0.85)
    splits = {"IS":summarize("IS_70",trades_sorted[:i1]),
              "OOS1":summarize("OOS1_15",trades_sorted[i1:i2]),
              "OOS2":summarize("OOS2_15",trades_sorted[i2:])}
    fails = []
    if combined["n"] < 200: fails.append(f"n={combined['n']} < 200")
    if combined.get("sharpe",0) <= 1.0: fails.append(f"Sharpe {combined.get('sharpe',0):.2f} <= 1.0")
    if combined.get("win_rate",0) <= 0.55: fails.append(f"WR {combined.get('win_rate',0):.3f} <= 0.55")
    if combined.get("wl_ratio",0) <= 1.0: fails.append(f"W/L {combined.get('wl_ratio',0):.2f} <= 1.0")
    is_s = splits["IS"].get("sharpe",0)
    for k in ("OOS1","OOS2"):
        v = splits[k].get("sharpe",0)
        if is_s > 0 and v < 0.7*is_s:
            fails.append(f"{k} Sharpe {v:.2f} < 0.7 x IS {is_s:.2f}")
    yrs_ok = sum(1 for y in ("2022","2023","2024","2025") if by_year.get(y,{}).get("sharpe",0) > 0.5)
    if yrs_ok < 2: fails.append(f"Only {yrs_ok}/4 yearly sub-windows (2022-2025) Sharpe>0.5")
    verdict = "PASS" if not fails else "FAIL"
    result = dict(
        spec=dict(lookback_d=LOOKBACK, entry_quantile=ENTRY_Q, max_hold_d=MAX_HOLD_D,
                  leg_cost_bps=LEG_COST_BPS, proxy="long SVXY (short vol-of-vol)",
                  window="2020-01-01..2026-04-18",
                  data_caveat=("yfinance ^VVIX series has occasional stale/NA "
                               "days (esp. holidays) which we drop with .dropna(). "
                               "SVXY had a 0.5x leverage re-scale on 2018-02-27, "
                               "pre-window. No further data breaks identified.")),
        combined=combined, per_year=by_year, splits=splits,
        verdict=verdict, failed_criteria=fails,
        rows_used=int(len(df)),
        generated_utc=datetime.now(timezone.utc).isoformat())
    OUT_JSON.write_text(json.dumps(result, indent=2))
    md = [f"# C3 VVIX/VIX Mean Reversion -- S1 Result: {verdict}","",
          f"Generated: {result['generated_utc']}","",
          "## Headline",
          f"- n trades: **{combined['n']}**",
          f"- Sharpe (ann, post-cost): **{combined.get('sharpe',0):.3f}**",
          f"- Win rate: **{combined.get('win_rate',0):.3f}**",
          f"- W/L magnitude ratio: **{combined.get('wl_ratio',0):.3f}**",
          f"- Sum bps: {combined.get('sum_bps',0):.1f}   Max DD bps: {combined.get('max_dd_bps',0):.1f}",
          f"- Avg hold (d): {combined.get('avg_hold_d',0):.2f}",
          "", "## Year-by-year"]
    for y,s in by_year.items():
        md.append(f"- {y}: n={s['n']}  Sharpe={s.get('sharpe',0):.2f}  WR={s.get('win_rate',0):.2f}")
    md += ["","## Splits (time-ordered 70/15/15)"]
    for k,s in splits.items():
        md.append(f"- {k}: n={s['n']}  Sharpe={s.get('sharpe',0):.2f}  WR={s.get('win_rate',0):.2f}")
    md += ["","## Failed criteria" if fails else "## All criteria passed"]
    for f in fails: md.append(f"- {f}")
    md += ["","## Data caveat", result["spec"]["data_caveat"]]
    OUT_MD.write_text("\n".join(md))
    print(f"[C3] verdict={verdict} n={combined['n']} Sharpe={combined.get('sharpe',0):.3f} "
          f"WR={combined.get('win_rate',0):.3f} WL={combined.get('wl_ratio',0):.3f}")

if __name__ == "__main__":
    main()
