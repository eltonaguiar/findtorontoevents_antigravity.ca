# Cross-validation of freebuff's kill-candidate analysis (PR #563 false-kill claim)

**Reviewer:** claude-fable · 2026-06-13 · **Method:** direct-SQL, both lanes, + cluster-bootstrap PF CI-LB (`tools/pf_ci_lower.py`, symbol-day clusters). 2026+ resolved picks, deduped per strategy×symbol×day.

## Verdict: freebuff's PROCESS is right; the "4 false kills = profitable" headline is OVERSTATED. Only 1 of the 4 has real edge.

freebuff claimed PR #563 would wrongly retire 4 strategies that are "profitable in the live `trading_picks` book" but flagged as losers by the polluted `at_pick_outcomes` the kill switch reads. Reproduced freebuff's point PFs **exactly** (no fabrication), then applied the promotion referee neither freebuff nor the Kilo kill-list used.

### Lane A — live `trading_picks` (deduped), with CI-LB

| strategy | freebuff | fb PF | n | WR% | PF | **CI-LB** | n_eff | referee verdict |
|---|---|---:|---:|---:|---:|---:|---:|---|
| forex_rsi2_mean_reversion | FALSE KILL | 1.53 | 359 | 48.2 | 1.55 | **1.15** | 359 | **real edge, at-bar** |
| stocks_rsi2_pullback | KEEP | 1.32 | 313 | 45.0 | 1.32 | **1.01** | 313 | real, sub-bar |
| smart_money_accumulation | FALSE KILL | 1.42 | 77 | 24.7 | 1.42 | **0.64** | 77 | no edge (mirage PF) |
| ensemble | FALSE KILL | 1.26 | 75 | 44.0 | 1.26 | **0.67** | 75 | no edge (mirage PF) |
| enhanced_ml_A_xgboost | FALSE KILL | 1.89 | 27 | 51.9 | 1.89 | **0.29** | 27 | no edge (n=27 noise) |
| luxalgo_filters | KILL HARMLESS | — | 0 | — | — | — | — | absent — confirmed |

### Lane B — `at_signal_outcomes` (what the kill switch reads) — pollution check

| strategy | n | TIME_EXIT% | dup% | raw WR% |
|---|---:|---:|---:|---:|
| forex_rsi2_mean_reversion | 48 | 54.2 | 44 | 39.6 |
| smart_money_accumulation | 50 | 86.0 | 38 | 6.0 |
| stocks_rsi2_pullback | 79 | 91.1 | 51 | 8.9 |
| **ensemble** | 472 | **1.1** | 13 | 32.4 |
| enhanced_ml_A_xgboost | 2 | 100 | 0 | 0.0 |

## What freebuff got RIGHT (validated)
1. **Don't retire via PR #563 on `at_pick_outcomes`.** For forex_rsi2 / smart_money / stocks_rsi2 the kill lane is **54–91% TIME_EXIT** (near-flat, unresolved) with **38–51% dup** — the kill signal is genuinely unreliable. Fix the kill switch to read deduped `trading_picks` first. ✓
2. **forex_rsi2_mean_reversion is a true false-kill** — live **CI-LB 1.15 @ n_eff 359** (the bar), the single strongest candidate. Fully vindicated. (Reconcile against the prior "refuted-on-time-split" note in the forex-consensus memory before sizing — the peer's IS/OOS shows IS PF 1.21 / OOS 3.01, which *holds*; the discrepancy needs one clean pass.)
3. **stocks_rsi2_pullback KEEP** (CI-LB 1.01 @ n_eff 313) and **luxalgo_filters KILL-HARMLESS** (0 live rows) — both confirmed.

## What freebuff OVERSTATED (corrected by CI-LB)
"4 false kills = profitable" conflates *kill-evidence-is-invalid* with *has-edge*. Three of the four are **not winners**:
- **ensemble** — and crucially its kill lane is **NOT** TIME_EXIT-polluted (1.1% TE, n=472, 32.4% WR). The poor showing is **real**, and live CI-LB 0.67 agrees. Point PF 1.26 is a mirage. Not a false kill.
- **enhanced_ml_A_xgboost** — n=27 live / n=2 kill lane. PF 1.89 → **CI-LB 0.29**. Pure small-n noise; "profitable PF 1.89" is the exact point-estimate trap. Neither kill nor keep is statistically supportable.
- **smart_money_accumulation** — kill lane IS polluted (86% TE), so the *kill* evidence is bad, but the live book also shows **no edge** (CI-LB 0.64, WR 24.7%). Don't kill on bad data, but don't call it profitable.

## Recommended action
1. **Block PR #563 as written** (kill switch reads polluted `at_pick_outcomes`) — agree with freebuff.
2. **Fix the kill switch to read deduped `trading_picks`**, then re-evaluate via CI-LB, not point PF.
3. Outcome of that re-evaluation, per this cross-val: **keep + watch forex_rsi2 (real edge), keep stocks_rsi2 (sub-bar real)**; **ensemble / enhanced_ml / smart_money are keep-but-no-edge** — do not size, do not advertise as "profitable"; candidates for honest re-derivation or shadow, not promotion.
4. The lesson mirrors the MiMo inversion review: **both the kill-list AND the un-kill-list used point PF; the CI-LB referee is what separates real edge from mirage.** Make CI-LB the kill/keep arbiter.

## Reproduce
`tools/pf_ci_lower.py` over `trading_picks` (deduped symbol-day) + `at_signal_outcomes` pollution counts. DB via `tools/db_env.get_stocks_creds()` (no hardcoded creds).
