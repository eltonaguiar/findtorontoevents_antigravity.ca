# Hourly Audit — 2026-05-09 04Z

**Dashboard snapshot:** 2026-05-09T04:03:20Z
**Audit run:** 2026-05-09 ~05:10 UTC
**Previous audit:** `reports/HOURLY_AUDIT_2026-05-09_03Z.md` (PR #870, merged this run)
**Source data:** `audit_dashboard/data/dashboard_data.json` (n=3500 recent_closed)

---

## 1. Dashboard Refresh Status

Pull from `origin/main` succeeded (forced update, 26 files changed — hourly `[skip ci]` data refresh landed). Snapshot timestamp: `2026-05-09T04:03:20Z` (~1h after 03Z snapshot at `2026-05-09T02:35:49Z`).

---

## 2. Per-Asset PF / WR — 24h / 7d / 30d Windows

Computed from `picks.recent_closed` (n=3500) using `closed_at` timestamps vs UTC now.

| Class     | 24h n | 24h WR% | 24h PF | 7d n | 7d WR% | 7d PF | 30d n | 30d WR% | 30d PF |
|-----------|------:|--------:|-------:|-----:|-------:|------:|------:|--------:|-------:|
| CRYPTO    |   237 |   60.3  |   4.20 |  842 |   47.7 |  1.76 |  1500 |    49.0 |   1.66 |
| EQUITY    |     7 |   57.1  |   3.52 |   24 |   62.5 |  4.24 |   127 |    63.8 |   3.22 |
| FOREX     |    20 |   10.0  |   0.13 |  232 |   18.1 |  0.33 |  1060 |    38.6 |   0.27 |
| COMMODITY |     6 |  100.0  |    inf |   39 |   92.3 | 43.27 |   149 |    57.7 |   4.89 |
| ETF       |     3 |  100.0  |    inf |   13 |   92.3 | 25.25 |    45 |    82.2 |   6.16 |
| BOND      |     0 |     —   |     — |    0 |     — |    — |     0 |      — |     — |
| **ALL**   |   273 |   57.9  |   4.06 | 1150 |   44.1 |  1.81 |  2885 |    46.8 |   1.74 |

> COMMODITY/ETF `inf` PF in 24h/7d windows = zero losses in period (thin samples, n<40). Not anomalous; 30d windows normalise to 4.89 and 6.16 respectively.

### Long-run `asset_class_health` (post-resolver-v2, for reference)

| Class     | PF   | WR%  |
|-----------|------|------|
| CRYPTO    | 1.41 | 48.4 |
| EQUITY    | 1.57 | 53.7 |
| COMMODITY | 3.97 | 67.2 |
| ETF       | 1.44 | 59.2 |
| FOREX     | 0.27 | 41.7 |
| BOND      | 0.66 | 54.5 |

---

## 3. Deltas vs 03Z Baseline (PR #870)

| Class / Window | 03Z PF | 04Z PF | Delta | n (04Z) | Note |
|---|---|---|---|---|---|
| CRYPTO 24h | 4.20 | 4.20 | 0.00 | 237 | Stable — strongest 24h in baseline series |
| CRYPTO 7d | 1.78 | 1.76 | -0.02 | 842 | Stable, marginal rounding |
| EQUITY 7d | 4.21 | 4.24 | +0.03 | 24 | 9th consecutive T1 run confirmed |
| EQUITY 30d | 3.22 | 3.22 | 0.00 | 127 | Locked at T1 |
| FOREX 7d | 0.33 | 0.33 | 0.00 | 232→232 | TEMP-UNBLOCK regression persists |
| FOREX 30d | — | 0.27 | — | 1060 | Long-run contamination from pre-#687 trades; 30d PF ≡ asset_class_health |

**Key takeaway:** all signals stable vs 03Z. No new regressions introduced in this window. FOREX 30d n=1060 vs FOREX 7d n=232 — confirms the bulk of bad FOREX volume pre-dates the 7d window and is historical contamination, not new bad trades.

---

## 4. Tier Status (post-03Z + 04Z confirmation)

| Class     | Tier verdict | Basis |
|-----------|-------------|-------|
| EQUITY    | ✅ **T1 (9th run)** | 7d PF=4.24, 30d PF=3.22, WR=62.5%/63.8% |
| COMMODITY | ✅ **T1-candidate** | 30d PF=4.89, n=149 (≥100 charter floor held) |
| ETF       | ✅ **T1-candidate** | 30d PF=6.16, n=45 (below 100 floor — monitor) |
| CRYPTO    | 🟡 **Below T2** | 7d PF=1.76 / long-run 1.41; improving trend confirmed |
| BOND      | ⚪ **Insufficient data** | n=0 in all windows |
| FOREX     | 🔴 **Sub-floor** | 7d PF=0.33; TEMP-UNBLOCK regression; mutation protocol active |

Issue #693 (EQUITY 7d/14d/30d divergence monitor): **RESOLVED** — 9 consecutive T1 readings post-#692 goldmine_6x kill. No further monitoring action required.

---

## 5. PR Triage

HOLD set (#660 #658 #681 #661): all closed; not touched.

| PR | Title | CI | Mergeable | Decision |
|----|-------|----|-----------|----------|
| #870 | audit(03Z 2026-05-09) | scan ✅ | MERGEABLE | **MERGED** (dc7a9abc) |
| #869 | chore(loop): B13 queue update | scan ✅ | MERGEABLE | **MERGED** (05a4ab74) |
| #868 | feat(b13): regime filter sidecar | scan ✅ | — | HOLD — explicit "DO NOT ADMIN-MERGE" |
| #865 | audit(05Z 2026-05-08) | scan ✅ | unknown (behind main) | HOLD — behind main |
| #862 | DB query bank findings | test(3.11) ❌ | — | HOLD — CI not green |
| #849 | Edge action plan + swarm harness | — | draft | SKIP — draft |
| #846 | feat(b18): shadow probation panel | scan ✅ | — | HOLD — explicit "DO NOT ADMIN-MERGE" |

**Total merges this run: 2** (#870, #869)

### Author-rebase PRs (#669 #676 #608 #665 #644 #597 #615 #655)

Not present in open PR list — all previously closed or merged. No action required.

---

## 6. Mutation Analysis — New Finding

Ran `python3 tools/mutation_analysis.py --json` against current `dashboard_data.json`.

### NEW kill candidate (not in 03Z report)

| Strategy | Direction | n | WR | Gate | Action |
|---|---|---|---|---|---|
| `quan_engine_swing` | LONG | 104 | **26.0%** | n≥20 ✅, WR<35% ✅ | ⚠️ 3-AI consensus pending |

`quan_engine_swing` SHORT has n=5 (60.0% WR) — sample too thin for SHORT-only mutation confirmation. Requires full mutation × inverse × symbol-rotation analysis per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`.

Posted to issue #686 comment #4411553437.

### Carry-over kill queue (from 03Z, pending 3-AI consensus)

| Strategy | Direction | n | WR | Status |
|---|---|---|---|---|
| `myfxbook_retail_contrarian` | LONG | 118 | 10.2% | 3-AI pending |
| `ig_contrarian_sentiment` | LONG | 163 | 14.7% | 3-AI pending |
| `forex_carry_momentum` | ALL | 17 (24h) | 0% | 3-AI pending |
| `rapid_fire` × UUSDT | — | 34 | 0% | 3-AI pending |
| `cta_cross_asset_tsmom` | LONG | 69 | 29.0% | 3-AI pending (from 05Z May 8) |

**Kill queue total: 6.** No auto-kills applied.

### Symbol-level signals (informational, not actionable yet)

- `multi_asset_copytrader`: SI=F, AMD, ZW=F at 0% WR — n per symbol not verified ≥20; sandbox flag only
- `quan_engine` × MATICUSDT/ONDOUSDT/SOLUSDT: WR 0-23% — noted in symbol variance section

---

## 7. New Strategy Investigation (FOREX TEMP-UNBLOCK — carry-over)

Root cause confirmed in 03Z: 3 strategies were TEMP-UNBLOCKED on 2026-05-08 in `audit_trail/quality_gates.py`:
- `forex_carry_momentum` (line 1502)
- `myfxbook_retail_contrarian` (line 1545)
- `ig_contrarian_sentiment` (lines 1575/1576)

FOREX 7d regression (PF 1.67→0.33) is attributable to these unblocks. Mitigating: only 5 FOREX active picks open (all `non_crypto_consensus`). Awaiting 3-AI consensus before re-blocking.

---

## 8. Constraints Verified

- [x] Resolver-rescope DONE (issue #685) — no code changes to `outcome_resolver.py` or `re_resolve_historical_v2.py`
- [x] Plan v2.1 stats (PF 5.81, ml_score 0.90, WINNER_FILTER) not cited anywhere in this report
- [x] No peer PR rebases (preserve_peer_changes)
- [x] HOLD set (#660 #658 #681 #661) — all closed; not touched
- [x] No auto-kills applied — kill queue at 6, all awaiting 3-AI consensus
- [x] Issues #685/#686/#693 read and incorporated

---

## 9. Actions Taken This Run

1. Pulled latest `origin/main` (hourly `[skip ci]` data refresh)
2. Computed per-asset 24h/7d/30d PF/WR from `picks.recent_closed` (n=3500)
3. Ran `tools/mutation_analysis.py --json` — 1 new finding
4. Posted new finding to issue #686 (comment #4411553437)
5. Merged PR #870 (03Z audit) — squash, dc7a9abc
6. Merged PR #869 (loop queue update) — squash, 05a4ab74
7. Authored this report on branch `audit/hourly-2026-05-09-04z`

_Generated by Claude Code (claude-sonnet-4-6)_
