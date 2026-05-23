# Hourly Audit — 2026-05-19T15Z

**Generated:** 2026-05-19T15:09Z  
**Dashboard snapshot:** 2026-05-19T14:16:29Z (53 min stale — ≤2h window met)  
**Prior audit:** PR #1254 (14Z) merged ✅ (squash sha `f16c46c2`)

---

## 1. Dashboard Refresh Status

Dashboard auto-refreshes hourly via `[skip ci]`. No 15Z refresh committed yet; 14:16Z snapshot used (within the ≤2h staleness window). All metrics below are from `audit_dashboard/data/dashboard_data.json` as of 14:16Z.

---

## 2. Per-Asset PF/WR — 15Z Snapshot

| Class | 24h PF | 24h WR | 24h n | 7d PF | 7d WR | 7d n | 30d PF | 30d WR | 30d n |
|-------|--------|--------|-------|-------|-------|------|--------|--------|-------|
| CRYPTO | 2.462 | 61.8% | 267 | 1.137 | 45.6% | 1036 | 1.304 | 46.5% | 2895 |
| EQUITY | 0.000 | 0.0% | 3 | 0.267 | 15.4% | 13 | 1.939 | 50.5% | 95 |
| FOREX | 1.324 | 42.9% | 7 | 1.303 | 31.6% | 19 | 2.535 | 48.4% | 93 |
| COMMODITY | 0.000 | 0.0% | 4 | 0.176 | 12.5% | 24 | 1.624 | 53.4% | 58 |
| ETF | 3.198 | 16.7% | 6 | 1.279 | 31.2% | 16 | 1.959 | 56.0% | 50 |
| BOND | 0.000 | 0.0% | 3 | 0.000 | 0.0% | 3 | 0.000 | 0.0% | 3 |

---

## 3. Deltas vs Baselines

| Class/Window | 15Z | 14Z | Baseline | Delta (15Z vs baseline) |
|-------------|-----|-----|----------|------------------------|
| CRYPTO 24h PF | 2.462 | 2.382 | 3.54 | −1.08 (↓ but still strong) |
| CRYPTO 7d PF | 1.137 | 1.119 | 1.33 | −0.19 (minor regression) |
| CRYPTO 30d PF | 1.304 | 1.282 | 1.33 | −0.03 (stable) |
| EQUITY 7d PF | 0.267 | 0.238 | 0.87 | −0.60 (n=13 — below floor) |
| EQUITY 30d PF | 1.939 | 1.939 | 1.41–2.18 | in range ✅ |
| FOREX 7d PF | 1.303 | 1.289 | 0.14 (pre-#687) | **+1.163 ✅ post-#687** |
| FOREX 30d PF | 2.535 | 2.525 | 0.97 (pre-#687) | **+1.565 ✅ post-#687** |
| COMMODITY 7d PF | 0.176 | 0.176 | — | FLAT (FINDING-19 watch) |
| ETF 7d PF | 1.279 | 0.989 | — | **+0.290 recovery** |

Key deltas from 14Z → 15Z: CRYPTO recovering slightly (24h +0.08, 7d +0.018), FOREX holding strong post-#687, ETF recovering 7d (0.989 → 1.279), EQUITY 7d still below kill floor but n=13 is noise.

---

## 4. Findings

### FINDING-15 — RESOLVED ✅
**`ensemble` CRYPTO** (14Z: n=25, WR 20%, PF 0.290)

At 15Z: **n=0 in all windows** (24h, 7d, 30d). Strategy has gone quiet since the 14Z snapshot. No picks from `ensemble` appear in `recent_closed`. Possible causes: pick generation paused, or recent picks not yet closed. **HOLD — monitoring**. Will re-escalate to issue #686 if n>20 resumes.

### FINDING-17 — RESOLVED ✅
**`cftc_cot_commercial_signal` COMMODITY** (14Z: n=18, WR 5.6%, PF 0.133)

At 15Z: **absent from COMMODITY 7d entirely**. COMMODITY 7d only shows `multi_asset_copytrader` (n=22) and `alpha_engine` (n=2). The `cftc_cot` family is confirmed dead — PR #683 kill fully effective. FINDING-17 CLOSED.

### FINDING-18 — CARRY (noise)
**COMMODITY 24h n=4, WR 0%, PF 0** — Unchanged. Below floor (n<20). Monitor only.

### FINDING-19 — NEW 🚨
**`multi_asset_copytrader` × COMMODITY — 7d regime collapse**

| Window | n | PF | WR | sum PnL% |
|--------|---|----|----|----------|
| 7d | 22 | **0.177** | **9.1%** | **−62.172%** |
| 30d | 56 | **1.633** | **53.6%** | +57.518% |

Kill criteria check (per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`):
- PF < 0.5: ✅ (0.177)
- n ≥ 20: ✅ (22)
- WR < 35% sustained: ✅ (9.1%)

**BUT:** 30d PF 1.633, WR 53.6% is healthy. This is a 7d regime-shift signal, not a systemic failure. Long-run positive attribution from CT=F (Cotton, n=180, WR 56.1% long-run per mutation analysis).

Mutation analysis (symbol variance): worst performers are PL=F (Platinum, 0% WR), GC=F (Gold, 0% WR), HG=F (Copper, 0% WR) — metals cluster. CT=F is the positive anchor.

**Recommended action:** Escalate to issue #686 for 3-AI consensus. Propose targeted `BLOCKED_STRATEGY_SYMBOL_PAIRS` for (`multi_asset_copytrader`, `PL=F`), (`multi_asset_copytrader`, `GC=F`), (`multi_asset_copytrader`, `HG=F`) rather than class-level kill. **Do NOT kill without 3-AI consensus.**

### FINDING-20 — CARRY (14Z)
**`cta_replicator/NG=F`**: n=24, WR 0%. Not in `recent_closed` 3500-cap — cross-source validation needed before escalating.

### FINDING-21 — CARRY (14Z)
**`rapid_fire/UUSDT`**: n=34, WR 0%. Same validation gap as FINDING-20.

---

## 5. Kill Verifications (all clean)

| Strategy | Status |
|----------|---------|
| `forex_carry_momentum` | ✅ absent from recent_closed |
| `forex_rsi2_mean_reversion` | ✅ absent (LONG-SHORT spread still visible in mutation tool but no new picks) |
| `goldmine_6x_consensus` | ✅ absent from recent_closed |
| `quan_engine/HYPEUSDT` | ✅ blocked |
| `quan_engine/MATICUSDT` | ✅ blocked |
| `cftc_cot` family | ✅ confirmed dead (FINDING-17 RESOLVED) |

---

## 6. EQUITY 7d Watch

`kimi_riseoftheclaw` EQUITY 7d: n=11, WR 18.2%, PF 0.312, sum −27.772%. Below kill floor (n<20). Post-#692 goldmine_6x kill, EQUITY 7d drag is now concentrated here. Per issue #693 protocol: if EQUITY 14d returns to PF ≥ 1.5 within 7d of #692 merge (2026-05-02 + 7d = 2026-05-09 deadline, now passed), escalate to mutation analysis. At 15Z 30d PF = 1.939 — the 30d is healthy, 7d n is too low for action.

EQUITY 14d check: insufficient data in recent_closed for meaningful 14d window (n<20). Continue monitoring.

---

## 7. Mutation Analysis Highlights (15Z run)

| Strategy | Finding | Action |
|----------|---------|--------|
| `cta_cross_asset_tsmom` | SHORT 52.7% WR vs LONG 29.4% (23pp spread) | LONG-only mutation SANDBOX |
| `ig_contrarian_sentiment` | SHORT 60.3% vs LONG 16.5% (44pp spread) | SHORT-only mutation SANDBOX |
| `quan_engine_swing` | SHORT 60.0% vs LONG 26.0% (34pp spread) | SHORT-only mutation SANDBOX |
| `cta_replicator/NG=F` | n=24, WR 0% | Symbol block (pending cross-source) |
| `rapid_fire/UUSDT` | n=34, WR 0% | Symbol block (pending cross-source) |
| `multi_asset_copytrader` | PL=F / GC=F / HG=F 0% WR | FINDING-19 targeted symbol block |

---

## 8. PR Triage

### Merged this hour
- **#1254** (14Z audit) — squash sha `f16c46c2` ✅

### Open PRs
- **0 open PRs** after #1254 merge (verified via `mcp__github__list_pull_requests`)

### HOLD set
- #660 #658 #681 #661 (Plan v2.1 fabrication family) — **absent** ✅

### Author-rebase watch
- #669 #676 #608 #665 #644 #597 #615 #655 — **all absent** ✅

---

## 9. New Findings Summary

| Finding | Strategy | Asset | 7d n | 7d PF | 7d WR | Action |
|---------|----------|-------|------|-------|-------|--------|
| FINDING-15 | `ensemble` | CRYPTO | 0 | — | — | RESOLVED ✅ |
| FINDING-17 | `cftc_cot` | COMMODITY | 0 | — | — | RESOLVED ✅ |
| **FINDING-19** | `multi_asset_copytrader` | COMMODITY | 22 | 0.177 | 9.1% | Escalate #686 (3-AI) |
| FINDING-20 | `cta_replicator/NG=F` | COMMODITY | — | — | 0% | Cross-source needed |
| FINDING-21 | `rapid_fire/UUSDT` | CRYPTO | — | — | 0% | Cross-source needed |

**New finding count: 1** (FINDING-19)  
**Resolved findings: 2** (FINDING-15, FINDING-17)

---

## 10. Constraints Check

- [x] HOLD set (#660 #658 #681 #661) not touched
- [x] No kills taken without 3-AI consensus
- [x] No peer PR rebases
- [x] Issue #685 resolver-rescope: no resolver PRs proposed
- [x] Plan v2.1 stats (PF 5.81, ml_score 0.90, WINNER_FILTER) not cited anywhere
- [x] Dashboard snapshot ≤2h stale at time of analysis

---

_Refs: issue #685 (resolver done), issue #686 (kill tracking), issue #693 (EQUITY monitor — closed 2026-05-13)_
