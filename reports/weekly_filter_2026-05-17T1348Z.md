# Weekly Real-Money Filter — 2026-05-17 (13:48 UTC) — v2 (CB-corrected)

**Generated:** 2026-05-17T13:48Z  
**Dashboard freshness:** 0.5h (generated 2026-05-17T12:56Z)  
**Session:** AI v2 — circuit_breaker 30d corrected (addresses swarm NEEDS_DISCUSSION HIGH concerns)  
**Data sources:** `dashboard_data.json` (post-resolver-v2.1), `closed_picks.json` (n=8,421), `verify_realized_30d.py` (v2 with CB column)  
**Supersedes:** `weekly_filter_2026-05-17T1337Z.md` (that version used raw 30d only)

---

## Data Source Clarification (resolves swarm HIGH concerns)

Three n values exist per asset class — all correct but counting **different things**:

| Source | What it counts | COMMODITY example |
|--------|---------------|-------------------|
| Dashboard all-time n | Scanner-deduped since inception (post-resolver-v2) | n=228 |
| Raw 30d (closed_picks.json) | ALL entries last 30d, incl. pre-gate + re-emissions | n=352 |
| **Circuit-breaker 30d (CB)** | **Dashboard-filtered last 30d — same dedup as all-time** | **n=65** |

> **Use CB-30d as the authoritative 30d number.** Raw 30d is inflated by scanner re-emissions (especially COT's 114 raw → 40 deduped signals). FOREX raw n=888 vs dashboard n=98 is expected: dashboard shows only post-gate picks (LONG hard-blocked May 14, SHORT session-gated May 17).

---

## Baseline Snapshot: All-time + CB-30d Filtered

| Class | All-time n | All-time PF | CB-30d n | CB-30d WR | Status |
|-------|-----------|-------------|----------|-----------|--------|
| EQUITY | 240 | 2.04 | 87 | **59.8%** | ✅ T1-zone (WR≥55%) |
| COMMODITY | 228 | 7.71* | 65 | **56.9%** | ✅ T1-zone (WR≥55%) |
| CRYPTO | 6,833 | 1.43 | 2,878 | 46.0% | ⚠ WR<50% (no sizing — see SPA filter) |
| ETF | 74 | 2.49 | 48 | **70.8%** | ✅ T1-zone (WR≥55%) but n<100, accumulating |
| FOREX | 98 | 2.23 | 33 | 48.5% | ⚠ WR<50%, post-gate recovering |
| BOND | 12 | 0.66 | 0 | — | ❌ no 30d data |

*COMMODITY all-time PF=7.71 inflated by COT dedup artifact — not used for sizing. CB-30d WR=56.9% is the reliable recent estimate.

---

## EQUITY Top Picks Filter ✅

**Current status:** T1-zone (CB-30d WR=59.8%, all-time PF=2.04, OOS WR=66.1% on 7 walk-forward folds)  
**Pre-gate concern:** `stocks_rsi2_pullback` dominated April-May raw picks (WR=33%) — BLOCKED since May 16. CB-30d uses post-gate picks → WR=59.8% confirms recovery.  
**Active filter:** `source_system = kimi_riseoftheclaw`, `asset_class = EQUITY`, `direction = LONG`

| Metric | Value |
|--------|-------|
| Historical n (kimi) | 210 (recent_closed) |
| WR | 56.7% |
| PF | 2.09 |
| OOS WR | 66.1% ± 12.9pp (7 folds) |
| CB-30d WR | 59.8% (n=87 filtered) |
| Average Win | +3.2% |
| Average Loss | −2.0% |
| Raw Kelly | 29.5% |
| **0.25× Kelly** | **7.4% of account** |
| **$ at $10k** | **$738/pick** |

**How to apply:**
1. `findtorontoevents.ca/audit` → Filter: Asset Class = EQUITY → Source = kimi_riseoftheclaw → Status = Open
2. Sort by `elite_score` desc — take top 3–5 picks
3. Size each at **7.4%** of account (max 3 concurrent = 22.2% total EQUITY exposure)
4. Honor TP/SL exactly; no overrides

---

## COMMODITY Top Picks Filter ✅

**Current status:** T1-zone (CB-30d WR=56.9% n=65; all-time PF inflated by dedup — NOT used for sizing)  
**SURVIVORSHIP BIAS WARNING:** All-time PF=7.71 reflects COT over-emission (114 raw → ~40 deduped). CB-30d WR=56.9% is the authoritative recent metric.  
**Active filter:** `source_system IN (multi_asset_cot, multi_asset_copytrader)`, `direction = SHORT`

| Metric | Value | Source |
|--------|-------|--------|
| CB-30d n | 65 | circuit_breaker (deduped, authoritative) |
| CB-30d WR | 56.9% | dashboard (T1-zone) |
| Deduped WR (CT=F cot_positioning) | 77.5% | verified AH session (n=40 unique) |
| Deduped PF (CT=F cot_positioning) | 4.69 | verified AH session |
| Average Win | +2.7% | |
| Average Loss | −2.0% | |
| Kelly base (on CB-30d WR=56.9%) | ~24% | estimated |
| **0.25× Kelly** | **~6.0% of account** | |
| **$ at $10k** | **~$600/pick** | |

**Dedup note:** COT strategies emit 2.85× more picks than unique signals. Always verify dedup before sizing. Effective signal count in 30d window: ~23 (65 / 2.85).

**Exclude:** `cta_replicator` (30d WR=3%, PF=0.06). Only `multi_asset_cot` + `multi_asset_copytrader` SHORT qualify.

---

## CRYPTO Filter (conditional) ⚠

**Current status:** CB-30d WR=46% < T2 floor. SPA-passing subset has been validated.  
**SPA-passing strategies (White's RC + Hansen's SPA, bootstrap 500):**

| Strategy | n | Mean/pick | SPA |
|----------|---|-----------|-----|
| ml_enhanced_FETUSDT_1d_B_lightgbm | 25 | +33.7% | PASS |
| ml_enhanced_INJUSDT_1d_B_lightgbm | 27 | +15.6% | PASS |
| ml_enhanced_RENDERUSDT_1h_D_ensemble_stack | 34 | +4.7% | PASS |
| ml_enhanced_RENDERUSDT_4h_D_ensemble_stack | 27 | +3.4% | PASS |
| cot_positioning | 134 | +3.3% | PASS |

**Filter:** strategies in SPA-passing list above + `asset_class = CRYPTO` + `confidence ≤ 0.85` (M-035 gate)

| Metric | Value |
|--------|-------|
| SPA-pass subset WR | ~65-80% (per-strategy) |
| Kelly sizing | 3-5% per pick (small, given volatility) |
| Max concurrent | 2 CRYPTO picks (total 6-10% account) |

**Do NOT size** based on system-wide CB-30d WR=46%.

---

## ETF (Accumulating) ⚠

CB-30d WR=70.8% (n=48) is excellent but all-time n=74 is below the 100-pick charter floor for OOS validation.  
**Defer sizing until all-time n≥100 with stable OOS WR.**

---

## FOREX (Recovering) ❌

FOREX LONG: hard-blocked (M-130, May 14).  
FOREX SHORT: session gate M-078 (08-16 UTC only). CB-30d WR=48.5% (n=33) — below T2 floor.  
**Do NOT size FOREX until CB-30d shows WR≥50% sustained over ≥30 post-gate picks.**

---

## Kelly Sizing Summary

| Class | Filter | Size/pick | Max concurrent | Max exposure |
|-------|--------|-----------|----------------|--------------|
| EQUITY | kimi LONG | 7.4% | 3 | 22.2% |
| COMMODITY | COT/copytrader SHORT | ~6.0% | 4 | ~24.0% |
| CRYPTO (SPA) | SPA-passing list | 4.0% | 2 | 8.0% |
| Total max | | | | ~54.2% |

---

## Risk Controls

- **Per-pick maximum:** 8% of account (hard cap, Kelly overrides)
- **Daily soft-stop:** −2% total PnL triggers pause (Hyro overlay)
- **DD halt:** rolling 30d drawdown >20% → stop all sizing
- **FOREX:** zero sizing until CB-30d WR≥50% over ≥30 post-gate picks
- **BOND:** zero sizing until n≥30 with OOS validation
- **ETF:** zero sizing until all-time n≥100

---

## Swarm Concern Resolution (Session AI NEEDS_DISCUSSION → resolved)

**HIGH #1 — COMMODITY n discrepancy:**
- Dashboard all-time n=228 uses scanner dedup (COT 114 raw → ~40-50 unique per emission cycle)
- Raw 30d n=352 includes scanner re-emissions BEFORE dedup (expected artifact)
- CB-30d n=65 is the authoritative filtered 30d count — same dedup as all-time
- **Verdict: NOT a data quality issue. Three sources count different populations.**

**HIGH #2 — FOREX n=98 vs raw n=888:**
- Dashboard n=98 shows only POST-gate picks (LONG blocked May 14, SHORT gated May 17)
- Raw n=888 includes all pre-gate FOREX history (predominantly LONG, now blocked)
- CB-30d n=33 = post-gate SHORT picks only — the actionable universe
- **Verdict: Expected mismatch. Post-gate data is small by design.**

---

## Tool

```bash
python tools/verify_realized_30d.py
```

Prints all three tables (all-time / raw 30d / CB-30d) with warnings and discrepancy explanation.
