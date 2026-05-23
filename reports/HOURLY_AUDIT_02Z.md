# Hourly Audit — 2026-05-04T02Z

**Dashboard snapshot:** `audit_dashboard/data/dashboard_data.json` @ 2026-05-04T01:33:05Z  
**Audit computed:** 2026-05-04T02:xx:xxZ  
**Session context:** Issues #685 / #686 / #693; post-8-PR session (PRs #684 #674 #673 #664 #683 #687 #692 #694 merged)

---

## 1. Dashboard Refresh Status

Dashboard auto-refresh fired at **2026-05-04T01:33:05Z** (hourly `[skip ci]` cron). Data is current. Pull from `origin/main` was clean (forced-update noted in fetch log).

---

## 2. Per-Asset Windowed Metrics

Computed from `picks.recent_closed` (n=3500 cap). Per-class FLAT threshold applied: FOREX 1bp, COMMODITY/BOND 5bp, all others 10bp.

| Class | Window | n | WR% | PF | Sum PnL% |
|---|---|---|---|---|---|
| **CRYPTO** | 24h | 71 | 35.2% | 0.80 | -10.19% |
| CRYPTO | 7d | 676 | 44.4% | 1.22 | +109.24% |
| CRYPTO | 30d | 1522 | 43.6% | 1.33 | +303.51% |
| **EQUITY** | 24h | 0 | — | — | — |
| EQUITY | 7d | 32 | 50.0% | 1.09 | +4.77% |
| EQUITY | 30d | 122 | 64.8% | 3.31 | +261.95% |
| **FOREX** | 24h | 9 | 50.0% | 1.42 | +1.70% |
| FOREX | 7d | 94 | 35.5% | 0.43 | -16.18% |
| FOREX | 30d | 533 | 50.2% | 0.80 | -6.82% |
| **COMMODITY** | 24h | 0 | — | — | — |
| COMMODITY | 7d | 59 | 38.9% | 1.18 | +9.50% |
| COMMODITY | 30d | 491 | 41.6% | 0.81 | -17.19% |
| **ETF** | 24h | 0 | — | — | — |
| ETF | 7d | 8 | 62.5% | 1.57 | +3.86% |
| ETF | 30d | 36 | 77.8% | 4.06 | +56.60% |
| **BOND** | 7d | 0 | — | — | — |
| BOND | 30d | 0 | — | — | — |

---

## 3. Delta vs Baselines

### CRYPTO
| Window | Baseline (2026-05-02 22:02Z) | Current | Delta |
|---|---|---|---|
| 24h WR | 63.0% | 35.2% | **−27.8pp** ⚠️ |
| 24h PF | 3.36 | 0.80 | **−2.56** ⚠️ |
| 7d WR | 44.8% | 44.4% | −0.4pp (stable) |
| 7d PF | 1.33 | 1.22 | −0.11 (within noise) |
| 30d PF | 1.33 | 1.33 | 0 (stable) |

**Interpretation:** 24h window regression is notable but n=71 is small. The 7d and 30d anchors are stable. CRYPTO regime-change risk is LOW. Do not act on 24h alone. Monitor next 24h snapshot.

### EQUITY ✅ Improving
| Window | Baseline (issue #693 / 00:10Z corrected) | Current | Delta |
|---|---|---|---|
| 7d WR | 41.0% | 50.0% | **+9pp** ✅ |
| 7d PF | 0.87 | 1.09 | **+0.22** ✅ |
| 30d WR | 64.2% | 64.8% | +0.6pp (stable) |
| 30d PF | 3.29 | 3.31 | +0.02 (stable) |

**Interpretation:** PR #692 (goldmine_6x_consensus kill) is showing effect. EQUITY 7d recovered from PF 0.87 → 1.09 and WR 41% → 50%. EQUITY 30d remains **Tier-1** (PF 3.31 / WR 64.8%). Issue #693 hypothesis confirmed — goldmine_6x was the concentrated drag.

### FOREX — Stable at sub-floor
| Window | Corrected baseline (00:10Z) | Current | Delta |
|---|---|---|---|
| 7d WR | 33.7% | 35.5% | +1.8pp (noise) |
| 7d PF | 0.44 | 0.43 | −0.01 (stable) |
| 30d WR | 49.4% | 50.2% | +0.8pp (stable) |
| 30d PF | 0.80 | 0.80 | 0 (stable) |

**Interpretation:** No deterioration since PRs #687 / #692. FOREX 24h n=9 / WR 50% / PF 1.42 — encouraging micro-signal but too small to conclude. Long-run still sub-floor (PF 0.27 asset_class_health). Watch `forex_rsi2_mean_reversion` SHORT-only edge (WR 51.2%, PF 3.47) vs LONG drag (WR 43.7%, PF 0.86).

### COMMODITY — Consistent with 03Z finding
| Window | 03Z baseline | Current | Delta |
|---|---|---|---|
| 7d PF | 1.18 | 1.18 | 0 (identical) |
| 30d PF | 0.81 | 0.81 | 0 (identical) |

COMMODITY 30d sub-floor drag persists. Mutation analysis recommended (see §5).

### ETF ✅ Tier-1 confirmed
30d PF 4.06 / WR 77.8% (n=36). Tier-1. No change.

---

## 4. PR Triage

**Open PRs found:** 1 (#759)  
**HOLD set** (#660 #658 #681 #661): not in open PR list — confirmed merged or closed by prior session.  
**Author rebase set** (#669 #676 #608 #665 #644 #597 #615 #655): none in open PRs.

### PR #759 — fix(sports): admin-auth fallback for sports_picks.php + sports_bets.php

| Check | Result |
|---|---|
| Mergeable state | `unknown` (GitHub computing) |
| CI test(3.11) | ❌ FAILED |
| CI test(3.12) | ❌ CANCELLED (upstream failure) |
| CI smoke | ✅ success |
| CI scan | ✅ success |
| REQUEST_CHANGES by Claude/Kimi/Copilot/Cursor | None (Codex COMMENTED; swarm NITS verdict) |

**Decision: HOLD.** CI test(3.11) failed. Cannot merge. The swarm review verdict is NITS (not REQUEST_CHANGES), and the author's follow-up comment documents the PHP 5.2 closure fix (commit b2eeacc). Once CI is green on a re-push, evaluate for merge.

**Merges this hour: 0**

---

## 5. New Strategy Kills — mutation_analysis.py Output

`python tools/mutation_analysis.py --json` run at 02Z.

### 🔴 NEW KILL CANDIDATE: `quan_engine × SOLUSDT`

| Metric | Value | Threshold | Status |
|---|---|---|---|
| n | 22 | ≥ 20 | ✅ |
| WR | 9.1% | < 35% sustained | ✅ |
| PF | 0.208 | < 0.5 | ✅ |
| Pattern match | `("quan_engine", "HYPEUSDT")` already blocked (PR #694) | same strategy family | ✅ |

`quan_engine_scalp × SOLUSDT` is already in `BLOCKED_STRATEGY_SYMBOL_PAIRS` (line 1434). `quan_engine` (un-suffixed base strategy) × SOLUSDT is NOT blocked. Same symbol, same strategy family, same WR catastrophe. SOLUSDT is listed as worst performer in mutation_analysis section §3: WR 23% by mutation_analysis (9.1% by my direct compute from recent_closed cap).

**Action:** Posted to issue #686 for 3-AI consensus per kill protocol. Do NOT add to `BLOCKED_STRATEGY_SYMBOL_PAIRS` without consensus.

### 🟡 Watch list (no action yet)

| Pattern | n | WR | Note |
|---|---|---|---|
| `quan_engine × MATICUSDT` | 0 (recent_closed) | — | Already blocked via `quan_engine_scalp`; base strategy has 0 recent trades |
| `rapid_fire × UUSDT` | 0 (recent_closed) | — | UUSDT already in BLOCKED_SYMBOLS (line 1086) |
| `COMMODITY × multi_asset_copytrader` bad symbols (SI=F, AMD, ZW=F) | mixed | 0% worst | Per 03Z audit recommendation — needs mutation_analysis COMMODITY filter pass |

### 🟢 No new kills triggered
`ig_contrarian_sentiment` — already in BLOCKED_ASSET_STRATEGY_PAIRS (line 1272).  
`(FOREX, myfxbook_retail_contrarian)` — already blocked (line 1485).  
`(CRYPTO, quan_engine_swing, LONG)` — already blocked (line 1562).

---

## 6. Goal-#1 Status Summary

| Class | 7d PF | 30d PF | Tier | Change vs Baseline |
|---|---|---|---|---|
| EQUITY | 1.09 | 3.31 | 🥇 Tier-1 (30d) | ✅ Improving post-#692 |
| ETF | 1.57 | 4.06 | 🥇 Tier-1 (30d, n=36) | Stable |
| CRYPTO | 1.22 | 1.33 | 🟡 Approaching Tier-2 | 24h dip; 7d/30d stable |
| COMMODITY | 1.18 | 0.81 | 🔴 Sub-floor (30d) | No change |
| FOREX | 0.43 | 0.80 | 🔴 Sub-floor | Stable (no new drag) |
| BOND | — | — | n<100 (charter floor) | — |

---

## 7. Actions Taken

1. Pulled `origin/main` — clean, dashboard data refreshed ✅
2. Computed per-asset 24h/7d/30d metrics ✅
3. Ran `tools/mutation_analysis.py` ✅
4. PR #759 triaged → HOLD (CI failure) ✅
5. New finding posted to issue #686: `quan_engine × SOLUSDT` ✅
6. This report created via GitHub API on `audit/hourly-02z` ✅

---

## 8. Next Hour Priorities

1. **Monitor CRYPTO 24h** — if next snapshot also shows WR <40% / PF <1.0, investigate by source system (rapid_fire / quan_engine volume by hour)
2. **EQUITY 7d watch** — if `stocks_rsi2_pullback` 7d WR stays <40% on n≥20 in next snapshot, initiate mutation analysis per issue #693
3. **quan_engine × SOLUSDT** — await 3-AI consensus on issue #686 comment; if consensus achieved, add to `BLOCKED_STRATEGY_SYMBOL_PAIRS`
4. **COMMODITY deep-dive** — run mutation_analysis with COMMODITY class filter to find which symbols/strategies drive the 30d drag

---

_Generated by Claude Sonnet 4.6 / Claude Code — 2026-05-04T02Z_
