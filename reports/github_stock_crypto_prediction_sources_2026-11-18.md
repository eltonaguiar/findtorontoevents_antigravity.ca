# GitHub Stock / Crypto Prediction Sources — Scout Report

**Date**: 2026-11-18 (America/Toronto)
**Agent**: kilo (code agent), worktree `auditcopytrader-v3`
**Purpose**: Find GitHub repos that publish stock/crypto/forex/futures/commodity predictions or signals that could be consumed as copy-trader feeds by the audit dashboard. Verify timestamp quality (future-bias safety) and integrability.

---

## 1. Method

- GitHub repository search via `github_search_repositories` with per-asset-class queries (`crypto prediction`, `stock prediction`, `crypto signals`, `forex trading bot`, `futures CTA`, `prediction market`, `equity ETF ML`, `commodity trading`, `alt season`).
- Candidate READMEs pulled via GitHub contents API.
- Independent LLM review fanned out through `tools/consult_multi.py` (providers under `~/dbpasses.txt`).
- Cross-checked against existing `copy_trader_intel/data/external_feeds_research.json` and `research_stock_sources.json` (2026-03-21) to avoid duplicating known leaderboard repos.

**Search limitation**: the GitHub search API returned sparse results for several queries (0 hits for `crypto prediction ML`, `futures CTA`, `equity ETF ML`, `commodity trading`, `alt season`). Candidate set below is therefore not exhaustive; it is the union of what the API returned plus README-verified leads.

---

## 2. Candidate repos

| Repo | Class | Feed? | Timestamps | Active (90d) | Integrable | Notes |
|---|---|---|---|---|---|---|
| `roman-rr/trading-skills` | crypto | **Yes — live signals API + MCP** | Signal-level, auto-verified vs real prices | Yes (pushed 2026-11-17) | Medium | Strongest candidate. Free key = signals + 24h history; Pro = entry/SL/TP. Proprietary license. Preview auth-gated. |
| `ccxt/ccxt` | multi (crypto + prediction markets) | Indirect — market data API, not predictions | Exchange UTC ms | Yes | High | Infrastructure, not a signal source. Use to build feeds. |
| `asavinov/intelligent-trading-bot` | equity/crypto | Yes — ML signal generation | UTC | Yes (pushed 2026-11-17) | Medium | Generates signals from feature engineering; needs export layer. |
| `51bitquant/howtrader` | crypto | Yes — TradingView signal webhook | UTC | Stale (Jun 2026) | Medium | Framework; consume external signals. |
| `JordiCorbilla/stock-prediction-deep-neural-learning` | equity | No public feed | n/a | Yes (Nov 2026) | Low | Model only. |
| `jaungiers/LSTM-Neural-Network-for-Time-Series-Prediction` | multi | No public feed | n/a | Stale (2023) | Low | Model only. |
| `kaushikjadhav01/Stock-Market-Prediction-Web-App-...` | equity | No public API | n/a | Stale (2024) | Low | Web app. |
| `sstklen/trump-code` | equity | No structured feed | n/a | Yes (Nov 2026) | Low | Claims 61.3% hit rate; **future-bias / methodology risk**. |
| `aitradingbotspro/crypto-liquidity-ai-trading-bot` | crypto | No feed | n/a | Inactive (Mar 2026) | Low | Liquidity detection, not signals. |
| `ogunjobiFX/MT4-MT5-Forex-Signal-Copier-Telegram-Bot` | forex | Consumes provider signals | Provider-dependent | Stale (2024) | Medium | Copier, not a source. |
| `bennyjo/phil` | prediction markets | Yes — self-improving agent, paper 24/7 | Trade-level | Yes (pushed 2026-11-18) | Low | Agent, not a feed. |

### 2b. Second-pass candidates (topic search)

Topic queries (`topic:stock-prediction`, `topic:crypto-trading`, `topic:crypto-trading signals`) returned far more hits than keyword search. New leads worth noting:

| Repo | Class | Feed? | Timestamps | Active (90d) | Integrable | Notes |
|---|---|---|---|---|---|---|
| `Travisun/EtherSignals` | crypto (ETHUSDT) | **Yes — live public JSON feed** | `receivedAt`/`pushedAt` UTC, per-signal | Yes (Nov 2026) | High | MIT, self-hostable engine + webhook + Telegram. 12,950 signals total, 402/24h. Trend states + levels, no entry/SL/TP. |
| `CRYPDRYP/aa-signals` | crypto (8 symbols) | **Yes — live API + public backtest** | `generated_at` UTC, per-signal | Yes (Nov 2026) | High | MIT, x402 pay-per-call, 3 free calls/day. Action/confidence/regime, no entry/SL/TP. |
| `Bitget-AI/agent_hub` | crypto | Yes — official Bitget AI toolkit | Exchange UTC | Yes (Feb 2026) | Medium | Toolkit, not a turnkey feed. |
| `Chamanrajragu/purffle-copybot` | crypto | Yes — Hyperliquid copy-trading + backtest | Trade-level | Yes (Jun 2026) | Medium | Copy-bot with backtesting; not a signal feed. |
| `shirosaidev/stocksight` | equity | No public feed | n/a | Yes (Nov 2026) | Low | NLP stock analyzer/predictor; model only. |
| `achillesrasquinha/bulbea` | equity | No public feed | n/a | Stale | Low | ML stock prediction library. |
| `razorbladekisses/Tradingview-Indicators` | multi | Indirect — Pine scripts | n/a | Yes (Nov 2026) | Low | Indicators, not timestamped picks. |
| `sanzol-tech/ai-trader` | crypto | No public feed | n/a | Yes | Low | Trading agent code. |

---

## 3. Verification results

### 3.1 `roman-rr/trading-skills` (top candidate)
- README verified via GitHub API. Claims: 1,595 signals in Oct 2026, 74.7% hit target/profit, +1.41%/signal after 0.12% fees, 401 losses. Self-reported, falling-market month.
- API endpoints: `GET /api/skill/signals`, `/signals/:id`, `/stats` — all require `X-Api-Key`.
- MCP preview endpoint `https://signals.x70.ai/mcp` returns **405 on GET** (requires MCP POST handshake); `/api/skill/signals` returns **401 without key**.
- **Verdict**: promising but **not yet verified**. To clear it we need a free key, then: (a) capture raw signal JSON, (b) confirm each signal has a `created_at`/`timestamp` in UTC, (c) confirm no signal is emitted after the price move it predicts, (d) replay against our own price history with the existing `copy_trader_intel/copytrader_quality_backtest.py` / `multi_asset_backtester.py` plus `audit_trail/copytrader_verification.py`.
- **Tooling note**: `copy_trader_intel/future_bias_check.py` and `copy_trader_intel/source_backtest.py` do **not** exist in this worktree (verified by filename listing and content grep). The available verification stack is `audit_trail/copytrader_verification.py`, `copy_trader_intel/copytrader_quality_backtest.py`, and `copy_trader_intel/multi_asset_backtester.py`.
- **Licensing**: proprietary; commercial redistribution needs a paid license. Internal audit use likely fine, but do not republish signals.

### 3.2 Future-bias flags
- `sstklen/trump-code`: accuracy claim without published methodology or timestamped feed — treat as unverifiable.
- Any repo that only publishes model code (LSTM/ARIMA) has no feed to bias-check; it is a model, not a source.

### 3.3 LLM fan-out status
| Provider | Result |
|---|---|
| aimlapi / gpt-4o-mini | ✅ produced per-repo table + summary |
| deepinfra / llama3.1-8b | ✅ produced generic audit (low specificity; did not read repos) |
| mistral | ❌ HTTP 429 (rate limited) |
| groq / qwen3-32b | ❌ HTTP 404 (model/endpoint) |
| cerebras / llama3.1-8b | ❌ HTTP 404 |
| nvidia / kimi-k2.6 | ❌ HTTP 410 |
| fireworks / kimi-k2p5 | ❌ HTTP 404 |
| nous / Hermes-4-405B | ❌ HTTP 404 |
| together | ❌ HTTP 401 |
| github_models | ❌ DNS failure |
| gemini_api | ❌ client URL bug (key padding) |

Fan-out artefacts: `reports/github_sources_fanout/`, `reports/github_sources_fanout2/`.

### 3.4 `Travisun/EtherSignals` — verified live feed

- Public endpoint `https://ethersignals.com/api/signals` (and `?limit=200`) returns signal JSON without auth.
- Stats: `total: 12950`, `last24h: 402`, `lastSignalAt: 2026-11-18T05:12:01.741Z`, `serverTime: 2026-11-18T05:13:22.585Z`.
- 100-signal page: `receivedAt` range `2026-11-17T23:24:02Z` → `2026-11-18T05:12:01Z`; all timestamps are **in the past** relative to `serverTime` (max skew ~80s) — no future bias.
- Fields: `symbol`, `marketType`, `price`, `timeframe` (2m/5m/30m/2h/1d), `regime` (up/strong_up/down/strong_down/neutral), `score`, `board[]` with per-TF regime/score/prob/patterns, `levels`, `message`, `receivedAt`, `pushedAt`.
- **Verdict**: verified timestamped feed, MIT, self-hostable. Limits: ETHUSDT only, and it publishes trend states/levels rather than entry/SL/TP. Best used as a **regime overlay**, not a direct pick source.

### 3.5 `CRYPDRYP/aa-signals` — verified live API + public backtest

- Free call `GET https://signals.brobotapp.com/v1/signal/BTC` returned `generated_at: 2026-11-18T05:00:00+00:00` (hour-rounded, in the past), `action: flat`, `confidence: 0.0172`, `composite_score: -0.114`, `regime: mean_reverting`, `source: quant-trader-bot v3 + decisionmodels`.
- `GET /api/track_record` (no auth) returns per-symbol backtest: `last_updated 2026-11-14`, rolling ~30-day Kraken 1h window (661 bars), explicit methodology and sample-size caveats. Examples: BTC v3 PF 1.254 / WR 69.4%; ETH v1 PF 4.206 / WR 60%; DOGE v3 PF 0.735 / WR 77.9%; ZEC v1 PF 0.512 / WR 41%.
- Symbols: BTC, ETH, TAO, QNT, ZEC, DOGE, DOG, VVV. License MIT; free tier 3 calls/day, paid via x402.
- **Verdict**: verified live API with honest public backtest. Limits: action/confidence/regime only (no entry/SL/TP), 30-day rolling window is not a long-horizon guarantee. Usable as a **crypto regime/confidence overlay**.
- **Quota confirmed**: by the 08:13Z pull the free tier had returned **HTTP 402 Payment Required** after three calls, confirming the 3/day cap. Cache aggressively or treat as an hourly-at-most overlay.

### 3.6 Independent forward-return spot check (EtherSignals)

Method: took the 100-signal snapshot, fetched Binance `ETHUSDT` 1m klines for the same window, aligned each 2m signal to its bar close, and measured the next-2-minute forward return by regime.

| Regime | n | Avg forward 2m return |
|---|---|---|
| down | 28 | -0.000% |
| strong_down | 17 | -0.008% |
| up | 18 | -0.020% |
| neutral | 1 | +0.071% |

**Verdict**: no measurable directional edge in this ~5h, single-asset sample. `up` signals actually had a slightly negative forward return. This is a small sample and not a rejection of the engine's published stats, but it **argues against deriving synthetic tradeable picks from EtherSignals** without a longer multi-day replay. Use as a descriptive overlay only.

---

## 4. Ranked integration shortlist

1. **`Travisun/EtherSignals`** — verified live timestamped feed (12,950 signals), MIT, self-hostable. ETHUSDT trend/regime overlay only; no entry/SL/TP. Best near-term integration candidate for a regime overlay.
2. **`CRYPDRYP/aa-signals`** — verified live API + public per-symbol backtest, MIT, 8 crypto symbols. Action/confidence/regime overlay only.
3. **`roman-rr/trading-skills`** — strongest entry/SL/TP candidate but auth-gated; gate on free-key verification + future-bias replay.
4. **`asavinov/intelligent-trading-bot`** — active ML signal generator; needs an export/API layer before it can feed the dashboard.
5. **`Bitget-AI/agent_hub`** — official Bitget AI toolkit; plumbing/feed-building rather than a turnkey source.

No equity/forex/futures/commodity repo with a public timestamped prediction feed was found in this pass. The existing `research_stock_sources.json`, `research_forex_sources.json`, `research_commodity_sources.json` remain the better sources for those classes.

**Integration caveat**: the two verified feeds (EtherSignals, aa-signals) do **not** publish entry/SL/TP, so they cannot be registered as pick sources in `SYSTEM_SOURCES` without either (a) treating their regime/confidence as a scoring overlay, or (b) deriving synthetic picks and backtesting them first. Do not wire them as-is.

---

## 5. Blockers / next actions

- [x] Re-run GitHub search with topic queries (`topic:stock-prediction`, `topic:crypto-trading`, `topic:crypto-trading signals`) — done; second-pass candidates in §2b.
- [x] Verify `EtherSignals` live feed timestamps — done (§3.4); no future bias.
- [x] Verify `aa-signals` live API + public backtest — done (§3.5).
- [ ] Obtain free key for `signals.x70.ai` (user decision — requires signup) and run the timestamp/future-bias audit.
- [x] Read-only adapter + future-bias checker built and tested (`copy_trader_intel/regime_feed_adapters.py`).
- [x] Independent forward-return spot check on EtherSignals — no directional edge in the 5h sample (§3.6), so **do not derive synthetic picks** from it yet.
- [ ] Decide whether to wire EtherSignals/aa-signals as a **descriptive regime overlay** in scoring (user decision); do not register in `SYSTEM_SOURCES`.
- [ ] If `trading-skills` clears verification, add a read-only adapter under `copy_trader_intel/` and register it in `audit_trail/universal_pick_resolver.py` `SYSTEM_SOURCES` + `dashboard_generator.py` `JSON_PICK_SOURCES`.
- [ ] Do **not** wire unverified feeds into the dashboard; keep this report as the evidence gate.

---

## 6. Files produced

- `reports/github_stock_crypto_prediction_sources_2026-11-18.md` (this file)
- `reports/github_sources_fanout/aimlapi__gpt-4o-mini.md`
- `reports/github_sources_fanout2/deepinfra_llama3.1-8b.md`
- `toronto-job-kit/` (job board kit — separate workstream)
