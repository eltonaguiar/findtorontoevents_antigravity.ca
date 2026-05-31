# Phase-2 Performance Audit — FOREX

Date: 2026-05-31 (post PR #158 SHIBUSDT resolver, post PR #166 EQUITY mistag backfill)
Source: `ejaguiar1_stocks.trading_picks WHERE category='forex' AND closed_at IS NOT NULL`
Peer: claude-opus-4-7

## Class-aggregate

n=1666  WR=43.10%  PF=1.258  avg_pnl=+0.073%  cum_pnl=+121.6 (peak +142, drawdown -334)  worst=-100%  best=+99.14%

T2 verdict (PF≥1.5 / WR≥50 / MDD<20 / n≥100):
- n  PASS (1666)
- WR FAIL (43.10 < 50)
- PF FAIL (1.258 < 1.50)
- MDD FAIL (cum-pnl drawdown 334 units vs peak 142 = 2.35× — equity curve clearly underwater)

Overall: **FAIL T2** on 3 of 4 axes. Consistent with CLAUDE.md current FOREX state (PF 0.55 / WR 40% in `money_ready_verdict.json` 2026-05-24). The slightly better PF here (1.258 vs registry 0.55 / vs policy-clean 0.037) is the *raw* number — it includes still-tagged-but-policy-scrubbed concentration and noisy strategies. Do not cite 1.258 as "improvement."

## Per-strategy table (n ≥ 10)

| strategy | n | WR | PF | avg_pnl | worst | best | T2 verdict |
|---|---|---|---|---|---|---|---|
| cta_fx_multifactor | 10 | 70.00% | 26.852 | +0.304% | -0.07 | +0.74 | THIN-N (PF/WR pass but n<100) |
| ig_contrarian_sentiment | 314 | 42.99% | 16.732 | +0.417% | -0.50 | +79.55 | FAIL (WR), PF dominated by one +79% outlier |
| non_crypto_consensus | 144 | 45.14% | 6.337 | +0.535% | -0.61 | +79.56 | FAIL (WR), PF outlier-driven |
| cta_cross_asset_tsmom | 32 | 18.75% | 4.554 | +2.436% | -2.35 | +99.14 | FAIL (WR + n), single-leg lottery |
| myfxbook_retail_contrarian | 364 | 47.53% | 3.815 | +0.206% | -2.46 | +79.55 | FAIL (WR borderline 47.5<50) |
| fx_smart_carry_trade_momentum | 21 | 52.38% | 1.623 | +0.105% | -0.56 | +0.77 | THIN-N (PF + WR pass on tiny sample) |
| (empty strategy) | 22 | 72.73% | 0.726 | -1.313% | -76.13 | +27.93 | DATA-QUALITY (untagged legacy) |
| forex_rsi2_mean_reversion | 664 | 43.67% | 0.241 | -0.294% | **-100.00** | +5.00 | FAIL ALL — primary loss driver |
| forex_carry_momentum | 43 | 6.98% | 0.058 | -0.552% | -3.34 | +1.10 | DEAD |

## Promotable to T2 (PASS all 4 axes, n≥100)

**NONE.** No FOREX strategy currently meets `n≥100 AND WR≥50 AND PF≥1.5 AND MDD<20`.

## Watchlist (1–2 axes failing or thin sample)

- **fx_smart_carry_trade_momentum** (n=21, WR=52%, PF=1.62) — only strategy with PF+WR both passing live. Path-to-T2 = grow sample to n≥100 (4–5× current). No outlier drivers (worst -0.56, best +0.77 — clean distribution). **HIGHEST-PRIORITY GRADUATION CANDIDATE** once sample matures.
- **cta_fx_multifactor** (n=10, WR=70%, PF=26.85) — too thin to trust; PF distorted by single outlier dynamics. Watch but do not size.
- **non_crypto_consensus** (n=144, WR=45%, PF=6.3 outlier-driven) — strip the +79.56 outlier and PF collapses near 1.0. Diagnose what produced the outlier; is it a real edge or a resolver mis-fill?
- **myfxbook_retail_contrarian** (n=364, WR=47.5%, PF=3.8 outlier-driven) — same outlier story. Largest sample of the "contrarian sentiment" family; worth a deep-dive after the +79.55 outliers (also present in ig_contrarian_sentiment + non_crypto_consensus — likely same underlying pick replicated).

## Dead / retire candidates

- **forex_rsi2_mean_reversion** (n=664, WR=43.7%, PF=0.24, worst -100%) — largest sample, deeply unprofitable, has at least one -100% outlier (FX should NOT see -100% on a vanilla MR strategy — likely leverage/PnL-calc bug; investigate before retire).
- **forex_carry_momentum** (n=43, WR=6.98%, PF=0.058) — broken. Retire after one-pass investigation per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` (apply `tools/mutation_analysis.py` three-axis protocol).
- **(empty-strategy)** (n=22) — data-quality bug, not a strategy. Backfill `strategy` column from `source_system` lineage.

## pf_registry divergences

Reference: `audit_dashboard/data/pf_registry.json` → `by_asset_class_strategy_policy_clean_net` (FOREX) + `by_asset_class_policy_clean_net` (FOREX agg).

- **Class-aggregate massive sample delta**: registry FOREX n=28 vs DB raw n=1666 (59× scrub ratio). Registry PF=0.037, WR=28.6%, MDD=0.81. The policy-clean cohort is dominated by `multi_asset_scanner` (n=11, PF 0.21, single_source_pct=1.0 → flagged `is_single_source_artifact=True`). This means **policy-clean view treats virtually all live FOREX strategies as noise/concentration artifacts** — the only ones surviving the filter are tiny (alpha_engine n=1, multi_asset_copytrader n=3, regime_* n=1–4). The "policy-clean" view does NOT include the big 4 (`ig_contrarian_sentiment`, `myfxbook_retail_contrarian`, `forex_rsi2_mean_reversion`, `non_crypto_consensus`) at all — they're either flicker-dedup'd out or fail single-source policy. **Investigate why the high-n live strategies are absent from the policy-clean registry — either they SHOULD be there (registry bug) or they SHOULD be killed at source (live-engine bug).**
- **Strategy name mismatch**: registry uses `alpha_engine`, `cta_replicator`, `multi_asset_scanner`, `multi_asset_copytrader`, `regime_terminal`, `regime_mild_bear`, `regime_accumulation`. DB raw uses `ig_contrarian_sentiment`, `myfxbook_retail_contrarian`, `forex_rsi2_mean_reversion`, etc. The two namespaces almost don't overlap — strong signal that policy-clean is pulling from a different upstream (backtest registry?) than live picks. This is the FOREX equivalent of the CRYPTO "78.9% disputed" issue.
- **No 1:1 strategy comparison possible** — divergence is too structural to score per-row >10%. Flag at the class level: **registry FOREX cohort and live FOREX cohort are effectively disjoint**.

## Symbol leakage check (per PR #158/166 follow-up)

Top symbols: GBPJPY=X (193), AUDJPY=X (192), USDCAD=X (179), EURGBP=X (173), EURJPY=X (169), CADJPY=X (155), AUDUSD=X (141), USDJPY=X (114), NZDUSD=X (103), USDCHF=X (94), GBPUSD=X (75), EURUSD=X (71). All Yahoo `*=X` FX pairs. **No crypto-suffix leakage detected** — PR #158/166 cleanup is holding on the FOREX side. USDJPY concentration is 6.8% (114/1666), well below the 55% figure cited in CLAUDE.md (which referenced the old recompute-path cohort). **JPY-cross concentration overall = 985/1666 = 59.1%** — bigger structural risk than any single pair. Any FOREX edge here is functionally a "JPY carry/cross" edge.

## Recommendation

1. **Next graduation candidate: `fx_smart_carry_trade_momentum`** — only strategy with clean WR≥50 + PF≥1.5 distribution (no outlier dependency). Grow sample to n≥100 before sizing; expected 4–6 weeks at current pick rate.
2. **Immediate kill candidate: `forex_carry_momentum`** (n=43, WR=7%, PF=0.058). Run `tools/mutation_analysis.py` then add to `BLOCKED_SOURCE_SYSTEMS` per TESTING_PROTOCOL §7. **Also investigate `forex_rsi2_mean_reversion`'s -100% outlier as a P1 data-integrity bug** (FX vanilla MR cannot lose 100% without a calc/leverage error) before retiring the strategy — kill the bug first, then re-evaluate PF.
3. **P0 follow-up**: reconcile `pf_registry` FOREX cohort (n=28, alpha_engine/cta_replicator namespace) vs live DB (n=1666, ig_contrarian/myfxbook/rsi2 namespace). Two disjoint universes today; one of them is wrong.
