# Money-Maker-Ready Audit — 2026-10-20 (findtorontoevents.ca/audit)

Canonical source for money-ready verdicts: `audit_dashboard/data/money_ready_verdict.json` (9 classes, generated 2026-10-19T19:38:52Z). `dashboard_data.json::performance.asset_class_health` covers 7 classes (no MEME/PENNY_STOCK) and is the resolved-pick view; the verdict file is authoritative for money-ready status. Reconciliation: both report 0 money-ready classes (verdict: 0/9; asset_class_health view: 0/7). The 2-class gap (MEME, PENNY_STOCK) are verdict-only thin/insufficient-data sleeves.

Tier thresholds (PERFORMANCE_CHARTER): T1 PF≥2.0/WR≥55%/MDD≤10%/n≥200; T2 PF≥1.5/WR≥50%/MDD≤20%/n≥100; T3 PF≥1.2/WR≥45%/MDD≤25%/n≥100. WR is hidden where n<20 (MEME 13, PENNY_STOCK 1).

## 0. Freshness preflight
`money_ready_verdict.json` generated 2026-10-19T19:38:52Z; `dashboard_data.json` 2026-10-19T19:40:11Z — both within 2h. OK.

## 1. Investigation: why /audit had no top-notch trades
`picks.smart_picks` (quality-gates extraction) was 0 of 23 active. Causes: `forward_validated=false` (6), per-class visibility floor (8), score/RR/consensus floors (rest). The curated `smart_picks_feed` had 1 vetted pick (ETHUSDT SHORT, copy_hl_RTB_2, copy_trader_intel) never promoted. Fix (in PR): keep `smart_picks` gate-validated only; add `picks.curated_feed` (labeled "Curated – not gate-validated") and `picks.smart_picks_gate_failures` counts + top-3 near-miss contingency. See `updates/2026-10-20-audit-empty-state.md`.

## 2. Per-asset-class money-ready status (canonical: money_ready_verdict.json)

| Class | n (intrabar) | WR% | PF | Verdict |
|---|---|---|---|---|
| COMMODITY | 227 | 40.1 | 1.03 | WATCH |
| CRYPTO | 3497 | 35.5 | 0.88 | NOT_READY |
| FOREX | 547 | 30.7 | 0.61 | NOT_READY |
| EQUITY | 230 | 56.1 | 0.84 | NOT_READY |
| FUTURES | 47 | 40.4 | 1.04 | INSUFFICIENT_DATA |
| ETF | 28 | — | 0.00 | INSUFFICIENT_DATA |
| BOND | 21 | 9.5 | 0.53 | INSUFFICIENT_DATA |
| MEME | 13 | — | 0.02 | INSUFFICIENT_DATA |
| PENNY_STOCK | 1 | — | 0.00 | INSUFFICIENT_DATA |

Verdict: 0/9 money-ready. (WR hidden for n<20: ETF 28? no—ETF n=28≥20, shown as 0.0; MEME 13 and PENNY_STOCK 1 hidden; COMMODITY 227 shown.)

## 3. Walk-forward verification
`walkforward.by_class` is EMPTY (generated 2026-04-15, stale). No OOS evidence → every class UNVERIFIED for walk-forward. Action: regenerate walk-forward artifacts.

## 4. Cumulative system winners (n≥100, PF≥1.5, WR≥50)
| System | n | WR% | PF | MDD% | Asset classes | Notes |
|---|---|---|---|---|---|---|
| multi_asset_copytrader | 237 | 54.5 | 3.24 | 1.9 | COMMODITY,EQUITY,FOREX,FUTURES | EXCLUDED – data integrity (banned; CADJPY +427% feed bug) |
| mega_mutation | 729 | 60.0 | 2.49 | 64.2 | CRYPTO | MDD too high |
| battleground | 122 | 56.6 | 1.76 | 7.3 | CRYPTO | Only Tier-2 candidate; needs n≥200 |

## 5. System draggers (most negative PnL)
rapid_fire (-167, PF0.28), luxalgo_filters (-161, PF0.97, n=3786), mercury2_fast (-140), aggregated_picks (-65), ml_bg_system_b (-55), ml_bg_system_a (-50), ml_bg_ensemble (-30), copy_trader_clones (-13, PF0.52), breakout_c_spike (-12), signal_aggregator (-6), paper_trading (-5), goldmine_stocks (-5, PF0.42).

## 6. Best potential matches (edges to pursue)
- battleground (CRYPTO): PF 1.76, WR 56.6, MDD 7.3, n=122 — closest to Tier-2; needs n≥200 and PF≥2.0.
- multi_asset_copytrader: PF 3.24 but banned; if re-validated on clean data, strong cross-asset sleeve.
- mega_mutation: PF 2.49 but MDD 64.2 — needs volatility scaling / position sizing.
- ETF n=28 WR 0.0 PF 0.0 — tiny sample; promising only if re-validated.

## 7. Math / statistics to run
1. Intrabar re-resolution: `tools/reresolve_intrabar.py` (dry-run then --apply) for entry-anchored TP/SL.
2. Clean-cohort screen: exclude backfill resolvers, banned sources, sane-pnl guard, count EXPIRED as non-win; require ≥3 months n≥30/mo.
3. Walk-forward OOS: populate `walkforward.by_class` with folds, oos_wr, oos_wr_std, oos_sharpe, decay, consistency.
4. Per-class stat-sig gates (Layer 2.5): n≥8, WR≥52%, PF≥1.5 for (symbol,strategy,source) triples.
5. Concept-drift KS test: `hf_stats.concept_drift`; auto-pause if D>0.10.
6. MDD/volatility scaling for mega_mutation to push MDD≤20.
7. Backtest-overfit detector: `fwd_vs_bt_divergence.rows` grouped by system family; surgical quarantine.
8. Entry-condition stamping: `tools/stamp_entry_conditions.py` → `entry_conditions_forward.json` (RSI 50-70 x US session) until n≥100 + R1/R2/R3 re-pass.

## 8. Best-Possible-Action (ranked)
P0: Fix intrabar resolution + walk-forward regeneration (measurement first).
P1: Re-baseline clean cohort; paper-pilot ≥4wk; ban FOREX bleeders; wire emitter discipline.
P2: Academic sleeves (TSMOM, residual momentum, carry) with trailing-stop exits.
P3: ETF emitter expansion; drift auto-pause; FRED_API_KEY.
Never promote from: 14d pick summaries alone, AI tournament WR, 32.6M backtest rows.

## 9. Areas for further research
- Why `forward_validated` is false for the majority of active picks and how to set it correctly.
- Whether the per-class visibility floor (`_visibility_floor: per_class`) is too aggressive for non-crypto classes.
- Data-integrity re-validation of banned sources (multi_asset_copytrader) on clean intrabar data.
- Walk-forward regeneration pipeline (currently empty/stale).
- MDD reduction for mega_mutation (currently 64.2%).
- ETF sample expansion (n=28 → target 100+).

## 10. Verifiable claims log
- Canonical money-ready source: `audit_dashboard/data/money_ready_verdict.json` (9 classes, 0 money-ready).
- Dashboard view: `audit_dashboard/data/dashboard_data.json::performance.asset_class_health` (7 classes).
- PR: `opencode/audit-empty-state` (not merged).
"