# Hourly Audit — 2026-05-21 14Z

**Dashboard snapshot:** `2026-05-21T12:18:29Z` (same as 13Z; 14Z cron not yet refreshed at audit time)
**Audit run at:** 2026-05-21T14:12Z
**Auditor:** Claude Sonnet 4.6 (claude-code)

---

## 1. Dashboard Refresh Status

- Last cron refresh: `2026-05-21T12:18:29Z` — same snapshot as 13Z audit
- 14Z hourly cron had not yet produced a new `dashboard_data.json` at time of audit
- recent_closed n=3500 (cap), asset_class_health reflects resolver-v2 clean data

---

## 2. Per-Asset Metrics (14Z Windows)

| Class | 24h PF | 24h n | 7d PF | 7d WR | 7d n | 30d PF | 30d n | vs 13Z |
|-------|--------|-------|-------|-------|------|--------|-------|--------|
| CRYPTO | 2.908 | 93 | 1.413 | 48.0% | 918 | 1.321 | 2699 | 24h -0.051 (normal drift) |
| EQUITY | 2.321 | 8 | 0.803 | 37.0% | 46 | 1.431 | 151 | identical (no new closes) |
| FOREX | 1.460 | 8 | **1.083** | 35.3% | 17 | 2.576 | 94 | **13th consecutive hr ≥1.0 post-#687** ✅ |
| COMMODITY | 4.016 | 2 | **0.227** | 9.5% | 42 | 1.005 | 77 | **PERSISTENT 14th hr crisis** 🔴 |
| ETF | — | 0 | 1.322 | 27.3% | 11 | 2.121 | 47 | stable ✅ |
| BOND | 0.000 | 1 | 0.000 | 0.0% | 4 | 0.000 | 4 | n too small |
| FUTURES | — | 0 | — | — | 0 | inf | 2 | n too small |

### Deltas vs 13Z baseline

- **CRYPTO 24h**: 2.959 → 2.908 (−0.051), n 90→93 — normal tick-level drift ✅
- **All other windows**: no change (same cron snapshot) — numbers identical to 13Z

---

## 3. COMMODITY 7d Crisis — Strategy Attribution (NEW this hour)

Previous audits identified the crisis (PF=0.227, n=42) but lacked per-strategy breakdown. First full attribution:

| Strategy | PF (7d) | WR (7d) | n (7d) | Status |
|----------|---------|---------|--------|---------|
| `futures_momentum` | 0.087 | 11.8% | 17 | ALREADY BLOCKED (`COMMODITY,futures_momentum` in BLOCKED_ASSET_STRATEGY_PAIRS) — historical trades pre-kill |
| `cftc_cot_commercial_signal` | 0.351 | 8.7% | 23 | **ACTIVE DRAIN** — deduped (PR #683) but NOT hard-killed; n=23 ≥ 20, PF < 0.5 ← **FINDING-48 confirmed primary driver** |
| `futures_bb_mean_reversion` | 0.000 | 0.0% | 2 | n too small |

**Root cause confirmed**: `cftc_cot_commercial_signal` × COMMODITY is the active drain. FINDING-48 from 13Z (cftc_cot dedup ≠ hard-kill) is now confirmed as the cause of the persistent COMMODITY 7d PF=0.227. The strategy has 7d WR=8.7% on n=23, PF=0.351 — well below kill threshold.

**All-time** `cftc_cot_commercial_signal` PF = 1.653 (n=56) — elevated by pre-dedup data. Post-dedup 7d is the real signal.

**Action required**: Needs 2 more AI votes (Kimi/Copilot/Cursor) for 3/3 consensus to add `("COMMODITY", "cftc_cot_commercial_signal")` to `BLOCKED_ASSET_STRATEGY_PAIRS`. 1/3 AI vote logged here.

---

## 4. New Kill Candidates (FINDING-50, FINDING-51)

Both meet criteria: PF < 0.5, n ≥ 20, WR < 35%, NOT currently in BLOCKED_STRATEGY_SYMBOL_PAIRS.

### FINDING-50: `rapid_fire × UUSDT`
- All-time: WR = 0.0%, n = 34, avg PnL = −0.17% → PF ≈ 0 (zero wins)
- Pattern match: existing rapid_fire pair kills already in BLOCKED_STRATEGY_SYMBOL_PAIRS (e.g. `macd_rsi_confluence`, `SOLVUSDT`, `ORCAUSDT`)
- Kill candidate criteria met: PF < 0.5 ✅, n ≥ 20 ✅, WR < 35% ✅, pattern match ✅
- **Status: 1/3 AI vote. Needs Kimi + Copilot/Cursor for consensus. Posted to issue #686.**

### FINDING-51: `cta_replicator × NG=F`
- All-time: WR = 0.0%, n = 24, avg PnL = −0.03% → PF ≈ 0 (zero wins)
- `cta_replicator` has strong performance on USDJPY=X (WR 69.6%, n=115) — symbol-specific failure, not system-wide
- Kill candidate criteria met: PF < 0.5 ✅, n ≥ 20 ✅, WR < 35% ✅
- **Status: 1/3 AI vote. Needs Kimi + Copilot/Cursor for consensus. Posted to issue #686.**

---

## 5. PR Triage

### Merged this hour
- **#1290** (13Z audit — CI 3/3 green, Greptile COMMENTED only, mergeable=clean) ✅

### Current open PRs
| PR | Title | CI | Action |
|----|-------|----|--------|
| #1289 | B10 UEPS KPI sidecar | `test (3.11)` FAIL | **HOLD** |
| #1287 | B10 UEPS KPI Path B | `test (3.11)` FAIL | **HOLD** |
| #1279 | docs AGENTS.md | DRAFT | **HOLD** |

### HOLD set (#660 #658 #681 #661) — Plan v2.1 family
Confirmed absent from open PR list ✅

### Rebase check PRs (#669 #676 #608 #665 #644 #597 #615 #655)
All already merged or closed prior to this session ✅:
- #669 (B2 lane grid): MERGED 2026-05-02 ✅
- #676 (events quality): MERGED 2026-05-03 ✅
- #608 (B26 smoke test): MERGED 2026-05-03 ✅
- #665 (B17 HC after-cost): MERGED 2026-05-02 ✅
- #644 (docs per-asset plan): MERGED 2026-05-03 ✅
- #597 (P0 rapid_fire + USDCHF): MERGED 2026-05-03 ✅
- #615 (scanner blockers): MERGED 2026-05-03 ✅
- #655 (docs roadmap): CLOSED (no merge) — doc-only, superseded

---

## 6. Plan v2.1 Guardrails

No open PRs citing Plan v2.1 stats (PF 5.81, ml_score 0.90, WINNER_FILTER) detected. ✅

---

## 7. Kill Queue Status (cumulative)

| Finding | Pair | PF | WR | n | AI votes | Action |
|---------|------|----|----|---|----------|--------|
| FINDING-41 | COMMODITY × futures_momentum | 0.087 (7d) | 11.8% | 17 | 3/3 ✅ | BLOCKED (PR merged) |
| FINDING-42 | CRYPTO × quan_engine HYPEUSDT | 0.7 (system) | 41.6% | 553 | 3/3 ✅ | BLOCKED (PR #694) |
| FINDING-43 | FOREX × forex_carry_momentum | 0.00 (7d) | 1.8% | 57 | 3/3 ✅ | BLOCKED (PR #692) |
| FINDING-44 | FOREX × goldmine_6x_consensus | 0.00 (7d) | 0% | 6 | 3/3 ✅ | BLOCKED (PR #692) |
| FINDING-45 | FOREX × forex_rsi2_mean_reversion | 0.14 (7d) | 10.9% | 52 | 3/3 ✅ | BLOCKED (PR #692) |
| FINDING-46 | ig_contrarian × LONG | 0.16 | 16.5% | 200 | 1/3 | Pending |
| FINDING-47 | myfxbook_retail × LONG | ~0.3 | 13.7% | 124 | 1/3 | Pending |
| FINDING-48 | COMMODITY × cftc_cot_commercial_signal | 0.351 (7d) | 8.7% | 23 | **1/3** | **Confirmed primary COMMODITY drain** |
| FINDING-49 | COMMODITY × futures_momentum (gap check) | 0.087 | 11.8% | 17 | 1/3 | Already blocked; historical contamination |
| **FINDING-50** | `rapid_fire × UUSDT` | 0.000 | 0.0% | 34 | **1/3 NEW** | Needs Kimi + AI vote |
| **FINDING-51** | `cta_replicator × NG=F` | 0.000 | 0.0% | 24 | **1/3 NEW** | Needs Kimi + AI vote |

Total active kill candidates (1/3 vote): 5 (FINDING-46, 47, 48, 50, 51)

---

## 8. Strategy PF Leaderboard (all-time, n≥20) — for reference

Top performers (PF > 2.0):
- `mega_mutation_macd_rsi_m048`: PF=5.545, WR=72.7%, n=44 ✅
- `rs-breakout-scout`: PF=3.560, WR=71.1%, n=38 ✅
- `ig_contrarian_sentiment`: PF=2.618, WR=63.0%, n=46 (SHORT-only edge; LONG drags)
- `st_fear_greed_contrarian`: PF=2.558, WR=63.7%, n=270 ✅

Sub-floor strategies (PF < 0.6, n≥20):
- `claude_ml_conservative_mut`: PF=0.545, WR=20.0%, n=20 — watch for n growth

---

## 9. Next-Hour Priorities

1. **COMMODITY crisis**: await Kimi/Copilot/Cursor votes on FINDING-48 (`cftc_cot × COMMODITY`)
2. **PRs #1287/#1289**: diagnose `test (3.11)` failure root cause — both B10 UEPS PRs have same CI failure
3. **EQUITY 7d**: monitor stocks_rsi2_pullback WR (currently 40.4% all-time vs 37% 7d)
4. **cron refresh**: next dashboard refresh due ~15:18Z; re-run 24h/7d windows against fresh data

---

Refs: issues #685 #686 #693 | PRs merged this hour: #1290
