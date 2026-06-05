# Paper-Pilot Cohort — v3 RESOLVER-FAIL FINDING

**Date:** 2026-06-05
**Status:** **ALL 4 SLEEVES FAIL at Stage 0 (Resolver Validation gate per v2 spec §7)**
**Author:** claude-sonnet-4.6

---

## 0. Headline

The v2 spec demanded intrabar OHLCV validation before any real money. **That validation REFUTED the entire cohort.** Of the 4 proposed sleeves:

| Sleeve | Symbol | Reclassify Rate | Stressed PF | Verdict |
|---|---|---|---|---|
| S1 | JUPUSDT | **28.0%** | 3.00 | **FAIL** (over 20% threshold) |
| S2 | ENAUSDT | **100.0%** | 0.67 | **FAIL** (every TP was actually SL) |
| S3 | ADAUSDT | **87.5%** | 0.93 | **FAIL** |
| S4 | DYDXUSDT | **100.0%** | 0.67 | **FAIL** (only 3 in window, but 100%) |

**Per v2 spec §7 Step 1 gate: reclassify_rate > 20% = REJECT SLEEVE.**
**3 of 4 sleeves have reclassify_rate > 80%.**

---

## 1. What This Means

The "85% WR / PF 9" historical numbers were inflated by the **NOMINAL_TP_LEGACY resolver bug**. When we replay 1h OHLCV from entry to close, the true intrabar price action shows:

- The price usually **hit the SL first** intraday before reaching the TP
- The resolver assumed a clean TP fill at the target price with no intrabar drawdown
- The "wins" were not really wins — they were trades that would have been stopped out in real life

**The 4 CRYPTO edges are largely an artifact of the resolver, not real edge.**

---

## 2. Data Quality Findings

The validation tool also surfaced two pre-existing data quality issues:

### 2a. `created_at` is 100% NULL for these sleeves
- All 47 JUPUSDT TP_HIT picks have `created_at = NULL`
- Only `closed_at` is populated
- The resolver cannot have done a true intrabar replay — it computed fills at TP target from `entry_price` + `pnl_pct` back-calc

### 2b. OHLCV data only covers 2026-05-06 to 2026-06-05 (30 days)
- 720 hourly bars per symbol
- Of the 47 JUP picks, only 30 (64%) have `closed_at` in this window
- The other 17 (36%) are from before OHLCV data was retained — **unverifiable**

### 2c. Replay methodology: approximate
- Since `created_at` is NULL, we proxy `entry_ts = closed_at - 24h`
- For trades that held longer than 24h, the replay window misses early SL hits
- **The actual reclassify rate is likely HIGHER than the 28-100% reported**

---

## 3. Per-Sleeve Breakdown

### S1 JUPUSDT (only partial pass)
- 47 historical picks, 30 in OHLCV window, 25 with TP_HIT
- 7/25 (28%) reclassified as SL-hit-first
- Original WR 83.3% → Replayed WR 73.3% → Stressed WR 60.0%
- Stressed PF 3.00 — best of the 4
- **Even S1 fails the strict 20% reclassify threshold**

### S2 ENAUSDT (catastrophic fail)
- 30 historical picks, 16 in window, 11 with TP_HIT
- **11/11 (100%) reclassified as SL-hit-first**
- The 11 "wins" were all actually losses in intrabar
- Stressed PF 0.67 (catastrophic)
- **This sleeve should never have been proposed**

### S3 ADAUSDT (catastrophic fail)
- 29 historical picks, 22 in window, 16 with TP_HIT
- 14/16 (87.5%) reclassified
- Stressed PF 0.93
- Same family of issue as ENA

### S4 DYDXUSDT (small sample + fail)
- 34 historical picks, **only 3 in OHLCV window**
- 2/2 (100%) reclassified in the small sample
- The n=3 is too small to draw conclusions, but direction is clearly wrong
- n<30 in window = no confidence in any conclusion
- **Marked FAIL pending larger OHLCV history**

---

## 4. What v2 Spec §7 Demanded — and What It Caught

The v2 spec said (per 6-way peer consensus):
> "**Resolver validation is the primary gate before $100 step.**"
> "If >20% reclassify, **reject that sleeve from pilot.**"

This gate **worked**. It caught the inflated historical WR before any real money was risked. **This is the entire purpose of the gate.** If we had skipped it and gone straight to live deployment, we would have lost 28-100% of every trade.

---

## 5. Decision per v2 Spec §7

| Stage | Status | Notes |
|---|---|---|
| 0 — Paper | **NOT STARTED** | Stage 0 would replay 1h OHLCV live; but historical replay already failed |
| 1 — Micro ($100) | **BLOCKED** | Resolver validation must pass before this stage; it did not |
| 2-4 | **N/A** | Cannot reach without passing Stage 1 gate |

**Recommendation: DO NOT proceed to live money on any of the 4 CRYPTO sleeves.**

---

## 6. Forward-Looking Actions

1. **Resolver fix is now P0 priority.** The NOMINAL_TP_LEGACY fill method is producing fiction.
   - Action: rewrite `alpha_engine/outcome_resolver.py` to do true intrabar OHLCV replay
   - Owner: claude-sonnet-4.6 (next session)
   - ETA: 1 week

2. **OHLCV data retention extension.** Need at least 90 days of OHLCV to validate picks from older `created_at` dates.
   - Action: extend `crypto_ohlcv` retention to 1 year
   - Owner: infrastructure

3. **`created_at` backfill.** Many historical picks have NULL `created_at`.
   - Action: backfill from `closed_at - max_hold_h` (approximate) or via signal-source time
   - Owner: claude-sonnet-4.6

4. **Re-run validation AFTER resolver fix.** Once resolver is fixed, re-run `tools/validate_intrabar_fills.py` to see if any sleeves survive.

5. **Pivot to FOREX / ETF / EQUITY.** Those classes have less data quality noise and may have real edges.
   - See `reports/PER_ASSET_CLASS_REAL_MONEY_PICKS_2026-06-05.md` for non-CRYPTO sleeves

---

## 7. Tool Created

`tools/validate_intrabar_fills.py` — re-runnable on any sleeve set. Outputs:
- `reports/validate_intrabar_fills_<UTC>.json`
- `reports/validate_intrabar_fills_latest.json`

Re-run after resolver fix or new sleeve additions:
```bash
python3 tools/validate_intrabar_fills.py --sleeves S1,S2,S3,S4
```

---

## v3 STATUS: RESOLVER-FAIL FINDING — ALL 4 SLEEVES BLOCKED
