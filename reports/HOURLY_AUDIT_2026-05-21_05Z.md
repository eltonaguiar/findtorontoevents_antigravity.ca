# Hourly Audit — 2026-05-21 05Z

**Dashboard snapshot:** 2026-05-21T04:42:51Z (fresh — generated ~19 min before audit)
**Snapshot repo SHA:** `d212dc9551d5d90a222e15ce5af3145b93f36a39`
**Payload lag:** 4871s (~81 min, within normal bounds)

---

## 1. Per-Asset Summary (computed windows)

| Class | 24h n | 24h PF | 7d n | 7d PF | 7d WR | 30d n | 30d PF | 30d WR | vs 04Z baseline |
|-------|-------|--------|------|-------|-------|-------|--------|--------|------------------|
| CRYPTO | 89 | 3.174 | 904 | 1.476 | 48.9% | 2731 | 1.365 | 46.4% | 7d +0.076 / 30d +0.027 ✅ |
| EQUITY | 2 | 1.873 | 40 | 0.754 | 32.5% | 145 | 1.418 | 44.1% | 7d ±0.000 / 30d stable 🟡 |
| FOREX | 7 | 1.331 | 17 | 1.350 | 35.3% | 93 | 2.545 | 48.4% | 7d −0.031 (4th hr ≥1.0) ✅ |
| COMMODITY | 3 | 0.000 | 41 | 0.088 | 7.3% | 76 | 0.879 | 40.8% | unchanged — legacy drag ⚠️ |
| ETF | 0 | — | 11 | 1.322 | 27.3% | 47 | 2.121 | 59.6% | stable ✅ |
| BOND | 1 | 0.000 | 4 | 0.000 | 0.0% | 4 | 0.000 | 0.0% | insufficient data |
| FUTURES | 0 | — | 0 | — | — | 2 | 999.0 | 100.0% | insufficient data |

**Baseline references:** CRYPTO 24h 3.54 / 7d 1.33 / 30d 1.33 (issue #686); EQUITY 7d 0.87 / 30d 1.41-2.18 (issue #693); FOREX 7d 0.14 pre-#687 (issue #686).

---

## 2. Strategy Attribution — New Findings

### CRYPTO 7d top strategies (positive signals)
| Strategy | n | WR | PF | sum PnL% |
|---|---|---|---|---|
| `st_fear_greed_contrarian` | 261 | 64.0% | 2.627 | +149.62% |
| `super consensus` | 12 | 75.0% | 7.375 | +36.84% |
| `claude_ml_moderate_mut` | 41 | 51.2% | 1.779 | +24.37% |
| `luxalgo_confluence` | 144 | 42.4% | 1.059 | +10.46% |
| `keltner_compression_expansion_sol_v1` | 16 | 56.2% | 1.557 | +2.70% |

Drag: `crypto_mtf_ema_slope_alignment_v1` n=29, PF=0.403; `multi_period_rsi_confluence_eth` n=17, PF=0.513.

### COMMODITY 30d breakdown (root cause of sub-1 PF)
| Strategy | n | WR | PF | sum PnL% |
|---|---|---|---|---|
| `cftc_cot_commercial_signal` | 55 | 52.7% | 1.439 | +43.73% |
| `futures_momentum` | 18 | 11.1% | 0.086 | −53.31% |
| `futures_bb_mean_reversion` | 3 | 0.0% | 0.000 | −10.90% |

`futures_momentum` is responsible for the entire 30d COMMODITY deficit. `cftc_cot_commercial_signal` is healthy in 30d but dragging in 7d (WR=4.5%, n=22) — confirmed legacy pre-block picks closing out (FINDING-35, verified).

### EQUITY 30d: bright spots + drags
Bright: `donchian-stock-breakout` (n=8, PF=5.23), `gap-and-go-stocks` (n=5, PF=7.9), `rs-breakout-scout` (n=11, PF=3.32), `mtf-align-scout` (n=8, PF=4.56).
Drag: `macd-hidden-div-scout` (n=10, WR=30.0%, PF=0.276), `adx-trend-scout` (n=6, PF=0.462), `price-accel-scout` (n=7, PF=0.410), `stocks_rsi2_pullback` (n=47, PF=0.973).

---

## 3. PR Triage

| PR | Status | CI | Reviews | Action |
|----|--------|----|---------|--------|
| #1279 | Open, **DRAFT** | ✅ all green | bot only | **No merge** (draft) |
| #1278 | **Merged this hour** | ✅ | bot COMMENTED | ✅ merged (04Z audit) |
| #1277 | **Merged this hour** | ✅ | bot COMMENTED | ✅ merged (03Z audit) |

**HOLD set (#660 #658 #681 #661):** not present in open PR list ✅
**Author-rebase watch PRs (#669 #676 #608 #665 #644 #597 #615 #655):** not present ✅
**Merges this hour: 2** (#1277, #1278)
**Session total to date: 10** (#684 #674 #673 #664 #683 #687 #692 #694 #1277 #1278)

---

## 4. New Findings (05Z)

| # | Finding | Priority | Action |
|---|---------|----------|--------|
| FINDING-37 | `ig_contrarian_sentiment` LONG: **n=0 in 30d window** (vs SHORT n=46, WR=63.0%). LONG side has completely stopped generating. May be silently blocked or dead signal path. FINDING-33 partially SUPERSEDED: SHORT direction is high-quality (63% WR), the LONG side is the problem. | P2 | Investigate call path for LONG signal generation; post to #686 |
| FINDING-38 | `macd-hidden-div-scout` EQUITY 30d: n=10, WR=30.0%, PF=0.276. Sub-threshold (n<20) but worst-performing scout. Monitor until n≥20. | P3 | Watch; no kill until n≥20 |

### Prior findings status update
| # | Previous finding | 05Z status |
|---|-----------------|------------|
| FINDING-36 | `rapid_fire × UUSDT` n=34, WR=0% (04Z claim) | **UNVERIFIED** — n=0 in 30d window with current snapshot. 04Z agent may have used wrong symbol or stale data. Do not act. |
| FINDING-34 | `cta_replicator × NG=F` n=24, WR=0% (03Z claim) | **UNVERIFIED** — n=0 in 30d window. Same issue. Do not act. |
| FINDING-35 | `cftc_cot_commercial_signal` block verified | **CONFIRMED** — 30d PF=1.439 (healthy), 7d WR=4.5% is legacy closures. Recovery expected ~May 28. |
| FINDING-31 | `futures_momentum` COMMODITY n=18 (pre-approved kill at n≥20) | **ACTIVE** — n=18 unchanged. Still 2 trades from threshold. |
| FINDING-33 | `ig_contrarian_sentiment` LONG/SHORT divergence | **PARTIALLY SUPERSEDED** by FINDING-37: LONG n=0, SHORT n=46 WR=63%. SHORT is fine; investigate LONG absence. |

---

## 5. mutation_analysis.py Candidates

No strategy×asset_class pair meets the formal kill criteria (PF<0.5, n≥20, WR<35%) in the 30d window per latest data **except**:

| Pair | 30d n | 30d WR | 30d PF | Status |
|------|-------|--------|--------|--------|
| COMMODITY × `futures_momentum` | 18 | 11.1% | 0.086 | **n<20** — monitor; pre-approved kill per #685 when n≥20 |

No new pairs cross the formal n≥20 + PF<0.5 + WR<35% threshold. No new postings to #686 required this hour.

---

## 6. Positive Signals

- **CRYPTO across all windows improving:** 24h PF=3.174 / 7d PF=1.476 / 30d PF=1.365 — all three windows ticked up vs 04Z. `st_fear_greed_contrarian` is the anchor (n=261, PF=2.627, WR=64%).
- **FOREX 7d PF=1.350** — 4th consecutive hourly audit with 7d PF ≥1.0 (baseline was 0.14 pre-PR #687/#692). Recovery is stable, not a fluke.
- **`goldmine_6x_consensus` + `forex_carry_momentum`** absent from all windows — PR #692 effect fully propagated.
- **ETF 30d PF=2.121** — solid, approaching n=50 candidate floor (currently n=47).

---

## 7. Plan v2.1 Guardrails

- HOLD set (#660 #658 #681 #661): **not present** in open PR list ✅
- No open PRs cite PF 5.81 / ml_score 0.90 / WINNER_FILTER ✅
- No resolver-rescope PRs detected (issue #685: DONE) ✅
- #1279 is DRAFT and docs-only — no Plan v2.1 content ✅

---

## 8. asset_class_health (from dashboard)

| Class | Status | n | PF | WR | Circuit Breaker |
|-------|--------|---|----|----|------------------|
| CRYPTO | stable | 1078 | 1.327 | 48.2% | ok (30d WR=46.4%) |
| FOREX | stable | 151 | 1.447 | 55.0% | ok (30d WR=57.7%) |
| EQUITY | candidate | 55 | 0.921 | 36.4% | ok (30d WR=47.8%) |
| COMMODITY | candidate | 58 | 1.238 | 51.7% | no_backtest |
| ETF | insufficient | 2 | 11.995 | 50.0% | ok (30d WR=59.6%) |
| BOND | insufficient | 6 | 0.000 | 0.0% | cold_start |
| FUTURES | thin | 12 | 0.956 | 16.7% | no_backtest |

Note: `asset_class_health` PF values are computed on the sliding recent window used by the dashboard; they differ from the 30d computed values above because of window definition and n-cap differences.

---

Refs: issues #685, #686, #693 | PRs merged: #1277, #1278
