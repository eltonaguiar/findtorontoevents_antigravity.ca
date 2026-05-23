# PR Integration Plan — 2026-05-03 05:40Z

**Author:** Antigravity session, cross-checked via cavecrew-investigator + cavecrew-reviewer subagents.
**Source of truth:** `gh pr list --state open` snapshot @ 05:35Z; `audit_dashboard/data/dashboard_data.json::performance.asset_class_health` @ 04:03Z.
**Goal alignment:** Goal #1 — phenomenal performance across ALL asset classes (T2+ baseline).

---

## Goal #1 baseline (no movement since session start)

| Class | PF | WR | n | Status | Tier gap |
|---|---|---|---|---|---|
| EQUITY | 1.41 | 52.9% | 420 | stable | T2-cand → scale |
| CRYPTO | 1.24 | 44.6% | 8188 | watch | sub-T2 → cut drag |
| FOREX | **0.27** | 46.4% | 1169 | **stressed** | sub-floor → corruption-filter rescue |
| COMMODITY | 1.78 | 46.9% | 750 | stable | T2 PF met → lift WR |
| ETF | 1.24 | 55.2% | 87 | stable | T3 → n=100 |
| BOND | 1.72 | 55.6% | 18 | thin_sample | T2 thresholds met → grow n |

The FOREX corruption-filter root cause (PR #724 investigation) remains highest-leverage single fix: PF 0.27 → ~1.15-1.25 estimated 5× lift if `dashboard_generator.py:4163-4240` JPY-divergence threshold relaxed correctly.

---

## Open PR triage (12 PRs as of 05:35Z)

### Merge-readiness scorecard

| PR# | Title | Age | Merge | CI | Diff | Verdict |
|---|---|---|---|---|---|---|
| 735 | docs: per-asset playbook | 0d | MERGEABLE | GREEN | 564/0 | **SHIP NOW** (mine, doc-only, low risk) |
| 734 | audit hourly-05z refresh | 0d | MERGEABLE | GREEN | 183/0 | **SHIP NOW** (audit snapshot) |
| 597 | rapid_fire pair-block + revalidator | 1d | MERGEABLE | RED | 1414/27 | **SHIP-WITH-CHANGES** (Wire-Up Rule + import-warn) |
| 661 | Infra v2.0 (PSR/DSR/Decay) | 0d | MERGEABLE | RED | 626/159 | HOLD — CI red, 4 new orphan modules need wiring plan |
| 660 | P0 Emergency Gate Fixes | 0d | CONFLICTING | GREEN | 306/22 | **HOLD — CRITICAL contradiction** (R:R 1.25 vs 1.50, ml_score 0.82 vs 0.90 between two files in same PR) |
| 644 | per-asset quality-gate plan | 0d | CONFLICTING | GREEN | 737/52 | REBASE + scope check (overlaps #723 on `quality_gates.py`) |
| 723 | B18 shadow-mode promote | 0d | CONFLICTING | — | 456/6 | REBASE (overlaps #644) |
| 615 | scanner blockers | 1d | CONFLICTING | RED | 490/37 | **HOLD** — circuit_breaker reset risks repeating `feedback_circuit_breaker_stale_state_leak` incident |
| 724 | FOREX/CRYPTO investigation docs | 0d | CONFLICTING | GREEN | 1390/0 | REBASE — high-value, doc-only |
| 726 | hourly-04z audit | 0d | CONFLICTING | — | 177/0 | SUPERSEDED by #734 — close |
| 676 | events data quality | 0d | CONFLICTING | — | 84/240 | REBASE |
| 608 | tradingagents smoke test | 1d | CONFLICTING | RED | 262/5 | REBASE — gated test, low risk |

### Conflict cluster (HIGH attention)

| Files | PRs | Risk |
|---|---|---|
| `audit_trail/dashboard_generator.py` + `audit_trail/quality_gates.py` | #644 ↔ #723 | Whichever lands first forces the other to rebase + reconcile gate logic |

---

## Adversarial findings — top 3 ship candidates

### PR #660 — `P0 Emergency Gate Fixes` — **CANNOT SHIP**

Two file-level contradictions inside the single PR:

1. **R:R floor disagreement.** `hf_quality_gates.json` sets `min_risk_reward: 1.25` ("+$937/mo lift"); `per_asset_thresholds.json` changelog says "1.25 BACK to 1.50" ("1.25-1.5 band: PF 1.01, Kelly -1.6% — UNPROFITABLE"). Self-refuting.
2. **ml_score floor disagreement.** Same PR ships `min_ml_score: 0.82` ("optimal F1=0.68") AND a changelog claiming "0.8-0.9 band has 39.3% accuracy, worse than coin flip."
3. Cited evidence files (`near_miss_analysis_2026_05_02.md`, `shadow_blocked.json`) don't exist in repo.
4. No precedence rule when both config files are loaded.

Comment posted on PR. Author must split or align before re-review.

### PR #615 — `scanner blockers` — **HOLD**

Resets `circuit_breaker.json` from EMERGENCY → NORMAL while underlying state shows -25,465% drawdown. Repo memory `feedback_circuit_breaker_stale_state_leak.md` (2026-04-27 incident): a prior naive reset locked `alpha_engine_fast` for ~115h because `max_picks=0` leaked via `min()` even after status flip. Fix shipped requires atomic clearing of ALL state fields (active_count, daily_loss, max_picks, cumulative DD).

Other 4 fixes in this PR (stdout hardening, yfinance dict, `production_scanner` always-on print) are clean. Recommendation: **split** circuit_breaker reset into its own PR with the invariant test `assert status == NORMAL implies max_picks > 0 and active_count == 0`. Comment posted.

### PR #597 — `pair-block + revalidator` — **SHIP-WITH-CHANGES**

Required:
1. Add `## Wiring Plan` section to PR body for `alpha_engine/pick_revalidator.py` (target = `smart_picks_engine.py`, ETA = 7d, gate = `PICK_REVALIDATOR_ENABLED=1`). Per CLAUDE.md Wire-Up Rule.
2. `isolated_signal_integrator.py:129-135` — fallback when `is_blocked_pick` import fails returns False = silent fail-open. Add `log.warning` before falling back.

19 tests pass. The rapid_fire pair-block bypass fix is the highest-impact code change in this PR (closes the `feedback_long_source_bias`-class leak). Comment posted.

---

## Recommended merge order

| # | PR | Action | Why |
|---|---|---|---|
| 1 | #735 | Merge (mine, doc-only) | Codifies playbook, zero risk |
| 2 | #734 | Merge | Audit refresh, doc-only |
| 3 | #726 | Close as superseded | #734 supersedes |
| 4 | #597 | Author addresses 2 changes → merge | Highest-impact code fix on the list |
| 5 | #724 | Rebase onto main → merge | Doc-only, unblocks FOREX corruption-filter follow-up |
| 6 | #676 | Rebase → merge | Events data quality, isolated scope |
| 7 | #608 | Rebase → merge | Gated test, near-zero risk |
| 8 | #644 | Reconcile with #723 → merge winner first | Gate-policy doc; pick coordinator |
| 9 | #723 | Rebase against #644 winner → merge | B18 backend |
| 10 | #660 | **Author splits PR**, fix contradictions → re-review | Cannot ship as-is |
| 11 | #615 | **Author splits PR**, isolate circuit_breaker reset → re-review | Safety bypass risk |
| 12 | #661 | Author wires the 3 new orphan modules per Wire-Up Rule → re-review | Breadth-not-depth pattern |

---

## Highest-leverage next implementation steps (ROI-ranked)

### A. Land the FOREX corruption-filter fix (5× PF lift for FOREX)
Per PR #724 investigation: `audit_trail/dashboard_generator.py:4163-4240::_pnl_pct_looks_corrupt()` over-rejects 405/911 JPY pairs. Surgical fix: raise JPY-divergence threshold from 10× → 50× behind opt-in flag. Could recover FOREX PF 0.27 → ~1.15-1.25.

**Acceptance:** rerun canonical recompute over the same 1169 closed FOREX picks; require post-fix PF ≥ 1.0 with bootstrap CI not crossing 0.8. If pass → ship; if fail → keep flag OFF and document.

### B. Cut the CRYPTO drag (move from PF 1.24 → ~1.4)
PR #724 verified the *real* CRYPTO drag is `alpha_engine` (29.5%, PF 0.81) + `baby_strats_forward` (15.5%, PF 1.03), NOT `quan_engine` (3.4%, PF 0.30) + `unknown` (0%) as previously claimed. Action: investigation-before-kill on those 2 strategies; mutate-three-axis per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`; only then trim weight if mutation fails.

### C. Validate post-resolver-v2 numbers via OOS walk-forward
Per `walk_forward_by_class()` table user pasted: COMMODITY OOS Sharpe -2.41, CRYPTO -0.51, FOREX -1.41 — all negative despite "stable" headline status. ETF OOS Sharpe +6.37 looks too good (n=12 folds, decay 10.8 — likely overfit). Add a fold-count + decay floor to the dashboard's "stable" classifier so headlines stop reporting OOS-negative classes as stable.

### D. Wire #735 playbook into peer agent prompts
The new playbook lives in `updates/2026-05-03-per-asset-class-enhancement-playbook.md`. Add it to `AGENTS.md` as the canonical reference for any "weak asset class" investigation, replacing ad-hoc patterns from past sessions.

---

## Cadence & monitoring

- **Hourly cron** (`trig_0119HU5VfusFrJF5bw5x9HYA`): per-asset PF/WR refresh + PR triage. Active.
- **24h doc-PR audit** (`trig_01K5v5LuHQBGVPpMuAhDdJgQ`): one-shot at 2026-05-04T05:32Z. Will post a follow-up audit PR.
- **20-min in-session check**: `RemoteTrigger` minimum interval is 1h, so manual checks every ~20 min from this session: pull `gh pr list --state open` + `audit_dashboard/data/dashboard_data.json::asset_class_health`, diff against this baseline, comment on movement.

---

## What I'm doing right now

1. ✅ Posted REQUEST_CHANGES-equivalent comments on #660, #615, #597 with specific blockers.
2. ✅ Captured this integration plan as a single committable doc.
3. ⏭ Open PR for this plan (next).
4. ⏭ 20-min wakeup loop on PR/payload state.

---

## Cross-AI consult attempted

- Cerebras API — key returned 401 "Wrong API Key". Skipped.
- opencode CLI installed but TUI-only per `reference_cli_agent_consultation.md`. Skipped for non-interactive flow.
- ollama present locally — usable for next iteration if a 2nd-opinion LLM is needed.

---

_Generated 2026-05-03 by Antigravity session. Successor sessions: read this doc + `updates/2026-05-03-per-asset-class-enhancement-playbook.md` (PR #735) + `reports/ASSET_CLASS_RESCUE_STATE_2026_05_03_0510Z.md` first._
