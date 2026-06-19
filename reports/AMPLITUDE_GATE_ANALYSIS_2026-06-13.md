# Amplitude / reachability gate analysis — 2026-06-13 (loop iteration 7)

**Goal:** prototype the #1 structural fix (amplitude-aware emission gate). **Result: the cost-based amplitude gate is useless, AND the real fix (a reachability gate) is currently UNBUILDABLE because the volatility data is missing/broken. The precise root cause of low realized amplitude is identified: targets are unreachable in the hold window + the ATR field is unusable.**

## Finding 1 — a cost-based amplitude gate filters NOTHING (targets already clear cost by 20–125×)

Gate `TP-distance ≥ k × round-trip-cost`, k∈{1,2,3}, deduped per symbol-day:

| Class | n | TP-dist p50 | TP-dist p90 | cost | all net PF | k=1 surv/PF | k=2 | k=3 |
|---|---|---|---|---|---|---|---|---|
| equity | 679 | 5.00% | 10.0% | 0.04% | 0.92 | 100%/0.92 | 100%/0.92 | 100%/0.92 |
| forex | 678 | 0.70% | 0.80% | 0.03% | 0.65 | 100%/0.65 | 100%/0.65 | 100%/0.65 |
| etf | 319 | 5.49% | 20.0% | 0.04% | 1.09 | 100%/1.09 | … | … |
| index | 80 | 4.83% | 6.92% | 0.04% | 1.57 | 100%/1.57 | … | … |
| bond | 58 | 0.99% | 2.65% | 0.03% | 1.05 | 100%/1.05 | … | … |

**Nothing is filtered** — the smallest typical target (FOREX 0.70%) is already ~23× the cost. So "raise the TP target" is the WRONG framing: targets are ambitious enough.

## Finding 2 — the real problem is REACHABILITY (precisely quantified on FOREX)

FOREX resolved status mix (raw 15,084):

| Status | n | share | avg \|pnl\| |
|---|---|---|---|
| **TIME_EXIT** | 11,809 | **78%** | **0.091%** |
| LOST | 2,238 | 15% | 0.037% |
| TP_HIT | 746 | **5%** | 0.114% |
| EXPIRED | 286 | 2% | 0.021% |
| SL_HIT | 5 | 0% | 0.448% |

**Picks aim for a 0.70% TP but only 5% ever reach it; 78% time-exit at ~0.09%.** The 0.70% target is unreachable in the (3-day) FOREX hold window given FX daily volatility. The tiny realized winners that killed the net edge are TIME_EXIT near-flat outcomes — not small targets. **This is a reachability problem: TP set too far for the hold window / volatility.**

## Finding 3 — a reachability gate is currently UNBUILDABLE (volatility data gap)

A reachability gate ("keep picks where TP ≤ R × ATR over the hold window") needs a usable per-pick volatility/expected-move. The data isn't there:

- `volatility_atr` is **0% populated** for FOREX, BOND, INDEX.
- For EQUITY it's ~98% "populated" but **near-zero / wrong-scale** (median `volatility_atr / entry ≈ 0`), so the reachability ratio is meaningless (R=1 keeps 0 picks, R=5 keeps 1%). Unusable.

## Verdict & recommendation (the corrected money-ready lever)

The bottleneck is **not** target amplitude vs cost. It is: **(a) TP targets are unreachable in the hold window (78% time-exit near-flat), and (b) the volatility/expected-move data needed to size reachable targets or build a reachability gate is missing or broken.**

Concrete fix sequence (this is the real path, replaces the vague "raise amplitude"):
1. **Fix the volatility data at emission** — populate a correct per-pick expected-move (ATR% or realized-vol over the hold window) for ALL classes (FOREX/bond/index currently 0%; equity wrong-scale). Without this, neither right-sizing nor a reachability gate is possible.
2. **Size TP to reachability** — set TP to ≈1–1.5× expected-move-over-hold so a meaningful fraction of picks actually reach it, instead of a fixed 0.7%/5% that 95% never touch.
3. **OR extend the hold window** for far targets (FOREX 3-day hold is too short for 0.7% in low-vol regimes).
4. Re-resolve intrabar (`verified_strategies/intrabar_replay_noncrypto.py`) and re-run the robustness gauntlet (#596) after the fix.

This reframes improvement-area #1: the lever is **reachability + volatility-data hygiene at the emission source**, not raising targets.

Reproduce: amplitude/reachability analysis in this session; cost model = `tools/forex_long_pilot_tracker.py`.
