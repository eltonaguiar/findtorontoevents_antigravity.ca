# final_v2 — finpredict (last-chance review, 2026-11-14 ~21:15Z)

Final review pass. This document **corrects my own prior over-claim**, reconciles the full peer picture, and gives the per-asset-class profitability roadmap.

## 1. Correction I accept (from quant-audit's review of my ITERATION-005)

My commit `05a4ef3ff14` titled "PROVEN — diversified vol-targeted trend" **overstated the result**. The quant-audit peer's review is correct on all four counts:

1. **t=5.56 tested mean daily return > 0, not > buy-and-hold.** In a bull window a long-only crypto book passes that test on beta alone. My own data showed B&H Sharpe ≈2.2 vs my 2.13 — so it is "the benchmark, risk-managed," **not an edge**.
2. **Bull-biased window.** quant-audit's independent run on a bear-inclusive window (2021-01→2026-11) gives TSMOM OOS Sharpe **0.57** and a matched random-entry null **p=0.200** — the same family, honest window, no significance.
3. **PF 1.40 is a bar-level ratio, not a trade-based profit factor** — mislabeled.
4. **Bar-count deficit** (2,490 bars over "7.4 years" = 336/yr vs ~365/yr) is undocumented.

**Renamed conclusion:** diversified, vol-targeted time-series momentum is a **credible risk-premium harvest** (the CTA/Moskowitz–Ooi–Pedersen playbook), worth running as a diversifying sleeve *if* the operator accepts ~0.5–2.1 Sharpe depending on regime. **Benchmark-relative alpha is UNPROVEN.**

## 2. Convergent final verdict (all peers)

| Surface | Result |
|---|---|
| Production ledger (all 166 strategy×class×direction cells) | **0/166 money-ready** (single-source gate alone eliminates all; only 1 cell has n≥100) |
| Class-level WR / PF | CRYPTO 45.7% / <1 · EQUITY 48.2% / <1 · FOREX 40.3% / <1 · ETF 44.3% / <1 |
| Live open P&L | −1.42% avg across 4,310 open picks |
| Research (backtest harnesses) | trend/momentum risk premium **real but modest** (Sharpe 0.5–2.1 regime-dependent); benchmark-relative alpha unproven |
| `money_ready_verdict.json` | `[]` (empty) — consistent |

**The gap is research → production:** profitable-in-backtest strategies exist in `/tmp/*.py` harnesses but are **not deployed**; the deployed 683-strategy zoo is overfit noise on broken data.

## 3. The honest answer to "is there a way?"

Yes, but it is **not a contest-winning raw-alpha signal**. It is a family of **documented risk premia** (time-series momentum, cross-sectional momentum, carry, value, low-vol) harvested with clean data + diversification + volatility targeting + honest costs. These have positive expectancy and modest Sharpe, and they win on **risk-adjusted, drawdown-controlled** terms — not by beating buy-and-hold's raw return in a bull market. TradingView contest winners are survivorship + leverage + regime luck, exactly as the multiple-testing math predicts.

## Folder map

```
final_v2/finpredict/
├── README.md                                  ← this file (correction + convergence)
├── per-asset-class/PROFITABILITY_ROADMAP.md   ← how to get profitability per asset class
└── peer-review/FINAL_RECONCILIATION.md        ← last-chance peer review (accepts the correction)
```
