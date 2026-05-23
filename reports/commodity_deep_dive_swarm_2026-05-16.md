# COMMODITY Asset Class — Deep Dive Research Report
**Date:** 2026-05-16 | **Priority:** P0 | **Author:** Quantitative Research Subagent
**Sources:** dashboard_data.json (live), quality_gates.py (audit_trail/), commodity_*_2026-05-16.md reports, commodity_phase2d_reaudit_2026-05-16.md, commodity_n339_forensics_20260515.md, asset_class_90day_plan_COMMODITY_2026-05-15.md

---

## Executive Summary

The COMMODITY T2/T1 headline is **entirely a data artifact**. Strip the CT=F COT over-emission duplicates and the ZW=F/ZS=F blacklist leakage, and true tradeable COMMODITY performance is **PF 0.12–0.33 / WR 5–16%** — sub-floor, comparable to FOREX. Two bugs actively corrupt the current numbers: (1) `multi_asset_copytrader` is not in `COT_DEDUP_SYSTEMS` so it continues firing duplicate COT signals on blacklisted grain symbols; (2) `non_crypto_consensus` bypasses the `COMMODITY_BLACKLIST` check entirely. HG=F and PL=F (the two officially allowed symbols) have **zero picks in recent_closed** — the production gate is allowing nothing tradeable through.

---

## 1. Strategy Inventory — All COMMODITY Sources

### Source System Performance (recent_closed, n=67 total COMMODITY picks)

| Source System | n | WR% | PF | Sum PnL | Notes |
|---|---|---|---|---|---|
| multi_asset_cot | 30 | 60.0% | 1.67 | +33.81% | Inflated by CT=F pre-dedup. After dedup: WR~40%, PF~0.17 per forensic audit |
| multi_asset_copytrader | 33 | 54.5% | 2.38 | +55.24% | 41/33 picks are CT=F (WR 80%); ex-CT pick count is tiny with 0-15% WR on blacklisted symbols |
| alpha_engine | 2 | 50.0% | 0.80 | −0.20% | NG=F (1 win), GC=F (1 loss) — both blacklisted |
| alpha_engine_fast | 2 | 0.0% | 0.00 | −2.43% | GC=F + SI=F — both blacklisted, both pre-blacklist-date |

### Strategy Performance (recent_closed)

| Strategy | n | WR% | PF | Sum PnL | Assessment |
|---|---|---|---|---|---|
| cot_positioning | 32 | 59.4% | 1.66 | +33.61% | Inflated by CT=F over-emission; post-dedup true WR ~40%, PF ~0.17 |
| cftc_cot_commercial_signal | 32 | 56.2% | 2.41 | +55.69% | Same issue; fires on ZS=F/ZW=F (blacklisted) without dedup |
| liquidity_sweep_reversal | 2 | 0.0% | 0.00 | −2.43% | Legacy GC=F/SI=F — pre-blacklist |
| futures_bb_mean_reversion | 1 | 0.0% | 0.00 | −0.44% | ZW=F — blacklisted |
| commodity_carry_momo_double_sort | 0 closed | N/A | N/A | N/A | 1 active (OJ=F SHORT score=56); opt-in sidecar, not wired to scoring path |

### Full Database (by_asset_class, all time)

| Metric | Value | Status |
|---|---|---|
| closed | 229 | Includes ~200+ pre-dedup COT duplicates |
| wins | 195 | Inflated |
| WR | 85.5% | **Artifact — not real** |
| PF | 7.71 | **Artifact — not real** |

**Tradeable reality (post-dedup, ex-CT=F cotton):** ~PF 0.12–0.33, WR 5–16% on n=~25 picks.

---

## 2. Per-Symbol Stats Table

### Recent Closed Picks (n=67, rolling window)

| Symbol | Blacklisted? | n | WR% | PF | Sum PnL% | Notes |
|---|---|---|---|---|---|---|
| CT=F (Cotton) | NO (unblocked 2026-05-16) | 41 | 80.5% | 5.74 | +134.49% | **Dominant driver. Pre-dedup: 5 unique CFTC cycles. One cotton price move counted ~41×.** |
| ZW=F (Wheat) | YES | 13 | 23.1% | 0.41 | −23.43% | **Leaking through blacklist via multi_asset_copytrader (not in COT_DEDUP_SYSTEMS)** |
| ZS=F (Soybeans) | YES | 8 | 0.0% | 0.00 | −17.10% | **Leaking through blacklist same path** |
| KC=F (Coffee) | YES | 2 | 0.0% | 0.00 | −5.91% | Pre-blacklist-date |
| NG=F (Nat Gas) | YES | 1 | 100.0% | inf | +0.80% | Pre-blacklist-date, single pick |
| GC=F (Gold) | YES | 1 | 0.0% | 0.00 | −0.03% | Pre-blacklist-date |
| SI=F (Silver) | YES | 1 | 0.0% | 0.00 | −2.40% | Pre-blacklist-date |
| **HG=F (Copper)** | **NO** | **0** | **N/A** | **N/A** | **N/A** | **ZERO picks — officially allowed, but no signals generated** |
| **PL=F (Platinum)** | **NO** | **0** | **N/A** | **N/A** | **N/A** | **ZERO picks — officially allowed, but no signals generated** |

### Active Picks Right Now (2026-05-16)

| Symbol | Source | Strategy | Direction | Score | Status |
|---|---|---|---|---|---|
| OJ=F | commodity_carry_momo | commodity_carry_momo_double_sort | SHORT | 56 | OJ=F not blacklisted; carry_momo sidecar |
| CT=F | non_crypto_consensus | non_crypto_consensus | SHORT | 51 | Aggregated from copytrader signal |
| ZW=F | multi_asset_copytrader | cftc_cot_commercial_signal | SHORT | 40 | **BUG: blacklisted symbol, should be blocked** |
| ZW=F | non_crypto_consensus | non_crypto_consensus | SHORT | 35 | **BUG: blacklisted, bypasses blacklist via aggregator** |
| CT=F | multi_asset_copytrader | cftc_cot_commercial_signal | SHORT | 32 | Cotton; dedup needed |

---

## 3. WR Gap Analysis

The WR discrepancy across sources (46.9% / 54% / 55.2% / 85.5%) reflects **four different measurement windows and artifact states**:

| Panel | WR | n | Source date | Artifact state |
|---|---|---|---|---|
| CLAUDE.md (asset_class_health) | 46.9% | 750 | 2026-05-03 | Pre-CT=F unblock; different data cut |
| recent_closed rolling window | 55.2% | 67 | 2026-05-16 | Includes CT=F (80.5% WR) pulling aggregate up; ex-CT=F = 15.4% WR |
| hf_stats by_asset_class (n=74) | 54% | 74 | 2026-05-16 | Same window, slight difference in closed count |
| by_asset_class (full DB) | 85.5% | 229 | All time | **Maximally inflated** — all pre-dedup COT duplicates, full CT=F artifact |

**True tradeable WR (post-dedup, blacklist-enforced, ex-CT=F):** approximately 5–16% based on recent_closed ex-CT slices. Below 20%.

---

## 4. COT Signal Quality Analysis

### COT Dedup Gate Status (PR-#994)

The `COT_DEDUP_GATE` (72h window, `quality_gates.py` L1819-1834) is **partially implemented but has a critical gap**:

**Covered systems** (L1829-1834):
- `multi_asset_cot`
- `cot_positioning`
- `cftc_cot_commercial_signal`

**Gap: `multi_asset_copytrader` is NOT in `COT_DEDUP_SYSTEMS`** even though it emits `cftc_cot_commercial_signal` picks on ZS=F and ZW=F without any dedup protection. ZW=F (score=40) is active right now from this source.

### Historical Over-Emission Impact

Pre-PR-#994 data from `commodity_phase2d_reaudit_2026-05-16.md`:
- CT=F: 230 closed picks from **16 unique dates, 14.4 picks/date average**
- 21 distinct entry prices had >2 duplicates; worst = 22 picks at $83.00
- All are SHORT (100%), WR 85.7%, PF 7.80 — one profitable cotton SHORT counted 230×

Post-PR-#994 window (2026-05-15+): 5 picks total — 3× ZW=F (0 wins), 2× CT=F (1 win). Post-dedup CT=F picks are from `multi_asset_copytrader`, not `multi_asset_cot`, so they are not subject to the dedup gate.

### COT vs Non-COT Split

Of the 67 recent_closed COMMODITY picks:
- COT-tagged (cot_positioning or cftc_cot_commercial_signal strategy): **64 picks (95.5%)**
- Non-COT: **3 picks** (alpha_engine_fast liquidity sweeps)

COMMODITY is almost entirely a COT bet, with zero diversification from other strategies.

---

## 5. Seasonal Patterns (calendar_anomalies.py)

**Finding: No COMMODITY seasonal patterns implemented.** `alpha_engine/calendar_anomalies.py` contains exactly **1 reference** to "commodity/seasonal" — a boilerplate citation of Bouman & Jacobsen (2002) about turn-of-month effects, not a commodity-specific implementation.

The `commodity_carry_momo_double_sort` sidecar (`audit_dashboard/data/commodity_carry_momo.json`) references backtest_commodity_seasonal_2026-05-12 but is flagged `wiring_status="OPT_IN_SIDECAR"` and has 0 resolved picks in the dashboard systems table.

**No commodity seasonal patterns are wired into production.** This is a confirmed gap vs. the academic literature (Gorton & Rouwenhorst 2006 commodity seasonal, USDA crop calendar).

---

## 6. VIX/YC Gate Coverage

`audit_trail/vix_regime_gate.py::should_reject_combined()` (L140-167) explicitly gates on:
```python
if ac not in ("EQUITY", "ETF"):
    return False
```

**COMMODITY is NOT covered by VIX/YC gate.** This is **appropriate** for two reasons:
1. Commodity volatility regimes (inventory cycles, weather, CFTC positioning) are orthogonal to equity VIX.
2. Adding VIX gate to COMMODITY would require independent validation against commodity-specific volatility metrics (e.g. OVX for oil, GVZ for gold).

**Recommendation: Do not extend should_reject_combined() to COMMODITY.** Instead, consider a commodity-specific regime gate (CFTC managed money net position as regime filter, or HG=F spread as economic signal).

---

## 7. Blacklist Symbol Review (GC=F, SI=F, NG=F)

### Current Blacklist Data (from commodity_phase2d_reaudit_2026-05-16.md full DB)

| Symbol | n (full DB) | WR% | Non-COT WR | Assessment |
|---|---|---|---|---|
| GC=F (Gold) | 10 | 0.0% | 0.0% | Sub-floor. No COT data. n too small for regime verdict. **Keep blacklisted.** |
| SI=F (Silver) | 47 | 2.1% | 2.1% | 2 wins in 47 picks. No COT exposure. n=47 approaching charter floor but WR catastrophic. **Keep blacklisted.** |
| NG=F (Nat Gas) | 26 | 3.8% | 3.8% | 1 win in 26 picks (non-COT). Extreme volatility, gap risk. **Keep blacklisted.** |
| HG=F (Copper) | 33 | 0.0% | 0.0% | Officially allowed, but 0% WR in full DB with n=33. **Investigate before relying on** |
| ZW=F (Wheat) | 35 | 20.0% | 12.5% | Blacklisted, leaking. Minor COT inflation. **Stay blacklisted.** |
| ZS=F (Soybeans) | 19 | 0.0% | 0.0% | Blacklisted, leaking. 0% WR. **Stay blacklisted.** |

**No currently-blacklisted symbols merit probation.** GC=F is the best candidate for future review (n=10 is too small for verdict; if COT-enabled GC signals emerge post-dedup with n≥30, re-evaluate). SI=F at n=47 / 2.1% WR has sufficient n to confirm it is genuinely sub-floor.

---

## 8. Top 3 Actionable Code Changes

### Change 1 (P0) — Add `multi_asset_copytrader` to `COT_DEDUP_SYSTEMS`

**File:** `audit_trail/quality_gates.py`, **Lines:** 1829–1834

**Current:**
```python
COT_DEDUP_SYSTEMS = frozenset({
    "multi_asset_cot",
    "cot_positioning",
    "cftc_cot_commercial_signal",
})
```

**Fix:**
```python
COT_DEDUP_SYSTEMS = frozenset({
    "multi_asset_cot",
    "cot_positioning",
    "cftc_cot_commercial_signal",
    "multi_asset_copytrader",  # Added 2026-05-16: emits cftc_cot_commercial_signal picks
                                # on ZS=F/ZW=F (blacklisted) without dedup. ZW=F active pick
                                # observed 2026-05-16 09:11Z from this source.
})
```

**Expected impact:** Blocks duplicate COT signals from `multi_asset_copytrader` on ZS=F, ZW=F, CT=F. Reduces COMMODITY noise picks immediately. The dedup gate only fires for picks that are already active within 72h, so it doesn't block first-occurrence signals — it stops the hourly re-emission of the same weekly COT signal.

---

### Change 2 (P0) — Remove `multi_asset_cot` and `multi_asset_copytrader` from `_COMMODITY_TRUSTED_SOURCES` in `passes_smart_gate`

**File:** `audit_trail/quality_gates.py`, **Lines:** 7161–7165

**Problem:** `_COMMODITY_TRUSTED_SOURCES` grants grade-D picks from these sources a bypass past the score floor in `passes_smart_gate`. The trust was awarded based on `PF 20.54` (multi_asset_cot) and `WR 93.8%` (multi_asset_copytrader) — both measured **before** the COT dedup fix and are inflated. Post-dedup: WR~40%, PF~0.17.

**Fix:**
```python
_COMMODITY_TRUSTED_SOURCES = frozenset({
    # REMOVED 2026-05-16: multi_asset_cot (PF 20.54 was pre-dedup artifact, post-dedup PF=0.17)
    # REMOVED 2026-05-16: multi_asset_copytrader (WR 93.8% was CT=F over-emission artifact)
    "commodity_cot_contrarian",  # CFTC COT commercial signal — keep, institutionally validated
    # Re-add multi_asset_cot/copytrader only after post-dedup n≥30 clean picks confirmed
})
```

**Expected impact:** Forces multi_asset_cot and multi_asset_copytrader COMMODITY picks to pass the score floor. Since these picks consistently score grade-D (no crypto boosters), most will be rejected, reducing COMMODITY active pick volume to near-zero until a clean COT strategy is built. This is correct — the data shows the current volume is noise.

**Risk:** May temporarily drop COMMODITY to 0 active picks. This is acceptable and honest — there is no proven edge to display.

---

### Change 3 (P1) — Enforce `COMMODITY_BLACKLIST` for `non_crypto_consensus` picks

**File:** `audit_trail/quality_gates.py`, **Lines:** 6001–6014

**Problem:** `non_crypto_consensus` picks currently have `source_system="non_crypto_consensus"` which does not appear in `_COMMODITY_TRUSTED_SOURCES`. However, the blacklist check at L6004–6014 only checks `asset_class in ("COMMODITY","COMMODITIES")` and `symbol in COMMODITY_BLACKLIST`. The ZW=F active pick from `non_crypto_consensus` (score=35) is in the dashboard's `active_raw`, meaning it passed `passes_active_gate`. This suggests the consensus aggregator inserts picks into `active_raw` without running them through `passes_active_gate`, or the pick was admitted before the blacklist update.

**Fix:** Add explicit `non_crypto_consensus` blacklist enforcement after the existing check (L6015):
```python
# ── Non-crypto consensus aggregator: enforce COMMODITY_BLACKLIST explicitly ──
# non_crypto_consensus aggregates from multiple sources and may bypass the
# blacklist check if picks are inserted directly into the active cache.
# 2026-05-16: ZW=F active pick from non_crypto_consensus confirmed in dashboard.
_ncc_ss = str(pick.get("source_system", "") or "").lower()
if _ncc_ss == "non_crypto_consensus":
    _ncc_ac = str(pick.get("asset_class", "") or "").upper()
    if _ncc_ac in ("COMMODITY", "COMMODITIES") and symbol.upper() in COMMODITY_BLACKLIST:
        logger.debug("Pick rejected: non_crypto_consensus commodity_blacklist (%s)", symbol)
        return False
```

**Expected impact:** Closes the aggregator bypass for blacklisted commodity symbols. Prevents ZW=F, ZS=F from appearing as active COMMODITY picks via the consensus path.

---

## 9. Risk Register

| Risk | Severity | Likelihood | Mitigation |
|---|---|---|---|
| Change 1 over-blocks first-occurrence signals | Medium | Low | COT_DEDUP_GATE only blocks re-emissions within 72h while a pick is already active; first-occurrence is never blocked |
| Change 2 drops COMMODITY to 0 active picks | Medium | High | Acceptable — current picks are noise. Label COMMODITY as "rebuilding" in dashboard. Carry_momo sidecar (OJ=F) still active |
| Change 3 breaks non_crypto_consensus for legitimate commodity symbols | Low | Low | The check is scoped to symbols in COMMODITY_BLACKLIST; CT=F, HG=F, PL=F, OJ=F are NOT in the blacklist and will pass |
| Historical dirty data persists in by_asset_class (n=229, WR=85.5%) | High | Certain | Requires dashboard_generator.py re-aggregation with dedup applied to historical MySQL data — not addressable via quality_gates.py alone |
| commodity_carry_momo_double_sort emits on unvalidated symbols (OJ=F) | Medium | Medium | OJ=F is not blacklisted but has no resolved picks in dashboard. 1 active pick. Monitor but don't block. |
| Removing trusted sources causes HG=F/PL=F legitimate picks to be blocked | Low | Low | HG=F/PL=F have zero current picks anyway; if they emit, they won't be from multi_asset_cot/copytrader — they'll need their own source |
| CT=F cotton remains single-symbol concentration after fixes | High | Certain | Cannot fix via quality_gates alone; requires hard cap: add CT_MAX_CONCURRENT_ACTIVE = 1 or max_concentration gate |

---

## 10. Symbols for SHADOW/PROBATION Review

### Current Recommendations

| Symbol | Current Status | Recommendation | Evidence |
|---|---|---|---|
| CT=F | PROBATION (just unblocked 2026-05-16) | **Continue PROBATION but enforce single-active-pick cap** | WR 80.5% is real-direction correct but was over-emitted. Post-dedup n is ~5 cycles. Need n=20+ clean cycles before graduating. |
| OJ=F | Active (commodity_carry_momo) | **SHADOW** — monitor without increasing allocation | 1 active pick, no resolved history. Carry_momo signal. Not blacklisted. |
| HG=F | Allowed (0 picks) | **Investigate why no signals generate** — add diagnostic logging | n=33 in full DB at 0% WR, but this may be old pre-blacklist data. No current strategy actively targeting HG=F. |
| GC=F | Blacklisted | **Keep blacklisted** — n=10 too small for probation; no COT coverage | 0% WR in full DB (n=10). Re-evaluate if a COT-based GC signal emerges with n≥30 |
| SI=F | Blacklisted | **Keep blacklisted** — n=47, WR 2.1% is verdict-grade bad | 45 losses in 47 picks. No viable edge at any strategy tested. |
| NG=F | Blacklisted | **Keep blacklisted** — extreme gap risk, n=26 WR 3.8% | 1 win in 26 picks. High vol, no micro contract. |
| ZW=F | Blacklisted + leaking | **Keep blacklisted; fix the leak (Changes 1+3 above)** | n=13 post-blacklist leaks at WR 23.1%, sum −23.43% |
| ZS=F | Blacklisted + leaking | **Keep blacklisted; fix the leak** | n=8 post-blacklist leaks at WR 0% |

---

## 11. Why the Headline Numbers Are Wrong (Technical Summary)

```
Full DB  by_asset_class: closed=229, WR=85.5%, PF=7.71
  └─ ~200 CT=F COT duplicates (same 5 CFTC releases re-emitted 14-20× each)
  └─ ~30 pre-blacklist blacklisted symbols (GC, SI, CL, KC, ZW, ZS)

Recent_closed window: n=67, WR=55.2%
  └─ CT=F n=41, WR=80.5% (post-unblock probation data; still pre-dedup)
  └─ ZW=F n=13, WR=23.1% (blacklisted, leaking via multi_asset_copytrader)
  └─ ZS=F n=8, WR=0% (blacklisted, leaking)
  └─ Other blacklisted n=4 (legacy)

True clean COMMODITY:
  └─ Post-dedup, ex-CT, ex-blacklisted: n≈25, WR≈10-16%, PF≈0.12-0.33
  └─ Confirmed by: commodity_cot_post_dedup_rederivation_2026-05-16.md
     "post-PR#994: n=20, WR=5.0%, PF=0.12, −58.9%"
     "ex-cotton: n=36, WR=16.7%, PF=0.33, −51.5%"

HG=F + PL=F (officially allowed): 0 resolved picks. Production strategies not generating signals.
```

**Verdict: COMMODITY is NOT T2 and NOT T1.** It is sub-floor (PF<1) on clean data. The 90-day plan from `reports/asset_class_90day_plan_COMMODITY_2026-05-15.md` is the correct roadmap — diversify, clean historical data, wire carry_momo, re-validate with independent n≥100.

---

## 12. References

- `reports/commodity_cot_post_dedup_rederivation_2026-05-16.md` — post-dedup PF 0.12 confirmation
- `reports/commodity_phase2d_reaudit_2026-05-16.md` — full DB forensic; 230 CT=F duplicates
- `reports/commodity_n339_forensics_20260515.md` — n=339 inflation analysis
- `reports/commodity_dedup_verification_2026-05-16.md` — PR-#994 dedup not confirmed applied
- `reports/asset_class_90day_plan_COMMODITY_2026-05-15.md` — 90-day diversification plan
- `reports/cot_pipeline_audit_20260514.md` — over-emission timeline
- `audit_trail/quality_gates.py` L1829-1834 (COT_DEDUP_SYSTEMS), L6001-6014 (COMMODITY_BLACKLIST gate), L7161-7165 (_COMMODITY_TRUSTED_SOURCES)
- `audit_trail/vix_regime_gate.py` L140-167 (should_reject_combined — EQUITY/ETF only)
- `alpha_engine/calendar_anomalies.py` — no commodity seasonals implemented

_NFA. All numbers from 2026-05-16 workspace files. This report advances Goal #1 by exposing the data artifacts that would otherwise lead to false confidence in COMMODITY sizing._
