# 05 — Profitability Review: Are We on the Right Track?

**Scope:** `WIRED_IN/` (~21 timestamped folders of parallel agent research) + last 24–48h of `main` commits.
**Method:** three independent subagents read the conclusion layer, the per-asset-class evidence layer, and the forward-test/artifact layer in parallel. Findings synthesized below.

## 1. Bottom line

**Not on track to *proven alpha* — but on the right track to *knowing the truth*.**

Every agent report converges on the same negative result: **zero active strategies beat buy-and-hold after costs.** The process is now methodologically honest (proof protocol, DSR/PBO, walk-forward, forward ledger), but the *conclusion* is "no edge found — deploy passive beta only, forward-test one open question."

The single candidate worth a forward test is **BTC `sma200` trend** (`BTC_TREND200`): CAGR 58.62% vs 51.04% hold (+7.58pp), Sharpe 1.10 vs 0.93, max drawdown −63.6% vs −83.0%. But DSR 0.84 (< 0.95), single asset, one boom-bust cycle — **not statistically proven.**

## 2. Per-asset-class verdict

| Class | Best candidate | Metric (exact) | Benchmark | Verdict |
|---|---|---|---|---|
| **CRYPTO** | BTC `sma200` trend | CAGR 58.62% vs 51.04%, Sharpe 1.10 vs 0.93, DSR 0.84 | BTC hold | **NOT-PROVEN** (only wealth-beater) |
| **CRYPTO** | `prediction_market_consensus` | WR 89.89%, PF 24.5, **PBO 0.603** | BTC | REJECT (overfit) |
| **EQUITY** | `stocks_rsi2_pullback` / `eq-mom-lb12` | n=78, t=1.05; or in-sample PF 2.62 | SPY | FAIL / overfit |
| **ETF** | TAA rotation / Faber10 | Sharpe 0.88 vs 0.74 (in-sample); CAGR 8.33% vs 10.76% | SPY | UNDERPERFORMS (cuts DD only) |
| **MUTUAL_FUNDS** | FXAIX / SWTSX | ER 0.015–0.03% | SPY | PASS (beta only, fee noise) |
| **BOND** | TLT/BND sma200 | negative Sharpe, loses wealth | B&H | REJECT |
| **FOREX** | `ig_contrarian_sentiment` / copytrader | PF 0.66, WR 32.2%, MDD 82% | cash | ELIMINATED |
| **COMMODITY** | GLD sma200 / COT trend | 2.12 vs 2.01 (window-sensitive); COT DSR 1.0 (concentration artifact) | GLD | NOT-PROVEN / contaminated |
| **PENNY** | memecoin | PF 0.50 (1,869 trades) | — | ELIMINATED |
| **PREDICTION** | Kalshi/Polymarket copy | taker fee 3.5–6.3% of stake | — | ELIMINATED (structural) |

## 3. The proof protocol — and how much passes it

10 gates: no look-ahead → walk-forward WFE>0.6 → DSR≥0.95 / PBO≤0.10 → block-bootstrap >95% paths → full-friction PF≥1.15 → CI excludes zero → regime robustness → shuffle control → pre-registered forward n≥100 → reproducibility.

**Zero candidates pass any complete set.** The closest is `stocks_rsi2_pullback` ("fails only sample size", still fails the SPY gate).

## 4. Why everything fails (common causes)

1. **Overfitting / data-snooping** — 37,500 param combos on equity with no multiple-testing correction; PBO/DSR rarely computed.
2. **Look-ahead & data bugs** — TIME_EXIT forging, 134 forced pnl=0, EXPIRED→WON mislabel, 22,947 ghost rows, `resolution_method=None` on all 3,500 closed rows.
3. **Costs never modeled** — only one cost-gate script exists; the forward excess endpoint is **gross** of fees.
4. **Insufficient n** — BOND n=1, ETF n=1, FUTURES n=31.
5. **Survivorship / hindsight universe** — SPY/TLT/GLD chosen knowing they are the canonical trio.

## 5. Forward-test leg — the right track, but not yet proof

`tools/forward_tracker.py` is **methodologically the strongest artifact** in the tree: pre-registered plan, structurally refuses pre-2026-11-15 closes, fees charged net on the ledger, same-window class-beta benchmark, OF kill/promote interim verdicts. Two gaps:
- **Zero live trades** — proves nothing yet (needs ~2–3 yrs per rule at observed fire rates).
- **Excess-return is gross of fees** in both `forward_tracker.py` and `pick_excess.py` (P0-4).

Also: `pick_excess.py` shows CRYPTO book **−0.795pp (t −3.65)** vs BTC — the crypto book is actively underperforming, driven by `MomentumEMA`. That is a live negative result worth acting on now.

## 6. Red flags / disagreements across agents

- **Best candidate differs:** scratch-hippodraco → equity rsi2; finpredict → BTC sma200; hilarious-seer → BTC sma200+RSI2; finpredict-v4 → TAA rotation. **No consensus on the single path forward.**
- **Faber Sharpe contradiction:** 1.01 (finpredict-v4) vs 0.40 (hilarious-seer) vs 0.66 (buffy) — 1.01 is flagged "UNVERIFIED risk-overlay only".
- **Multiple-testing denominator inconsistent:** 23 vs 87 vs 163 vs 683 vs 37,500 — the DSR/Bonferroni gate can't be computed without a settled `n_trials`.
- **Gate-count drift:** "10 gates" vs "9+1" vs "11" across reports.
- **COT 93.8%** is confirmed rejected (concentration artifact), matching the existing project decision `cot_93_8_rejected_contaminated`.

## 7. Recommendation

1. **Run the full proof protocol on BTC `sma200` trend** — the only wealth-beating candidate. Settle it.
2. **Fix the net-excess bug (P0-4)** before trusting any forward result.
3. **Reconcile `n_trials`** (one canonical multiple-testing denominator) so DSR/PBO gates are computable.
4. **Pivot the dashboard to passive beta** (FXAIX/SWTSX, or a volatility-targeted 60/40) with an explicit benchmark, and **publish the negative active result** — this is the honest deployable state.
5. **Kill `MomentumEMA`** (live crypto shortfall, t −3.65) per the existing constraint `kill_tlt_bnd_strong_buy_below_200dma`-style rule.

**One-line verdict:** the *process* (proof protocol + forward ledger + honest negative diagnosis) is now correct; the *alpha* is not there yet — passive beta is the only money-ready allocation, and BTC sma200 is the one open question left to forward-test.
