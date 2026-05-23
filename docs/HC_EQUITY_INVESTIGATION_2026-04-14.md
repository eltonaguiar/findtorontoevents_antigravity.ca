# HC equity pipeline investigation (2026-04-14)

This document records root-cause analysis for why **strict High Conviction (HC)** showed few or no **equity** picks, and what was shipped to address it.

## Finding 1: `null_ml_solo_source` depressed goldmine scores (real bug)

**Symptom:** Many `goldmine_stocks` rows showed `null_ml_solo_source(1):-20` in penalties while `ml_score` / `ml_composite_score` in the **final** payload were populated (e.g. 61).

**Cause:** `_apply_score_penalties()` in `audit_trail/quality_gates.py` can run when both ML fields are still empty; later enrichment fills them but the score is not recomputed, so the penalty list reflects a stale assessment.

**Shipped fix:** Exempt `source_system == goldmine_stocks` from the null-ML solo/dual penalty block. Goldmine consensus rows use consensus / `avg_score` as the effective ML signal; treating “missing ml_composite” the same as a null upstream ML row was incorrect for this source.

**Impact:** Restores ~+20 on affected goldmine rows for gate thresholds that depend on the adjusted score (e.g. Gates 1–2 style floors in the audit UI). It does **not** by itself fix forward-sample gates if `strat_fwd_trades` is still zero.

## Finding 2: `regime_terminal` forward WR misread

An earlier ~60% forward win rate quote was traced to the wrong field / snapshot. On strategy-level data, `regime_terminal` is **below** the usual ~45% forward-WR gate. Admitting it via tier-B shortcuts would not be statistically justified without new evidence.

## Finding 3: Tier-B bypass does not skip Gate 5

The tier-B supplemental path still runs HC Gates 1–7 and 9; it mainly bypasses consensus (Gate 8). Strategies failing **forward WR** (Gate 5) remain rejected.

## Finding 4: Goldmine had no closed history in the dashboard forward join

**Symptom:** Active goldmine picks showed `strat_fwd_trades == 0` because the **closed ledger** was not feeding the dashboard aggregation.

**Cause:** `data/goldmine/closed_trades.json` stores rows under the top-level key **`trades`**. `audit_trail/dashboard_generator.py` `_extract_picks()` did not consider that key, so the generic JSON loader returned **zero** picks from the goldmine closed file.

**Additional alignment:** For `goldmine_stocks` closed rows with an empty `strategy`, derive `goldmine_{N}x_consensus` from `consensus_count` or `algo_count` so forward stats join on the same strategy keys as active picks. Prefer-book PnL for closed rows now includes **`final_return_pct`** in the fallback chain.

**Verification (local):** After the change, `collect_all_picks()` yields **51** closed `goldmine_stocks` rows (exact count may vary with data files and dedup).

## What we did not change

- **`hc_gate_params.json` floors** — no broad relaxation without statistical review.
- **Strategy implementations** for `regime_terminal` / `super_signals` — quality work is out of scope for HC UI wiring.
- **Structural timing fix** for `_apply_score_penalties` vs `smart_picks_engine` — deferred; the goldmine exemption is the low-risk correction for the affected source.

## Files touched

- `audit_trail/quality_gates.py` — goldmine exemption for null-ML penalty.
- `audit_trail/dashboard_generator.py` — `trades` extraction, `final_return_pct`, goldmine strategy alignment on closed rows.

## Follow-ups

- Regenerate audit dashboard payload (`dashboard_generator` / CI) so production `dashboard_data.json` reflects new forward stats.
- Optional: reorder penalty application after ML merge for **all** sources (larger change; coordinate with ML ranker path).
