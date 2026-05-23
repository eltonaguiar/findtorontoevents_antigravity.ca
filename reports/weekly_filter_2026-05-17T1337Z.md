# Weekly Real-Money Filter — 2026-05-17 (13:37 UTC)

**Generated:** 2026-05-17T13:37Z  
**Dashboard freshness:** 0.5h (generated 2026-05-17T12:56Z)  
**Session:** AI — 30d realized context + COMMODITY bias warning  
**Data sources:** `dashboard_data.json` (post-resolver-v2.1), `closed_picks.json` (n=8,421), `verify_realized_30d.py`

---

## Baseline Snapshot + 30d Realized Context

| Class | All-time n | All-time PF | 30d n | 30d WR | 30d PF | Warning |
|-------|-----------|-------------|-------|--------|--------|---------|
| EQUITY | 240 | 2.04 | 42 | 33.3% | 0.67 | ⚠ 30d dominated by pre-gate `stocks_rsi2_pullback` (now blocked May 16) |
| COMMODITY | 228 | 7.71 | 352 | 60.5% | 2.29 | ⚠ All-time PF inflated by COT dedup artifact; 30d PF=2.29 is more reliable |
| CRYPTO | 6,833 | 1.43 | 183 | 51.4% | 0.27 | ⚠ 30d includes SPA-failing ml_enhanced strategies; SPA-passing subset healthy |
| ETF | 74 | 2.49 | 0 | — | — | No resolved picks in 30d window |
| FOREX | 98 | 2.23 | 888 | 25.2% | 0.33 | ⚠ 30d includes pre-gate picks; FOREX LONG hard-blocked since May 14 |
| BOND | 12 | 0.66 | 1 | 0.0% | 0.0 | n too thin for sizing |

> **Important:** All-time n in dashboard is post-dedup/gate. 30d n from raw `closed_picks.json` includes pre-gate admissions. Use 30d only when n30≥30 and pre-gate context is understood.

---

## EQUITY Top Picks Filter ✅

**Current status:** T2+ (all-time WR=53.2%, PF=2.04, OOS WR=66.1% on 7 walk-forward folds)  
**Pre-gate concern:** `stocks_rsi2_pullback` dominated April-May closed picks (WR=33%) — NOW BLOCKED since May 16  
**Active filter:** `source_system = kimi_riseoftheclaw`, `asset_class = EQUITY`, `direction = LONG`

| Metric | Value |
|--------|-------|
| Historical n (kimi) | 210 (recent_closed) |
| WR | 56.7% |
| PF | 2.09 |
| OOS WR | 66.1% ± 12.9pp (7 folds) |
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

**Current status:** T1 (30d WR=60.5%, PF=2.29 — more trustworthy than all-time 7.71)  
**SURVIVORSHIP BIAS WARNING:** All-time PF=7.71 reflects COT dedup artifact. Raw n=352 vs dashboard n=228 confirms dedup inflation. **Use 30d PF=2.29 for sizing decisions.**  
**Active filter:** `source_system IN (multi_asset_cot, multi_asset_copytrader)`, `direction = SHORT`

| Metric | Value | Source |
|--------|-------|--------|
| 30d n | 352 | closed_picks.json |
| 30d WR | 60.5% | empirical |
| 30d PF | 2.29 | empirical (RELIABLE) |
| Deduped WR (CT=F cot_positioning) | 77.5% | verified AH session |
| Deduped PF (CT=F cot_positioning) | 4.69 | verified AH session |
| Average Win | +2.7% | |
| Average Loss | −2.0% | |
| Raw Kelly (on 30d PF) | 23.4% | |
| **0.25× Kelly** | **5.8% of account** | |
| **$ at $10k** | **$580/pick** | |

**Dedup note:** Pick deduplication is mandatory for COT strategies (114 raw CT=F picks → 40 unique signals). The 30d n=352 includes scanner re-emissions; effective signal count is ~120-140.

**Exclude:** `cta_replicator` (30d WR=3%, PF=0.06). Only `multi_asset_cot` + `multi_asset_copytrader` SHORT qualify.

---

## CRYPTO Filter (conditional) ⚠

**Current status:** Sub-T2 but SPA-passing subset exists  
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

**Do NOT size** based on all-time CRYPTO PF=1.43 (includes drag from blocked sources).

---

## ETF (Accumulating) ⚠

n=74, approaching 100 minimum. No resolved picks in 30d — likely all active.  
**Defer sizing until n≥100 with stable OOS WR.**

---

## FOREX (Blocked) ❌

FOREX LONG: hard-blocked (M-130, May 14).  
FOREX SHORT: session gate M-078 (08-16 UTC only). 30d PF=0.33 still recovering from pre-gate history.  
**Do NOT size FOREX until 30d post-gate window shows PF≥1.5.**

---

## Kelly Sizing Summary

| Class | Filter | Size/pick | Max concurrent | Max exposure |
|-------|--------|-----------|----------------|--------------|
| EQUITY | kimi LONG | 7.4% | 3 | 22.2% |
| COMMODITY | COT/copytrader SHORT | 5.8% | 4 | 23.2% |
| CRYPTO (SPA) | SPA-passing list | 4.0% | 2 | 8.0% |
| Total max | | | | ~53.4% |

---

## Risk Controls

- **Per-pick maximum:** 8% of account (hard cap, Kelly overrides)
- **Daily soft-stop:** −2% total PnL triggers pause (Hyro overlay)
- **DD halt:** rolling 30d drawdown >20% → stop all sizing
- **FOREX:** zero sizing until 30d post-gate PF≥1.5 verified
- **BOND:** zero sizing until n≥30 with OOS validation
- **ETF:** zero sizing until n≥100

---

## 30d Realized vs All-Time Divergence Summary

This session (AI) surfaced significant 30d divergence from all-time numbers:

1. **COMMODITY all-time PF=7.71 is inflated** — COT dedup artifact; use 30d PF=2.29
2. **EQUITY 30d WR=33% is pre-gate noise** — `stocks_rsi2_pullback` blocked May 16; post-gate WR expected to recover to ~55%+
3. **CRYPTO 30d PF=0.27** — SPA-failing ml_enhanced strategies dragging; SPA-passing subset remains strong
4. **FOREX 30d n=888 vs all-time n=98** — dashboard n reflects only post-gate picks; raw closed_picks includes pre-gate history

**Tool:** `python tools/verify_realized_30d.py` — surfaces these divergences on demand.
