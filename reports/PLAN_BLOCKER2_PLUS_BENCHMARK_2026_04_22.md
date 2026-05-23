# Plan: Blocker 2 (placeholder HC-gate picks) + Benchmark Synthesis

**Date:** 2026-04-22
**Author:** Claude Code (opus-4-7)
**Related:**
- [`reports/INTEGRATIONS_BENCHMARK_2026_04_22.md`](INTEGRATIONS_BENCHMARK_2026_04_22.md) — EBM / pyod / purged-CV benchmark on 5,135 closed picks
- `testreq.txt` (Blocker 2 analysis — clone_hl_copy placeholder stats bypassing HC gate)
- Memory: `feedback_clone_hl_placeholder_stats.md`, `feedback_gate_at_execution_not_generation.md`, `feedback_confidence_is_not_edge.md`, `reports/HC_GATE_COMPRESSION_DIAGNOSIS_2026_04_22.md`

---

## 1. Feedback on Blocker 2

**The analysis is correct. Option (d) is the only defensible action.**

Supporting evidence on top of what the original analysis cited:

### The "100/100/100" + "85/85/85.7" + "80/80/80" pattern is mathematically impossible

Across unrelated symbols (BTC, BNB, AVAX, LINK, NEAR, SUI, RENDER, HYPE, ONDO) every `clone_hl_copy_PensionFund_24M` row reports identical `score=100, n=100, fwd_wr=100.0%`. Real forward-WR measurements on distinct markets over any non-trivial window have dispersion. Three fixed triples across a dozen symbols means the pipeline is writing a fixed seed value, not a computed statistic.

### Corroboration from the live benchmark

On 5,135 real closed picks (from `alpha_engine/data/closed_picks.json`) I just ran — the `clone_hl_copy_*` sources do not appear in the top-volume source table at all. That's consistent with them being fresh/unresolved placeholder rows that have never seen a real outcome. The 97% that did close are `quan_engine` and `rapid_fire`; neither is `clone_hl_copy_*`.

### Confidence is inverse-correlated with wins (r = -0.087)

The same pipeline hygiene problem rhymes: the system publishes confidence numbers whose realized correlation with outcomes is **negative**. Treating "reported edge" as "real edge" is the bug class. Option (c) — accepting clone picks on override — repeats it.

### Gate At Execution Not Generation (memory feedback)

The `feedback_gate_at_execution_not_generation.md` memory explicitly warns: "Filter-named paper accounts (HIGHFWWRABV55_SCOREABOVE50_V4) bypass their filter because gate only runs at pick-generation; re-run at exec step." The Blocker 2 data shows exactly this failure mode — the clone_hl_copy rows *formally satisfy* the HC gate label numerically, but the numeric fields are placeholder constants, not computed from a closed-trade ledger. Gating at generation doesn't catch this; gating at execution with a **non-placeholder check** would.

### Why not (a), (b), or (c)

| Option | Why rejected |
|---|---|
| (a) Place the single real HC-gate pass | Acceptable tactically, but doesn't fix the pipeline; the placeholder rows will re-appear next cycle and eventually overwhelm the gate again. |
| (b) Drop the `fwd_wr≥55` label + route non-clone shorts | Changes account label semantics (HIGHFWWRABV55) while underlying data stays broken. Label-misrepresentation is its own compliance/audit risk. |
| (c) Accept clone picks on override | Directly violates `feedback_confidence_is_not_edge.md` and `feedback_clone_hl_placeholder_stats.md`. Creates a precedent that override > gate. |
| (d) **Fix placeholder pipeline first** | Addresses root cause. Zero trading risk from fake stats. Matches the "Mutate Before Kill" / "Investigate Before Act" pattern already codified in memory. |

---

## 2. Benchmark findings relevant to the plan

From [`reports/INTEGRATIONS_BENCHMARK_2026_04_22.md`](INTEGRATIONS_BENCHMARK_2026_04_22.md):

| Metric | Value | Implication |
|---|---|---|
| n closed picks | 5,135 | Larger than the 3,500 cited in memory — system is still running |
| Baseline WR | 29.72% | **Worse than the 31.1% memory figure** — drift is active, not plateaued |
| Baseline PF | 0.39 | Realized edge is deeply negative |
| `confidence` ↔ WIN | r = **-0.087** | "Confidence ≠ Edge" confirmed live; reported confidence is actively misleading |
| `elite_score` ↔ WIN | r = +0.149 | Weak positive — elite score does something, but not much |
| EBM out-of-sample acc (5 purged folds) | 0.6735 | **BELOW the 0.7028 always-predict-loss baseline.** Current feature set can't separate wins from losses at scale. |
| pyod ECOD anomalies | 249 picks, WR 33.3% | **Anomalies WIN more than normals (29.4%).** The flash-crash-filter hypothesis is inverted for this distribution. Don't deploy pyod as a blanket regime filter here. |
| Source concentration | 4,998 / 5,135 = 97.3% `quan_engine` | Single-source dependency. One upstream bug, one catastrophic drawdown vector. |

---

## 3. Recommended action order

Strictly sequenced — do not parallelize items 1–3. Each depends on the one before it being honest.

### Priority 1 (this week) — Fix the placeholder pipeline at source

Required before any HC-gated trading resumes.

1.1 Trace where `clone_hl_copy_*` rows get their `score` / `n` / `fwd_wr` fields populated. Likely candidate: `audit_dashboard/hc_filter.js` consumes fields that upstream ingestion never recomputes per symbol. Search order: `alpha_engine/forward_validator.py`, `audit_trail/dashboard_generator.py`, `alpha_engine/clone_*.py`.
1.2 Add an **assertion at ingestion**: if `score == n` and `abs(n - fwd_wr) < 1` across ≥3 unrelated symbols within one source, reject the batch and raise `PlaceholderStatsError`. Evidence threshold is intentionally conservative to avoid false positives on a source that genuinely only has 3 recent picks.
1.3 Add the same check as a **runtime gate at execution** (per `feedback_gate_at_execution_not_generation.md`). A pick that passes the ingestion hash but fails the exec-time check gets quarantined; trading proceeds on remaining passes.
1.4 Require `trust_tier != ""` and `trust_score is not null` for any HC-gated execution. Today's 50/50 failing rows have both blank.

### Priority 2 (this week) — Diversify the source stack

97% of closed volume is `quan_engine`. One ingestion bug here kills the whole book.

2.1 Audit `luxalgo`, `dna_winner`, `mercury`, `kimi_inverse_scanner` for pipeline health (feature memory `LONG Source Bias` recommends routing their SHORTs specifically).
2.2 Target: no single `source_system` accounts for more than 60% of live entries. Add a portfolio-level constraint at execution.
2.3 Use `pyod` in an **inverted** role — flag bars where the feature vector is *typical* and enter; skip when features are regime-shifted. This inverts the current expected use but matches the data: flagged picks had higher WR in the benchmark.

### Priority 3 (two weeks) — Rebuild the confidence signal

Current confidence is inverse-correlated with wins. Either:

3.1 **Invert** the sign (cheap, immediate; but probably means the feature is broken, not just inverted — inversion is a smell test not a fix).
3.2 **Replace** with a triple-barrier-labeled ML confidence trained with López de Prado purged K-Fold. The benchmark already runs the purged CV loop inline; graduate it to a production feature.

### Priority 4 (deferred) — Restore the integration wrapper layer

The 11 `alpha_engine/*_integration.py` modules, `alpha_engine/integrations/` facade, `tools/demo_next_phase_integrations.py`, and `NEXT_PHASE_INTEGRATION_STATUS.md` were wiped by an untracked-files + branch-switch race mid-session. The underlying libraries (`tsfresh`, `interpret`, `skforecast`, `flaml`, `pyod`, `bt`, `skfolio`, `feature-engine`, `imbalanced-learn`) remain installed and directly callable, as the benchmark script proves. Re-authoring is straightforward but lower leverage than fixing the placeholder pipeline. Defer until Priorities 1–3 are green.

---

## 4. What I'm committing with this plan

- [`reports/INTEGRATIONS_BENCHMARK_2026_04_22.md`](INTEGRATIONS_BENCHMARK_2026_04_22.md) — the real findings on 5,135 closed picks
- [`reports/PLAN_BLOCKER2_PLUS_BENCHMARK_2026_04_22.md`](PLAN_BLOCKER2_PLUS_BENCHMARK_2026_04_22.md) — this document

No existing file is modified. No trading code is touched. No picks are placed.

## 5. What I explicitly did not do

- Did **not** place the single real HC-gate pick from option (a). That decision requires user confirmation because the broader account is contaminated.
- Did **not** accept the `clone_hl_copy_*` picks under override (option c).
- Did **not** relabel the `HIGHFWWRABV55_SCOREABOVE50_V4` account (option b).
- Did **not** recreate the integration wrapper modules in this pass — defer to Priority 4.
