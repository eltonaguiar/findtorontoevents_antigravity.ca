# Weekly Real-Money Filter — 2026-05-17

**Generated:** 2026-05-17T05:21Z  
**Data source:** `audit_dashboard/data/dashboard_data.json` (age: 1.2h < 2h threshold ✓)  
**Methodology:** Quarter-Kelly (fraction=0.25) per `alpha_engine/kelly_position_sizer.py`

---

## Dashboard Snapshot (2026-05-17)

| Asset Class | n | WR | PF | Status | Real-Money? |
|-------------|---|----|----|--------|-------------|
| EQUITY | 393 | 53.2% | 1.65 | stable | ✅ YES (T2) |
| ETF | 75 | 66.7% | 2.25 | candidate | ⚠️ PAPER (n<100) |
| COMMODITY | 228 | 85.5% | 7.71 | stable | ⚠️ SHORT-only, verify |
| CRYPTO | 7563 | 47.0% | 1.32 | stable | 🔬 ELITE strategies only |
| BOND | 11 | 54.5% | 0.66 | thin_sample | 🚫 BLOCKED (n<20) |
| FOREX | 251 | 57.8% | 0.85 | watch | 🚫 HARD DISABLED |

---

## EQUITY Top Picks Filter ✅ REAL-MONEY-READY

**Performance:** WR=53.2%, PF=1.65, n=393 (T2 certified — PF>1.5, WR>50%, n>100)

**Filter criteria:**
- `asset_class = EQUITY`
- `status = OPEN`
- `direction = LONG`
- `elite_score >= 55` (quality_gates.py M-038 floor)
- `forward_validated = true` OR `trust_score >= 8`
- `confidence >= 0.55`
- Source NOT in `BLOCKED_SOURCE_SYSTEMS`

**Kelly sizing:**
- Fraction: 0.25 (quarter-Kelly per `alpha_engine/config.py::EQUITY_KELLY_FRACTION`)
- Position size: **5.2% of account per pick** ($524 at $10k account)
- Max concurrent EQUITY picks: 4 (total 20.8% exposure)

**VIX regime bonus:** +15 score when VIX<22 AND YC>0 (currently active: VIX≈14)

**Expected return per pick:** avg_win ≈ 1.45× avg_loss, PF=1.65

---

## ETF Filter ⚠️ PAPER-TRADE ONLY (n=75 < 100)

**Performance:** WR=66.7%, PF=2.25, n=75 (T1 performance, building toward stable)

**Filter criteria:**
- `asset_class = ETF`
- `status = OPEN`
- `direction = LONG`
- `score >= 60` (ETF_TIGHT_GATE=1 active — higher floor than EQUITY)
- `forward_validated = true`
- ETF_MACRO_VETO=0 (shadow mode; enable at n≥150)

**Kelly sizing (paper only):**
- Fraction: 0.25
- Indicative size: **9.3% of account** ($926 at $10k) — do NOT use for real money yet
- Await n≥100 for real-money sizing

**Accelerate n growth:** ETF scanner already covers 14 symbols (SPY, QQQ, IWM, GLD, SLV, etc.)

---

## COMMODITY Filter ⚠️ SHORT-ONLY, PAPER WHILE VERIFYING

**Gate:** M-042 COMMODITY_SHORT_ONLY=1 (blocks LONG picks — backtest PF=2.10/WR=58%, n=62)

**Performance claim:** Dashboard shows PF=7.71/WR=85.5% at n=228  
⚠️ **Inflated — needs verification.** Dashboard PF/WR includes pre-gate picks.  
**Verified edge:** SHORT-only PF=2.10/WR=58% (n=62) per `edge_filter_engine_v3.py`

**Filter criteria:**
- `asset_class = COMMODITY`
- `status = OPEN`
- `direction = SHORT` (LONG picks blocked by M-042)
- `source_system IN (multi_asset_cot, multi_asset_copytrader)` — highest PF strategies
- Exclude CT=F (PROBATION until 2026-06-06 review)

**Kelly sizing (SHORT-only verified edge):**
- Position size: **7.6% of account** ($760 at $10k) — paper only until n≥50 post-gate
- Current post-gate n≈62 (border — watch for 30 more clean SHORT picks)

---

## CRYPTO Filter 🔬 ELITE STRATEGIES ONLY

**Class-wide:** WR=47%, PF=1.32 — dragged by quan_engine (PF=0.70, 18% volume)

**Elite strategy filter (sub-class only):**
- `source_system IN (copy_trader, coinglass_whale, funding_rate_scanner)` — PF 2.34-3.97
- `direction = LONG`
- `confidence >= 0.70` (M-034 CRYPTO_CONF_INVERSION inverted from original)
- Exclude quan_engine pending autopsy (see `docs/STRATEGY_INVESTIGATION_quan_engine_2026_05_17.md`)

**Kelly sizing (elite strategies, indicative):**
- Fraction: 0.25 (conservative — class WR below 50%)
- Indicative size: **6.2% per pick** ($625 at $10k) — apply only to elite source systems
- Do NOT apply to all CRYPTO picks (class-wide edge not yet confirmed)

---

## BOND Filter 🚫 BLOCKED BY M-043

**Status:** n=11 < 20 floor — M-043 BOND_MIN_N_GATE=1 blocking all BOND picks  
**Unblock at:** n≥20 (approximately 3 picks/day → ~3 days from now)  
**Performance:** WR=54.5%, PF=0.66 at n=11 — PF below T2; wait for n≥30

---

## FOREX Filter 🚫 HARD DISABLED

**Status:** FOREX_HARD_DISABLE=1 — class PF=0.85 despite WR=57.8% (TP/SL ratio issue)  
**Rehabilitation path:** `tools/research/forex_carry.py` — G10 carry scaffold  
**Unlock condition:** 30-trade rolling WR>50% AND PF>1.0 post-carry filter

---

## How to Apply This Filter

1. Open `findtorontoevents.ca/audit`
2. Apply filter: `Asset Class = EQUITY`, `Status = OPEN`, `Direction = LONG`
3. Sort by `elite_score DESC`
4. Size per Kelly: 5.2% of account per EQUITY pick
5. Maximum 4 concurrent EQUITY picks (20.8% total exposure)
6. Exit: follow TP/SL as set on each pick

---

## Risk Controls

| Control | Value | Gate |
|---------|-------|------|
| Max per-pick (EQUITY) | 5.2% = $524 at $10k | Kelly 0.25-fraction |
| Max per-pick (ETF, paper) | 9.3% = $926 | Indicative only |
| Daily soft-stop | −2% total PnL | Hyro overlay |
| DD halt | Rolling 30d drawdown > 30% | `compute_position_size()` DD guard |
| VIX hard stop | VIX > 25 blocks new EQUITY picks | M-045 (enable with EQUITY_VIX_FILTER=1) |

---

## Gates Active (2026-05-17)

| Gate | Default | Status |
|------|---------|--------|
| M-041 SWARM_TIER_GATE | ON | Blocks single-tier swarm picks |
| M-042 COMMODITY_SHORT_ONLY | ON | LONG commodity blocked |
| M-043 BOND_MIN_N_GATE | ON | BOND blocked until n≥20 |
| M-044 CRYPTO_MIN_TRADE_AGE | OFF | Skeleton only |
| M-045 EQUITY_VIX_FILTER | OFF | Shadow — enable with EQUITY_VIX_FILTER=1 |
| ETF_TIGHT_GATE | ON | Score floor 60 for ETF |
| FOREX_HARD_DISABLE | ON | Class-wide FOREX blocked |
| VIX_YC_SCORE_BONUS | ON | +15 EQUITY bonus (VIX=14, favorable) |

---

## User Action Required

| Action | Impact | Priority |
|--------|--------|----------|
| `EQUITY_VIX_FILTER=1` in prod `.env` | Protect EQUITY in VIX spikes | P2 (enable now, VIX=14 = no impact) |
| PA console: check `UEPS_ENABLE_PEAD=1` | PEAD earnings-momentum feed | P1 |
| PA console: MySQL ghost-row purge | 655k stale rows in ejaguiar1_stocks | P2 |
| 2026-05-24: `python tools/mutation_analysis.py` on quan_engine | CRYPTO drag investigation | P1 |
| 2026-06-06: CT=F PROBATION review | COMMODITY Tier 1 unlock | P1 |

---

*Produced by Claude Code (claude-sonnet-4-6) via `/money-maker-readyv2` protocol*  
*Source data: `audit_dashboard/data/dashboard_data.json` + `alpha_engine/kelly_position_sizer.py`*
