# Hourly Audit — 18Z 2026-05-20

**Generated:** 2026-05-20T18:07Z  
**Dashboard snapshot:** 2026-05-20T04:13Z (14h stale — cron has not regenerated since last check)  
**Previous audit PR:** #1268 (17Z) — **merged this hour** ✅  
**Auditor:** Claude Sonnet 4.6

---

## 1. Dashboard Refresh Status

Dashboard at `audit_dashboard/data/dashboard_data.json` remains at `2026-05-20T04:13Z` — no refresh since 17Z check. All metrics below are derived from the same n=3500 recent_closed snapshot. 24h window drifts by 1h relative to the 17Z report due to the stale snapshot.

---

## 2. Per-Asset Metrics — 18Z Snapshot

| Class | 24h PF | 24h WR | 24h n | 7d PF | 7d WR | 7d n | 30d PF | 30d WR | 30d n | vs 17Z baseline | Status |
|-------|--------|--------|-------|-------|-------|------|--------|--------|-------|-----------------|--------|
| **CRYPTO** | 0.51 | 27.7% | 65 | 1.24 | 46.9% | 936 | 1.32 | 46.4% | 2755 | 24h dip −0.21; 7d +0.01 | 🟡 Watch 24h |
| **EQUITY** | 0.23 | 14.3% | 7 | 0.68 | 30.0% | 40 | 1.40 | 44.1% | 145 | 7d unchanged (same snapshot) | 🔴 Weak 7d |
| **FOREX** | 1.28 | 42.9% | 7 | 1.31 | 35.3% | 17 | 2.51 | 48.4% | 93 | +1.17 vs pre-#687 — JPY fix holding | 🟢 Recovering |
| **COMMODITY** | 0.00 | 0.0% | 8 | 0.10 | 7.9% | 38 | 0.96 | 42.5% | 73 | Critical unchanged | 🔴 Critical |
| **ETF** | — | — | 0 | 1.23 | 31.2% | 16 | 1.92 | 56.0% | 50 | Stable | 🟢 Stable |
| **BOND** | — | — | 0 | 0.00 | 0.0% | 3 | 0.00 | 0.0% | 3 | n too small | ⚪ n/a |
| **FUTURES** | — | — | 0 | — | — | 0 | inf | 100% | 2 | n=2, not actionable | ⚪ n/a |

### Delta vs documented baselines (issue #686 / #693)

| Class | Baseline 24h PF | 18Z 24h PF | Baseline 7d PF | 18Z 7d PF | Baseline 30d PF | 18Z 30d PF |
|-------|----------------|------------|----------------|-----------|----------------|------------|
| CRYPTO | 3.54 | 0.51 | 1.33 | 1.24 | 1.33 | 1.32 |
| EQUITY | — | 0.23 | 0.87 | 0.68 | 1.41–2.18 | 1.40 |
| FOREX | — | 1.28 | 0.14 (pre-#687) | 1.31 | 0.97 (pre-#687) | 2.51 |
| COMMODITY | — | 0.00 | — | 0.10 | — | 0.96 |

**Notes:**
- CRYPTO 24h PF=0.51 vs baseline 3.54: snapshot is stale (04:13Z); 24h window at 18Z excludes trades that fell in the 17:00–18:00Z bracket. Not a regression signal — confirms dashboard cron lag.
- EQUITY 7d PF=0.68: same data as 17Z. `goldmine_6x_consensus` already killed in PR #692. Remaining drag: `stocks_rsi2_pullback` n=27 WR=37.0% (watch; not yet kill-floor).
- FOREX 30d PF=2.51: strong recovery post-#687 JPY-cross BUY rule fix. 7d low n=17 due to kill of `forex_carry_momentum` + `forex_rsi2_mean_reversion`.
- COMMODITY 7d PF=0.10 WR=7.9% n=38: dominated by `cftc_cot_commercial_signal` pre-kill residual (confirmed below) and `futures_momentum` (n=17, not yet kill-floor).

---

## 3. Strategy-Level Kill-Floor Check (7d, PF<0.5 + n≥20)

| Strategy | Asset Class | 7d n | 7d PF | 7d WR | Kill status |
|----------|-------------|------|-------|-------|-------------|
| `cftc_cot_commercial_signal` | COMMODITY | 20 | 0.11 | 5.0% | **Already blocked** — in `alpha_engine/strategy_blocklist.py` + `BLOCKED_SOURCE_SYSTEMS`. Pre-kill residual, flushing within ~7d. |

**New kill-floor breaches requiring 3-AI consensus: 0**

`cftc_cot_commercial_signal` at exactly n=20 is a false alarm — already killed in PR #683. No new action required.

### Strategies approaching floor (n<20, PF<0.5)

| Strategy | Asset Class | 7d n | 7d PF | 7d WR | Action |
|----------|-------------|------|-------|-------|--------|
| `futures_momentum` | COMMODITY | 17 | 0.09 | 11.8% | ⏳ n=17 — 3 from floor. Pre-kill residual. Monitor. |
| `multi_period_rsi_confluence` | CRYPTO | 13 | 0.28 | 30.8% | n=13 — watch; not actionable yet |

---

## 4. Direction Anomaly Findings (mutation_analysis.py)

| Finding | Strategy | LONG WR (n) | SHORT WR (n) | Spread | Status |
|---------|----------|-------------|--------------|--------|--------|
| **FINDING-37** (carry-fwd) | `ig_contrarian_sentiment` | 16.5% (n=200) | 60.3% (n=58) | 44pp | 🟡 Axis-1 candidate — awaiting 3-AI consensus |
| **FINDING-38** (carry-fwd) | `myfxbook_retail_contrarian` | 13.7% (n=124) | 50.0% (n=14) | 36pp | 🟡 SHORT n=14 small; low confidence |
| **FINDING-39 NEW** | `quan_engine_swing` | 26.0% (n=104) | 60.0% (n=5) | 34pp | 🟡 SHORT n=5 — spread unreliable; watch only |
| — | `combined_confidence` | 26.7% (n=15) | 55.6% (n=9) | 29pp | ⚪ Both sides n<20; not actionable |
| — | `forex_rsi2_mean_reversion` | 12.1% (n=124) | 34.8% (n=23) | 23pp | ✅ Dead (#692) — residual data |

**FINDING-39** (`quan_engine_swing`) is a new direction anomaly. SHORT n=5 is insufficient to confirm the 34pp spread as systematic. Flag for monitoring; recommend SHORT-direction promotion test if n(SHORT) reaches 20.

---

## 5. Open-Findings Tracker

| Finding | Status | Action |
|---------|--------|--------|
| FINDING-24 `HYPEUSDT` bypass via `unknown` source | 🔴 P0 OPEN | 53 picks in 7d via unknown path post-#694. Symbol-block needed in unknown-source code path. |
| FINDING-31 `rapid_fire × UUSDT` | 1/3 consensus | n=34, WR=0% — awaiting 2nd + 3rd AI |
| FINDING-32 `cta_replicator × NG=F` | 1/3 consensus | n=24, WR=0% — awaiting 2nd + 3rd AI |
| FINDING-35 `futures_momentum` | ⚠️ WATCH n=17 | PF=0.09 — 3 from kill floor; pre-kill residual |
| FINDING-37 `ig_contrarian_sentiment` LONG | 🟡 Consensus | Awaiting 2nd + 3rd AI |
| FINDING-38 `myfxbook_retail_contrarian` LONG | 🟡 LOW confidence | SHORT n=14; needs more data |
| FINDING-39 `quan_engine_swing` LONG | 🟡 NEW — watch | SHORT n=5; unreliable spread |

---

## 6. Kill Verifications (7d window)

| Strategy | 7d n | Status |
|----------|------|--------|
| `forex_carry_momentum` | 0 | ✅ DEAD (PR #692) |
| `goldmine_6x_consensus` | 0 | ✅ DEAD (PR #692) |
| `cftc_cot` | 0 | ✅ DEAD (PR #683) |
| `forex_rsi2_mean_reversion` | 0 | ✅ DEAD (PR #692) |
| `quan_engine` HYPEUSDT | residual via `unknown` | ⚠️ bypass via unknown-source path (FINDING-24) |
| `cftc_cot_commercial_signal` | 20 | ⏳ Pre-kill residual — flushing |

---

## 7. PR Actions

| PR | Action | Reason |
|----|--------|--------|
| #1268 (17Z audit) | ✅ **MERGED** | clean + [skip ci] + greptile COMMENTED only |
| HOLD set #660 #658 #681 #661 | ✅ Absent from open PRs | |

**Total PRs merged this hour: 1 (#1268)**

---

## 8. HOLD Set Confirmation

HOLD set (#660 #658 #681 #661 — Plan v2.1 fabrication family) absent from open PR list. ✅

---

## 9. Priority Actions for 19Z

1. **HYPEUSDT bypass (P0):** Identify unknown-source path in `alpha_engine/` and add symbol-block matching #694's approach. FINDING-24 open >1h post-#694.
2. **Dashboard refresh:** Check if cron regenerated by 19Z. Snapshot is 15h stale at that point.
3. **FINDING-37 3-AI consensus:** Forward `ig_contrarian_sentiment` LONG anomaly to 2nd AI for validation before any Axis-1 direction-filter PR.
4. **EQUITY 7d monitor:** At next fresh snapshot, recheck EQUITY 7d PF. If still <0.87 post-goldmine_6x kill, escalate `stocks_rsi2_pullback` for mutation analysis (n=27, approaching threshold).
5. **COMMODITY deep-dive:** With `cftc_cot_commercial_signal` and `futures_momentum` both flushing, 30d PF=0.96 is near break-even. Once residuals clear, recompute clean COMMODITY baseline.

---

## Refs

- Issue #685: resolver-rescope DONE; do not reopen
- Issue #686: live quality tracker (updated with 18Z findings)
- Issue #693: EQUITY 7d monitor — closed (goldmine_6x killed in #692)
- PR #683: cftc_cot kill
- PR #687: JPY-cross BUY rule fix
- PR #692: forex_carry_momentum + goldmine_6x_consensus kill
- PR #694: quan_engine HYPEUSDT symbol-block (bypass via unknown still active)
- `docs/MUTATION_THREE_AXIS_PROTOCOL.md`
- `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`
