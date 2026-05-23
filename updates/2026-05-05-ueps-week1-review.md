# UEPS v1.1 Week-1 Review — 2026-05-05

**Reviewer:** Claude Sonnet 4.6 (automated)
**Review window:** 2026-04-28 (v1.1 weight flip) → 2026-05-05 (today, 7 days)
**Sources:** `alpha_engine/value_screener.py`, `audit_dashboard/data/ueps_picks.json`,
`alpha_engine/data/active_picks.json`, `alpha_engine/data/closed_picks.json`,
`updates/long_term_value_project_2026-04-27/findings/SYNTHESIS.md`,
`docs/PERFORMANCE_CHARTER.md`, git log `main`

---

## 1. Summary

The v1.1 quality-tilt flip (VALUE_WEIGHT 0.55→0.45, QUALITY_WEIGHT 0.45→0.55) **is live in
code** and the screener pipeline fired its first weekly emit on 2026-05-05 (30 long-term picks,
0 swing, 0 short). However, with **n=0 closed long_term_value picks** and a 3y+ holding
horizon, there is nothing to measure yet. The weight flip cannot be validated this week — that
is expected, not alarming.

Critical context gaps: `FINAL_SYNTHESIS_2026_04_28.md` and research files `06_methodology_critique.md`
and `08_real_backtest.md` **do not exist on disk** — the backtest rationale for the v1.1 flip is
absent from the repo. The sourced commit `4c861fbbec` and branch
`feat/ueps-production-wiring-2026-04-28` are not present in local history. The resolver-fix
branch (`fix/outcome-resolver-bar-replay-2026-04-28`) is also gone, but the fix itself
(`PNL_WIN_THRESHOLD_BY_CLASS`) is confirmed merged at `outcome_resolver.py:115-126`.

Two quality gaps in the live emit need attention before n grows: Beneish M is null for all 30
picks (placeholder −2.5 used, nominally passing SafetyGate); and earnings / dividend data is
empty (fetchers exist but are not called in the runner).

---

## 2. v1.1 Emit Metrics (n=0 closed — data too thin)

| Metric | Target (v1.1 backtest projection) | Actual (Week 1) |
|--------|----------------------------------|-----------------|
| n closed | — | **0** (all picks status=ACTIVE, horizon=3y+) |
| WR | 68.5% (28-stock research/08 window) | n/a |
| PF | 3.11 | n/a |
| MaxDD | — | n/a |
| Active emits | — | 30 long / 0 swing / 0 short |

**First emit snapshot (2026-05-05T13:02 UTC):** 30 long-term value picks from a 51-symbol
universe (50 passed gates). Top picks by composite score: ADBE (0.748), META (0.700), QCOM
(0.688). Scores are dominated by value composite (v1.1 de-weights value to 0.45 vs prior 0.55),
confirming the flip is arithmetically active.

**Mirror-pair alert:** GOOG (rank 12) and GOOGL (rank 13) both appear in the 30-pick portfolio.
These are the same underlying company — double exposure without a dedup gate. This is a data
quality issue, not a weight issue.

**Beneish M:** null for all 30 picks. `compute_safety_gate()` substitutes placeholder −2.5
(hardcoded in `value_screener.py:35`) which passes the ≤−1.78 threshold. SafetyGate is
nominally green but without real fraud-detection signal.

> **Verdict on data:** n<10 closed at this stage. Cannot validate the v1.1 flip vs v1.0.
> Recommend extending one more week (at minimum one full 90-day holding cycle) before any
> v1.2 decision.

---

## 3. P0/P1 Completion Audit

`FINAL_SYNTHESIS_2026_04_28.md` (the canonical P0/P1 list) **does not exist on disk**. Audit
is reconstructed from `PROJECT.md` phase table, `SYNTHESIS.md`, and code presence.

| # | Item | Source | Status | Evidence |
|---|------|---------|--------|----------|
| P0-1 | v1.1 weight flip (0.45V/0.55Q) | `value_screener.py:44-45` | **DONE** | `VALUE_WEIGHT=0.45` confirmed |
| P0-2 | `long_term_pick_contract.py` schema | Phase 2 | **DONE** | File on disk, 9 KB |
| P0-3 | `fundamentals_fetcher.py` | Phase 3 | **DONE** | Imported by screener |
| P0-4 | `value_screener_runner.py` + weekly cron | Phase 14 | **DONE** | Emit fired 2026-05-05 |
| P0-5 | `PERFORMANCE_CHARTER.md` charter | Phase 12 | **DONE** | 136 lines, canonical |
| P1-1 | `thesis_resolver.py` | Phase 8 | **DONE** | File on disk, 12 KB |
| P1-2 | `swing_screener.py` + `swing_resolver.py` | Phases 7+9 | **DONE** | Files on disk; n_swing=0 in emits |
| P1-3 | `outcome_resolver.py` bar-replay fix | `fix/…-2026-04-28` branch | **DONE** | `PNL_WIN_THRESHOLD_BY_CLASS` at :115 |
| P1-4 | `earnings_calendar_fetcher.py` wired | Phase 4 | **PARTIAL** | File exists; `earnings_history=[]` on all 30 live picks |
| P1-5 | `dividend_history_fetcher.py` wired | Phase 5 | **PARTIAL** | File exists; `dividend_record={}` on all 30 live picks |

**Score: 8/10 DONE, 2/10 PARTIAL.** The two PARTIAL items (earnings + dividend enrichment)
are not plumbing failures — the fetcher modules exist — but the runner does not pass
`earnings_calendar_fetcher` or `dividend_history_fetcher` results into `ScreenerInput`. The
dashboard pick cards therefore show empty earnings and dividend sections, reducing transparency.

**Missing artifacts (red flag):** `FINAL_SYNTHESIS_2026_04_28.md`, `research/06`, `research/08`
were referenced in this review prompt but do not exist. The v1.1 weight flip rationale lives
only in code comments (`value_screener.py:44-45`) and is not backed by recoverable research
files. If this session is revisited, the 28-stock backtest grid should be re-run and committed.

---

## 4. Resolver Fix Branch Status

Branch `fix/outcome-resolver-bar-replay-2026-04-28`: **not present as a live branch**.
Fix is confirmed merged to main: `outcome_resolver.py:115-126` contains
`PNL_WIN_THRESHOLD_BY_CLASS = {… "CRYPTO": 0.001, … default 5bp for non-crypto …}`.
The v2/v2.1 resolver fix described in `CLAUDE.md` MAJOR GOALS §1 is complete.
No action needed here.

---

## 5. P2 Readiness Ranking (top 3 next session)

| Rank | P2 Item | Prerequisite met? | Effort | Risk | Recommendation |
|------|---------|-------------------|--------|------|----------------|
| **1** | Wire earnings + dividend fetchers into runner | Yes — fetchers on disk, runner callable | Low (1-2h) | Low | **Do first.** Enriches pick cards immediately; no scoring change. |
| **2** | GOOG/GOOGL mirror dedup in universe gate | Yes — `_apply_universe_gates()` is the right entry point | Low (1h) | Low | Add dedup before scoring; reduces artificial concentration. |
| **3** | Soft-gate SafetyGate (pass-through with penalty flag vs hard zero) | Yes once earnings/div are wired (data completeness prerequisite) | Medium (3-4h + backtest) | Medium — changes scoring | Needs Phase-13 `value_backtest.py` re-run to validate soft gate impact first. |

Items 4-6 from the task spec (ETF reclassify, PROVEN sync, thin-sample warning) are lower
priority until n≥30 closed picks. Thin-sample warning already baked into the dashboard tab
(`Building track record · n=0/100`).

---

## 6. Surprises and Red Flags

1. **Missing research files.** `research/06_methodology_critique.md` and
   `research/08_real_backtest.md` — the academic backing and backtest that justified the weight
   flip — are not on disk. The weight change is committed without its supporting evidence. Next
   agent should re-run the 28-stock backtest grid via `value_backtest.py` and commit the output.

2. **Commit 4c861fbbec not in local history.** The branch `feat/ueps-production-wiring-2026-04-28`
   doesn't exist. History may have been rewritten or the branch was squashed without preserving
   the SHA. Not a functional issue (code is correct) but breaks traceability.

3. **Beneish M null on all live picks.** `compute_beneish_m_score()` requires `prior_fundamentals`
   (a second EDGAR fetch for the prior fiscal year). The runner is passing only current
   fundamentals. Until prior_fundamentals is wired, the SafetyGate is running on a synthetic
   −2.5 placeholder — it will pass every company that clears Altman Z ≥ 1.10, defeating the
   purpose of the fraud screen. Medium-priority fix.

4. **n_swing=0 across all emits.** The swing screener module exists but the runner does not
   invoke it. The UEPS dashboard "Swing Plays" sub-tab will remain empty until swing emission
   is enabled.

5. **TSLA in top 30 (rank 28).** TSLA scores low (0.279) and has an Acquirer's Multiple of
   343x — the scoring formula is correctly down-weighting it, but it still passes universe
   gates. Worth monitoring whether it should be excluded via a universe gate cap on
   Acquirer's Multiple (e.g., exclude AM > 100).

---

## 7. Recommended Next-Session Prompt

```
UEPS Week-2 session — pick up from `updates/2026-05-05-ueps-week1-review.md`.

Priority order:
1. Wire earnings_calendar_fetcher + dividend_history_fetcher into value_screener_runner.py
   so live picks populate earnings_history and dividend_record fields. Test by running
   `python alpha_engine/value_screener_runner.py --dry-run` and verifying non-empty fields.

2. Add GOOG/GOOGL mirror dedup in value_screener._apply_universe_gates() or in the
   ScreenerInput builder: if company_short_name matches a previously scored symbol, skip
   the duplicate share class.

3. Wire prior_fundamentals into the screener run so Beneish M is computed from real XBRL
   data instead of the -2.5 placeholder. The EDGAR fundamentals_fetcher already supports
   fetching prior year data (pass fiscal_year_offset=-1).

4. Re-run the 28-stock walk-forward grid (value_backtest.py --universe mega28) and commit
   the output as research/08_real_backtest_v1.1.md to restore the weight-flip rationale.

5. Do NOT change weights yet — n=0 closed picks means any v1.2 decision is premature.
   Revisit at Week 4 (earliest plausible close date for any thesis-break event).

Gate: do not declare UEPS 'proven' until n≥30 closed picks with real (non-placeholder)
Beneish M scores.
```

---

## Verdict

**CONTINUE v1.1.**

The weight flip (0.45V/0.55Q) is live and the weekly screener fired its first emit
successfully (30 long picks, 2026-05-05). With n=0 closed picks at 7 days into a
3y+ holding horizon, any comparison to the v1.0 projection (WR 66.9% / PF 2.87) is
statistically meaningless. The plumbing works; the quality gaps (Beneish M placeholder,
empty earnings/dividend enrichment, GOOG+GOOGL mirror pair) are P1.5 fixes that should
land before Week 4, but they do not justify a weight roll-back. **Extend v1.1 for at
minimum 4 more weeks; reassess at the first measurable thesis-break close event.**
