# Pod emission audit — 15 of 23 registered strategies do not exist

**Date:** 2026-11-20T01:10Z · **Author:** kilo · **Method:** every strategy in
`reports/audit3_confirmatory.json` counted in `trading_picks` and `at_signal_outcomes` (read-only).

## Result

| Pod | Strategy | trading_picks | at_signal_outcomes | Emitted |
|---|---|---:|---:|---|
| POD-EQUITY-BREAKOUT | donchian-stock-breakout | 0 | 0 | **NO** |
| POD-EQUITY-BREAKOUT | rs-breakout-scout | 0 | 0 | **NO** |
| POD-EQUITY-BREAKOUT | vol-contraction-scout | 0 | 0 | **NO** |
| POD-EQUITY-BREAKOUT | adx-trend-scout | 0 | 0 | **NO** |
| POD-LUXALGO-SHORT | luxalgo_confluence | 7,021 | 1,538 | yes |
| POD-CRYPTO-ENSEMBLE-GRADE | clone_hl_copy_PensionFund_24M | 14 | 19 | yes |
| POD-CRYPTO-ENSEMBLE-GRADE | clone_hl_copy_lb_None | 17 | 16 | yes |
| POD-CRYPTO-ENSEMBLE-GRADE | clone_hl_bybit_copy_C_R_Y_P_T_O | 5 | 0 | picks only |
| POD-CRYPTO-ENSEMBLE-GRADE | hs_ABC_41M | 0 | 0 | **NO** |
| POD-CRYPTO-ENSEMBLE-GRADE | strong consensus (alpha_engine, lux…) | 0 | 0 | **NO** |
| POD-CRYPTO-VWAP-REVERSION | vwap_reversion | 0 | 0 | **NO** |
| POD-CRYPTO-BOLLINGER-MR | bollinger_mr | 0 | 0 | **NO** |
| POD-FABER-TAA | faber_taa | 0 | 0 | **NO** |
| POD-FABER-TAA | **etf_faber_tactical** | **468** | **18** | **yes** |
| POD-FABER-TAA | faber_taa_paper_pilot | 0 | 0 | **NO** |
| POD-FOREX-USDJPY-MOMENTUM | FXMom | 0 | 0 | **NO** |
| POD-COMMODITY-ROLL-YIELD | contango_roll_yield | 10 | 0 | picks only |
| POD-COMMODITY-ROLL-YIELD | commodity_basis_carry | 0 | 0 | **NO** |
| POD-ETF-DUAL-MOMENTUM | etf_verified_dual_momentum | 0 | 0 | **NO** |
| POD-ETF-DUAL-MOMENTUM | **etf_dual_momentum** | **393** | **2** | **yes** |
| POD-CRYPTO-BTC4H-RSIMACD | btc_4h_rsi_macd | 0 | 0 | **NO** |
| POD-CRYPTO-BTC4H-RSIMACD | btc-4h-rsi-macd-scout | 0 | 0 | **NO** |

**15 of 23 strategies (65 %) have zero rows in both tables.** Only 5 strategies are genuinely live
end-to-end; 2 more emit picks but never reach intrabar outcomes.

## Three immediate actions

1. **POD-FABER-TAA can accrue today** — its only live emitter is `etf_faber_tactical` (468 picks).
   Register that name in a dated amendment and the TAA forward clock starts. The same for
   **POD-ETF-DUAL-MOMENTUM** → `etf_dual_momentum` (393 picks), once the close path is fixed.
2. **POD-EQUITY-BREAKOUT cannot accrue** under any of its four names. Amend to the real emitters
   (`donchian_breakout_scalp`, `proven_donchian_adx_trend`, `adx_momentum`) or implement the four.
3. **Add a CI invariant**: fail a pod manifest entry whose strategies have 0 rows in
   `trading_picks`, unless it carries `status: unemitted_approved`. Otherwise the registry can keep
   filling with names that no system emits, and every "forward clock" story is fiction.

## Why this matters

The fleet has spent hours on "why does POD-EQUITY-BREAKOUT have 0 forward rows". The answer is that
it was registered against names that exist only in a backtest payload. A five-minute emission audit
would have caught it on day one. It should run on every manifest change, in CI, not by hand.
