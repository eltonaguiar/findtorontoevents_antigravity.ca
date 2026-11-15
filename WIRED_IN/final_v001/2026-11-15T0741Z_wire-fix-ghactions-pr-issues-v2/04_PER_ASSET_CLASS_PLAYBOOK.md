# 04 — Per-Asset-Class Playbook

Format per class: **benchmark · data · best hypothesis · cost floor · binding
gate · current verdict · next action.** All promotion decisions use
`01_PROOF_PROTOCOL.md`.

---

## CRYPTO — benchmark BTC-USD
- **Data:** existing OHLCV cache + `at_signal_outcomes` (intrabar truth preferred
  over daily; daily PF 0.26 vs honest 0.92 = 3.4× inflation).
- **Best hypothesis:** BTC trend filter (SMA200 daily/weekly) as a *risk*
  overlay, not an alpha; then cross-sectional momentum/reversal (H-120) on a
  liquid 12–20 coin universe.
- **Cost floor:** 30 bps RT (15/side) + funding on perps.
- **Binding gate:** Gate 0 (frozen-price cohorts) then Gate 6 (forward n=0).
- **Current verdict:** `NOT_READY` — PF 0.9196, WR 35.87%, n=3,705, DSR 0.0.
- **Next action:** kill `fear_greed_contrarian` (WR 28.3%, n=3,525) and
  `keltner_bounce` (PF 0.995, DSR 0.008); reproduce BTC-SMA200 with a shipped
  script (the cited `experiments/crypto_sma200_oos_protocol.py` is missing);
  register H-120 if the backtest clears Gates 2–5.

## EQUITY — benchmark SPY
- **Data:** daily OHLCV via the quote chain (Finnhub/FMP/AlphaVantage/Polygon),
  survivorship-aware universe.
- **Best hypothesis:** Betting-Against-Beta (BAB) and Quality-Minus-Junk (QMJ)
  have real academic priors; SMA200 trend is a *less-bad beta*, not alpha
  (worse wealth vs SPY).
- **Cost floor:** 12 bps RT + borrow on shorts.
- **Binding gate:** Gate 2 (wealth vs SPY) and Gate 7 (excess t).
- **Current verdict:** `NOT_READY` — PF 0.9392, WR 59.2%, n=250.
- **Next action:** add `equity_vs_spy.py` output to the payload (already exists
  on main); pre-register BAB/QMJ variants with ≥5 for PBO; do **not** promote
  SMA200 on drawdown alone.

## ETF — benchmark SPY (risk-adjusted) / 60-40 (drawdown)
- **Data:** adjusted closes; ETF universe with expense ratios.
- **Best hypothesis:** **H-103 cross-asset dual momentum** — the single
  best-evidenced candidate in the repo (PF 3.57, CI [1.64, 9.69], alpha t 2.36,
  cost-robust to 20 bps). Second: TAA top-5/6m rotation (in-sample only).
- **Cost floor:** 12 bps RT + premium/discount.
- **Binding gate:** Gate 6 — **0 of 100 required forward trades.**
- **Current verdict:** `SHADOW` — backtest strong, forward not started.
- **Next action:** register H-103 in `plan.json` with 152-window target; start
  the forward ledger; log the missing August stamp; publish interim verdicts on
  `/audit` every 20 windows.

## MUTUAL_FUNDS — benchmark category fund
- **Data:** **none** — no NAV feed, `mutual_fund_ranker.py` does not exist.
- **Best hypothesis:** low-cost index tracking + tactical rotation (unbuilt).
- **Cost floor:** NAV + redemption, T+1.
- **Current verdict:** `KILLED (no data path)`.
- **Next action:** either build a NAV ingest (fund company APIs / Yahoo mutual
  fund tickers) behind a flag, or formally declare out of scope in
  `manifest.json`. Do not claim MF coverage until data exists.

## BOND — benchmark AGG
- **Data:** ETF proxies (TLT/BND/SHY/AGG) daily.
- **Best hypothesis:** duration timing (TLT vs SHY) as risk management; SHY
  ballast is explicitly "not an alpha rule".
- **Cost floor:** 12 bps RT.
- **Current verdict:** `INSUFFICIENT_DATA` — n=1, PF 0.0; TLT SMA200 Sharpe −1.19.
- **Next action:** if kept, only as a defensive sleeve with a defined benchmark;
  otherwise eliminate. Never show a BOND "pick" sourced from n=1.

## FOREX — benchmark DXY (or pair B&H)
- **Data:** major pairs; spread-aware.
- **Best hypothesis:** carry + momentum (academic prior), with London-breakout as
  a session overlay.
- **Cost floor:** spread + 1 pip + swap.
- **Current verdict:** `NOT_READY` — PF 0.6596, WR 32.19%, WF-OOS PF 0.48;
  `FOREX_HARD_DISABLE=1` is set (good).
- **Next action:** keep hard-disabled until a carry hypothesis clears Gates 2–5
  net of FX costs including swap. The plan-level "WR 6.82% / DSR fail" and the
  live "WR 32% / dsr_ok true" contradiction must be reconciled first.

## COMMODITY_FUTURES — benchmark GLD / underlying B&H
- **Data:** GLD/gold, oil, and a cleaned CFTC COT series.
- **Best hypothesis:** GLD SMA200 trend (weak) + COT positioning **only after**
  the 93.8% contamination is corrected (post-dedup WR ~40%, PF ~0.17).
- **Cost floor:** 1 tick + commission + roll.
- **Current verdict:** `WATCH` — PF 1.0256 but **negative expectancy −0.0017**
  (gate-logic incoherence; WATCH must require positive expectancy).
- **Next action:** fix the WATCH rule to require expectancy > 0; re-run COT on
  deduped data; do not promote on PF alone.

## PENNY — benchmark IWM
- **Data:** IWM + low-priced equities; wide spreads.
- **Best hypothesis:** none credible; n=4 is not a sample.
- **Cost floor:** 60 bps RT + slippage.
- **Current verdict:** `KILLED (insufficient sample)`.
- **Next action:** keep as high-risk illustrative sleeve only; never "money
  ready". If anything, test a liquidity/quality filter first.

---

## Cross-class ranking for the next forward test

| Rank | Class | Hypothesis | Prior strength | Why now |
|------|-------|------------|----------------|---------|
| 1 | ETF | H-103 dual momentum | **highest** (PF 3.57, CI>1) | only candidate with a real backtest artifact |
| 2 | CRYPTO | BTC trend overlay | medium (wealth beat, unverified) | huge live sample to clean |
| 3 | EQUITY | BAB / QMJ | medium (academic) | cheap to pre-register |
| 4 | FOREX | carry+momentum | low-medium | must clear FX costs |
| 5 | COMMODITY | cleaned COT | low | data cleanup required |

Everything below rank 5 stays killed or illustrative.
