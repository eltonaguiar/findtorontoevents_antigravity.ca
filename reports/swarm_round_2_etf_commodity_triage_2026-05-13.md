# Swarm Round 2 — ETF Push-to-T2 + COMMODITY Sanity Check

**Date:** 2026-05-13 (after wave-2 ship)
**Agents:** 2× Explore (parallel)
**Verdict:** **DEFER both** — neither is safe to act on in this session without further work documented below.

---

## 1. ETF push toward Tier-2 (PF 1.41 → ≥1.50)

**Live state (2026-05-13T23:19Z):** ETF n=106, PF=1.41, WR=56.6%.

**Swarm finding:** the single drag is `goldmine_stocks` (1 pick, −5.77% PnL on XLE, elite_score=20 — well below the ETF floor of 50). Removing it alone lifts PF to ~1.50 (right at Tier-2 floor). Adding `super_signals` (3 picks, −0.06% aggregate) is marginal.

**Why DEFER:**
- `CLAUDE.md` explicitly states: **"NEVER auto-add to `BLOCKED_ASSET_STRATEGY_PAIRS` or `BLACKLISTED_STRATEGIES` without explicit user approval"**.
- `CLAUDE.md` also requires the mutation-before-kill protocol (`docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` + `docs/MUTATION_THREE_AXIS_PROTOCOL.md`) before any strategy demotion.
- n=1 for goldmine_stocks on ETF is below any reasonable demotion threshold. The pick should never have been admitted (elite_score=20 < floor=50) — the more durable fix is the admission-time gate, not a retro blacklist.

**Recommended path (next session):**
1. Investigate why `goldmine_stocks` produced an ETF pick with elite_score=20 at all (gate misfire?).
2. If admission-time gate is correctly tuned, leave the pick as a one-off; PF will mean-revert with the next ETF closes.
3. If the admission gate is mis-tuned, fix the gate (root cause) rather than the blacklist (symptom).
4. **Aspirational lift:** the ETF sector-rotation strategy in `reports/etf_sector_rotation_backtest_20260513T020800Z.md` shows PF 2.05 backtest. That is the path to Tier-1, but is a new-module wire-up (multi-PR scope).

---

## 2. COMMODITY 70.5% WR / PF 4.03 sanity check

**Live state (2026-05-13T23:19Z):** COMMODITY n=281 resolved (of 451 closed; 38% unresolved), PF=4.03, WR=70.5%.
**CLAUDE.md banner state (2026-05-03):** n=750, PF=1.78, WR=46.9%.

**Swarm finding:** the headline numbers are **statistically sound** (n=281 ≥ Tier-2 floor of 100) but reflect a **resolver baseline shift**, not a regime change. The 38% unresolved gap suggests prior COMMODITY picks landed FLAT inside the 5bp resolver threshold. The CLAUDE.md baseline included those FLATs; the live `asset_class_health` excludes them.

**Why DEFER:**
- Apples-to-oranges: comparing a resolved-only sample to a closed-including-FLAT sample inflates PF/WR.
- A recent-window cut (last 60-90 days) would be the apples-to-apples comparison, but that data is not surfaced in `asset_class_health` as of this run.
- Sizing up on PF 4.03 without verifying the recent-window equivalent is the kind of move that gets retroactively classified as overconfidence.

**Recommended path (next session):**
1. Extend `audit_trail/dashboard_generator.py::asset_class_health` to emit both `resolved_n` and `closed_n` plus a `recent_window_pf_60d` field. (Already a documented dashboard surface improvement.)
2. Identify which source systems contribute the 198 COMMODITY wins. If concentrated in one strategy, that strategy may be the real edge.
3. Until then, keep COMMODITY sizing at current allocation; do not graduate to Tier-1 based on the headline figure.

---

## 3. What this round changes about future work

The pattern from rounds 1 and 2: **swarm agents tend to recommend bolder action than the live numbers + CLAUDE.md guardrails support.** The right discipline is to use swarm output as a starting hypothesis, then verify against ground-truth dashboard data and the explicit constraints in CLAUDE.md.

This is consistent with the earlier-session pattern (8 confidently-wrong claims caught via reproducible-query rule). The cost of an unwarranted gate change is the kind of WR-collapse the drift circuit-breaker (#977) was just built to catch.

---

## 4. Concrete next-session deliverables (no swarm needed)

1. **Verify drift breaker stamps on next dashboard regen.** Read `audit_dashboard/data/dashboard_data.json::performance.asset_class_health.*.circuit_breaker` after the post-#977 generator run completes. If keys are present, the wire is live.
2. **Verify BOND merge.** Read `alpha_engine/data/active_picks.json` after the next bond-agent run (hourly). Check for `asset_class=bond` entries that weren't there pre-#981.
3. **Surface `n` per class on `asset_class_health`.** The current payload omits `n`/`total_trades` for every class, which forced this round to use `closed_n` proxies. One-line fix in `dashboard_generator.py`.
4. **Recent-window PF.** Add `pf_60d` to `asset_class_health` for COMMODITY-style baseline-shift detection.
