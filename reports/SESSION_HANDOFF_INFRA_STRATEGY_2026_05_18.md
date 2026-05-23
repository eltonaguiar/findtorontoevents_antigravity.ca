# Session Handoff — Infra Fragility + Strategy State (2026-05-18)

**Author:** Claude Opus 4.7. Consolidates `reports/infra_fragility_audit_2026_05_18.md`,
`MASTER_ENHANCEMENT_PLAN_2026_05_18.md`, `ROADMAP_TO_EDGE_2026-05-18.md`, and the
canonical `audit_dashboard/data/pf_registry.json` (gen 2026-05-18T06:32Z).
Purpose: a single fresh-session pickup doc + the input brief for the strategy-review swarm.

---

## 1. Authoritative posture (read first)

Research sandbox / **paper-only. Real capital = $0.** 7–8 straight `edge_stability_harness`
kills. No asset class is money-ready. Verdict-grade numbers = `pf_registry.json`
policy-clean-net, NOT the inflated `/audit` tiles.

### Canonical per-class PF (pf_registry, policy-clean, gross)

| class | n | WR % | PF | verdict |
|-------|---|------|-----|---------|
| EQUITY | 33 | 33.3 | 0.60 | no edge / insufficient data (resolver placeholders) |
| COMMODITY | 173 | 42.2 | 1.11 | sub-floor (prior "best" cot_positioning was COT look-ahead leak, M-095) |
| CRYPTO | 6,274 | 40.9 | 0.88 | sub-floor (ml_enhanced family ≈PF 0.64 drag, 147/149 unquarantined) |
| FOREX | 474 | 25.1 | 0.32 | catastrophic — hard-disabled |
| FUTURES | 127 | 4.7 | 0.11 | catastrophic — hard-disabled |
| BOND | 1 | 0.0 | 0.0 | no data |

The one allowed bet: **CRYPTO funding-rate / basis arbitrage (delta-neutral, structural)**
— not directional, pending user go/no-go. Peer STRAND B + peer `vhgaxcm7` (C-3/H-017
funding-settlement liquidation-cascade backtest) are already in flight — coordinate.

---

## 2. Infra fragility — broken workflows (act on these)

| Workflow | State | Fix |
|----------|-------|-----|
| `penny-stock-picks.yml` | failing 21 days — `could not read Username for github.com` | repair checkout token/PAT |
| `dxy-state-update.yml` | cron defined, never executed → `dxy_state.json` stale → degrades M-074 COMMODITY booster | re-enable workflow (GitHub 60-day inactivity auto-disable) |
| `sports-betting-refresh` / `custom-sports-update` | leg cancelled 5× at Checkout — Goal #2 sports leg silently not refreshing | fix checkout |
| `ci-tests.yml` | ~18/19 runs cancelled (concurrency cascade) — CI not a reliable gate | concurrency-group fix |
| `equities/etf/commodities/bond-agent` | **green but 0 quality picks** — yfinance empties, scanners fail-open, exit success. **Status UI lies.** | fail/alert on 0 raw picks |
| `outcome-resolver` | logged `YM=F` PnL **+18,926,991%** — futures unit/price-scale bug | fix bar-replay resolver scale |

### #1 systemic fragility — yfinance monoculture

~147 of 150 `yf.download`/`yf.Ticker` callers hit Yahoo with **no failover** — direct
CLAUDE.md API-Failover-Rule violation. Failover infra **exists** (`ohlcv_failover.py`,
`equity_price_failover.py`, `api_failover.py`, `crypto_data_failover.py`) but only
`etf_scanner.py` + `bond_scanner.py` use it. Top fix: route `scanner.py:1291,1301` and
`forex_smart_picks.py:333` through `ohlcv_failover.fetch_ohlcv_failover` using the
`failover_available()`-gated pattern proven in `etf_scanner.py:194-219`. Focused tested PR.

---

## 3. Open items (specified, not yet done)

- **P0** `penny-stock-picks.yml` token + `dxy-state-update.yml` cron re-enable (quickest wins)
- **P0** fail-open masking — asset agents exit green on 0 picks
- **P0** non-crypto outcome resolver — EQUITY/FOREX/FUTURES/ETF/BOND close at `pnl_pct=0.0`
  placeholders → 5 of 6 classes statistically invisible (highest-leverage repo task)
- **P0** duplicate re-emission at the writer (83% downstream drop, 4,830 dup re-emissions)
- **P0** wire yfinance failover into `scanner.py` + `forex_smart_picks.py`
- **P0** quarantine `ml_enhanced` family (M-105, 147/149 variants)
- **P0** default `/audit` per-class tiles to `pf_registry.json` (#1221) + honest "Money Ready" empty state
- **P1** `YM=F` 19M% resolver unit bug
- **P1** regime-conditional admissibility mode in `edge_stability_harness.py`
- open from prior session: `cot_*` `closed_at` fix, `mega_mutation` report push, roadmap Phase 0

---

## 4. Strategy-review swarm brief

The swarm is asked to review the existing strategy stack and propose **further** strategies,
subject to these hard constraints (from `MASTER_ENHANCEMENT_PLAN` §6 / `ROADMAP_TO_EDGE` §7):

1. **Causal hypothesis before data** — economic mechanism written first, pre-registered
   `H-xxx` in `hypothesis_registry.json`. No data-dredging.
2. **Banned families** — funding-rate *directional* predictor, yield-curve, F&G/RSI, COT
   directional. A *regime filter* using funding rate is allowed; a directional predictor is not.
3. **Regime-conditional** — a signal admissible *within* a regime even if it flips across
   regimes is acceptable; the current harness kills these.
4. **Ensemble over hero-signal** — many weak partially-correlated signals + Bayesian
   shrinkage + portfolio construction, not one hero signal per class.
5. **Risk model as a first-class gate** — cross-asset correlation, liquidity, hedging
   modeled before any signal is admitted.
6. **Net-of-cost** — every proposal must survive the post-cost expectancy gate (keep ≥60%
   of gross after round-trip cost; funding-arb needs a *continuous*-funding cost model).
7. Free APIs + shared hosting only. No paid feed assumed (Phase 0b is a separate track).

Swarm output goes to `reports/strategy_review_swarm_2026_05_18.md`.
