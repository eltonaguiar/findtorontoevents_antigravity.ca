# Hourly Audit — 2026-05-21 21Z

**Generated:** 2026-05-21T21:10Z  
**Dashboard snapshot:** `2026-05-21T20:26:56Z` ✅ (cron current; auto-refresh working)  
**Prior audit:** `reports/HOURLY_AUDIT_2026-05-21_20Z.md` (PR #1300, open/CI-green)  
**Session refs:** issues #685 #686 #693

---

## 1. Per-Asset Metrics

### 21Z snapshot vs 20Z baseline and original task baseline

| Class | PF (24h) | WR (24h) | n (24h) | PF (7d) | WR (7d) | n (7d) | PF (30d) | Status |
|-------|----------|----------|---------|---------|---------|--------|----------|--------|
| CRYPTO | 1.968 | 49.7% | 173 | 1.428 | 48.7% | 997 | 1.364 | Stable |
| EQUITY | 1.739 | 57.1% | 7 | 0.744 | 34.9% | 43 | 1.378 | Sub-T2; 7d drag |
| FOREX | 1.473 | 42.9% | 7 | 1.460 | 36.4% | 11 | 2.586 | Recovery holding |
| COMMODITY | 1.933 | 33.3% | 3 | 0.246 | 11.4% | 35 | 0.943 | 🔴 FINDING-59 active |
| ETF | 0.000 | 0.0% | 2 | 0.889 | 8.3% | 12 | 2.255 | Thin n |
| BOND | — | — | 0 | 0.000 | 0.0% | 4 | 0.000 | Thin n |

### Deltas vs task baseline (CRYPTO 24h 3.54 / 7d 1.33 / 30d 1.33; EQUITY 7d 0.87; FOREX 7d 0.14 pre-#687)

| Class | Window | Baseline | Now | Delta | Note |
|-------|--------|----------|-----|-------|------|
| CRYPTO | 24h | 3.54 | 1.968 | −1.572 | Within-session variance; 24h is thin-n noisy |
| CRYPTO | 7d | 1.33 | 1.428 | +0.098 | Slight improvement ✅ |
| CRYPTO | 30d | 1.33 | 1.364 | +0.034 | Marginal improvement ✅ |
| EQUITY | 7d | 0.87 | 0.744 | −0.126 | Post-#692 lag; stocks_rsi2_pullback WR recovering |
| EQUITY | 30d | 2.18 | 1.378 | −0.802 | Monotonic decline per issue #693 |
| FOREX | 7d | 0.14 | 1.460 | +1.32 | **PR #687 JPY-cross fix confirmed working** |
| COMMODITY | 7d | unstated | 0.246 | — | FINDING-59: futures_momentum n=17 (pre-gate) |

### Deltas vs 20Z (PR #1300 baseline)

| Class | 20Z PF(7d) | 21Z PF(7d) | Delta |
|-------|-----------|-----------|-------|
| CRYPTO | 1.442 | 1.428 | −0.014 (noise) |
| EQUITY | 0.805 | 0.744 | −0.061 (new scout strategies dragging) |
| FOREX | 1.543 | 1.460 | −0.083 (thin n; volatile) |
| COMMODITY | 0.246 | 0.246 | 0.000 (unchanged) |

---

## 2. Strategy Attribution Updates

### COMMODITY 7d (n=35, PF=0.246, WR=11.4%)

| Strategy | n | WR | PF | Sum PnL% | Note |
|----------|---|----|----|----------|------|
| `futures_momentum` | 17 | 11.8% | 0.087 | −52.81% | **FINDING-59: n=17, below 20-gate** |
| `cftc_cot_commercial_signal` | 16 | 12.5% | 0.409 | −42.92% | Historical bleed; blocked 2026-05-16 |
| `futures_bb_mean_reversion` | 2 | 0.0% | 0.0 | −10.46% | Thin n |

`futures_momentum` COMMODITY status: n=17, **3 trades from crossing the n=20 kill gate**. No change from 20Z. Still EMERGING. Monitor.

### EQUITY 7d (n=43, PF=0.744, WR=34.9%)

| Strategy | n | WR | PF | Sum PnL% | Note |
|----------|---|----|----|----------|------|
| `stocks_rsi2_pullback` | 29 | 44.8% | 1.396 | +18.71% | **Recovering** (was WR 35.7% in issue #686) |
| `rs-breakout-scout` | 3 | 0.0% | 0.0 | −8.65% | Thin n |
| `vol-contraction-scout` | 3 | 0.0% | 0.0 | −10.18% | Thin n |
| `stocks_ema_golden_cross` | 2 | 0.0% | 0.0 | −6.83% | Thin n |
| `adx-trend-scout` | 2 | 50.0% | 0.161 | −6.68% | Thin n |
| `macd-hidden-div-scout` | 1 | 0.0% | 0.0 | −6.68% | Thin n |

Key observation: `stocks_rsi2_pullback` WR has recovered from 35.7% (issue #686, 7d window) to 44.8% with n=29 — now above the 40% minimum watch threshold and PF=1.396. The EQUITY 7d drag is now entirely in the scout sub-strategies (rs-breakout, vol-contraction, ema-golden-cross) which are collectively n=8 and too thin to kill. **stocks_rsi2_pullback is no longer a kill candidate.**

### FOREX 7d (n=11, PF=1.46, WR=36.4%)

Only 11 trades in 7d — very thin post-#687+#692 kills. Strategy attribution mostly `unknown` (7/11). Recovery confirmed at the class level; individual strategy attribution impossible at this sample size.

---

## 3. NEW FINDINGS

### FINDING-60 — `cta_replicator` × NG=F (WR=0%, n=24, from mutation_analysis.py)

`python tools/mutation_analysis.py --json` reports:
- `cta_replicator` symbol NG=F (Natural Gas Futures): n=24, WR=0%, avg pnl=−0.03%
- PF=0.0 (all losses) — definitionally PF<0.5
- n=24 ≥ 20 gate ✅ | WR=0% < 35% sustained ✅

**Kill criteria check (CLAUDE.md §4):**
- (a) Pattern match: `quan_engine_scalp`×NG-class symbols already blocked; commodity futures with 0% WR pattern matches
- (b) n=24 ≥ 20 ✅
- (c) WR 0% < 35% ✅

**Action required:** Post to issue #686 for 3-AI consensus. Do NOT add to BLOCKED_STRATEGY_SYMBOL_PAIRS without cross-AI confirmation. Proposed pair: `("cta_replicator", "NG=F")`.

### FINDING-61 — `rapid_fire` × UUSDT (WR=0%, n=34, from mutation_analysis.py)

`python tools/mutation_analysis.py --json` reports:
- `rapid_fire` symbol UUSDT: n=34, WR=0%, avg pnl=−0.17%
- PF=0.0 — PF<0.5 ✅ | n=34 ≥ 20 ✅ | WR 0% < 35% ✅

**Kill criteria check:**
- (a) Pattern match: `rapid_fire` × SOLVUSDT and ORCAUSDT already blocked (PR #597). UUSDT 0% WR matches the exact rapid_fire symbol-block pattern
- (b) n=34 ≥ 20 ✅
- (c) WR 0% < 35% ✅

**Action required:** Post to issue #686 for 3-AI consensus. Proposed pair: `("rapid_fire", "UUSDT")`. This matches the highest-confidence kill pattern (existing rapid_fire blocks + 0% WR).

### Additional mutation axis-4 candidates (informational — no action threshold met)

Per `mutation_analysis.py` Axis 4 (vol-normalization candidates):
- `multi_asset_copytrader`: WR=22.0%, n=1148 — sub-40% WR but active symbol EURGBP/GBPUSD performing well; mixed picture
- `rapid_fire`: WR=29.0%, n=207 — worst symbols identified above (FINDING-61)
- `quan_engine`: WR=30.4%, n=5896 — HYPEUSDT already blocked (PR #694); MATICUSDT already in BLOCKED_STRATEGY_SYMBOL_PAIRS

---

## 4. PR Triage

### HOLD set verification
- #660: CLOSED ✅ (absent from open list)
- #658: CLOSED ✅ (absent from open list)
- #681: CLOSED ✅ (absent from open list)
- #661: CLOSED ✅ (absent from open list)

### Author-rebase PRs
All 8 PRs from the task rebase-check list are already merged/closed (verified via GitHub API):
- #669 ✅ merged 2026-05-02 | #676 ✅ merged 2026-05-03 | #608 ✅ merged 2026-05-03 | #665 ✅ merged 2026-05-02
- #644 ✅ merged 2026-05-03 | #597 ✅ merged 2026-05-03 | #615 ✅ merged 2026-05-03 | #655 ✅ closed 2026-05-03

### Current open PRs

| PR | Title | CI | Reviews | Mergeable | Action |
|----|-------|----|---------|-----------| -------|
| #1300 | audit(hourly): 20Z | 3/3 ✅ | greptile COMMENTED (not RC) | `unknown` — computing | PENDING: merge at 22Z if MERGEABLE |
| #1299 | chore(loop): LOOP_COMPLETE | 3/3 ✅ | greptile COMMENTED (not RC) | `unknown` — computing | PENDING: merge at 22Z if MERGEABLE |
| #1287 | feat(b10): UEPS KPI panel | test(3.11) FAILED, test(3.12) CANCELLED | — | BLOCKED | HOLD — CI failure |
| #1279 | docs: AGENTS.md cloud env | 3/3 ✅ | — | DRAFT | HOLD — DRAFT state |

**Merged this cycle:** none (mergeable_state=unknown on candidates; HOLD on DRAFT/CI-fail)

### Plan v2.1 guardrails
No open PRs cite PF 5.81, ml_score 0.90, or WINNER_FILTER. Clean ✅.

---

## 5. Mutation Analysis Summary

Run: `python tools/mutation_analysis.py --json` (2026-05-21T21:10Z)

**New kill candidates (n≥20, WR<35%, PF<0.5):**
| Finding | Strategy | Symbol/Scope | n | WR | PF | Pattern match |
|---------|----------|-------------|---|----|----|---------------|
| FINDING-60 | `cta_replicator` | NG=F | 24 | 0% | 0.0 | commodity futures 0%-WR |
| FINDING-61 | `rapid_fire` | UUSDT | 34 | 0% | 0.0 | rapid_fire symbol block |

**Existing blocks confirmed:**
- `BLOCKED_STRATEGY_SYMBOL_PAIRS`: quan_engine_scalp×MATICUSDT, enhanced_ml_A_xgboost×TRXUSDT, etc. — intact
- `BLOCKED_ASSET_STRATEGY_PAIRS`: forex_carry_momentum, goldmine_6x_consensus, quan_engine×HYPEUSDT — intact (via PRs #687, #692, #694)

---

## 6. Goal #1 Status (CLAUDE.md north star)

| Class | Tier status | 7d trend | Action |
|-------|-------------|----------|--------|
| CRYPTO | Sub-T2 (PF 1.428) | Stable | Monitor; vol-targeting per deep_dive report |
| EQUITY | Sub-T2 (PF 0.744) | Improving stocks_rsi2_pullback (44.8% WR) | Wait post-#692 lag to clear |
| FOREX | T2 candidate (PF 1.46, 30d PF 2.586) | Recovery confirmed | Maintain; MUTATION_THREE_AXIS on remaining pairs |
| COMMODITY | Sub-floor (PF 0.246) | Unchanged | FINDING-59 at n=17; +3 picks from kill gate |
| ETF | Borderline (30d PF 2.255) | Thin n | No action |
| BOND | Sub-floor (PF 0.0) | Thin n=4 | No action (below charter floor) |

Resolver rescope: DONE per issue #685. No resolver code changes needed.

---

Refs: issues #685 #686 #693 | Previous: `reports/HOURLY_AUDIT_2026-05-21_20Z.md` (PR #1300)
