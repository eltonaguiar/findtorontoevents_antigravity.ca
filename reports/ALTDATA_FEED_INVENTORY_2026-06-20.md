# Alternative-data feed inventory — no data-feasible NEW edge avenue (2026-06-20)
**Author:** claude-opus · SQL-verified · repo-grounded idea mining (incidents.html + data inventory) per operator request

## Question
With the crypto strategy book proven dead at scale and equity prices frozen, is there ANY data-feasible NEW per-ticker edge avenue in our inventory (insider / sentiment / options / earnings / macro)? Answer: **No.**

## Every candidate alt-data feed is dead, snapshot, or stale (SQL-verified)
| Feed | Rows | Coverage | Verdict |
|---|---|---|---|
| `gm_sec_insider_trades` | 929 (26 tkr) | Jan-Jun 2026 | **17 open-market buys (code P)** — the only informative type (Lakonishok-Lee/Cohen-Malloy use P, not grants/sales/exercises). Far below n_eff≥80. NOT feasible. |
| `gm_news_sentiment` | 140 (28 tkr) | **Feb 11-16 only** | 5-day one-time snapshot, abandoned. Dead. |
| `lm_wsb_sentiment` | 12 | one date | Dead. |
| `lm_bridge_sentiment` | 0 | — | Dead. |
| `social_sentiment` | 0 | — | Dead. |
| `lm_insider_sentiment` | 191 (12 tkr) | monthly mspr | Too thin (12 tickers). |
| `lm_bridge_options` (GEX/PCR) | 12 | snapshot | Dead. |
| `alpha_earnings`/`stock_earnings`/`alpha_fundamentals` | 242-2964 | **frozen 2026-04-27** | Stale; no announce dates (PEAD already forward-shadow per A2). |
| `alpha_macro` (VIX/SPY/yields) | 321 | 2025-03→2026-06 fresh | Usable but **macro-overlay only** (not a per-ticker signal); already wired (vix_regime_gate). |

## Conclusion (honest, per "say so if no avenue exists")
The alt-data collectors ran once ~Feb 2026 and were never scheduled — they are effectively **dead feeds**. There is **no maintained, broad, per-ticker alternative-data source** to build a new equity/multi-asset signal from. Combined with:
- the crypto book having no edge at 11× scale (`CRYPTO_EDGE_AT_SCALE_2026-06-20.md`),
- equity `daily_prices` frozen (404 since 2026-04-29),
- funding + cointegration refuted on the 181d window,
- the honest ledger 95.7% placeholder for lack of price paths,

→ **no autonomous backtest can surface a new edge from current data.** The binding constraint is DATA — both price-path coverage AND the absence of maintained alternative-data feeds.

## What this means for next steps (ranked)
1. **The genuine unlock is data infrastructure, not analysis** — revive + schedule the dead alt-data collectors (insider P-transactions at scale, news/WSB sentiment, options GEX) so a real signal can accrue forward. These are collector/operator tasks, not backtests.
2. **Accrue the one live lead** — crypto rsi5070_us overlay (CI-LB 0.95) toward n-gate; it is the only surviving honest candidate.
3. **Make the canonical ledger honest at scale** — re-resolve the ~14k resolvable crypto placeholders (backup-first) so verdicts reflect the full sample (won't change the no-edge result, but makes the measurement foundation correct).
4. Do NOT keep backtesting current data for new edge — it is exhausted; that would be re-fishing.
