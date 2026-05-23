# Hourly Audit — 13Z 2026-05-20

**Generated:** 2026-05-20T13:15Z  
**Snapshot:** 2026-05-20T04:13:12Z (STALE ~9h — no 13Z cron refresh yet visible)  
**Previous audit:** PR #1263 (12Z) merged ✅ this hour  
**Session:** claude-sonnet-4-6

---

## Dashboard Snapshot Status

Snapshot remains at **2026-05-20T04:13:12Z** — same as 04Z–12Z windows. The 13Z hourly `[skip ci]` cron refresh has not yet written a new `dashboard_data.json`. All per-asset numbers below are computed against this stale snapshot; 14Z check will confirm whether refresh landed.

---

## Per-Asset Metrics (13Z — same snapshot as 12Z)

| Class | 24h PF | 24h n | 7d PF | 7d n | 30d PF | 30d n | vs 12Z (7d) |
|-------|--------|-------|-------|------|--------|-------|-------------|
| CRYPTO | 0.694 | 98 | 1.193 | 968 | 1.328 | 2772 | −0.016 (window-shift, stable) |
| EQUITY | 0.075 | 16 | 0.641 | 45 | 1.419 | 146 | 0.000 unchanged — degradation continues |
| FOREX | 1.278 | 7 | 1.313 | 17 | 2.515 | 93 | stable post-#687 ✅ |
| COMMODITY | 0.000 | 15 | 0.097 | 38 | 0.962 | 73 | catastrophic — FINDING-22 + FINDING-28 active |
| ETF | 0.000 | 1 | 1.233 | 16 | 1.917 | 50 | stable |
| BOND | 0.000 | 3 | 0.000 | 3 | 0.000 | 3 | trivial n |

**Baseline deltas (vs documented: CRYPTO 24h PF 3.54 / 7d 1.33 / 30d 1.33; EQUITY 7d 0.87; FOREX 7d 0.14 pre-#687):**
- CRYPTO 24h: 3.54 → 0.694 (−2.85) — stale snapshot distorts 24h window; 7d/30d stable.
- EQUITY 7d: 0.87 → 0.641 (−0.23) — goldmine_6x kill (#692) not yet reflected; continued degradation.
- FOREX 7d: 0.14 → 1.313 (+1.17) — JPY-cross BUY rule fix (#687) is working.
- COMMODITY: catastrophic across all windows (FINDING-22 active, awaiting kill consensus).

---

## EQUITY Strategy Attribution (7d, n=45)

| Strategy | n | WR | PF | Sum PnL% |
|----------|---|----|----|----------|
| `stocks_rsi2_pullback` | 29 | 34.5% | 0.980 | −1.13% |
| `vol-contraction-scout` | 3 | 33.3% | 1.109 | +0.97% |
| `stocks_ema_golden_cross` | 2 | 0.0% | 0.000 | −6.83% |
| `macd-hidden-div-scout` | 2 | 0.0% | 0.000 | −12.04% |
| `price-accel-scout` | 2 | 0.0% | 0.000 | −9.18% |
| others (n<=2 each) | 7 | mixed | — | −18.08% |

Note: `goldmine_6x_consensus` is absent from 7d data (PR #692 effective). EQUITY 7d PF deteriorated further to 0.641 from 0.87 baseline — stocks_rsi2_pullback is the main drag at n=29.

---

## COMMODITY Strategy Attribution (7d, n=38)

| Strategy | n | WR | PF | Sum PnL% |
|----------|---|----|----|----------|
| `cftc_cot_commercial_signal` | 20 | 5.0% | 0.113 | −65.79% |
| `futures_momentum` | 17 | 11.8% | 0.087 | −52.81% |
| `futures_bb_mean_reversion` | 1 | 0.0% | 0.000 | −6.41% |

---

## CRYPTO Strategy Attribution (7d, n>=20 strategies)

| Strategy | n | WR | PF |
|----------|---|----|----|----|
| `st_fear_greed_contrarian` | 219 | 67.1% | 3.012 |
| `unknown` (FINDING-24 bypass) | 150 | 32.0% | 1.120 |
| `luxalgo_confluence` | 149 | 41.6% | 1.027 |
| `strong consensus (alpha_engine, ml_crypto_pred)` | 112 | 36.6% | 0.839 |
| `claude_ml_moderate_mut` | 43 | 48.8% | 1.563 |
| `crypto_mtf_ema_slope_alignment_v1` | 27 | 33.3% | 0.505 |

---

## Findings Status

**FINDING-22 (P1)** — `cftc_cot_commercial_signal x COMMODITY`: n=20, WR=5.0%, PF=0.113, sum=−65.79%. All kill criteria met (PF<0.5, n>=20, WR<35%). Awaiting 3-AI consensus. Posted to issue #686. No action until consensus confirmed.

**FINDING-24 (P1)** — `quan_engine x HYPEUSDT` gate bypass: `unknown` strategy still generating n=150 picks (7d) — gate bypass in `passes_active_gate()` not yet patched post-PR #694. Fix required in production scanner.

**FINDING-28 (WATCH)** — `futures_momentum x COMMODITY`: n=17, WR=11.8%, PF=0.087. Below n=20 floor — no kill action. Escalate at 14Z if n>=20.

**FINDING-29 (WATCH)** — `strong_consensus x CRYPTO`: n=112, WR=36.6%, PF=0.839. Above kill floor (PF>0.5). Monitor only.

**FINDING-30 (WATCH → ESCALATE at 14Z)** — `stocks_rsi2_pullback` (EQUITY): 7d n=29, WR=34.5%, PF=0.980. n=29 is 1 below the n=30 escalation threshold. If 14Z snapshot shows n>=30 with WR<35%, escalate to mutation analysis per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`.

---

## NEW FINDINGS (from 13Z mutation_analysis.py run)

### FINDING-31 (NEW — P1 candidate) — `rapid_fire x UUSDT`
- 7d n=34, WR=0.0%, avg PnL=−0.17%, sum=−5.78%
- Meets kill criteria: PF<0.5 (PF≈0), n>=20, WR<35%
- Pattern: consistent 0% WR across 34 trades — not a statistical fluke
- Action: posted to issue #686 for 3-AI consensus. Do NOT auto-add to `BLOCKED_STRATEGY_SYMBOL_PAIRS` without consensus.

### FINDING-32 (NEW — P1 candidate) — `cta_replicator x NG=F`
- 7d n=24, WR=0.0%, avg PnL=−0.03%
- Meets kill criteria: PF<0.5 (PF≈0), n>=20, WR<35%
- `cta_replicator` also drags on `ZC=F` (n=8, WR=0%) and `AUDUSD=X` (n=12, WR=8.3%) — symbol allowlist mutation warranted
- Action: posted to issue #686 for 3-AI consensus.

### FINDING-33 (NEW — WATCH) — Direction-flip mutation candidates
From `mutation_analysis.py` section 1 (direction-flip by SHORT vs LONG):

| Strategy | SHORT WR | SHORT n | LONG WR | LONG n | Spread |
|----------|----------|---------|---------|--------|--------|
| `ig_contrarian_sentiment` | 60.3% | 58 | 16.5% | 200 | 44pp |
| `myfxbook_retail_contrarian` | 50.0% | 14 | 13.7% | 124 | 36pp |
| `quan_engine_swing` | 60.0% | 5 | 26.0% | 104 | 34pp |
| `cta_cross_asset_tsmom` | 52.0% | 171 | 29.4% | 85 | 23pp |

These are Axis-1 mutation candidates per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` — SHORT-only variants should be sandboxed. None qualify for kill today (LONG WR > 0, need mutation test, not kill).

---

## Kill Verifications (unchanged from 12Z)

| Strategy | 7d n | Status |
|----------|------|--------|
| `forex_carry_momentum` | 0 | DEAD |
| `goldmine_6x_consensus` | 0 | DEAD |
| `cftc_cot` (PR #683) | 0 | DEAD |
| `forex_rsi2_mean_reversion` | 0 | DEAD |
| `quan_engine/HYPEUSDT` (PR #694) | 150 (`unknown`) | Gate bypass — FINDING-24 |

---

## PR Triage

**Merged this hour:** #1263 (12Z audit)  
**HOLD set (#660 #658 #681 #661):** absent from open PRs  
**Author-rebase watch (#669 #676 #608 #665 #644 #597 #615 #655):** absent from open PRs  
**Plan v2.1 fabrication family:** no open PRs citing PF 5.81 / ml_score 0.90 / WINNER_FILTER seen  

---

## 14Z Checklist

- [ ] Confirm snapshot refresh (04:13Z → should update to ~13Z or 14Z)
- [ ] FINDING-28: check n>=20 for `futures_momentum x COMMODITY`
- [ ] FINDING-30: check n>=30 for `stocks_rsi2_pullback`; if WR<35% → escalate to mutation analysis
- [ ] FINDING-31: check issue #686 for 3-AI consensus on `rapid_fire x UUSDT`
- [ ] FINDING-32: check issue #686 for 3-AI consensus on `cta_replicator x NG=F`
- [ ] FINDING-24: verify gate bypass fix PR status in `passes_active_gate()`
- [ ] CRYPTO 24h: re-evaluate with fresh snapshot (current 0.694 likely snapshot-window artifact)

---

_Generated by Claude Code · audit/hourly-13z_
