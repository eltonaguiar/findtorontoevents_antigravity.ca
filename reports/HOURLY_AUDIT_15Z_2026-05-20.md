# Hourly Audit — 15Z — 2026-05-20

Generated: 2026-05-20T15:11Z | Session: claude-sonnet-4-6

---

## §1 — Dashboard Snapshot Status

| Field | Value |
|-------|-------|
| Snapshot timestamp | **2026-05-20T04:13Z** |
| Age at audit time | ~11h (stale; hourly cron ran once today at 04:13Z, has not re-run) |
| Previous audit snapshot | 2026-05-15T21:00:17Z (117h stale, 14Z) |
| Status | **IMPROVED vs 14Z** — snapshot refreshed since last audit. Cron ran at 04:13Z. Still stale ~11h; operator should verify cron health if 16Z snapshot also remains 04:13Z. |

**Previous audit (14Z):** PR #1265 merged ✅ — squash merge sha `76f1de2a`

---

## §2 — Per-Asset Numbers (15Z, 04:13Z snapshot)

Computed from `audit_dashboard/data/dashboard_data.json` → `picks.recent_closed` (n=3500).

### 24h Window (cutoff 2026-05-19)

| Class | n | WR | PF | Sum PnL% | Delta vs baseline |
|-------|---|----|----|----------|-------------------|
| CRYPTO | 223 | 52.9% | 1.55 | +88.64% | ↓ from 3.54 (spike normalized) |
| EQUITY | 16 | 6.2% | 0.08 | −49.87% | 🔴 CRITICAL — stocks_rsi2_pullback dominant |
| FOREX | 7 | 42.9% | 1.28 | +1.40% | ✅ stable post-#687 |
| COMMODITY | 16 | 0.0% | 0.00 | −69.26% | 🔴 CRITICAL — futures_momentum + cftc_cot_commercial_signal |
| ETF | 1 | 0.0% | 0.00 | −2.00% | n too small |
| BOND | 3 | 0.0% | 0.00 | −1.83% | n too small |

### 7d Window (cutoff 2026-05-13)

| Class | n | WR | PF | Sum PnL% | Delta vs baseline |
|-------|---|----|----|----------|-------------------|
| CRYPTO | 1037 | 46.7% | 1.25 | +215.32% | ↓ −0.08 vs 1.33 — **stable, within noise** |
| EQUITY | 45 | 28.9% | 0.64 | −40.62% | ↓ −0.23 vs 0.87 — **worsened** (stocks_rsi2_pullback drag) |
| FOREX | 18 | 33.3% | 1.27 | +2.05% | ↑ +1.13 vs 0.14 pre-#687 — **JPY-cross fix confirmed** |
| COMMODITY | 38 | 7.9% | 0.10 | −125.01% | 🔴 CRITICAL — dominated by FINDING-22 + FINDING-35 |
| ETF | 16 | 31.2% | 1.23 | +6.31% | stable |
| BOND | 3 | 0.0% | 0.00 | −1.83% | n too small |

### 30d Window (cutoff 2026-04-20)

| Class | n | WR | PF | Sum PnL% | Delta vs baseline |
|-------|---|----|----|----------|-------------------|
| CRYPTO | 2793 | 46.8% | 1.34 | +746.79% | ↑ +0.01 vs 1.33 — **stable** |
| EQUITY | 147 | 44.9% | 1.45 | +108.79% | ↑ +0.04 vs 1.41 — **T2 candidate intact** |
| FOREX | 93 | 48.4% | 2.51 | +29.77% | ↑ vs 0.97 pre-#687 — **strong recovery** |
| COMMODITY | 73 | 42.5% | 0.96 | −5.82% | sub-T2 (was 1.78 per CLAUDE.md) |
| ETF | 50 | 56.0% | 1.92 | +41.76% | ✅ T2 |
| BOND | 3 | 0.0% | 0.00 | −1.83% | n insufficient |

### asset_class_health (all-time verdict-grade, fresh 04:13Z snapshot)

| Class | PF | WR | Tier verdict |
|-------|----|----|-------------- |
| CRYPTO | 1.263 | 48.3% | ❌ WR below 50% floor |
| EQUITY | 0.874 | 35.2% | ❌ sub-T2 |
| FOREX | 1.476 | 55.7% | ⚠️ T2 PF borderline; WR ≥ T2 — recovering |
| COMMODITY | 1.424 | 54.5% | ⚠️ T2 WR; PF borderline (need 1.5+) |
| ETF | 11.994 | 50.0% | ⚠️ PF anomalous (tiny n); WR at floor |
| FUTURES | 0.956 | 16.7% | ❌ sub-floor |
| BOND | 0.000 | 0.0% | ❌ n insufficient |

---

## §3 — Strategy Attribution (COMMODITY 24h/7d crash)

### COMMODITY 24h (n=16, WR=0%, PF=0.00)

| Strategy | n | WR | Sum PnL% |
|----------|---|----|---------|
| `futures_momentum` | 13 | 0% | −51.82% |
| `cftc_cot_commercial_signal` | 2 | 0% | −11.03% |
| `futures_bb_mean_reversion` | 1 | 0% | −6.41% |

### COMMODITY 7d (n=38, WR=7.9%, PF=0.10)

| Strategy | n | WR | PF | Sum PnL% |
|----------|---|----|----|----------|
| `cftc_cot_commercial_signal` | 20 | 5% | 0.11 | −65.79% |
| `futures_momentum` | 17 | 12% | 0.09 | −52.81% |
| `futures_bb_mean_reversion` | 1 | 0% | 0.00 | −6.41% |

### EQUITY 24h (n=16, WR=6.2%)

| Strategy | n | WR | Sum PnL% |
|----------|---|----|---------|
| `stocks_rsi2_pullback` | 11 | 0% | −33.00% |
| `rs-breakout-scout` | 1 | 0% | −2.98% |
| `aroon-trend-scout` | 1 | 100% | +4.05% |
| `vol-contraction-scout` | 1 | 0% | −3.06% |
| `price-accel-scout` | 1 | 0% | −6.92% |
| `adx-trend-scout` | 1 | 0% | −7.96% |

---

## §4 — Active Findings

### FINDING-35 (NEW — P1 Kill Candidate, n=18 floor watch)

**`futures_momentum` — all-time catastrophic**

| Metric | Value |
|--------|-------|
| All-time n | **18** |
| WR | **11.1%** |
| PF | **0.09** |
| Sum PnL | −53.31% |
| 7d n | 17 (of 38 COMMODITY 7d) |

Kill criteria check: PF<0.5 ✅ | WR<35% ✅ | n≥20 ❌ (n=18 — 2 short of floor).

**Issue #685 explicitly names `futures_momentum` as a kill candidate** ("strategy kill gated on #1: futures_momentum per tools/mutation_analysis.py"). Resolver work is complete, so gating condition is met. At n=20 (next 2 closed trades), post to issue #686 with full mutation analysis and request 3-AI consensus. **Do NOT auto-kill at n=18.**

**Action:** WATCH — escalate to consensus track at n≥20.

---

### FINDING-36 (NEW — Escalated to mutation analysis track)

**`stocks_rsi2_pullback` crossed n=30 threshold**

| Metric | Value |
|--------|-------|
| 7d n | **30** (crossed 14Z watch threshold) |
| 7d WR | **36.7%** |
| 24h n | 11 |
| 24h WR | **0%** |

14Z watch list condition met: n≥30 → escalate per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`. WR 36.7% is borderline (above 35% floor but below 40%) and 24h WR collapsed to 0% on n=11. Per mutation protocol, this needs direction-split + symbol-rotation analysis before kill decision. **Not yet a confirmed kill candidate.**

**Action:** trigger mutation analysis sandbox for `stocks_rsi2_pullback`. Post findings to issue #686 at 16Z if n stays ≥30.

---

### FINDING-24 (P0 — Gate bypass confirmed post-#694)

| Metric | Value |
|--------|-------|
| HYPEUSDT 7d n | **53** |
| Attribution | `unknown` (was `quan_engine`) |
| Expected post-#694 | 0 (symbol-block should halt all HYPEUSDT) |

**Root cause hypothesis:** PR #694 blocked `quan_engine × HYPEUSDT` via `BLOCKED_STRATEGY_SYMBOL_PAIRS`, but trades continue with `strategy = "unknown"`. Either:
- (a) The picks file is populated by a path that bypasses quality_gates.py pair-check when source attribution is missing
- (b) #694 blocked by strategy-name match only; symbol still admitted when strategy unknown/null

**Action (P0):** Investigate `audit_trail/quality_gates.py` — check if `BLOCKED_STRATEGY_SYMBOL_PAIRS` is applied before or after source attribution. If bypass confirmed, open P0 fix PR targeting symbol-level block independent of strategy attribution.

---

### FINDING-31 (Awaiting 3-AI consensus)

**`rapid_fire × UUSDT`** — n=34, WR=0.0%, PF≈0. Posted to issue #686 at 13Z. No consensus replies yet as of 15Z check. Continue monitoring.

---

### FINDING-32 (Awaiting 3-AI consensus)

**`cta_replicator × NG=F`** — n=24, WR=0.0%, PF≈0. Posted to issue #686 at 13Z. No consensus replies yet. Continue monitoring.

---

### FINDING-22 (Awaiting 3-AI consensus — n now confirmed 20)

**`cftc_cot_commercial_signal × COMMODITY`** — 7d n=20, WR=5%, PF=0.11. Kill criteria all met (PF<0.5 ✅, n≥20 ✅, WR<35% ✅). Posted previously. Awaiting 2 more AI consensus confirmations.

---

## §5 — Kill Verifications (15Z)

| Strategy | 7d n | Status |
|----------|------|--------|
| `forex_carry_momentum` | 0 | ✅ DEAD (#692) |
| `goldmine_6x_consensus` | 0 | ✅ DEAD (#692) |
| `cftc_cot` | 0 | ✅ DEAD (#683) |
| `forex_rsi2_mean_reversion` | 0 | ✅ DEAD (#692) |
| `quan_engine × HYPEUSDT` | 53 via `unknown` | ⚠️ FINDING-24 bypass (see §4) |

---

## §6 — PR Triage

### Merged this hour
- **PR #1265** (14Z audit, `audit/hourly-14z-2026-05-20`) — mergeable=clean, [skip ci], Greptile COMMENTED only, no REQUEST_CHANGES → **MERGED** ✅

### HOLD set — confirmed absent
#660 #658 #681 #661 — none present in open PR list. Hold confirmed.

### Author-rebase watch — confirmed resolved
#669 #676 #608 #665 #644 #597 #615 #655 — all absent from open PR list.

### Open PRs (as of 15Z)
Only PR #1265 was open; merged this hour. No other open PRs observed.

---

## §7 — Mutation Analysis Summary (15Z run)

Key outputs from `python tools/mutation_analysis.py`:

**Axis 1 — Direction-split candidates:**

| Strategy | SHORT WR | n | LONG WR | n | Spread |
|----------|----------|---|---------|---|--------|
| `ig_contrarian_sentiment` | 60.3% | 58 | 16.5% | 200 | 44pp → sandbox SHORT-only |
| `myfxbook_retail_contrarian` | 50.0% | 14 | 13.7% | 124 | 36pp → sandbox |
| `cta_cross_asset_tsmom` | 52.0% | 171 | 29.4% | 85 | 23pp → sandbox |

**Axis 3 — Symbol allowlist candidates:**

| Strategy | Worst symbols (WR, n) |
|----------|-----------------------|
| `rapid_fire` | UUSDT 0% n=34, ESPUSDT 0% n=5, TAOUSDT 5.6% n=18 |
| `cta_replicator` | NG=F 0% n=24, ZC=F 0% n=8, AUDUSD=X 8.3% n=12 |
| `quan_engine` | MATICUSDT 0%, ONDOUSDT 22%, SOLUSDT 23% |

**No new kill candidates beyond FINDING-35/36/22/31/32.**

---

## §8 — 16Z Watch List

1. **Dashboard snapshot:** if still 04:13Z at 16Z, escalate cron health to operator (hourly cron missed 10+ cycles)
2. **FINDING-35** (`futures_momentum`): check if n≥20 all-time → post to #686 with mutation evidence, request 3-AI consensus
3. **FINDING-36** (`stocks_rsi2_pullback`): run mutation sandbox, post direction-split + symbol-rotation results to #686
4. **FINDING-24** (HYPEUSDT gate bypass): investigate `audit_trail/quality_gates.py` block logic
5. **FINDING-31/32/22**: check issue #686 for consensus replies; if 2+ AIs confirm, open kill PRs
6. **EQUITY 7d PF=0.64**: monitor — if stays below 0.7 for 48h post-#692, escalate to root-cause review per issue #693 protocol

---

## §9 — Appendix: Baselines

| Class | Documented baseline | Source |
|-------|---------------------|--------|
| CRYPTO 24h PF | 3.54 | CLAUDE.md |
| CRYPTO 7d PF | 1.33 | CLAUDE.md |
| CRYPTO 30d PF | 1.33 | CLAUDE.md |
| EQUITY 7d PF | 0.87 | CLAUDE.md |
| EQUITY 30d PF | 1.41–2.18 | CLAUDE.md / issue #693 |
| FOREX 7d PF | 0.14 (pre-#687) | CLAUDE.md |
| FOREX 30d PF | 0.97 (pre-#687) | CLAUDE.md |
| COMMODITY PF | 1.78 (long-run) | CLAUDE.md |
