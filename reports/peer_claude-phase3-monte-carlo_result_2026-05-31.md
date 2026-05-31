# Phase 3 — Monte Carlo on Watchlist Candidates (RESULT)

Date: 2026-05-31
Author: peer_claude (Opus 4.7)
Source: `tools/phase3_mc_watchlist.py` (read-only on `ejaguiar1_stocks.trading_picks`, 10,000-iter bootstrap)

## TL;DR

Two real priorities; two likely small-sample artifacts; one dead-on-arrival.

- **KEEP ACCUMULATING (real, edge consistent with current draw):** `fx_smart_carry_trade_momentum` (P(T2 at n=100)=64%, P(T2 at n=200)=70%) and `stocks_rsi2_pullback` (P(T2 at n=100)=52%, P(T2 at n=200)=53%). Both have median bootstrap PF >=1.5 and median WR >=55% at every target n. These are the only two "ordinary edge" candidates.
- **EXTREME PF — SOURCE-AUDIT BEFORE TRUSTING:** `cta_golden_cross_200` (PF 44, WR 96%, n=25) and `prediction_market_consensus` (PF 24.5, WR 90%, n=89). P(T2 at n=100)=100% in the bootstrap, but those PFs are not realistic for a tradable edge — almost certainly resolver mislabel, TP_HIT artifact, or single-symbol concentration. Bootstrap can't tell you the data are wrong; it just resamples what's there. **Do not size up; open an audit.**
- **KILL/SHRINK:** `luxalgo_confluence` — n=1906, P(T2 at n=100)=6.7%, P(T2 at n=200)=2.1%. With this much sample, MC says the edge is not there. Mutate-before-kill per `MUTATION_THREE_AXIS_PROTOCOL.md` (regime gate / vol floor / source-confluence).
- **SANITY CHECK ONLY:** `futures_momentum` BOND, n=5. Skewed by 1-2 fat winners. Bootstrap returns P(T2)=98% which is not believable at this n; reflects only that the 5 in-sample draws are dominated by a fat tail. Treat as no-information until n>=30.

## Per-candidate table

| candidate | n_now | WR_now | PF_now | P(T2 @ 100) | P(T1 @ 100) | 95%CI PF @ 100 | 95%CI WR @ 100 | Verdict |
|---|---:|---:|---:|---:|---:|---|---|---|
| `stocks_rsi2_pullback` (EQUITY) | 31 | 58.1% | 1.52 | **52%** | 14% | [0.99, 2.36] | [50.0, 66.0] | **KEEP ACCUMULATING** — ordinary edge, sample is consistent with T2 boundary |
| `fx_smart_carry_trade_momentum` (FOREX) | 20 | 55.0% | 1.62 | **64%** | 17% | [1.15, 2.34] | [47.0, 63.0] | **KEEP ACCUMULATING** — strongest "real edge" candidate; widen sample to n>=50 next |
| `cta_golden_cross_200` (COMMODITY) | 25 | 96.0% | 44.09 | 100% | 100% | [22.4, 178.3] | [93.0, 99.0] | **AUDIT** — PF/WR not realistic for tradable edge; resolver/TP_HIT artifact suspected |
| `prediction_market_consensus` (CRYPTO) | 89 | 89.9% | 24.51 | 100% | 100% | [11.2, 72.8] | [85.0, 95.0] | **AUDIT** — DOGEUSDT 50%+ concentration (per Phase 2); treat as one-symbol bet, not strategy |
| `luxalgo_confluence` (CRYPTO) | 1,906 | 43.8% | 1.10 | **6.7%** | 0.3% | [0.75, 1.60] | [36.0, 52.0] | **MUTATE-BEFORE-KILL** — with n=1906 the bootstrap CI is tight; T2 is statistically unreachable from this distribution |
| `futures_momentum` (BOND) | 5 | 60.0% | 362.6 | 98% | 87% | [214, 621] | [52.0, 68.0] | **NO INFO** — n=5 dominated by fat tail; ignore bootstrap until n>=30 |

(95%CI = 5th–95th percentile of bootstrap distribution at target n; `_now` columns are observed in DB as of 2026-05-31. Live n differs slightly from Phase-2 figures because closed picks ticked up since 2026-05-31 morning.)

## Interpretation by candidate

### 1. `stocks_rsi2_pullback` (EQUITY) — KEEP ACCUMULATING
Observed PF 1.52 / WR 58% at n=31 sits right on the T2 boundary. At n=100 the 5th-percentile PF is 0.99, meaning the lower tail just touches sub-T2 — there is real downside risk if the next 70 picks regress. But the median (1.52) stays at T2, and P(T2 at n=200) only moves marginally (0.527). This is the **expected behavior of a real ordinary edge near threshold**: more sample tightens the CI around the same median. **Action:** keep emitting, do not size up until n>=100 with stable PF; re-MC at n=70 and n=100 to confirm the median has not shifted down.

### 2. `fx_smart_carry_trade_momentum` (FOREX) — KEEP ACCUMULATING (top "real edge" candidate)
P(T2) climbs from 64% at n=100 to 70% at n=200 — the only candidate where additional sample materially lifts the T2 probability. Bootstrap median PF 1.62 is comfortably above T2; 5th-percentile PF at n=100 is 1.15 (still profitable in the tail). The narrow std_pnl (0.46) vs mean (0.10) reflects a stable per-pick payoff. **This is the highest-confidence candidate.** Action: prioritize source instrumentation, target n>=50 in next 2 weeks.

### 3. `cta_golden_cross_200` (COMMODITY) — AUDIT, DO NOT PROMOTE
PF 44, WR 96%, mean pnl 4.55%, std 1.98%. Bootstrap returns P(T2)=100% at every n. **This is not a real edge** at face value — no tradable trend-following strategy clears 96% WR over 25 closed picks unless something is wrong with the resolver, the TP_HIT method, or the strategy is closing on tiny stops while the rare large losses are being labelled non-loss (CANCELLED/EXPIRED). Cross-reference with the `cta_golden_cross_200` Phase 2 audit and the 2026-05-31 COMMODITY incident. Action: pull these 25 picks and inspect entry/exit/exit_reason distribution before any sizing.

### 4. `prediction_market_consensus` (CRYPTO) — AUDIT (concentration)
PF 24.5, WR 90%, n=89 (up 6 since Phase 2's 95-close = different filter; this uses pnl_pct NOT NULL strict). Bootstrap P(T1)=100% at all n. But Phase 2 flagged DOGEUSDT 50.5% concentration — this is one symbol's bet, not a portfolio strategy. Even if the per-pick numbers are real, MC at the pick level overstates a portfolio-tradable edge because the resamples are not symbol-independent. Action: re-run MC after deduplicating to per-symbol, or treat as a single-asset bet not eligible for class-level promotion.

### 5. `luxalgo_confluence` (CRYPTO) — MUTATE-BEFORE-KILL
The only candidate with n large enough (1,906) that the bootstrap is informative as a kill signal. Bootstrap median PF=1.10, 95th-percentile PF at n=100 is 1.60 — meaning **even cherry-picking 100 of the best resamples, the upper tail barely clears T2**. P(T2 at n=200) is 2.1%. The edge is not at T2 at this distribution. Action: apply three-axis mutation per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (regime gate + vol floor + source-confluence) before retiring; killing without mutation removes the largest n base and the only known emitter calibration.

### 6. `futures_momentum` (BOND) — NO INFO
n=5 (Phase 2 said n=8; the strict pnl_pct-NOT-NULL filter cut 3). PF 362 is a 1-2-trade artifact. Bootstrap math has nothing to work with. Ignore.

## Recommendations

1. **>60% P(T2 at n=100) priority list (real edges):**
   - `fx_smart_carry_trade_momentum` (P=64% → 70% at n=200). Top accumulation target.
   - `stocks_rsi2_pullback` (P=52%, near boundary). Second.
2. **<20% P(T2 at n=100) — small-sample noise or actual non-edge:**
   - `luxalgo_confluence` (P=6.7%, large-n confirmed non-edge → mutate-before-kill).
   - Note: `cta_golden_cross_200` and `prediction_market_consensus` both show P>>0.6 but those are **data-integrity flags**, not edges. AUDIT before any sizing.
3. **Re-run MC checkpoints:**
   - When `fx_smart_carry_trade_momentum` reaches n=50 (currently 20): re-bootstrap. If P(T2 at n=100) drops below 50%, downgrade.
   - When `stocks_rsi2_pullback` reaches n=70 (currently 31): re-bootstrap. If median PF drops below 1.40, downgrade.
4. **Do NOT use Phase 3 numbers in isolation.** Bootstrap assumes i.i.d. — it does not catch regime change, concentration, resolver bugs, or look-ahead. Pair with the Phase 2 per-strategy audits and the 14d/48h recency panels in `audit_dashboard/data/pick_summary_stats_*.json` before any sizing decision.

## Method recap

- 10,000 resamples WITH replacement per (candidate, target_n).
- Target n: observed n_now, 100, 200.
- PF = sum(positive pnl_pct) / |sum(negative pnl_pct)|; ∞ PFs (zero-loss resamples) excluded from percentile calcs and reported via `inf_rate` (only material for n=5 BOND: 33% — another no-info signal).
- WR = % of pnl_pct > 0.
- T2 = (PF≥1.5 AND WR≥50). T1 = (PF≥2.0 AND WR≥55).
- Seed 42, deterministic. Run on 2026-05-31 against live `ejaguiar1_stocks.trading_picks`.

## Files

- `tools/phase3_mc_watchlist.py` — self-contained, read-only.
- `reports/peer_claude-phase3-monte-carlo_plan_2026-05-31.md` — BEFORE.
- `reports/peer_claude-phase3-monte-carlo_result_2026-05-31.md` — THIS file.
