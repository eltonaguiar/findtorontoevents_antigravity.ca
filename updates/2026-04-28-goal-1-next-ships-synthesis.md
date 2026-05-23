# Goal #1 — What Ships Next, In Order

**Date:** 2026-04-28 (~02:00 UTC)
**Author:** claude-opus-4-7
**Scope:** Single source-of-truth pointer for Goal #1 (phenomenal performance across ALL asset classes on `findtorontoevents.ca/audit`). Consolidates 7 open PRs, 4 deep-dive recommendations, 5 scheduled triggers, and the deconfliction matrix for parallel-agent work.

This doc supersedes the cherry-picked priority lists scattered across `updates/2026-04-27-asset-class-deep-cleanup-key-findings-and-chatlog.md`, `reports/hedge_fund_performance_review_summary_2026_04_27.md`, and `updates/2026-04-28-claude-cursor-alignment-addendum.md`. Read this first; descend to the cited reports for detail.

## 1. Open PRs (current state)

| PR | Branch | Status | Conflict risk | Action |
|---|---|---|---|---|
| **#461** | `extract/asset-class-cleanup-clean` | OPEN, tests pass, 2 bot commits leaked via rebase | LOW (own scope) | **Squash-merge.** Drops the 4 CRYPTO bleeders + 9 poison symbols + resurrection workflow. |
| #460 | `chore/action-required-handoff-2026-04-27` | OPEN, handoff doc | NONE | Close after #461 merges + ACTION_REQUIRED.md is deleted. |
| #459 | `fix/asset-class-deep-cleanup-2026-04-27` | OPEN (CI RED, superseded by #461) | NONE | Close with cross-ref to #461. |
| #458 | `docs/asset-class-consolidated-action-items-2026-04-27` | OPEN, docs only | LOW | Review & merge or close (overlaps with our hedge-fund roadmap). |
| #457 | `fix/unknown-asset-class-normalization-2026-04-27` | OPEN | NONE | Independent — review on its merits. |
| #455–#456 | various asset-class doc branches | OPEN | LOW | Probably close (superseded by canonical recompute). |
| **(pending)** | (Copilot Cloud's branch) | NOT YET PUSHED | **HIGH** | Will collide with #461's `_POISON_SYMBOLS_BY_CLASS` — see §5 deconfliction. |

## 2. Concrete ships in priority order

Each item lists the ROI rank, the canonical design doc, the conflict surface, and a one-line acceptance criterion.

### P0 #1 — Resolver fix (`alpha_engine/outcome_resolver.py:97 + :384–405`)

- **Why first:** unblocks FOREX (n=794) and COMMODITY (n=622) verdicts. 63–67% of their wins are sub-bp resolver flicker. Every downstream metric built on those WRs is polluted (per Copilot Cloud's Performance Charter answer Q1).
- **Design:** `reports/action_B_resolver_2026_04_27.md` — close at TP/SL hit using yfinance OHLC replay (mirror crypto path at `alpha_engine/forward_validator.py:1180–1213`), not live spot. Threshold from 0.001% (0.1bp) → 0.05% (5bp) for non-crypto, keep 0.1bp for crypto.
- **Re-resolve plan:** ~1,860 historical picks across 8 source-systems. Stamp `resolver_version: "v2"` + preserve `_legacy_pnl_pct` audit fields.
- **Conflict surface:** none with PR #461 / Copilot Cloud's blocklist work. Different files entirely.
- **Acceptance:** post-fix, FOREX + COMMODITY noise share <30%.
- **T+7d follow-up agent (`trig_01LZS8ZNaHoVRqZMUefwpfmS`)** auto-checks whether this shipped on 2026-05-05.

### P0 #2 — Merge PR #461 (asset-class clean re-extraction)

- **Why second:** retires 4 CRYPTO bleeders (combined drag −137%) + 9-symbol poison gate + machine-readable `_BLOCK_JUSTIFICATIONS` + resurrection workflow. Tests pass (22/22 in feed_hygiene + validator confirms 1,417/3,500 = 40.5% blocked).
- **Caveat:** 2 bot commits (Autonomous Trading + Battle Test) leaked via `git pull --rebase`. **Squash-merge required** to drop them.
- **Conflict surface:** Copilot Cloud is in flight with parallel `BLOCKED_SYMBOLS`/`BLOCKED_SYMBOL_DIRECTIONS` work in `audit_trail/quality_gates.py` (different file). Both can ship; the deconfliction is documentation — see §5.

### P0 #3 — CRYPTO MDD reduction (Goal #1 path to Tier 2)

Per `reports/deep_dive_crypto_mdd_reduction_2026_04_28.md`, ship 3 small PRs in this order. Sharpe/Sortino/Calmar already exceed targets (3.62 / 5.72 / 6.46) — only realized MDD is broken.

- **PR-V (vol-targeting):** new `alpha_engine/vol_target.py` module + wire at `feed_hygiene.is_valid_active_pick:160` (size cap, not hard reject). Backtest-projected MDD: **140% → 9.21%**.
- **PR-R (regime kill-switch):** repurpose `regime_terminal` from peer-emitter to gate. Per memory `feedback_long_source_bias.md` (with the caveat that memory is 22d stale — re-verify alpha_engine SHORT data first).
- **PR-K (Kelly + portfolio cap):** update `config/risk_policy.json` with `class_budget_pct=0.30` for CRYPTO + per-source half-Kelly + flip the observability-only check at `production_scanner.py:5025` to hard reject.
- **Conflict surface:** PR-V is greenfield (no conflicts). PR-K touches `config/risk_policy.json` which Copilot Cloud isn't editing.

### P1 #4 — EQUITY zombie kills + JNJ removal (Goal #1 fastest Tier-1 reach)

- **Why high-priority:** smallest single PR with biggest projected impact on the only investable class. EQUITY PF projects 1.385 → ~1.55 (Tier 1 reach: PF≥1.5 / WR>50 / MDD<20).
- **What:** retire `goldmine_stocks` (n=13, 0% WR, sum −53%), `fast_stocks_competition` (n=6, 0% WR, sum −22%), `Classic Momentum` (n=41, WR 36.6%, sum −15.38%). Block `JNJ` from EQUITY universe (n=23, WR 13%, sum −44.21 — drives ~30% of EQUITY MDD).
- **Conflict surface:** **HIGH with PR #461** (touches same blocklist file) and **HIGH with Copilot Cloud's pending PR**. Recommend bundling EQUITY zombies into PR #461 as a follow-up commit on the same branch, OR waiting until #461 merges then opening a focused EQUITY PR.
- **Status:** the `_BLOCK_JUSTIFICATIONS` machinery already exists in PR #461 — adding EQUITY entries is a 30-line append + 4 lines in `BLOCKED_ASSET_SOURCE_PAIRS`.

### P1 #5 — COMMODITY rescue (Goal #1 path to Tier 3 or replication)

Per `reports/deep_dive_commodity_rescue_2026_04_28.md`, this class is more nuanced than "broken":

- **Carrier identified:** `multi_asset_copytrader.futures_momentum` (n=488, **clean WR 46.9%**, sum +16.15) is a real edge source dragged into negative by 121 broken picks across 5 specific strategies.
- **5 specific bug hypotheses with file:line refs** (e.g., `cta_commodity_momentum_term:655` and `:676` compute identical numbers — combined-rank double-counts momentum).
- **Sequence:** sandbox COMMODITY emissions days 1–30 (waiting on resolver fix), re-resolve days 31–60, deploy 50/50 internal/external days 61–90.
- **External fallback:** DBMF primary (0.85% / 5Y 8.3%), WTMF secondary (0.65% / longer track record), CTA Simplify tertiary.
- **Blocked on:** P0 #1 resolver fix.

### P1 #6 — CI freshness assertion (already shipped warn-only)

- **Status:** `tools/assert_model_freshness.py` + `.github/workflows/ml-staleness-watchdog.yml` shipped 2026-04-28 (commit `632910b06a`). Warn-only mode for now.
- **T+14d follow-up agent (`trig_01Hdd3dx5BRof1iUujLAWaUF`)** evaluates whether to flip to hard-fail on 2026-05-12.

## 3. Scheduled triggers

| Trigger ID | Fires (UTC) | Purpose |
|---|---|---|
| `trig_01PEK3xQJt4eVPUQkuB39SmQ` | 2026-04-28T01:05Z | ACTION_REQUIRED #1 *(already fired by now)* |
| `trig_01T6peTJmcpbXLHbXcW9qmFi` | 2026-04-28T01:10Z | 30-min health check on PRs + dashboard *(already fired by now)* |
| `trig_014VfQ3ZrdYSJ6r5UbNu1bGN` | 2026-04-28T01:25Z | ACTION_REQUIRED #2 |
| `trig_014UBFCnj3bPyraHhqtyRQfv` | 2026-04-28T01:45Z | ACTION_REQUIRED #3 (final, escalates) |
| `trig_01GAkTbLU3sFA9GSmvncvDpB` | 2026-04-28T03:17Z | Peer agent task `8d2baa1e` 2-hour follow-up |
| `trig_01LZS8ZNaHoVRqZMUefwpfmS` | 2026-05-05T01:55Z | **Resolver fix follow-up + clean recompute** |
| `trig_01Hdd3dx5BRof1iUujLAWaUF` | 2026-05-12T01:55Z | Watchdog flip evaluation |

The first 4 short-term triggers may produce redundant "no change" notes (the recovery work they were watching is already done via Cursor's manual recovery + my recovery subagent → PR #461). They're harmless — let them fire.

## 4. Decision points for the user

These are the items where my recommendation could be wrong and you should weigh in:

1. **Squash-merge PR #461 vs. force-push to drop bot commits.** I recommend squash-merge. AGENTS.md says no force-push without explicit authorization, and squash-merge achieves the same hygiene goal with no risk. Confirm or override.
2. **Bundle EQUITY zombies into PR #461 (Option A) vs. open a separate PR (Option B).** Option A ships faster but expands #461's scope. Option B is cleaner but waits for #461 to merge first. Recommend B (cleaner audit trail).
3. **Vol-targeting deployment risk.** PR-V projects MDD 140% → 9.21% on backtest, but this is paper math. Pre-deploy in shadow mode (compute target_size but don't enforce) for 7 days first? Or wire it directly with hard reject at `feed_hygiene.is_valid_active_pick:160`? Recommend shadow-then-enforce.
4. **CRYPTO SHORT-disable scope.** Workstream C said source-scoped (only `alpha_engine` SHORT triple); my peer review of #461 said the same. PR #461 currently has a blanket SHORT-disable. Recommend follow-up commit narrowing scope to source-scoped — luxalgo_filters SHORT (n=88, 50% WR, +29.39) and copy_trader_highscore SHORT (n=10, 70% WR, +20.47) are clear winners that the blanket would kill.
5. **Copilot Cloud's parallel work.** Ask them to rebase onto PR #461's `_POISON_SYMBOLS_BY_CLASS` instead of shipping parallel `BLOCKED_SYMBOLS`/`BLOCKED_SYMBOL_DIRECTIONS` in `quality_gates.py`. Two parallel mechanisms will diverge.

## 5. Deconfliction matrix (parallel-agent work)

| Mechanism | Owner | File | Status | Recommendation |
|---|---|---|---|---|
| `_POISON_SYMBOLS_BY_CLASS` + `_BLOCK_JUSTIFICATIONS` + resurrection workflow | PR #461 (opencode session) | `alpha_engine/strategy_blocklist.py` | OPEN, tests pass | **Canonical** — merge first |
| `BLOCKED_SYMBOLS` + `BLOCKED_SOURCE_SYSTEMS` + `BLOCKED_SYMBOL_DIRECTIONS` | Copilot Cloud Agent (in flight) | `audit_trail/quality_gates.py` | NOT YET PUSHED | Rebase onto #461 + delete the parallel sets, OR ship as inferior fallback gate (defense-in-depth) |
| MAJOR GOAL banner | this session | `audit_dashboard/template.html` | merged | Independent — propagates next cron cycle |
| ML staleness watchdog | this session | `tools/assert_model_freshness.py` + workflow | merged warn-only | Independent — flip to hard-fail at T+14d |
| Resolver fix | unowned | `alpha_engine/outcome_resolver.py` | NOT STARTED | P0 #1 — needs an owner |

## 6. Source-of-truth precedence (per Cursor's request)

When two docs conflict on a number or recommendation, defer in this order:

1. **This file** (`updates/2026-04-28-goal-1-next-ships-synthesis.md`) — most recent consolidation
2. **PR #461 description + tests** — actual code state
3. **`reports/deep_dive_*_2026_04_28.md`** — rescue plans with file:line evidence
4. **`reports/hedge_fund_performance_review_*_2026_04_27.md`** — per-class roadmap
5. **`reports/asset_class_independent_recompute_2026_04_27.md`** (mercury-2 owned) — canonical numbers
6. **`reports/canonical_recompute_corrections_2026_04_28.md`** — corrects mercury-2's lookup-key bug
7. **Memory entries in `~/.claude/projects/.../memory/`** — durable context for future sessions

The MAJOR GOAL banner on `/audit` is the canonical 1-screen summary.

## 7. What this doc does NOT cover

- Goal #2 (sports betting) — see `updates/2026-04-26-sports-next-steps.md` and the sports-specific reports
- Goal #3 (events listing) — see Apr 23/25/27 events docs in `updates/`
- Anything pre-Apr 27 — see Claude Opus 4.6 Thinking's 7-day review at `updates/2026-04-27-7day-code-review-analysis.md`

If you're a future agent reading this and you can't tell whether your work is on Goal #1, #2, or #3 — pause, name the goal, then proceed. Per CLAUDE.md daily-focus rule: a goal-mismatched PR is rejected unless it's a P0 fix that protects production.
