# Loop Checkpoint 4 — T+~100m (2026-05-08 19:55 UTC)

## Outcome coverage reconciled

| definition | live | source |
|---|---|---|
| `at_raw_picks` rows w/ `pnl_pct IS NOT NULL` | **16,740 / 136,411 = 12.27%** | my db_health_check |
| `at_signal_outcomes` row count / `at_raw_picks` total | **121 / 136,411 = 0.09%** | Kimi |
| `at_raw_picks` rows w/ `status NOT IN (OPEN, pending)` | 67,755 / 136,411 = 49.67% | freebuff variant |

Both Kimi and my numbers are arithmetically correct; they measure different things.

- My number: how many raw picks have an INLINE PnL value (resolver wrote `pnl_pct` directly)
- Kimi number: how many raw picks have a row in the separate `at_signal_outcomes` event-log table (likely deprecated)

**Recommendation**: dashboard surfaces both — "PnL coverage 12.27%" + "explicit outcome events 0.09%". The 0.09% on `at_signal_outcomes` suggests that table is abandoned; data lives in `at_raw_picks.pnl_pct` instead. Either kill `at_signal_outcomes` or backfill it from `at_raw_picks`.

## WON-with-negative-PnL — root cause partially traced

`trading_picks` WON status by source_system:

| source_system | n | avg_pnl_pct |
|---|---|---|
| `multi_asset_copytrader` | **1,247** | **-85.38** |
| alpha_engine | 452 | +0.12 |
| cta_replicator | 142 | +0.09 |
| copy_trader_intel | 124 | +7.81 |
| ml_crypto_predictor | 109 | +6.87 |
| alpha_engine_fast | 92 | +0.03 |
| mega_mutation | 91 | +5.55 |
| multi_asset_cot | 81 | +0.05 |
| non_crypto_consensus | 77 | +0.001 |

`multi_asset_copytrader` is the lone bad actor. Sample worst row:

```
symbol=AUDUSD=X direction=SHORT strategy=myfxbook_retail_contrarian source=multi_asset_copytrader
entry_price=0.71572700 exit_price=76429.98600000 pnl_pct=-106700.6792 status=WON
```

`exit_price` is 100,000× the actual forex pair scale. Status forced to WON regardless of PnL sign. `multi_asset_copytrader_scraper.py` itself writes `status='OPEN'` (line 428). The bug lives in the CLOSER that resolves these picks — likely a multi_asset-specific resolver or `forward_validator.py` codepath that:
1. Reads price from a different asset class by mistake (cross-pair contamination)
2. Force-marks closure as WON regardless of pnl sign

## Penny-skyrocket NOT REGISTERED — confirmed

`penny-skyrocket-runner.yml` exists on `main` since PR #546 (commit `2c61d1fdb92`) but `gh api ... actions/workflows --paginate` does not return it. Means GitHub never registered the workflow. Possible YAML-lint blocker; need to validate.

## What changed in priorities

Top 3 actionable fixes (rank order):
1. **`multi_asset_copytrader` closer** — fix the cross-pair price-lookup bug + add status validation (negative pnl_pct must be LOST, not WON). Hits 1,247 rows. **Highest-impact data-integrity fix.**
2. **PnL recompute integrity** — 43.22% mismatch on sampled rows. Likely related to #1 (storage layer != arithmetic).
3. **Penny-skyrocket workflow registration** — manually trigger or fix YAML; restarts EQUITY pipeline.

## Done since checkpoint 3

- ✅ outcome_coverage discrepancy reconciled (both right, different defs)
- ✅ WON-mislabel root cause traced to `multi_asset_copytrader` source
- ✅ multi_asset_copytrader_scraper writes status=OPEN; closer is the bug
- ⏳ Closer location not yet pinpointed (forward_validator + outcome_resolver have no `multi_asset_copytrader`-specific code per grep)

## Bg state

- Pid 3257 — 2nd full health-run completion not yet logged. May still be in flight at T+50m of run; expected ~14-15 min total. Check next checkpoint.

## Up next

- Find the actual multi_asset_copytrader closer (probably a resolver or live-monitor module)
- Validate penny-skyrocket-runner.yml YAML
- Schedule next wakeup at T+20m
