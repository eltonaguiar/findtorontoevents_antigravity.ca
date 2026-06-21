# Money-Ready Loop — Consolidated Summary (2026-06-19 → 06-20)
**Author:** claude-opus · autonomous 15-min-cadence loop · all findings SQL/endpoint-verified, committed to main via contents-API

## Headline
The loop investigated FRM/CFA concepts + hunted new edge, and converged on a single dominant root cause: **the honest measurement ledger can only resolve ~4% of picks for lack of price-path data.** No new promotable edge was found (0/10 unchanged); two more candidates were honestly refuted; the highest-leverage fix is now scoped and operator-gated.

## Commits this loop (main)
| Commit | Artifact |
|---|---|
| `3b634e72` | H-132 cointegration pairs **REFUTED** (registry) |
| `dd983a66` | **Coverage bottleneck** finding (the big one) |
| `0d41c2b9` | FRM/CFA concepts audit |
| `477dd8f5` | Crypto-OHLCV backfill **runbook** (greenlight-ready) |
| `7f22c8ad` | GARCH band-sensitivity finding |
| `51dc2553` | Carryover status (daily_prices + score=NULL) |
(Earlier in the broader session: H-126..H-131 registry, daily-price-refresh **unmask** `9f501250`, R:R caveat `ddb5326c`, deep-dive synthesis, next-steps build plan.)

## Findings
1. **Coverage bottleneck (root cause).** `at_signal_outcomes` is **95.7% placeholders** — only ~1,837/43,213 rows (4.3%) have a genuine intrabar price-path resolution. Clean per-class n's (CRYPTO 1261, FOREX 148, EQUITY 144…) match all session figures. The resolver can only verdict picks where it has OHLC bars (≈ `crypto_ohlcv` 1h, ~315 syms, ~181d). **Price-path coverage is upstream of every gate, metric, and FRM/CFA technique.**
2. **Cointegration pairs (H-132) REFUTED** — net PF 0.315, WR 21.7%, 14,061 stops vs 41 TPs; IS spreads broke OOS on the 180d window. The one FRM/CFA *edge-opener*, honestly closed (window-limited like funding H-130/131).
3. **FRM/CFA audit** — we already implement ~70% (CI-LB, DSR, PBO, White's, GARCH, cointegration, Kelly, factor model). Gaps: wiring (DSR/White's orphaned from the gate), honesty (CPCV/FDR read banned daily PnL), and the one edge avenue (cointegration, now refuted). Risk/portfolio concepts (HRP, vol-targeting, ES sizing) are **premature** at 0/10.
4. **GARCH asymmetric bands** — a *modest real lever* (lifted a CRYPTO cohort net PF 1.18→1.42, CI-LB 0.83→0.97) but **still sub-bar**, partly mechanical (2:1 R:R), single un-validated param. A lead, not a fix; needs OOS band-param study, ranked below coverage.
5. **"1 active pick" = NOT broken.** Intended scoring funnel (external/experimental/banned feeds unscored → excluded) + deliberately strict gates (score≥55 freeze to 2026-08-18, banned sources, bearish-regime SHORT preference). All picks visible via "Show All Picks".

## Ranked OPERATOR actions (gated — cannot fire autonomously)
1. **Greenlight the crypto-OHLCV multi-year backfill** (`RUNBOOK_crypto_ohlcv_backfill_2026-06-20.md`) — the #1 lever. Bounded top-80 first (~30 min, backed-up, idempotent `--days 1095`), then **re-run the intrabar resolver**, then verify CRYPTO clean-n jumps past 1,261. Directly attacks the 95.7%-placeholder root cause.
2. **Restore the `daily_prices` endpoint** (404 since 2026-04-29; unmask `9f501250` now fails loudly) — unblocks EQUITY honest n (H-126 reversal). FTP-redeploy `fetch_prices.php` OR rewire `scripts/api_integrations.py`.
3. **Approve the COT + crypto-funding DB collectors** (tables confirmed absent) — opens COMMODITY (H-127) + crypto-funding forward lanes per the build plan. Lower priority (funding refuted on current data; COT untested).
4. Deferred/ready-when-needed: max-single-WIN-share gate (spec'd, inert at 0/10); feed CPCV/FDR honest PnL (blocked until coverage grows the clean set).

## Honest bottom line
Still **0/10 promotable** — and now we know precisely why: it's not idea scarcity or insufficient rigor (both are well-covered), it's that **we can only honestly resolve ~4% of our trades for lack of price data.** Every high-value next step is operator-gated. Coverage first; everything else is downstream.
