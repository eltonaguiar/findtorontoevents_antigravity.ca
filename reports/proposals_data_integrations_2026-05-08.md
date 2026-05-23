# Data-Pipeline Integration Proposals — 2026-05-08

**Author:** Claude Opus 4.7 (1M ctx)
**Scope:** Evaluate 4 candidate eltonaguiar/* repos + propose 5 NEW external data sources for `findtorontoevents.ca/audit`.
**Mode:** Read-only investigation. No code changes.
**Inputs verified:** `gh api repos/eltonaguiar/<repo>` for all 4; sampled `data/v2/current.json` schema for STOCKSUNIFY2; cross-checked against `audit_trail/dashboard_generator.py` JSON_PICK_SOURCES registry and `reports/long_term_picks_integration_audit_2026-05-08.md`.

---

## Part A — Evaluation of 4 Identified Candidates

### 1. STOCKSUNIFY2 — `eltonaguiar/STOCKSUNIFY2`

| Field | Value |
|-------|-------|
| Accessible | YES (public, default `main`) |
| Repo size | 9,885 KB |
| Last push | **2026-05-07 21:26 UTC** (active, daily commits "Audit: Scientific Ledger for YYYY-MM-DD") |
| Output format | JSON — `data/daily-stocks.json` (13 KB) + `data/v2/current.json` (8 KB) + history dir |
| Schema | `{version, date, regime{symbol,price,sma200,status}, picks[{symbol, score, rating, algorithm, timeframe, risk, metrics{ulcerIndex, totalReturn, martinRatio}, audit_id}]}` |
| Coverage | EQUITY long/swing horizon, regime-gated, V2 algorithm = "Volatility-Adjusted Momentum" with Ulcer/Martin (DD-aware) |
| Integration cost | **~80 LoC** (one new entry in `JSON_PICK_SOURCES` + a fetch step in `audit-dashboard.yml` to clone or curl raw.githubusercontent of `data/v2/current.json` + asset-class normalizer) |
| Closes gap | EQUITY (Tier-2 candidate at PF 1.41 / WR 52.7% / n=421 — bumping n>=600 stabilizes verdict) |
| Stale-data risk | **LOW.** Daily commit cadence is verifiable via GitHub API + `pushed_at` freshness gate (mirror the mercury2_fast disable pattern: refuse to ingest if `current.json.timestamp` > 36 h old). |
| **Verdict** | **INTEGRATE — highest leverage of the four.** |

### 2. mikestocks / mikestocks_april272025 — `eltonaguiar/mikestocks*`

| Field | Value |
|-------|-------|
| Accessible | YES (both public) |
| Repo sizes | mikestocks 734 KB; **mikestocks_april272025 4,083 KB** (the canonical fork) |
| Last push | **2025-04-27** (>1 year stale) |
| Output format | CSV (`screen_results YYYY-MM-DD HH-MM-SS.csv`) + JSON via `growth_stock_screener/json/*` (reused by penny-skyrocket repo: liquidity, nasdaq_listings, relative_strengths, revenue_growth, trend) |
| Coverage | CAN SLIM growth screener (William O'Neil method) — RS rating, revenue growth, liquidity floors |
| Integration cost | **~120 LoC** but pipeline is **abandoned** — no current data file, would need to fork + run the screener ourselves on a cron |
| Closes gap | EQUITY growth (CAN SLIM signals are differentiated from STOCKSUNIFY2's momentum/regime model) |
| Stale-data risk | **HIGH** — last commit 2025-04-27. Without us running the screener, this is a one-shot dataset. |
| **Verdict** | **DEFER.** Methodology is good (CAN SLIM) but it's a code-fork project, not a live feed. Use only after STOCKSUNIFY2 is wired and we need a 2nd EQUITY long-horizon screen. |

### 3. SCREENER_PENNYSTOCK_SKYROCKET_24HOURS_CURSOR — `eltonaguiar/SCREENER_*`

| Field | Value |
|-------|-------|
| Accessible | YES |
| Repo size | 4,378 KB |
| Last push | **2025-04-26** (>1 year stale) |
| Output format | HTML report (`skyrocket_candidates_24_hours.html` 537 KB) + JSON via `growth_stock_screener/json` (shared with mikestocks) |
| Coverage | Penny stocks + 24h skyrocket detection (EQUITY momentum sub-class) |
| Integration cost | **~150 LoC** to scrape the HTML (no JSON output) OR fork+run the screener ourselves |
| Closes gap | **DUPLICATE of in-repo `alpha_engine/strategies/skyrocket_detector.py` (penny-skyrocket lane)** — already wired but workflow currently broken (5/5 failures, `git add` exit 128 on empty days, see `reports/long_term_picks_integration_audit_2026-05-08.md` §4). |
| Stale-data risk | **CRITICAL** — would replicate a broken in-tree path with even older data. |
| **Verdict** | **REJECT.** Fix our own `penny-skyrocket-runner.yml` (one-line patch: write empty JSON instead of skipping) before adding a stale external mirror. |

### 4. eltonsstocks-apr24_2025 — `eltonaguiar/eltonsstocks-apr24_2025`

| Field | Value |
|-------|-------|
| Accessible | YES |
| Repo size | 315 KB |
| Last push | **2025-04-24** (>1 year stale) |
| Output format | NONE persisted — code-only. `main.py` (33 KB), `data_fetchers.py` (33 KB, asyncio + aiohttp + aiolimiter), `ml_backtesting.py`, `scoring.py`, `sheets_handler.py` (35 KB Google Sheets bridge) |
| Coverage | "Stock Spike Replicator" = portfolio mgmt + ML backtest + risk control framework |
| Integration cost | **HIGH** — this is a *system*, not a feed. ~600+ LoC to extract scoring + spike-replicator logic into `alpha_engine/`. |
| Closes gap | Methodology overlap with our existing `alpha_engine/strategies/skyrocket_detector.py` and `genetic_programmer`. The Google Sheets bridge is unique but we don't need it. |
| Stale-data risk | N/A (no data) |
| **Verdict** | **REJECT as a feed.** Cherry-pick the ML scoring + technical_indicators.py modules into `alpha_engine/integrations/` only if we hit a gap there — but flag as "code archeology", not pipeline integration. |

### Candidates summary

| # | Repo | Verdict | Effort | Edge |
|---|------|---------|--------|------|
| 1 | STOCKSUNIFY2 | **INTEGRATE NOW** | 80 LoC, 0.5 d | EQUITY long, fresh, daily |
| 2 | mikestocks_april272025 | DEFER | 120 LoC + fork+cron, 2 d | EQUITY CAN SLIM (stale) |
| 3 | SCREENER_PENNYSTOCK | REJECT | duplicate of in-tree | (stale) |
| 4 | eltonsstocks-apr24_2025 | REJECT (cherry-pick only) | 600+ LoC | system not feed |

---

## Part B — Five NEW External Data Sources to Add

Scoring rubric: **Edge** = expected uplift to `asset_class_health` PF/WR for the class served (1=marginal, 5=structural). **Effort** = days to ship (1 = single API key + 1 file, 5 = scraper + auth + rate-limit infra). **Maint** = ongoing burden (1=set-and-forget, 5=fragile scrape). **Score** = `(Edge ÷ Effort) × (6 − Maint)`.

| # | Source | What it provides | Asset class served | Edge | Effort | Maint | Score |
|---|--------|------------------|--------------------|------|--------|-------|-------|
| 1 | **FRED (St. Louis Fed) economic data** | DGS2/DGS10 yield curve, DFF fed funds, UNRATE, CPIAUCSL, T10YIE breakevens, DTWEXBGS dollar index — free API, no key required for most series | **BOND** (charter floor n=18, currently strangled), FOREX session-gating, regime classifier upgrade for ALL classes | 5 | 1 | 1 | 25.0 |
| 2 | **CFTC Commitments of Traders (COT)** weekly futures positioning | Net commercial vs non-commercial positioning, % of OI, in 22 futures incl. metals, crude, FX, eurodollar — free CSV from cftc.gov | **COMMODITY** (currently PF 1.78 / WR 46.9% — lift WR via positioning regime), **FOREX** (rescue lane, esp. EUR/JPY/AUD futures) | 4 | 2 | 2 | 8.0 |
| 3 | **SEC EDGAR Form 4 real-time** (insider buys/sells, full-text RSS) | Cluster-buy detection (3+ insiders within 14d), C-suite "open-window" buys, 10% holder accumulation — free RSS + JSON | **EQUITY** (CAN SLIM-style alpha factor; pairs cleanly with STOCKSUNIFY2 momentum) | 4 | 2 | 2 | 8.0 |
| 4 | **Cryptopanic news + sentiment** | Per-symbol news flow + community sentiment + "important" flag — free tier 1 req/sec, 14-day history | **CRYPTO** (currently sub-T2 PF 1.25 — rescue `quan_engine`/`unknown` drag classes via news-quiet regime gating) | 3 | 1 | 2 | 12.0 |
| 5 | **Polygon.io options flow** (free unusual-options ticker, 5 calls/min) | Large block call/put detection, OI delta, IV percentile — Polygon free tier covers EOD options chains | **EQUITY** (most-leveraged conviction signal), proxy for **ETF** (SPY/QQQ flow → regime) | 5 | 3 | 3 | 5.0 |

### Top-5 Ranked by `(Edge ÷ Effort) × (6 − Maint)`

| Rank | Source | Score | Why it wins |
|------|--------|-------|-------------|
| 🥇 1 | **FRED economic data** | 25.0 | One API call, no key, no rate-limit headaches. Yield curve alone unlocks BOND charter and gives regime classifier real macro inputs (instead of SPY-200dma-only). Highest leverage by a wide margin. |
| 🥈 2 | **Cryptopanic news sentiment** | 12.0 | Direct rescue path for the CRYPTO drag classes (`quan_engine` 18% volume @ PF 0.70; `unknown` 7% @ PF 0.35). News-quiet windows are where `dna_winner`/`luxalgo` shine — gating by Cryptopanic flow lets elite strategies breathe. |
| 🥉 3 | **CFTC COT positioning** | 8.0 | Tied #3 for raw score but ranked higher than Form 4 because COMMODITY is closest to T2 promotion (PF 1.78). Crowding-aware FX entries also help the FOREX rescue lane. |
| 4 | **SEC Form 4 cluster-buy** | 8.0 | EQUITY add-on. Pairs with STOCKSUNIFY2 momentum to cover both technical + insider-conviction lanes. |
| 5 | **Polygon options flow** | 5.0 | Lower score because of 5-rpm rate limit and need to pick a small symbol universe; still highest raw Edge (5/5) — graduate to a paid plan once the universe expands. |

### Stale-data pollution guards (apply lessons from `mercury2_fast` disable)

For every new feed, the loader must:
- Stamp a `feed_timestamp` and refuse to ingest if older than the source's natural cadence × 3 (FRED 36 h; COT 10 d; Form 4 6 h; Cryptopanic 4 h; Polygon EOD 36 h).
- Tag picks/factors with `source_freshness=fresh|stale|missing` so the dashboard can grey out stale rows instead of silently mixing them.
- Record the upstream HTTP/API status code + body length to `audit_trail/feed_health_check.py`.
- **Never** raise a kill-switch on a strategy whose only justification is a stale external feed.

---

## Combined ship order (next 2 weeks)

| Sprint day | Ship | Rationale |
|-----------|------|-----------|
| D+0–1 | **STOCKSUNIFY2** wire-up | Already-built feed, daily commits, 80 LoC. EQUITY n→600+. |
| D+1–2 | **FRED** macro feed → regime classifier upgrade | Unlocks BOND charter; helps every class. |
| D+3–4 | **Cryptopanic** news gating for CRYPTO `quan_engine`/`unknown` | Direct PF-rescue lane. |
| D+5–7 | **CFTC COT** → COMMODITY/FOREX | Promote COMMODITY to T2. |
| D+8–10 | **SEC Form 4** cluster-buy → EQUITY | Adds insider-conviction lane to STOCKSUNIFY2 momentum. |
| D+11–14 | **Polygon options** flow (free tier, 50-symbol universe) | Highest raw edge, but rate-limited; ship last. |

Defer mikestocks/SCREENER_PENNYSTOCK/eltonsstocks unless the first six all land and we still need EQUITY breadth.
