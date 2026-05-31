# Peer-claude verify — Qwen FOREX PF reversal claim (2026-05-31)

## Claim under test
Qwen reported: dashboard FOREX PF = **2.02** vs raw DB PF = **0.108** — i.e. a "direction reversal" where dashboard looks healthy but raw DB is broken.

## Method
- Raw DB query against `ejaguiar1_stocks.at_raw_picks` (table lives in `stocks`, not `backtests`).
- Dashboard JSON: `audit_dashboard/data/dashboard_data.json` (generated 2026-05-31T21:31:21Z, sha `97810c560`).
- All numbers re-derived from a fresh query/JSON parse (no transcription from Qwen).

## Raw DB — at_raw_picks FOREX (status IN WON,LOST, pnl_pct NOT NULL)

| Window | PF | n | wins | losses |
|--------|----|----|------|--------|
| ALL-TIME | **3.62** | 5,976 | 4,850 | 1,119 |
| Last 90d (by signal_timestamp) | **3.87** | 5,916 | 4,816 | 1,093 |

Query used:
```sql
SELECT SUM(CASE WHEN pnl_pct>0 THEN pnl_pct ELSE 0 END)
      /NULLIF(ABS(SUM(CASE WHEN pnl_pct<0 THEN pnl_pct ELSE 0 END)),0) pf,
       COUNT(*) n,
       SUM(pnl_pct>0) wins, SUM(pnl_pct<0) losses
FROM at_raw_picks
WHERE asset_class='FOREX' AND status IN ('WON','LOST') AND pnl_pct IS NOT NULL;
```

Note: this is gross-pnl sum-ratio, identical formula Qwen alleges he used.

## Dashboard FOREX PF — every occurrence found

| Path | n | PF |
|------|---|----|
| `performance.asset_class_health.FOREX` | 74 | **0.76** |
| `performance.by_asset_class.FOREX` | 74 closed | **0.76** |
| `hf_stats.by_asset_class.FOREX` | 88 | **0.984** |
| `money_ready_verdicts.FOREX` | 29 resolved | **0.0349** |
| `readiness.by_class.FOREX` | 74 | **0.76** |
| `swarm_picks_data.leaderboard.by_asset_class.FOREX` | 2 resolved | 0.0 |

There is **no FOREX PF = 2.02** anywhere in dashboard_data.json.

## Verdict: **DOESNT_REPRODUCE**

Neither side of Qwen's claim reproduces:
- Dashboard FOREX PF: actual values are 0.0349 / 0.76 / 0.984 depending on cohort (policy-clean money_ready vs trading_picks vs hf_stats). **2.02 does not appear.**
- Raw at_raw_picks FOREX PF: actual 3.62 all-time / 3.87 90d. **0.108 does not appear.**

The two surfaces measure different cohorts (raw aggregator output vs policy-clean resolved trading_picks), so the *direction* of the discrepancy is the OPPOSITE of Qwen's claim: raw at_raw_picks looks much healthier (PF 3.6) than the policy-clean money_ready slice (PF 0.035). That is consistent with the known M-067 policy-clean filter culling 99%+ of the aggregator firehose to a tiny resolved sample (n=29) where one big loser dominates.

Qwen's specific numbers (2.02 / 0.108) appear fabricated or pulled from a stale/wrong source. Treat the underlying "dashboard FOREX is misleading" thesis with extreme skepticism until a different reviewer re-derives both numbers from current data.

## Return
`FOREX_PF:dashboard=0.76(ach)/0.984(hf)/0.0349(money_ready):raw=3.62(all)/3.87(90d):n_raw=5976/5916:verdict=DOESNT_REPRODUCE`
