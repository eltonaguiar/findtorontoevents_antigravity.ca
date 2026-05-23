# Weekly Real-Money Filter — 2026-05-16

**Dashboard freshness:** 2026-05-16T04:04Z (1h old — OK)
**Source:** `audit_dashboard/data/dashboard_data.json` + `alpha_engine/data/active_picks.json`
**Script:** `python tools/weekly_filter_picks.py --output reports/weekly_picks_2026-05-16.json`

---

## TODAY'S LIVE ELITE PICKS

| Symbol | Class  | Dir  | Conf | RR  | System               | Alloc | Entry     |
|--------|--------|------|------|-----|----------------------|-------|-----------|
| JNJ    | EQUITY | LONG | 0.70 | 2.0 | multi_asset_copytrader | 2.97% | live      |

*1 pick passed the elite filter (confidence≥0.65, RR≥2.0, elite system only) out of 152 active picks.*

---

## Per-Class Verdict & Weekly Filter

### COMMODITY — **Tier 1 ✅ INVEST NOW**

**Stats:** PF=2.57, WR=62.6% (post-resolver-v2)
**Best system:** `multi_asset_cot` — PF=4.72, WR=79.4%, n=131, MDD=79.97%\*

**Weekly filter:**
- source_system = `multi_asset_cot` OR `multi_asset_copytrader`
- confidence ≥ 0.65
- risk_reward ≥ 2.0
- direction = follow model signal (no bias)

**Kelly sizing (PF-implied RR, Quarter-Kelly):**
| System | f\* | Quarter-Kelly | MDD-adj | Per-pick alloc (\$10k) |
|--------|-----|--------------|---------|----------------------|
| multi_asset_cot | 0.626 | 15.64% | **5.16%** | **\$516** |
| multi_asset_copytrader | 0.450 | 11.25% | **3.71%** | **\$371** |

*\*MDD is portfolio-level across all classes, not COMMODITY-specific. Per-pick alloc already reduced 67% for MDD>40%.*

**How to apply on /audit:**
1. Go to `findtorontoevents.ca/audit`
2. Filter: Asset Class = COMMODITY
3. Filter: Source System = `multi_asset_cot` (or `multi_asset_copytrader`)
4. Take picks with confidence ≥ 0.65 and RR ≥ 2.0
5. Size each at 5.16% of portfolio (or 3.71% for copytrader picks)

**Expected edge (historical):** WR ~73%, PF ~3.9 on the combined filter bucket (n=131+162)

---

### EQUITY — **Tier 2 ✅ INVEST (elite filter)**

**Stats:** PF=1.56, WR=51.5% (class-wide). Elite filter raises to WR~69%, PF~4.2
**Best system:** `aggregated_picks` — PF=5.35, WR=76.3%, n=388, MDD=88.05%\*

**Weekly filter:**
- source_system = `aggregated_picks` OR `multi_asset_copytrader`
- confidence ≥ 0.65, risk_reward ≥ 2.0
- asset_class = EQUITY

**Kelly sizing:**
| System | Per-pick alloc (\$10k) |
|--------|----------------------|
| aggregated_picks | **\$512** (5.12%) |
| multi_asset_copytrader | **\$371** (3.71%) |

**This week's confirmed pick:**
- **JNJ** (LONG, conf=0.70, RR=2.0) via `multi_asset_copytrader` → size **\$371** at \$10k account

**How to apply on /audit:**
1. Filter: Asset Class = EQUITY, Source = `aggregated_picks` or `multi_asset_copytrader`
2. Confidence ≥ 0.65, RR ≥ 2.0
3. Size per table above. Exit at TP (do not override SL).

---

### CRYPTO — **Sub-floor class-wide, Tier 1 elite-only ⚠️**

**Stats (class-wide):** PF=1.31, WR=46.5%
**Elite systems:** `signal_validation` (PF=4.70, MDD=8.14%), `kimi_signal_tracking` (PF=5.43, MDD=4.0%)

**Weekly filter (SMALL ALLOCATION — building sample):**
- source_system = `signal_validation` OR `kimi_signal_tracking` OR `ml_crypto_pred_v12`
- confidence ≥ 0.70 (tighter due to class noise)
- risk_reward ≥ 2.0
- asset_class = CRYPTO

**Kelly sizing (thin-n penalty — halved until n≥100):**
| System | n today | Per-pick alloc (\$10k) |
|--------|---------|----------------------|
| signal_validation | 64 | **\$586** (5.86%) — HALVED (thin-n) |
| kimi_signal_tracking | 20 | **\$765** (7.65%) — HALVED (thin-n) |
| mega_mutation | 165 | **\$285** (2.85%) — MDD-adjusted |

**Promotion tracker:**
- `signal_validation` needs **36 more picks** to cross the 100-pick charter floor → estimated 9-12 weeks at current emission rate. When promoted: remove thin-n halving, allocation doubles.
- `kimi_signal_tracking` needs **80 more picks** → 20+ weeks. Priority: wire to emit more signals.

**How to apply on /audit:**
1. Filter: Asset Class = CRYPTO, Source = `signal_validation`
2. Confidence ≥ 0.70, RR ≥ 2.0
3. Cap each position at 5.86% of account (increase to 11.7% when n≥100)

---

### FOREX — **DO NOT SIZE (Mutation Protocol Active) ❌**

**Stats:** PF=0.86, WR=54.7%
**Gate:** `is_forex_sizing_allowed()` in `risk_policy_check.py` — currently BLOCKS when PF<0.80. Current PF=0.86 technically clears the 0.80 floor but remains far below Tier 2 (PF≥1.5).

**Directional analysis:**
- The sub-floor drag (`rapid_fire` PF=0.78 n=264, `multi_asset` PF=0.34 n=252) poisons the FOREX class-wide stats.
- Elite FOREX systems (`signal_validation` PF=4.70, `kimi_signal_tracking` PF=5.43) DO have Tier 1 edge.
- **Recommended action:** raise `FOREX_SIZING_PF_FLOOR = 1.0` until class-wide PF recovers, then lower back to 0.8 once n_elite ≥ 100.

**Mutation plan (30-day):**
1. Week 1-2: Stop routing `rapid_fire` + `multi_asset` to FOREX. Redirect to monitoring-only.
2. Week 3-4: Collect 50+ filtered FOREX picks from `signal_validation` + `kimi_signal_tracking`
3. Day 30: Re-evaluate class-wide PF. If ≥1.5 → reinstate sizing.

---

### ETF — **Developing (PF 1.32, WR 57%) ⏳**

**Stats:** PF=1.32, WR=57.0%, n=107
**Issue:** WR is above 50% but PF is below 1.5 — average loss exceeds average win relative to frequency. Need RR≥2.5 filter.

**Weekly filter (micro allocation):**
- source_system = `aggregated_picks` (ETF picks only)
- confidence ≥ 0.75 (tighter)
- risk_reward ≥ 2.5 (higher bar to fix win/loss asymmetry)
- asset_class = ETF
- SPY 20d return ≥ 0% for LONG picks (from `alpha_engine/data/spy_20d_return.json`)

**Current SPY 20d return:** 0.0% (stub — workflow runs daily at 06:00 UTC)

**Kelly sizing:** Not computed — insufficient n at the 2.5 RR filter. Accumulate 50+ picks first.

---

### BOND — **Insufficient Data ❌**

n=11 (6W/5L), PF=0.66. No statistical basis. Do not allocate.

---

## Risk Controls (ALL picks)

| Control | Setting | Mechanism |
|---------|---------|-----------|
| Per-pick max | See table per class | Kelly Quarter-fraction + MDD adjustment |
| Daily soft-stop | -2% total daily PnL | Hyro overlay (`HYRO_RISK_SIZER_ENABLED=1`) |
| Portfolio DD halt | rolling 30d DD > 30% | `KELLY_DD_HALT_ENABLED=1` |
| FOREX hard-cap | PF < 0.80 → 0 size | `risk_policy_check.py::is_forex_sizing_allowed()` |
| ETF regime gate | SPY 20d ≤ 0% → no ETF LONG | `tools/fetch_spy_20d_return.py` |
| SL discipline | Always exit at SL price | Never override — model's edge depends on this |

---

## What Changed Since Last Week

- COMMODITY `multi_asset_cot` confirmed Tier 1 (PF=4.72 stable over n=131)
- EQUITY `aggregated_picks` remains the best EQUITY system (PF=5.35 WR=76.3%)
- CRYPTO `signal_validation` at n=64 — 36 picks to promotion
- `alpha_engine_fast` (PF=0.62) remains the single biggest class-wide drag: 228 picks pulling CRYPTO, EQUITY, COMMODITY, FOREX all down simultaneously
- First live elite pick confirmed: JNJ LONG via `multi_asset_copytrader`

---

## How to Grow the Edge

### Priority 1 — Remove the drag (biggest PF lift)
Stopping `alpha_engine_fast`, `rapid_fire`, `super_signals` from contributing to class-wide stats would immediately lift:
- CRYPTO: 1.31 → ~2.1 estimated class PF
- EQUITY: 1.56 → ~3.5 estimated class PF
- FOREX: 0.86 → ~2.8 estimated class PF (if routed through elite systems only)

**Required action:** Investigation gate per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` before adding to kill list.

### Priority 2 — Accelerate `signal_validation` to n=100
`signal_validation` (PF=4.70, MDD=8.14%) is the best balanced system we have. At n=100:
- Qualifies for Tier 2 promotion
- Allocation doubles (thin-n penalty removed)
- Covers CRYPTO + FOREX → both classes benefit simultaneously

**Required action:** Ensure `signal_validation` workflow runs daily and emits picks.

### Priority 3 — COT data freshness for COMMODITY
`multi_asset_cot` (PF=4.72) depends on CFTC Commitment of Traders data. Verify the data pipeline is refreshing weekly (COT data releases every Friday 15:30 ET).

---

## Files Created This Session

| File | Purpose |
|------|---------|
| `reports/statistical_edge_analysis_2026-05-16.md` | Full per-class audit with system breakdown |
| `reports/weekly_filter_2026-05-16T0507Z.md` | This file — weekly actionable filter |
| `tools/weekly_filter_picks.py` | Runnable filter script (`python tools/weekly_filter_picks.py`) |

---

*NOT FINANCIAL ADVICE — research surface only. All metrics from live dashboard as of 2026-05-16T04:04Z.*
*For questions about methodology: `reports/statistical_edge_analysis_2026-05-16.md` §Kelly Sizing.*
