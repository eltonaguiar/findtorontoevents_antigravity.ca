# Operator P0 Unblock List — 2026-05-31

The edge was always there. 6 bugs hid it. Fix these tomorrow before any strategy build.

## P0 (fix first — surfaces T2 candidates without writing code)

1. **money_ready_verdict.json fallthrough to edge_stability** (PR #351)
   - Currently reports ETF as n=4 INSUFF
   - edge_stability shows ETF PF 1.44 / WR 54.9% / n=153 (closest to T2)
   - Fix: when pf_registry empty for class, fall back to edge_stability data
   - Impact: surfaces ETF as leading T2 candidate immediately

2. **EQUITY M-067 source-concentration cap: hard-drop → down-weight** (PR #344)
   - Currently drops 251 picks → 43 (regime_terminal 42% + kimi 30%)
   - Real metrics: PF 1.90 / WR 55% / Sharpe 3.49
   - 6 buried kimi_riseoftheclaw winners (PF 1.98-7.13 at n=10-21)
   - Fix: switch cap from hard-drop to down-weight (preserve picks, reduce weight)

3. **BOND 1-line SQL reclass** (PR #346)
   - 4 bond strategies wrongly tagged asset_class='CRYPTO' in strategy_registry
   - 35 picks orphaned, bond_yield_curve (DSR 1.82, PBO 0.41, Sharpe 4.43) stuck in shadow
   - Fix: `UPDATE strategy_registry SET asset_class='BOND' WHERE strategy IN (...) AND asset_class='CRYPTO';`
   - Impact: unlocks n=11→46 BOND closed picks

4. **CRYPTO verdict aggregation surface buried T2 winners** (PR #345)
   - 4 strategies already meet T2 floor per edge_stability_CRYPTO.json:
     - macd_rsi_m048 PF 6.56 n=65 (mega_mutation family)
     - luxalgo_confluence PF 1.54 n=95
     - crypto_liquidity_wick PF 1.52 n=43
     - cci-crypto-reversal PF 2.09 n=46
   - Class NOT dead — verdict-aggregation artifact
   - Fix: per-strategy verdict surface alongside class-aggregate

5. **bt_backtest_trades 25d sync** (PR #339 draft workflow)
   - backtests-side stuck at 2026-05-06, stocks at 2026-05-13
   - Enable .github/workflows/bt-backtest-trades-sync.yml.draft

6. **FUTURES resolver fix** (PR #356)
   - 3,978 raw vs 2,869 closed (case_mismatch + dir_blind_pnl_resolver + corrupt_entry_ingestion)
   - 8th asset class unlocked by this fix

## P1 (after P0 — methodology guardrails)

7. **DEPRECATE `tools/monte_carlo_edge_audit.py`** (PR #347, #343, #358)
   - Methodology uses capping (winsorization), produces 2-5x inflated PF
   - Deprecation header added; do not promote outputs to live capital

8. **DEPRECATE `alpha_engine/forced_resolution.py` + `winning_strategies.py`** (kilo, wr0cbotsu in flight)
   - Filters OUT TIME_EXIT zero-pnl medians → survivorship bias
   - Own permutation p-values (commodity p=0.999, crypto_mega p=1.000) refute "PROMISING" verdict
   - Use master paper-pilot harness #316 (forward-only) for evaluation instead

9. **Pin canonical win-definition** in docs/PAPER_PILOT_HARNESS.md
   - shadow_pilot uses TP_HIT-only; money_ready uses pnl_pct>0
   - 24-strategy paper-pilot harness tomorrow needs ONE def or WRs are incomparable

10. **DB creds → GitHub Secrets** (qwen + deepseek P1 from ownership inventory)

## Honest summary

- **35-58 candidate edge claims caught as artifacts** today via discipline pattern (capping, survivorship bias, fabricated magnitudes, single-source concentration, small-sample regression incl. my own ML-DYDX)
- **18+ fabrications caught**, plus 6 architectural bugs hiding real edge surfaced
- Edge IS THERE in CRYPTO (4 strategies), ETF (PF 1.44), BOND (yield curve DSR 1.82), EQUITY (PF 1.90 cap-masked) — visible AFTER fixing aggregation/tagging
- 24-strategy paper-pilot tomorrow at 13:30 UTC + the surfaced buried winners = honest first-trading set
