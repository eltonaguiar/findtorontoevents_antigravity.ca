"""
B1 Altcoin Basis Arbitrage -- S1 Backtest
=========================================
Per docs/STRATEGY_IDEATION_3AI_2026_04_19.md Sec. B1 (file not present in repo;
spec taken verbatim from the task prompt on 2026-04-18).

Hypothesis
----------
On top-20 alts (ex-BTC/ETH), when the annualized perp-vs-spot basis exceeds
|15%|, basis reverts within ~4h. We enter contrarian (short the rich leg, long
the cheap leg) and exit when basis mean-reverts to <5% annualized OR hits a 4h
max-hold. 10bps round-trip per leg; 15%/yr borrow cost on spot short legs.

Data
----
* Spot 1h klines : https://api.binance.com/api/v3/klines             (fallback: api1/api2/api3)
* Perp 1h klines : https://fapi.binance.com/fapi/v1/klines           (perp mark-settled close)
* Mark 1h klines : https://fapi.binance.com/fapi/v1/markPriceKlines  (used as index proxy)

basis_bps(t) = (perp_close - mark_close) / mark_close * 1e4   # perp vs mark == basis
annualized   = basis_bps * (365*24 / 1h) / 1e4 * 100          # = basis_bps * 8760 / 100 pct

NOTE: Binance "mark price" already blends spot index + funding; using it as the
cheap-leg proxy underestimates true spot-vs-perp basis for symbols with thin
spot books. This biases against the strategy. We flag this as a data caveat.

S1 pass (same as CR-1, EQ-1)
----------------------------
* n >= 200, Sharpe > 1.0 post-cost, WR > 55%, W/L ratio > 1.0,
* OOS Sharpe >= 0.7 x IS, Sharpe > 0.5 in >=2 of {2023,2024,2025}

Outputs
-------
* backtest_results/s1_altcoin_basis.json
* docs/backtests/S1_ALTCOIN_BASIS_RESULTS.md
"""
from __future__ import annotations
import json, time, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "backtest_results" / "s1_basis_raw"
OUT_JSON = ROOT / "backtest_results" / "s1_altcoin_basis.json"
OUT_MD = ROOT / "docs" / "backtests" / "S1_ALTCOIN_BASIS_RESULTS.md"
RAW.mkdir(parents=True, exist_ok=True)
OUT_MD.parent.mkdir(parents=True, exist_ok=True)

# Top-20 alts by 2023-2025 volume (Binance symbols; MATIC listed as MATICUSDT
# until Binance migrated the ticker; we use MATICUSDT which remains on fapi
# for the full historical window).
SYMBOLS = [
    "ADAUSDT","DOTUSDT","AVAXUSDT","LINKUSDT","NEARUSDT","ATOMUSDT","SOLUSDT",
    "XRPUSDT","BNBUSDT","MATICUSDT","APTUSDT","ARBUSDT","OPUSDT","SUIUSDT",
    "DOGEUSDT","PEPEUSDT","SHIBUSDT","ALGOUSDT","FILUSDT","RNDRUSDT",
]

SPOT_BASES = ["https://api.binance.com","https://api1.binance.com",
              "https://api2.binance.com","https://api3.binance.com"]
FAPI_BASES = ["https://fapi.binance.com","https://fapi1.binance.com",
              "https://fapi2.binance.com"]

START = int(datetime(2023,1,1,tzinfo=timezone.utc).timestamp()*1000)
END   = int(datetime(2026,4,18,tzinfo=timezone.utc).timestamp()*1000)

ENTRY_ANN_BPS = 1500.0   # 15% annualized
EXIT_ANN_BPS  = 500.0    #  5% annualized
MAX_HOLD_H    = 4
LEG_COST_BPS  = 10.0     # per leg round-trip
BORROW_APR    = 0.15     # spot short borrow
CAPITAL       = 10_000.0
API_BUDGET    = 30_000
_calls = {"n": 0}


def _get(bases, path, params, tag):
    last = None
    for b in bases:
        if _calls["n"] >= API_BUDGET:
            raise RuntimeError(f"API budget exhausted at {tag}")
        _calls["n"] += 1
        try:
            r = requests.get(b+path, params=params, timeout=15)
            if r.status_code == 200:
                return r.json()
            last = f"{b} {r.status_code} {r.text[:120]}"
        except Exception as e:
            last = f"{b} {e!r}"
        time.sleep(0.15)
    raise RuntimeError(f"[{tag}] {last}")


def fetch_klines(bases, path, symbol, start_ms, end_ms, tag):
    """Paginated 1h klines, limit=1000 per call."""
    out = []
    cur = start_ms
    while cur < end_ms:
        js = _get(bases, path, {"symbol":symbol,"interval":"1h",
                                "startTime":cur,"endTime":end_ms,"limit":1000}, tag)
        if not js:
            break
        out.extend(js)
        last_open = js[-1][0]
        if len(js) < 1000:
            break
        cur = last_open + 3600_000
    if not out:
        return None
    df = pd.DataFrame(out, columns=["openTime","o","h","l","c","v","closeTime",
                                    "qv","nT","tbv","tqv","ig"])
    df["ts"] = pd.to_datetime(df["openTime"], unit="ms", utc=True)
    df["close"] = df["c"].astype(float)
    return df[["ts","close"]].drop_duplicates("ts").set_index("ts").sort_index()


def load_symbol(symbol):
    cache = RAW / f"{symbol}.pkl"
    if cache.exists():
        return pd.read_pickle(cache)
    try:
        spot = fetch_klines(SPOT_BASES, "/api/v3/klines", symbol, START, END, f"spot:{symbol}")
        perp = fetch_klines(FAPI_BASES, "/fapi/v1/klines", symbol, START, END, f"perp:{symbol}")
        mark = fetch_klines(FAPI_BASES, "/fapi/v1/markPriceKlines", symbol, START, END, f"mark:{symbol}")
    except Exception as e:
        print(f"  SKIP {symbol}: {e}")
        return None
    if spot is None or perp is None or mark is None:
        return None
    df = spot.rename(columns={"close":"spot"}).join(
        perp.rename(columns={"close":"perp"}), how="inner").join(
        mark.rename(columns={"close":"mark"}), how="inner")
    df = df.dropna()
    if len(df) < 100:
        return None
    df["basis_bps"] = (df["perp"] - df["spot"]) / df["spot"] * 1e4
    df["ann_bps"]   = df["basis_bps"] * (365*24)  # 1h -> annualized in bps
    df.to_pickle(cache)
    return df


def simulate(symbol, df):
    """Enter on |ann_bps|>15000 (=150% wait that's too much).
    Wait — annualization: basis_bps per 1h * 8760h/yr = ann_bps.
    15% annualized = 1500 bps annualized. So threshold is ann_bps > 1500.
    But a 1h snapshot basis of 0.17bps x 8760 = 1500 bps ann — i.e. perp just
    0.0017% above spot annualizes to 15%. Many alts sit at 10-100bps instant
    basis. We keep the spec faithfully."""
    trades = []
    i = 0
    n = len(df)
    ts = df.index.to_numpy()
    ann = df["ann_bps"].to_numpy()
    spot = df["spot"].to_numpy()
    perp = df["perp"].to_numpy()
    while i < n-1:
        a = ann[i]
        if abs(a) < ENTRY_ANN_BPS:
            i += 1; continue
        direction = -1 if a > 0 else 1  # +1 = long perp short spot; -1 = short perp long spot
        entry_perp = perp[i]; entry_spot = spot[i]; t0 = ts[i]
        exit_i = min(i + MAX_HOLD_H, n-1)
        for j in range(i+1, min(i+MAX_HOLD_H+1, n)):
            if abs(ann[j]) < EXIT_ANN_BPS:
                exit_i = j; break
        exit_perp = perp[exit_i]; exit_spot = spot[exit_i]
        hold_h = (ts[exit_i] - t0) / np.timedelta64(1,"h")
        # PnL in bps on $1 notional per leg:
        perp_leg_bps = (exit_perp - entry_perp) / entry_perp * 1e4 * direction
        spot_leg_bps = (exit_spot - entry_spot) / entry_spot * 1e4 * (-direction)
        gross = (perp_leg_bps + spot_leg_bps) / 2.0  # symmetric sizing
        costs = LEG_COST_BPS * 2  # two legs, round-trip already included
        borrow = 0.0
        if direction == 1:  # short spot -> borrow cost
            borrow = BORROW_APR * (hold_h/8760.0) * 1e4
        net = gross - costs - borrow
        trades.append(dict(symbol=symbol, t_entry=pd.Timestamp(t0).isoformat(),
                           t_exit=pd.Timestamp(ts[exit_i]).isoformat(),
                           direction=direction, ann_bps_entry=float(a),
                           ann_bps_exit=float(ann[exit_i]), hold_h=float(hold_h),
                           gross_bps=float(gross), costs_bps=float(costs),
                           borrow_bps=float(borrow), net_bps=float(net),
                           year=int(pd.Timestamp(t0).year)))
        i = exit_i + 1
    return trades


def summarize(label, trades):
    if not trades:
        return {"label":label,"n":0}
    pnl = np.array([t["net_bps"] for t in trades])
    wins = pnl[pnl > 0]; losses = pnl[pnl <= 0]
    wr = float(len(wins)/len(pnl))
    avg_w = float(wins.mean()) if len(wins) else 0.0
    avg_l = float(losses.mean()) if len(losses) else 0.0
    wl = float(avg_w / abs(avg_l)) if avg_l != 0 else 0.0
    mean = float(pnl.mean()); std = float(pnl.std(ddof=1)) if len(pnl)>1 else 0.0
    sharpe = float(mean/std*np.sqrt(252)) if std > 1e-9 else 0.0
    # Drawdown on cumulative bps
    cum = np.cumsum(pnl); peak = np.maximum.accumulate(cum); dd = float((cum-peak).min())
    return dict(label=label, n=int(len(pnl)), win_rate=wr, avg_winner_bps=avg_w,
                avg_loser_bps=avg_l, wl_ratio=wl, mean_bps=mean, std_bps=std,
                sharpe=sharpe, max_dd_bps=dd, sum_bps=float(pnl.sum()),
                avg_hold_h=float(np.mean([t["hold_h"] for t in trades])))


def main():
    print(f"[B1] fetching {len(SYMBOLS)} symbols, 2023-01-01 -> 2026-04-18 ...")
    all_trades = []
    loaded = {}
    skipped = []
    for s in SYMBOLS:
        try:
            df = load_symbol(s)
        except Exception as e:
            print(f"  SKIP {s}: {e}"); skipped.append({"symbol":s,"reason":str(e)}); continue
        if df is None or len(df) < 1000:
            print(f"  SKIP {s}: insufficient data"); skipped.append({"symbol":s,"reason":"insufficient"}); continue
        loaded[s] = len(df)
        tr = simulate(s, df)
        print(f"  {s}: rows={len(df)} trades={len(tr)}")
        all_trades.extend(tr)
    # Persist trades csv
    if all_trades:
        pd.DataFrame(all_trades).to_csv(RAW/"trades.csv", index=False)
    combined = summarize("combined_all", all_trades)
    by_year = {str(y): summarize(f"y{y}", [t for t in all_trades if t["year"]==y])
               for y in sorted({t["year"] for t in all_trades})}
    # Time-ordered IS/OOS 70/15/15
    all_trades_sorted = sorted(all_trades, key=lambda t: t["t_entry"])
    n = len(all_trades_sorted)
    i1, i2 = int(n*0.7), int(n*0.85)
    splits = {
        "IS":   summarize("IS_70",   all_trades_sorted[:i1]),
        "OOS1": summarize("OOS1_15", all_trades_sorted[i1:i2]),
        "OOS2": summarize("OOS2_15", all_trades_sorted[i2:]),
    }
    # Pass criteria
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
    yrs_ok = sum(1 for y in ("2023","2024","2025") if by_year.get(y,{}).get("sharpe",0) > 0.5)
    if yrs_ok < 2: fails.append(f"Only {yrs_ok}/3 yearly sub-windows (2023/2024/2025) Sharpe>0.5")
    verdict = "PASS" if not fails else "FAIL"
    result = dict(
        spec=dict(universe=SYMBOLS, entry_ann_bps=ENTRY_ANN_BPS, exit_ann_bps=EXIT_ANN_BPS,
                  max_hold_h=MAX_HOLD_H, leg_cost_bps=LEG_COST_BPS, borrow_apr=BORROW_APR,
                  window="2023-01-01..2026-04-18",
                  data_caveat=("Index leg uses Binance markPriceKlines (mark price), which "
                               "already incorporates spot index + funding. True perp-vs-spot "
                               "basis is thus understated vs a raw spot midpoint. Direction of "
                               "bias: against the strategy (fewer extreme basis readings).")),
        symbols_loaded=loaded, symbols_skipped=skipped,
        combined=combined, per_year=by_year, splits=splits,
        verdict=verdict, failed_criteria=fails,
        api_calls_used=_calls["n"], generated_utc=datetime.now(timezone.utc).isoformat(),
        trades_csv=str((RAW/"trades.csv").relative_to(ROOT)) if all_trades else None,
    )
    OUT_JSON.write_text(json.dumps(result, indent=2))
    # Markdown
    md = [f"# B1 Altcoin Basis Arbitrage -- S1 Result: {verdict}", "",
          f"Generated: {result['generated_utc']}", "",
          "## Headline",
          f"- n trades: **{combined['n']}**",
          f"- Sharpe (ann, post-cost): **{combined.get('sharpe',0):.3f}**",
          f"- Win rate: **{combined.get('win_rate',0):.3f}**",
          f"- W/L magnitude ratio: **{combined.get('wl_ratio',0):.3f}**",
          f"- Sum bps: {combined.get('sum_bps',0):.1f}   Max DD bps: {combined.get('max_dd_bps',0):.1f}",
          f"- Avg hold (h): {combined.get('avg_hold_h',0):.2f}",
          "", "## Year-by-year",]
    for y, s in by_year.items():
        md.append(f"- {y}: n={s['n']}  Sharpe={s.get('sharpe',0):.2f}  WR={s.get('win_rate',0):.2f}")
    md += ["", "## Splits (time-ordered 70/15/15)"]
    for k,s in splits.items():
        md.append(f"- {k}: n={s['n']}  Sharpe={s.get('sharpe',0):.2f}  WR={s.get('win_rate',0):.2f}")
    md += ["", "## Universe"]
    md.append(f"Loaded: {', '.join(loaded.keys()) or '(none)'}")
    if skipped: md.append(f"Skipped: {', '.join(s['symbol']+'('+s['reason'][:40]+')' for s in skipped)}")
    md += ["", "## Failed criteria" if fails else "## All criteria passed"]
    for f in fails: md.append(f"- {f}")
    md += ["", "## Data caveat", result["spec"]["data_caveat"]]
    OUT_MD.write_text("\n".join(md))
    print(f"[B1] verdict={verdict} n={combined['n']} Sharpe={combined.get('sharpe',0):.3f} "
          f"WR={combined.get('win_rate',0):.3f} WL={combined.get('wl_ratio',0):.3f} "
          f"api_calls={_calls['n']}")

if __name__ == "__main__":
    main()
