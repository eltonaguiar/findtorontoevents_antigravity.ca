# Picks Data Review — 2026-11-15 exports

**Inputs:** `antigravity_active_picks_2026-11-15.csv` (11 rows), `..._all_picks...` (1,664), `..._closed_picks...` (1,653)
**Tool:** `proof/picks_audit.py --dir ~/Downloads` (reproduces every number below; `--json` for machine use)

## Verdict

**Not deployable at retail cost.** Gross PF is 1.126, but breakeven is ~0.15%/trade round-trip and crypto taker fees alone are 0.10–0.20% before slippage. Two structural findings matter more than the headline: 39% of positions exit **outside their bracket**, and 95% of trades are net-negative as a group with a handful of winners carrying the book.

## 1. Composition

| Class | n | Share | WR | Avg | Median | PF |
|---|---|---|---|---|---|---|
| CRYPTO | 1,579 | 95.5% | 44.0% | +0.174% | **−0.99%** | 1.130 |
| FOREX | 52 | 3.1% | 38.5% | +0.059% | 0.00% | 1.294 |
| COMMODITY | 7 | 0.4% | 42.9% | −0.509% | −1.17% | 0.663 |
| ETF | 7 | 0.4% | 28.6% | −0.581% | −1.05% | 0.400 |
| EQUITY | 5 | 0.3% | 60.0% | +0.550% | +0.92% | 3.311 |
| BOND | 3 | 0.2% | 33.3% | −0.737% | −1.10% | 0.056 |

Mean positive, **median −0.99%** → right-skewed, outlier-dependent. Crypto is 1,280/1,579 = **81% one strategy** (`luxalgo_confluence`). Every non-crypto class except FOREX is too small to conclude anything (n ≤ 7).

## 2. Cost sensitivity — the cliff

| Cost/trade | ALL avg | ALL PF | CRYPTO avg | CRYPTO PF |
|---|---|---|---|---|
| 0.05% | +0.114% | 1.086 | +0.124% | 1.091 |
| 0.10% | +0.064% | 1.047 | +0.074% | 1.053 |
| **0.15%** | **+0.014%** | **1.010** | **+0.024%** | **1.017** |
| 0.20% | −0.036% | 0.974 | −0.026% | 0.982 |
| 0.30% | −0.136% | 0.907 | −0.126% | 0.916 |

**Breakeven ≈ 0.164% (all) / 0.174% (crypto).** There is **no fee, cost or slippage column** in any export, so all PnL is gross. Proof step 5 (friction) cannot be evaluated from this data.

## 3. Concentration

- top 5 winners = 20% of net · top 10 = 38% · top 25 = **83%**
- **top 50 winners sum to 146% of net** → the remaining ~1,529 trades are collectively ≈ −127 pts
- excluding the top 10 winners: total +170.5 pts, avg +0.109%

The book is a thin edge with a fat right tail, not a broad statistical edge.

## 4. Exit mix — the real defect

| Exit | n | Share | WR | Avg | PF |
|---|---|---|---|---|---|
| **FORCE_CLOSED** | 616 | **39.0%** | 40.4% | **+0.021%** | 1.011 |
| SL_HIT | 512 | 32.4% | 2.5% | −1.757% | 0.018 |
| TP_HIT | 387 | 24.5% | 100% | +2.936% | ∞ |
| TIME_EXIT | 61 | 3.9% | 70.5% | +0.387% | 4.814 |

`FORCE_CLOSED` is **a label, not an action** — `audit_trail/quality_gates.py:3632 _canonical_exit_reason` assigns it when a WON/LOST pick's exit price sits >0.5% away from *both* TP and SL. So 39% of crypto positions are being closed **at neither bracket**, and that bucket contributes exactly zero (avg +0.02%, coin-flip WR).

**Excluding FORCE_CLOSED:** n=963, WR 46.2%, avg +0.272%, **PF 1.283**, payoff 1.49, breakeven WR 40.1% vs actual 46.2% → a **6.1-point margin**, still +0.172% after 10 bps.

So the strategy's bracket-resolved subset has a real margin; the force-close bucket is diluting it into breakeven. The bottleneck is exit discipline, not signal quality — the same conclusion the repo audit reached from the code side (F24/F25 stop-fill work).

## 5. Grade is monotonic — the one genuinely predictive column

| Grade | n | WR | Avg | PF |
|---|---|---|---|---|
| A | 26 | 69.2% | +1.190% | **2.567** |
| B | 998 | 44.8% | +0.248% | 1.176 |
| C | 527 | 43.3% | +0.044% | 1.036 |
| D | 28 | 3.6% | −0.977% | **0.193** |

Perfect A > B > C > D ordering across 1,579 trades. This is the strongest signal in the dataset and should drive filtering; grade A's n=26 is too small to size on alone, but the ordering is not noise.

## 6. Timeframe

| TF | n | WR | Avg | PF |
|---|---|---|---|---|
| INTRADAY | 1,412 | 44.1% | +0.183% | 1.139 |
| **SWING** | **134** | **35.1%** | **−0.450%** | **0.716** |
| POSITION | 33 | 72.7% | +2.292% | 3.290 |

**SWING is negative and still enabled.** POSITION looks excellent but n=33 is below any usable floor.

## 7. Strategies (n ≥ 30)

| Class | Strategy | n | WR | PF |
|---|---|---|---|---|
| CRYPTO | `luxalgo_confluence` | 1,280 | 42.9% | 1.125 |
| CRYPTO | `crypto_signal_engine` | 37 | **2.7%** | **0.140** |
| CRYPTO | `crypto_liquidity_wick_reversal_v1` | 43 | 58.1% | 1.495 |
| CRYPTO | `strong consensus (alpha_engine, luxalgo_filters)` | 46 | 54.3% | 1.486 |
| **FOREX** | **`forex_rsi2_mean_reversion`** | **35** | **48.6%** | **1.364** |

- `crypto_signal_engine` at **2.7% WR** is not weak, it is broken — quarantine.
- **FOREX is the only non-crypto pocket that is not negative**: n=52, PF 1.294, and its RSI2 mean-reversion strategy shows PF 1.364 at n=35. Small, but it is direct support for keeping forexs in scope rather than disabling it.

## 8. Data integrity

- **No benchmark column** → excess-vs-buy-and-hold cannot be computed from these files at all (proof step 2)
- **No cost/slippage column** → proof step 5 impossible
- **87% of closed picks have neither Entry nor Exit time** (1,440 / 1,653) → holding period, regime splits and time-slicing are impossible for most of the book; where computable, median hold is 12.0h
- **16 rows labelled LOST with positive PnL**; **11 CLOSED rows with PnL 0 and `Exit Reason=UNKNOWN`** (unresolved exits inflating the denominator)
- `Forward Trades` mixes scales (4494, 62, 3, 1, 2) — per-pick vs strategy-level metadata conflation, same defect flagged in the PR #794 review
- 6 `CROSS_DUP` rows; no fully duplicated rows
- Active: 11 open, max age 22.9h, none past 72h — clean

## Recommended order of work

1. **Sub-label FORCE_CLOSED** (`MAX_HOLD` / `PRUNED` / `LEADER_EXIT` / `MTM` / `NO_BRACKET`) so the 39% bucket becomes actionable instead of a black hole. Do not change the existing label's semantics — add a secondary field.
2. **Record cost and benchmark at write time.** Without them no row can ever pass proof steps 2 and 5, no matter how many rows accumulate.
3. **Grade-filter the pipeline.** A/B only; D at PF 0.193 should not be emitted at all.
4. **Disable SWING** (PF 0.716) and quarantine `crypto_signal_engine` (WR 2.7%).
5. **Keep FOREX running** — n=52 at PF 1.294 with RSI2 MR at 1.364 is the only non-crypto evidence that isn't negative, and it is exactly the class flagged to stay in scope.
