# PR Specs — Supreme Edge P0 Cluster (2026-05-12)

Source: `updates/2026-05-11-money-maker-master-plan.html` cross-cutting P0 cluster + Ernie reality-check.
Branch base: `main`. Each PR self-contained, small enough to swarm-review.

---

## PR-A — Remove SPORTS from /audit asset-class scope

**Goal:** `/audit` shows alpha-trading classes only. Sports betting lives at `/live-monitor/sports-betting.html` per Goal #2 (CLAUDE.md).

**Rationale (Ernie + user):** SPORTS is a different beast — different KPIs (CLV, vig, sport-tier matrices), different infra, different gate. Mixing inflates the asset-class dropdown + confuses verdicts.

**Files:**
- `audit_trail/dashboard_generator.py` — `compute_asset_class_health()` (~L5301): exclude `SPORTS/BETTING/SPORT/BET` from class enum before aggregation.
- `audit_dashboard/template.html` — asset-class dropdown: hide SPORTS option.
- `audit_dashboard/template.html` — add banner under MAJOR GOAL section: "Sports betting tracked at `/live-monitor/sports-betting.html`".

**Risk:** Low. SPORTS already filtered from `picks.active` at L15785; this just removes the empty/noisy entry from aggregate.

**Verification:**
- `audit_dashboard/data/dashboard_data.json::performance.asset_class_health` no longer contains `SPORTS` key.
- `/audit` dropdown does not list SPORTS.
- Playwright: no JS errors when SPORTS filter is absent.

**Frontend impact:** YES. Needs data-feed-job run + Playwright.

---

## PR-B — Verify `kimi_signal_tracking` exec-gate enforcement

**Goal:** Already blacklisted at `alpha_engine/config.py:216`. Per memory `feedback_gate_at_execution_not_generation`, blocks at intake can be bypassed when filter-named accounts re-run picks at exec time. Confirm enforcement.

**Files:**
- `alpha_engine/check_active_picks.py` — add grep test: assert `kimi_signal_tracking` count == 0 in current active picks.
- `tests/test_blacklist_enforcement.py` — new pytest covering BLACKLISTED_STRATEGIES at exec gate.
- `audit_trail/quality_gates.py` — verify `BLOCKED_SOURCE_SYSTEMS` includes `kimi_signal_tracking`.

**Risk:** Low. Verification + test only.

**Frontend impact:** No.

---

## PR-C — Quarantine `crypto_soc_*` baby_strats via BLOCKED_ASSET_STRATEGY_PAIRS

**Goal:** 12 overfit flags in `fwd_vs_bt_divergence.rows`. Per `reports/baby_strats_overfit_quarantine_proposal_2026_05_10.md`.

**Named draggers:** `crypto_soc_proxy_decoupling` (-32.2%), `crypto_soc_delta_divergence` (-21.6%), `crypto_soc_orderflow_absorption` (-14.8%).

**Files:**
- `audit_trail/quality_gates.py` (~L1499): add per-(asset_class, strategy) pairs to `BLOCKED_ASSET_STRATEGY_PAIRS`.
- `tests/test_blocklist_enforcement.py` — pair-level test.

**Risk:** Medium. Per-strategy block, not full source-system kill. Reversible.

**Frontend impact:** Indirect (CRYPTO PF will improve once dragger picks stop emitting).

---

## PR-D — FOREX hard-cap sizing = 0 (explicit gate, NOT silent kill)

**Goal:** Per CLAUDE.md FOREX directive + `docs/MUTATION_THREE_AXIS_PROTOCOL.md`. Apply explicit per-class gate, NOT BLOCKED_SOURCE_SYSTEMS extension.

**Files:**
- `alpha_engine/risk_policy.py` (or equivalent sizing module) — add `FOREX_SIZING_HARD_CAP_USD = 0` until `asset_class_health.FOREX.profit_factor >= 0.8`.
- Block depends on PR #876 (mysql_sync pnl_pct clamp) — must merge first to fix unit corruption.

**Risk:** Low (sizing already OFF per `asset_class_health.sizing_allowed=False`). This makes implicit OFF explicit + auditable.

**Frontend impact:** Indirect (FOREX tile shows explicit "BLOCKED at PF<0.8" reason).

**Dependency:** PR #876 merge first.

---

## PR-E — DB-verify `multi_asset_cot` PF=19.19

**Goal:** Data-integrity smoke test. PF=19.19 is implausibly high; verify against `ejaguiar1_stocks` before naming as Tier-1 seed.

**Files:**
- `tools/verify_multi_asset_cot.py` — new script:
  - Query `bt_backtest_trades` / `closed_picks` for source_system='multi_asset_cot'
  - Compute PF, WR, n
  - Cross-check vs `audit_dashboard/data/dashboard_data.json` value
  - Emit `reports/multi_asset_cot_db_verify_2026_05_12.md`

**Risk:** Read-only.

**Frontend impact:** No (until verdict drives separate PR).

---

## PR-F — Reconcile `claude_gainer_st` winner-vs-blacklist contradiction

**Goal:** `claude_gainer_st` is in BLACKLISTED_STRATEGIES (config.py:216) yet tops EQUITY leaderboard at 78.5% WR / PF 6.12 / n=3472.

**Hypothesis:** Either (a) blacklist enforced only at intake, not on historical leaderboard read; (b) historical picks predate blacklist; (c) `aggregated_picks` re-includes them.

**Files:**
- `tools/audit_blacklist_consistency.py` — new script:
  - For each entry in BLACKLISTED_STRATEGIES, count active picks + leaderboard appearances.
  - Surface diff.
- `audit_trail/dashboard_generator.py` — filter blacklisted from leaderboard render (if hypothesis (a)).

**Risk:** Medium. May change visible numbers on `/audit` Performance tab.

**Frontend impact:** YES (leaderboard numbers change). Needs Playwright.

---

## PR-G — Verify capped-PnL drives MDD calc

**Goal:** Kimi flagged 680% MDD anomaly. Codex made `capped_vs_raw_pnl_gap` a payload-contract field. Confirm `max_drawdown` uses capped not raw.

**Files:**
- `audit_trail/dashboard_generator.py` — locate MDD compute, ensure source = capped PnL series.
- Add `capped_vs_raw_pnl_gap` to `readiness.by_class` payload.
- `audit_dashboard/template.html` — surface gap field in DB Health panel.

**Risk:** Medium. Changes payload contract — Codex `readiness.by_class` work needs coordination.

**Frontend impact:** YES. Needs Playwright + payload-contract review (dashboard-contract-reviewer agent).

---

## PR-H — Cap `quan_engine` to 12% CRYPTO volume share

**Goal:** Kimi finding — `quan_engine` 18% volume @ PF 0.70 drags CRYPTO aggregate. Cap to 12%.

**Files:**
- `alpha_engine/risk_policy.py` — add `PER_SOURCE_VOLUME_CAP = {'quan_engine': {'CRYPTO': 0.12}}`.
- Smart-picks engine: enforce cap at intake.
- Test: assert quan_engine CRYPTO volume share ≤ 12%.

**Risk:** Medium. Changes pick mix.

**Frontend impact:** Indirect (CRYPTO PF should improve over rolling window).

---

# Post-implementation plan

## Frontend-affecting PRs: A, F, G

1. **Pre-merge:** swarm review of spec + diff.
2. **Merge order:**
   - PR-A (simplest, low risk) → first.
   - PR-G (payload-contract) → second (uses dashboard-contract-reviewer).
   - PR-F (leaderboard numbers shift) → third.
3. **Data feed jobs to monitor (each one runs hourly via cron):**
   - `.github/workflows/audit-dashboard.yml` — primary `dashboard_data.json` regen.
   - `.github/workflows/sports-smoke-and-e2e.yml` — sports E2E (verifies PR-A doesn't break sports surface).
   - Any `hf_stats` regen job (`hf_stats.concept_drift`).
4. **Verification gate per merge:**
   - Wait for next `audit-dashboard.yml` cron to run.
   - Diff `audit_dashboard/data/dashboard_data.json` for expected schema change.
   - Run Playwright E2E (golden path + edge cases on `/audit` + sports tab).
   - Capture JS console errors (fail PR if any new errors).

## Backend-only PRs: B, C, D, E, H

- Spec + diff review only.
- pytest must pass.
- No Playwright required.
- Smoke: `python alpha_engine/check_active_picks.py` post-merge.

## Acceptance criteria (all PRs)

- [ ] Swarm review (≥3 engines) returns no MUST-FIX.
- [ ] CI green (pytest + py_compile + lint).
- [ ] For frontend PRs: data-feed job completed + Playwright green + zero new JS errors.
- [ ] Memory updates: any behavioral change recorded in `~/.claude/projects/.../memory/`.
