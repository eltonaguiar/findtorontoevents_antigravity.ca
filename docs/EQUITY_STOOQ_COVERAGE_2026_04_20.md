# Stooq Equity Coverage Assessment — 2026-04-20

## Status

- `pandas-datareader` is **broken on Python 3.12** in this venv (distutils missing;
  `deprecate_kwarg` signature mismatch vs installed pandas). Installing
  `setuptools` resolves distutils but not the pandas API break.
- Stooq's historical bulk CSV endpoint (`/q/d/l/`) now **requires an API key**
  obtained via captcha on the site (message: "Get your apikey…"). This is new
  gating vs. older docs.
- Stooq's **quote snapshot endpoint** (`/q/l/?s=...&f=sd2t2ohlcv&h&e=csv`) still
  works anonymously and returns the most-recent OHLCV row.

We wrote `alpha_engine/equity_data_stooq.py` which:
- uses the quote endpoint for snapshots (`fetch_stooq_quote`)
- uses the historical endpoint with `STOOQ_API_KEY` env var when available
  (`fetch_stooq_ohlcv`), raising `StooqKeyRequired` otherwise
- retries with backoff, caches responses for 24h under `.cache/stooq/`

## Comparison vs yfinance (5 reference tickers)

| Ticker   | Stooq last | yfinance last | % diff | Notes |
|----------|-----------|---------------|--------|-------|
| SPY      | 2026-04-21 | 2026-04-21   | +0.007% | match |
| AAPL     | 2026-04-21 | 2026-04-21   |  0.000% | match |
| ^GDAXI / ^DAX | 2026-04-21 | 2026-04-21 | n/a | yfinance index close not scalar in this harness |
| 7203.JP  | 2026-04-20 | 2026-04-21   | +3.35% | Stooq one day behind (TSE close timing) |
| NESN.CH  | N/D       | 2026-04-21    | — | **Swiss listings gated** on free endpoint |

No material US divergences (<0.01%). Intraday delta for Japan is expected
(Tokyo close vs snapshot time).

## 20 Proposed Non-US Tickers (all verified on free Stooq endpoint, 2026-04-20/21)

Germany (5): SAP (sap.de), Siemens (sie.de), Allianz (alv.de), BMW (bmw.de), Deutsche Telekom (dte.de)
Netherlands (1): ASML (asml.nl)
UK (7): Shell (shel.uk), AstraZeneca (azn.uk), HSBC (hsba.uk), BP (bp.uk), Rio Tinto (rio.uk), Unilever (ulvr.uk), Diageo (dge.uk)
Japan (4): Toyota (7203.jp), Sony (6758.jp), SoftBank (9984.jp), MUFG (8306.jp)
Hong Kong (3): Tencent (700.hk), Alibaba (9988.hk), HSBC-HK (5.hk)

## Known Gaps (free endpoint)

- **France** (`.fr` / `.pa`) — LVMH, L'Oréal, Airbus, Sanofi all return N/D
- **Switzerland** (`.ch`) — Nestle, Roche all N/D
- **Nordics** (`.dk`, `.no`, `.se`) — Novo Nordisk, Equinor, Ericsson all N/D
- **Korea** (`.kr` / `.ks`) — Samsung 005930 N/D

These need a Stooq API key or fall back to yfinance/TwelveData.

## Usage Notes

- Treat Stooq as a **secondary snapshot source** for cross-validation — NOT a
  sole source. Historical bars require `STOOQ_API_KEY`.
- Time zone: Stooq quote `date`/`time` is local exchange time; normalize before
  comparing to yfinance `Close` (which is already session-close).
- Rate-limit: keep requests ≥0.3s apart; cache aggressively.
- Do **not** add these 20 tickers to active screening until a second source
  confirms each symbol and historical bars are wired (needs API key).
