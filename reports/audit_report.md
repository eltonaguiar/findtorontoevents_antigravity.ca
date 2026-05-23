# Crypto Audit v3 Report

- run_time: `2026-03-16 12:20:28 UTC`
- closed_csv: `antigravity_closed_picks_2026-03-16.csv`
- active_csv: `antigravity_active_picks_2026-03-16.csv`
- features: `['Score_num', 'signal_score', 'consensus_score', 'noconflict_score', 'confluence_num', 'trust_tier_ord', 'grade_ord', 'trust_mult', 'system_prior_wr', 'system_prior_pnl']`
- calibration: `sigmoid`

## Hard Gate Config

- hard_block_systems: `alpha_engine_fast`
- hard_long_min_score: `20.0`
- hard_allow_shorts: `False`
- combine_with_model_gate: `False`

## Data Integrity

- closed_rows_before_dedupe: `1908`
- closed_rows_after_dedupe: `1114`
- duplicate_rows_removed: `794`
- duplicate_keys_with_repeats: `193`
- trusted_rows: `592`
- train_rows: `473`
- holdout_rows: `119`

## Direction Model Summary

| direction | train_n | holdout_n | oof_auc | holdout_auc | train_threshold | final_threshold | train_gate_trades | holdout_gate_trades |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| LONG | 330 | 104 | 0.9481 | 0.4915 | 0.83 | 0.83 | 49 | 103 |
| SHORT | 143 | 15 | 0.4912 | 0.8056 | None | None | 0 | 0 |

## Active Gate Summary

- active_rows_total: `502`
- active_model_gate_pass_rows: `315`
- active_hard_gate_pass_rows: `115`
- active_final_gate_pass_rows: `115`
- active_final_gate_pass_pct: `22.91%`

| direction | rows | passes | pass_rate |
|---|---:|---:|---:|
| LONG | 380 | 115 | 30.26% |
| SHORT | 122 | 0 | 0.00% |

