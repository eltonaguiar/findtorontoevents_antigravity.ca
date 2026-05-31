# WON-185 Forensics — Plan (BEFORE)

Date: 2026-05-31
Author: Claude Opus 4.7 (peer subagent)
Scope: 185 rows in `ejaguiar1_stocks.trading_picks` with `status='WON'` (non-canonical status). Phase-10b status-std agent aborted as ambiguous; this forensics pass characterizes the population and recommends an action.

## Live distribution queries (run against mysql.50webs.com)

### Q1: exit_reason distribution

```sql
SELECT exit_reason, COUNT(*)
FROM trading_picks WHERE status='WON'
GROUP BY exit_reason ORDER BY 2 DESC LIMIT 30;
```

Result:

| exit_reason | count | share |
|---|---|---|
| `RECONCILED_POSITIVE_PNL` | 162 | 87.6% |
| `PRICE_RESOLVED [RECO [FIX] (RE` | 23 | 12.4% |

Total: 185. **Only 2 distinct exit_reasons.** The second is **truncated** — `exit_reason` column is `VARCHAR(30)`, so the original text was longer (likely `PRICE_RESOLVED [RECONCILED] [FIX] (RESOLVED)` or similar).

### Q2: exit_reason × avg pnl_pct × WR

| exit_reason | n | avg pnl_pct | wr_pct |
|---|---|---|---|
| `RECONCILED_POSITIVE_PNL` | 162 | **+9.99%** | 100% |
| `PRICE_RESOLVED [RECO [FIX] (RE` | 23 | **+0.0057%** | 100% |

Both buckets are 100% positive PnL by construction (status='WON'). The avg pnl divergence (1740×) signals two completely different sub-populations.

### Q3: source_system distribution

```
copy_trader_intel        87
alpha_engine             31
multi_asset_copytrader   21
battleground_luxalgo     13
regime_terminal           7
genome                    6
multi_asset_scanner       4
genome_mutations          4
non_crypto_consensus      3
cta_replicator            3
ml_strategy_reviver_inverse  2
prediction_market_agents  2
coinglass_sentiment       1
quan_engine               1
```

Spread across 14 source_systems — not a single writer's bug.

### Q4: category × exit_reason

| category | exit_reason | n |
|---|---|---|
| crypto | `RECONCILED_POSITIVE_PNL` | 135 |
| forex | `PRICE_RESOLVED [RECO...` | 20 |
| equity | `RECONCILED_POSITIVE_PNL` | 9 |
| stocks | `RECONCILED_POSITIVE_PNL` | 7 |
| (empty) | `RECONCILED_POSITIVE_PNL` | 5 |
| futures | `RECONCILED_POSITIVE_PNL` | 4 |
| commodity | `PRICE_RESOLVED [RECO...` | 3 |
| etf | `RECONCILED_POSITIVE_PNL` | 1 |
| forex | `RECONCILED_POSITIVE_PNL` | 1 |

**The 23 truncated-label rows are exclusively forex(20)/commodity(3).** All other categories use only `RECONCILED_POSITIVE_PNL`.

### Q5: 23 truncated rows vs 5bp non-CRYPTO threshold

```sql
SELECT COUNT(*), SUM(CASE WHEN ABS(pnl_pct)<0.05 THEN 1 ELSE 0 END) below_5bp
FROM trading_picks WHERE status='WON' AND exit_reason LIKE 'PRICE_RESOLVED%';
```

Result: **23 / 23 (100%) are below 5bp.** Per `PNL_WIN_THRESHOLD_BY_CLASS` in `alpha_engine/outcome_resolver.py:115-126` (CRYPTO 0.1bp, others 5bp), these rows are sub-threshold and should NOT be wins for forex/commodity. They appear to be victims of a pre-fix resolver that used the CRYPTO threshold for forex.

### Q6: 162 RECONCILED_POSITIVE_PNL pnl buckets

| bucket | n |
|---|---|
| < 0.5% | 7 |
| 0.5–2% | 18 |
| 2–5% | 38 |
| 5–10% | 45 |
| ≥ 10% | 54 |

Huge dispersion — incompatible with a single exit mechanism. TPs typically cap gains, so 54 rows above 10% are likely **TIME_EXIT_PROFITABLE** (held to time-bar in a winning trend). Many sub-2% rows could be **TP_HIT** for tight-TP strategies.

### Q7: closed_at range

`MIN: 2026-03-11 13:27:44 → MAX: 2026-05-31 00:00:00` — 81-day span, not a single bad backfill batch.

## Sub-population summary

**Group A — `RECONCILED_POSITIVE_PNL` (n=162, 87.6%)**
- Resolver-reconciliation label assigned during backfill when exit mechanism (TP_HIT vs TIME_EXIT) was indeterminate but pnl was clearly positive.
- Spread across 13 source_systems × 7 categories (crypto-dominated 135/162).
- pnl spans 0.13% → 30%+, far too wide for a single exit-mechanism mapping.
- Semantically valid wins; non-canonical status name only.

**Group B — `PRICE_RESOLVED [RECONCILED] [FIX] (RE...)` truncated (n=23, 12.4%)**
- 20 forex (all EURGBP=X) + 3 commodity.
- 100% have |pnl| < 5bp → sub-threshold for non-CRYPTO per `PNL_WIN_THRESHOLD_BY_CLASS`.
- Likely pre-v2 resolver output using CRYPTO threshold on forex. These rows are **mislabeled wins** — should be `TIME_EXIT` (FLAT).

## Decision-tree mapping

- NOT >80% single TP-like exit_reason.
- NOT >80% single TIME_EXIT-like exit_reason.
- Population IS dominated (87.6%) by `RECONCILED_POSITIVE_PNL` — but this reason is **explicitly a "couldn't determine mechanism" backfill label**, not an exit-mechanism class. Forcing a TP_HIT or TIME_EXIT mapping would invent information.
- Group B is a clear bug (sub-threshold forex/commodity should be FLAT), but the truncated reason text means we cannot recover the full original label without DB introspection of the source script. Safe mutation possible (re-resolve under canonical threshold) but conservative.

**Verdict: MIXED — drop operator-decision docs PR with the distribution matrix and a recommendation menu. Do NOT mutate the 162 reconciled rows (status='WON' is semantically valid). Recommend a targeted re-resolve for the 23 sub-threshold forex/commodity rows in a follow-up PR after operator confirms.**

## Files referenced

- `alpha_engine/outcome_resolver.py:115-126` (`PNL_WIN_THRESHOLD_BY_CLASS`)
- `reports/action_B_resolver_2026_04_27.md` (resolver fix history)
- `reports/feedback_noncrypto_resolver_live_close_bug.md` (sub-threshold forex bug bundle)
