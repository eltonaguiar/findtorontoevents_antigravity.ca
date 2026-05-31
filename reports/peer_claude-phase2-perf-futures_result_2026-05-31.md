# Phase-2 Performance Audit — FUTURES

Date: 2026-05-31
Agent: peer_claude (Opus 4.7), READ-ONLY
DB: `ejaguiar1_stocks.trading_picks` WHERE `category='futures'`
Source-of-truth XREF: `audit_dashboard/data/pf_registry.json` (by_asset_class + policy_clean_net + by_asset_class_strategy_policy_clean_net)

## Headline: FUTURES is a NON-VIABLE asset class today (massive data-integrity hole)

- Of 428 total `category='futures'` rows, only **18 are non-zombie** (i.e., have non-zero realized pnl OR a non-NULL pnl_pct).
- **372 / 373** `futures_connors_rsi2` rows carry `status='TIME_EXIT'` with `pnl_pct = exactly 0.0000` — these are not real closures; they look like signals the outcome resolver auto-stamped TIME_EXIT but never priced.
- **15 / 18** rows with `status='LOST'` have `pnl_pct = NULL` — resolver tagged them lost but failed to compute realized PnL.
- Net: the raw `trading_picks` cohort is unusable for FUTURES T2 verdicts. The honest cohort is the pf_registry policy-clean-net view (n=12).

## Status / closure distribution (raw)

| status | n | closed_at NULL | pnl_pct NULL |
|---|---|---|---|
| TIME_EXIT | 374 | 374 | 0 (but 372 = 0.0000 = unpriced placeholder) |
| OPEN      | 35  | 35  | 16 |
| LOST      | 18  | 0   | 15 (NULL pnl) |
| TP_HIT    | 1   | 0   | 0  |

Only 19 rows have `closed_at IS NOT NULL` (18 LOST + 1 TP_HIT). Of those, only 4 have a real (non-NULL, non-zero) pnl_pct.

## Class-aggregate

Two cohorts disagree wildly — both reported for transparency:

### A. Raw DB, `closed_at IS NOT NULL AND pnl_pct IS NOT NULL AND pnl_pct != 0`
n=4  WR=25%  PF=10.28  avg_pnl=2.07%  worst=-0.88%  best=+9.15%
→ **Driven entirely by a single TP_HIT on `proven_futures_term_structure_proxy` (+9.15%) plus 3 tiny losses.** Statistically meaningless.

### B. pf_registry `by_asset_class_policy_clean_net` (current source of truth)
n=12  WR=16.67%  PF=0.535  total_pnl=-8.3 bp  MDD=16.6%  single_source_pct=91.7% (top_source=`multi_asset_scanner`)
T2 axes:
- PF >= 1.5  → **FAIL** (0.54)
- WR >= 50%  → **FAIL** (16.7%)
- MDD < 20%  → PASS (16.6%) — but trivially so on n=12
- n >= 100   → **INSUFF-N** (n=12 < 100)
- single-source artifact flag = TRUE (HHI > 0.90 → unreliable per concentration gate)

**Class verdict: FAIL + INSUFF-N + SINGLE-SOURCE ARTIFACT. Not a candidate for live capital.**

## Per-strategy table (registry policy-clean-net)

| strategy | n | WR | PF | total_pnl | MDD | T2 verdict |
|---|---|---|---|---|---|---|
| multi_asset_scanner | 11 | 9.09% | 0.475 | -9.4 bp | n/a | FAIL on PF + WR; INSUFF-N; 100% single-source |
| proven_futures_term_structure_proxy | 1 | 100% | n/a (no losses) | +1.1 bp | n/a | INSUFF-N (single trade); PF undefined |

## Per-strategy table (raw DB, `n>=10`, `status!='OPEN'`)

| strategy | n | wins | wr | avg_pnl | PF | note |
|---|---|---|---|---|---|---|
| futures_connors_rsi2 | 373 | 1 | 0.27% | 0.025% | undefined | **372/373 are zombie TIME_EXIT with pnl_pct=0.0000**; the 1 TP_HIT carries the entire signal |

No other strategy clears n>=10 in the raw cohort.

## Promotable to T2 (PASS all axes)
**None.** No FUTURES strategy meets even one of (n>=100, PF>=1.5, WR>=50%) cleanly. Even the only positive strategy (`proven_futures_term_structure_proxy`) is n=1.

## Watchlist (axes failing or thin sample)
- `proven_futures_term_structure_proxy` (n=1, WR=100%, +1.1 bp) — directionally interesting (term-structure / contango is a real CTA-grade edge per DBMF/KMLM), but sample is one trade. Recommend: scale signal-generation, target n>=30 over next 60d before any live size.
- `multi_asset_scanner` (n=11, WR=9%, PF=0.48) — bleeding small; not a true strategy edge (it's the cross-asset signal router). Holding for diagnostic value only.

## Dead/retire candidates
- `futures_connors_rsi2` — **373 picks, effectively zero real outcomes.** This is the dominant strategy in the raw cohort but is operationally broken (TIME_EXIT-zombie). **Recommend: halt signal generation until the resolver hole is fixed**, since every new pick is just adding to the zero-pnl placeholder pile.
- `connors_rsi2` / `hyperopt_connors_rsi2` (n=5 / n=3) — all LOST with NULL pnl. No edge evidence.
- `vix_reversal`, `ema_stack_momentum`, `mean_reversion_bollinger`, `contango_roll_yield`, `extreme_oversold_bounce`, `futures_mean_reversion` — all n<=3 closed; no signal.

## pf_registry divergences

Computed (raw DB, non-zombie) vs registered (policy_clean_net):
- **Class-aggregate**: raw PF = 10.28 (n=4) vs registry PF = 0.535 (n=12). Δ massive. Registry is correct — raw is contaminated by the single TP_HIT outlier.
- **`futures_connors_rsi2`**: raw shows n=373 but registry does not list this strategy at all in `by_asset_class_strategy_policy_clean_net`. The 372 zombie rows are presumably filtered out by the policy-clean cohort (correctly), but this means a strategy that produces 87% of FUTURES `trading_picks` rows is **invisible to the verdict layer**.
- **`multi_asset_scanner`**: only the registry exposes this (n=11). It does not appear as a `strategy` value in `trading_picks` raw query (likely tagged via source_system, not strategy column). Confirms the policy-clean-net view normalizes signal origin differently than the raw `strategy` field.

## Data-integrity flags (P0 / P1)

1. **P0 (resolver hole)**: 372 `futures_connors_rsi2` rows are TIME_EXIT with pnl_pct=0.0000 and closed_at NULL. Either:
   (a) the resolver writes status before pricing and never returns, or
   (b) signals expired without a quote (Yahoo `=F` continuous-contract gap?).
   Suggest auditing `alpha_engine/outcome_resolver.py` for FUTURES `=F` symbol-handling (continuous contract → next-month roll); cross-ref with `reports/feedback_noncrypto_resolver_live_close_bug.md`.
2. **P0 (LOST without pnl)**: 15/18 `status='LOST'` rows carry NULL pnl_pct. Resolver assigned the label but skipped the math — same root-cause pattern as M-067 incidents on COMMODITY/FOREX.
3. **P1 (concentration)**: registry flags `is_single_source_artifact: True` at 91.7% — even the clean cohort is dominated by `multi_asset_scanner`. Strategy diversity for FUTURES is effectively zero today.
4. **No symbol leakage detected**: zero rows match crypto-suffix (`USDT/USDC/BTC/ETH`) or FX-pair regex. Post PR #158 + PR #166, FUTURES symbol-tagging is clean. Top symbols are all proper Yahoo continuous-contract codes: `SI=F`, `CL=F`, `GC=F`, `ZN=F`, `HG=F`, `NQ=F`.

## Recommendation

1. **Do NOT graduate any FUTURES strategy.** No candidate clears T2 on any single axis with adequate n.
2. **Next graduation candidate (long-shot)**: `proven_futures_term_structure_proxy` — externally validated CTA edge (contango/backwardation roll yield is the DBMF / KMLM trick), but needs n>=30 before any size. Scale signal generation.
3. **Next kill**: `futures_connors_rsi2`. Pause signal emission until the outcome-resolver `=F` gap is patched; otherwise it will continue to poison the dataset with zombie TIME_EXIT rows.
4. **P0 follow-up**: file an incident to backfill / re-resolve the 372 zombie + 15 NULL-pnl rows. Until that runs, FUTURES dashboard numbers should carry a DISPUTED banner (mirror the CRYPTO Smart-Picks treatment per `c1b977997`).

---
Methodology: WON = `status IN ('WON','TP_HIT')`. PF = sum(pnl>0)/abs(sum(pnl<0)). MDD = peak-to-trough on unweighted equity curve of closed pnl_pct. T2 thresholds from `reports/hedge_fund_performance_review_*.md`. Registry XREF: 2026-05-25 build of `pf_registry.json`.
