# Backtest Admissibility Standard (M-108)

**Effective:** 2026-06-02  
**Owner:** Quant research / audit pipeline  
**Replaces:** ad-hoc promotion from `real_data_backtest.py` or raw leaderboard PF alone.

Every strategy sleeve must pass **all stages** before capital sizing or scanner merge (except explicit shadow mode).

---

## Stage 0 — Pre-registration (M-107)

- Register in `reports/hypothesis_registry.json` **before** first OHLCV run.
- Kill on confirmed leakage (e.g. H-001 COT commercial timing).

## Stage 1 — Real data only

| Class | Primary chain | Forbidden |
|-------|---------------|-----------|
| CRYPTO | Binance mirrors → CoinGecko → KuCoin | Synthetic random walk |
| EQUITY/ETF | yfinance OHLCV | Closed-pick replay as "backtest" |
| FOREX carry | FRED via `tools/cache/fred_carry_rates.json` | Hardcoded rate tables without cache flag |
| COMMODITY | yfinance futures proxies | Pre-leakage COT cohorts |

## Stage 2 — Purged walk-forward + costs

**Engine:** `alpha_engine/rigorous_backtest_harness.py` (purged k-fold + embargo)  
**Fallback lab path:** `verified_strategies/walkforward_suite.py` (70/30 OOS, costed)

Report IS/OOS: PF, WR, n, max DD **after** per-class costs:

| Class | Round-trip cost (default) |
|-------|---------------------------|
| CRYPTO | 10 bps + 5 bps slippage |
| EQUITY/ETF | 4 bps |
| FOREX | 2–5 bps |
| COMMODITY/FUTURES | 5 bps |

**Gate:** OOS PF ≥ 1.2, OOS n ≥ 10 (lab); full harness min n ≥ 30 for promotion.

## Stage 3 — Multiple-testing correction

- **DSR** ≥ 0.90 (Tier-2) / 0.95 (Tier-1) — conservative `n_trials` = all variants ever tested.
- **PBO** ≤ 0.10 (Tier-2) / 0.05 (Tier-1).
- **SPA/Reality Check** when ≥2 strategies compete per class.

Implementation: `rigorous_backtest_harness.py` (`run_backtest()`).

## Stage 4 — Robustness

- **Block bootstrap** on trade PnL (not i.i.d. shuffle) — required before Tier-1.
- Regime split: trend × vol; min 30 trades per cell or fail.

## Stage 5 — Forward virtual book (mandatory for scanner merge)

**Engine:** `verified_strategies/paper_pilot/pilot_virtual_book.py`

Promotion only if **all**:

- forward n_closed ≥ 100  
- forward PF ≥ 1.5  
- forward WR ≥ 50%  
- forward PF ≥ 0.85 × lab OOS PF  

**Tool:** `tools/pilot_forward_dashboard.py` → `reports/pilot_forward_dashboard.json`

## Stage 6 — Live shadow → sized capital

1. Opt-in env flag (default OFF) in `production_scanner.py`  
2. 30d shadow log without merge  
3. 0.1% sizing cap  
4. Scale only if `money_ready_verdict.py` flips class to READY  

---

## Sizing tiers (harness)

| Tier | PF | WR | n | DSR | PBO | MDD |
|------|-----|-----|---|-----|-----|-----|
| T1 | ≥2.0 | ≥55% | ≥30 | ≥0.95 | ≤0.05 | ≤10% |
| T2 | ≥1.5 | ≥50% | ≥30 | ≥0.90 | ≤0.10 | ≤20% |
| T3 | ≥1.2 | ≥48% | ≥20 | ≥0.80 | ≤0.20 | ≤30% |
| shadow | below T3 | | | | | |

---

## Trust hierarchy (where to look for edge)

```
1. policy_clean money_ready_verdict     ← ONLY surface for real-money sizing
2. verified_strategies lab + WF         ← promotion candidates
3. paper_pilot forward (n≥100)          ← gate before scanner merge
4. ai-tournament / pf.html              ← separate universe; paper only
5. pick_funnel cells / nav matrix       ← discovery; many DISPUTED
```

**Never size from:** raw `by_asset_class_raw`, Smart Picks nav cell without policy-clean confirmation, tournament pf_ci_lo on n<30.

---

## Commands

```bash
# Unified admissibility + edge map (writes audit JSON)
python3 tools/strategy_admissibility_report.py --write

# Rigorous harness (single strategy or batch)
python3 alpha_engine/rigorous_backtest_harness.py --class CRYPTO --batch

# Lab walk-forward
VERIFY_SKIP_FRED=1 python3 verified_strategies/walkforward_suite.py

# Forward pilots + dashboard
python3 tools/run_verified_pilots_daily.py
python3 tools/pilot_forward_dashboard.py

# Live money-ready verdict
python3 alpha_engine/money_ready_verdict.py --json
```

---

## Known engine gaps (2026-06-02)

| Engine | Classes | WF | DSR/PBO | Costs |
|--------|---------|-----|---------|-------|
| `rigorous_backtest_harness.py` | All (PnL series) | Purged | Yes | Yes |
| `walkforward_suite.py` | Verified sleeves | 70/30 OOS | No | Yes |
| `real_data_backtest.py` | 25/31 academic | **No** | **No** | **No** |
| `walk_forward_backtester.py` | CRYPTO academic | Partial | Partial | Partial |

**Action:** Route all new academic adapters through Stage 2 harness before production wiring.

**Audit reference:** `reports/backtesting_methodology_audit_2026-06-02.md`  
**Root-cause review:** `reports/quant_strategy_root_cause_review_2026-06-02.md`
