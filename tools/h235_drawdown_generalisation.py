"""H-235: does the drawdown reduction survive outside the 2005-2026 US book?

Pre-registered at plans/2026-11-23-prereg-H-235-drawdown-generalisation.md and filed in
reports/hypothesis_registry.json before this file was run.

Context: H-233 refuted the RETURN half of vol-targeted 60/40 (dCE flips sign between
sub-periods, both CIs contain zero) but the DRAWDOWN half replicated in both windows of the
US 2005-2026 sample. H-233's own limitation note said the obvious next test is a book outside
that sample. This is that test: the same rule on (a) a pre-2005 US window and (b) a
non-US 60/40 book.

What "the drawdown claim survives" means, fixed in advance: vol targeting produces a smaller
max drawdown than plain in BOTH books. dCE is reported as secondary, never used to rescue a
failed drawdown test.

Usage
  python3 tools/h235_drawdown_generalisation.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vol_target_vs_hold import perf, vol_target, TRADING_DAYS  # noqa: E402

TARGET, LOOK, CAP, COST_BP = 0.10, 60, 2.0, 5.0

# Fixed before the run. Pre-2005 US is short by construction: TLT listed 2002-07-30, so there
# is no longer pre-2005 60/40 in these instruments. That limitation is disclosed, not hidden.
BOOKS = {
    "US_pre2005": {"legs": {"SPY": 0.60, "TLT": 0.40}, "start": "2002-07-30", "end": "2004-12-31"},
    "US_2005_2026_control": {"legs": {"SPY": 0.60, "TLT": 0.40}, "start": "2005-01-03", "end": "2026-11-20"},
    "INTL_exUS": {"legs": {"EFA": 0.60, "BWX": 0.40}, "start": "2007-05-01", "end": "2026-11-20"},
}

N_BOOT, BLOCK, SEED = 10_000, 20, 235


def download(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    import yfinance as yf

    raw = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)
    close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]]
    return close.dropna(how="all")


def rebalanced(close: pd.DataFrame, legs: dict[str, float]) -> pd.Series:
    rets = close.pct_change().dropna()
    tgt = pd.Series(legs, dtype=float)
    cur, out, prev = tgt.copy(), [], None
    for d, row in rets.iterrows():
        if d != prev:
            transacted = float((cur - tgt).abs().sum()) if prev is not None else 1.0
            cost = transacted * COST_BP / 1e4
            cur, prev = tgt.copy(), d
        else:
            cost = 0.0
        out.append(float((cur.fillna(0.0) * row.fillna(0.0)).sum()) - cost)
        if row.notna().all():
            grown = cur * (1.0 + row)
            s = grown.sum()
            if s > 0:
                cur = grown / s
    return pd.Series(out, index=rets.index, name="book")


def dce_bootstrap(vt: pd.Series, plain: pd.Series) -> dict:
    j = pd.concat([vt.rename("vt"), plain.rename("p")], axis=1).dropna()
    a, b = j["vt"].to_numpy(), j["p"].to_numpy()
    n = len(a)
    if n < BLOCK * 3:
        return {"error": "insufficient observations", "n": n}

    def ce(x):
        return float(x.mean() * TRADING_DAYS - 0.5 * x.var() * TRADING_DAYS)

    rng = np.random.default_rng(SEED)
    nb = int(np.ceil(n / BLOCK))
    deltas = np.empty(N_BOOT)
    for i in range(N_BOOT):
        st = rng.integers(0, n, size=nb)
        idx = np.concatenate([(s + np.arange(BLOCK)) % n for s in st])[:n]
        deltas[i] = ce(a[idx]) - ce(b[idx])
    lo, hi = np.percentile(deltas, [2.5, 97.5])
    return {"n_days": int(n), "delta_ce_pct": round((ce(a) - ce(b)) * 100, 4),
            "ci95_low_pct": round(float(lo) * 100, 4), "ci95_high_pct": round(float(hi) * 100, 4),
            "p_boot_le_zero": round(float((deltas <= 0).mean()), 4)}


def main() -> None:
    out: dict = {"hypothesis": "H-235",
                 "prereg": "plans/2026-11-23-prereg-H-235-drawdown-generalisation.md",
                 "question": "does the vol-target drawdown reduction survive on a pre-2005 or non-US book?",
                 "assumptions": {"target": TARGET, "lookback": LOOK, "cap": CAP,
                                 "cost_bp_per_unit": COST_BP, "books": BOOKS},
                 "books": {}}

    drawdown_wins, details = [], {}
    for name, cfg in BOOKS.items():
        px = download(list(cfg["legs"]), cfg["start"], cfg["end"])
        px = px.dropna()
        if len(px) < 150:
            out["books"][name] = {"error": "insufficient history", "rows": int(len(px))}
            print(f"{name}: insufficient history ({len(px)} rows) - skipped")
            continue
        book = rebalanced(px, cfg["legs"])
        vt, lev = vol_target(book, TARGET, LOOK, CAP, COST_BP)
        p_book, p_vt = perf(book, "plain"), perf(vt, "vol-target")
        dd_win = p_vt.get("max_drawdown_pct", -1e9) > p_book.get("max_drawdown_pct", 0)
        drawdown_wins.append(dd_win)
        details[name] = dd_win
        out["books"][name] = {"window": {"start": str(px.index[0].date()), "end": str(px.index[-1].date())},
                              "legs": cfg["legs"], "rows": int(len(px)),
                              "plain": p_book, "vol_target": p_vt,
                              "delta_ce": dce_bootstrap(vt, book),
                              "dd_improvement_pp": round(p_book.get("max_drawdown_pct", 0) - p_vt.get("max_drawdown_pct", 0), 2),
                              "drawdown_win": dd_win,
                              "mean_leverage": round(float(lev.mean()), 3)}
        print(f"\n{name}  {px.index[0].date()}..{px.index[-1].date()}  rows={len(px)}")
        for lbl, s in (("plain", p_book), ("vol-target", p_vt)):
            print(f"   {lbl:<11} CAGR {s['cagr_pct']:>6.2f}%  vol {s['vol_pct']:>6.2f}%  SR {s['sharpe']:>6.3f}"
                  f"  MDD {s['max_drawdown_pct']:>7.2f}%  CE {s['ce_pct']:>6.2f}%")
        d = out["books"][name]["delta_ce"]
        print(f"   dCE {d.get('delta_ce_pct')}pp CI95 [{d.get('ci95_low_pct')},{d.get('ci95_high_pct')}] "
              f"dd_improvement {out['books'][name]['dd_improvement_pp']}pp -> drawdown_win={dd_win}")

    tested = [k for k in BOOKS if k in out["books"] and "plain" in out["books"][k]]
    survivors = [k for k in tested if out["books"][k]["drawdown_win"]]
    if len(survivors) == len(tested):
        verdict = "SURVIVES"
    elif not survivors:
        verdict = "FAILS"
    else:
        verdict = "PARTIAL"
    out["verdict"] = {"label": verdict, "books_tested": tested, "drawdown_better_in": survivors,
                      "reading": ("max drawdown improved in every tested book" if verdict == "SURVIVES"
                                  else "drawdown benefit is book-specific, so it cannot be sold as a general rule")}
    print(f"\nbooks tested: {len(tested)} | drawdown improved in: {len(survivors)} -> {verdict}")

    Path("reports").mkdir(exist_ok=True)
    p = Path("reports/h235_drawdown_generalisation_2026-11-23.json")
    p.write_text(json.dumps(out, indent=2) + "\n")
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
