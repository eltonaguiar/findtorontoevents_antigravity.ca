# Remaining items after the 2026-11-16 audit session

Prioritized. Owner column is where the work sits right now. Everything below was verified on 2026-11-16 after 22:00Z unless noted.

## P0 — blocks trustworthy numbers

1. **Dashboard generator crash (PR 856).** `audit_trail/dashboard_generator.py` `collect_audit_events` sliced `crypto_signal_engine` `new_picks` when the writer stores an int (`len(h_active)`). One run died with `TypeError: 'int' object is not subscriptable`. Fix is written and tested; the PR needs merging after this CI fix gives it a green run.
2. **22 red tests on main (fixed in this PR).** Root cause was the per-class VIX gate rejecting EQUITY fixtures, not the wf_verdict or Phase-1 logic. Test-only pin added; 61 tests pass locally. Until this lands, no audit PR can show a green check.
3. **Live Sharpe is not stored for any asset class.** It is one of the five gates (DSR>0.95, PBO<0.05, WFE>60%, live-Sharpe>0.5, n>=100) and cannot be evaluated. Compute it from the closed-pick ledger per class before any class can be called profitable.
4. **WFE is a PF split, not edge retention.** `wf_oos_ratio` is displayed as WFE but is not OOS Sharpe / IS Sharpe. Publish a real WFE or stop calling it that.

## P1 — false labels still reachable

5. **`alpha_engine/money_ready_verdict.py` can still return MONEY_READY** through the SPA OR (`PBO_THRESHOLD = 0.55`, no WFE argument, no live-Sharpe argument). PR 848 hardened the display filter only. The generator needs the same five-gate test.
6. **`audit_trail/stamp_pick_quality.py` `_assign_trust_tier` writes PROVEN at n>=10 and WR>=55%**, and a missing DSR does not block. This rewrites stored labels, so it needs its own review and a backfill plan.
7. **PBO on CRYPTO is ghost-contaminated** (sleeves with PF 37–120 before dedupe). Recompute PBO on ghost-filtered, policy-clean returns.
8. **Polymarket PROVEN badge remnants.** Page text is fixed; check any remaining badge/`Verified Alpha` filter path in `audit_dashboard/template.html` still names prediction markets.

## P2 — data quality

9. **Ghost rows 22,947** and **open_bloat 92,232** trading_picks, 29,247,197 `bt_backtest_trades` open. `harness_healthy: false`, overall 3 passed / 2 failed. Quarantine-not-delete policy stands.
10. **Feed Health run 43931137682 fails**: `pm_momentum_signals missing_from_payload`. Owner: GHA seat.
11. **QA Market Validation run 43927629856 fails**: 11 critical flags, EQUITY blank TP/SL (6), mismatch (10). Owner: GHA seat.
12. **PR 839 CI red** (`test 3.11`, `test 3.12`). Owner: ghactions seat.

## Asset-class status (do not oversell)

- Book n=7805, WR 40.9%, PF 0.91, expectancy -0.16, compounded PnL -77.7%, Sharpe -0.109.
- 0/10 money-ready. COMMODITY is the only PF>1 class with n>=100 (PF 1.03, DSR 0). EQUITY is 59.2% WR but PF 0.94.
- Prediction markets: no closed book, verified-alpha slice losing (n=896, WR 42.4%, PnL -193%), prior PBO 0.603. Shadow only.
- Research candidates BTC sma200, GLD sma200 and Faber remain unproven (0/11 proof protocol).

## Local-only note

`tests/test_combined_book_reproduction.py::test_research_dataset_reproducible_subset` fails in this worktree because `combined_book/data/kfrench/Portfolios_Formed_on_OP.txt` is not present locally. It is not one of the CI failures.
