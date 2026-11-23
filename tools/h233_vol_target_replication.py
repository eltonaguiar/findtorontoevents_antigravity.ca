"""H-233: does the vol-target 60/40 advantage survive on a disjoint window?

Pre-registered at plans/2026-11-23-prereg-H-233-vol-target-replication.md and filed in
reports/hypothesis_registry.json BEFORE this file was run.

Why this exists: C-014 claims vol-targeting a 60/40 book lifts CAGR 7.85% -> 9.28%, Sharpe
0.750 -> 0.895 and cuts max drawdown -31.42% -> -22.37%, with independent_runs = 0. That
claim is currently the only "stable rung" in reports/asset_class_risk_reward_ladder_2026-11-23.md,
so it gets a replication test with the decision rule fixed in advance.

Disclosure: the holdout is NOT virgin. C-014 already used 2005-2026 in aggregate, so this
is a REPLICATION on a disjoint window, not out-of-sample evidence. What pre-registration
buys is that I cannot pick the sub-window, the statistic or the rebalance convention after
seeing which choice flatters the rule.

Reuses vol_target() and perf() from tools/vol_target_vs_hold.py so the construction is the
same code that produced C-014, not a reimplementation.

Usage
  python3 tools/h233_vol_target_replication.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vol_target_vs_hold import perf, vol_target, TRADING_DAYS  # noqa: E402

TARGET = 0.10
LOOK = 60
CAP = 2.0
COST_BP = 5.0
WINDOWS = {
    "A_development": ("2005-01-03", "2015-12-31"),
    "B_holdout": ("2016-01-01", "2026-11-20"),
    # Diagnostic only, never an acceptance window: this is C-014's full sample, run so the
    # reimplementation can be checked against the original artifact's numbers.
    "FULL_reproduction": ("2005-01-03", "2026-11-20"),
}
ACCEPTANCE_WINDOWS = ("A_development", "B_holdout")
N_BOOT = 10_000
BLOCK = 20
RNG_SEED = 233


def download(start: str, end: str) -> pd.DataFrame:
    import yfinance as yf

    raw = yf.download(["SPY", "TLT"], start=start, end=end, auto_adjust=True, progress=False)
    close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]]
    return close.dropna(how="all")


def rebalanced_book(rets: pd.DataFrame, weights: dict[str, float], freq: str | None,
                    cost_bp: float) -> pd.Series:
    """60/40 with weights reset at `freq` (None = every day), full drift between resets.

    Turnover is charged on the weight change actually transacted, so a daily reset charges
    the drift back plus nothing spurious, and a monthly reset charges one bigger trade a
    month. That is the granularity difference C-020 found, priced honestly.
    """
    idx = rets.index
    tgt = pd.Series(weights, dtype=float)
    cur = tgt.copy()
    out = []
    prev_bucket = None
    for d, row in rets.iterrows():
        bucket = "daily" if freq is None else d.to_period(freq)
        if bucket != prev_bucket:
            transacted = float((cur - tgt).abs().sum()) if prev_bucket is not None else 1.0
            cost = transacted * cost_bp / 1e4
            cur = tgt.copy()
            prev_bucket = bucket
        else:
            cost = 0.0
        r = float((cur.fillna(0.0) * row.fillna(0.0)).sum()) - cost
        out.append(r)
        if row.notna().all():
            grown = cur * (1.0 + row)
            s = grown.sum()
            if s > 0:
                cur = grown / s
    return pd.Series(out, index=idx, name="book")


def delta_ce_block_bootstrap(vt: pd.Series, plain: pd.Series, n_boot: int = N_BOOT,
                             block: int = BLOCK, seed: int = RNG_SEED) -> dict:
    """Paired block bootstrap CI on CE(vol-target) - CE(plain).

    Block resampling rather than iid because both series are daily and vol clustering is
    the very effect under test; iid resampling would understate the interval.
    """
    j = pd.concat([vt.rename("vt"), plain.rename("plain")], axis=1).dropna()
    a = j["vt"].to_numpy()
    b = j["plain"].to_numpy()
    n = len(a)
    if n < block * 3:
        return {"error": "insufficient observations", "n": n}

    def ce(x: np.ndarray) -> float:
        return float(x.mean() * TRADING_DAYS - 0.5 * x.var() * TRADING_DAYS)

    point = ce(a) - ce(b)
    rng = np.random.default_rng(seed)
    n_blocks = int(np.ceil(n / block))
    deltas = np.empty(n_boot)
    for i in range(n_boot):
        starts = rng.integers(0, n, size=n_blocks)
        idx = np.concatenate([(s + np.arange(block)) % n for s in starts])[:n]
        deltas[i] = ce(a[idx]) - ce(b[idx])
    lo, hi = np.percentile(deltas, [2.5, 97.5])
    return {
        "n_days": int(n),
        "delta_ce_pct": round(point * 100, 4),
        "ci95_low_pct": round(float(lo) * 100, 4),
        "ci95_high_pct": round(float(hi) * 100, 4),
        "n_boot": n_boot,
        "block": block,
        "seed": seed,
        "p_boot_le_zero": round(float((deltas <= 0).mean()), 4),
    }


def evaluate(rets: pd.DataFrame, base_label: str, freq: str | None, out: dict) -> dict:
    book = rebalanced_book(rets, {"SPY": 0.60, "TLT": 0.40}, freq, COST_BP)
    vt, lev = vol_target(book, TARGET, LOOK, CAP, COST_BP)
    per_window = {}
    for wname, (s, e) in WINDOWS.items():
        m = (book.index >= pd.Timestamp(s)) & (book.index <= pd.Timestamp(e))
        bk = book[m]
        vt_w = vt[(vt.index >= pd.Timestamp(s)) & (vt.index <= pd.Timestamp(e))]
        if len(bk) < 300 or len(vt_w) < 300:
            per_window[wname] = {"error": "insufficient observations", "n_book": len(bk)}
            continue
        p_book = perf(bk, f"{base_label} plain")
        p_vt = perf(vt_w, f"{base_label} vol-target {TARGET:.0%}")
        bt = delta_ce_block_bootstrap(vt_w, bk)
        per_window[wname] = {
            "plain": p_book,
            "vol_target": p_vt,
            "delta_ce": bt,
            "delta_cagr_pp": round(p_vt.get("cagr_pct", 0) - p_book.get("cagr_pct", 0), 2),
            "delta_sharpe": round(p_vt.get("sharpe", 0) - p_book.get("sharpe", 0), 3),
            "delta_maxdd_pp": round(p_vt.get("max_drawdown_pct", 0) - p_book.get("max_drawdown_pct", 0), 2),
            "maxdd_not_worse": p_vt.get("max_drawdown_pct", -1e9) >= p_book.get("max_drawdown_pct", 0),
        }
    out["evaluations"][base_label] = {
        "rebalance": "daily" if freq is None else f"every {freq}",
        "mean_leverage": round(float(lev.mean()), 3),
        "max_leverage": round(float(lev.max()), 3),
        "mean_annual_turnover": round(float(lev.diff().abs().dropna().sum()) / (len(lev) / TRADING_DAYS), 2),
        "windows": per_window,
    }
    return out["evaluations"][base_label]


def main() -> None:
    out: dict = {
        "hypothesis": "H-233",
        "prereg": "plans/2026-11-23-prereg-H-233-vol-target-replication.md",
        "question": "does the vol-target 60/40 advantage replicate on a disjoint window?",
        "assumptions": {"target": TARGET, "lookback": LOOK, "cap": CAP, "cost_bp_per_unit": COST_BP,
                        "signal_lag_days": 1, "windows": WINDOWS},
        "data_disclosure": "holdout is NOT virgin: C-014 already used 2005-2026 in aggregate",
        "evaluations": {},
    }

    px = download("2005-01-01", "2026-11-21")
    rets = px.pct_change().dropna()
    print(f"data {px.index[0].date()} -> {px.index[-1].date()} rows={len(px)} cols={list(px.columns)}")
    out["data"] = {"start": str(px.index[0].date()), "end": str(px.index[-1].date()), "rows": int(len(px))}

    primary = evaluate(rets, "60/40 daily", None, out)
    evaluate(rets, "60/40 monthly", "M", out)

    b = primary["windows"]["B_holdout"]
    a = primary["windows"]["A_development"]
    crit = {
        "1_delta_ce_positive": b.get("delta_ce", {}).get("delta_ce_pct", -1) > 0,
        "2_ci_low_above_zero": b.get("delta_ce", {}).get("ci95_low_pct", -1) > 0,
        "3_maxdd_not_worse": b.get("maxdd_not_worse", False),
        "4_sign_agreement": (a.get("delta_ce", {}).get("delta_ce_pct", 0) > 0) ==
                            (b.get("delta_ce", {}).get("delta_ce_pct", 0) > 0),
    }
    if all(crit.values()):
        verdict = "REPLICATED"
    elif not crit["2_ci_low_above_zero"]:
        verdict = "REFUTED_OOS"
    else:
        verdict = "INCONCLUSIVE"
    out["verdict"] = {"label": verdict, "criteria": crit,
                      "kill_rule_applied": "criterion 2 failing => REFUTED_OOS per pre-registration"}

    print(f"\n{'window':<16}{'sleeve':<26}{'CAGR':>8}{'vol':>8}{'SR':>7}{'MDD':>9}{'CE':>8}")
    for wn in WINDOWS:
        for k in ("plain", "vol_target"):
            s = primary["windows"][wn].get(k, {})
            if "cagr_pct" in s:
                print(f"{wn:<16}{s['label']:<26}{s['cagr_pct']:>7.2f}%{s['vol_pct']:>7.2f}%"
                      f"{s['sharpe']:>7.3f}{s['max_drawdown_pct']:>8.2f}%{s['ce_pct']:>7.2f}%")
    for wn in WINDOWS:
        d = primary["windows"][wn].get("delta_ce", {})
        print(f"\n{wn}  dCE {d.get('delta_ce_pct')}pp  CI95 [{d.get('ci95_low_pct')}, {d.get('ci95_high_pct')}]"
              f"  p(<=0)={d.get('p_boot_le_zero')}  n={d.get('n_days')}")
    print("\ncriteria:", json.dumps(crit))
    print("VERDICT:", verdict)

    Path("reports").mkdir(exist_ok=True)
    p = Path("reports/h233_vol_target_replication_2026-11-23.json")
    p.write_text(json.dumps(out, indent=2) + "\n")
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
