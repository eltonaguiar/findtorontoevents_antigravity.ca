# 00 — Executive Summary (final_v2)

**Date:** 2026-11-14  
**Worktree:** childlike-airport (Kilo)  
**Scope:** Peer-reviewed synthesis of AI/ML trading audits, per-asset-class profitability assessment, and a statistically-grounded action plan for `eltonaguiar/findtorontoevents_antigravity.ca`.

## Bottom Line

- **System-level verdict: NOT profitable / not production-ready.** Deep audit evidence shows pervasive data-quality and PnL integrity failures (81% of open picks with fake 0% P/L, losses understated ~10x, 78.6% EXPIRED/zombie active rows, stale/frozen DB snapshots, near-empty audit trail, 7 failing workflows, regime coverage ~0.25%).
- **Component-level verdict: statistically valid profitable approaches DO exist** in isolated, rigorously tested slices — but they are not the current end-to-end system and require clean data, controlled deployment, and continued validation.
- **Path forward:** stop mining signals from the broken multi-strategy zoo; remediate data/pipeline integrity first, then deploy one or few clean, diversified, risk-managed strategies per asset class with strict OOS/statistical gates.

## Peer Consensus (synthesized)

| Peer / Source | Core contribution | Key numbers / claims |
|---|---|---|
| deepAI (audit branch) | Live repricing + data integrity audit | 81% fake 0% P/L; losses understated ~10x; PF 0.80 overall; walk-forward Variant C (equity/ETF) PF 1.26, n=237, p<0.0013 (pilot) |
| ITERATION-005 | Vol-targeted time-series momentum (crypto, 7.4y) | CAGR 23.0%, Sharpe 2.13, PF 1.40, MDD −17.4%, t=5.56, bootstrap CI [1.25,3.25] — PROVEN (research) |
| Grok | Implementation/roadmap perspective | T2 targets emphasized (n≥500 crypto, PF≥1.5, Sharpe≥1.0, WR≥50%, MDD<20%, PBO<0.3, DSR>0.95) |
| flaxen-hair | Strategy-level backtest/forward evidence | `mega_mutation_macd_rsi`/`ema_momentum` CRYPTO PF 3.12–5.816 backtest, 8.32 forward, WR 84% |
| hilarious-seer / scratch-hippodraco | Peer review inputs | Incorporated into synthesis; reinforce data-quality and validation concerns |
| Kilo (childlike-airport) | ML/DB audit, proposed fixes, VWAP research | DB stale ~172d (129 picks), 8 sign contradictions, 15 calc mismatches; Regime-Filtered VWAP MR 4h crypto v11 PF=1.435 Sharpe=7.10 PBO=0.480 DSR P(SR>0)=1.000 MDD=3.5% n=65; v12 (8 symbols) PF=1.210 Sharpe=3.76 PBO=0.489 MDD=10.0% n=129 (strict gates: PBO<0.3 fails) |

## Validated / Candidate Profitable Approaches

| Approach | Asset | Evidence | Verdict |
|---|---|---|---|
| Regime-Filtered VWAP Mean Reversion (4h) | Crypto | v11: PF 1.435, Sharpe 7.10, MDD 3.5%, n=65, PBO 0.480, P(SR>0)=1.0. v12 (expanded): PF 1.210, Sharpe 3.76, MDD 10.0%, n=129, PBO 0.489, P(SR>0)=1.0; 4/8 symbols profitable (BTC/ETH/SOL/XRP/ADA core) | PROFITABLE (basic gates pass); strict PBO<0.3 unmet — needs more data/symbol selectivity |
| Vol-Targeted TSMOM (50d+200d, 20% vol target) | Crypto (diversified) | 7.4y, CAGR 23.0%, Sharpe 2.13, PF 1.40, MDD −17.4%, t=5.56, bootstrap CI [1.25,3.25] | PROVEN in research; requires production wiring & live validation |
| Walk-Forward Variant C | Equity/ETF | PF 1.26, n=237, p<0.0013 | PILOT — promising but below PF≥1.5 target; needs expansion |
| mega_mutation_macd_rsi / ema_momentum | Crypto | PF 3.12–5.816 BT, 8.32 FW, WR 84% | CANDIDATE — strong but must be independently revalidated OOS with costs/slippage and leakage checks |

## Critical Data Quality / Integrity Issues (must fix before trusting performance)

- `data/live_picks.db`: 129 picks, all stale ~172 days; ACTIVE/OPEN frozen; 8 PnL sign contradictions; 15 PnL calc mismatches; 6 missing `asset_class`; no mutual funds.
- `data/audit_trail.db`: core tables effectively empty (consensus/raw/feature/filter/trades = 0).
- Active/closed universe: 273 active, 16,771 closed (16,176 with pnl) but dominated by EXPIRED/zombie rows (~78.6% in active_raw) and fake 0% P/L patterns.
- Pipeline/sync bugs: `sync_all_picks_to_mysql.py` (null/zero entry, `pnl *= 100` heuristic), `price_realism_check.py` (hardcoded expected prices), unsynced JSON sources (`active_picks_bond.json`, `active_picks_etf.json`), regime layer near-empty.
- Operational: 7 workflows failing; Unified Audit Dashboard frequently cancelled.

## Recommended Immediate Priorities

1. **Freeze claims of profitability** for the aggregate system until PnL repricing and data integrity are repaired.
2. **Remediate data pipeline**: fix sync/PnL math, backfill/resolve stale & zombie picks, unify sources of truth, restore audit trail logging, stabilize workflows.
3. **Promote only gated strategies**: deploy regime-filtered VWAP MR (crypto, BTC/ETH/SOL/XRP/ADA core) and/or vol-targeted TSMOM in paper/shadow mode with live monitoring; require expanded OOS sample to meet PBO/DSR/T2 targets.
4. **Per-asset build-out**: implement/wire Faber TAA (stocks/ETFs/mutual funds), bond trend, FX momentum + kill switch, commodity trend; fix futures/commodity zero-P/L handling.
5. **Institutionalize validation**: enforce PF/Sharpe/PBO/DSR/MDD/trade-count/cost-sensitivity gates, leakage checks, and independent reproduction before any “profitable” label.

*This summary is a synthesis of peer artifacts and local analysis; component results are not proof of end-to-end, live, net-of-all-costs profitability.*
