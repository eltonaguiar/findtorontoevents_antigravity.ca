#!/usr/bin/env python3
"""fund_deep_dive.py — real-data comparison of index funds / ETFs / mutual funds.

Source: 2026-11-15_AM_profitability-plan/copilot-financial-review/market_prices.csv
(adjusted close, 2021-11-15..2026-11-13, ~1,254 daily returns). Computes per-fund:
CAGR, vol, true Sharpe, true Sortino, max drawdown, and NET-of-MER CAGR. Also builds
simple portfolios (100% equity, 60/40, 80/20, T-bill), net of the fund's own MER.
This is a BUYING analysis (beta), not an edge claim.

2026-11-23 corrections (see docs/edge_research/FUND_DEEP_DIVE_TODO_2026-11-23.md):
  A1/A2  Sharpe and Sortino are now (R - R_f)/risk with SGOV net CAGR as R_f.
         The old column survives as `ret_vol` because it is a fee-adjusted
         return/vol ratio, NOT Sharpe. Calling it Sharpe did not make it Sharpe.
  A4     SGOV's ratio is reported as cash (n/a), not 15.886.
  A5     Sortino used a downside-only denominator (dividing by the count of
         negative days), which inflates sigma_down. The correct target downside
         deviation divides by ALL n. Both are emitted so the delta is visible;
         `sortino` is the correct one.
  A6     net_cagr was additive (cagr - mer); now compounded (1+cagr)(1-mer)-1.
  A7     vol used the population stdev; now the sample stdev.
Paper only. Zero capital. Not investment advice.
"""
import csv, json, math, statistics as st
from datetime import datetime, timezone
from pathlib import Path

SRC = "2026-11-15_AM_profitability-plan/copilot-financial-review/market_prices.csv"
ANN = 252
CASH_KEY = "SGOV_adj"
# expense ratios (MER), decimal per year
MER = {"FZROX_adj": 0.0000, "FXAIX_adj": 0.00015, "VTSAX_adj": 0.0004,
       "SPY_adj": 0.000945, "VTI_adj": 0.0003, "BND_adj": 0.0003, "SGOV_adj": 0.0009}
LABEL = {"FZROX_adj": "Fidelity ZERO Total Market (index MF, 0.00%)",
         "FXAIX_adj": "Fidelity 500 Index (index MF, 0.015%)",
         "VTSAX_adj": "Vanguard Total Stock (index MF, 0.04%)",
         "SPY_adj": "SPDR S&P 500 ETF (0.0945%)",
         "VTI_adj": "Vanguard Total Market ETF (0.03%)",
         "BND_adj": "Vanguard Total Bond ETF (0.03%)",
         "SGOV_adj": "iShares 0-3mo T-bill ETF (0.09%)"}


def load():
    rows = list(csv.DictReader(open(SRC)))
    cols = [c for c in rows[0] if c.endswith("_adj")]
    ser = {c: [] for c in cols}
    dates = []
    for r in rows:
        ok = True
        vals = {}
        for c in cols:
            try:
                vals[c] = float(r[c])
            except Exception:
                ok = False
                break
        if ok:
            dates.append(r["date"])
            for c in cols:
                ser[c].append(vals[c])
    ret = {c: [ser[c][i] / ser[c][i - 1] - 1 for i in range(1, len(ser[c]))] for c in cols}
    return dates, ser, ret


def metrics(r, mer=0.0, ann=ANN):
    """Raw fee-adjusted statistics. Ratios are finalised by add_ratios()."""
    n = len(r)
    mu = st.mean(r)
    sd = st.stdev(r) if n > 1 else 0.0          # A7: sample, not population
    cagr = (math.prod(1 + x for x in r)) ** (ann / n) - 1 if n else 0
    net_cagr = (1 + cagr) * (1 - mer) - 1        # A6: compounded, not cagr-mer
    eq = 1.0
    peak = 1.0
    mdd = 0.0
    for x in r:
        eq *= (1 + x)
        peak = max(peak, eq)
        mdd = min(mdd, eq / peak - 1)
    return {
        "cagr_pct": round(cagr * 100, 2),
        "net_cagr_pct": round(net_cagr * 100, 2),
        "vol_pct": round(sd * math.sqrt(ann) * 100, 2),
        "max_dd_pct": round(mdd * 100, 2),
        "n": n,
        "_net_cagr": net_cagr, "_vol": sd * math.sqrt(ann),
        "_mu_ann": mu * ann, "_mer": mer, "_r": r, "_ann": ann,
    }


def add_ratios(m, rf):
    """A1/A2/A4/A5: true Sharpe and Sortino, excess of cash.

    rf is the annual cash return as a decimal (SGOV's own net CAGR). mar is the
    same rate expressed per-period, so downside deviation is measured against the
    cash hurdle rather than against zero.
    """
    vol, n, r, mer, ann = m["_vol"], m["n"], m["_r"], m["_mer"], m["_ann"]
    mar = (rf or 0.0) / ann
    dsd_all = math.sqrt(sum(min(0.0, x - mar) ** 2 for x in r) / n) if n else 0.0
    down = [x for x in r if x < 0]
    dsd_legacy = math.sqrt(sum(x * x for x in down) / len(down)) if down else 0.0
    m["ret_vol"] = round((m["_mu_ann"] - mer) / vol, 3) if vol else None
    m["sharpe"] = round((m["_net_cagr"] - rf) / vol, 3) if (vol and rf is not None) else None
    m["sortino"] = (round((m["_net_cagr"] - rf) / (dsd_all * math.sqrt(ann)), 3)
                    if (dsd_all and rf is not None) else None)
    m["sortino_legacy"] = (round((m["_net_cagr"] - rf) / (dsd_legacy * math.sqrt(ann)), 3)
                           if (dsd_legacy and rf is not None) else None)
    m["rf_pct"] = round(rf * 100, 2) if rf is not None else None
    for k in [k for k in list(m) if k.startswith("_")]:
        del m[k]
    return m


def portfolio(ret, weights, rebal=None, merblend=0.0):
    """Weighted daily returns.

    NOTE (plan item D1, NOT yet fixed): `rebal` is accepted for API compatibility
    but ignored — port[i]=sum(w*r_i) is a DAILY-rebalanced series, which harvests
    volatility and overstates a 60/40 versus buy-and-hold. The output is labelled
    daily-rebalanced until real rebalancing lands.
    """
    n = min(len(ret[c]) for c in weights)
    port = [0.0] * n
    for i in range(n):
        port[i] = sum(w * ret[c][i] for c, w in weights.items())
    return port, merblend


def main():
    dates, ser, ret = load()
    out = {"schema_version": 2,
           "generated_at": datetime.now(timezone.utc).isoformat(),
           "source": SRC, "period": [dates[0], dates[-1]],
           "n_days": len(ret[list(ret)[0]]),
           "corrections": ["A1/A2 excess-of-cash Sharpe+Sortino", "A4 SGOV cash-labelled",
                           "A5 Sortino all-N denominator", "A6 compounded net CAGR",
                           "A7 sample stdev"],
           "rebalancing": "daily (rebal ignored -- plan item D1)",
           "funds": {}}

    # Pass 1: raw statistics. Pass 2: ratios need the cash hurdle from SGOV.
    base = {c: metrics(ret[c], MER[c]) for c in ret}
    rf = base[CASH_KEY]["net_cagr_pct"] / 100.0

    hdr = (f"{'fund':34s}{'CAGR':>8s}{'netCAGR':>9s}{'vol':>7s}"
           f"{'ret/vol':>9s}{'Sharpe':>14s}{'Sortino':>9s}{'MaxDD':>8s}")
    print(f"cash hurdle R_f = {rf*100:.2f}%/yr (SGOV net CAGR)\n")
    print(hdr)
    for c in ret:
        m = add_ratios(base[c], rf)
        if c == CASH_KEY:
            # A4: SGOV is the hurdle. Its own ratio is 0/0, so store null --
            # a number here (e.g. -0.006) is an artefact of float rounding and
            # would be read as a real Sharpe by any consumer of this JSON.
            m["sharpe"] = None
            m["sortino"] = None
            m["ratio_note"] = "cash hurdle (R_f); Sharpe/Sortino undefined"
        out["funds"][c] = m
        label = "n/a (cash)" if c == CASH_KEY else str(m["sharpe"])
        print(f"{LABEL[c][:33]:34s}{m['cagr_pct']:8.2f}{m['net_cagr_pct']:9.2f}"
              f"{m['vol_pct']:7.2f}{str(m['ret_vol']):>9s}{label:>14s}"
              f"{str(m['sortino']):>9s}{m['max_dd_pct']:8.2f}")

    print("\nPortfolios (DAILY-rebalanced, net of blended MER):")
    ports = {
        "100% SPY (SP500)": ({"SPY_adj": 1.0}, 0.000945),
        "100% VTI (total mkt)": ({"VTI_adj": 1.0}, 0.0003),
        "80/20 SPY/BND": ({"SPY_adj": 0.8, "BND_adj": 0.2}, 0.8 * 0.000945 + 0.2 * 0.0003),
        "60/40 SPY/BND": ({"SPY_adj": 0.6, "BND_adj": 0.4}, 0.6 * 0.000945 + 0.4 * 0.0003),
        "100% SGOV (T-bill)": ({"SGOV_adj": 1.0}, 0.0009),
    }
    out["portfolios"] = {}
    for name, (w, mer) in ports.items():
        p, _ = portfolio(ret, w, merblend=mer)
        m = add_ratios(metrics(p, mer), rf)
        if set(w) == {CASH_KEY}:
            m["sharpe"] = None
            m["sortino"] = None
            m["ratio_note"] = "cash hurdle (R_f); Sharpe/Sortino undefined"
        out["portfolios"][name] = m
        # A4: the 100%-cash portfolio IS the hurdle; a Sharpe against itself is
        # 0/0 and meaningless, so label it instead of printing -0.006.
        is_cash = set(w) == {CASH_KEY}
        label = "n/a (cash)" if is_cash else str(m["sharpe"])
        print(f"{name:34s}{m['cagr_pct']:8.2f}{m['net_cagr_pct']:9.2f}"
              f"{m['vol_pct']:7.2f}{str(m['ret_vol']):>9s}{label:>14s}"
              f"{str(m['sortino']):>9s}{m['max_dd_pct']:8.2f}")

    Path("reports").mkdir(exist_ok=True)
    Path("reports/fund_deep_dive.json").write_text(json.dumps(out, indent=2) + "\n")
    print("\nwrote reports/fund_deep_dive.json")


if __name__ == "__main__":
    main()
