# Frozen simulation design and execution plan

## What this can prove

It can demonstrate **positive or negative historical modeled account returns**, benchmark comparison and conditional risk under stated assumptions. It cannot prove future repeatability, executable historical fills, independent alpha or capital readiness. The retained history's passive summaries have already been inspected; there is **no virgin OOS claim**.

This is opt-in, offline research. No production wiring, venue credentials, DB mutation, orders or generators. User requested executed simulations on2026-11-15; the dated publication folder is the requested design/spec location.

## Alternatives and choice

1. Reproduce frozen passive portfolios plus one small tactical challenger: simple to audit, credible costs, constrained trial count. **Chosen.**
2. Replay every class's historical picks: more direct but currently missing provenance/open-NAV/cost contracts; cannot safely prove profit yet.
3. Search dozens of strategy variants: likely more attractive curves, but increases overfitting and repeats rejected families. **Rejected.**

## Preregistration before execution

Append two exact next sequential H-NNN records to the canonical registry on GitHub main **before any strategy calculation**. H-datestamp-name entries are a separate namespace, not sequential H-NNN IDs.

- **H-142**, unless concurrently occupied: `wrapper_correct_passive_portfolio_simulation`. Descriptive fixed fund/ETF baseline and risk simulation; not fund ranking or H-141's rejected survivor-selection retune.
- **H-143**, unless concurrently occupied: `single_asset_month_end_trend_replication`. One fixed10-month SPY trend/cash rule, related-family replication/diagnostic of allocation research, not a relabeled independent discovery or a killed VIX/price-factor retune.

No arbitrary family-wide independence is claimed. Record actual allocated IDs and registry commit before execution. Retain prior results and policies. The unchanged trade-level admissibility harness is not invoked on daily NAV marks as fabricated independent picks; these allocation experiments remain **UNTESTED for trade-admission / not capital eligible**.

## Locked data, rules and accounting

- Existing public Yahoo daily caches only: FZROX, FXAIX, VTSAX, SPY, VTI, BND, SGOV;2021-11-15..2026-11-13. Freeze original response hashes and derived CSV hash; verify identity, timestamps, arrays, duplicates, nulls, raw and adjusted close.
- Fixed, survivor-known universe. One vendor; no verified historical purchase eligibility, dead funds, taxes, currency conversion or independent corporate-action audit. This is a limit, not clean selection alpha.
- Passive baseline: each instrument held across the full common history. Also compare FXAIX/SPY/SGOV across the tactical experiment's exact shorter window.
- Tactical rule: at each observed calendar month-end, compare SPY total-return-adjusted close with the simple mean of its latest10month-end adjusted closes. Strictly above mean ->100%SPY, otherwise100%SGOV. No parameters fit, no shorts/leverage/stops.
- Signal at close is **not filled at that close**. Execute at the next common observed close; previous allocation earns returns through that execution close. First entry occurs only after10complete month-ends.
- No partial/incomplete last-month signal. Do not fill-forward missing prices or silently change the universe. Month-end uses the last observed common session; missing instrument dates are audited, not interpreted as a market holiday automatically.
- Model funded USD100,000, fractional total-return units and reinvested distributions implicit in adjusted prices, drifting weights between rebalances, cash allocation explicit. Adjusted prices are total-return modeling units, **not claimed executable raw quotes**; save raw closes as execution-reference evidence.
- Deduct5bps per dollar traded each side, including initial buys and final liquidation. Repeat at20bps as locked cost stress, not an optimized selector. This is a modeled transaction allowance, not observed fills; NAV expenses are already embedded and not deducted twice.
- No outside contributions, borrow or funded leverage. Tax/platform/FX scope excluded and disclosed. SGOV is an investable proxy, not guaranteed cash.
- Report initial capital, daily NAV, execution weights/turnover/costs, terminal liquidation, and source-date/price evidence. Missing/invalid data fails explicitly.

## Locked comparisons and decision rules

Report net total return, calendar CAGR, volatility, cash-relative Sharpe, MDD/recovery and daily tail ES with support, plus SPY excess/IR. No trade-PF/WR from manufactured daily trades.

Tactical comparisons:

1. Same-window SPY, FXAIX and SGOV passive total return.
2. A monthly constant SPY/SGOV mix with the tactical strategy's realized mean SPY exposure: **ex-post exposure diagnostic**, not an investable preselected alpha benchmark.
3. Fixed chronological segments before2025-01-01 and from2025-01-01. Historical reporting splits, not pristine OOS.

Flags remain separate:

- **ABSOLUTE_BACKTEST_PROFIT:** net total return>0.
- **RAW_SPY_OUTPERFORMANCE:** net CAGR>same-window SPY CAGR.
- **RISK_DIAGNOSTIC_IMPROVEMENT:** smaller MDD and higher excess Sharpe than the exposure-matched diagnostic; not factor-alpha certification.
- **ALLOCATION_SCREEN:** tactical after-cost Sharpe>=0.8, MDD<=20%, positive SPY excess in both fixed splits and positive95%paired-bootstrap mean-excess lower bound under all block cases. All conditions required; otherwise FAIL/INSUFFICIENT.
- Capital/admissibility remain false regardless of flags; no forward evidence or genuine untouched holdout exists.

## Simulations, not future probabilities

Use1,000joint circular moving-block paths, seed20261115, block sizes21/60/120sessions, horizons21/63/252/756sessions. Resample contemporaneous portfolio/SPY/cash returns together, preserving within-block dependence. No IID trade-win/average-loss ruin model.

Report conditional fraction of positive wealth, fraction beating SPY, wealth/drawdown quantiles and block sensitivity. These are **historical fitted scenario frequencies**, not calibrated future success/ruin probabilities. Repeating observed blocks does not create independent evidence. Simulated tactical returns replay the already-derived return process; they do not rebuild the policy on synthetic price paths.

Include the predeclared60/30/10joint shocks (-35/-10/0 and -50/-20/0), and clearly distinguish them from simulated strategy execution or stress risk limits.

## Implementation and validation sequence

1. Commit registry entries/protocol to main; save SHA and hashes.
2. Build a standalone stdlib research runner under this folder and freeze derived source CSV.
3. Focused tests: future-data causality, next-close lag, incomplete month, missing/nonpositive/duplicate data, equal-weight concurrent returns, weight drift, transaction costs and no-invention on invalid input.
4. Run exact frozen experiments, retain daily NAV and machine-readable results. Check identities, intervals, sums/costs, flags and reproducibility.
5. Append actual results—positive **and** negative—to this package; do not change rules after observing them.
6. Add a forward tracking/early-elimination protocol by holding horizon. A failed alpha screen is not a proven inability to earn passive beta.
