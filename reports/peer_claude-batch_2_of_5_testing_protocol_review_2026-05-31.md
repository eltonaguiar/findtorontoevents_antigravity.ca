# Batch 2/5 — Testing-Protocol File Review (2026-05-31)

**Author:** peer_claude (Opus 4.7)
**Scope:** 18 files from Batch 02 of the dupe-scan unique-file list.
**Canonical reference:** `docs/PAPER_PILOT_HARNESS.md` (cursor statistical framework — Wilson z=1.96, Bonferroni 0.05/7, **n_closed ≥ 500**, PF CI lo > 1.0).

---

## Per-file classification

### 1. `.github/workflows/money-ready-snapshot.yml`
- **Defines:** GHA cron (06:15 UTC daily) that runs `tools/money_ready_snapshot.py` → writes `audit_dashboard/data/money_ready_verdict.json` + dated archive. Sets `MDD_GATE_ENFORCE=1` and `ML_ENHANCED_CRYPTO_QUARANTINE=1`.
- **Last modified:** 2026-05-29 14:55
- **Redundant with:** None — it's the operator for the archive series cataloged in Batch 01.
- **Conflict with PAPER_PILOT_HARNESS.md:** None (different surface — money-ready verdict vs paper-pilot strategy harness).

### 2. `KIMI_CLAW_RESEARCH_FEB162026/AGENTS.md`
- **Defines:** Per-folder agent-onboarding playbook (BOOTSTRAP/SOUL/USER/MEMORY) for the Kimi vendored research workspace. Not testing protocol; folder-local agent rules.
- **Last modified:** 2026-05-25 20:29
- **Redundant with:** Root `./AGENTS.md` (sibling content but different scope; dupe-scan §filename-collisions notes "keep both").
- **Conflict with PAPER_PILOT_HARNESS.md:** None (out of scope).

### 3. `KIMI_RISEOFTHECLAW/METHODOLOGY_AUDIT_TRAIL.md`
- **Defines:** Antigravity Alpha system Feb-17-2026 audit trail — 117 strategies tested, 24 winners, per-strategy validation framework. Includes a 4-check rubric where **Check #4 = Sharpe ≥ 1.0** as the risk-adjusted threshold.
- **Last modified:** 2026-05-25 20:29
- **Redundant with:** No exact dupe; overlaps in spirit with `reports/PHENOMENAL_PERFORMANCE_METHODOLOGY.md` (Batch 03).
- **CONFLICT with PAPER_PILOT_HARNESS.md:** Mild — does not specify n-floor; uses Sharpe≥1.0 as primary check instead of Wilson-LB / Bonferroni-p / PF-CI multi-gate. **Older, pre-cursor-framework.**

### 4. `reports/2026-05-25_money_maker_readyv2_vs_actual.md`
- **Defines:** Per-class success bars for the `/money-maker-readyv2` skill:
  - EQUITY: n≥30/bucket, PF≥1.5, WR≥55
  - CRYPTO: **resolved_n≥100**, WR≥50, PF≥1.5
  - COMMODITY: n≥50, PF≥1.5
  - ETF: n≥150 toward OOS_READY, PF≥1.3
  - BOND: n≥20
- **Last modified:** 2026-05-25 20:29
- **Redundant with:** Skill-spec partial mirror of `.claude/skills/money-maker-readyv2/SKILL.md`.
- **CONFLICT with PAPER_PILOT_HARNESS.md (HIGH):**
  - **n-floor mismatch:** harness mandates **n_closed ≥ 500** for graduation; this doc accepts **n≥100 (CRYPTO)**, n≥50 (COMMODITY), n≥30/bucket (EQUITY), n≥20 (BOND).
  - **Significance:** doc uses PF≥1.5 / WR≥50 point estimates; harness uses Wilson-LB > break-even AND PF CI lo > 1.0 AND Bonferroni p<0.00714.
  - **Resolution:** money-maker-readyv2 is the *paper-tier filter*; PAPER_PILOT_HARNESS is the *graduation-to-live* gate. Both are valid IF the doc explicitly says "paper screening, not graduation". It currently does not call that out.

### 5. `reports/90day_pages_2026-05-15/hyrotrader_methodology_enhancements_2026-05-15.html`
- **Defines:** HTML render of HyroTrader-bridge 90-day roadmap (P0/P1/P2). Archive page.
- **Last modified:** 2026-05-25 20:29
- **Redundant with:** Byte-divergent HTML twin of `reports/hyrotrader_methodology_enhancements_2026-05-15.md` (#12 below) — same content, different format.
- **Conflict with PAPER_PILOT_HARNESS.md:** None (different surface).

### 6. `reports/ai_tournament_methodology_swarm_review_20260519.md`
- **Defines:** 3-engine consensus (Ring/Cerebras/GPT-4o-mini) on AI-tournament methodology. Fix adopted: **minimum n=30 per model per class**, Wilson/Agresti-Coull CIs, bootstrap PF CI, exact binomial, Bonferroni for multi-model multi-class testing.
- **Last modified:** 2026-05-25 20:29
- **Redundant with:** Companion to `tools/swarm/prompts/ai_tournament_methodology_review_20260519.md` (Batch 04).
- **CONFLICT with PAPER_PILOT_HARNESS.md (MEDIUM):** **n=30** vs **n=500**. Different surface (per-model-per-class tournament ranking vs strategy graduation) — n=30 here is for *ranking comparability*, not *graduation*. Should be tagged "ranking-only" to avoid threshold-shopping.

### 7. `reports/CLAUDE_METHODOLOGY_PROOF_2026_05_02.md`
- **Defines:** Live-data-first methodology pipeline; per-class PNL_WIN_THRESHOLD chain (0.001 non-FOREX / 0.0001 FOREX) for FLAT/WIN classification. Self-audit of FLAT_PNL_THRESHOLD scale mismatch (Py vs JS).
- **Last modified:** 2026-05-25 20:29
- **Redundant with:** Builds on resolver-fix doc trail (`outcome_resolver.py:115-126` block referenced in CLAUDE.md).
- **Conflict with PAPER_PILOT_HARNESS.md:** None (threshold is for outcome resolution, not graduation gate).

### 8. `reports/CONFIDENCE_METHODOLOGY_2026-05-24.md`
- **Defines:** 3-method confidence assignment (persona WR / model-reported / imputed). **n≥20 persona floor** for Method 1. HIGH/MEDIUM/LOW/NONE bands with position-size mappings (1.5% / 1.0-1.3% / 0.5-0.75% / paper-only).
- **Last modified:** 2026-05-25 20:29
- **Redundant with:** None unique.
- **CONFLICT with PAPER_PILOT_HARNESS.md (MEDIUM):** **n≥20** persona floor — well below harness n=500. Different surface (per-pick confidence vs strategy graduation), but the doc internally acknowledges the conflict ("80% confidence on n=23 is mathematically unsupportable", "Risk Manager flagged this as the 80% confidence epidemic"). Effectively self-deprecating.

### 9. `reports/DEEP_DIVE_MONEYREADY_2026-05-18.md`
- **Defines:** Per-class admissibility deep-dive on `pf_registry.json` gated by `tools/edge_stability_harness.py::is_admissible()`. Verdict: 0 admissible. Specifically REJECTS Hermes "RR≥1.5 + conf≥0.65 → 48.9% WR" filter as poisoned (146 CRYPTO rows had confidence 15-78 in a 0-1 domain).
- **Last modified:** 2026-05-25 20:29
- **Redundant with:** None.
- **Conflict with PAPER_PILOT_HARNESS.md:** Compatible — both anchor to `is_admissible()` / multi-gate logic.

### 10. `reports/equity_money_ready_path_20260517.md`
- **Defines:** EQUITY path-to-MONEY_READY. Cites internal threshold floors: **n≥50**, WR≥52% (MIN_WR_BY_CLASS), PF≥1.5, DSR≥0.95, SPA p≤0.10, **DSR/SPA require ≥2 strategies with n≥20 each**.
- **Last modified:** 2026-05-25 20:29
- **Redundant with:** None.
- **CONFLICT with PAPER_PILOT_HARNESS.md (HIGH):** **n≥50 (class-level) / n≥20 (per-strategy DSR/SPA input)** vs harness n≥500. Same surface conflict as file #4 — money-ready verdict vs paper-pilot graduation.

### 11. `reports/HARVEST_CONSTRUCTIVE_MONEY_READY_2026-05-19.md`
- **Defines:** Harvest of multi-AI suggestions for money-ready per class. Per-class verdicts + hypothesis seeds (H-029..H-035) for pre-registration under M-107.
- **Last modified:** 2026-05-25 20:29
- **Redundant with:** None unique; complements other money_maker_ready_* files.
- **Conflict with PAPER_PILOT_HARNESS.md:** None (hypothesis backlog, not a gate).

### 12. `reports/hyrotrader_methodology_enhancements_2026-05-15.md`
- **Defines:** Same content as #5 (HTML twin) — HyroTrader 90-day P0/P1/P2 roadmap, with HyroTrader graduation gate as faster-path to higher sizing.
- **Last modified:** 2026-05-25 20:29
- **Redundant with:** #5 (HTML render of same content).
- **Conflict with PAPER_PILOT_HARNESS.md:** None — proposed HyroTrader graduation gate is complementary external forward-test, not replacement.

### 13. `reports/kimi_uplift_2026_05_02/METHODOLOGY.md`
- **Defines:** 999-line full-fat methodology proposal for the audit uplift — explicit tier table:
  - **T1:** PF>2.0, WR>55, MDD<10
  - **T2:** PF>1.5, WR>50, MDD<20
  - **T3:** PF>1.2, WR>48, MDD<30
  - FAIL: below all
  Includes BH-FDR / decay tracker / persona infra / per-class threshold map (5bp non-crypto, 0.1bp crypto — matches `outcome_resolver.py`).
- **Last modified:** 2026-05-25 20:29
- **Redundant with:** Tier table is the source of truth cited verbatim in CLAUDE.md. Likely co-canonical with `docs/PERFORMANCE_CHARTER.md`.
- **CONFLICT with PAPER_PILOT_HARNESS.md (MEDIUM):** Tier table uses **point estimates** (PF>2.0, etc.) at samples as low as **n=20** for T1/T2 classifications. Harness requires CI-lower-bound + n≥500. Same pattern as money-ready-v2 — *screening tier* vs *graduation gate*. Doc does not flag this distinction.

### 14-18. `reports/money_maker_ready_20260512T194402Z*.md` (5 dated snapshots)
- **Defines:** Dated `/money-maker-readyv2` skill outputs (raw + CORRIGENDUM + 3 mid-week regenerations 14T0017, 14T2049, 14T2312). Each: freshness preflight + per-class baseline (CRYPTO/EQUITY/COMMODITY/ETF/FOREX/BOND/FUTURES) + verdict tier mapping per `docs/PERFORMANCE_CHARTER.md`.
- **Last modified:** All 2026-05-25 20:29 (touched in batch, content is from mid-May)
- **Redundant with:** Each other (5 same-skill, same-week, same-class-table snapshots). **HIGH content overlap.** The 0512 CORRIGENDUM specifically retracts the n=0 bug claim of the 0512 raw report.
- **Conflict with PAPER_PILOT_HARNESS.md:** None directly (skill outputs, not protocol docs). But they inherit the file-#13 tier table at point estimates — so per-class verdicts in these reports (e.g. "EQUITY Tier-2 at n=418/447") would FAIL the n≥500 harness gate.
- **Action:** Archive to `reports/archive/money_maker_ready/` per dupe-scan §Recommendations.

---

## Conflict summary (cross-file)

| # | File | Threshold stated | vs harness (n≥500) | Severity |
|---|---|---|---|---|
| 3 | KIMI_RISEOFTHECLAW METHODOLOGY_AUDIT_TRAIL | Sharpe≥1.0 only | no n-floor declared | MEDIUM (old) |
| 4 | 2026-05-25 v2-vs-actual | CRYPTO n≥100, COMMODITY n≥50, BOND n≥20 | far below | HIGH |
| 6 | ai_tournament swarm review | n≥30/model/class | far below (different surface) | MEDIUM |
| 8 | CONFIDENCE_METHODOLOGY | persona n≥20 | far below | MEDIUM |
| 10 | equity_money_ready_path | class n≥50, strat n≥20 | far below | HIGH |
| 13 | kimi_uplift METHODOLOGY | tier table point-estimate at n≥20 | far below | MEDIUM |
| 14-18 | money_maker_ready_*Z snapshots | inherits #13 tier table | far below | MEDIUM |

**Root cause:** the repo has two genuinely different surfaces — *paper-screening tiers* (Charter / money-ready-v2 / kimi-uplift) and *live-money graduation* (cursor framework / PAPER_PILOT_HARNESS). The conflicts are real only when a doc silently treats a screening threshold as a graduation threshold. PAPER_PILOT_HARNESS is the *only* doc that names the n=500 floor; every other file silently sets a much lower bar.

## Canonical recommendations

1. **PAPER_PILOT_HARNESS.md remains canonical for graduation.** It explicitly carries the n≥500 / Wilson-LB / Bonferroni / PF-CI multi-gate.
2. **Add a one-line disambiguation header** to each of files #4, #10, #13, and the 5 dated snapshots: *"Thresholds below are screening tiers, NOT live-money graduation. See `docs/PAPER_PILOT_HARNESS.md` for the n≥500 graduation gate."*
3. **Mark file #3 (KIMI_RISEOFTHECLAW METHODOLOGY_AUDIT_TRAIL)** as `pre-cursor-framework (Feb 2026)` — its Sharpe≥1.0 single-check is obsolete.
4. **Archive files #14-18** (5 dated `money_maker_ready_*Z.md` snapshots from 0512-0514) to `reports/archive/money_maker_ready/` per the dupe-scan recommendation.
5. **De-dupe files #5 and #12** (HTML twin of same hyrotrader content) — keep the `.md`, drop the `.html` once `90day_pages_*` page is retired.
6. **Tag file #6** (ai_tournament_methodology_swarm_review) explicitly as "ranking comparability, n=30 OK; graduation still needs PAPER_PILOT_HARNESS gates".
