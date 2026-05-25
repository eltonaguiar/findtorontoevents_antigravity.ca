# 2026-05-25 Marathon Session — Findings & Action Log

**Session scope:** 7.7M JSONL transcript (~392 turns), 4 parallel-agents at peak, 3-engine external-AI consultations (codex/grok/gemini), and ~30 commits pushed to `main`.

---

## 1. Executive Summary

This session moved 17 open action items from a multi-AI transcript scan (_transcript_scan_20260525_055154.md_, 409 deduped items) to **all-clear or drafted** status.

| Deliverable | Status |
|-------------|--------|
| 3 audit reports published + incidents DB seeded | Done |
| 3 P0 code-fixes applied to `alpha_engine` (confidence weight, trust_score, FOREX) | Done |
| 2 broken tools unblocked (`check_resolver_health`, `audit_won_picks`) | Done |
| Live deploys verified (`pick_funnel.html`, `ai-tournament.html` fixes) | Done |
| CI Tests green after 30-hour failure streak | Done |
| 1 major data-artifact debunked (COMMODITY) + 1 hypothesis pre-registered (H-101) | Done |

Remaining **genuinely open** (require your review or are benignly queued):

| # | Item | Decision needed |
|---|------|---------------|
| 1 | `smart_picks_engine.py` — confidence floor 0.10 vs 0.05 | Already committed; settle preference for v2 weighting |
| 2 | `trust_score` historical backfill (38k closed rows are NULL) | Yes — approve migration? |
| 3 | `FOREX pnl_pct < -100%` clamp + correct `−106,700%` row | Yes — approve DB UPDATE? |
| 4 | `won-picks` 10 contradictory rows (WON + negative PnL) | Yes — run `--correct`? |
| 5 | XLI sector-ETF category backfill in MySQL | Yes — approve DB UPDATE? |
| 6 | `edge_filter_engine_v3.py` exit-1 (silently caught) | Low priority |
| 7 | 4 verification follow-ups (0-for-648 gate claim, regime_adaptive×ETF, etc.) | 3 queued as enhancements in incidents seed |

---

## 2. CRYPTO 78% WR → **DISPUTED** (heavyweight finding)

The headline "Smart Picks CRYPTO = 78.9% WR / PF 9.69" on `pick_funnel.html` is **poisoned by 4 leakage signals**:

1. **1,864 duplicate rows** (`symbol, signal_ts, source`) in raw 90d CRYPTO.
2. **97 EXPIRED rows** mislabeled as WON at 63.9% WR (noise ~50%).
3. **12 LOST rows** with positive `sum_pnl` (ATR-trailing bookkeeping bug).
4. **91.7% concentration** in `claude_gainer_st` (a source with only 3 closed rows in raw DB).

**Live DB-verified reality** (decisive, last 90d): **39.4% WR**, PF **0.37**, mean PnL **−4.6%**.

Deliverables:
- `reports/2026-05-25_crypto_78pct_wr_verification.md`
- `audit_dashboard/pick_funnel.html` now carries a **DISPUTED** banner above the nav-surface table (not deleted).

---

## 3. COMMODITY COT "Edge" → **FULLY DEBUNKED** (4-method convergence)

Z-AI (NIM 5-model) panel called this the `#1 alpha`. Three independent in-house methods proved it a **data artifact**:

| Method | Verdict |
|--------|---------|
| DB trade-level forensics | 87.6% is one symbol (CT=F cotton), 30d-only hot streak, effective Bonferroni tests ≈ 7 (not 200) |
| Filter pipeline tracing | `top_edges.py` runs **no dedup**; same cell collapsed PF 20.54 → 0.17 after prior 72h COT dedup |
| External AI panel (codex/grok/gemini) | `DATA_QUALITY_LEAKAGE`, ~90% confidence, recognized as residue from **already-rejected H-001** (2026-05-20) |
| Live `build_pf_registry` merged-cohort rerun | COMMODITY policy-clean NET PF → **0.937** (inside predicted 0.3–1.0 collapse range) |

MySQL extension to `build_pf_registry` was built (`PF_REGISTRY_INCLUDE_DB=1`, default off, committed). When enabled, it merges 45,432 DB rows into the same dedup+policy+NET pipeline and **confirms the edge vanishes**.

Hypothesis **H-101** pre-registered in `reports/hypothesis_registry.json` with kill criteria (post-fix PF<1.10 || n<30 || single_underlying>50% → REJECT).

---

## 4. Multi-AI Panel Meta-Review (Lesson)

The most important lesson of the session: **multi-AI consensus is only as good as the prompt grounding.**

- **Panel A** (NVIDIA NIM: Kimi/GPT-OSS/GLM/Nemotron/Mistral) saw pre-dedup numbers → consensus "COMMODITY is #1". Wrong.
- **Panel B** (Claude/codex/grok/gemini) saw the same numbers **plus leakage signals** → consensus `DATA_QUALITY_LEAKAGE`. Right, and 3 independent in-house methods confirmed it.

Roo's session did, however, surface a **striking new claim** (queued for verification):
> 648 un-gated picks (moderate+low confidence) went **0-for-648**, destroying **−825% PnL**. 300 gated picks generated **+994%**.

Enhancement seeded in `tools/audit_pick_funnel/seed_incidents_enhancements.py` to verify this claim with the same rigor that killed the COMMODITY claim.

---

## 5. P0 Code Fixes Applied (3 commits, live)

All applied with operator authorization per `docs/INCIDENTS_TRIAGE_PROCESS_2026-05-25.md` Phase 3 (HITL gate waived for code-only reversible changes).

### 5a. `alpha_engine/smart_picks_engine.py` — kill inverted confidence weighting
**Bug:** `confidence` weighted at 30% (line 97), but Spearman(confidence, pnl) = **0.07** (near-zero predictive power).
**Fix:** Dropped confidence weight 0.30 → **0.10**; freed 20% redistributed to ml_composite (0.60 → 0.75) and forward_wr (0.10 → 0.15).
**Caveat:** `elite_score` IC is contradictory (docstring says r=-0.001, but SCORE_PNL_EDGE_REVIEW reports 0.20/0.39). Not promoted yet — requires follow-up.

### 5b. `alpha_engine/active_picks_sync.py` — fix trust_score NULL
**Bug:** Trust_score **99.96% NULL** in `trading_picks` (only 17/48,348 rows populated on closed book = 5/38,852). HIGH CONVICTION overlay's retrospective WR claims were unreproducible.
**Fix:** Added `trust_score`, `elite_score`, `confidence` to the 11-field persistence dict on OPEN→WON/LOST transitions. Forward fix only.

### 5c. `alpha_engine/mysql_trading_sync.py` — zero-allocate FOREX
**Bug:** FOREX kill-switch existed only inside `scanner.py:2559`'s `nc_quality_gate`, missing `multi_asset_copytrader` (164 picks since 05-24), `non_crypto_consensus` (118), and 5 other sources. **387 FOREX picks leaked**.
**Fix:** Added FOREX block at the **single funnel** every pick traverses before DB upsert. Preserves the `FOREX_HIGH_CONVICTION` carve-out (39 `cta_replicator` picks, PF 2.51).

All 28 existing tests pass after these changes.

---

## 6. Incident & Enhancement Seeding

39 open incidents (18 P0) / 38 enhancements identified at `audit/incidents.html`.

Top 3 P0s (triaged by codex/grok/gemini consensus):
1. `smart_picks_engine` confidence weighting inverted → solved (§5a)
2. FOREX `pnl_pct < -100%` missing clamp + `−106,700%` row poisoning ROI → DB mutation, HITL held
3. Resolver/forward_validator **dead** — `signal_outcomes` **82 days stale** → forwards all AI tournament picks to "BUILDING" tier (n_resolved=0)

New additions to `seed_incidents_enhancements.py`:
- **1 P1 incident**: Multi-AI panel grounding failure (prompt missing leakage context)
- **3 Enhancements**: Verify 0-for-648 quality-gate claim; verify `regime_adaptive × ETF` Wilson CI; verify `kimi_signal_tracking` / `aggregated_picks` per-source claims

---

## 7. Infrastructure & Tooling Fixes

| Tool | What was broken | Fix |
|------|----------------|-----|
| `tools/db_env.py` | Legacy per-DB env vars (`DB_PASS_STOCKS` etc.) held stale passwords, triggered host-blocks | `DB_PASSWORDS_JSON` is now canonical source; legacy vars demoted to last-resort fallback |
| `tools/check_resolver_health.py` | Missing `import argparse` → crashed on every launch | Added import |
| `tools/audit_won_picks.py` | Referenced nonexistent columns `asset_class` and `opened_at` | Renamed to `category` and `created_at` per actual schema |
| `tests/test_tier2_hero_cards.py` | Fixture had hardcoded `last_signal_at='2026-04-25'` — rotted when date hit 30d stale threshold on 2026-05-25 | Relative date (`datetime.now(UTC) - timedelta(days=18)`) |
| `build_pf_registry.py` | Read only 32 JSON ledgers (60 COMMODITY rows); top_edges read MySQL (1,219 rows) — two pipelines never intersected | Added `_load_mysql_rows()` gated by `PF_REGISTRY_INCLUDE_DB=1` (default off) |

CI Tests has been **green since 07:51 UTC** (broken for 30+ hours before the fixtures were fixed).

---

## 8. UI / Frontend Bugs Fixed

| Page | Bug | Status |
|------|-----|--------|
| `/audit/pick_funnel.html` | Broken HTML comment leaked `"block. -->"` and header text above Click Funnel panel | Fixed + deployed |
| `/audit/pick_funnel.html` | Missing 14d/48h recency cohorts, no active/closed pick summary | Added amber `[14d]` subset per section + magenta `[48h]` hero panel. **Verified live.** |
| `/audit/ai-tournament.html` | Brain icon (🧠) did nothing because `allPicks` was local-scoped `let`, but `ai_postmortem_helper.js` read `window.allPicks` (undefined) | Exposed `window.allPicks = allPicks` after merge |
| `/audit/ai-tournament.html` | Per-day `picks_YYYYMMDD.json` files 404'd (not generated/deployed) | Added fallback: when 5 daily files are all missing, explicitly loads `ai_tournament_picks_latest.json` |

---

## 9. Money-Maker-Readyv2 vs Actual Performance

**Verdict: 0/6 classes pass the v2 bar.** 3 classes degraded in last 72h.

| Class | v2 PF target | Actual PF | v2 WR target | Actual WR | n_actual | Verdict |
|-------|-------------|-----------|-------------|-----------|----------|---------|
| CRYPTO | ≥ 1.50 | 1.14 | ≥ 50% | 43% | 728 | FAIL |
| EQUITY | ≥ 1.30 | 0.90 | ≥ 50% | 33% | 33 | FAIL |
| COMMODITY | ≥ 1.50 | 0.31 | ≥ 50% | 11% | 28 | FAIL |
| ETF | ≥ 1.50 | 11.99 | ≥ 50% | 50% | 2 | INSUFFICIENT-n |
| FOREX | ≥ 1.30 | 0.55 | ≥ 50% | 40% | 53 | FAIL |
| BOND | ≥ 1.00 | 0.00 | ≥ 50% | 0% | 8 | FAIL |

Fresh recency data (recent 14d) shows a dramatic divergences vs all-time aggregates:
- CRYPTO: 38.4% WR in 14d (down from 78.9% all-time) → **0 closed in 48h, 322 still active**
- EQUITY: actually improving (37% all-time → 67% in 14d → 55% in 48h)
- FOREX: 83.7% WR in 14d but PF 0.103 → death-by-small-wins-big-losses

Report: `reports/2026-05-25_money_maker_readyv2_vs_actual.md`

---

## 10. New Skills Shipped

| Skill | Where | What |
|-------|-------|------|
| `consult-nvidia-models` | `.claude/skills/consult-nvidia-models/SKILL.md` | Multi-model fan-out across NVIDIA Integrate API (NIM). Panels for wide-diversity, reasoning-heavy, coding-heavy. |
| `consult-cloudflare-models` | `.claude/skills/consult-cloudflare-models/SKILL.md` | Same fan-out pattern for Cloudflare Workers AI. Includes `@cf/` prefix, per-account rate-limit, response-shape variation notes. |

Both formalize the pattern that caught the COMMODITY debunk.

---

## 11. Recommendations — What to Do Next

1. **Operator call on DB mutations** (P0):
   - Approve FOREX `pnl_pct < -100%` clamp + correct `−106,700%` row
   - Approve `--correct` run on 10 WON+negative-PnL rows
   - Approve XLI sector-ETF category backfill
   These are now the only items requiring a DB WRITE.

2. **Resolver restart** (P0):
   - The forward-resolution pipeline is dead (82 days). AI tournament is entirely blind (0 resolved, 1,607 submitted, all "BUILDING" tier). Draft fix is next.

3. **Elite_score weight promotion** (P1 — needs IC reconciliation):
   - smart_picks_engine docstring says r=-0.001, but SCORE_PNL_EDGE_REVIEW says 0.20/0.39. If the positive measurement is real, promoting it would deliver +0.30→+0.39 Spearman lift.

4. **Flip `PF_REGISTRY_INCLUDE_DB=1` for one hourly run:
   - This would merge DB+JSON into a single policy-clean NET cohort. Watch for expected COMMODITY PF ~0.94 (validates the debunk).

5. **Periodic fixture audit**:
   - The `test_tier2_payload_staleness_detection` failure mode (hardcoded date rotting at 30d threshold) will recur. Recommend periodic scan for `20\d{2}-\d{2}-\d{2}` in test fixtures against wall-clock.

---

## 12. File Index (new/updated in this session)

**Reports/docs (created):**
- `reports/2026-05-25_crypto_78pct_wr_verification.md`
- `reports/2026-05-25_commodity_cot_edge_deep_dive.md`
- `reports/2026-05-25_policy_clean_vs_top_edges_funnel.md`
- `reports/2026-05-25_commodity_cot_edge_triangulation.md`
- `reports/2026-05-25_commodity_cot_edge_consult_{codex,gemini,grok}.md`
- `reports/2026-05-25_money_maker_readyv2_vs_actual.md`
- `reports/2026-05-25_md_sweep_action_items.md`
- `reports/2026-05-25_smart_picks_inverted_weight_fix_DRAFT.md`
- `reports/2026-05-25_high_conviction_trust_score_audit.md`
- `reports/2026-05-25_forex_zero_allocate_filter_DRAFT.md`
- `reports/2026-05-25_dashboard_data_path_canonicalization.md`
- `reports/2026-05-25_n_counter_disagreement.md`
- `reports/2026-05-25_multi_ai_panel_meta_review.md`
- `reports/2026-05-25_session_deploy_and_ci_health.md`
- `reports/2026-05-25_asset_class_edge_audit_deepseek_session.md`
- `docs/INCIDENTS_TRIAGE_PROCESS_2026-05-25.md`
- `audit_reports/ASSET_CLASS_EDGE_AUDIT_2026-05-25.md`

**Data (created):**
- `audit_dashboard/data/pick_summary_stats.json`
- `audit_dashboard/data/pick_summary_stats_2w.json`
- `audit_dashboard/data/pick_summary_stats_48h.json`

**Code (modified by commits):**
- `audit_dashboard/pick_funnel.html`
- `tools/build_pf_registry.py`
- `tools/db_env.py`
- `tools/check_resolver_health.py`
- `tools/audit_won_picks.py`
- `tests/test_tier2_hero_cards.py`
- `alpha_engine/smart_picks_engine.py`
- `alpha_engine/active_picks_sync.py`
- `alpha_engine/mysql_trading_sync.py`
- `audit_dashboard/ai-tournament.html`
- `tools/audit_pick_funnel/seed_incidents_enhancements.py`
- `tools/audit_pick_funnel/build_recency_summary.py`
- `updates/index.html`
- `CLAUDE.md`
- `reports/hypothesis_registry.json`

---

*(End of review — 53 commits audited, 30+ reports indexed, 3 fixes live.)*
