# GPT-5.5 Audit Chain Feedback - 2026-05-05T0121Z

Agent: GPT-5.5  
Surface: `findtorontoevents.ca/audit`  
Goal: Goal #1, hedge-fund-grade audit performance across all asset classes.

## End-To-End Checks

I checked the full feedback chain before writing this:

- Payload source: `audit_dashboard/data/dashboard_data.json`, generated `2026-05-05T00:49:03.235562+00:00`.
- Generator logic: `audit_trail/dashboard_generator.py` via `compute_asset_class_health`.
- Syntax sanity: `python -c "import py_compile; py_compile.compile('audit_trail/dashboard_generator.py', doraise=True)"`.
- Rehab evidence: `python tools/mutation_analysis.py --json`.
- Swarm health: `python tools/swarm/swarm_inspect.py swarm_runs/run_audit_improvement_free_20260504`.

Important chain finding: `sizing_allowed` is currently driven by `status in ("stable", "watch")`, not strict Tier-2 charter gates. That means CRYPTO `sizing_allowed=true` is a policy/gate weakness, not a JSON parse defect.

## Current Class Verdicts

| Class | n | WR% | PF | PnL% | Dashboard status | GPT-5.5 verdict |
|---|---:|---:|---:|---:|---|---|
| FOREX | 1249 | 45.6 | 0.28 | -986.16 | stressed | Highest priority rehab |
| EQUITY | 428 | 52.8 | 1.42 | 276.23 | stable | Candidate; PF below Tier 2 |
| CRYPTO | 8166 | 44.8 | 1.26 | 2198.61 | watch | Watch-only; fails PF and WR gates |
| COMMODITY | 816 | 48.7 | 2.08 | 285.05 | stable | Strong PF, WR below Tier 2 |
| ETF | 88 | 53.4 | 1.20 | 19.79 | candidate | Under-sampled and PF weak |
| BOND | 18 | 55.6 | 1.72 | 3.41 | thin_sample | Promising only as observation |
| FUTURES | 2 | 100.0 | n/a | 0.00 | insufficient_data | Not analyzable |

Strict class-level Tier 2 requires `PF > 1.5`, `WR > 50%`, `MDD < 20%`, and `n >= 100`. No asset class clears all class-level gates in this snapshot.

## Strongest Confirmed System

`signal_validation` is the only clean Tier-2 style system I would treat as real right now:

- Tier card: `n=203`, `WR=63.1%`, `PF=2.56`, `MDD=12.0%`, assets `CRYPTO` and `FOREX`.
- Clean metrics: `total_resolved=200`, `PF=2.51`, `avg_trade_pnl=0.94`, `MDD=12.0`, no concentration warning.

Do not generalize this to a class-level promotion. It is a system-level edge and needs controlled sizing and continued forward monitoring.

## Highest-Priority Fixes

1. **FOREX rehab lane:** open a dedicated rehab issue/PR for `kimi_signal_tracking` and the confirmed FX direction splits. FOREX is `PF=0.28` with `-986.16%` raw PnL, so it cannot remain a passive dashboard row.
2. **Mutation gates before kill:** run SHORT-only SANDBOX variants for `ig_contrarian_sentiment`, `myfxbook_retail_contrarian`, `quan_engine_swing`, `cta_cross_asset_tsmom`, and a toxic-LONG pause for `forex_rsi2_mean_reversion`.
3. **Symbol-dependency reporting:** add a dashboard artifact that recomputes PF/PnL after removing the top winner and top loser per system. Current `top_symbol_pnl_pct` is useful but misleading when total PnL is near zero.
4. **CRYPTO sizing semantics:** rename or split `sizing_allowed` into `risk_budget_allowed` vs `tier2_sizing_allowed`, or force Tier-2 gates for class-level sizing.
5. **Candidate demotion hygiene:** mark `aggregated_picks` as candidate only (`MDD=21.81%`), and `non_crypto_consensus` as unproven/cost-failed (`avg_trade_pnl=0.00`, `total_pnl_raw=0.03`).

## Per-Asset Notes

Per-asset suggested fixes are in:

- `reports/audit_asset_feedback_2026-05-05T0121Z_FOREX.md`
- `reports/audit_asset_feedback_2026-05-05T0121Z_CRYPTO.md`
- `reports/audit_asset_feedback_2026-05-05T0121Z_EQUITY.md`
- `reports/audit_asset_feedback_2026-05-05T0121Z_COMMODITY.md`
- `reports/audit_asset_feedback_2026-05-05T0121Z_ETF.md`
- `reports/audit_asset_feedback_2026-05-05T0121Z_BOND.md`
- `reports/audit_asset_feedback_2026-05-05T0121Z_FUTURES.md`

## Claims I Do Not Trust

- "CRYPTO is proven because total PnL is positive." False; class PF and WR fail Tier 2.
- "COMMODITY is done." False; PF is strong, but WR is below 50%.
- "BOND can size." False; `n=18`.
- "FUTURES has 100% WR." Meaningless at `n=2`.
- "`aggregated_picks` is Tier 2." False; MDD breaches the cap.
- "`non_crypto_consensus` is deployable because PF is 1.55." False; zero average PnL is erased by costs.

## Suggested Next PR

Title: `feat(audit): add rehab-first asset-class gate reports`

Scope:

- Generate a JSON/MD symbol-dependency report for systems with `n >= 100`.
- Add a class-level `tier2_sizing_allowed` field that uses charter gates, keeping current `sizing_allowed` only if the UI needs a softer "not stressed" label.
- Emit a FOREX rehab queue from `tools/mutation_analysis.py --json` output.

Acceptance:

- CRYPTO no longer appears as class-level Tier-2 sizeable while `PF=1.26` and `WR=44.8%`.
- `kimi_signal_tracking` has a documented symbol/direction rehab path.
- No strategy is hard-killed without a three-axis mutation result.
