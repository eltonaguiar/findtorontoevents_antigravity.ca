# Weekly Loop Scorecard — 2026-06-23 (money-maker-ready June edition)

## MEASURE (honest intrabar ledger, dedup per symbol-dir-day, net of cost)
| class | n | PF | T2 (PF>=1.5,WR>=50,n>=100)? |
|-------|---|-----|------|
| CRYPTO | 1222 | 0.787 | NO (loser overall) |
| FOREX | 118 | 1.218 | NO (marginal +, n>=100) |
| COMMODITY | 128 | 1.161 | NO (marginal +, n>=100) |
| EQUITY | 124 | 0.475 | NO (loser) |
| MEMECOIN | 77 | 0.58 | NO |
| BOND/ETF/FUTURES/UNKNOWN | <=16 | <=1.27 | NO (insufficient-n) |

**0/9 classes pass T2.** Unchanged standing reality.

## Forward-lane candidates (all sub-gate — promotion is FORWARD-lane only, CI-LB>1.15 @ n>=80)
- **crypto_short_volhigh** (CRYPTO SHORT, vol-regime HIGH) — sole cell to pass the robustness-gated miner; netPF 1.83 n=56, bootstrap CI-LB 1.41. BUT multi-regime-untested (68% of trades in one month, only 6/56 in a BTC-up month) -> a down-regime crash-fade pocket, NOT all-weather. n<80. NOT sized. Refs: CRYPTO_SHORT_VOLHIGH_{ROBUST_CANDIDATE,VALIDATION}_2026-06-22.
- **crypto_rsi5070_us** (CRYPTO LONG, RSI50-70, US) — netPF 1.27 n=117, but recent n30 PF 1.08 softening; fails the symbol-bootstrap CI-LB (0.74) — fat-tail-fragile (ex-top-3 symbols net-negative). NOT promotable.
- **forex_trend_aligned** (FOREX, trend-aligned) — netPF 5.72 at **n=20, entirely recent (n30=20, single window)**. Classic small-sample optimism; below the n>=40 mining floor. SHADOW-only; do NOT believe until n>=40 + full falsification (crash-catch/per-symbol/walk-forward/month-concentration). Same shape as the refuted FOREX-consensus + forex_rsi2 n=20 pockets.

## DIAGNOSE (H1-H5)
- H1 measurement: GREEN (ledger + dedup + intrabar resolution working; no halt).
- H2 backtest/small-n: forex_trend_aligned + forex_rsi2 (n=20) — shadow + accrue, never promote at n=20.
- H3 data scarcity: BINDING — cohort recency-weighted, ~93% one BTC-down stretch; no up-regime to test multi-regime robustness. Lever = forward-n + breadth (FRED/CFTC/wider universe).
- H4 external signals: one-sided-resolution sources (youtube:coinbureau 21/21 WON, cta_fx_multifactor 20/20 WON, stocktwits 35/35 LOST) = resolution bias, discount; not edges.
- H5 coverage: one-sided resolution on several sources — extend resolution before judging those sources.

## Cross-check: parallel adversarial swarm (2026-06-22) + this cycle agree
No new robust T2 edge on current data (FDR screen empty; 6 angles NO-EDGE/insufficient). Confirmed again here.

## FORWARD checkpoints
- crypto_short_volhigh: accrue to n>=80 across a genuine multi-month incl-BTC-up window; then re-run full battery + swarm before a tiny downside-hedge paper-pilot.
- crypto_rsi5070_us: REFUTED as promotable (bootstrap CI-LB 0.74); keep tracking only.
- Always-on robust-edge-miner cron (#649/#653) auto-alerts on any NEW cell clearing the full gate.

## RATCHET / deliverables this cycle
- Confirmed picks-now/TTWO feature live + durable (#660-#663; the 11-day stale-page masked-failure fixed at root via reliable plumbing-commit).
- /audit data-feed freshness audit: all live feeds fresh (no other silently-stale surfaces).
- Verdict: size up NOTHING. The bottleneck is TIME + BREADTH, not strategy search.
