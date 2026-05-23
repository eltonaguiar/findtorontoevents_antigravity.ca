# CRYPTO Edge Artifact Audit — 2026-05-17

**Source:** External 2-engine swarm second opinion (deepseek + xai) on a
reproduction-grade prompt with 22 real `recent_closed` trades + the verbatim
`dashboard_generator.py` aggregation code. Run dir:
`swarm_runs/second-opinion-crypto-v2-20260517/`. Claims then cross-checked
against the codebase by 4 parallel subagents.

**Headline:** Both engines reproduced PF from the 22-row sample and got
**PF 0.83–0.99 (below 1.0)** — inconsistent with the claimed CRYPTO aggregate
PF 1.33. The codebase cross-check **confirms 4 of 6 data-integrity claims** and
**confirms the fixed-TP artifact** on the "elite" sources. Two claims were
PARTIAL (real but milder/mis-framed). Net: the 1.33 PF is genuinely
contaminated; the worst confirmed bugs are survivorship (A3), zero fee model
(A4), and fixed-TP ghost rows (B2). Plus two **new** findings the subagents
surfaced (see §D).

## A. Data-integrity claims — cross-checked

| ID | Claim | Verdict | Evidence |
|----|-------|---------|----------|
| A1 | Look-ahead / timestamp inversion in `crypto_ml_edge` (`entry_time` after `closed_at`). | **PARTIAL** | Inversion is real but it is NOT trading look-ahead. `entry_time` is overwritten with the dashboard run-time because `universal_pick_resolver.py:469-485` `_SCORING_FIELDS` drops `signal_time`/`entry_time`/`closed_at`; generator backfills run-time when `entry_ts==""`. Source file `crypto_ml_edge/data/active_picks.json` has correct `signal_time` < `closed_at`. PnL/PF unaffected (derive from prices). Only corrupts `age_hours`/staleness analytics. |
| A2 | Mirror padding — `baby_strats_forward` LONG+SHORT pairs at identical prices, both counted. | **PARTIAL** | Mirror pairs real (~22 groups / 8% of sample rows) but NOT deliberate padding — emergent collision of *independent* baby strategies firing opposite signals on the same shared bar series (`incubator/validation/update_forward_matches.py:247-307`). Net pnl contribution 0; WR shifted ~0.2pp. Minor data-hygiene issue, not a metrics-padding bug. |
| A3 | Survivorship — blocked source systems' historical trades stay in the aggregate. | **CONFIRMED** | `BLOCKED_SOURCE_SYSTEMS` (`quality_gates.py:1688`) is **never imported** into `dashboard_generator.py`; `_get_blocked_sets():4515` omits it; only enforced in `passes_active_gate` (generation-time). Blocked sources' history (e.g. `ml_crypto_pred_v12` PF 0.55, `crypto_winners` PF 0.30) still flows into the CRYPTO aggregate. |
| A4 | Zero cost term — PF from gross `pnl_pct`. | **CONFIRMED** | `compute_pnl` (`outcome_resolver.py:650-660`) is a pure price ratio; `:964` writes gross. A net field `_pnl_pct_net` exists (`charter_slippage.py`, CRYPTO 4 bp one-way) but is **display-only**; `ac_breakdown:14310` reads the gross field. |
| A5 | `pnl_pct == 0` trades inflate `closed` count, not wins/losses. | **CONFIRMED** | `dashboard_generator.py:14307` increments `closed` before the `if pnl>0 / elif pnl<0` branches (`:14318-14321`); 0 hits neither. (Minor — upstream filters strip most auto-expired/zero-exit rows; only genuine break-evens survive.) |
| A6 | Gross-% equal-weighted PF, not dollar/duration-weighted. | **CONFIRMED** | `:14311/14320/14323` add raw `pnl_pct`; no notional/position/duration multiplier. A 5% scalp on $10 == a 5% gain on $100k. |

## B. Elite-source artifact claims — cross-checked

`kimi_signal_tracking` / `aggregated_picks` / `signal_validation`.

| ID | Claim | Verdict | Evidence |
|----|-------|---------|----------|
| B1 | Single-symbol dominance (>60% one symbol). | **REFUTED** (source level) | Max source-level share: aggregated_picks ETHUSDT 20.4%, signal_validation USD-JPY 14.6%. No MATIC-style pattern. NOTE: at *strategy* level, `AuditEnsemble_LONG` is 87% BTCUSDT (97/112) — concentration exists one layer down. |
| B2 | Fixed-TP ghost rows (identical TP, no exit variation). | **CONFIRMED** | aggregated_picks 19/27 wins (70%) at *exactly* +3.5%; signal_validation 17/21 wins (81%) at *exactly* +3.0%, and all 21 wins' TP-distance exactly 3.0%. Wins credited at nominal TP, not verified exit fills. |
| B3 | Unresolved/flat marked WON. | **PARTIAL** | No OPEN-as-WON; 15 flat rows correctly excluded. But 4/21 signal_validation WONs are `TIME_EXIT` partial exits below TP graded WON on any positive pnl — softer version of the artifact, modestly inflates WR. |

## C. Proposed fixes / enhancements (ranked by confirmed impact)

| ID | Fix | Targets | Priority |
|----|-----|---------|----------|
| C2 | Use the existing `_pnl_pct_net` (charter slippage, CRYPTO 4 bp) — or subtract 5–8 bp round-trip — in the `ac_breakdown` PF/WR computation instead of gross `pnl_pct`. | A4 (CONFIRMED) | **P0** — cheapest, biggest truth-gain; net field already exists. |
| C3 | Import `BLOCKED_SOURCE_SYSTEMS` into `dashboard_generator.py` and exclude blocked sources' historical trades from `ac_breakdown` (or surface a separate "legacy" ledger). | A3 (CONFIRMED) | **P0** — removes known losers (PF 0.30–0.55) from the live verdict. |
| C4 | Correct the `m004` autopsy + add an n-floor: report `resolved_picks` (not `closed_picks`) as sample size; require n≥100 valid resolved before "proven". | §D1 | **P0** — current "scale the elites" advice rests on a 57× inflated n. |
| C1 | Resolve fixed-TP ghost rows: credit wins at a *verified* exit price, not the nominal TP target; treat `TIME_EXIT` partials by their real pnl distribution. | B2 (CONFIRMED), B3 (PARTIAL) | **P1** — explains the implausible PF 4.5–5.8. |
| C5 | Add `signal_time`/`entry_time`/`closed_at` to `_SCORING_FIELDS` in `universal_pick_resolver.py` so `entry_time` is not overwritten with run-time. | A1 (PARTIAL) | **P2** — fixes age/staleness analytics; no PF impact. |
| C6 | Dedupe same-bar opposite-direction baby-strat collisions in the resolver. | A2 (PARTIAL) | **P3** — ~0.2pp WR effect; cosmetic. |

## D. New findings surfaced by the cross-check (not in the swarm output)

**D1 — The `m004_crypto_drag_autopsy_20260515.md` numbers are wrong.**
`kimi_signal_tracking` real verifiable sample is **n=21**, not 1198 — the
autopsy cited `closed_picks` (1203) while 1182 are `excluded_closed` by
`_is_valid_resolved_pick`. A 57× overstatement. The autopsy's recommendation to
"scale kimi_signal_tracking + aggregated_picks into active picks" rests on
inflated sample sizes and must not be acted on. The autopsy should be corrected.

**D2 — `aggregated_picks` is a loser, not a star, and the data contradicts itself.**
`systems[].aggregated_picks` shows PF 4.54 / +763.92 PnL, but
`system_clean_metrics.aggregated_picks` shows PF 0.54 / avg_trade −0.70 /
total_pnl −82.55. The two aggregates flatly disagree — a data-integrity bug.
The autopsy cited the optimistic one. Reconcile `systems[]` vs
`system_clean_metrics` before trusting either.

## E. Bottom line

The swarm's headline (PF 1.33 is contaminated, true crypto edge likely ≤ 1.0)
**survives cross-check.** But the mechanism is not the dramatic "look-ahead +
deliberate padding" the engines framed — it is **(1) no fee model, (2) blocked
losers still counted, (3) wins credited at nominal TP instead of real fills,
and (4) inflated sample sizes in the source-of-truth autopsy.** P0 fixes
C2/C3/C4 are small, mechanical, and should precede any decision to size up
CRYPTO. Do not act on the `m004` "scale the elites" recommendation.
