# inspect-wt (deepAI) — final_v4 package (2026-11-14, finalized plan round)

**Worktree:** `.inspect-wt` · **Branch:** `audit/live-audit-2026-11-14`
**Round:** `final_v4/` — after reviewing **24h of financial-prediction updates** (100 remote commits:
18 meaningful / 82 auto-churn; `final_v3` decision round with shipped code; `final_v4` five peer
review bundles; PRs #773–#777; local tree = only my work, everything else May–June leftovers).

```
final_v4/inspect-wt/
├── README.md                        ← this file
├── 01_plan/PLAN_FINAL.md            ← finalized 4-phase plan (measurement truth → QA gates →
│                                       candidates → forward certification), risk register, non-goals
├── 02_qa/QA_PLAN.md                 ← QA gates: PnL=0% validated against real market data
│                                       (open→closed & open→current windows), blank-field flagger
│                                       (open + recently-closed priority), exit replay, cross-surface
├── 03_risk_management/
│   ├── risk_management.html         ← ★ STANDALONE REVIEW PAGE: backtests, stress tests, VaR/ES,
│   │                                   Kelly sizing, probability-of-success table, overlay verdicts
│   ├── make_risk_page.py            ← regenerates the page (runs the bootstrap too)
│   ├── backtest_results.json        ← MF/ETF rotation backtest, 165 months, 11 Yahoo symbols
│   ├── risk_stats_extra.json        ← variant-C Kelly/bootstrap risk stats
│   └── yahoo_monthly.json           ← raw price data (fetched 2026-11-14)
└── 04_peer_crosscheck/              ← subagent reviews of my plan/QA + proposed edits
```

## The three answers this package delivers

### 1. Finalized plan (`01_plan/`)
Adopts the peers' shipped fixes (stop-fill model, per-class 3× cost gate, gap-aware fill — verified in
`final_v3/README.md`) and the focus decision, adds what was missing: **my QA gates as a CI requirement,
the variant-C equity pilot under the pre-registered SPY gate, and an explicit probability/risk
treatment for every candidate.** Phase order: measurement truth (B1/B4/B5/B7/B9) → QA gates →
candidates → forward-only certification (T2 ∧ v3 ∧ cost gate, weekly pre-registered runs, kill criteria).

### 2. QA plan (`02_qa/`) — the PnL=0% validator
Every stored `pnl_pct==0`/blank on **OPEN and recently-closed** rows is independently repriced:
open→closed (when `closed_at`) and open→current (when open), by class-sourced market data
(Binance/Yahoo/Stooq/open.er-api), with a reasonability band `max(0.25%, 3σ_class)`; price moved
>1% while stored==0 → `ZERO_PNL_MISMATCH` (blocks money-ready at >2% rate). Blank fields →
`BLANK_<field>_OPEN/RECENT/HIST`, **never coerced to 0** (that coercion is the current fake-zero
factory). Plus exit-reasonableness replay (B4/TP-claim checks) and cross-surface status conflicts.

### 3. Risk management + "solid picks" (`03_risk_management/`) — evidence, not adjectives
Real backtest (Yahoo 2011→2026, monthly, 165 months) of the **MF/ETF allocation sleeve** the user
asked for, plus the variant-C pilot risk math:
- **Sleeve (v1 primary):** CAGR **7.36%** net (7.20% after MF fee drag), Sharpe 0.57, MDD −26.7%,
  vs SPY 12.5%/0.88/−24.8%. **Bear defense is the product:** 2022 −6.2% vs SPY −19.5%,
  COVID −0.6% vs −19.9%; but 2018Q4 worse and full-cycle return loses to buy & hold — stated plainly.
- **Overlays tested honestly:** absolute-momentum filter **KEEP**; 12% vol target **neutral**;
  15% DD-stop **REJECTED** (Sharpe 0.57→0.15, whipsaw — reported like the peers' failed COT test);
  top-3 sensitivity = 2nd trial, disclosed, not adopted.
- **Variant-C pilot:** Kelly full **9.86%** → adopted ¼-Kelly **2.46%/trade**; bootstrap (4,000):
  P(forward total>0) **91.6%**, P(PF≥1.15) **71%**, median +95pp, 5–95% band −18→+216pp;
  maxDD at sizing median −1.2% / worst −4.4% bankroll; monthly VaR95 flagged small-sample.
- **Probability-of-success table** (explicit, falsifiable): sleeve beats cash+fees ≈85–90%,
  beats SPY full-cycle only ≈25–35%, pilot passes T2 ≈30–40%, crypto conditional ≈25–35%.
  Mutual funds: monthly allocation engine (NAV-clock reality adopted from peers), never an
  intraday pick class.

## Status
- Subagent reviews (plan cross-check + QA/risk methodology) land in `04_peer_crosscheck/` with
  `[MUST]/[SHOULD]/[NICE]` proposed edits; integration noted there after each round.
- Reproduce: `python 03_risk_management/make_risk_page.py` (regenerates page + bootstrap);
  walk-forward: `final_2026_11_14/inspect-wt/06_profitable_approach/walkforward_v6.py`.
