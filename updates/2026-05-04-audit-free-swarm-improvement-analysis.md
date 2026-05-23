# Audit Free-Swarm Improvement Analysis - 2026-05-04

## Scope

Goal #1: improve `findtorontoevents.ca/audit` toward hedge-fund-grade performance across asset classes.

This note summarizes a free/subscription-bundled `tools/swarm` audit pass, then red-teams the model feedback against first-party repo evidence. Treat this as an action plan, not a promotion memo.

## Swarm Run

Prompt:

- `swarm_runs/briefing_audit_improvement_2026_05_04.md`

Command:

```powershell
python tools/swarm/swarm_run.py --prompt-file swarm_runs/briefing_audit_improvement_2026_05_04.md --engines gemini,kilo,kimi,agent,codex --max-parallel 3 --cost-cap-usd 0 --out-dir swarm_runs/run_audit_improvement_free_20260504
```

Health check:

```powershell
python tools/swarm/swarm_inspect.py swarm_runs/run_audit_improvement_free_20260504
```

Result:

- `kimi`: content-bearing, schema-invalid (`PARSE_FAILED`), used only as commentary.
- `kilo`: content-bearing, schema-invalid (`PARSE_FAILED`), used only as commentary.
- `codex`: unusable; free usage limit hit.
- Remaining engines did not produce usable files before the hung run was stopped.

## Current Evidence Snapshot

Source: `audit_dashboard/data/dashboard_data.json`, generated `2026-05-05T00:49:03.235562+00:00`.

| Class | n | WR% | PF | PnL% | Status | Sizing |
|---|---:|---:|---:|---:|---|---|
| FOREX | 1249 | 45.6 | 0.28 | -986.16 | stressed | false |
| EQUITY | 428 | 52.8 | 1.42 | 276.23 | stable | true |
| CRYPTO | 8166 | 44.8 | 1.26 | 2198.61 | watch | true |
| COMMODITY | 816 | 48.7 | 2.08 | 285.05 | stable | true |
| ETF | 88 | 53.4 | 1.20 | 19.79 | candidate | false |
| BOND | 18 | 55.6 | 1.72 | 3.41 | thin_sample | false |
| FUTURES | 2 | 100.0 | n/a | 0.00 | insufficient_data | false |

Strict Tier 2 class gate remains: `PF > 1.5`, `WR > 50%`, `MDD < 20%`, `n >= 100`.

No asset class clears all class-level Tier 2 gates in this snapshot. `signal_validation` is the strongest confirmed system-level candidate: `total_resolved=200`, `PF=2.51`, `MDD=12.0`, `avg_trade_pnl=0.94`, no concentration warning.

## Verified Improvement Areas

1. **FOREX needs immediate rehab, not silent death.**  
   FOREX is still the only large-sample stressed class: `n=1249`, `PF=0.28`, `WR=45.6%`, `PnL=-986.16%`, sizing already halted. This triggers `docs/MUTATION_THREE_AXIS_PROTOCOL.md` and the rehabilitation-first path in `TESTING_PROTOCOL.MD`.

2. **`kimi_signal_tracking` is the largest clean-metric drag.**  
   Current clean metrics show `total_resolved=177`, `PF=0.26`, `total_pnl_raw=-958.10`, `avg_trade_pnl=-5.41`, `MDD=994.95`. `USDCHF=X` is the top loss dependency at `-441.77` PnL contribution. This needs a symbol and direction autopsy before any kill decision.

3. **Concentration risk is real, but quote it carefully.**  
   `alpha_engine` depends heavily on `INJUSDT`: removing it drops raw PnL from `+363.72%` to `+39.6%`. `multi_asset_copytrader` flips from `+7.01%` to `-32.8%` without `CT=F`. `rapid_fire` drops from `-10.01%` to `-35.2%` without `ZECUSDT`. The `top_symbol_pnl_pct` values over 100% are near-zero-denominator artifacts, so the actionable metric is "remove top symbol and recompute PnL," not the inflated percentage alone.

4. **CRYPTO is watch-only by charter, even though `sizing_allowed=true`.**  
   CRYPTO has adequate sample (`n=8166`) but fails both core Tier 2 quality gates: `PF=1.26` and `WR=44.8%`. The JSON currently allows sizing because `watch` is treated permissively. That is a policy/gate concern, not proof that CRYPTO is Tier 2.

5. **Several profitable-looking systems are not promotion-ready.**  
   `aggregated_picks` has `PF=2.25`, but `MDD=21.81` breaches the Tier 2 MDD cap and `TSTUSDT` contributes `29.8%` of raw PnL. `non_crypto_consensus` has `PF=1.55` and `n=113`, but `total_pnl_raw=0.03` and `avg_trade_pnl=0.00`, so any realistic cost model erases the edge.

## Mutation Targets

These should enter SANDBOX mutation/backtest lanes before any blocklist expansion:

| Target | Evidence | Mutation lane |
|---|---|---|
| `ig_contrarian_sentiment` | SHORT `57.1%` WR / `42` trades vs LONG `19.2%` / `120`; spread `38pp` | SHORT-only sandbox |
| `myfxbook_retail_contrarian` | SHORT `46.2%` / `13` vs LONG `10.2%` / `88`; spread `36pp` | SHORT-only sandbox, but sample caveat |
| `cta_cross_asset_tsmom` | SHORT `65.6%` / `64` vs LONG `33.9%` / `56`; spread `32pp` | SHORT-only sandbox |
| `forex_rsi2_mean_reversion` | SHORT `27.3%` / `11` vs LONG `2.4%` / `82`; both weak, but LONG is toxic | Pause LONG; test inverse/alternate regime |
| `multi_asset_copytrader` | `CT=F` winner dependency; `SI=F`, `AMD`, `ZW=F` worst slices | Symbol allow/block SANDBOX |
| `quan_engine` | `MATICUSDT` `0%`, `ONDOUSDT` `22%`, `SOLUSDT` `23%`; better slices include `XRPUSDT` `51.0%` / `51` | Symbol blocklist plus allowlist test |
| `rapid_fire` | `ENJUSDT` `88.9%` / `9`; `UUSDT` `0%` / `34`, `ESPUSDT` `0%` / `5` | Symbol blocklist plus min-n guard |

Downgrade: the free-swarm output suggested `quan_engine_swing` as a direction-split target. The local mutation output from this pass showed it, but the later red-team found prior repo reports did not consistently corroborate that slice. Keep it as "needs separate verification," not as a confirmed action.

## Rejected Or Downgraded Feedback

- **"CRYPTO is stable/proven."** Rejected. It is `watch` with `PF=1.26` and `WR=44.8%`, below class-level Tier 2 gates.
- **"BOND can size because PF/WR look good."** Rejected. `n=18` is below the `n>=100` floor.
- **"FUTURES has 100% WR."** Rejected as meaningless at `n=2`.
- **"`aggregated_picks` is Tier 2."** Downgraded. PF is strong, but `MDD=21.81` violates the cap.
- **"`non_crypto_consensus` is proven."** Downgraded. `avg_trade_pnl=0.00` and `total_pnl_raw=0.03` fail any cost-aware edge test.
- **"Top-symbol percentage over 100% equals position exposure over 100%."** Rejected. It is a percentage-of-total-PnL artifact; still useful only as fragility evidence.

## Next PR-Sized Step

Build a rehab gate, not a kill switch:

1. Add a SANDBOX directional-mutation runner for confirmed direction splits above `20pp` with minimum trade thresholds.
2. Add a symbol-dependency report that recomputes system PF/PnL after removing the top winner and top loser symbol.
3. Tighten audit sizing language so `sizing_allowed=true` is not displayed or interpreted as Tier 2 proof.
4. Open a FOREX deep-dive note focused on `kimi_signal_tracking` and the four confirmed direction-split candidates.

Acceptance gate for the follow-up PR:

- No system is promoted unless it clears post-cost PF/WR/MDD/n gates.
- No underperformer is hard-blocked unless the three-axis mutation report shows no recoverable symbol, direction, or timeframe slice.
- CRYPTO remains watch-only until class PF clears `1.5` and WR clears `50%`, or the dashboard explicitly documents why a looser sizing rule is intentional.

## Verification

Ran:

```powershell
python tools/mutation_analysis.py --json
python tools/swarm/swarm_inspect.py swarm_runs/run_audit_improvement_free_20260504
```

Also cross-checked the surviving swarm claims against `audit_dashboard/data/dashboard_data.json`, `docs/MUTATION_THREE_AXIS_PROTOCOL.md`, and `TESTING_PROTOCOL.MD`. Schema-invalid swarm outputs were not treated as authoritative.
