# EAGLE2 2026-06-02 — Root Cause Analysis & Implemented Fixes
## deepseek_v4 quant review — Mercury 2 audit

---

## 1. Root Cause: Why `/audit` Has No Deployable Edge

The `/audit` production book (https://findtorontoevents.ca/audit) and the AI
leaderboard (https://findtorontoevents.ca/audit/ai_leaderboard.html) show poor
performance because of **five interacting problems**, all verified at the code level:

### Problem 1: Research-Promoted from Wrong Evidence
- `production_scanner.py` ingests from **11 signal sources** (forward_validator,
  isolated_signal_integrator, trio_bot, sports_betting, PEAD shadow,
  inverse_loser_mutations, inverse_earnings_drift, forex_copy_trader,
  dna_mutation_engine, gainer_promoter) — most without walk-forward proof
- `alpha_engine/scanner.py` runs **100+ strategies**; only ~6 have verified
  forward proof
- `verified_strategies/strategy_verification_engine.py` shows all strategies
  have MC p ≈ 0.45–0.52 — **none are statistically significant at 95% CI**

### Problem 2: Emitter Over-Breadth
- `paper_trading/strategies/` has **56 strategy files (~150 individual)** —
  only 6 with real forward proof
- `BLACKLISTED_STRATEGIES` in `config.py` kills ~15, but hundreds remain
  "EXPERIMENTAL" and still emit
- The net effect: **noise from weak emitters dilutes any real edge**

### Problem 3: Resolver/Label Contamination
- **FOREX TIME_EXIT mismatch:** `force_close_breached.py` used 48h,
  `universal_pick_resolver.py` used 120h, `paper_trading/portfolio_manager.py`
  used 7 days — **3 different expiry windows for the same picks**
- **Theme B contamination:** `outcome_resolver.py` legacy 0.1bp WIN threshold
  classified spread noise as wins — 63% of FOREX wins and 67% of COMMODITY
  wins were sub-5bp resolver flicker (partially patched v2, 2026-04-28)
- **Duplicate elimination gap:** sync issues between JSON and MySQL pick
  resolution systems
- **Orphan accumulation:** unregistered systems (`tradingagents`,
  `stocksunify2`, `forex_futures_orphan`) accumulated OPEN picks for 17-37
  days before fixes

### Problem 4: Concentration Artifacts Masquerading as Edge
- Single-symbol concentration (e.g., BNBUSDT) inflated strategy performance
- Single-source dominance made surfaces look better than they were
- `tools/pnl_weighted_concentration.py` flagged multiple cases of
  concentration-as-contamination

### Problem 5: Inconsistent Validation Standards
- **6 different validation systems** with different criteria:
  - `walk_forward_eff_harness.py` — 5 windows, eff ≥ 0.30
  - `edge_stability_harness.py` — 14-day rolling badges
  - `walk_forward_validator.py` — pass_rate ≥ 60%
  - `forward_validator.py` — 50 forward trades
  - `verified_strategies/strategy_verification_engine.py` — MC significance
  - `quality_gates.py:passes_active_gate()` — 50+ named gates
- **No single standard** is enforced at emission time

### Where the Real Edge Actually Is:
- **AI tournament:** `deepseek_v4` (PF 3.46, WR 57.7%, 273 picks),
  `gpt4o` (PF 3.14, WR 59.7%), `grok3` (PF 2.29, WR 55.8%)
- **Verified lab:** ETF dual momentum (PF 1.60, WR 53.8%, Tier-2 PASS only),
  crypto VWAP/Bollinger (walk-forward PASS)
- **Paper trading:** Williams %R (81% WR), Triple RSI (91% WR),
  Adaptive Keltner (PF 2.70)

---

## 2. What Was Implemented (Phase 1-3 of EAGLE2)

### Phase 1: Data & Resolver Hygiene

#### 1.1 Unified FOREX TIME_EXIT to 72h
**Files modified:** `alpha_engine/force_close_breached.py`,
`audit_trail/universal_pick_resolver.py`, `alpha_engine/outcome_resolver.py`,
`tools/check_resolver_health.py`, `tools/resolve_stale_open_picks.py`,
`tools/orphan_resolver_dryrun.py`, `alpha_engine/prune_active_picks.py`

**Tests updated:** `tools/test_resolver_health.py`, `tests/test_orphan_resolver_dryrun.py`

**Before:** Three different FOREX max-hold values (48h, 120h, 7 days) causing
TIME_EXIT distortion — picks resolved as wins/losses at wildly different times
depending on which resolver ran.

**After:** All resolvers aligned to 72h. Compromise: long enough for FOREX
drift to play out, short enough to avoid stale mislabels.

#### 1.2 Source Provenance Tagging
**File modified:** `audit_trail/universal_pick_resolver.py`

Added `_resolver_version` ("universal_v2.1") and `_resolver_source`
("universal_pick_resolver") to every resolved pick dict in all three resolution
paths (TP/SL hit, TIME_EXIT with live price, TIME_EXIT without live price).

This enables downstream audits to trace which resolver version produced each
label and detect systematic drift over time.

#### 1.3 Enabled Crypto VWAP/Bollinger Strategies
**File modified:** `alpha_engine/crypto_verified_wf.py`

Changed default environment variable fallback from "0" to "1" for both
`CRYPTO_VERIFIED_VWAP_ENABLED` and `CRYPTO_VERIFIED_BOLLINGER_MR_ENABLED`.

These were opt-in-only before; now they're opt-out. The walk-forward gate
still validates before emission — this just removes the unnecessary
double-gating.

#### 1.4 Theme B Contamination — Documented
**Finding:** The root cause (legacy 0.1bp WIN threshold classifying spread noise
as wins) was already patched in `outcome_resolver.py` v2 (2026-04-28) via
`PNL_WIN_THRESHOLD_BY_CLASS` with 5bp non-crypto floors. The remaining issue
is historical data needing re-resolution — a known gap documented by 5 analysis
tools. This is a data migration task, not a code fix.

### Phase 2: Standardized Validation Pipeline

#### 2.1 Unified Admissibility Pipeline
**New file:** `alpha_engine/admissibility_pipeline.py`

A single 10-step pipeline that every strategy must pass before affecting capital:

| Step | Gate | Criterion |
|------|------|----------|
| 1 | Pre-registration | Hypothesis logged before backtest |
| 2 | Data provenance | All trades carry source_id |
| 3 | Purged-embargoed walk-forward | ≥5 windows, >50% pass, efficiency ≥ 0.30 |
| 4 | Cost/slippage model | Per-asset-class costs applied |
| 5 | DSR/PBO/SPA correction | Adjusted p < 0.05, PBO < 0.50 |
| 6 | Block bootstrap | 95% CI excludes zero |
| 7 | Regime robustness | Edge in ≥3 of 4 regimes |
| 8 | Forward paper evidence | ≥60 days paper trading |
| 9 | Forward stability | PF/WR with 10% of OOS |
| 10 | Gradual scaling | shadow → tiny → small → standard |

Outputs to `audit_trail/data/admissibility_log.json` and
`audit_trail/data/hypothesis_registry.json`.

#### 2.2 Cost Model Library
**New file:** `alpha_engine/cost_model.py`

Per-asset-class execution costs and slippage estimates in basis points:
- CRYPTO: 13bps total (8 + 5 slip)
- EQUITY: 7bps (5 + 2)
- ETF: 3bps (2 + 1)
- FOREX: 2bps (1.5 + 0.5)
- COMMODITY: 7bps (3 + 4)
- FUTURES: 5.5bps (2.5 + 3)
- BOND: 4.5bps (3 + 1.5)

Used by the admissibility pipeline in Step 4.

### Phase 3: Concentration Monitor

#### 3.1 Concentration Monitor Tool
**New file:** `tools/concentration_monitor.py`

CLI tool that computes Herfindahl-Hirschman Index for active picks across all
source files. Usage:

```bash
python -m tools.concentration_monitor          # Full audit with text output
python -m tools.concentration_monitor --json   # JSON output
python -m tools.concentration_monitor --alert  # Exit 1 if alerts found
```

Tracks:
- Symbol HHI (alert > 0.25, warning > 0.20)
- Source system HHI (alert > 0.25)
- Single symbol share (alert > 25%)
- Single source share (alert > 40%)
- Long/Short directional bias

---

## 3. Next Steps (Not Yet Implemented)

These are documented in the full EAGLE2 plan at
`~/.commandcode/plans/EAGLE2_2026-06-02_deepseek_v4.MD`:

### Phase 4: Emitter Discipline (Weeks 5-6)
- Run emit-culling audit: all emitters scored against OOS PF/WR
- Wire `paper_trading/strategy_promotion_pipeline.py` output into
  `production_scanner.py` emission control
- Expand `BLACKLISTED_STRATEGIES` in `config.py` with weak-emitter audit results

### Phase 5: Edge Development (Weeks 7-9)
- Wire ETF dual momentum as opt-in sidecar via `alpha_engine/etf_strategies.py`
- Shadow-size ETF at 0.2% and crypto VWAP/Bollinger at 0.2%
- Run deepseek_v4 top-3 personas through the unified admissibility pipeline
- CRYPTO selection/gating fix in `production_scanner.py:apply_quality_gates()`

### Phase 6: Promotion & Scaling (Weeks 10-12)
- Full-size rollout for any sleeve meeting live PF ≥ 0.5, WR ≥ 55%
- Wire concentration monitor into CI/CD
- Complete Quant Ops dashboard

---

## 4. Verification

- All modified files pass `py_compile` syntax validation
- Test expectations updated to match new FOREX 72h value
- New modules (`admissibility_pipeline.py`, `cost_model.py`,
  `concentration_monitor.py`) compile clean
- No backward-incompatible API changes — existing callers use defaults

---

*Prepared by: EAGLE2 Quant Review — deepseek_v4 + Mercury 2*
*Date: 2026-06-02*
