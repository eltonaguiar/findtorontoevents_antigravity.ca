# Hourly Audit — 03Z 2026-05-11

**Dashboard snapshot:** 2026-05-11T01:51:38Z
**Audit run:** 2026-05-11 ~03:16 UTC
**Previous audit:** PR #896 (06Z 2026-05-10, merged this run)
**Source data:** `audit_dashboard/data/dashboard_data.json` (n=3500 recent_closed)

---

## 1. Dashboard Refresh Status

Pull from `origin/main` succeeded (forced update — 3 files changed: `forward_stats.json`, `incubator/backtest_results/forward_signals.json`, `incubator/forward_test.db`). Dashboard snapshot: `2026-05-11T01:51:38Z`. Payload lag: 2329s (~39min). Last code change: `2026-05-11T01:12:49Z` (SHA `e1b5537d`).

---

## 2. Per-Asset PF / WR — 24h / 7d / 30d Windows

Computed from `picks.recent_closed` (n=3500) using `closed_at` / `exit_time` / `entry_time` timestamps (3401 parseable) vs snapshot time.

| Class     | 24h n | 24h WR% | 24h PF | 7d n | 7d WR% | 7d PF | 30d n | 30d WR% | 30d PF |
|-----------|------:|--------:|-------:|-----:|-------:|------:|------:|--------:|-------:|
| CRYPTO    |   278 |   49.6  |   1.75 |  971 |   45.5 |  1.46 |  1499 |    46.4 |   1.41 |
| EQUITY    |     0 |     —   |     — |   24 |   62.5 |  4.37 |   121 |    62.8 |   3.07 |
| FOREX     |     4 |    0.0  |   0.00 |  229 |   13.5 |  0.33 |   998 |    37.2 |   0.25 |
| COMMODITY |     0 |     —   |     — |   19 |   94.7 | 43.93 |   103 |    54.4 |   6.02 |
| ETF       |     0 |     —   |     — |   12 |   91.7 | 23.26 |    44 |    81.8 |   6.03 |
| BOND      |     0 |     —   |     — |    0 |     — |    — |     0 |      — |     — |

> COMMODITY/ETF inflated 7d PF (43.93 / 23.26) from thin samples (n=19 / n=12) with near-zero losses. 30d windows (n=103 / n=44) are more reliable signal.

### Long-run `asset_class_health` (post-resolver-v2, for reference):

| Class     | PF   | WR%  | n resolved | Status      |
|-----------|------|------|-----------|-------------|
| CRYPTO    | 1.39 | 47.7 | 7,862     | Stable      |
| EQUITY    | 1.60 | 54.0 | 441       | Stable      |
| COMMODITY | 3.92 | 67.0 | 394       | Stable      |
| ETF       | 1.42 | 58.8 | 97        | Candidate   |
| FOREX     | 0.27 | 41.7 | 1,805     | Stressed    |
| BOND      | 0.66 | 54.5 | 11        | Thin sample |

---

## 3. Deltas vs Documented Baseline

| Class / Window | Baseline (issue #686) | 03Z 2026-05-11 | Delta | Note |
|---|---|---|---|---|
| CRYPTO 24h PF | 3.54 | 1.75 | -1.79 | 24h noise; 7d/30d stable |
| CRYPTO 7d PF | 1.33 | 1.46 | +0.13 | Slight improvement |
| CRYPTO 30d PF | 1.33 | 1.41 | +0.08 | Long-run stable |
| EQUITY 7d PF | 0.87 | 4.37 | **+3.50** | PR #692 goldmine_6x kill confirmed effective |
| EQUITY 30d PF | 2.18 | 3.07 | +0.89 | T1 confirmed |
| FOREX 7d PF | 0.14 (pre-#687) | 0.33 | +0.19 | Still sub-floor; FOREX kills (#692) effect visible |
| FOREX 30d PF | 0.97 (pre-#687) | 0.25 | -0.72 | Historical contamination from pre-fix trades |

**Key takeaway:** CRYPTO 24h softness (1.75 vs 3.54 baseline) is expected intraday noise — 7d/30d at 1.46/1.41 are stable. EQUITY is the strongest signal this hour: 4.37 7d PF confirms PR #692 was the correct kill. FOREX improvement from 0.14 → 0.33 is real but far from floor.

---

## 4. Tier Status

| Class     | Tier verdict | Basis |
|-----------|-------------|-------|
| EQUITY    | T1 confirmed | 7d PF=4.37, 30d PF=3.07, WR=62.5%/62.8% |
| COMMODITY | T1-candidate | 30d PF=6.02, n=103 (>=100 charter floor) |
| ETF       | T1-candidate, thin | 30d PF=6.03, n=44 (below 100 floor; monitor to n=100) |
| CRYPTO    | Below T2 | 7d PF=1.46 / long-run 1.39; improving trend |
| BOND      | Insufficient data | n=0 in all recent windows |
| FOREX     | Sub-floor | 7d PF=0.33; mutation protocol active |

Issue #693 (EQUITY 7d/14d/30d divergence monitor): **ACCEPTANCE CRITERION SATISFIED** — EQUITY 7d PF 4.37 >> 1.5 threshold post-#692. Comment posted to issue #693.

---

## 5. FOREX Strategy Attribution (7d, post-#687 + post-#692)

n=229 FOREX 7d picks breakdown:

| Strategy | n | WR | PF | Status |
|----------|---|----|----|--------|
| `forex_carry_momentum` | 75 | 10.7% | 0.17 | Kill candidate (posted #686 prev. hours) |
| `forex_rsi2_mean_reversion` | 48 | 4.2% | 0.04 | Kill candidate (posted #686 prev. hours) |
| `myfxbook_retail_contrarian` | 48 | 6.2% | 0.10 | **NEW kill candidate (posted #686 this hour)** |
| `MeanReversionBB` | 35 | 22.9% | 1.63 | Positive — protect |
| `fx_smart_carry_trade_momentum` | 8 | 50.0% | 1.78 | Positive (n too small) |
| `fx_smart_forex_rsi2_mean_reversion` | 4 | 50.0% | 2.67 | Positive (n too small) |

Notable: `MeanReversionBB` (PF 1.63, n=35) is the only FOREX strategy with meaningful positive edge in the 7d window. Should be preserved and investigated for lift.

---

## 6. Mutation Analysis — New Kill Candidates

From `python tools/mutation_analysis.py --json` at 03Z:

### Direction-split candidates:

| Strategy | LONG n | LONG WR | LONG PF | SHORT n | SHORT WR | SHORT PF | Action |
|----------|--------|---------|---------|---------|---------|---------|--------|
| `ig_contrarian_sentiment` | 164 | 14.6% | — | 46 | 60.9% | — | Kill LONG — awaiting 2 AI sign-offs |
| `myfxbook_retail_contrarian` | 158 | 31.0% | 0.34 | 160 | 54.4% | 0.55 | NEW — Kill LONG — awaiting consensus |
| `quan_engine_swing` | 104 | 26.0% | — | 5 | 60.0% | — | SHORT n=5 too small; monitor |

`myfxbook_retail_contrarian` LONG meets all 3 auto-add criteria: pattern matches directional kills, n=158 >= 20, WR 31% < 35% sustained, PF 0.34 < 0.5. **NOT auto-added to BLOCKED_ASSET_STRATEGY_PAIRS** — awaiting 3-AI consensus per protocol.

### Symbol-variance candidates (for sandbox allowlist testing):
- `rapid_fire`: UUSDT 0.0% WR n=34, TAOUSDT 5.6% WR n=18 — UUSDT meets n>=20 threshold
- `quan_engine`: HYPEUSDT 41.6% WR n=553 (previously symbol-blocked in PR #694; confirm still blocked)

---

## 7. PR Triage

HOLD set (#660 #658 #681 #661): all confirmed closed per previous audit #896.
Author-rebase set (#669 #676 #608 #665 #644 #597 #615 #655): all resolved per #896.

**PRs merged this run:**

| PR | Title | CI | Reason |
|----|-------|----|--------|
| #896 | audit(06Z 2026-05-10): EQUITY T1 stable | scan OK | Docs-only audit, no reviews |
| #890 | reports: verified edge per asset class | scan OK | Reports-only, no reviews |

**PRs held (CI failures — systemic `test (3.11)` blocker):**

| PR | Title | Failing checks |
|----|-------|---------------|
| #876 | fix(mysql_sync): pnl_pct anomaly clamp | gate FAIL, test(3.12) FAIL |
| #877 | feat(mysql_sync): elite_score backfill | gate FAIL, test(3.12) FAIL |
| #878 | feat(short_engine): BULL-regime gate | gate FAIL, test(3.12) FAIL |
| #883 | feat(quality_gates): swarm-batch-1 | test(3.11) FAIL |
| #884 | feat(mysql_sync): infer category | test(3.11) FAIL, gate FAIL |
| #885 | feat(risk_policy): v2 crypto cap | test(3.11) FAIL, gate FAIL |
| #887 | feat(quality_gates): WIN_RATE_TRAP | test(3.11) FAIL |
| #891 | fix(mysql_sync): entry/exit time fallback | gate FAIL, test(3.11) FAIL |
| #893 | feat(safe-ops): orphan_resolver_dryrun | test(3.11) FAIL |
| #873 | chore(loop): B13 PR #872 queue doc | test(3.11) FAIL |
| #862 | DB query bank findings | test(3.11) FAIL |
| #881 | tv-orchestrator fill-relative TP/SL | test(3.11) cancelled, test(3.12) cancelled |

**PRs held (manual gate required before merge):**

| PR | Title | Blocker |
|----|-------|--------|
| #895 | feat(b13): HMM regime filter sidecar | Explicit DO NOT admin-merge; needs quality_gates.py manual patch |
| #846 | feat(b18): Shadow Probation panel | Explicit DO NOT ADMIN-MERGE; awaiting human review |
| #879 | feat(audit-dashboard): Hermes 5-phase | No CI checks ran; 14,447 files — human review needed |
| #892 | feat(db-safety): safe_db_archive | No CI checks ran |
| #849 | Edge action plan + swarm harness | DRAFT |

**Systemic CI blocker:** `test (3.11)` failing across 10+ unrelated PRs — shared fixture/dependency regression. Dedicated root-cause PR recommended before any feature PRs can clear CI.

---

## 8. New Findings Summary

| # | Finding | Severity | Action |
|---|---------|----------|--------|
| 1 | `myfxbook_retail_contrarian` LONG: n=158, WR 31%, PF 0.34 | P1 | Posted to issue #686; awaiting 3-AI consensus for kill |
| 2 | FOREX `MeanReversionBB` only 7d positive strategy (PF 1.63, n=35) | P2 | Protect; investigate for scale-up |
| 3 | EQUITY 7d PF 4.37 — acceptance criterion of issue #693 satisfied | Info | Posted to issue #693; recommend closing |
| 4 | CRYPTO 24h PF 1.75 vs baseline 3.54 — soft but 7d/30d stable | Monitor | No action; 24h noise |
| 5 | Systemic `test (3.11)` CI blocker holds 10+ feature PRs | P1 | Dedicated fix PR recommended |

---

_Generated by Claude Code (claude-sonnet-4-6) — 03Z 2026-05-11_
_Dashboard: `audit_dashboard/data/dashboard_data.json` generated_at 2026-05-11T01:51:38Z_
