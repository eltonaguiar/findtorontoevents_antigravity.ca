# Anonymous AI Council — Strategy Harvest Summary
**Date:** 2026-05-19  
**Purpose:** Harvest institutional-grade strategy ideas from anonymous AI sources for hypothesis pipeline  
**Coverage:** 102 sources tested, 6 returned usable content  
**Key finding:** 3 sources yield genuine counsel (Pollinations.ai, Perplexity.ai, eye2.ai)

---

## Harvested Strategy Ideas

### EQUITY — 2 candidates

#### E-ANON-001: Short-Term Price Momentum (5d/30d)
- **Signal:** Buy when 5-day return > 30-day rolling average; hold 5 days
- **Source:** Pollinations.ai (Jegadeesh & Titman reference), confirmed by Perplexity.ai
- **Causal mechanism:** Investor underreaction + gradual information diffusion → persistent price continuation
- **Academic backing:** Jegadeesh & Titman (1993) — one of the most replicated anomalies in finance
- **M-107 check:** NOT a banned family (distinct from our existing `cta_cross_asset_tsmom` which is 12-month lookback, commodity-focused)
- **Relevance to /money-maker-readyv2:** EQUITY class has WR=46.4%, PF=0.765 (sub-T2). Short-term momentum on liquid small/mid cap could be complementary to existing strategies.
- **Next step:** Pre-register as H-033 candidate; backtest with 5d/30d parameters on EQUITY universe

#### E-ANON-002: Cross-Sectional Momentum (6-12 month, monthly rebalance)
- **Signal:** Buy top decile stocks by 6-12 month past returns; short bottom decile; rebalance monthly
- **Source:** Perplexity.ai (CRSP/Bloomberg data)
- **Causal mechanism:** Same as E-ANON-001 but on longer lookback — classic cross-sectional factor
- **Note:** This is close to our existing `cta_cross_asset_tsmom` — overlap analysis required before pre-registration

---

### FOREX — 1 candidate (already partially covered)

#### F-ANON-001: Interest Rate Carry Trade
- **Signal:** Long currency pair where domestic short-term rate > foreign short-term rate; hold until reversal
- **Source:** Pollinations.ai + Perplexity.ai + eye2.ai (3/3 agreement)
- **Causal mechanism:** UIP deviation — investors earn risk-free spread + risk premium on carry
- **M-107 check:** We already have `forex_carry_g10` (n=13, ephemeral — below 30-pick floor). This counsel supports continuing to accumulate.
- **Relevance to /money-maker-readyv2:** FOREX is sub-floor (PF=0.27 current). Carry is the most academically supported FOREX edge. Validate that `forex_carry_g10` is correctly implemented.

---

### CODE HARVEST — Institutional Pipeline Template

eye2.ai returned a production-grade Python pipeline with:
- `yfinance` for data pull (appropriate for backtesting)
- `TimeSeriesSplit` from sklearn (correct — prevents future leakage)
- `RandomForestRegressor` (appropriate baseline)
- Feature engineering: SMA_10, SMA_50, RSI, Volatility

**Relevance:** This is a usable scaffold for H-028v2 (SEC Form-4 insider cluster-buy) and future equity hypothesis research scripts. The `TimeSeriesSplit` approach matches our `edge_stability_harness` rolling-window methodology.

---

## Connection to /money-maker-readyv2

| Class | Current Status | Council Suggestion | Action |
|-------|---------------|-------------------|--------|
| EQUITY | WR=46.4%, PF=0.765 (sub-T2) | Short-term momentum (5d/30d) | Pre-register E-ANON-001 as research hypothesis |
| FOREX | PF=0.27 (sub-floor) | Carry trade (3/3 AI consensus) | Verify `forex_carry_g10` implementation; accumulate n |
| CRYPTO | PF=2.54 filtered | Not addressed by council | Continue current approach |
| COMMODITY | PF=1.78 (T2 candidate) | Not addressed by council | Continue COT signal work |

---

## How to Leverage /consult-webscrape in the Future

1. **Pre-hypothesis sweep:** Before pre-registering a new hypothesis, run `/consult-webscrape` with a domain-specific prompt to get academic consensus on signal validity.
2. **Tier 1 sources only:** Use Pollinations.ai (direct GET, no browser) + Perplexity.ai (Playwright, direct) for high-quality counsel. Skip blackbox.ai/notegpt.io/andisearch.com (not counsel).
3. **Anonymity:** Currently NOT anonymous (real IP 142.198.176.179). For sensitive queries, ensure Tor is running before using `--proxy socks5h://127.0.0.1:9050`.
4. **Code harvest prompt:** The prompt "Write production-grade Python code for ONE institutional-quality stock prediction pipeline..." works on eye2.ai and chatgot.io. Good for bootstrapping new research scripts.

---

## Files Generated
- `swarm_runs/deep_probe_full102_non_tor_2026-05-19.json` — full 102-source probe results
- `swarm_runs/ai_council_v2_20260519T*/council_v2_results.json` — per-run council results
- `updates/2026-05-19-anonymous-ai-council-transcript.md` — verbatim AI responses
- `updates/2026-05-19-anonymous-ai-council-benchmark.md` — source benchmark / anonymity report
- `updates/2026-05-19-anonymous-ai-council-summary.md` — this file
