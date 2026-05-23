# Hourly Audit — 2026-05-21 11Z

**Generated:** 2026-05-21T11:10Z  
**Dashboard snapshot:** `recent_closed` n=3500 (generated 2026-05-21T10:19:20Z — hourly auto-refresh, [skip ci])  
**Note:** Dashboard data is same snapshot as 10Z audit (next auto-refresh expected ~11:20Z); deltas below are computed against the 10Z PR #1285 baseline.

---

## 1. Dashboard Refresh Status

| Field | Value |
|-------|-------|
| `generated_at` | 2026-05-21T10:19:20Z |
| `picks.recent_closed` count | 3500 |
| Auto-refresh mechanism | `[skip ci]` hourly cron |
| Since last audit (10Z) | Same snapshot; no new refresh yet |

---

## 2. Per-Asset Performance (11Z computed windows)

| Class | 24h n | 24h PF | 7d n | 7d PF | 7d WR | 30d n | 30d PF | vs 10Z baseline |
|-------|-------|--------|------|-------|-------|-------|--------|------------------|
| **CRYPTO** | 94 | **3.081** | 909 | **1.482** | 49.1% | 2,698 | 1.370 | 24h +0.129 ↑ / 7d +0.014 ↑ |
| **EQUITY** | 8 | 2.321 | 46 | **0.803** | 37.0% | 152 | 1.457 | flat (same window) |
| **FOREX** | 8 | 1.492 | 17 | **1.097** | 35.3% | 94 | 2.591 | 7d +0.027 ↑ — **10th consecutive hr ≥1.0** ✅ |
| **COMMODITY** | 2 | 0.000 | 41 | **0.088** | 7.3% | 76 | 0.879 | flat — **PERSISTENT 11th hr** 🔴🔴 |
| **ETF** | 0 | — | 11 | 1.322 | 27.3% | 47 | 2.121 | stable ✅ |
| **BOND** | 1 | 0.000 | 4 | 0.000 | 0.0% | 4 | 0.000 | insufficient n, cold start |
| **FUTURES** | 0 | — | 0 | — | — | 2 | 999.0 | n<10, no signal |

### asset_class_health (resolved, from JSON)

| Class | status | n | PF | WR | sizing_allowed |
|-------|--------|---|----|----|----------------|
| CRYPTO | stable | 1133 | 1.266 | 48.4% | **true** |
| FOREX | stable | 153 | 2.778 | 54.9% | **true** |
| COMMODITY | candidate | 58 | 1.238 | 51.7% | false |
| EQUITY | candidate | 56 | 0.703 | 35.7% | false |
| ETF | insufficient | 2 | 11.99 | 50.0% | false |
| BOND | insufficient | 6 | 0.000 | 0.0% | false |
| FUTURES | thin_sample | 12 | 0.956 | 16.7% | false |

---

## 3. Delta Summary vs Documented Baselines

| Class | Baseline | 10Z | 11Z | Trend |
|-------|----------|-----|-----|-------|
| CRYPTO 24h PF | 3.54 (issue #686) | 2.952 | 3.081 | recovering toward baseline |
| CRYPTO 7d PF | 1.33 (issue #686) | 1.468 | 1.482 | above baseline ✅ |
| CRYPTO 30d PF | 1.33 (issue #686) | 1.365 | 1.370 | at baseline |
| EQUITY 7d PF | 0.87 (issue #693) | 0.803 | 0.803 | slightly below #693 baseline |
| EQUITY 30d PF | 1.41–2.18 (issue #693) | 1.431 | 1.457 | in range ✅ |
| FOREX 7d PF | 0.14 (issue #686, pre-#687) | 1.070 | 1.097 | massive improvement post-#687 ✅ |
| FOREX 30d PF | 0.97 (issue #686, pre-#687) | 2.577 | 2.591 | above pre-kill baseline ✅ |
| COMMODITY 7d PF | 1.18 (issue #686) | 0.088 | 0.088 | **deep crisis** 🔴 |

---

## 4. COMMODITY Crisis — Strategy Attribution (7d)

| Strategy | n | WR | PF | Sum PnL% | Status |
|----------|---|----|----|----------|--------|
| `cftc_cot_commercial_signal` | 22 | **4.5%** | 0.099 | −76.40 | FINDING-48: 1/3 AI vote (posted #686) |
| `futures_momentum` | 17 | 11.8% | 0.087 | −52.81 | BLOCKED in `BLOCKED_ASSET_STRATEGY_PAIRS` |
| `futures_bb_mean_reversion` | 2 | 0.0% | 0.000 | −10.46 | n<20, watch only |

**Root cause:** `futures_momentum` is already blocked but still appears in `recent_closed` — these are pre-block residual closes. `cftc_cot_commercial_signal` is actively generating picks (last close 2026-05-21T08:30Z) and is the only remaining unblocked COMMODITY driver.

**FINDING-48 status:** 1/3 AI consensus posted to issue #686. Awaiting 2nd + 3rd AI confirmation before adding `("COMMODITY", "cftc_cot_commercial_signal")` to `BLOCKED_ASSET_STRATEGY_PAIRS` in `audit_trail/quality_gates.py`. Kill criteria met: n≥20, WR<35% (4.5%), PF<0.5 (0.099).

---

## 5. EQUITY 7d Strategy Breakdown

| Strategy | n | WR | PF | Sum PnL% | Note |
|----------|---|----|----|----------|------|
| `stocks_rsi2_pullback` | 29 | 44.8% | 1.287 | +13.47 | **Improved** vs issue #686 (WR 35.7%, n=14) |
| `rs-breakout-scout` | 3 | 0.0% | 0.000 | −5.69 | n<20, watch |
| `vol-contraction-scout` | 3 | 33.3% | 1.109 | +0.97 | n<20 |
| `stocks_ema_golden_cross` | 2 | 0.0% | 0.000 | −6.83 | n<20 |
| `adx-trend-scout` | 2 | 50.0% | 0.343 | −5.23 | n<20 |
| `goldmine_6x_consensus` | 0 | — | — | — | **Killed by PR #692 ✅** |

**Assessment (issue #693 hypothesis check):** Post-PR-#692, `goldmine_6x_consensus` no longer appears in 7d window. `stocks_rsi2_pullback` recovered from WR 35.7% to 44.8% (n=29 vs n=14) — consistent with the #693 hypothesis that goldmine_6x kill would partially restore EQUITY 7d. EQUITY 7d PF still sub-1.0 (0.803) but 30d PF 1.457 remains in Tier-2 candidate range. Monitor criterion from #693: if EQUITY 14d returns to PF≥1.5 within 7 days post-#692, deterioration was concentrated in goldmine_6x — **currently on track**.

---

## 6. FOREX Recovery Track Record

| Hour | 7d PF | Status |
|------|-------|--------|
| Pre-#687 baseline | 0.14 | catastrophic |
| 02Z | 1.0+ | recovery begins |
| 09Z | 1.070 | 8th hr ≥1.0 |
| 10Z | 1.070 | 9th hr ≥1.0 |
| **11Z** | **1.097** | **10th consecutive hr ≥1.0** ✅ |

FOREX `asset_class_health` status: `stable`, n=153, PF=2.778, WR=54.9%, `sizing_allowed=true`. Recovery is persistent and trending. PR #687 (JPY-cross BUY rule fix) + PR #692 (forex_carry_momentum + goldmine_6x kill) are confirmed effective.

---

## 7. PR Triage

### Merged this turn
| PR | Title | Rationale |
|----|-------|----------|
| **#1285** | audit(hourly): 10Z 2026-05-21 | CI 3/3 green; Greptile COMMENTED (not REQUEST_CHANGES); no Claude/Kimi/Copilot/Cursor REQUEST_CHANGES |

### Open PRs
| PR | State | Action |
|----|-------|--------|
| **#1279** | DRAFT | No merge (draft) |

### HOLD set (#660 #658 #681 #661)
Not present in open PR list. ✅

### Author-rebase watch PRs (#669 #676 #608 #665 #644 #597 #615 #655)
All previously merged or closed per 10Z audit. ✅

---

## 8. New Strategy Kill Candidates (mutation_analysis.py)

`python tools/mutation_analysis.py --json` run this turn. New candidates meeting (PF<0.5 + n≥20):

| Finding | Strategy×Class | n | WR | PF | Kill status |
|---------|----------------|---|----|----|-------------|
| FINDING-48 | `cftc_cot_commercial_signal`×COMMODITY | 22 | 4.5% | 0.099 | **1/3 AI vote** — posted to #686 |

No new candidates beyond FINDING-48. Axis-4 (vol-normalization) candidates flagged by tool: `multi_asset_copytrader` (WR 22%, n=1143), `quan_engine` (WR 30.4%, n=5896), `rapid_fire` (WR 29%, n=207) — these require separate mutation/inverse/symbol-rotation analysis before any kill action.

---

## 9. Kill Queue Status (7 items, 1 updated)

| Finding | Strategy×Symbol/Class | n | WR | Votes | Status |
|---------|-----------------------|---|----|----|-------|
| FINDING-34 | `cta_replicator`×NG=F | 24 | 0% | 1/3 | awaiting 2nd+3rd |
| FINDING-36 | `rapid_fire`×UUSDT | 34 | 0% | 1/3 | awaiting 2nd+3rd |
| FINDING-37/46 | `ig_contrarian` LONG | — | — | 1/3 | awaiting 2nd+3rd |
| FINDING-44 | `quan_engine_swing` LONG | — | — | 1/3 | awaiting 2nd+3rd |
| FINDING-45 | `cta_cross_asset_tsmom` LONG | — | — | 1/3 | awaiting 2nd+3rd |
| FINDING-47 | `crypto_mtf` SHORT | — | — | 1/3 | awaiting 2nd+3rd |
| FINDING-48 | `cftc_cot_commercial_signal`×COMMODITY | 22 | 4.5% | **1/3** | **NEW this hour** |

---

## 10. Plan v2.1 Guardrails

- HOLD set (#660 #658 #681 #661): not present ✅
- No open PRs citing PF 5.81 / ml_score 0.90 / `WINNER_FILTER` ✅
- No resolver-rescope PRs detected (issue #685: DONE) ✅

---

## 11. Recommended Actions for Next Agent

1. **COMMODITY FINDING-48:** Cast 2nd AI vote on `cftc_cot_commercial_signal`×COMMODITY. If 3/3 consensus reached, add `("COMMODITY", "cftc_cot_commercial_signal")` to `BLOCKED_ASSET_STRATEGY_PAIRS` via PR.
2. **EQUITY monitor:** At next audit, check if EQUITY 14d PF ≥1.5 — this is the #693 recovery criterion. Current 30d PF 1.457 is promising.
3. **CRYPTO:** 24h PF 3.081 continues recovery. Do not destabilize (issue #686 directive). Watch for vol-normalization opportunities in quan_engine (axis-4 candidate, n=5896).
4. **FOREX:** 10th consecutive hr ≥1.0; no action needed. Re-audit at 14Z if streak breaks.
5. **Dashboard refresh:** Next hourly auto-refresh should land ~11:20Z; pull and re-check COMMODITY numbers.

---

Refs: issues #685, #686, #693 | PRs #687, #692, #694, #1285 (merged) | `audit_dashboard/data/dashboard_data.json` (2026-05-21T10:19Z)
