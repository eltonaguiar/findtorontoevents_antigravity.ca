# CORRIGENDUM — /audit Truth-Layer Validation Swarm — 2026-05-31 (EST late)

> Purpose: correct three claims in the w2n0g4jnv consolidation wave entry
> (`updates/index.html` Truth-Layer Validation card + `MASTER_TRUTH_REPORT_2026-05-31_FINAL.md`)
> that became stale or wrong between drafting and posting. The broader honest
> verdict ("no statistically-valid edge across asset classes today") stands.

Branch context: `blackboxai/gha-heatlh-fixes`. Source-of-truth commits referenced
below.

---

## Section 1 — `+313.43%` verdict: NUANCED, not "FABRICATED"

**Original claim (in flight)**: "+313.43% rolling-100 is FABRICATED — 4 agents grepped the
repo; 313.43 appears only in a STOCKS price field. Mathematically impossible vs
WR 25% / PF 0.61."

**Correction**: The specific number `313.43` does **not** appear in current live JSONs,
but the *closest* live value is `+300.53%` (rolling_100, decayed from a slightly
higher value seen earlier in the session — confirmed 13bp drift since the
21:09 UTC snapshot). What the operator screenshotted was almost certainly a
real-but-now-decayed reading, not a fabrication.

**What remains valid**: a positive rolling_100 of ~+300% is still
mathematically incompatible with the WR 25% / PF 0.61 headline. This is the
**same bug class** as the "Tier-2 Proven" `mega_mutation` +318% 90d_cum
artifact — verbatim `cum += v` (arithmetic sum, not compounded) at
`dashboard_generator.py:11543`. Real `total_pnl_pct_compounded_rolling_100`
is **−41.63% (NEGATIVE)** when computed correctly.

**Net**: don't call the number "fabricated". Call it
**"compounded-vs-arithmetic dashboard rendering artifact"**, same root cause
as the Tier-2 Proven mega_mutation row.

---

## Section 2 — Edge Stability daily refresh: LIVE (not pending)

**Original claim (in flight)**: "Edge-stability daily cron shipped as PR #285
(00:30 UTC). EST timestamp added." — written before merge + first run completed.

**Correction / status now**:
- PR #285 **MERGED** (`a0239170e ci(edge-stability): daily 00:30 UTC refresh workflow (#285)`).
- First scheduled run **#26724681663** — `conclusion: success`, `status: completed`,
  workflow name `Edge stability refresh`.
- `audit_dashboard/data/edge_stability/edge_stability_<CLASS>.json` `as_of`
  advanced from `2026-05-12T21:53Z` → `2026-05-31T21:15Z` across all 8 classes
  (CRYPTO `n=1022`).
- The "Last updated May 12" headline issue on `/audit/edge_stability.html` is
  **FIXED**. Status: **AUTOMATED + REFRESHED**, no longer a pending action item.

---

## Section 3 — Zoo work integrated (commit + ML calibration verdict)

**Original claim (in flight)**: "Filter-survival gap: 62 picks missing; main
cause RESOLVE_FAILED_MAX_RETRIES."

**Correction / expansion**:
- Zoo commit `5ad53a9d0 audit: analyze COMMODITY filter survival gap` landed
  on `blackboxai/gha-heatlh-fixes` with the full analysis: **62/72 = 16.67%
  survival**, and the smoking gun is **resolver-v2 cross-contamination** —
  SHIB $4100 exit price leaking into EURUSD exits — NOT
  `RESOLVE_FAILED_MAX_RETRIES`. Update Section 7 / filter-gap row accordingly.
- ML calibration verdict from `audit_dashboard/data/research/ml_calibration_audit.json`
  **REFUTES** the "global ML inversion" framing in earlier incidents:
  - **FOREX**: CRITICAL inversion (0.65 → 0.75 = 46.7pp drop).
  - **COMMODITY**: MODERATE.
  - **CRYPTO**: localized 0.8-bucket dip, not inversion (matches PR #227
    verdict + PR #263 0.8-bucket dampen).
  - **Other classes**: OK.
- This is consistent with the memory note `project-confidence-trust-edges-2026-05-31`
  — **"no global inversion" position holds**; only FOREX (and to a lesser
  degree COMMODITY) is a calibration emergency.

---

## Section 4 — Hyrotrader phantom A+ STILL unfixed (consistent across 3 agents)

No correction — re-emphasized for the operator queue.

- Producer: `hyro_pick_performance_validator.py:461`.
- Consumer: same file line 1714.
- Account snapshot date on `/audit/hyrotrader.html`: **2026-04-08** (53+ days
  stale at time of audit).
- Three independent agents in the validation swarm reached the same finding;
  no PR has landed against it this session.

Operator next action: ticket the phantom-A+ producer/consumer pair against
the next /audit/hyrotrader sweep; it is the highest-impact unaddressed
truthfulness defect on the hyrotrader subpage.

---

## Provenance

- Live `edge_stability_*.json` files in `audit_dashboard/data/edge_stability/`
  (post-cron run `#26724681663`).
- Commit `5ad53a9d0` (zoo filter-survival analysis).
- `audit_dashboard/data/research/ml_calibration_audit.json` (per-class
  calibration verdict).
- `reports/peer_claude-MASTER_TRUTH_REPORT_2026-05-31.md` (skeleton being
  finalized as `_FINAL.md`).
- `updates/index.html` Truth-Layer Validation entry (the one this corrigendum
  amends).

— Issued by peer-claude (blackboxai/gha-heatlh-fixes worktree) on 2026-05-31
EST late evening as a corrigendum to the in-flight w2n0g4jnv consolidation
wave.
