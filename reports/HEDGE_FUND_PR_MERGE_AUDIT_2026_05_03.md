# Hedge-Fund PR Merge Audit — 2026-05-03

**Auditor:** Claude Code (Sonnet 4.6)  
**Window:** 2026-05-02 08:00Z → 2026-05-03 08:45Z  
**Reference doc:** `reports/HEDGE_FUND_MASTER_COORDINATION_2026_05_02.md` (PR #666)  
**Session:** `docs/pr-merge-audit-2026-05-03`

---

## 1. Per-PR Status Table

| PR | Title (short) | State | Merged At | Merge SHA (head) | Author | Notes |
|----|--------------|-------|-----------|-----------------|--------|-------|
| **#659** | Per-class walk-forward UI card | ✅ MERGED | 2026-05-02 07:36Z | `fb620358d86b` | eltonaguiar | Confirmed on main; +82 lines template.html, +183 lines test file |
| **#662** | 3-AI gap synthesis on Kimi PR #658 | ✅ MERGED | 2026-05-02 08:38Z | `1352dadeb3b7` | eltonaguiar | 2 report files; MERGE-AS-DOCS verdict |
| **#663** | Kimi v1 attachments (47 files, docx+18 PNGs) | ✅ MERGED | 2026-05-02 08:38Z | `0b1438efb8d7` | eltonaguiar | 52 changed files, 11 414 additions |
| **#666** | Master coordination synthesis | ✅ MERGED | 2026-05-02 08:38Z | `e1e8285aa37b` | eltonaguiar | 4 files, canonical navigation index |
| **#667** | Kimi v2 attachments (53 files, FOOLPROOF_ACTION_PLAN) | ✅ MERGED | 2026-05-02 08:38Z | `d1045cb02ea7` | eltonaguiar | Includes v2.1 self-corrections |
| **#668** | Cloud Agent feature flags (opt-in sidecar) | ✅ MERGED | 2026-05-03 04:34Z | `0f49d61afaa9` | Copilot SWE Agent | config/feature_flags.json only; no production callers wired |
| **#660** | Kimi P0 emergency gates | 🔴 OPEN | — | — | eltonaguiar | 17 comments, all REQUEST_CHANGES/HOLD (see §2) |
| **#661** | Kimi infra v2.0 | 🔴 OPEN | — | — | eltonaguiar | 12 comments, CI failing (see §2) |

### #659 downstream verification

PR #659 was merged at 07:36Z — 8 minutes before PRs #660 and #661 opened. Both of those PRs were rooted on pre-#659 `main` and their branches still silently delete the walk-forward card (per REQUEST_CHANGES comment on #660 at 07:56Z). Neither PR has been rebased since. The #659 changes remain on `main` and are visible in the continuous [skip ci] commit stream; no downstream commit has reverted them.

---

## 2. Stalled PRs — Detailed Blockers and Next Actions

### PR #660 — STALLED (25h+ open, 17 comments, zero follow-up commits since v2.1 partial patch at ~08:15Z 2026-05-02)

**Last activity:** adversarial review posted at 2026-05-03 05:42Z — still REQUEST_CHANGES.

**Active blockers (consensus across ≥4 independent reviewers):**

| Blocker | Detail |
|---------|--------|
| Internal config contradiction | `config/hf_quality_gates.json` ships `min_risk_reward: 1.25`; `config/per_asset_thresholds.json` (same PR, v2.1 commit) explicitly states "R:R floor corrected from 1.25 BACK to 1.50 — 1.25-1.5 band PF 1.01, Kelly -1.6% UNPROFITABLE." Runtime cannot determine which is canonical. |
| `ml_score` gate is a 100% no-op | `per_asset_thresholds.json` proposes `min_ml_score: 0.90`; live `dashboard_data.json` (n=3500 recent_closed, mtime 2026-05-02 14:50) shows **max observed ml_score = 0.865**. A gate at 0.90 blocks 100% of all picks. |
| Live-data refutation of ALL headline numbers | R:R 1.5-2.0 actual PF = 1.211 (claimed 5.81). R:R >2.0 actual PF ≈ 0.95 (claimed 0.35). WINNER_FILTER accuracy claim — WINNER_FILTER is live at `alpha_engine/forward_validator.py:399-569` with STATS tracking. R:R floor 1.5 already in production at `audit_trail/quality_gates.py:513 SMART_PICKS_MIN_RR=1.5`. |
| Zero wiring | Both JSON files consumed by `alpha_engine/hf_quality_gate.py::hf_smart_pick_post_score_reason` which has **zero production callers**. Live gate is `hedge_fund_quality_gate.py::passes_hedge_fund_gate` (wired at `quality_gates.py:4926`), which uses hardcoded Python constants — ignores both JSON files entirely. Net production effect: zero. |
| Missing evidence files | `reports/near_miss_analysis_2026_05_02.md`, `reports/gate_optimization_2026_05_02.md`, `reports/crypto_analysis_2026_05_02.md` cited as sources — **none exist** in repo. |
| PR not rebased | Still silently reverts PR #659 (per-asset-class walk-forward card). Rebase to current `main` is mandatory before any other action. |

**Concrete next action:** Close #660 and open a replacement PR with: (a) rebase on current `main`; (b) a single focused change — R:R ceiling reduction from 3.5 to 2.0 (the only live-data-supported lever; `quality_gates.py:2362-2381` already documents R:R 0-1.5 as the best band); (c) wire into `passes_hedge_fund_gate()` directly, not into the orphan JSON consumer; (d) all claims cite `dashboard_data.json` snapshot + reproducer command.

---

### PR #661 — STALLED (25h+ open, 12 comments, zero follow-up commits, CI failing)

**Last activity:** REQUEST_CHANGES comment at 2026-05-03 01:03Z.  
**CI status:** `test (3.11)` FAILED, `test (3.12)` CANCELLED.

**Active blockers:**

| Blocker | Detail |
|---------|--------|
| Fatal ImportError | `alpha_engine/__init__.py` re-exports `StrategyValidator`, `batch_validate`, `ValidationResult` from `statistical_rigor.py` — **none of these symbols exist** in `statistical_rigor.py` on this branch. Any `import alpha_engine` anywhere crashes. This is what breaks CI. |
| `statistical_rigor.py` is fabricated diff | `git diff origin/main:alpha_engine/statistical_rigor.py origin/infrastructure-modules-2026-05-02:alpha_engine/statistical_rigor.py` returns empty. The file already shipped in PR #626 (commit `80b7ac53466`). PR takes credit for existing code while introducing the export bug. |
| `decay_tracker.py` breaks a production caller | Old stateless `compute_decay_blocks(...)` API removed; `tools/run_strategy_research.py:36,183` call the old API and were not updated. |
| PR not rebased | Same as #660 — silently deletes PR #659's walk-forward card and 178-line regression test. |
| Wire-Up Rule violation | Zero production callers for `TrackCalculator`, `get_track_wr`, `DecayTracker`. No `## Wiring Plan` section. |
| Storm-commit data files | PR drags in stale snapshots from `KIMI_RISEOFTHECLAW/data/*`, `audit_dashboard/data/*`, `copy_trader_intel/data/*`, `ml_consensus/*` that collide with pipeline state. |

**Concrete next action:** Ask Kimi to split into 3 surgical PRs post-rebase:
1. **PR A** — `track_calculator.py` only, with PF formula fix (`sum(wins)/abs(sum(losses))` not `count(wins)/count(losses)`), wired to `audit_trail/dashboard_generator.py::_build_forward_wr_section`, default-OFF env flag `TRACK_CALC_ENABLED`.
2. **PR B** — `decay_tracker.py` only, preserving old `compute_decay_blocks()` as deprecated wrapper, updating `tools/run_strategy_research.py`, and a `## Wiring Plan` pointing to `production_scanner.py`.
3. **PR C** — Drop `statistical_rigor.py` entirely (already on main); clean up the `__init__.py` export list to not reference non-existent symbols.

---

## 3. GHA Monitor Summary

**Finding:** The workflow named `system-health-check.yml` fires on `cron: '0 */2 * * *'` — every **2 hours**, not every hour. Over the ~24h window since 08:00Z 2026-05-02, the expected run count is **~12 runs**, not ~24 as the audit request implied.

Additional health-adjacent workflows found:
- `strategy-health-monitor.yml` — strategy-level health
- `ml-health-monitor.yml` — ML model health  
- `pick-monitor-30min.yml` — every 30 min pick monitor
- `live-position-monitor.yml` — live position tracking
- `continuous-improvement-monitor.yml`

**GHA run color for system-health-check:** Cannot determine from MCP tools alone (no `gh run list` access). No RED artifacts found in repo commits since 08:00Z 2026-05-02 — all `[skip ci]` commits are normal pipeline output (scan cycles, outcome resolver, momentum trackers, etc.). No emergency/alert commits visible in the 50-commit sample inspected.

**Note:** The `chore(audit-dashboard): refresh payload [skip ci]` commit at 2026-05-03T08:07Z confirms the dashboard generator is running successfully and writing to main.

---

## 4. Gemini Phase-0 Progress Checklist

Gemini Antigravity v3 identified 4 remaining Phase-0 actions (9/13 already implemented per their audit). Status as of 2026-05-03:

| # | Action | Target | Status | Evidence |
|---|--------|--------|--------|----------|
| 1 | Crypto C-Tier suspension behind `HF_CRYPTO_CTIER_ENABLED` env flag | `alpha_engine/hedge_fund_quality_gate.py:238` | ❌ NOT IMPLEMENTED | Line 238 is mid-CRYPTO-path; no C-Tier classification or env flag exists. The file does gate on banned symbols, banned strategies, confidence dead band, and RSI killzone — but no confidence-tier bucketing. |
| 2 | `SMART_PICKS_CRYPTO_LONG_ONLY=False` | `audit_trail/quality_gates.py:534` (actual: line 596) | ❌ NOT IMPLEMENTED | `quality_gates.py:596` currently reads `SMART_PICKS_CRYPTO_LONG_ONLY = True`. Setting to `False` would re-enable CRYPTO short picks. Gemini's rationale: CRYPTO system-wide WR drag is partly from missing short-side alpha. |
| 3 | `ml_score` dual-path shadow gate | `alpha_engine/hf_quality_gate.py:100-102` | ❌ NOT IMPLEMENTED | Lines 100-102 show `elite = float(scored.get("elite_score") or scored.get("score") or 0)` — still using `elite_score`. No `ml_score` dual-path logic present. Note: implementing this is BLOCKED by PR #660's finding that max observed `ml_score` is 0.865 (a gate at 0.82 would function; at 0.90 would block everything). |
| 4 | `UNKNOWN` asset class reclassification | `alpha_engine/outcome_resolver.py` | ❌ NOT IMPLEMENTED | `outcome_resolver.py` uses `pick.get("asset_class", "UNKNOWN")` with no reclassification attempt. The `asset_class_health` dashboard shows `unknown` source as PF 0.35 drag (7% volume share); reclassification would sharpen per-class metrics. |

**Summary: 0/4 Phase-0 actions implemented.**

---

## 5. Toxic-Strategy Enforcement Bug (Copilot §14)

**Finding: CONFIRMED AND SEVERE.**

- `BLACKLISTED_STRATEGIES = {'quan_engine_scalp', 'binance_smart_money', 'hl_funding_fade'}` is defined in:
  - `alpha_engine/copy_trader_bridge.py:38` — enforced at bridge layer only
  - `alpha_engine/config.py:201` — definition only, no enforcement at call site
- `alpha_engine/smart_picks_engine.py` — **no blacklist check** (grepped: zero references to `BLACKLISTED_STRATEGIES` or `blacklisted_strategies`)
- Result in `alpha_engine/data/closed_picks.json` (n=7,445 total):
  - **5,293 picks** (71.1%) have `strategy = quan_engine_scalp`
  - Date range: 2026-03-07 → 2026-04-25
  - The blacklist entry `quan_engine_scalp: 0% WR, -794% total PnL zombie` has been on `BLACKLISTED_STRATEGIES` since 2026-04-02 per the comment in `copy_trader_bridge.py:38`
  - All 5,293 picks are in `closed_picks.json` — they passed through pick generation and outcome resolution unchecked

**The enforcement bug:** `copy_trader_bridge.py:192` checks the blacklist at the **copy-trader output layer** only. The main pick-generation path (`smart_picks_engine.py`) and outcome resolver (`outcome_resolver.py`) do not check `BLACKLISTED_STRATEGIES` from `config.py`. These picks are counted in all PF/WR calculations, massively dragging CRYPTO metrics (18% of CRYPTO volume at PF 0.70 per `dashboard_data.json::asset_class_health`).

**Estimated fix effort:** ~30 minutes. Add one call to `config.BLACKLISTED_STRATEGIES` at the pick-intake gate in `smart_picks_engine.py` (before `calculate_smart_score`), and a parallel check in `outcome_resolver.py` before resolution counts. This matches the Copilot §14 description.

---

## 6. Recommended Operator Next-Actions (Priority Order)

| Priority | Action | Owner | Effort |
|----------|--------|-------|--------|
| **P0** | Fix toxic-strategy enforcement bug: add `BLACKLISTED_STRATEGIES` check in `smart_picks_engine.py` + `outcome_resolver.py`. 5,293 zombie picks contaminating all metrics. | Any agent | ~30 min |
| **P1** | Close PR #660, open replacement PR with single focused change: R:R ceiling reduction 3.5→2.0 + wire into `passes_hedge_fund_gate()` directly. All claims cite `dashboard_data.json` with reproducer. | Kimi / operator | ~2h |
| **P1** | Close PR #661, ask Kimi to submit 3 surgical replacement PRs (track_calculator / decay_tracker / __init__ cleanup). Fix CI ImportError first (drop bogus `statistical_rigor` re-exports from `__init__.py`). | Kimi | ~3h |
| **P2** | Implement Gemini Phase-0 item 4 (UNKNOWN reclassification) in `outcome_resolver.py` — highest-ROI of the 4 since it cleans the per-class health metrics used for all gate decisions. | Any agent | ~1.5h |
| **P2** | Implement Gemini Phase-0 item 1 (Crypto C-Tier env flag) — but only AFTER confirming what "C-Tier" means in the current codebase; the tier taxonomy is not defined in `hedge_fund_quality_gate.py` as of today. Define first, then gate. | Any agent | ~2h |
| **P3** | Wire orphan goldmines per PR #666 §5 — `consensus_tier.py` (1.2h), `dsr_pick_filter.py` (2.5h), `kelly_position_sizer.py` (1.5h). All have zero production callers but are estimated to add 3-5 pp WR. | Any agent | 5-8h total |
| **P3** | Implement Gemini Phase-0 items 2+3 (`SMART_PICKS_CRYPTO_LONG_ONLY=False`, `ml_score` shadow gate) only AFTER the toxic-strategy bug is fixed — current CRYPTO metrics are too contaminated to calibrate new gates reliably. | Any agent | ~1h each |

---

*Generated by Claude Code (Sonnet 4.6) — this is a status report; no PRs were auto-merged, no config was modified.*
