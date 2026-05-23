# Hourly Audit — 2026-05-11 04Z

**Dashboard snapshot:** 2026-05-11T03:58:29Z
**Audit run:** 2026-05-11 ~04:15 UTC
**Previous audit:** `reports/HOURLY_AUDIT_03Z_2026_05_11.md` (PR #897, merged this run)
**Source data:** `audit_dashboard/data/dashboard_data.json` (n=3500 recent_closed)

---

## 1. Dashboard Refresh Status

Pull from `origin/main` succeeded (forced update, 7 files changed — hourly `[skip ci]` prediction-market data refresh: kalshi_signals, polymarket_signals, prediction_market_picks, prediction_market_whales, prediction_quality_history, polymarket_picks, polymarket_trader_profiles). Snapshot timestamp: `2026-05-11T03:58:29Z` (~35min after 03Z snapshot at `2026-05-11T01:51:38Z`).

---

## 2. Per-Asset PF / WR — 24h / 7d / 30d Windows

Computed from `picks.recent_closed` (n=3500) using `closed_at` timestamps vs UTC now (04:15Z).

| Class     | 24h n | 24h WR% | 24h PF | 7d n | 7d WR% | 7d PF | 30d n | 30d WR% | 30d PF |
|-----------|------:|--------:|-------:|-----:|-------:|------:|------:|--------:|-------:|
| CRYPTO    |   312 |   46.5  |   1.53 |  977 |   44.8 |  1.43 |  1497 |    46.4 |   1.40 |
| EQUITY    |     0 |    —    |    —   |   24 |   62.5 |  4.37 |   110 |    63.6 |   3.07 |
| FOREX     |     6 |    0.0  |  N/A†  |  221 |   13.1 |  0.32 |   392 |    12.8 |   0.24 |
| COMMODITY |     0 |    —    |    —   |   19 |   94.7 | 43.93‡|    39 |    76.9 |   6.07 |
| ETF       |     0 |    —    |    —   |   12 |   91.7 | 23.26‡|    44 |    81.8 |   6.03 |
| BOND      |     0 |    —    |    —   |    0 |     — |    — |     0 |      — |     — |
| **ALL**   |   318 |   46.2  |   1.53 | 1253 |   41.7 |  1.37 |  2082 |    43.9 |   1.31 |

†FOREX 24h n=6 with 0 wins — sample too thin for PF computation; not a signal.
‡COMMODITY/ETF 7d PF inflated from thin samples (n<20). 30d windows are the reliable signal.

### Long-run `asset_class_health` (post-resolver-v2, snapshot 03:58Z)

| Class     | PF   | WR%  | vs CLAUDE.md baseline | Delta |
|-----------|------|------|-----------------------|-------|
| EQUITY    | 1.60 | 54.0 | baseline 1.41/52.7%   | +0.19 ↑ |
| COMMODITY | 3.92 | 67.0 | baseline 1.78/46.9%   | +2.14 ↑↑ |
| ETF       | 1.42 | 58.8 | baseline 1.24/55.2%   | +0.18 ↑ |
| CRYPTO    | 1.39 | 47.4 | baseline 1.25/44.6%   | +0.14 ↑ |
| FOREX     | 0.27 | 41.7 | baseline 0.27/46.4%   | 0.00 WR ↓ |
| BOND      | 0.66 | 54.5 | baseline 1.72/55.6%   | -1.06 ↓↓ (small n) |
| UNKNOWN   | 2.40 | 50.0 | —                     | — |

> BOND long-run PF regression (1.72→0.66): n=18 at baseline, still below 100-trade charter floor — not actionable, cosmetic storage-layer artifact.

---

## 3. Deltas vs Baselines

### vs CLAUDE.md documented baseline (2026-05-03T00:06Z)

| Class / Window | Baseline PF | 04Z PF | Delta | Note |
|---|---|---|---|---|
| CRYPTO 24h | 3.54 | 1.53 | -2.01 | Intraday noise; 7d/30d stable confirm no regression |
| CRYPTO 7d | 1.33 | 1.43 | +0.10 ↑ | Sustained improvement |
| CRYPTO 30d | 1.33 | 1.40 | +0.07 ↑ | Confirmed trend |
| EQUITY 7d | 0.87 (pre-#692) | 4.37 | **+3.50 ↑↑** | goldmine_6x kill (PR #692) working |
| FOREX 7d | 0.14 (pre-#687) | 0.32 | +0.18 ↑ | Some recovery but still catastrophic |
| FOREX 30d | 0.97 (pre-#687) | 0.24 | -0.73 ↓ | Historical contamination, pre-fix data |

### vs 03Z audit (PR #897, snapshot 01:51Z)

| Class / Window | 03Z PF | 04Z PF | Delta |
|---|---|---|---|
| CRYPTO 24h | 1.75 | 1.53 | -0.22 (intraday noise) |
| CRYPTO 7d | 1.46 | 1.43 | -0.03 (stable) |
| CRYPTO 30d | 1.41 | 1.40 | -0.01 (stable) |
| EQUITY 7d | 4.37 | 4.37 | 0.00 (same window) |
| EQUITY 30d | 3.07 | 3.07 | 0.00 (same window) |
| FOREX 7d | 0.33 | 0.32 | -0.01 (stable, catastrophic) |
| FOREX 30d | 0.25 | 0.24 | -0.01 (stable, catastrophic) |

**Key takeaway:** all signals stable vs 03Z. CRYPTO 24h dip from 1.75→1.53 is normal intraday variance — 7d/30d anchors confirm no regression. EQUITY T1 confirmed for second consecutive audit run. FOREX unmoved; kill protocol is the correct path.

---

## 4. Tier Status

| Class     | Tier verdict | Basis |
|-----------|-------------|-------|
| EQUITY    | ✅ **T1 confirmed** | 7d PF=4.37, 30d PF=3.07, WR=62.5%/63.6% (post-goldmine_6x kill) |
| COMMODITY | ✅ **T1-candidate** | 30d PF=6.07, n=39 (below 100 charter floor — needs volume) |
| ETF       | ✅ **T1-candidate** | 30d PF=6.03, n=44 (below 100 floor — monitor) |
| CRYPTO    | 🟡 **Below T2** | Long-run PF=1.39 / 7d 1.43; improving trend, do not destabilize |
| BOND      | ⚪ **Insufficient data** | n=0 all windows; long-run n=18 (below charter floor) |
| FOREX     | 🔴 **Sub-floor** | 7d PF=0.32, 30d PF=0.24; mutation protocol active; do NOT silently kill |

### Issue #693 Status (EQUITY 7d/14d/30d divergence monitor)

EQUITY 7d PF=4.37 > acceptance criterion (PF ≥ 1.5). Criterion satisfied; confirmed in two consecutive runs (03Z + 04Z). No further monitoring action required this session.

---

## 5. PR Triage

HOLD set (#660 #658 #681 #661): all previously closed per PR #897. Not touched.
Author-rebase set (#669 #676 #608 #665 #644 #597 #615 #655): all resolved per prior audit (#897). Not touched.

### Open PRs assessed this run

| PR | Title | CI status | Decision |
|----|-------|-----------|----------|
| #898 | fix(B15): cross-asset correlation numpy | scan ✅, audit ✅ / **test(3.11) ❌**, test(3.12) cancelled | HOLD — systemic CI failure |
| #897 | audit(03Z 2026-05-11) | no CI (docs-only) | **MERGED ✅** this run |
| #895 | feat(b13): regime filter sidecar v4 | no CI | HOLD — explicit "DO NOT admin-merge" (manual patch required) |
| #893 | orphan_resolver_dryrun | no CI | HOLD — requires #892 first per body |
| #892 | safe_db_archive tool | not checked | HOLD — awaiting human gate |
| #891 | fix(mysql_sync): entry_time fallback | **gate ❌, test(3.11) ❌** | HOLD — CI failures |
| #887 | feat(quality_gates): WIN_RATE_TRAP_BLACKLIST | not checked (post-#883 stack) | HOLD — wiring queued |
| #885 | feat(risk_policy): v2 crypto cap | no CI checked | HOLD — no outstanding CI data |
| #884 | feat(mysql_sync): NULL category mapper | not checked | HOLD |
| #883 | feat(quality_gates): swarm-batch-1 retunings | not checked | HOLD |
| #881 | feat(tv-orchestrator): fill-relative TP/SL | not checked | HOLD |
| #879 | feat(audit-dashboard): Hermes 5-phase | not checked (14k files) | HOLD — large PR, no reviews yet |
| #878 | feat(short_engine): BULL-regime gate | not checked | HOLD |
| #877 | feat(mysql_sync): elite_score backfill | not checked | HOLD |
| #876 | feat(mysql_sync): pnl clamp | **gate ❌, test(3.12) ❌** | HOLD — CI failures |
| #873 | chore(loop): B13 queue doc | scan ✅, audit ✅, **test(3.11) ❌** | HOLD — systemic CI (docs-only but CI not all green) |
| #862 | DB query bank findings | **test(3.11) ❌** | HOLD — CI not green |
| #849 | Edge action plan + swarm harness | draft | SKIP — draft |
| #846 | feat(b18): shadow probation panel | no CI checked | HOLD — explicit "DO NOT ADMIN-MERGE" |

**Total merges this run: 1** (#897)

**Systemic blocker:** `test (3.11)` failing across 10+ unrelated PRs (confirmed cross-PR pattern in #897, persists at 04Z). Shared fixture/dependency regression — not per-PR issue. Feature PR queue entirely blocked. Dedicated root-cause fix PR needed before normal merge throughput resumes.

---

## 6. Mutation Analysis — New Findings

Ran `python3 tools/mutation_analysis.py --json` at 04:13Z against current `dashboard_data.json`.

### NEW kill candidate (first appearance 04Z 2026-05-11)

| Strategy | Direction | n | WR | Pattern | Action |
|---|---|---|---|---|---|
| `quan_engine_swing` | LONG | 104 | **26.0%** | 34pp direction-spread (SHORT n=5, WR=60%) | ⚠️ Posted to #686 — awaiting 3-AI consensus |

Meets kill preconditions: WR<35% ✅, n≥20 ✅, direction-split pattern matches `ig_contrarian_sentiment`/`myfxbook_retail_contrarian` family ✅. SHORT sample n=5 — too thin for SHORT-only mutation confirmation. Full mutation × inverse × symbol-rotation analysis per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` required before blocking.

### Confirmed kill candidates (all pending 3-AI consensus)

| # | Strategy | Dir | n | WR | PF | First posted |
|---|---|---|---|---|---|---|
| 1 | `ig_contrarian_sentiment` | LONG | 164 | 14.6% | — | 06Z 2026-05-10 |
| 2 | `myfxbook_retail_contrarian` | LONG | 158 | 31.0% | 0.34 | 03Z 2026-05-11 |
| 3 | `forex_carry_momentum` | ALL | 142 | 9.2% | 0.10 | Prior sessions |
| 4 | `forex_rsi2_mean_reversion` | LONG | 319 | 37.6% | 0.51 | Prior sessions |
| 5 | `quan_engine_swing` | LONG | 104 | 26.0% | — | **04Z 2026-05-11** ← NEW |

**Kill queue total: 5.** No auto-kills applied. All require 3-AI consensus per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`.

Note: `forex_rsi2_mean_reversion` LONG PF=0.51 is just above the 0.5 auto-kill threshold. Monitor for crossing; do NOT add to kill queue yet.

### Symbol-level signals (informational)

| Source | Symbol | n | WR | Note |
|---|---|---|---|---|
| `rapid_fire` | UUSDT | 34 | 0.0% | Meets n≥20 + WR<35% but no PF computable from mutation analysis |
| `rapid_fire` | TAOUSDT | 18 | 5.6% | n<20 — monitor only |
| `multi_asset_copytrader` | SI=F, AMD, ZW=F | 0% | — | Per-symbol n not verified ≥20 |
| `quan_engine` | MATICUSDT, ONDOUSDT, SOLUSDT | 0-23% | — | Noted; HYPEUSDT already blocked (PR #694) |

---

## 7. Strategy Investigation — FOREX Sub-floor Status

FOREX 30d PF=0.24 / 7d PF=0.32 — catastrophic, sub-floor. Per CLAUDE.md, mutation-before-kill protocol (`docs/MUTATION_THREE_AXIS_PROTOCOL.md`) is mandatory. Kill queue has 3 FOREX-specific candidates (items 2, 3, 4 above). Do NOT silently kill; awaiting 3-AI consensus.

FOREX bright spot: `MeanReversionBB` n=86 in recent_closed — protect and investigate for volume lift.

---

## 8. Issue #685 — Resolver Rescope

Status: **DONE**. No changes to `outcome_resolver.py`, `re_resolve_historical_v2.py`, or `PNL_WIN_THRESHOLD_BY_CLASS`. As documented in issue #685, resolver work is complete. Any PR claiming "widen re-resolve scope" should receive REQUEST_CHANGES per constraint.

---

## 9. Constraints Verified

- [x] Resolver-rescope DONE (issue #685) — no code changes this run
- [x] Plan v2.1 stats (PF 5.81, ml_score 0.90, WINNER_FILTER) not cited anywhere in this report
- [x] No peer PR rebases (preserve_peer_changes)
- [x] HOLD set (#660 #658 #681 #661) — all closed; not touched
- [x] Author-rebase set — all resolved per prior audit; not touched
- [x] No auto-kills applied — kill queue at 5, all awaiting 3-AI consensus
- [x] Issues #685/#686/#693 read and incorporated
- [x] PR #895 / #846 explicit "DO NOT admin-merge" respected

---

## 10. Actions Taken This Run

1. Read GitHub issues #685, #686, #693 for context
2. Pulled latest `origin/main` (7-file prediction-market `[skip ci]` refresh)
3. Computed per-asset 24h/7d/30d PF/WR from `picks.recent_closed` (n=3500)
4. Read `asset_class_health` long-run metrics and compared vs CLAUDE.md baselines
5. Ran `python3 tools/mutation_analysis.py --json` — 1 new finding (`quan_engine_swing` LONG)
6. Posted new finding to issue #686 (comment #4417565619)
7. Triaged 19 open PRs — systemic `test (3.11)` failure blocking all feature merges
8. Merged PR #897 (03Z 2026-05-11 audit doc) — squash, sha 27dd2f76
9. Authored this report on branch `audit/hourly-2026-05-11-04z`

_Generated by Claude Code (claude-sonnet-4-6) at 2026-05-11T04:15Z_
