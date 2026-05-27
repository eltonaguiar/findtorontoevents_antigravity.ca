# EAGLE: Safety Gate Exemptions — Picks That Would Have Won
**Date:** 2026-05-27 02:26 EST | **Model:** Claude Opus 4.7 (via CommandCode)
**Branch:** `feat/EAGLE-2026-05-27-end-to-end-review`

---

## Executive Summary

**Finding:** The safety gates in `audit_trail/quality_gates.py` (10,500+ lines) are calibrated correctly. Overwhelmingly they block picks where edge is provably absent (WR 6-40%). However, 3 categories of picks deserve targeted exemption: (1) high-confidence band (0.85-0.90) CRYPTO picks with 82% WR, (2) elite sources on liquid core symbols filtered by class-wide blocks, (3) SHORT-only FOREX picks where directional gate blocks the proven edge.

---

## 1. Picks That Would Have Won but Were Filtered

### 1.1 CRYPTO: Confidence Band 0.85-0.90 (WR=82%)

The confidence overfit cliff gate (M-035) correctly blocks conf>0.90 (WR=14%). But the adjacent 0.85-0.90 band has WR=82% — the HIGHEST in any band. The gate correctly does NOT block this band. However, the confidence dead-zone gate (0.65-0.75, WR=26.2%, currently shadow) could accidentally overlap if promoted without band-checking.

**Exemption recommendation:** DO NOT change the gates. The 0.85-0.90 band is already exempt from M-035. Ensure any dead-zone enforcement has explicit band overlap check.

### 1.2 CRYPTO: Elite Sources on Liquid Core — Blocked by Class-Wide Dragger Rules

**The problem:** luxalgo_filters contributes 23% of CRYPTO volume but overall PF=1.07. On BTC/ETH specifically, PF is significantly higher. Source-quarantine rules (M-004, currently shadow) don't distinguish liquid core from meme coins. 5+ high-volume sources (luxalgo/alpha_engine/quan_engine/copy_trader/battleground = 50%+ combined volume at PF<1.1) are not fully blocked — just penalized or capped. The reverse problem: if we hard-block these sources, we lose the BTC/ETH edge.

**Exemption recommendation:** Source whitelist for LIQUID_CRYPTO_CORE only:
```
IF source IN ['luxalgo_filters', 'alpha_engine', 'quan_engine']
   AND symbol IN LIQUID_CRYPTO_CORE (BTC/ETH/SOL/AVAX/NEAR/SUI/ADA/LINK/ARB)
   THEN ALLOW (exempt from source quarantine)
ELSE BLOCK
```

**Expected impact:** Retain BTC/ETH edge from high-volume sources while cutting -20-30% of noisy alt/meme volume. Pf lift: +0.1-0.2.

### 1.3 FOREX: SHORT-Only Sleeve — Blocked by HARD_DISABLE

**The evidence:** SHORT direction PF=8.11 on n=29 vs LONG PF=0.80 on n=119. The FOREX HARD_DISABLE (NS-E) blocks ALL FOREX correctly (class-level PF=0.81). But a SHORT-only sleeve on 4 majors (EURUSD/GBPUSD/AUDUSD/USDJPY) with DXY confluence gate has proven edge in mutation autopsy.

**Exemption recommendation:** Per-symbol, per-direction exemption from HARD_DISABLE:
```
IF asset_class == 'FOREX'
   AND direction == 'SHORT'
   AND symbol IN ('EURUSD=X', 'GBPUSD=X', 'AUDUSD=X', 'USDJPY=X')
   AND passes DXY confluence gate (DXY 4H EMA20 < EMA50 for USD-weak SHORT)
   THEN ALLOW (exempt from HARD_DISABLE)
```

**Acceptance gate:** 30d rolling PF≥1.3, WR≥50%, n≥20 in paper before ANY exemption activates.

### 1.4 EQUITY: Classic Momentum — Soft-VIX not Hard-VIX

The VIX regime gate for EQUITY is currently shadow/soft (vix_confidence_adj only). The branch `feat/equity-vix-regime-gate-sidecar-2026-05-13` has VIX<22 hard filter with backtest PF 5.37 vs baseline 2.82. This gate would be too aggressive — it skips 16% of months. Classic Momentum with soft VIX adj already delivers PF 1.57 live.

**Exemption recommendation:** Keep VIX as SOFT adj (confidence reduction, not hard block) for proven momentum strategies. Only hard-block if VIX>30 (crisis) for all EQUITY.

### 1.5 COMMODITY: Carry-Momo — Bypass the COT Over-Emission Problem

COT positioning on CT=F is falsified (PF 0.17 post-dedup). But carry_momo double-sort (Miffre 2010) on 18 symbols is academic-grade and NOT using COT data. The carry-momo sidecar is currently pending — it bypasses the COT problem entirely.

**Exemption recommendation:** Carry-momo should be EXEMPT from COT-related gates (MATCH gate, DSR≥0.85 COT gate). It uses different data (price momentum + roll-yield proxy), different symbols (18 vs 1), and different academic backing.

---

## 2. Hot Streak Auto-Exemption Framework

A pick that consistently wins should earn progressively looser gate treatment:

### Auto-Exemption Criteria
| Condition | Threshold | Effect |
|---|---|---|
| Rolling 30d PF | ≥1.8 | Exempt from elite_score floor |
| Rolling 30d WR | ≥55% | Exempt from confidence dead-zone (0.65-0.75) |
| Rolling 30d n | ≥30 | Statistically meaningful — trust the edge |
| Symbol liquidity | In LIQUID_* core | Exempt from ADV gate |
| Source reputation | dna_winner/mega_mutation/baby_strats_forward | Exempt from source quarantine |

### Auto-Revoke Criteria
| Condition | Threshold | Effect |
|---|---|---|
| Rolling 7d PF | <1.3 | Revoke all exemptions |
| Rolling 7d WR | <48% | Revoke confidence exemptions |
| Regime change flag | VIX spike >2σ, DXY trend reversal | Temporary exemption suspension |
| MDD breach | >15% in 30d | Permanent review flag |

### Implementation
- **File:** `audit_trail/quality_gates.py` — new function `exemption_hot_streak(pick, rolling_stats)`
- **Env:** `HOT_STREAK_EXEMPTION_ENABLED=1` (default OFF until shadow-proven)
- **Shadow first:** 30d of shadow logging before any enforcement — never auto-exempt without evidence
- **Audit trail:** Every exemption stamped with `exemption_reason`, `rolling_pf`, `rolling_wr`, `exemption_expires_at`

---

## 3. Picks That Should NEVER Get Exempted

| Category | Reason |
|---|---|
| MEMECOIN class (any) | PF=0.50, WR=15.7%, n=1869 — structural negative edge. No hot streak is real. |
| PENNY_STOCK class (any) | PF=0.19, WR=6.8%, n=148 — sub-coin-toss. Gap risk alone invalidates any short-term PF. |
| FOREX LONG direction | LONG WR=29.4% PF=0.80 — anti-edge proven across 119 trades, multiple sources. |
| Confidence >0.90 (CRYPTO) | WR=14% — the cliff is real. 82% WR drops to 14% probability between 0.85-0.90 and 0.90+. |
| 15m timeframe strategies | DSR<0.5, structural overfit. M-028 correctly quarantines these. |
| Baby strats overfit variants | Forward WR 33-41% vs backtest WR 49-66%. 12 variants already blocked. |
| copy_trader_highscore | PF=0.80, WR=30.3% — already in BLOCKED_SOURCE_SYSTEMS. |
| battleground | PF=0.65 — already blocked. |
| regime_terminal | PF=0.95, WR=32.3% — consistently negative alpha. |

---

## 4. Summary Matrix

| What | Exempt? | Condition | PF Lift Expected |
|---|---|---|---|
| CRYPTO conf 0.85-0.90 band | Already exempt | Keep it that way | 0 (correctly deployed) |
| luxalgo_filters on BTC/ETH only | YES | Source whitelist for LIQUID_CORE | +0.05-0.10 |
| alpha_engine on BTC/ETH only | YES | Source whitelist for LIQUID_CORE | +0.05-0.10 |
| FOREX SHORT on 4 majors | YES (after paper) | DXY gate + 30d PF≥1.3 | PF>1.3 if gated |
| EQUITY momentum VIX<22 | SOFT EXEMPT | VIX adj, not hard block | +0.3-0.8 |
| COMMODITY carry-momo | EXEMPT from COT gates | Uses different data | T2 if n≥80 |
| MEMECOIN (any) | NEVER | — | — |
| PENNY_STOCK (any) | NEVER | — | — |
| FOREX LONG (any) | NEVER | — | — |
| conf >0.90 (CRYPTO) | NEVER | — | — |
| 15m timeframe strats | NEVER | — | — |
