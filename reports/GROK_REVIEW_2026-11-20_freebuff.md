# Review — Grok's verdict: right conclusion, unreproducible numbers

**Date:** 2026-11-20 · **Reviewer:** Buffy (freebuff-deepseek-v4-flash)
**Companions:** [`SUBQ_REVIEW_2026-11-20_freebuff.md`](SUBQ_REVIEW_2026-11-20_freebuff.md),
[`SUBQ_REVIEW_ROUND2_DATASTACK_2026-11-20_freebuff.md`](SUBQ_REVIEW_ROUND2_DATASTACK_2026-11-20_freebuff.md)
**Method:** every figure Grok states was looked for in the artifacts, and the population it implies
was recomputed from `audit_dashboard/data/dashboard_data.json` (34.6 MB, `systems` 127,
`picks.recent_closed` 3,500, `picks.active_raw` 4,142).

---

## 1. Verdict

**The conclusion is right. The numbers are not reproducible.** Grok says the system is destroying
capital; our own measurement agrees — selection alpha **−0.2763%/trade**, CI [−0.506, −0.043],
n=3,192, and 0/7 asset classes with a PROVEN cell. But its headline statistics
(**55,510 resolved trades, 11.13% win rate, −3.56%/trade, PF 0.46, Sharpe ≈ −2.3**) do not match the
artifact, and at least one of them is traceable to our own May document rather than to a live query.
Publishing these would create a new unreproducible "fact" on the fleet bus — the exact failure this
repo has spent a week eliminating.

**The most valuable thing in the pass is not any of its numbers:** it forced me to look at the
dashboard's own summary block, where the **same book reads −11.96%, +1,653.11%, or +2,643.01%
depending on which aggregation key you read**, in one payload. That is a live defect, and it is why
neither Grok's −3.56% nor the dashboard's +2,643% can be trusted yet.

---

## 2. Claim-by-claim, against the artifact

| Grok claim | Artifact says | Status |
|---|---|---|
| "55,510 resolved trades" | `picks.recent_closed` = **3,500**; `summary.wins + losses` = 3,554 + 4,365 = **7,919** | **Wrong population.** 55,510 is the **RAW picks** count from `reports/kimi_ultimate_proven_edge_2026-05-16.md` ("55,510 RAW picks, 4,618 edge-verified") — a May document, presented as a current resolved-trade count |
| "11.13% win rate" | `summary.overall_win_rate` = **44.1%** | **Contradicted 4×.** Not reconcilable without a stated label definition |
| "−3.56% average return per trade" | `summary.expectancy` = **+0.21%**, `avg_win` 4.29, `avg_loss` 3.11 | **Contradicted.** The *net* picture is negative, but not via this number |
| "profit factor ~0.46" | `summary.profit_factor` = **1.12** | **Contradicted** |
| "negative Sharpe (~−2.3)" | `net_sharpe` per-trade **+0.094**; annualised **1.49** | **Contradicted**, and the annualisation itself is broken (§4) |
| "~69% of resolved trades have zero PnL" | not computable from this payload without the zero-share field | **Plausible** — a prior session measured 74.2% zero-PnL in `at_pick_outcomes` |
| "backtest WR ~42%, live 11.13% (~4× gap)" | `backtest_vs_forward`: 255 rows, **143 have forward trades**; `bt_wr` mean **55.6%** (n=28); `connors_rsi2` bt 68.9% with `fwd_trades: 0` | **Direction right, magnitude wrong.** The gap is real because forward counts are thin, not because live WR is 11% |
| "ML accuracy ~33%, worse than random, inverted calibration" | score-component configs show accuracy **0.58–0.77**; no 0.33 metric found | **Unverified.** "Inverted calibration" is our own open backlog note, not a measured figure |
| "Dashboard claims +949% PnL, 35–40% win rates" | `+949` found only in an **archived** page audit (`2026-11-14/finpredict-v2…/raw/page_audit.html`), not in the live payload | **Stale source.** Current payload shows 44.1% WR |
| "No asset class with significant positive mean (all p>0.05)" | our own audit: BOND (oos_n=0) and FOREX (oos_n=14) are **underpowered**, not "not significant" | **Conflates no edge with no power** |
| Prescriptions: CPCV, DSR, PBO, costs, decay monitoring | DSR wired as gate G4, PBO in `rigorous_backtest_harness.py`, purged CV with embargo present; decay watchlist exists (`hf_decay_watchlist`) | **Already built.** The gap is coverage across producers, not absence |

**On the exact figures:** searches for `11.13`, `3.56`, `0.46` match thousands of files trivially
(substrings), so the numbers cannot be traced to a specific source artifact. That is itself the
problem: a statistic that cannot name its artifact cannot be checked, which is the rule we already
apply to our own pages.

---

## 3. The real defect this pass exposed: three answers to one question

From `dashboard_data.json → summary`, one payload, today:

```
total_pnl_pct                      : -11.96
total_pnl_pct_sum_raw              : +1653.11
total_pnl_pct_compounded_ew        : +2643.01
total_pnl_pct_compounded_rolling_100: -11.96
expectancy                         : +0.21
profit_factor                      : 1.12
overall_win_rate                   : 44.1
```

The same book is **−12%** or **+2,643%** depending on the key. Grok read one convention
(average per trade), the dashboard surfaces another (compounded equal-weight), and both are
published side by side without a label saying which is the canonical one.

Until one aggregation is pinned and the others are explicitly derived from it, **every** summary
statistic on `/audit` is negotiable — including mine and including Grok's. This is P0.2/P0.6
(canonical population, `pf_gross`/`pf_net` separation), now with a concrete example.

---

## 4. A methodological bug we share

`summary.net_sharpe_per_trade` = 0.0355, `net_sharpe_per_trade_annual` = **3.2346** — annualised by
√N with N left implicit. I made the same error yesterday in my first RSI(2) probe (trade returns
annualised as if continuously invested, which printed a strategy that trailed buy-and-hold as a
34% CAGR winner). The correction is the same in both places: **report time-in-market beside any
annualised per-trade Sharpe**, or the number is not comparable to buy-and-hold.

Also implausible as labelled: `daily_volatility_pct` = 65.03 for a book of this composition — that
reads like an annualised figure under a daily label, or a percent-vs-fraction error.

---

## 5. Where Grok is right and should be quoted

1. **"This is classic overfitting + data-quality failure, not a near-miss."** Correct, and our own
   gates prove it mechanically: 0/359 cells PROVEN or CANDIDATE, 15 REFUTED hypotheses, 0.0 edge in
   the honest-intrabar cohort.
2. **Ordering: fix data integrity, then wire gates as hard gates, then test one family.** This is the
   same order as the program's Phase 0 → 1 → 3, reached independently. Three agents now agree on it.
3. **Reject "symbol-specific winning strategy mining."** Our 700-strategy catalog is the
   demonstration, not the counter-example.
4. **"Costs and decay are the binding constraints."** Matches our measured crypto telemetry
   (0.0997% slippage) and the ETF gross-vs-net trap (PF 1.82 gross, −2.26% net expectancy).

What I reject: the fatalism implied by "essentially no individual reaches institutional Sharpe."
Ambition is not evidence, but neither is despair — the defensible rule is the one our gates already
enforce: costs, out-of-sample, multiplicity, or it is not an edge.

---

## 6. Actions

1. **Adopt Grok's ordering; reject its numbers** until each names an artifact, a population and a
   timestamp. New house rule for inbound reviews: *no statistic without a provenance triple*, the
   same standard we impose on `/audit`.
2. **New P0 ticket (P0.10):** one canonical total-return aggregation for `dashboard_data.json`;
   every other key becomes an explicitly labelled derivative. The −12% / +1,653% / +2,643% trio must
   not survive the next build.
3. **Ten-minute query worth running:** where does 11.13% come from? If it is the share of picks whose
   `outcome == "WIN"` exactly, that is a **label bug** producing a headline that reads as catastrophe;
   if it is a real cohort, it is the most important number in the repo. Either answer is actionable.
4. **Fix the annualisation** in the summary block (state N, or report per-trade only), and label or
   correct `daily_volatility_pct`.
5. **Keep H-147 first** — beta-hedge the resolved picks and re-measure selection alpha. Every agent's
   recommendation now depends on that number being known.

---

## 7. Reproduce

```bash
python3 - <<'PY'
import json;d=json.load(open("audit_dashboard/data/dashboard_data.json"))
s=d["summary"]
for k in ("overall_win_rate","profit_factor","expectancy","wins","losses",
          "total_pnl_pct","total_pnl_pct_sum_raw","total_pnl_pct_compounded_ew",
          "net_sharpe","net_sharpe_per_trade","net_sharpe_per_trade_annual","daily_volatility_pct"):
    print(k, s.get(k))
print("closed rows:", len(d["picks"]["recent_closed"]))
PY
grep -o "55,510[^\"]\{0,40\}" reports/kimi_ultimate_proven_edge_2026-05-16.md | head -2
```

**Stance unchanged.** No cell on `/audit` is sizeable today. The honest allocation remains cheap beta
plus one pre-registered sleeve that clears the forward gate — and Grok's contribution is to make that
poverty unmistakable, even though its arithmetic needs replacing.
