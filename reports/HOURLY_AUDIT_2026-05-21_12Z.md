# Hourly Audit — 2026-05-21 12Z

**Audit time:** 2026-05-21T12:00Z  
**Dashboard snapshot:** `2026-05-21T10:19:20Z` (n=3500 recent_closed; same data as 11Z — next cron refresh ~12:20Z)  
**Session:** Claude Sonnet 4.6 hourly audit

---

## Dashboard Refresh Status

Snapshot unchanged from 11Z (10:19Z). Next auto-refresh expected ~12:20Z. Numbers below are recomputed from the same snapshot; any delta vs 11Z is due to window-boundary drift only (picks aging out of the 24h/7d windows at the trailing edge).

---

## Per-Asset Windows (computed at 12Z)

| Class | 24h n | 24h PF | 7d n | 7d PF | 7d WR | 30d n | 30d PF | 30d WR |
|-------|-------|--------|------|-------|-------|-------|--------|--------|
| CRYPTO | 88 | 3.191 | 908 | 1.482 | 49.1% | 2,694 | 1.373 | 46.7% |
| EQUITY | 8 | 2.321 | 46 | 0.803 | 37.0% | 151 | 1.431 | 45.0% |
| FOREX | 8 | 1.492 | 17 | 1.097 | 35.3% | 94 | 2.591 | 48.9% |
| COMMODITY | 1 | 0.000 | 41 | 0.088 | 7.3% | 76 | 0.879 | 40.8% |
| ETF | 0 | — | 11 | 1.322 | 27.3% | 47 | 2.121 | 59.6% |
| BOND | 1 | 0.000 | 4 | 0.000 | 0.0% | 4 | 0.000 | 0.0% |

### Long-run asset_class_health (resolver-v2, post-kill baseline)

| Class | PF | WR | n | Status |
|-------|-----|-----|---|--------|
| FOREX | 2.778 | 54.9% | 153 | sizing_allowed=true |
| COMMODITY | 1.238 | 51.7% | 58 | 7d crisis (residual tail picks) |
| CRYPTO | 1.266 | 48.4% | 1,133 | T2 candidate |
| ETF | 11.995 | 50.0% | 2 | n too small for sizing |
| EQUITY | 0.703 | 35.7% | 56 | sub-T2 in health view |
| FUTURES | 0.956 | 16.7% | 12 | sub-floor |
| BOND | 0.000 | 0.0% | 6 | sub-floor |

*Note: The 7d COMMODITY PF=0.088 vs health PF=1.238 gap is explained by time-window difference: health view covers the most recent closed batch (post-block), while the 7d rolling window includes 22 pre-block `cftc_cot_commercial_signal` picks still closing out as stop-losses.*

---

## Deltas vs Session Baseline

Baseline per task brief: CRYPTO 24h 3.54 / 7d 1.33 / 30d 1.33; EQUITY 7d 0.87 / 30d 1.41-2.18; FOREX 7d 0.14 / 30d 0.97 (pre-#687).

| Class | Window | Baseline | Current | Delta | Signal |
|-------|--------|----------|---------|-------|--------|
| CRYPTO | 24h | 3.54 | 3.191 | -0.35 | volatile but >3.0 |
| CRYPTO | 7d | 1.33 | 1.482 | +0.15 | improving |
| CRYPTO | 30d | 1.33 | 1.373 | +0.04 | stable |
| EQUITY | 7d | 0.87 | 0.803 | -0.07 | sub-T2; issue #693 monitor |
| EQUITY | 30d | 1.41 | 1.431 | +0.02 | T2 candidate |
| FOREX | 7d | 0.14 | 1.097 | +0.96 | post-#687 recovery sustained |
| FOREX | 30d | 0.97 | 2.591 | +1.62 | T1-candidate territory |
| COMMODITY | 7d | — | 0.088 | — | PERSISTENT CRISIS (12th hr) |
| ETF | 30d | — | 2.121 | — | stable T1 |

---

## PR Triage

### Merged this turn
- **#1286** (11Z audit): CI 3/3 green (scan, Gitleaks, DB-grep); Greptile COMMENTED only (no REQUEST_CHANGES); squash-merged

### Open PRs
- **#1287** (UEPS KPI panel B10 Path B): CI FAILING — `test (3.11)` failed, `test (3.12)` and `ueps-pytest` cancelled. HOLD — do not merge.
- **#1279** (AGENTS.md docs): DRAFT state. HOLD.

### HOLD set verified absent
#660 #658 #681 #661 — not present in open PR list

### Author-rebase watch
#669 #676 #608 #665 #644 #597 #615 #655 — all previously merged or closed

### Plan v2.1 guardrails
- No open PRs citing PF 5.81 / ml_score 0.90
- No resolver-rescope PRs (issue #685: DONE)

---

## Mutation Analysis (12Z run)

### Axis 1 — Direction flip candidates

| Finding | Strategy | Direction | n | WR | Spread | Status |
|---------|----------|-----------|---|----|--------|--------|
| FINDING-46 | `ig_contrarian_sentiment` | LONG | 200 | 16.5% | 44pp vs SHORT 60.3% | 1/3 AI voice |
| FINDING-39 | `myfxbook_retail_contrarian` | LONG | 124 | 13.7% | 36pp vs SHORT 50.0% | 1/3 AI voice |
| FINDING-44 | `quan_engine_swing` | LONG | 104 | 26.0% | 34pp vs SHORT 60.0% | 1/3 AI voice |
| FINDING-45 | `cta_cross_asset_tsmom` | LONG | 85 | 29.4% | 22pp vs SHORT 51.1% | 1/3 AI voice — P3 watch |

Note: `forex_rsi2_mean_reversion` appears in mutation output (LONG n=124, WR=12.1%) but these are historical picks only — strategy confirmed absent from 7d window (killed PR #692).

### Axis 3 — Symbol variance candidates

| Finding | Strategy | Symbol | n | WR | Status |
|---------|----------|--------|---|----|--------|
| FINDING-36 | `rapid_fire` | UUSDT | 34 | 0.0% | 1/3 AI voice |
| FINDING-34 | `cta_replicator` | NG=F | 24 | 0.0% | 1/3 AI voice |
| WATCH | `rapid_fire` | TAOUSDT | 18 | 5.6% | n<20 floor |
| WATCH | `quan_engine` | HYPEUSDT | 553 | 41.6% | PR #694 should have blocked — verify |

### Axis 4 — Vol-normalization watch (not kill candidates)

| Strategy | WR | n | Note |
|----------|----|---|------|
| `quan_engine` | 30.4% | 5,896 | High volume; needs ATR-unit recalibration |
| `rapid_fire` | 29.0% | 207 | Symbol-level blocks more precise |
| `multi_asset_copytrader` | 22.0% | 1,143 | Direction-mix effect |

### New findings vs 11Z
No new PF<0.5 + n>=20 candidates emerged. All kill candidates are continuations of findings already posted to issue #686 (FINDINGs 34, 36, 39, 44, 45, 46, 47, 48).

---

## COMMODITY Crisis Detail (12th consecutive hour)

7d strategy breakdown:
| Strategy | n | WR | PF | Gate status |
|----------|---|----|----|-------------|
| `cftc_cot_commercial_signal` | 22 | 4.5% | 0.099 | UNBLOCKED — FINDING-48 |
| `futures_momentum` | 17 | 11.8% | 0.087 | BLOCKED (historical tail) |
| `futures_bb_mean_reversion` | 2 | 0.0% | 0.000 | n<20 floor |

FINDING-48 kill criteria: n>=20, WR<35%, PF<0.5, pattern matches COT family — all met.
Still 1/3 AI voice (Claude). Needs Kimi/Copilot/Cursor 2nd + 3rd vote before adding `("COMMODITY", "cftc_cot_commercial_signal")` to `BLOCKED_ASSET_STRATEGY_PAIRS`.

Expected self-correction if blocked: futures_momentum tail picks age out ~May 28; cftc_cot_commercial_signal legacy picks would age out within 7d of blocking.

---

## EQUITY 7d Sub-T2 Analysis

7d EQUITY strategy breakdown (post-#692):
| Strategy | n | WR | PF | Note |
|----------|---|----|----|------|
| `stocks_rsi2_pullback` | 29 | 44.8% | 1.287 | Recovering from 35.7% |
| `vol-contraction-scout` | 3 | 33.3% | 1.109 | n<20 |
| `rs-breakout-scout` | 3 | 0.0% | 0.000 | n<20 |
| `stocks_ema_golden_cross` | 2 | 0.0% | 0.000 | n<20 |

7d PF=0.803 driven by small-n scout noise (n<=3 each) pulling composite down; `stocks_rsi2_pullback` (dominant, n=29) is T2-floor (WR 44.8%, PF 1.287). No kill candidates. Issue #693 monitor continues.

---

## Kill Queue Status (all pending 3-AI consensus)

| # | Finding | Proposed action | Votes |
|---|---------|-----------------|-------|
| FINDING-48 | `cftc_cot_commercial_signal` x COMMODITY n=22 WR=4.5% | Add to `BLOCKED_ASSET_STRATEGY_PAIRS` | 1/3 |
| FINDING-46 | `ig_contrarian_sentiment` LONG n=200 WR=16.5% | LONG-direction block | 1/3 |
| FINDING-39 | `myfxbook_retail_contrarian` LONG n=124 WR=13.7% | LONG-direction block | 1/3 |
| FINDING-44 | `quan_engine_swing` LONG n=104 WR=26.0% | SHORT-only sandbox mutation | 1/3 |
| FINDING-47 | `crypto_mtf_ema_slope_alignment_v1` SHORT n=38 WR=31.6% PF=0.497 | SHORT-direction block | 1/3 |
| FINDING-36 | `rapid_fire` x UUSDT n=34 WR=0% | Add to `BLOCKED_STRATEGY_SYMBOL_PAIRS` | 1/3 |
| FINDING-34 | `cta_replicator` x NG=F n=24 WR=0% | Add to `BLOCKED_STRATEGY_SYMBOL_PAIRS` | 1/3 |
| FINDING-45 | `cta_cross_asset_tsmom` LONG n=85 WR=29.4% | P3 watch | 1/3 |

---

## Refs

- Issues: #685 (resolver: DONE), #686 (live quality), #693 (EQUITY monitor, closed)
- Today's merged PRs: #684, #674, #673, #664, #683, #687, #692, #694, #1286
- reports/HOURLY_AUDIT_2026-05-21_11Z.md (predecessor)
- audit_dashboard/data/dashboard_data.json (snapshot 2026-05-21T10:19:20Z)
