# Hourly Audit — 2026-05-20 11Z

**Generated:** 2026-05-20T11:00Z  
**Dashboard snapshot:** 2026-05-20T04:13:12Z (STALE ~7h — same as 04Z–10Z; cron refresh expected at 12Z)  
**Previous audit:** PR #1261 (10Z 2026-05-20) merged ✅ this hour  
**HOLD set (#660 #658 #681 #661):** absent ✅  
**Author-rebase watch PRs (#669 #676 #608 #665 #644 #597 #615 #655):** absent ✅  

---

## Per-asset windows — 11Z snapshot

> Dashboard still at 04:13Z; window cutoffs shifted +1h vs 10Z so 24h deltas are primarily window-shift artifacts, not real signal. 7d/30d deltas are meaningful.

| Class     | 24h PF | 24h WR | 24h n | 7d PF | 7d WR  | 7d n | 30d PF | 30d n | vs 10Z (7d) |
|-----------|--------|--------|-------|-------|--------|------|--------|-------|-------------|
| CRYPTO    | 0.671  | 35.5%  | 110   | 1.198 | 46.0%  | 991  | 1.332  | 2776  | −0.005 (stable) |
| EQUITY    | 0.075  | 6.2%   | 16    | 0.641 | 28.9%  | 45   | 1.446  | 147   | −0.092 (degrading) |
| FOREX     | 1.278  | 42.9%  | 7     | 1.313 | 35.3%  | 17   | 2.515  | 93    | stable post-#687 ✅ |
| COMMODITY | 0.000  | 0.0%   | 15    | 0.097 | 7.9%   | 38   | 0.962  | 73    | stable (catastrophic) |
| ETF       | 0.000  | 0.0%   | 1     | 1.233 | 31.2%  | 16   | 1.917  | 50    | stable |
| BOND      | 0.000  | 0.0%   | 3     | 0.000 | 0.0%   | 3    | 0.000  | 3     | stable (low-n) |
| FUTURES   | —      | —      | 0     | —     | —      | 0    | 999    | 2     | n/a |

**vs documented baseline (issues #686/#693):**

| Class | Baseline 7d PF | 11Z 7d PF | Delta |
|-------|----------------|-----------|-------|
| CRYPTO | 1.21 (issue #686) | 1.198 | −0.012 |
| EQUITY | 0.87 (issue #693) | 0.641 | −0.229 (stocks_rsi2_pullback drag) |
| FOREX | 0.14 pre-#687 | 1.313 | +1.173 ✅ PR #687 recovery holding |
| COMMODITY | 1.18 (issue #686) | 0.097 | −1.083 🚨 FINDING-22/#28 active |

---

## EQUITY 7d strategy attribution (11Z)

| Strategy | n | WR | PF | Sum PnL% |
|----------|---|----|----|----------|
| `stocks_rsi2_pullback` | 29 | 34.5% | 0.980 | −1.13% |
| `vol-contraction-scout` | 3 | 33.3% | 1.109 | +0.97% |
| `stocks_ema_golden_cross` | 2 | 0.0% | 0.000 | −6.83% |
| `rs-breakout-scout` | 2 | 0.0% | 0.000 | −3.02% |
| `macd-hidden-div-scout` | 2 | 0.0% | 0.000 | −12.04% |
| `price-accel-scout` | 2 | 0.0% | 0.000 | −9.18% |
| `adx-trend-scout` | 2 | 50.0% | 0.343 | −5.23% |

`goldmine_6x_consensus`: 0 entries ✅ (confirmed killed by PR #692).  
`stocks_rsi2_pullback` now n=29 (crossed n=20 floor). Dominant 7d strategy, WR=34.5% just below 35% threshold → **FINDING-30** (see below).

---

## COMMODITY 7d strategy attribution (11Z)

| Strategy | n | WR | PF | Sum PnL% |
|----------|---|----|----|----------|
| `cftc_cot_commercial_signal` | 20 | 5.0% | 0.113 | −65.79% |
| `futures_momentum` | 17 | 11.8% | 0.087 | −52.81% |
| `futures_bb_mean_reversion` | 1 | 0.0% | 0.000 | −6.41% |

---

## Active findings

### FINDING-22 (continuing — awaiting 3-AI consensus)
**`cftc_cot_commercial_signal × COMMODITY`**: n=20, WR=5.0%, PF=0.113, sum=−65.79% (7d).  
All kill criteria met: PF<0.5 ✅, WR<35% ✅, n≥20 ✅ (exactly at floor). Pattern matches existing COMMODITY kills.  
Status: posted to issue #686 at 05Z. 3-AI consensus gate still open. **No code action until consensus confirmed.**

### FINDING-24 (P1 open)
**`quan_engine × HYPEUSDT` gate bypass**: 62+ post-kill picks with `strategy=unknown` bypassing PR #694 block.  
Root cause: `passes_active_gate()` checks `strategy` field but picks have `strategy=unknown, source_system=quan_engine`.  
Fix target: `audit_trail/quality_gates.py:passes_active_gate()` — add `source_system` check in addition to `strategy` field.  
Status: no PR yet. Continues from 05Z.

### FINDING-25 (continuing — all below n=20 floor)
- `quan_engine × XRPUSDT`: n=13, WR=0.0%
- `quan_engine × DOGEUSDT`: n=12, WR=8.3%
- `quan_engine × ETCUSDT`: n=5, WR=0%

None crossed n=20. Monitor at 12Z.

### FINDING-27 (WATCH)
**`crypto_mtf_ema_slope_alignment_v1`**: PF=0.505 — above 0.5 kill floor. No action.

### FINDING-28 (continuing — 3 below n=20 floor)
**`futures_momentum × COMMODITY`**: n=17, WR=11.8%, PF=0.087, sum=−52.81% (7d).  
Still 3 below n=20 floor (same as 10Z). Escalate to kill protocol if n≥20 at 12Z.

### FINDING-29 (continuing — WATCH)
**`strong_consensus (alpha_engine, ml_crypto_pred) × CRYPTO`**: n=112, WR=36.6%, PF=0.839 (7d).  
PF above 0.5 kill floor, WR marginally above 35% threshold. No action. Monitor at 12Z.

### FINDING-30 🆕 (new this hour)
**`stocks_rsi2_pullback` (EQUITY)**: 7d n=29, WR=34.5%, PF=0.980; all-time n=23, WR=30.4%, PF=0.650.

Crossed n=20 floor at n=29. WR=34.5% is just below the 35% monitor threshold. PF=0.980 (above 0.5 kill floor — does NOT meet PF kill criterion). Per issue #693 recommendation: monitor `stocks_rsi2_pullback` when 7d WR stays <40% on n≥20.

**Verdict: WATCH.** Not a kill candidate (PF>0.5). If 7d WR continues below 35% with n≥30 at 12Z, escalate to mutation analysis.

---

## Mutation analysis highlights (11Z)

No new PF<0.5 + n≥20 symbol×strategy pairs untracked:

- `rapid_fire × UUSDT` (n=34, WR=0%): already flagged in `audit_trail/quality_gates.py` ("broken symbol"). Note: comment says "14 trades" but current count is 34 — comment is stale. Already penalized/tracked.
- `cta_replicator × NG=F` (n=24, WR=0%): already in COMMODITY symbol blocked list in `quality_gates.py`.
- `stocks_rsi2_pullback` all-time: n=23, WR=30.4%, PF=0.650 — PF>0.5, WATCH only (see FINDING-30).

Direction-asymmetry candidates (already posted to issue #686 at 07Z 2026-05-17 — not repeating):
- `ig_contrarian_sentiment LONG` (n=197, WR=16.8%)
- `myfxbook_retail_contrarian LONG` (n=123, WR=13.8%)
- `quan_engine_swing LONG` (n=104, WR=26.0%)
- `cta_cross_asset_tsmom LONG` (n=84, WR=29.8%)

All awaiting 3-AI consensus per protocol.

---

## Kill verifications

| Strategy | 7d n | Status |
|----------|------|--------|
| `forex_carry_momentum` | 0 | ✅ DEAD (PR #692) |
| `goldmine_6x_consensus` | 0 | ✅ DEAD (PR #692) |
| `cftc_cot` | 0 | ✅ DEAD (PR #683) |
| `forex_rsi2_mean_reversion` | 0 | ✅ DEAD (PR #692) |
| `quan_engine/HYPEUSDT` | 53 | ⚠️ Gate bypass — FINDING-24 (P1) |

---

## PR actions this hour

| PR | Action | Reason |
|----|--------|--------|
| #1261 | **MERGED** ✅ | CI: 6/6 green; reviews: bot COMMENT only (no REQUEST_CHANGES); HOLD set absent |

No other open PRs found (HOLD set #660/#658/#681/#661 absent; author-rebase watch list absent).

---

## Checklist

- [x] Dashboard snapshot freshness verified (STALE ~7h; 12Z refresh expected)
- [x] PR #1261 (10Z) merged — all CI green, no REQUEST_CHANGES
- [x] HOLD set PRs absent (no #660/#658/#681/#661)
- [x] Author-rebase watch list absent
- [x] FINDING-22 status confirmed (n=20 at floor; awaiting 3-AI consensus, no change)
- [x] FINDING-28 status confirmed (n=17, still below n=20 floor)
- [x] FINDING-29 status confirmed (WATCH, no change)
- [x] FINDING-30 documented (stocks_rsi2_pullback crossed n=20, WATCH)
- [x] Mutation analysis run — no new untracked PF<0.5 + n>=20 pairs
- [x] Kill verifications confirmed (all 4 killed strategies at 0 7d trades)
- [ ] 12Z: re-run with fresh snapshot; check FINDING-28 n>=20; confirm FINDING-22 consensus; watch FINDING-30 WR trend
