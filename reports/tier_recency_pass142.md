# Tier / Recency Pass 142 — 2026-06-13 (Goal #1)

**Worktree:** .worktrees/audit-dig-deeper-2026-06-12 (branch audit-dig-deeper-2026-06-12, PR #564)
**Focus:** Goal #1 (0/9-0/10 T2; COM+velocity on 15 CONDITIONS n=108 crypto_rsi 47.2/1.535 retention lift best visible granular edge inside class drag; one-sided hygiene 33 complete; harness measurement showed not admissible due to n_eff/conc/walk). 14d/48h first per CLAUDE rule. NFA.

## 14d/48h Recency Panels (verified FIRST per CLAUDE.md rule — never size on historical without)
**14d (gen 2026-06-13T05:10Z, window 336h, source ejaguiar1_stocks.at_raw_picks):**
- CRYPTO: n_touched=17786, n_closed=10423, n_decisive=10393, wins=4194, wr_pct=40.35, pf=6.432, mean_pnl=35.6369, top_sym=BTCUSDT(12.1%), top_src=AlphaEngine(37.4%), caveats=["dup_groups=370"]
- FUTURES (COM proxy): n_decisive=243, wr=32.1, pf=0.548, caveats=["dup_groups=4","single_source_concentration=100%_via_AlphaEngine"]
- EQUITY: n_dec=1029, wr=48.79, pf=1.398, caveats=["single_source_concentration=60%_via_AlphaEngine"]
- FOREX: n_dec=310, wr=27.42, pf=0.543, caveats=["dup_groups=7","single_source_concentration=100%","EXPIRED_pos_pnl_share=55%_likely_mislabeled_WON"]
- Other (ETF/BOND/MEMECOIN/PENNY/UNKNOWN): mostly low n or INSUFF (n_dec<10 omitted WR); ETF wr~52 but pf=0.513 conc high.
**48h (gen 2026-06-13T05:32Z, window 48h):**
- CRYPTO: n_touched=263, n_closed=170, n_decisive=170, wins=48, wr=28.24, pf=0.493, mean_pnl=-1.00, top=DOGEUSDT, src=AlphaEngine 100%, caveats=["dup_groups=7","single_source_concentration=100%_via_AlphaEngine"]
- FUTURES (COM proxy): n_dec=28, wr=46.43, pf=0.799, top=CL=F(28.6%), caveats=["single_source_concentration=100%"]; sample picks include wins on NQ/YM/HG/GC/PL/SI (tsmom/commodity_term_cot) but losses on CL/ZC/NG (combined_confidence/momentum) — granular mixed.
- No other classes with decisive n>=10 closed in 48h window (CRYPTO dominant but collapsed WR/PF vs 14d; 0 closed in some prior notes).

**Recency note:** 14d CRYPTO PF inflated by outliers/dups but WR~40% sub-T2; 48h severe degradation (28% WR / 0.49 PF). FUTURES 48h WR lift 32->46 but n=28 tiny, pf<1. COM class drag confirmed. 14d/48h panels checked before any tier/historical claim.

## pf_registry Snapshot (gen 2026-06-13T05:10:00Z, canonical per CLAUDE; read instead of recompute)
- schema 1.1.0, source_files: closed_picks from alpha_engine(502), battleground(123), mercury2(469), paper(34), ml_battle* (small 0-19)
- top keys: schema_version, generated_utc, description, source_files, ..., by_asset_class_raw, by_asset_class, by_asset_class_policy_clean, by_asset_class_policy_clean_net, by_asset_class_strategy_policy_clean_net, asset_class_health, ...
- by_asset_class_policy_clean_net COMMODITY: n small ~8-12 range (INSUFF/FAIL per prior verdicts), wr~33 pf~0.82-1.26
- by_asset_class_policy_clean_net CRYPTO: n~1697 or filtered slices ~160 in tracker view, sub-T2 (wr~43-51 but PF low ~0.65-1.14, mdd/conc issues)
- asset_class_health: 0/ classes pass T2 (COM INSUFF n=8-12; CRYPTO FAIL+; others INSUFF n<30 or worse metrics)
- No velocity/conditions inside pf_registry (separate harness); policy_clean_net is post M-067 flicker/hygiene resolver fix.
- (Full 330kB file; key for tier source of truth.)

## Full Tier Tracker Output (run: python3 tools/strategy_tier_tracker.py --no-write ; attempted --force-db unrecognized; source pf_registry 05:10Z)
# Strategy Tier Tracker — 2026-06-13T06:18:08.992643+00:00

Source: `audit_dashboard/data/pf_registry.json` generated `2026-06-13T05:10:00Z`

Tier thresholds (CLAUDE.md MAJOR GOALS): T1 PF>2.0/WR>55; T2 PF>1.5/WR>50; T3 PF>1.2/WR>45; min n=30 for any tier.

## COMMODITY
**Class verdict:** INSUFFICIENT_DATA (n=8)
| Strategy | n | wins | losses | WR% | PF | Tier | Note |
|---|---:|---:|---:|---:|---:|---|---|
| `feature_signals` | 4   | 1   | 3   | 25.0  | 0.79  | INSUFF_N (n=4) |  |
| `metals_mean_reversion` | 2   | 1   | 1   | 50.0  | 2.00  | INSUFF_N (n=2) |  |
| `commodity_tsmom_12m` | 2   | 1   | 1   | 50.0  | 1.57  | INSUFF_N (n=2) |  |

## CRYPTO
**Class verdict:** FAIL  (n=160, PF=0.53, WR=33.8%)
| Strategy | n | wins | losses | WR% | PF | Tier | Note |
|---|---:|---:|---:|---:|---:|---|---|
| `copy_trader_clones` | 34  | 15  | 19  | 44.1  | 0.78  | FAIL |  |
| `UNKNOWN` | 24  | 1   | 23  | 4.2   | 1.02  | INSUFF_N (n=24) |  |
| `ml_breakout` | 21  | 0   | 21  | 0.0   | 0.00  | INSUFF_N (n=21) |  |
| `battleground_luxalgo` | 18  | 11  | 7   | 61.1  | 1.93  | INSUFF_N (n=18) |  |
| `multi_period_rsi_confluence_eth` | 16  | 7   | 9   | 43.8  | 0.43  | INSUFF_N (n=16) |  |
| `drawdown_recovery_rsi_eth` | 9   | 5   | 4   | 55.6  | 3.39  | INSUFF_N (n=9) |  |
| `beta_adjusted_residual_momentum` | 7   | 2   | 5   | 28.6  | 0.53  | INSUFF_N (n=7) |  |
| `luxalgo_confluence` | 4   | 3   | 1   | 75.0  | 3.69  | INSUFF_N (n=4) |  |
| `vwma_momentum_trend` | 4   | 3   | 1   | 75.0  | 3.42  | INSUFF_N (n=4) |  |
| `B_flip_PriceRocMeanReversion` | 3   | 0   | 3   | 0.0   | 0.00  | INSUFF_N (n=3) |  |
| `gru_attention` | 3   | 0   | 3   | 0.0   | 0.00  | INSUFF_N (n=3) |  |
| `atr_percentile_gate_scanner` | 2   | 0   | 2   | 0.0   | 0.00  | INSUFF_N (n=2) |  |
| `inverse_ml_enhanced_ADAUSDT_15m_D` | 2   | 2   | 0   | 100.0 | —     | INSUFF_N (n=2) | no_losses |
| `inverse_ml_enhanced_RENDERUSDT_4h_D` | 2   | 2   | 0   | 100.0 | —     | INSUFF_N (n=2) | no_losses |
| `ml_strategy_reviver_inverse` | 2   | 0   | 2   | 0.0   | 0.00  | INSUFF_N (n=2) |  |
| `ornstein_uhlenbeck` | 2   | 0   | 2   | 0.0   | 0.00  | INSUFF_N (n=2) |  |
| `commodity_tsmom_12m` | 1   | 1   | 0   | 100.0 | —     | INSUFF_N (n=1) | no_losses |
| `connors_rsi2` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |
| `genome_mutation_lab` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |
| `hoffman_ema_trend` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |
| `inverse_ml_enhanced_RENDERUSDT_1h_D` | 1   | 1   | 0   | 100.0 | —     | INSUFF_N (n=1) | no_losses |
| `mega_mutation` | 1   | 1   | 0   | 100.0 | —     | INSUFF_N (n=1) | no_losses |
| `rapid_trend_only_mut` | 1   | 0   | 1   | 0.0   | 0.00  | INSUFF_N (n=1) |  |

## EQUITY
**Class verdict:** INSUFFICIENT_DATA (n=41)
... (UNKNOWN 14n 64.3/3.21 INSUFF; regime_terminal 9n; vt_equity...6n no-loss; all others n<=2 INSUFF)

## ETF / FOREX / FUTURES / INDEX / PENNY_STOCK
All INSUFFICIENT_DATA (n=1-22), e.g. FOREX multi_asset_scanner 11n 9.1/0.21; FUTURES multi 11n 9.1/0.48 + tiny; no T2/T1/T3 anywhere (n<30 or PF/WR below).

**Updated tiers for velocity conds (crypto_rsi etc.) + COM slices:** pf_registry tiers (closed picks aggregate) show no velocity/cond granularity (crypto_rsi not surfaced here; see harness). COM slices in pf: feature_signals etc n<=4 INSUFF (class n=8). Velocity harness (separate 14d stamped) provides granular CONDITIONS view (see below). No class reaches T2 min (n>=30 + PF>1.5/WR>50). crypto_rsi not in pf tiers but best edge per harness.

---
Read-only. Source of truth is pf_registry.json; do not recompute PF from raw picks. (Full run captured 2026-06-13T06:18Z in wt.)

## Velocity Harness 15 CONDITIONS (from audit_dashboard/data/velocity_harness_results.json gen 2026-06-13T05:08Z; stamped 1162/1205 cohort; 14d window)
num_conditions: 15
Thresholds: min_n=100, min_n_eff=80, min_wr=48.0, min_pf=1.5, min_ci_lb=1.15, max_concentration=0.35

(sorted by PF desc):
1. forex_trend_aligned: n=16 wr=68.8 pf=5.333 n_eff=1.6 conc_max=1.000 walk_pass=False
2. luxalgo_short: n=38 wr=71.1 pf=2.211 n_eff=3.8 conc_max=1.000 walk_pass=False
3. crypto_rsi5070_us: n=108 wr=47.2 pf=1.535 n_eff=45.6 conc_max=0.639 walk_pass=False
4. baseline_FOREX: n=43 wr=41.9 pf=1.48 n_eff=4.3 conc_max=1.000 walk_pass=False
5. equity_lowvol: n=22 wr=36.4 pf=1.328 n_eff=2.2 conc_max=1.000 walk_pass=False
6. baseline_EQUITY: n=58 wr=48.3 pf=0.989 n_eff=5.8 conc_max=1.000 walk_pass=False
7. equity_highvol_NEGATIVE: n=36 wr=55.6 pf=0.824 n_eff=3.6 conc_max=1.000 walk_pass=False
8. baseline_CRYPTO: n=924 wr=32.0 pf=0.712 n_eff=404.7 conc_max=0.631 walk_pass=False
9. baseline_MEMECOIN: n=65 wr=27.7 pf=0.605 n_eff=10.5 conc_max=0.769 walk_pass=False
10. baseline_COMMODITY: n=43 wr=20.9 pf=0.515 n_eff=4.3 conc_max=1.000 walk_pass=False
11. forex_contrarian_NEGATIVE: n=27 wr=25.9 pf=0.458 n_eff=2.7 conc_max=1.000 walk_pass=False
12. baseline_FUTURES: n=10 wr=10.0 pf=0.439 n_eff=1.0 conc_max=1.000 walk_pass=False
13-15. baseline_BOND/ETF/UNKNOWN: n<=11 wr<=0 pf=0 (degenerate)

**crypto_rsi5070_us details (best visible granular edge inside CRYPTO class drag, n=108 closest to min_n=100):**
n=108 wins=51 losses=57 wr=47.2 pf=1.535 avg_pnl=0.5882 gp=182.3 gl=118.8
n_eff=45.6
concentration: max_share=0.639 top=alpha_engine n_sources=3 hhi=0.5259 passes=false
symbol_concentration: max=0.056 top=RENDERUSDT n_syms=65 passes=true
ci_95: lb=1.228 ub=1.918
wilson_ci: lb=38.1 ub=56.6
binomial_p=0.250
walk_forward: windows=8 stable_windows=4 wr_range=24.7 pass=false
per_window: [0:38n 52.6/1.4], [1:20n 40/1.569], [2:17n 64.7/2.686], [3:15n 46.7/1.503], [4:7n 28.6/0.598], [5:8n 25/1.566], [6:1n 100/0], [7:2n 0/0]
**COM slices in velocity:** baseline_COMMODITY n=43 wr=20.9 pf=0.515 (drag); baseline_FUTURES n=10 wr=10 pf=0.439 (tiny). (Granular COM fut per-sym in prior DB probes better vs class aggregate.)

**Harness measurement (per focus):** not admissible due to n_eff/conc/walk (n_eff=45.6 <80; conc 0.639>0.35; walk 4/8 unstable; wr 47.2<48 borderline; pf 1.535~ok but gates fail overall). Retention lift real (l30 ~48.3/1.454 vs baseline decay) but full AddH/forward not yet. No promote without n>=100 clean + re-runs + gates pass + 14d/48h + verdict.

## Summary / Conclusion (Pass 142)
- Tiers from tracker/pf_registry: 0 T2 across 9-10 classes (COM/FUT/ETF/BOND tiny n INSUFF; CRYPTO large but FAIL 33.8/0.53 in this view; velocity conds not in pf tiers).
- Recency 14d/48h + pf snap + velocity 15 conds: crypto_rsi n=108 47.2/1.535 best granular CRYPTO inside drag (retention + vs baseline 32/0.71); COM baseline 20.9/0.515 + FUT proxy mixed but overall class FAIL/INSUFF. 48h CRYPTO collapsed.
- Harness: 15 CONDITIONS captured; crypto_rsi + luxalgo/forex_aligned top but none admissible (small n_eff high conc for most, walk fails).
- One-sided hygiene 33 complete (prior); no size up.
- Next per plan: pre-reg H-158, COM DB probe, paper on admissible post full gates, ratchet with 14d/48h always first.
- Files: this report, action_plan append (small), prior progress MDs. Only own (MDs). py_compile N/A (no py edit this subtask). git status own only.

**Verif iron:** read pre/post (tails + full action), status only own (M action + ?? new report + prior wt untracked), py_compile on tracker if re-run (syntax ok), no generators, rebase if needed --ours non-own. NFA. Goal #1.
