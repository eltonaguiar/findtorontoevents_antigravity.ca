# B_failed: equity_vix_regime_momentum + commodity_carry_momo (and seasonal/funding variants) — No Full 6/8-Gate Pass on Clean Resolved — Firing 3 (2026-05-20)

**Subagent:** Quant validation for 019e490182df firing 3 (lighter + candidates focus)
**Verdict:** B (fail/insufficient). Inspected via alpha_engine/equity_vix_regime_momentum.py + tools/research/commodity_carry_momo.py + audit_dashboard/data/*.json + baby backtest json + validate_resolved_picks framework + 6GATES/90day context. No candidate achieves all 8 gates on production resolved_picks data.

## Citations
- alpha_engine/equity_vix_regime_momentum.py (VIX term structure regime + momentum on SPY/QQQ/IWM)
- audit_dashboard/data/equity_baby_strategies_backtest.json:3-30 (n=604 trades / 448 closed, WR=40.62%, PF=1.0263, Sharpe=0.202, +2800 USD)
- tools/research/commodity_carry_momo.py:84-178 + audit_dashboard/data/commodity_carry_momo.json:2-49 (WIRED 2026-05-20, 18 sym, quintile double-sort mom+carry proxy, recent OJ=F SHORT; caveat "MODERATE-confidence proxy" vs Miffre second-month; ref SSRN1127213)
- reports/continual_research/6gate_validation/COMMODITY_CYCLE_FIRING2_2026-05-21.md:29,32 (carry_momo "promising but limited resolved track"; "no strong clean per-named 6/8")
- 6GATES_2026-05-21_V1_FREEBUFF.MD:171 (real EQUITY n=20 insufficient); 6GATES appendix (per-trade Sharpe inflation; needs daily PnL)
- statistical_validation_framework.py:557 (Bootstrap), 752 (WalkForward), 1051 (gate pipeline); validate_resolved_picks.py:77 (_sharpe_from_trades), 39 (imports framework)
- alpha_engine/config.py:141 (ETF high Sharpe mention), 152 (funding carry), 265 (FUTURES/BOND floors)
- reports/asset_class_90day_plan_COMMODITY_2026-05-15.md + EQUITY (carry_momo / vix as sidecars)
- hypothesis_registry.json (related H-003/037 ETF VIX/momo; H-005 FUTURES; COMMODITY seasonals H-007+)

## Gate-by-Gate Simulation/Inspection on Candidates (using available outputs + framework logic)
**1. equity_vix_regime_momentum:**
- Data: Baby backtest (not full prod resolved_picks attribution; real EQUITY resolved total n=20 across all, post-tagging-correction per 6GATES). 448 closed trades.
- G1 Sharpe ≥1.0: 0.202 FAIL (very low; per-trade annualization in _sharpe_from_trades may inflate but still <<1; realistic daily would be worse).
- G2 Bootstrap p<0.05: Not run on resolved series (baby only); assume marginal given low Sharpe.
- G3 CI lower >0: Likely fail (low mean).
- G4 Walk-Forward ≥50% OOS positive: Insufficient windows/power on n=20-448 split (needs ≥42 min per framework); baby not chronological WF validated in prod.
- G5 MC Bootstrap 5th>0: Unavailable.
- G6 MC Crash: Unavailable.
- G7 Win Rate >40%: 40.62% — marginal, fails strict on closed (or passes relaxed per 6GATES FOREX note).
- G8 PF >1.0: 1.0263 PASS.
- **Overall:** 2-3/8 pass at best; G1 critical fail + n insufficient for full suite on real resolved EQUITY slice. VIX regime transfer from EQUITY to ETF promising in backtests but unproven in resolved.

**2. commodity_carry_momo_double_sort:**
- Data: Wired sidecar (05-20 json has OPEN picks only, no closed PnL series in universal_resolved_picks attributed to this exact name yet). 18-sym COMMODITY universe. Proxy carry (free-path rolling mean) vs true basis.
- G1-G8: Cannot execute (0+ few resolved trades for named strat; COMMODITY post-COT clean n~5-20 total for flagship, carry not yet accrued). Harness in commodity_strategy_harness.py exists but not run on clean carry slice.
- G4/G5 power: 0 (weekly signals, n low).
- **Overall:** INSUFFICIENT_N / UNTESTED. "Promising" per 90day/CYCLE but "lack clean power" + proxy caveat. Fails real 6/8 until post-hygiene accrual + daily PnL.

**3. Funding/Seasonal variants (e.g. funding_rate_arb, commodity_seasonal, forex_carry_momentum):**
- Similar: Attribution sparse in resolved (crypto-heavy or COMMODITY-polluted pre-fix); n per-named <20 clean. G1-8 not passable (power/hygiene). Registry pre-reg but results UNTESTED/REJECTED for related.

**Common:** Tagging bug + COT over-emission/hygiene block clean data for lighter + these cross-class candidates. validate_resolved_picks runs confirm only CRYPTO has power (16/27 BH-FDR, 6/27 all 8 gates).

## Next Actions Specific to These Candidates
- Post P0 tagging fix + COT re-agg: re-attribute historical picks to correct asset_class/strat names in resolved json.
- Accrue 30d+ paper/live for carry_momo (use tv-paper-trade) and vix_momentum on real equity/ETF.
- Implement daily PnL builder in validate_resolved_picks for accurate G1.
- Full run of commodity_strategy_harness + etf/equity_strategy_harness + statistical_validation_framework on post-fix slice.
- If pass: promote to A_passed/ + live sizing (0.1% pilot); else archive with kill_reason.
- Pre-reg any mutation in hypothesis_registry.json.

**Verdict for Firing 3:** These 2-3 + lighter classes remain B_failed pending hygiene/accrual. Strong academic/backtest signals exist (VIX transfer, Miffre carry) but production validation blocked — exactly why continual loop + markers. No promotion this cycle.

See also: lighter..._insufficient..._firing3 marker + pending prereqs file.

*Rigorous per task: cited files, simulated gates from actual outputs.*
