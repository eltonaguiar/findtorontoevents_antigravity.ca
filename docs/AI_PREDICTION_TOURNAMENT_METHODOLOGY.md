# AI Prediction Tournament — Methodology

**Project:** findtorontoevents.ca/audit/ai-tournament  
**Version:** 1.0 — 2026-05-19  
**Status:** ACTIVE — Forward-testing begins at publication

---

## 1. Purpose

Pit every cloud AI model family we have API access to against live financial markets. Each model is asked to:

1. Choose its own symbol universe (and justify why)
2. Generate a complete, production-grade trading strategy per asset class
3. Produce specific forward-test picks with entry price, direction, TP, SL, and confidence

We track performance on live market data, rank models by realized edge, and compare their predicted strategies to our own validated strategies in the main audit dashboard.

This is a **tournament**, not a benchmark. Models compete against each other and against our own system on real forward P&L.

---

## 2. Tournament Rules

### 2.1 What "counts"

- **Forward-test only.** Any pick submitted AFTER the tournament start date counts.
- **Backtests are recorded** but are secondary, verified for data integrity (see §5), and never used to rank models in the forward-test leaderboard.
- **A pick is valid** if it includes: symbol, direction (LONG/SHORT), entry price, take-profit (TP), stop-loss (SL), asset class, and a one-paragraph strategy rationale.
- **Invalid picks are discarded.** No retroactive adjustments.

### 2.2 Resolution

| Asset class | Resolution window | Win condition |
|---|---|---|
| EQUITY | 30 calendar days | Exit at TP or SL; mid-point if neither hit |
| CRYPTO | 14 calendar days | Exit at TP or SL |
| COMMODITY | 28 calendar days | Exit at TP or SL |
| FOREX | 10 calendar days | Exit at TP or SL |
| ETF | 30 calendar days | Exit at TP or SL |
| BOND | 60 calendar days | Exit at TP or SL |

### 2.3 Scoring

Each model is scored on its **forward-test picks only**:

- **Win rate (WR)** — picks closed at TP / total resolved
- **Profit factor (PF)** — sum of winning pnl_pct / abs(sum of losing pnl_pct)
- **Strategy consistency** — were the picks actually consistent with the stated strategy, or did the model contradict itself?
- **Hallucination penalty** — any pick based on fabricated data gets a -1 pick penalty applied to its total

### 2.4 Leaderboard tiers

| Tier | PF | WR | Human label |
|---|---|---|---|
| T1 | ≥2.0 | ≥55% | Exceptional |
| T2 | ≥1.5 | ≥50% | Institutional grade |
| T3 | ≥1.3 | ≥45% | Acceptable |
| BELOW | <1.3 | <45% | Below threshold |

---

## 3. Participant Model Matrix

### Phase 1 — Cloud (launch immediately, parallel where different API keys)

| Model family | Provider | API key env var | Parallel OK? |
|---|---|---|---|
| Mercury (inception-labs) | OpenRouter | OPENROUTER_API_KEY | Yes |
| Cerebras llama-4-scout | Cerebras | CEREBRAS_API_KEY | Yes |
| Ring-2.6-1T | OpenRouter | OPENROUTER_API_KEY | Yes (same key, rate-limit) |
| Grok-3 / Grok-3-mini | xAI | XAI_API_KEY | Yes |
| DeepSeek-R1 | DeepSeek | DEEPSEEK_API_KEY | Yes |
| GPT-4o / o3-mini | OpenAI | OPENAI_API_KEY | Yes |
| Claude Opus 4.7 | Anthropic | ANTHROPIC_API_KEY | Yes |
| Gemini 2.5 Pro | Google | GOOGLE_AI_API_KEY | Yes |
| GLM-4 | OFOX/ZhipuAI | OFOX_AI_KEY | Yes |
| Qwen3-235B | OpenRouter | OPENROUTER_API_KEY | Rate-limit |
| Mistral Large | Mistral | MISTRAL_API_KEY | Yes |
| Command R+ | Cohere | COHERE_API_KEY | Yes |

### Phase 2 — Local models (future, after Phase 1 complete)

- gemma3:1b, llama3.2:1b, qwen2.5:1.5b, qwen3:14b, deepseek-r1:14b (already benchmarked for speed — see `updates/2026-05-19-local-model-challenge-log.md`)

---

## 4. Prompt Protocol — `/noshortcutsprompt`

Every model receives this exact system prompt to prevent shortcuts, partial code, or hallucinated data:

```
Act as a senior quant researcher at a top hedge fund.
We need production-grade, mathematically rigorous, and thoroughly verified strategies for this task.

Requirements:
- Think step by step and show your reasoning before writing any code or picks.
- Double-check every formula and assumption against standard references (cite the exact source if possible).
- Use full type hints, complete docstrings, and include safety checks (e.g. minimum sample size, no lookahead bias).
- Output ONLY ready-to-apply strategies with: symbol, direction, entry_price, take_profit, stop_loss, confidence (0-1), asset_class, and a full strategy rationale.
- If anything is approximate or simplified, explicitly call it out and provide the full rigorous version instead.
- Explicitly state your data sources and date ranges. DO NOT fabricate historical data.
- If you cannot access real data for a claim, say so rather than inventing numbers.

Current live dashboard: https://findtorontoevents.ca/audit/
Task: [asset-class-specific prompt below]
```

### 4.1 Per-model prompt additions

For each model, append:

```
Your task: 
1. Choose your preferred symbol universe for [ASSET_CLASS] trading. 
   Justify each inclusion (liquidity, data availability, your prior conviction, economic rationale).
2. Design ONE primary strategy for [ASSET_CLASS]. Name it. Describe the exact entry/exit logic.
3. Generate [N] specific forward-test picks valid from today [DATE].
   For each pick: symbol | direction | entry_price | take_profit | stop_loss | confidence | rationale
4. State which historical period your strategy performed best in and cite the source.
5. What is the primary failure mode / when does this strategy NOT work?
```

---

## 5. Data Integrity Verification

Every model's backtest claim is checked before being posted to the leaderboard:

### 5.1 Hallucination check

For any claimed backtest metric (e.g., "WR=72% from 2020-2024"):
1. Pull the actual OHLC data for the stated symbols via yfinance / Binance API
2. Re-run the stated entry/exit logic on that data
3. Compare realized WR/PF to claimed WR/PF
4. Tolerance: ±5 percentage points. If outside → label `BACKTEST_DISPUTED`
5. If the model claimed data it cannot have accessed (e.g., live order book data from 2019) → label `HALLUCINATION_CONFIRMED`, apply -1 pick penalty

### 5.2 Lookahead bias check

- Verify no entry signal uses same-bar close price to enter at open
- Verify no strategy uses future-dated features in its signal
- Scripts: `alpha_engine/validation/statistical_gates.py` — DSR and PBO checks apply

### 5.3 Real vs fabricated data flag

The audit page shows a **clear visual distinction** between:
- 🟢 `FORWARD_TEST` — live market, data pulled post-tournament-start
- 🟡 `BACKTEST_VERIFIED` — historical, independently reproduced
- 🔴 `BACKTEST_DISPUTED` — claimed but not reproducible within ±5%
- ⚫ `HALLUCINATION_CONFIRMED` — fabricated data confirmed

---

## 6. Price Tracking Infrastructure

### 6.1 GitHub Actions workflow

A daily GHA job (`ai-tournament-price-tracker.yml`) runs at 23:00 UTC:
1. Fetches current prices for all open picks across all models
2. Uses 3-tier failover: Binance API → CoinGecko → KuCoin (CRYPTO); yfinance → Alpha Vantage → Tiingo (EQUITY/ETF); FRED → CMC Markets → Quandl (COMMODITY/BOND)
3. Resolves any pick where price hit TP or SL
4. Writes results to `data/ai_tournament/picks_<date>.json`
5. Updates `audit_dashboard/data/ai_tournament_leaderboard.json`
6. The audit page auto-refreshes from this JSON

### 6.2 Pick storage schema

```json
{
  "model_id": "grok-3",
  "provider": "xai",
  "pick_id": "grok3-001",
  "submitted_at": "2026-05-19T00:00:00Z",
  "asset_class": "EQUITY",
  "symbol": "NVDA",
  "direction": "LONG",
  "entry_price": 875.20,
  "take_profit": 950.00,
  "stop_loss": 840.00,
  "confidence": 0.72,
  "strategy_name": "AI_Capex_Cycle_Momentum",
  "rationale": "...",
  "status": "OPEN",
  "current_price": null,
  "exit_price": null,
  "pnl_pct": null,
  "resolved_at": null,
  "data_integrity_flag": "FORWARD_TEST",
  "backtest_claimed_wr": null,
  "backtest_verified_wr": null
}
```

---

## 7. Audit Page Design — `/audit/ai-tournament`

### 7.1 Page sections

1. **Hero banner** — "Which AI model is best at predicting markets? Find out live."
2. **Leaderboard** — ranked table: Model | WR | PF | Tier | n_picks | Last updated
3. **Per-model cards** — one card per model showing:
   - Model name + provider logo placeholder
   - Strategy description
   - Symbol universe with justification
   - Forward-test picks table (live P&L, color-coded)
   - Backtest claims + verification status flag
4. **Data integrity legend** — prominent at top (🟢/🟡/🔴/⚫)
5. **Comparison panel** — overlay model strategy vs our validated strategy per asset class
6. **Methodology link** — links to this document

### 7.2 Link from main audit page

Under the "Quick Links" or "Explore" nav section of `audit_dashboard/template.html`:
```
AI Model Tournament → /audit/ai-tournament
```

---

## 8. Execution Sequence

### Phase 1A — Infrastructure (this session)

1. Create methodology doc (this file) ✓
2. Create `/noshortcutsprompt` skill ✓
3. Run Grok + Cerebras + Ring on methodology for critique/refinement
4. Create audit page HTML skeleton
5. Create GHA price tracker workflow skeleton
6. Create pick storage JSON schema files
7. Commit all scaffolding

### Phase 1B — Model prompt execution (next session)

1. Send prompt to Mercury, Cerebras, Ring (parallel)
2. Send prompt to Grok, DeepSeek, GPT-4o, Gemini (parallel — different keys)
3. Send prompt to Claude Opus, GLM-4, Mistral, Command R+ (parallel)
4. Collect raw responses, run hallucination checks on all backtest claims
5. Ingest valid picks into `data/ai_tournament/`

### Phase 1C — Live tracking (automated after 1B)

1. GHA runs daily price tracker
2. Picks resolve over 10–60 day windows
3. Leaderboard updates automatically
4. Report generated monthly: which model was actually right

### Phase 2 — Local model expansion (future)

After Phase 1 completes its first resolution cycle, run the same protocol against local Ollama models (prioritize gemma3:1b and qwen2.5:1.5b — fastest GPU throughput per `updates/2026-05-19-local-model-challenge-log.md`).

---

## 9. Comparison to Our Own Strategies

At the end of Phase 1's first resolution cycle, publish a comparison table:

| Asset class | Best AI model | AI strategy | Our system strategy | AI WR | Our WR | AI PF | Our PF |
|---|---|---|---|---|---|---|---|
| EQUITY | TBD | TBD | PACP shadow scoring | — | 49.2%* | — | 0.760* |
| CRYPTO | TBD | TBD | quan_engine scalp | — | 44.6%* | — | 1.25* |
| COMMODITY | TBD | TBD | CTA trend + COT | — | 46.9%* | — | 1.78* |

*Current system stats from audit dashboard as of 2026-05-19.

This becomes the core editorial of the page: not just "which AI won" but "did any AI discover a better strategy than what our system is already running?"

---

## 10. Ethics and Disclaimers

- All picks are for research/tracking purposes only. Not financial advice.
- Model picks are stored as-is; we do not edit or curate to make any model look better.
- If a model refuses to make specific picks, it is listed as `NO_PICKS_SUBMITTED` and excluded from ranking.
- We disclose when a model is from Anthropic (Claude) and that the system itself runs on Claude Code — potential conflict of interest.
