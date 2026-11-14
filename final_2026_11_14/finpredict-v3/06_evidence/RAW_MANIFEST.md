# Evidence Manifest — finpredict-v3 (2026-11-14)

## Live payload referenced (read-only)
- `audit_dashboard/data/dashboard_data.json` (live site copy, generated 2026-11-14T14:30Z)
- `/tmp/kilo/dashboard_data_latest.json` (same payload cache used by the guardian/harness)

## Verified live defects (from guardian run)
| Defect | Live evidence |
|---|---|
| STALE_CRYPTO_PRICE | XRPUSDT / BTCUSDT `current_price == entry_price` while Binance moved +0.9%/+1.3% |
| FROZEN_CLOSED_PHANTOM | 11 closed FOREX rows `pnl_pct=0.0`, `exit_reason=UNKNOWN`, `exit_price==entry_price`, dated Mar 2026 |
| DATE_ONLY_SEED | `ES=F` active pick `signal_time`/`entry_time` = bare `"2026-11-14"` |
| NULL_PRICE | BOND/FUTURES current_price null; zombies per class |
| FABRICATED_FLAT_PNL_COHORT | flat-3% cohort (286 trades, every win exactly +3.00%, zero losers) |

## Horizon harness results (recorded realized trades)
- `results/horizon_validation_n60.txt`: 6 groups tested, 0 passed all gates
- `results/horizon_validation_n30.txt`: 26 groups tested, 0 passed all gates
- Best (still fail): ETF rs-breakout-scout n=78 WR 57.7% CI_lo 46.6% PF 1.75; CRYPTO luxalgo_confluence n=1,290 WR 42.9% CI_lo 40.3% (anti-skill).

## ML code findings (file:line)
- Target leakage: `ml_gatekeeper/gatekeeper.py:170-186`, `ab_router.py:28-38` (leaky sleeve live at gatekeeper.py:1002)
- Look-ahead: `claude_gainer_ml/train_model.py:685-711`
- Random-shuffle split: `scripts/sports_ml.py:47`
- Zero precision: `claude_gainer_ml/models/training_meta.json` (test precision/recall/F1=0.0 at threshold 0.75)

## Tests (all passing)
- `tests/test_pi_data_hygiene.py` (14) + `tests/test_pi_fundamental_ranker.py` (4) = 18 passed.

## Production change already on origin/main (needs sign-off)
- Commit `d8c8dd25581`: `ml_gatekeeper/gatekeeper.py` `_drop_leakage_enabled()` default FLIPPED to ON.
