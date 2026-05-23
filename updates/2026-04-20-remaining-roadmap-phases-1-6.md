# Remaining /audit roadmap — Phases 1 through 6

**Date:** 2026-04-20
**Context:** Phase 0 (descriptive legend + hiding the unreproducible Guide band) shipped today as commit `52cdcb61e`. Six additional phases remain per [`docs/REMAINING_ENHANCEMENT_PROPOSALS_V3_2026_04_20.md`](../docs/REMAINING_ENHANCEMENT_PROPOSALS_V3_2026_04_20.md), reviewed by six independent AI reviewers.

This entry tracks scope, files touched, and user-facing benefits of each remaining phase so contributors (and the user landing on `/audit`) can see the plan.

---

## Phase 1 — At-issue feed-membership stamping

**Effort:** ~3 hours
**User-visible:** No (internal tooling; enables Phase 2 + future banner)

### Files changed
- `audit_trail/stamp_pick_quality.py` — add `stamp_feed_membership(pick, at_issue=False)` function; wire into existing `stamp_picks()` pipeline step (post-`trust_tier`, post-`strat_fwd_wr`)
- `audit_trail/feed_membership.py` — new module with `VERIFIED_ALPHA_SOURCES` constant and helper predicates
- `audit_trail/dashboard_generator.py` — `_CLOSED_PICK_KEEP_FIELDS` already includes the required fields (shipped in [`faba0b66a`](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/commit/faba0b66a)); no change here
- `tests/test_stamp_feed_membership.py` — new test suite

### What it does
Every ingested pick gets `is_smart_pick`, `is_verified_alpha`, `hc_tier` stamped against the gate state at ingest time. When a pick transitions ACTIVE → CLOSED, `at_issue_is_smart_pick` / `at_issue_is_verified_alpha` / `at_issue_hc_tier` are snapshotted once and frozen — so historical analysis reflects "what the user actually saw" at pick open, not what the gate logic says today.

### Benefits
- Retroactive cohort analysis: "what did the Smart Picks tab return last month?" becomes answerable
- Feed-membership drift detection: when gate logic changes, stamps on closed picks freeze the prior semantics (don't rewrite history)
- Unblocks Phase 2 (backfill) and Phase 4 (risk-adjusted metrics per feed)

---

## Phase 2 — Backfill script for historical 3,500-row closed window

**Effort:** ~1 day
**User-visible:** Partial (analytics accuracy improves; no UI change)

### Files changed
- `tools/backfill_feed_membership.py` — new one-shot script
- `audit_dashboard/data/dashboard_data.json` — `recent_closed` rows get `is_smart_pick` + `at_issue_*` populated (non-destructive fill; never overwrites existing non-null stamps)
- `docs/AUDIT_DATA_PIPELINE_GAP_CHECKS_2026_04_20.md` — update coverage ratio after backfill
- Possibly `alpha_engine/data/closed_picks.json` hot file, similarly

### What it does
Iterates the 3,500-row `recent_closed` window. For picks missing `at_issue_trust_tier` or `at_issue_strat_fwd_wr`, stamps `is_smart_pick = null` (explicit null, not false) so downstream analytics exclude them from denominators. For picks that DO have at-issue fields, computes `is_smart_pick` / `is_verified_alpha` / `hc_tier` retroactively using point-in-time blocklist state (git-log the blocklist file @ `T_open(pick)`).

### Benefits
- Closes the "retroactively unauditable" gap flagged by today's effectiveness audit
- Publishes explicit coverage ratio ("stamped: X / 3500") so analytics consumers know which rows are trustworthy
- Prevents the look-ahead leak of forward-filling from current gate state onto historical picks (DeepSeek reviewer caught this)

---

## Phase 3 — HC evaluator parity test

**Effort:** ~0.5 day
**User-visible:** No (validation gate for Phase 1)

### Files changed
- `tools/hc_parity_test.js` — new Node CLI wrapping `audit_dashboard/hc_filter.js`
- `tools/hc_parity_test.py` — runner that pipes last 3,500 closed picks through both JS and Python evaluators and diffs
- `.github/workflows/hc-parity.yml` — new workflow (weekly cron + manual dispatch)
- `tools/data/hc_parity_baseline.json` — committed golden-diff artifact

### What it does
Ports `audit_dashboard/hc_filter.js` to a Node CLI (pure function eval, no browser). Runs both evaluators against the full 3,500 closed picks. Fails if any pick classified differently. Continuous shadow-eval for 2 weeks post-Phase-1-launch.

### Benefits
- Catches rare classification divergence between JS and Python evaluators before Phase 1 production stamping can lock in errors
- Ollama-ops reviewer caught: 500-pick headless-browser test in CI = flake magnet; Node CLI + full 3,500 offline is cheap and reliable

---

## Phase 4 — Risk-adjusted metrics pipeline (GATES any future banner)

**Effort:** ~3-5 days
**User-visible:** **YES** — unlocks the honest banner deferred from v2

### Files changed
- `tools/risk_adjusted_metrics.py` — new module with `compute_feed_metrics(feed_name)` returning Sharpe, max DD + duration, net-of-cost PF, expectancy-R
- `tools/regime_decomposition.py` — new module: 3×3 grid (F&G bucket × BTC-trend regime) of PF + Sharpe + n per feed
- `tools/block_bootstrap_ci.py` — new utility for block-bootstrap CI on PF (by `strategy_id`, not by pick)
- `audit_trail/dashboard_generator.py` — call these at generation time, stash results under `summary.feed_risk_metrics`
- `audit_dashboard/data/feed_risk_metrics.json` — generated artifact
- `audit_dashboard/template.html` — re-enable a headline banner now that Sharpe + DD + net-of-cost + regime decomp are available
- `docs/FEED_RISK_METRICS_METHODOLOGY.md` — new methodology doc (fee assumptions, regime-bucket definitions, bootstrap-N)

### What it does
Computes per-feed (HC / Smart Picks / Verified Alpha / Active) the six metrics every reviewer demanded before publicizing a point estimate:

1. Sharpe ratio (annualized)
2. Max drawdown (% equity) + duration
3. Net-of-cost PF (with explicit fee + slippage assumption in the doc)
4. Expectancy in R-multiples
5. Regime decomposition (F&G × BTC-trend, with amber flag on n<10 cells)
6. 95% CI on PF via block-bootstrap on `strategy_id`

Only when all six are populated does a headline number appear in a dashboard banner. All numbers render with an `as_of` timestamp and refresh weekly.

### Benefits
- Users see honest risk-adjusted edge, not bare PF that invites bad position sizing (Mercury reviewer)
- Block-bootstrap on `strategy_id` closes the "trades-are-not-iid" gap (DeepSeek reviewer)
- Regime decomposition surfaces "HC looks great but only in bull regimes" if true (Mercury reviewer)
- Unlocks the v2 Phase 0 banner that got pulled for being risk-naked

---

## Phase 5 — Wilson LB gate revision + hysteresis

**Effort:** ~2 hours
**User-visible:** Partial (Guide band will activate/deactivate correctly)

### Files changed
- `audit_trail/dashboard_generator.py` — new helper `should_activate_guide_band(wins, n)` implementing:
  - Wilson LB ≥ **0.52** (raised from v2's 0.45 after DeepSeek power analysis)
  - `n ≥ 50` (raised from 20 for ~80% power at 15pp effect)
  - Hysteresis: activate at 0.52, deactivate at 0.47 (Ollama-ops caught band-flicker)
  - Bonferroni adjustment if the same gate drives multiple filters (α = 0.05/k)
- `audit_dashboard/template.html` — re-enable the hidden "Maximum Conviction Combo" card conditionally, using the helper's output
- `tests/test_guide_band_activation.py` — new tests covering threshold, hysteresis, Bonferroni

### What it does
Replaces the v2 proposed `wilson_lb ≥ 0.45, n ≥ 20` gate with a statistically-defensible version. The band activates only when the evidence genuinely exceeds random 50% baseline, and doesn't flicker on noise at the boundary.

### Benefits
- Guide band no longer advertises filters that can't pass a power test (DeepSeek reviewer computed: v2's gate only discriminated WR 0.78 vs 0.50, not 0.60 vs 0.50)
- Hysteresis prevents "band disappeared then came back then disappeared" user-confusion (Ollama-ops reviewer)
- Mathematically honest: Bonferroni respects multiple-comparison discipline

---

## Phase 6 — MFE/MAE schema + writer plumbing

**Effort:** ~2-3 days
**User-visible:** No (data collection infrastructure)

### Files changed
- `audit_trail/dashboard_generator.py` — add `max_favorable_excursion_pct`, `max_adverse_excursion_pct` to `_CLOSED_PICK_KEEP_FIELDS`
- `alpha_engine/outcome_resolver.py` — compute MFE/MAE from intra-trade price history at TP/SL resolution
- `audit_trail/tp_sl_audit.py` — populate MFE/MAE for historical rows where the underlying price series is still available
- `audit_dashboard/template.html` — display MFE/MAE columns in closed picks table (optional; probably hidden-by-default expandable column)

### What it does
Closes the "could the user have held through the DD?" gap. For every closed pick, compute:
- **MFE** (Max Favorable Excursion): best unrealized gain during the trade
- **MAE** (Max Adverse Excursion): worst unrealized drawdown during the trade

### Benefits
- Position-sizing recommendations become defensible — without MAE, "survivable DD" is unknown (Mercury reviewer)
- "Almost-hit-TP" patterns surface — picks that reached 90% of TP before reversing to SL deserve different TP calibration
- Regime-conditioning improves: "HC picks have MFE median 1.4× in bull regimes vs 0.8× in chop" is actionable

---

## Sequencing and timeline

| Phase | Effort | Unlocks | Ship order |
|---|---|---|---|
| 1 — Stamping | 3 h | Phases 2, 4 | 1 |
| 3 — Parity test | 0.5 d | Phase 1 safety | 2 (parallel to 1) |
| 2 — Backfill | 1 d | Phase 4 accuracy | 3 |
| 5 — Wilson gate | 2 h | Guide band re-enable | 4 |
| 4 — Risk-adjusted metrics | 3-5 d | **User-facing banner** | 5 |
| 6 — MFE/MAE | 2-3 d | Sizing recs + DD analysis | 6 |

**Total:** ~8-12 days of engineering once all phases ship.
**User-visible wins along the way:**
- Phase 5 → Guide band returns correctly
- Phase 4 → honest risk-adjusted headline banner (replaces the v2 banner that was pulled for being unsafe)
- Phase 6 → position-sizing recommendations become defensible

---

## Philosophy note

This roadmap reflects a shift in discipline after today's audits: **never publicize a number without its risk-adjusted companion**. Phase 4 is the gate. Phase 0 (shipped today) honored this by being descriptive-only.

Cross-references:
- [`docs/REMAINING_ENHANCEMENT_PROPOSALS_V3_2026_04_20.md`](../docs/REMAINING_ENHANCEMENT_PROPOSALS_V3_2026_04_20.md) — full proposal with reviewer attribution
- [`docs/AUDIT_EFFECTIVENESS_AUDIT_2026_04_20.md`](../docs/AUDIT_EFFECTIVENESS_AUDIT_2026_04_20.md) — effectiveness audit that surfaced the gaps
- [`docs/AUDIT_ADDITIONAL_FIXES_2026_04_20.md`](../docs/AUDIT_ADDITIONAL_FIXES_2026_04_20.md) — blocklist-leakage finding
- [`docs/STRATEGY_FACTORY_V1_1_AMENDMENTS.md`](../docs/STRATEGY_FACTORY_V1_1_AMENDMENTS.md) — S-ladder cited by Mercury reviewer
