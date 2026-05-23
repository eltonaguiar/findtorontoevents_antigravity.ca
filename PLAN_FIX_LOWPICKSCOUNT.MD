# Plan: Improve Struggling Asset Class Performance

## Status: Draft — awaiting user review

---

## Plan: Infrastructure for Non-Crypto Asset Class Recovery

**TL;DR:** Three asset classes are dead or decaying (ETF, FUTURES already blocked, COMMODITY decaying), one is low-quality in active picks (EQUITY), and FOREX has corrupted exit labels that make its metrics unreliable. The plan builds the infrastructure to block bad signals, surface real edge, and monitor health automatically — without doing anything destructive that can't be reversed.

---

## Phase 1 — Triage & Hard Blocks (quick wins, reversible)

**Goal:** Stop admitting picks we know are losing. Zero new analysis needed.

1. **Block ETF in `BLOCKED_ASSET_CLASSES`** — `FUTURES` is already there (line 729 of `audit_trail/quality_gates.py`). ETF has PF 0.28, Sharpe -5.78, 19 picks, and blocked strategies dominate it. Add `"ETF"` to the same set. One-line change.

2. **Tighten EQUITY `passes_active_gate` bypass** — The `_non_crypto_active_raw_score_bypass()` function (lines 1054–1061 of `quality_gates.py`) allows EQUITY picks with `score < 55` if `history_wr_bayes ≥ 88%`. This was designed for high-WR systems, but stale WR windows are passing degraded strategies. Add a recency gate: bypass only applies if the strategy also has `strat_fwd_wr ≥ 55%` (same as HF Threshold A's forward WR signal). This eliminates the 41 low-score active EQUITY picks aging through on stale history.

3. **COMMODITY soft freeze** — Do NOT add new COMMODITY strategies or lower COMMODITY score floor (currently 60) while the decay investigation in Phase 3 is in progress. Document the freeze in `docs/COMMODITY_FREEZE_2026-04-14.md` (this is the `STRATEGY_INVESTIGATION_BEFORE_KILL.md`-equivalent per CLAUDE.md rules).

**Relevant files:**
- `audit_trail/quality_gates.py` — `BLOCKED_ASSET_CLASSES` (line 729), `_non_crypto_active_raw_score_bypass()` (lines 1054–1061), `passes_active_gate()` (lines 3189–3410)

---

## Phase 2 — Exit Label Normalization (infrastructure correctness)

**Goal:** Make FOREX and COMMODITY WR/PF metrics trustworthy. Currently `LOST`/`WON` labels from legacy copy-trader scrapers corrupt the stats.

4. **Normalize exit labels at ingestion time** — In `audit_trail/dashboard_generator.py`, add a post-processing pass that maps `exit_reason == "WON"` → `"TP_HIT"` and `exit_reason == "LOST"` → `"SL_HIT"` for the copy-trader source systems (identified in `quality_gates.py` lines 1093–1126). Apply only when TP/SL prices are available to confirm; fall back to `TIME_EXIT` otherwise.

5. **Add `exit_label_quality` field** — Flag picks where the exit label comes from a binary legacy source (not TP_HIT/SL_HIT/TRAILING/TIME_EXIT/EXPIRED). Dashboard can show a small warning on these picks and exclude them from PF CI calculations.

**Relevant files:**
- `audit_trail/dashboard_generator.py` — post-processing step after pick resolution
- `audit_trail/quality_gates.py` — lines 1093–1126 (copy-trader scraper exit path)

---

## Phase 3 — COMMODITY Strategy Investigation (per CLAUDE.md protocol)

**Goal:** Identify which strategies are driving COMMODITY's decay (PF 1.35→0.60) before blocking anything.

6. **Build per-strategy COMMODITY scorecard** — Script that reads `audit_dashboard/data/dashboard_data.json → picks.recent_closed` filtered to COMMODITY, groups by `strategy`, and computes for each: N, WR%, PF, old-half PF, new-half PF, delta. Output to `docs/COMMODITY_STRATEGY_SCORECARD_2026-04-{date}.md`.

7. **Apply HF Threshold A decay gate to COMMODITY active** — The gate already exists (`audit_trail/hf_policy_thresholds.py → decay_hard_gate_triggers()`) and applies a -45 score penalty. But COMMODITY bypasses the Smart Picks tier (avg score already at floor 60), so picks with decay never hit the smart gate exclusion. Add an explicit check in `passes_active_gate()` for non-crypto picks: if `_hf_threshold_a == True` → reject from active gate too.

8. **Per the CLAUDE.md docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md rule:** Once the scorecard is built, open a targeted strategy demotion PR with the mutation analysis for each flagged COMMODITY strategy. Do not expand `BLOCKED_STRATEGIES` without this document.

**Relevant files:**
- `audit_trail/hf_policy_thresholds.py` — `decay_hard_gate_triggers()` (lines 1–64)
- `audit_trail/quality_gates.py` — `_apply_score_penalties()` (line 2353), `passes_active_gate()`
- `audit_dashboard/data/dashboard_data.json` — source data

---

## Phase 4 — Asset Class Decay Monitor (visibility infrastructure)

**Goal:** Make decay visible on the dashboard instead of discovered manually.

9. **Add decay status to dashboard payload** — In `audit_trail/dashboard_generator.py`, compute per-asset-class half-split PF during payload generation. Add a `asset_class_health` block to the JSON:
   ```json
   { "CRYPTO": { "status": "STABLE", "old_pf": 1.22, "new_pf": 1.30, "delta": +0.08 },
     "COMMODITY": { "status": "DECAYING", "old_pf": 1.35, "new_pf": 0.60, "delta": -0.76 } }
   ```

10. **Add health badge to dashboard Overview tab** — In `audit_dashboard/template.html`, render colored status pills (STABLE/DECAYING/DEAD) next to each asset class row in the existing asset class breakdown table. No new UI panels needed — add inline to existing table.

**Relevant files:**
- `audit_trail/dashboard_generator.py` — add `asset_class_health` computation
- `audit_dashboard/template.html` — Overview tab, asset class breakdown section

---

## Phase 5 — EQUITY HC Filter Extension (surface the real edge)

**Goal:** EQUITY Score≥50+Trust≥3 has PF 2.37 [1.48–3.96] — this is real edge that never shows in the HC filter. Currently `classify_hf_conviction_tier()` returns `None` for most EQUITY picks because `_classify_non_crypto_hf_tier()` (lines 708–738 of `conviction_stack.py`) only covers PEAD/quality strategies with strict confidence thresholds.

11. **Expand EQUITY tier assignment in `conviction_stack.py`** — Add a score+trust composite path: if `score ≥ 55` AND `trust_score ≥ 4` AND `direction == LONG` AND `strat_fwd_wr ≥ 50%` → assign Tier B. If `score ≥ 65` AND `trust_score ≥ 5` → assign Tier A. This lets the existing HC filter (`passesStampedTierSupplementalPath`) promote these picks.

12. **Re-run parity validator after change** — `tools/validate_dashboard_parity.py` confirms JS/Python mirror stays in sync after this change.

13. **Verify count delta before deploying** — Measure HC pick count on current payload before/after and ensure increase is ≤ 10 picks (to keep signal rare/meaningful).

**Relevant files:**
- `alpha_engine/conviction_stack.py` — `_classify_non_crypto_hf_tier()` (lines 708–738)
- `audit_dashboard/hc_filter.js` — `passesStampedTierSupplementalPath()`
- `tools/dashboard_hc_rules.py` — Python mirror
- `tools/validate_dashboard_parity.py` — parity check

---

## Phase 6 — CRYPTO SL:TP Ratio Fix (reduce stop-outs)

**Goal:** CRYPTO exits show 663 SL/SL_HIT vs 392 TP/TP_HIT (1.7:1 ratio). This compresses PF.

14. **Audit the ATR multiplier settings in `tp_sl_filler.py`** — Current caps are 15% TP / 10% SL for crypto. Review whether the default ATR multiplier for SL is tighter than for TP. If SL = 1x ATR and TP = 2x ATR, the ratio should favor TP; if not, the issue is cap truncation.

15. **Add trailing stop trigger earlier** — In `scanner.py` (lines 1526–1560), `TRAIL_ACTIVATE_PCT` controls when trailing begins. Lowering this activates trail-to-profit more frequently, reducing SL-from-flat situations.

16. **This phase requires `docs/MUTATION_THREE_AXIS_PROTOCOL.md` analysis before any changes** — TP/SL is a mutation to the pick generation pipeline.

**Relevant files:**
- `alpha_engine/tp_sl_filler.py` — ASSET_CAPS, ATR multipliers
- `alpha_engine/scanner.py` — `TRAIL_ACTIVATE_PCT`, exit reason assignment (lines 1526–1560)

---

## Relevant Files Summary

- `audit_trail/quality_gates.py` — `BLOCKED_ASSET_CLASSES` (L729), `_non_crypto_active_raw_score_bypass()` (L1054-1061), `passes_active_gate()` (L3189-3410), `passes_smart_gate()` (L3528-3604)
- `audit_trail/hf_policy_thresholds.py` — `decay_hard_gate_triggers()` (L1-64)
- `audit_trail/dashboard_generator.py` — payload generation, post-processing
- `alpha_engine/conviction_stack.py` — `_classify_non_crypto_hf_tier()` (L708-738)
- `alpha_engine/tp_sl_filler.py` — ASSET_CAPS
- `alpha_engine/scanner.py` — exit label assignment (L1526-1560)
- `audit_dashboard/template.html` — Overview tab table
- `audit_dashboard/hc_filter.js` — `passesStampedTierSupplementalPath()`
- `tools/dashboard_hc_rules.py` — Python mirror
- `tools/validate_dashboard_parity.py` — parity checker
- `tools/_perf_by_class.py` — manual perf check script (new)

## Verification
1. After Phase 1: active EQUITY picks count drops from 41; ETF picks = 0 new
2. After Phase 2: FOREX closed picks use TP_HIT/SL_HIT labels; validate_dashboard_parity still passes
3. After Phase 3: COMMODITY_STRATEGY_SCORECARD written, decaying strategies identified by name
4. After Phase 4: dashboard shows COMMODITY badge as DECAYING visually
5. After Phase 5: HC count increases by ≤10 picks; parity test passes
6. After Phase 6: closed CRYPTO SL:TP ratio moves below 1.5:1

## Decisions / Scope
- ETF hard block is safe (only 19 historical picks, all known strategy blocks already exist)
- FUTURES already in BLOCKED_ASSET_CLASSES — no action needed
- FOREX is NOT being blocked — PF 2.03 with improving trend; fixing exit labels is the right fix, not blocking
- COMMODITY is frozen, not blocked — giving time to investigate before demotions
- No synthetic data generated anywhere in this plan
