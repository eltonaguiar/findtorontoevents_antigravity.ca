#!/usr/bin/env python3
"""portfolio_tracker.py — practical, free-data portfolio tracking.

Purpose
-------
Track several candidate portfolios side by side, mark them to market on real
prices, record an equity curve, and report performance. Deliberately boring:
the whole point of PART13 was that high-turnover strategies die of fees, so
every option here is low-frequency and low-cost by construction.

Commands
--------
  --init         create the portfolio state from config (idempotent)
  --mark         fetch latest daily close, apply rules, snapshot equity
  --report       performance table from the recorded equity curve
  --replay       walk history bar by bar to test the rules before trusting them
  --html         write a self-contained HTML dashboard

Why daily bars
--------------
Free, long history, and low turnover. A tracker that needs minute data cannot
be run for free at a useful history depth, and the cost wall makes intraday
economically pointless for these strategies anyway.

Rules available per portfolio
-----------------------------
  buy_hold          target weights held constantly
  sma_filter        hold only while <filter_symbol> > its N-month SMA, else cash
  rebalance         'monthly' re-derives target weights from prices

Costs: charged on every rebalance leg, default 10 bp one-way (equity/ETF-ish).
Signals use data through t-1 and trade at t's close (conservative, never
same-bar).
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CFG = ROOT / "portfolios" / "portfolio_config.json"
STATE = ROOT / "portfolios" / "portfolio_state.json"
CURVE = ROOT / "portfolios" / "equity_curve.jsonl"
REPORT_HTML = ROOT / "portfolios" / "portfolio_dashboard.html"
CACHE = ROOT / "portfolios" / "price_cache.json"

START_CASH = 10_000.0
COST_BP = 10.0          # one-way, per leg
SMA_MONTHS = 10


# ------------------------------------------------------------------ price data
def fetch_monthly(tickers: list[str], refresh: bool = False) -> dict[str, pd.Series]:
    """Monthly last-close series from yfinance, dividends included."""
    cache = {}
    if CACHE.exists() and not refresh:
        try:
            cache = json.loads(CACHE.read_text())
        except Exception:
            cache = {}
    out: dict[str, pd.Series] = {}
    missing = [t for t in tickers if t not in cache]
    if missing:
        try:
            import yfinance as yf
            for t in missing:
                try:
                    d = yf.download(t, period="max", interval="1d", auto_adjust=True,
                                    progress=False, threads=False)
                    if isinstance(d.columns, pd.MultiIndex):
                        d.columns = d.columns.get_level_values(0)
                    s = d["Close"].dropna()
                    if len(s) < 60:
                        continue
                    s.index = pd.to_datetime(s.index).tz_localize(None)
                    cache[t] = {i.strftime("%Y-%m-%d"): float(v) for i, v in s.items()}
                except Exception:
                    continue
            CACHE.parent.mkdir(parents=True, exist_ok=True)
            CACHE.write_text(json.dumps(cache))
        except ImportError:
            pass
    for t in tickers:
        if t in cache and cache[t]:
            s = pd.Series(cache[t])
            s.index = pd.to_datetime(s.index)
            out[t] = s.sort_index()
    return out


def to_monthly(s: pd.Series) -> pd.Series:
    return s.resample("ME").last().dropna()


# --------------------------------------------------------------------- metrics
def metrics(curve: pd.Series, periods_per_year: int = 12) -> dict:
    curve = curve.dropna()
    if len(curve) < 3:
        return {"n": len(curve)}
    r = curve.pct_change().dropna()
    n = len(curve)
    total = curve.iloc[-1] / curve.iloc[0] - 1
    years = n / periods_per_year
    cagr = (curve.iloc[-1] / curve.iloc[0]) ** (1 / years) - 1 if years > 0 else float("nan")
    sd = r.std(ddof=1)
    sharpe = (r.mean() / sd * math.sqrt(periods_per_year)) if sd else 0.0
    cum = curve / curve.cummax()
    mdd = float(cum.min() - 1)
    return {"n": n, "total_pct": total * 100, "cagr_pct": cagr * 100,
            "sharpe": sharpe, "mdd_pct": mdd * 100,
            "start": curve.index[0].strftime("%Y-%m-%d"),
            "end": curve.index[-1].strftime("%Y-%m-%d"),
            "terminal": float(curve.iloc[-1])}


# ------------------------------------------------------------------- the engine
def run_portfolio(pf: dict, prices: dict[str, pd.Series]) -> pd.Series:
    """Replay a portfolio definition over monthly bars. Returns an equity curve.

    Signals use data through month t-1; trades execute at month t's close.
    """
    tickers = pf["weights"]
    need = list(tickers) + ([pf["filter_symbol"]] if pf.get("filter_symbol") else [])
    series = {t: to_monthly(prices[t]) for t in need if t in prices}
    missing = [t for t in need if t not in series]
    if missing:
        raise KeyError(f"{pf['name']}: missing price series {missing}")
    idx = None
    for s in series.values():
        idx = s.index if idx is None else idx.intersection(s.index)
    idx = idx.sort_values()
    if len(idx) < SMA_MONTHS + 12:
        raise ValueError(f"{pf['name']}: only {len(idx)} common months")
    px = pd.DataFrame({t: series[t].reindex(idx) for t in need}).ffill()

    cash = START_CASH
    shares = {t: 0.0 for t in tickers}
    curve, last_rebal = [], None
    filt = pf.get("filter_symbol")
    sma_n = pf.get("sma_months", SMA_MONTHS)
    prev_on = None          # local state — a function attribute here would leak
                            # across portfolios and across runs

    for i, dt in enumerate(idx):
        # ---- decide target book using data through i-1 only
        if filt and i >= sma_n:
            on = px[filt].iloc[i - 1] > px[filt].iloc[i - sma_n:i].mean()
        else:
            on = not filt
        if not on:
            target = {t: 0.0 for t in tickers}
        else:
            target = dict(tickers)

        do_rebal = (i == 0) or bool(pf.get("rebalance") == "monthly") or (on != prev_on)
        prev_on = on

        equity_before = cash + sum(shares[t] * px[t].iloc[i] for t in tickers)
        if do_rebal:
            for t in tickers:
                price = px[t].iloc[i]
                if not np.isfinite(price) or price <= 0:
                    continue
                tgt_val = equity_before * target[t]
                cur_val = shares[t] * price
                delta = tgt_val - cur_val
                if abs(delta) < 1e-9:
                    continue
                d_shares = delta / price
                cost = abs(delta) * COST_BP / 1e4
                cash -= delta + cost
                shares[t] += d_shares
            last_rebal = dt
        eq = cash + sum(shares[t] * px[t].iloc[i] for t in tickers)
        curve.append((dt, eq))
    s = pd.Series({d: v for d, v in curve}).sort_index()
    s.index = pd.DatetimeIndex(s.index)
    return s


# ------------------------------------------------------------------ state mgmt
def load_cfg() -> dict:
    return json.loads(CFG.read_text())


def cmd_init(refresh: bool) -> int:
    cfg = load_cfg()
    tickers = sorted({t for p in cfg["portfolios"]
                      for t in list(p["weights"]) + ([p["filter_symbol"]] if p.get("filter_symbol") else [])})
    prices = fetch_monthly(tickers, refresh=refresh)
    print(f"price series loaded: {len(prices)}/{len(tickers)} -> {sorted(prices)}")
    state = {"created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
             "config_version": cfg.get("version", 1),
             "inception": None, "portfolios": {}}
    for pf in cfg["portfolios"]:
        try:
            curve = run_portfolio(pf, prices)
        except Exception as e:
            print(f"  {pf['name']:<22} SKIP: {e}")
            continue
        state["portfolios"][pf["name"]] = {
            "label": pf.get("label", pf["name"]),
            "weights": pf["weights"], "filter_symbol": pf.get("filter_symbol"),
            "sma_months": pf.get("sma_months", SMA_MONTHS),
            "rebalance": pf.get("rebalance"),
            "start_cash": START_CASH,
            "curve": {d.strftime("%Y-%m-%d"): round(float(v), 2) for d, v in curve.items()},
        }
        state["inception"] = min(state["inception"], curve.index[0].strftime("%Y-%m-%d")) \
            if state["inception"] else curve.index[0].strftime("%Y-%m-%d")
        m = metrics(curve)
        print(f"  {pf['name']:<22} {m['start']}..{m['end']}  n={m['n']:>4}  "
              f"CAGR={m['cagr_pct']:>6.2f}%  Sharpe={m['sharpe']:>5.2f}  MDD={m['mdd_pct']:>7.2f}%  "
              f"term=${m['terminal']:>10,.0f}")
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=1))
    print(f"\nstate written: {STATE}")
    return 0


def cmd_report() -> int:
    if not STATE.exists():
        print("no state — run --init first")
        return 2
    st = json.loads(STATE.read_text())
    rows = []
    for name, p in st["portfolios"].items():
        s = pd.Series(p["curve"])
        s.index = pd.to_datetime(s.index)
        m = metrics(s.sort_index())
        rows.append((name, p["label"], m))
    rows.sort(key=lambda r: -r[2].get("sharpe", -9))
    print(f"\n{'portfolio':<22} {'CAGR%':>8} {'Sharpe':>7} {'MDD%':>8} {'total%':>9} {'terminal$':>11} {'mo':>5}")
    print("-" * 78)
    for name, label, m in rows:
        if m.get("n", 0) < 3:
            print(f"{name:<22} insufficient data")
            continue
        print(f"{name:<22} {m['cagr_pct']:>8.2f} {m['sharpe']:>7.2f} {m['mdd_pct']:>8.2f} "
              f"{m['total_pct']:>9.1f} {m['terminal']:>11,.0f} {m['n']:>5}")
    print("\nNOTE: all series are computed on their own available window, which is")
    print("NOT the same for every portfolio. Do not compare CAGR across portfolios")
    print("without first re-running them on a common window (see --common).")
    return 0


def cmd_common(start: str | None = None) -> int:
    """Re-report every portfolio on one common window."""
    if not STATE.exists():
        print("no state — run --init first")
        return 2
    st = json.loads(STATE.read_text())
    curves = {}
    for name, p in st["portfolios"].items():
        s = pd.Series(p["curve"]); s.index = pd.to_datetime(s.index)
        curves[name] = s.sort_index()
    common_start = max(s.index[0] for s in curves.values())
    common_end = min(s.index[-1] for s in curves.values())
    if start:
        common_start = max(common_start, pd.Timestamp(start))
    print(f"\n=== COMMON WINDOW {common_start.strftime('%Y-%m')} .. {common_end.strftime('%Y-%m')} ===")
    print(f"{'portfolio':<22} {'CAGR%':>8} {'Sharpe':>7} {'MDD%':>8} {'total%':>9} {'terminal$':>11} {'mo':>5}")
    print("-" * 78)
    rows = []
    for name, s in curves.items():
        w = s[s.index >= common_start]
        if len(w) < 3:
            continue
        m = metrics(w)
        rows.append((name, m))
    for name, m in sorted(rows, key=lambda r: -r[1]["sharpe"]):
        print(f"{name:<22} {m['cagr_pct']:>8.2f} {m['sharpe']:>7.2f} {m['mdd_pct']:>8.2f} "
              f"{m['total_pct']:>9.1f} {m['terminal']:>11,.0f} {m['n']:>5}")
    return 0


def cmd_html() -> int:
    if not STATE.exists():
        print("no state — run --init first")
        return 2
    st = json.loads(STATE.read_text())
    curves = {}
    for name, p in st["portfolios"].items():
        s = pd.Series(p["curve"]); s.index = pd.to_datetime(s.index)
        curves[name] = s.sort_index()
    start = max(s.index[0] for s in curves.values())
    rows = []
    for name, s in curves.items():
        w = s[s.index >= start]
        if len(w) < 3:
            continue
        rows.append((name, st["portfolios"][name]["label"], metrics(w), w))
    rows.sort(key=lambda r: -r[2]["sharpe"])
    # normalise all curves to 100 at the common start for a fair visual
    series_js = []
    for name, label, m, w in rows:
        norm = (w / w.iloc[0] * 100).round(2)
        series_js.append({"name": label,
                          "dates": [d.strftime("%Y-%m") for d in norm.index],
                          "values": [float(v) for v in norm.values]})
    table = "\n".join(
        f"<tr><td>{label}</td><td>{m['cagr_pct']:.2f}</td><td>{m['sharpe']:.2f}</td>"
        f"<td>{m['mdd_pct']:.2f}</td><td>${m['terminal']:,.0f}</td><td>{m['n']}</td></tr>"
        for name, label, m, w in rows)
    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Portfolio tracker</title>
<style>
body{{font-family:system-ui,sans-serif;margin:2rem;background:#0f1115;color:#e6e6e6}}
table{{border-collapse:collapse;margin:1rem 0}}th,td{{padding:.4rem .9rem;border-bottom:1px solid #2a2f3a;text-align:right}}
th:first-child,td:first-child{{text-align:left}}
.warn{{background:#33270f;border-left:4px solid #d9a13b;padding:.8rem 1rem;margin:1rem 0}}
svg{{background:#151922;border-radius:8px}}
</style></head><body>
<h1>Portfolio tracker — candidate options</h1>
<p>Common window: <b>{start.strftime('%Y-%m')}</b> onward. All curves normalised to 100 at that month.
Costs charged at 10bp one-way per rebalance leg.</p>
<div class="warn"><b>Research artifact, not advice.</b> These are backtests on free daily data.
No forward observations exist. High-turnover strategies were excluded by design because
measured fee drag was 6–9× their gross edge (PART13).</div>
<table><thead><tr><th>Portfolio</th><th>CAGR %</th><th>Sharpe</th><th>MaxDD %</th><th>Terminal $</th><th>Months</th></tr></thead>
<tbody>{table}</tbody></table>
<svg id="chart" width="1000" height="420"></svg>
<script>
const data={json.dumps(series_js)};
const svg=document.getElementById('chart'),W=1000,H=420,pad=50;
const allV=data.flatMap(s=>s.values),lo=Math.min(...allV),hi=Math.max(...allV);
const maxLen=Math.max(...data.map(s=>s.dates.length));
const x=i=>pad+i*(W-2*pad)/Math.max(1,maxLen-1), y=v=>H-pad-(v-lo)*(H-2*pad)/Math.max(1e-9,hi-lo);
const colors=['#4ea1ff','#57d38c','#f2b134','#e06c75','#b78cf7','#38bdf8','#f472b6'];
data.forEach((s,k)=>{{
  const pts=s.values.map((v,i)=>x(i)+','+y(v)).join(' ');
  const p=document.createElementNS('http://www.w3.org/2000/svg','polyline');
  p.setAttribute('points',pts);p.setAttribute('fill','none');
  p.setAttribute('stroke',colors[k%colors.length]);p.setAttribute('stroke-width','2');
  svg.appendChild(p);
  const t=document.createElementNS('http://www.w3.org/2000/svg','text');
  t.setAttribute('x',pad+6);t.setAttribute('y',pad+16+18*k);
  t.setAttribute('fill',colors[k%colors.length]);t.setAttribute('font-size','13');
  t.textContent=s.name;svg.appendChild(t);
}});
</script>
</body></html>"""
    REPORT_HTML.parent.mkdir(parents=True, exist_ok=True)
    REPORT_HTML.write_text(html)
    print(f"wrote {REPORT_HTML}  ({len(rows)} portfolios)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--common", action="store_true")
    ap.add_argument("--html", action="store_true")
    a = ap.parse_args()
    if a.init:
        return cmd_init(a.refresh)
    if a.common:
        return cmd_common()
    if a.html:
        return cmd_html()
    return cmd_report()


if __name__ == "__main__":
    raise SystemExit(main())
