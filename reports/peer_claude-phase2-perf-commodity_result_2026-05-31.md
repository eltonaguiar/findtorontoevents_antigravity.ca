# Phase-2 Performance Audit — COMMODITY

Run date: 2026-05-31. Source: `ejaguiar1_stocks.trading_picks` (live, post-P0-batch 2026-05-31).

## Class-aggregate

n=712  WR=38.90%  PF=0.700  avg_pnl=-0.183%  worst=-98.4%  best=+16.1%
MDD (cum-pnl peak-to-trough proxy) ≈ 166.5% (driven by `futures_momentum` cumulative loss)

T2 verdict: **FAIL on every axis** (PF<1.5 FAIL · WR<50 FAIL · MDD>>20 FAIL · n>=100 PASS sample-size only).
T1 verdict: FAIL.

## Per-strategy table (n>=10 only)

| strategy | n | WR | PF | avg_pnl | MDD% | T2 verdict |
|---|---:|---:|---:|---:|---:|---|
| `cta_golden_cross_200`        |  26 | 76.9% | 44.09 | +4.55% |  2.6 | **PASS axes** but n<100 (INSUFF-N) |
| `cta_cross_asset_tsmom`       |  27 | 33.3% |  0.69 | -0.19% | 12.4 | FAIL (PF<1.5, WR<50) |
| `futures_momentum`            | 592 | 37.5% |  0.45 | -0.27% |175.6 | **FAIL hard** (PF, WR, MDD) |
| `cta_commodity_momentum_term` |  53 | 37.7% |  0.36 | -0.28% | 14.7 | FAIL (PF<1.5, WR<50); n<100 |

Strategies with n<10 (omitted from grading; observed in DB): `cftc_cot_commercial_signal` (0 closed loss), `combined_confidence`, `cot_positioning`, `futures_ema_stack_momentum`, `liquidity_sweep_reversal`, `non_crypto_consensus`.

## Symbol concentration

| symbol | n | share |
|---|---:|---:|
| HG=F | 236 | 33.1% |
| SI=F | 182 | 25.6% |
| PL=F | 160 | 22.5% |
| GC=F |  87 | 12.2% |
| KC=F |  21 |  2.9% |
| (other 10) | 26 | 3.7% |

HHI ≈ 0.235 across 11 traded symbols. Top-3 (HG, SI, PL — industrial/precious metals) = 81.2%. Cotton (CT=F) concentration that triggered M-067 is now only 4 closed picks (down from 57% historical).

## Promotable to T2 (PASS all axes)

**None at n>=100.**

The only strategy passing all PF/WR/MDD axes is `cta_golden_cross_200` (PF 44.1, WR 76.9%, MDD 2.6%) but n=26 — sample too thin for graduation. Its PF is also extreme (44.1) which usually indicates a small clean win streak rather than a robust edge. **Do not graduate; widen to n>=100 first.**

## Watchlist (1-2 axes failing or thin sample)

- `cta_golden_cross_200` — only sub-T2 axis is sample size. Recommend stalking: keep generating, target n=100 by Q3 2026, then re-grade. If WR holds >55% and PF>1.5 at n=100, recommend immediate T2 graduation.

## Dead / retire candidates

- **`futures_momentum` (n=592, PF 0.45, WR 37.5%, MDD 175.6%, avg_pnl −0.27%)** — by far the dominant commodity producer and a net loser at scale. Two embedded data-quality outliers (see anomalies below) inflate MDD, but even excluding `pnl_pct < -10` the PF is still 0.691 / WR 38.1% / avg −0.10%. This strategy carries the entire class verdict and must be paused or rewritten. **RECOMMEND retire / suspend** pending re-tune.
- `cta_commodity_momentum_term` (n=53, PF 0.36, WR 37.7%) — three full axes fail; thin sample but trajectory matches the broken `futures_momentum`. Suspend until mutation analysis (`tools/mutation_analysis.py`).
- `cta_cross_asset_tsmom` (n=27, PF 0.69, WR 33%) — same retire trajectory; note this strategy was just registered in non-crypto policy per commit 5676eace2. Watch one more cycle before kill.

## pf_registry divergences (HEAVY)

`audit_dashboard/data/pf_registry.json` (`by_asset_class` commodity): n=29, WR 17.2%, PF 0.71.
`by_asset_class_policy_clean_net` commodity: n=10, WR 40.0%, PF 1.72, MDD 6.6%.
DB live: **n=712, WR 38.9%, PF 0.70.**

- Class-aggregate count mismatch is ~24x — registry has not been regenerated since the M-067 cleanup + 2026-05-31 P0 batch landed (PR #158 SHIBUSDT resolver, PR #166 EQUITY backfill, plus today's commodity resolution). **ACTION: regenerate `pf_registry.json` before any verdict-grade public surface cites COMMODITY numbers.**
- Per-strategy registry rows are even thinner (cftc_socrata n=3, commodity_tsmom_12m n=3, cta_replicator n=3, vwap_rsi_confluence n=1) — these strategies don't even appear in my n>=10 table because they're sub-threshold. Registry's "Tier-2-PASS" PF=1.72 on n=10 (policy-clean) is **statistically meaningless** and should not be displayed without an INSUFF-N badge.
- The single-source artifact flag missed `futures_momentum` despite it being 83% of all closed commodity rows. Recommend registry build adds a per-strategy concentration check, not just per-source.

## Data-quality anomalies (P1)

1. `multi_asset_futures_momentum::HG=F::2026-05-24_1335` — entry $386.94, exit $6.197, pnl_pct −98.4%, status LOST, exit_reason `SL_HIT_REPLAY`. HG=F (copper) trades around $4-5/lb; both prices are scale-broken. Likely contract-month rollover or units bug.
2. `consensus_SI=F_BUY_20260420_2103` — entry $79.80, exit $3.13, pnl_pct −96.07%, status LOST, exit_reason starts `TP_HIT_RESOLVED [PRICE_MISMATCH...]`. The resolver flagged the mismatch but still wrote a catastrophic loss to the row. Inconsistent: TP_HIT in exit_reason vs LOST status — likely the same class of bug PR #158 fixed for SHIBUSDT, just on the COMMODITY side.

Excluding both outliers from `futures_momentum`: PF 0.69 / WR 38.1% (still FAIL). The strategy is broken on fundamentals, not just outliers — fixing the data alone won't graduate it.

No crypto-suffix symbols (USDT/BTC/ETH) found tagged as commodity — PR #166 backfill held.

## Recommendation

1. **Retire candidate (now):** `futures_momentum` — pause new picks, run a forensic on the HG=F / SI=F / PL=F sub-cohorts (these 3 = 81% of class volume) and `tools/mutation_analysis.py` before any restart. It is single-handedly responsible for the commodity-class FAIL verdict.
2. **Next graduation candidate (Q3 2026 once n>=100):** `cta_golden_cross_200` — clean PF/WR/MDD at n=26 makes it the only T2-trajectory strategy in the class. Increase signal cadence on HG/SI/PL/GC universe to bank sample size; re-grade when n hits 100.
3. **Registry regen required** before any /audit page repeats class-level commodity numbers.

---
_Method: SELECT-only against `trading_picks`. WIN = status IN ('WON','TP_HIT'). PF = Σ(pnl>0)/|Σ(pnl<0)|. MDD = peak-to-trough on time-ordered cum-pnl. No DB writes, no code edits._
