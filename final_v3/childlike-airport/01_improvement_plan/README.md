# 01 — Improvement Plan (Vast TODOs)

**Date:** 2026-11-14 | **Scope:** ML, bugs, data, CI/GitHub Actions, asset-class work, and backtest/simulation per proposed algorithm fix.  
**Rule:** no “profitable”/live-capital claim without strict validation gates and data-integrity preconditions.

## P0 — Stop-the-Bleeding
- [ ] **G-01** Reprice & reconcile PnL canonically (resolve sign/calc mismatches; single unit contract).
- [ ] **G-02** Fix `sync_all_picks_to_mysql.py` (reject null/zero `entry_price`, remove `pnl *= 100` heuristic, unit tests).
- [ ] **G-03** Fix `price_realism_check.py` (remove hardcoded `expected_2026_prices`; reference/bounded checks).
- [ ] **G-04** Resolve EXPIRED zombies / 0% frozen picks; enforce terminal states + timestamps/exit/provenance; fix EXPIRED→WON bias.
- [ ] **G-05** Restore freshness (SLA alerts; verify/restore dead price refresh e.g. `fetch_prices.php` 404).
- [ ] **G-06** Unify sources of truth (sync `active_picks_bond.json`, `active_picks_etf.json`, stale/empty JSONs; de-dup).
- [ ] **G-07** Fix futures/commodity ~98.4% zero-P/L (contract map, roll/continuous series, marks).
- [ ] **G-08** Restore `audit_trail.db` writes + require `resolution_method`/lineage.
- [ ] **G-09** Raise regime coverage (from ~0.25%).
- [ ] **G-10** Review/land today’s local fixes (`dashboard_generator.py` after-cost fallback, `universal_pick_resolver.py` gap-fill, `hc_gates_python.py` per-class cost gate) with tests via clean branch (own files only).

## General Fixes (code, data, ML)
- [ ] **GF-01** Per-asset-class cost model (fees/spread/slippage/funding/roll/borrow); report gross & net.
- [ ] **GF-02** Schema/contracts: units, required fields, validation on ingest.
- [ ] **GF-03** Cross-ledger reconciliation (verdict vs registry vs recent_closed vs raw/DB) — row-level diffs.
- [ ] **GF-04** Leakage-safe labels/targets; gap-aware fill realism.
- [ ] **GF-05** Multiple-testing controls (CSCV/PBO, DSR with effective-N, BH/Bonferroni); enforce `MIN_WINDOWS` & fixed windows.
- [ ] **GF-06** Benchmark-relative metrics (risk-matched B&H), carry-vs-alpha decomposition.
- [ ] **GF-07** Time-safe ML (embargo/purge, no future features, fold-stable scaling).
- [ ] **GF-08** Reproducibility (freeze configs, seeds/data hashes/params/code rev).
- [ ] **GF-09** Survivorship/liquidity-aware universes; delisting handling.
- [ ] **GF-10** Concentration controls (single/multi-source gates for promotion).
- [ ] **GF-11** Risk sizing (vol targeting, caps, drawdown kill-switches).
- [ ] **GF-12** Observability (drift, staleness, fill parity, slippage-vs-model, regime dashboards).

## GitHub Actions / CI Fixes
- [ ] **CI-01** Triage 7 failing workflows (permissions/secrets/timeouts/deps/paths).
- [ ] **CI-02** Fix mass cancellations (concurrency/cancel-in-progress tuning).
- [ ] **CI-03** Freshness/health jobs (SLA, audit-trail non-empty, regime coverage).
- [ ] **CI-04** Deterministic envs (pinned deps/locks, explicit runtimes).
- [ ] **CI-05** CI validation gates (PnL/sync/resolver tests, schema checks, seeded backtest smoke).
- [ ] **CI-06** Artifact integrity checks before deploy (non-zero, schema-valid, fresh).
- [ ] **CI-07** Loop/trigger safety (`[skip ci]`, avoid broad generator-triggering globs).
- [ ] **CI-08** Alerting on failure/stale/regression.
- [ ] **CI-09** Resource/time budgets (split jobs, timeouts, retention).
- [ ] **CI-10** API/secret/rate-limit hygiene (quotas, backoff/retry).

## Asset-Class-Specific Fixes & Build-Out

### Crypto
- [ ] **CR-01** VWAP-MR core-only (BTC,ETH,SOL,XRP,ADA); exclude persistent OOS losers.
- [ ] **CR-02** >730d 4h exchange data; revalidate regime-filtered VWAP-MR (target PBO<0.3).
- [ ] **CR-03** Productionize Vol-Targeted TSMOM (50d+200d, 20% vol target, diversified, net costs/funding).
- [ ] **CR-04** Independently reproduce `mega_mutation_macd_rsi/ema_momentum` (OOS, path-verified, full costs).
- [ ] **CR-05** Test MR+trend ensemble.

### Stocks / Equities
- [ ] **EQ-01** Reproduce Walk-Forward Variant C (raw, net-of-cost), expand sample.
- [ ] **EQ-02** Build/test Faber TAA or sector-neutral QVM (long daily history).
- [ ] **EQ-03** Risk-matched benchmarks; effective-N/multiple-testing control.

### ETFs
- [ ] **ET-01** Sync ETF picks; include in Variant C/Faber TAA OOS.
- [ ] **ET-02** Low-fee liquid universe; model spreads/rebalance costs.

### Bonds
- [ ] **BD-01** Sync bond picks; build Vol-Targeted Bond Trend (duration/rate/regime aware).
- [ ] **BD-02** Rate-regime stress; realistic carry/costs.

### Mutual Funds (low-capital, low-fee priority)
- [ ] **MF-01** Wire `MUTUAL_FUND` in `alpha_engine/asset_class.py` and `ml_gatekeeper/gatekeeper.py` + pipeline.
- [ ] **MF-02** Validated allocation signal on `mutual_fund_ranker.py` / `fund_holdings_deriver.py`.
- [ ] **MF-03** Low-capital/low-fee subset: $0 min, no-load, no 12b-1, ER ≤0.20% (prefer ≤0.05%), broad/liquid, large AUM.
- [ ] **MF-04** Model next-NAV execution, minimums, redemption/short-term fees.
- [ ] **MF-05** NAV walk-forward OOS net-of-fee vs benchmark.

### Forex
- [ ] **FX-01** FX momentum/trend with spread/rollover/session modeling.
- [ ] **FX-02** Wire/enable `fx_kill_switch.py`; macro/vol filters.
- [ ] **FX-03** Net-of-cost validation.

### Commodities / Futures
- [ ] **CM-01** Fix pricing/zero-P/L & roll logic first.
- [ ] **CM-02** Diversified commodity trend with margin/carry/slippage.
- [ ] **CM-03** Vol targeting, sector diversification.

## Backtest/Simulation per Proposed Fix (summary)
| Fix/Algo | Simulation | Pass criteria |
|---|---|---|
| PnL/unit & sync fix | Deterministic recompute + reconciliation | 0 sign/calc mismatches; tests pass |
| Gap-fill resolver | Gap-event replay naive vs gap-aware | No better-than-gap fills |
| Per-class cost gate | With/without counterfactual | Suppresses negative-expectancy classes |
| VWAP-MR core | >730d 4h walk-forward, cost stress | PF/Sharpe/MDD/PBO<0.3/DSR/n stable |
| Vol-Targeted TSMOM | 7y+ diversified, bear/subperiods, bootstrap CI | Robust net edge, CI>0, benchmark-aware |
| MR+TSMOM ensemble | Correlated blend OOS | Better risk-adjusted than components |
| mega_mutation | Independent OOS, path-verified, full costs | Persists without leakage |
| Variant C | Raw walk-forward net-of-cost | Gates met, stable |
| Faber TAA/QVM | Long-history costed OOS vs benchmark | Net outperformance, controlled MDD |
| MF low-fee allocation | NAV next-fill walk-forward | Net-of-fee, acceptable MDD |
| Bond trend | Rate-regime stress | Net positive/robust |
| FX momentum | Spread/roll-inclusive + kill-switch | Survives costs, capped MDD |
| Commodity trend | Roll/margin-aware post-fix | Diversified net positive |

*Detailed protocols in `../04_backtest_simulation/README.md`.*
