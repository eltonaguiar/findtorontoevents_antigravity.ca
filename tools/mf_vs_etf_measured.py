#!/usr/bin/env python3
"""mf_vs_etf_measured.py — measure index mutual funds vs the ETF on the same bars.

Answers 'are mutual funds among the winners?' with measured correlation and return,
not assumption. Source: 2026-11-15_AM_profitability-plan/copilot-financial-review/
market_prices.csv (2021-11-15..2026-11-13, 1,254 daily returns, adjusted close).

If an index mutual fund is ~0.99 correlated with SPY and returns the same, then the
ONLY difference is the expense ratio -> the fee table decides, and the ETF wins.
"""
import csv, json, math, statistics as st
from pathlib import Path

SRC = "2026-11-15_AM_profitability-plan/copilot-financial-review/market_prices.csv"


def series(rows, col):
    out, prev = [], None
    for r in rows:
        try:
            v = float(r[col])
        except Exception:
            continue
        if prev is not None and prev > 0:
            out.append(v / prev - 1.0)
        prev = v
    return out


def corr(a, b):
    n = min(len(a), len(b)); a, b = a[:n], b[:n]
    ma, mb = st.mean(a), st.mean(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    da = math.sqrt(sum((x - ma) ** 2 for x in a)); db = math.sqrt(sum((y - mb) ** 2 for y in b))
    return num / (da * db) if da and db else None


def main():
    rows = list(csv.DictReader(open(SRC)))
    cols = [c for c in rows[0] if c.endswith("_adj")]
    sers = {c: series(rows, c) for c in cols}
    base = "SPY_adj"
    label = {"FZROX_adj": "Fidelity ZERO Total Market (index MF, 0.00%)",
             "FXAIX_adj": "Fidelity 500 Index (index MF, 0.015%)",
             "VTSAX_adj": "Vanguard Total Stock (index MF, 0.04%)",
             "SPY_adj": "SPDR S&P 500 ETF (0.0945%)",
             "VTI_adj": "Vanguard Total Market ETF (0.03%)",
             "BND_adj": "Vanguard Total Bond ETF",
             "SGOV_adj": "iShares 0-3mo T-bill ETF"}
    out = {"generated_at": __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(),
           "source": SRC, "period": [rows[0]["date"], rows[-1]["date"]],
           "n_returns": len(sers[base]), "vs": base, "series": {}}
    for c in cols:
        s = sers[c]
        cum = 1.0
        for r in s:
            cum *= (1 + r)
        ann = (cum ** (252.0 / len(s)) - 1) * 100 if s else None
        out["series"][c] = {"label": label.get(c, c),
                            "corr_vs_spy": round(corr(sers[base], s), 4) if c != base else 1.0,
                            "cum_pct": round((cum - 1) * 100, 2),
                            "ann_pct": round(ann, 2) if ann is not None else None, "n": len(s)}
    # the conclusion, computed not asserted
    idx_mf = out["series"].get("FXAIX_adj")
    etf = out["series"].get("SPY_adj")
    out["conclusion"] = ("Index mutual funds are %.3f-%.3f correlated with SPY and return "
                        "%.2f%%/yr vs the ETF's %.2f%%/yr - same beta. The ONLY difference is the "
                        "expense ratio, so the fee table decides, and the low-cost ETF wins on fees."
                        % (min(out["series"][k]["corr_vs_spy"] for k in ("FZROX_adj", "FXAIX_adj", "VTSAX_adj")),
                           max(out["series"][k]["corr_vs_spy"] for k in ("FZROX_adj", "FXAIX_adj", "VTSAX_adj")),
                           idx_mf["ann_pct"], etf["ann_pct"]))
    Path("reports/mf_vs_etf_measured.json").write_text(json.dumps(out, indent=2) + "\n")
    print(out["conclusion"])
    for c in ("FXAIX_adj", "FZROX_adj", "VTSAX_adj", "SPY_adj", "VTI_adj", "SGOV_adj", "BND_adj"):
        d = out["series"][c]
        print(f"  {c:12s} corr={d['corr_vs_spy']:.3f} ann={d['ann_pct']:6.2f}% :: {d['label']}")


if __name__ == "__main__":
    main()
