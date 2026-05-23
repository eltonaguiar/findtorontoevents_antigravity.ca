# COT Timing-Leakage Audit — CONFIRMED — 2026-05-13

**Trigger:** DeepSeek V4-Pro flagged this as the most likely failure mode for the `cot_positioning` paper pilot (DSR=1.0, WR=90%, n=100). Three external models (DeepSeek + Loker-480B + GPT-OSS-120B) plus an internal Explore subagent at 98% confidence converged on the same finding. **VERDICT: LEAKAGE-CONFIRMED.**

## The bug

CFTC publishes the COT report Friday ~3:30pm ET, covering positions as of the **prior Tuesday's** settlement. [alpha_engine/cot_positioning.py:144](alpha_engine/cot_positioning.py#L144) was using `datetime.now()` as the pick timestamp and emitting picks immediately on fetch — picks generated Wed/Thu used Tuesday-settled data that wasn't public until Friday. Documented requirement at [docs/STRATEGY_PROPOSALS_V1_2026_04_19.md:205](docs/STRATEGY_PROPOSALS_V1_2026_04_19.md#L205) ("Friday close at earliest") existed; code did not enforce it.

DeepSeek estimate: lag-corrected backtest typically halves the WR. CT=F's reported 90% likely becomes 45-55%.

## Fix shipped — PR #941

`_is_cot_row_public()` + `COT_PUBLICATION_LAG_DAYS=3` constant + guard at signal emission. Requires the CFTC row's `report_date` be ≥ 3 calendar days before "today" before any pick using it can be emitted. 8/8 new tests pass in `tests/test_cot_timing_lag.py`.

## Acceptance gate before 2026-05-23 paper-pilot graduation

1. PR #941 merged
2. Re-run cot_paper_pilot backtest on full 100-pick history with the lag patch live
3. Lag-corrected WR must hold ≥ 75% (was 90%; conservative gate)
4. DSR on lagged series ≥ 0.85
5. 4-week paper pilot continues running WITH the patch; new WR ≥ 75% over that window

**If lagged WR drops to DeepSeek's predicted 45-55%:** pilot returns to REHAB, 2026-05-23 graduation rejected, COMMODITY headline numbers must be re-attributed to broader factors (zero-PnL artifact filter `bb083ab5ec` + forex_copy_trader suppression `c0f1c135dc` per [reports/commodity_bond_forensic_2026-05-13.md](reports/commodity_bond_forensic_2026-05-13.md)).

## Multi-model convergence (procedural)

| Source | Hypothesis | Method |
|---|---|---|
| DeepSeek V4-Pro | Named COT release-vs-settlement timing gap unprompted | Prompt only (no code access) |
| GPT-OSS-120B | "Backtest timestamp hygiene audit" flagged as missing item | Prompt only |
| Loker-480B | "Friday release vs Tuesday settlement is a textbook lookahead bias vector" verbatim + named the embargo test | Prompt only |
| Explore subagent | LEAKAGE-CONFIRMED at 98% confidence; cited [cot_positioning.py:107](alpha_engine/cot_positioning.py#L107), [:144](alpha_engine/cot_positioning.py#L144), [docs/STRATEGY_PROPOSALS_V1_2026_04_19.md:205](docs/STRATEGY_PROPOSALS_V1_2026_04_19.md#L205) | Code read |

The combined sequence — external first-principles hypothesis → internal code audit → surgical PR with tests — caught this before any live capital was sized against the headline number.

This procedure goes into the standard toolkit. Internal swarms have a confirmed failure mode of asserting false root causes (4 caught this session). External models have the inverse failure mode of hypothesizing without code access. Together they cover both.
