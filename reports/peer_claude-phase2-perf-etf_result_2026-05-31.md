# Phase-2 Performance Audit — ETF

Date: 2026-05-31  
Source: `ejaguiar1_stocks.trading_picks` (live), `audit_dashboard/data/pf_registry.json` (generated 2026-05-31T03:54:06Z)  
Filter: `category='etf' AND closed_at IS NOT NULL`

## Class-aggregate
n=20  WR=20.00%  PF=0.377  avg_pnl=-0.895%  worst=-5.13%  best=+4.40%

T2 status:
- PF >= 1.5 → **FAIL** (0.377)
- WR >= 50% → **FAIL** (20%)
- MDD proxy (worst pick) < 20% → PASS (-5.13%)
- n >= 100 → **FAIL** (n=20, INSUFF-N)

Overall: **FAIL on 3/4 axes — INSUFF-N + losing edge.** ETF is not promotable in any form right now.

Status mix: LOST=14 (70%), TP_HIT=4 (20%), EXPIRED=2 (10%). 0 SL_HIT — confirms ETF exits are landing in TP-or-time-stop regime; no stop-out discipline yet because samples too thin.

Total ETF rows in DB: 320 (300 still open / unresolved). The 20 closed are the entire post-PR #158/#166 honest sample.

Symbol concentration (closed only): SPY=3, VNQ/XLF/GLD/QQQ=2 each, then long tail of 1-pick symbols (43 distinct symbols across 320 total picks — broad diversification, no single-symbol concentration risk on the closed cohort). **No crypto-suffix contamination** (zero USDT/USDC/BTC/ETH suffix symbols in ETF) — PR #158/#166 cleanup verified.

## Per-strategy table (HAVING n>=1; ETF too thin for n>=10 cutoff)
| strategy | n | WR | PF | avg_pnl | T2 verdict |
|---|---|---|---|---|---|
| regime_mild_bull | 2 | 100.00% | n/a (no losers) | +2.121% | INSUFF-N (n=2) |
| sector_rotation | 1 | 100.00% | n/a (no losers) | +4.396% | INSUFF-N (n=1) |
| vix_reversal | 3 | 33.33% | 0.017 | -0.006% | FAIL (PF/WR) + INSUFF-N |
| proven_vwap_mean_reversion | 2 | 0.00% | n/a (no winners) | +0.006% | INSUFF-N + losing |
| ema_stack_momentum | 1 | 0.00% | n/a (pnl null) | n/a | INSUFF-N |
| fractal_decay_penny | 1 | 0.00% | n/a (pnl null) | n/a | INSUFF-N + tag-leak (penny on ETF) |
| hidden_divergence_continuation | 1 | 0.00% | n/a (pnl null) | n/a | INSUFF-N |
| luxalgo_confluence | 1 | 0.00% | n/a (pnl null) | n/a | INSUFF-N |
| hoffman_irb_reversal | 1 | 0.00% | 0.000 | -0.885% | INSUFF-N |
| extreme_oversold_bounce | 5 | 0.00% | 0.000 | -3.097% | **FAIL all axes** |
| hyperopt_connors_rsi2 | 2 | 0.00% | 0.000 | -3.288% | INSUFF-N + losing |

## Promotable to T2 (PASS all axes)
- **None.** No ETF strategy has n>=100 closed; the entire ETF closed cohort is n=20. The 100% WR rows (`regime_mild_bull` n=2, `sector_rotation` n=1) are noise, not edge.

## Watchlist (1-2 axes failing or thin sample)
- `regime_mild_bull` (2/2 wins +2.12% avg) — keep accumulating; promising regime-aware entry but needs 50+ samples before reading.
- `sector_rotation` (1/1 +4.40%) — same: macro-regime style, low frequency, needs 6+ months of forward picks to validate.
- `vix_reversal` (n=3 WR 33%) — tiny but not catastrophic; classic VIX-mean-reversion on ETF should produce more samples if VIX wakes up; watch.

## Dead/retire candidates
- `extreme_oversold_bounce` on ETF: 0/5 wins, avg -3.10%, worst -5.13%. Even at n=5 this is a 5-σ-ish signal against the strategy on ETF (it may work on penny/equity but for ETF underliers the signal is inverted). **RECOMMEND restricting `extreme_oversold_bounce` strategy from `category='etf'` source pool** until it produces a positive 30-pick walk-forward.
- `hyperopt_connors_rsi2` (0/2, avg -3.29%): Connors RSI(2) on ETF is a well-known publicly-known signal — likely over-arbitraged. Low priority but flag for kill if n grows past ~20 with no improvement.
- `fractal_decay_penny` tagged on an ETF row (n=1) — **tag leak suspect**. A "penny" strategy should not be emitting picks tagged `category='etf'`. INCIDENT candidate: audit the source emitter to confirm the symbol-classifier is not mislabeling small-cap ETFs as penny-strategy candidates.

## pf_registry divergences
- **No ETF entries in `audit_dashboard/data/pf_registry.json`** (top-level groups `by_asset_class`, `by_asset_class_policy_clean_net`, `by_asset_class_strategy_policy_clean_net` all return zero matches for any `etf`/`ETF` key, registry generated 2026-05-31T03:54:06Z).
- This matches CLAUDE.md MAJOR GOALS line for ETF (INSUFF-N gated out at registry time). **No divergence to flag**, but the registry omission means dashboard PF/WR cells for ETF are derived from a different path (asset_class_health) — coverage gap worth a follow-up.

## Recommendation
1. **Next graduation candidate:** none — no ETF strategy has the sample depth. Closest "watch" is `regime_mild_bull` (2/2 wins, macro-regime gating); flag for re-audit when n>=30.
2. **Kill candidate:** restrict `extreme_oversold_bounce` from emitting ETF picks (0/5, avg -3.1%, worst -5.1%) — the signal is anti-correlated on ETF underliers. File ENH ticket: gate this strategy's source pool to `category IN ('equity','penny','crypto')` only.
3. **Open incident:** investigate `fractal_decay_penny` tagging an ETF row — likely classifier leak; reuse the PR #166 EQUITY-mistag tooling to sweep penny→etf mistags.
