# BOND Quick Wins
Audit: §4.1/§4.3 — "bonds" are bond-ETF proxies (TLT 31 + HYG 4 of 35 closed); published PF 0.06 (n=3) vs window PF 0.59 (n=35) vs intrabar PF **0.39 / WR 7.7%** (n=26) **INSUFFICIENT_DATA**; `thresholdPass:true` vacuously (`minTrades=0`, `minScore=35` with avgScore 0.0); DB outcomes last 2026-11-10. No coupons/yield/duration in PnL. Peer (flaxen-hair BO-4/BO-5) adds: only TLT/IEF carry true BOND class, ZN=F sits in FUTURES, and a 2026-05-30 bond-class migration needs verifying on live MySQL.

## QW-BOND-1 · Fix the vacuous pass (S, <1h) — cheapest honesty win in the repo
- **Problem:** `asset_class_summary.BOND.thresholdPass=true` with 0 active, avgScore 0.0, because `thresholds.minTrades=0`. Any consumer reading the flag sees "bonds pass".
- **Fix:** `thresholdPass = (n_forward_trades >= max(minTrades,30)) && PF>=1 && WR>=threshold` — with an explicit `INSUFFICIENT_DATA` state (mirror `money_ready_verdicts`, which already says it). Set BOND minTrades to 30.
- **Verify:** Payload shows BOND `thresholdPass:false, state:INSUFFICIENT_DATA`; unit test on n=0 fixture.

## QW-BOND-2 · Rename the class honestly: BOND_ETF_PROXY (S)
- **Problem:** Users read "BOND" as fixed income; the system trades TLT/HYG equity-listed ETFs price-only, ignoring distributions (TLT/HYG pay monthly — price-only PnL is materially understated for longs and overstated for shorts).
- **Fix:** Display label `Bonds (ETF proxies)` now; add distributions to PnL with EQUITY QW-EQUITY-4's shared fix; keep the QuantLib pricer (`alpha_engine/bond_pricer.py:142-177`) explicitly out of pick PnL until wired + validated.
- **Verify:** UI/payload label changed; a TLT long spanning a distribution date shows total-return PnL.

## QW-BOND-3 · Resolve the ZN=F/ZB=F contradiction (S)
- **Problem:** `walkforward_validator.py:189-196` allows ZN=F/ZB=F as BOND; `asset_class.py:138-139` classifies any `=F` as FUTURES first. Same instrument, two classes, two stat buckets.
- **Fix:** Single rule in the unified classifier: exchange-traded treasury futures = FUTURES with `exposure_class:BOND`. Remove the walkforward exception.
- **Verify:** Grep shows one rule; ZN=F fixture classifies identically in both paths; historical counts restated in the fix doc.

## QW-BOND-4 · Verify the bond-class DB migration (S, read-only check)
- **Problem (peer-raised):** `tools/migrations/20260530_add_bond_asset_class.sql` may not be applied everywhere; live `trading_picks.category` already shows lowercase `bond` 1,603 rows vs canonical expectations.
- **Fix:** Read-only verification (`SHOW COLUMNS`/ENUM check per peer snippet, via `tools/db_env.py` — never paste credentials), then a case-normalisation update for category values (`bond→BOND` etc., all classes) with dry-run counts.
- **Verify:** ENUM contains BOND on all pick tables; `GROUP BY category` returns one spelling per class.

## Subagent-refined (verified file:line — supersedes estimates above)
- **ZN=F removal (S, 2h):** delete the two `=F` lines from `BOND_ALLOWED_SYMBOLS` (`walkforward_validator.py:194-195`); update `tests/test_m020_bond_walkforward.py:43-44` which asserts their inclusion; contract test `BOND_ALLOWED_SYMBOLS ∩ {*=F} = ∅`. (`config.py:906-909` also lists them as FUTURES.)
- **Vacuous pass — actual code locations:** `audit_trail/quality_gates.py:495` BOND `min_trades: 0` and `dashboard_generator.py:6824-6832` returns True when `active_count==0`. Fix: BOND `min_trades→5` (mirror EQUITY `:491`) and drop the `active_count == 0 or` shortcut; apply same to COMMODITY/FUTURES/ETF rows (`quality_gates.py:493-496`). My minTrades=30 display rule and this gate fix are complementary — do both.
- **No OOS Sharpe on train=3/test=2:** raise BOND `min_trades` to 30 in `DEFAULT_CLASS_WF_CONFIG` (`walkforward_validator.py:217`, per its own "revisit at n≥30" note); skipped classes emit `{"verdict":"INSUFFICIENT_DATA","n_trades":n}` stub instead of vanishing (`:285-286`).
- **Benchmark BOND→AGG:** `benchmark_closed_ledger.py:71` BOND→SPY becomes `"AGG"` (fallback TLT); extend `tests/test_benchmark_closed_ledger.py`; regenerate `audit_dashboard/data/benchmark_ledger_proof.json` per AGENTS.md registry.
- **Disclosure stamps:** `instrument_type="bond_etf_proxy"`, `pnl_basis="price_only_ex_distributions"` on BOND rows (`dashboard_generator.py:15436-15501`); QuantLib pricer is referenced only by `tools/run_bond_signal_demo.py:33` — confirmed never in the PnL path.

## QW-BOND-5 · Grow n or stay dark (policy, S)
- **Problem:** n=26 intrabar in total; WR 7.7% suggests possible inversion like ETF — but n is too small to even diagnose confidently.
- **Fix:** Keep BOND dark (no display promotion) until n≥100 intrabar; run the QW-ETF-2-style row audit on the 26 rows now since it's cheap.
- **Verify:** Disposition note on the 26 rows filed with the fix doc; class stays INSUFFICIENT_DATA until threshold met.
