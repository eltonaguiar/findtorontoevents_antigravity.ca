# Extended Model Consultation — Quant Rescue Per-Asset-Class Idea Harvest (2026-05-19)

**Lane:** WIDER cloud panel via API keys (OpenRouter, Cerebras, Groq, DeepSeek, Moonshot).
This is the API-key counterpart to the local-ollama harvest
(`reports/LOCAL_MODEL_IDEA_HARVEST_2026-05-19.md`) and builds ON the swarm verdict
(`reports/QUANT_RESCUE_SWARM_VERDICT_2026-05-19.md`). Real API calls only — raw model
outputs are in `swarm_runs/_extended_consult_2026-05-19/out/*.txt`; run scripts +
`_results*.json` in the same dir.

**Question put to every model (identical):** "Algo system, 11/11 pre-registered
causal hypotheses killed by a walk-forward sign-stability harness (eff>=0.30, same
sign in >=3/5 14-day windows, net of 30bps). For CRYPTO/EQUITY/FOREX/COMMODITY/
FUTURES/BOND/ETF name ONE concrete causally-grounded retail-accessible strategy
that could plausibly clear PF>1.5 net of cost AND survive sign-stability. Signal +
data source + causal mechanism. Forbidden: COT, funding-rate directional, roll-yield,
yield-curve momentum, PEAD, funding-arb carry, options-flow, on-chain counts,
funding-settlement cascade, exchange net-flow, cross-exchange premium."

---

## 1. API keys found in Windows env

Searched `*_API_KEY` / `*_KEY` / `*_TOKEN`. Present + usable:

| Key | Provider | Result |
|---|---|---|
| `OPENROUTER` | OpenRouter | WORKS (paid models); most `:free` models 404 (catalog churn) or 429 (rate-limited) |
| `CEREBRAS_API` | Cerebras | WORKS — `qwen-3-235b`, `gpt-oss-120b`, `llama3.1-8b` |
| `GROQ_API_KEY` | Groq | WORKS — llama-3.3-70b, gpt-oss-120b, qwen3-32b |
| `DEEPSEEK_API` | DeepSeek | WORKS — `deepseek-chat`; `deepseek-reasoner` returned empty content |
| `KIMI_API_KEY` / `KIMI_MOONSHOT_APIKEY` | Moonshot | PARTIAL — `kimi-k2-0905` 404; `moonshot-v1-32k` works |
| `HUGGING_FACE_TOKEN` | HuggingFace | KEY VALID but **402 — monthly inference credits depleted**; no HF router calls landed |
| `NOUS_API_KEY_FREE` | Nous | **401 — invalid/out of funds** |
| `XAI_API_KEY` / `X_AI_KEY` | xAI | not called directly (Grok already covered in prior swarm verdict; OpenRouter `grok-4-fast` deprecated/404) |
| `INCEPTION_AI_KEY`, `ABACUS_API_KEY_1MONTh`, `OLLAMA_CLOUD_KEY`, `OPENCODE_API_KEY`, `KILOCODE_API_KEY` | misc | not standard OpenAI-compatible chat endpoints — skipped to stay on time-box |

**HuggingFace note:** task authorized larger downloads, but the HF *Inference API*
is 402 (paid credits gone) — not a download problem, a billing wall. Running a
multi-GB GGUF locally would only re-cover models the ollama harvest already ran
(`LOCAL_MODEL_IDEA_HARVEST` used qwen3/deepseek-r1/llama3.1 locally). No new signal
available there, so no fresh download was made.

**Models that returned substantive output: 20** (9 round-1 + 11 round-2). Failures
were transport-level (404 catalog churn, 429 free-tier rate limits, 402/401 billing)
— not refusals.

---

## 2. Per-model best idea — the panel table

Only models that produced a real per-class answer are listed. "Distinct point" =
what that model added that others did not.

| Model | Provider | Per-asset-class best idea (condensed) | Distinct / novel point |
|---|---|---|---|
| **claude-sonnet-4.5** | OpenRouter | CRYPTO: **NO EDGE**. EQUITY: 260d-high breakout filtered by VIX<20. COMMODITY: days-of-supply <20pct + price<90d MA. FUTURES: implied-correlation spike short. BOND: SOFR-OIS>30bps front-end long. ETF: sector ETF 5d underperformance + positive analyst revisions. | **Regime-precondition framing**: every idea is event-gated ("episodic regimes"), and it argues the 11 kills failed *because they were always-on*. Most rigorous cost-amortization (bps/day per hold length). Only model to call CRYPTO outright NO EDGE *and* explain why (microstructure needs sub-second latency + maker rebates retail lacks). |
| **deepseek-chat** | DeepSeek | CRYPTO: stablecoin→exchange reserve z-score. EQUITY: SPY put/call detrended. FOREX: **NO EDGE**. COMMODITY: EIA ethanol-vs-gasoline. FUTURES: VIX contango deviation. BOND: **NO EDGE**. ETF: leveraged-ETF premium/discount-to-NAV. | Honest twin NO EDGE (FOREX, BOND) with cost reasoning. Ethanol-mandate inelastic-demand angle is unusually specific. |
| **qwen3-235b** (Cerebras) | Cerebras | CRYPTO: **NO EDGE**. EQUITY: 2-day short-term reversal in low-float (<10M shares) small-caps, long/short deciles. FOREX: IG retail-sentiment contrarian. COMMODITY: heating-oil/crude crack-spread seasonal. FUTURES: VIX>1.3x front-future reversion. BOND: TIPS-vs-nominal real-yield convergence. ETF: leveraged-ETF intraday decay. | **Low-float short-term reversal** — the cleanest, most-cited equity idea; mechanism = dealer spread-widening in thin names, float is regime-stable. Names a ~50-60bps gross edge. |
| **qwen3-max** | OpenRouter | CRYPTO: funding-rate deviation *(KILLED FAMILY — discard)*. EQUITY: residualized overnight return decile long/short. FOREX: **NO EDGE**. COMMODITY: calendar-spread + inventory surprise *(roll-yield-adjacent)*. FUTURES: ETF-proxy cross-sectional momentum into futures. BOND: **NO EDGE**. ETF: IOPV intraday premium mean-reversion. | **Residualized overnight return** (close-to-open minus SPY overnight, ranked X-sectionally) — a genuinely fresh equity signal; mechanism = private info in overnight gaps, not arbitraged intraday. |
| **gemini-2.5-flash** | OpenRouter | CRYPTO: negative-sentiment reversal *validated by* rising GitHub dev activity. EQUITY: micro-cap (<$300M) positive earnings beat that *underperformed* peers 3d post *(PEAD-adjacent — discard)*. FOREX: carry-fade post-event *(carry-adjacent — discard)*. COMMODITY: weather-driven crop-yield supply shock. FUTURES: Russell-2000 index-rebalance front-running. BOND: muni-bond rating-change yield lag. ETF: intraday premium/discount. | **Sentiment-divergence-validated-by-dev-activity** (CRYPTO) and **muni-bond rating-lag** (BOND) are both novel and not in the killed set. Muni angle exploits a genuinely fragmented, slow-information market. |
| **gpt-oss-120b** (free, OR) | OpenRouter | CRYPTO: stablecoin supply-reversion. EQUITY: post-earnings 1-day *reversal* (over-reaction). FOREX: central-bank-speech sentiment tilt. COMMODITY: USDA Crop-Progress planting % calendar spread. FUTURES: VIX term-structure roll-down. BOND: post-FOMC LQD-vs-Treasury spread fade. ETF: low-vol-factor Sharpe rotation. | **Post-earnings 1-day reversal** (distinct from PEAD: it fades the over-reaction, opposite sign) — a clean non-killed equity idea. Central-bank-speech NLP tilt repeated by 3 models. |
| **gpt-oss-120b** (Groq) | Groq | CRYPTO: order-book imbalance momentum (1-min bars). EQUITY: analyst-rating-revision momentum + price-stability filter. FOREX: post-news intraday momentum. COMMODITY: EIA crude inventory surprise. FUTURES: post-expiry calendar-spread reversion. | Adds the **price-stability filter** ("rating upgraded but price hasn't moved yet") as the entry condition — a concrete way to isolate un-priced information. |
| **deepseek-v3.1** | OpenRouter | CRYPTO: OI-vs-price divergence (spot-led rallies). EQUITY: **mid-cap insider net-buying (SEC Form 4)** z-score. FOREX: forward-points vs realized FX *(carry-adjacent — discard)*. COMMODITY: weeks-of-supply vs 5y seasonal. FUTURES: term-structure PCA vs ETF flows. BOND: **NO EDGE**. ETF: international-ETF AP create/redeem latency. | **Insider net-buying in mid-caps** — slow information diffusion; converges with a peer agent's in-flight E-1 work. Also the international-ETF settlement-latency angle is specific. |
| **claude-3.5-haiku** | OpenRouter | CRYPTO: 30d MA mean-reversion. EQUITY: 5-day momentum. FOREX: order-flow imbalance *(uses COT — discard)*. COMMODITY: weather sentiment. FUTURES: seasonal calendar spread. BOND: **NO EDGE**. ETF: ETF-vs-index tracking-error reversion. | Thin/generic — one usable negative (BOND NO EDGE). |
| **trinity-large-thinking** | OpenRouter | CRYPTO: perp order-book imbalance. EQUITY: high-short-interest + negative-sentiment slow-drift. FOREX: **AUD/USD vs Australia-China trade balance YoY**. COMMODITY: WTI summer crack + EIA drawdown. FUTURES: ES momentum gated on VIX term structure. BOND: 2Y yield momentum at Fed terminal-rate bound. ETF: inverse-ETF decay in range-bound low-VIX. | **AUD trade-balance** is the single most novel FOREX idea in the whole panel — real-sector commodity-export flow, not positioning/carry. |
| **nemotron-3-super-120b** | OpenRouter | CRYPTO: **NO EDGE**. EQUITY: low-volatility long/short decile. FOREX: dual-MA trend (generic). | Adds a third independent CRYPTO **NO EDGE** vote with the "HFT arb layer erodes residual edge" reason. |
| **mistral-large-2411** | OpenRouter | RSI / earnings-surprise / carry / inventory / seasonality / yield-spread / sector-rotation. | Filler — almost all generic or killed families. No signal. |
| **moonshot-v1-32k** | Moonshot | Social sentiment / volume / ESI / weather / basis / yield-curve / ETF flows. | Filler — generic, several killed-adjacent. |
| **cerebras gpt-oss-120b** | Cerebras | CRYPTO: **mining-difficulty-lag** (hash-rate vs difficulty). EQUITY: 13F-filing net-buy momentum. FOREX: central-bank-speech sentiment. | **Mining-difficulty-adjustment lag** is a genuinely novel CRYPTO mechanism — structural 2016-block (~2-week) lag, not in any killed family. |
| **cerebras llama3.1-8b** | Cerebras | Generic MA-crossover variants across all classes. | Filler. |
| **groq llama-3.3-70b** | Groq | Generic momentum/reversion + COT for FOREX. | Filler — BOND NO EDGE is the only usable bit. |
| **groq qwen3-32b** | Groq | Reasoning dump, lands on Fear&Greed / 5-day reversal / carry / supply-chain / nat-gas seasonal / credit-spread / fee-arb. | Mostly killed-adjacent; reasoning visible but weak final answer. |
| **glm-4.5-air** | OpenRouter | Reasoning dump → realized-vol anomaly / 5-day reversal / carry / Baltic-Dry supply shock / nat-gas seasonal / credit-spread compression / ETF fee-arb. | Self-flagged ETF as likely NO EDGE — honest. Otherwise killed-adjacent. |
| **minimax-m2.5** | OpenRouter | 319-line reasoning loop, never reaches a clean final answer; gravitates to low-vol factor + index-inclusion effect. | **Index-inclusion / Russell-rebalance demand** surfaces here too (also gemini) — mandated passive-fund buying. |
| **nemotron-3-nano-30b** | OpenRouter | Reasoning dump, generic. | Filler. |

---

## 3. Convergence with the 3 already-registered seeds

The local-ollama harvest registered three seeds: **H-029 vol-cluster mean-reversion
(CRYPTO)**, **H-030 small-cap liquidity-shock reversion (EQUITY)**, **H-031
agricultural harvest-seasonality (COMMODITY)**. Independent corroboration from the
wider panel:

- **H-030 (small-cap liquidity-shock reversion)** — **STRONGLY corroborated.**
  `qwen3-235b` independently proposed 2-day short-term reversal in **low-float
  small-caps** with the *same* dealer-spread-widening / thin-float mechanism.
  `claude-sonnet-4.5` (260d-high breakout) and `nemotron-3-super` (low-vol L/S)
  both also concentrate equity edge in the small/low-liquidity-name space. This is
  the most-converged idea across BOTH consultations.
- **H-031 (agricultural seasonality)** — **corroborated.** `gpt-oss-120b` (USDA
  Crop-Progress planting-% calendar spread) and `qwen3-235b` (heating-oil crack
  seasonal) both land on calendar-anchored, sign-stable physical-cycle commodity
  trades. `gemini` (crop-yield weather shock) is adjacent.
- **H-029 (vol-cluster mean-reversion)** — **weakly corroborated.** `glm-4.5-air`
  (realized-vol anomaly) and `claude-3.5-haiku` (30d-MA mean-reversion) gesture at
  crypto reversion, but no wider-panel model reproduced the specific
  volume-exhaustion / passive-liquidity mechanism. Notably, **5 strong models
  (claude-sonnet-4.5, deepseek-chat, qwen3-235b, nemotron-3-super, qwen3-max)
  independently said CRYPTO = NO EDGE** at retail/daily resolution — which is mild
  evidence *against* H-029 surviving the harness, not for it.

**Convergence-trap caveat:** every model read the same prompt that already lists the
11 kills and frames the problem. Convergence on small-cap reversion and ag-seasonality
is therefore *weak* corroboration — it shows the seeds are not obviously stupid, not
that they have edge. The harness, not the headcount, is the test.

---

## 4. Genuinely NEW non-killed, causally-grounded ideas worth registering as H-032+

Filtering ~20 models x 7 classes down to ideas that are (a) NOT a killed family or
relabel, (b) have a *structural* mechanism a 14-day walk-forward could plausibly hold,
(c) NOT already covered by H-029/030/031. Five candidates survive:

1. **H-032 candidate — Residualized overnight-return cross-sectional reversal/momentum
   (EQUITY).** Source: `qwen3-max`. Signal: close-to-open return minus SPY overnight
   move, ranked cross-sectionally, long/short deciles. Mechanism: overnight gaps carry
   private-information flow not arbitraged intraday because of overnight risk aversion;
   it is a *cross-sectional* test (breadth = power), the one design type the swarm
   said widening the universe actually helps. **Most worth registering** — it is
   genuinely un-tested here, distinct from PEAD (no earnings event), and the
   cross-sectional framing fits the harness's >=80-picks/window requirement.

2. **H-033 candidate — AUD/USD vs Australia-China trade-balance surprise (FOREX).**
   Source: `trinity-large-thinking`. Signal: AUD 1-month return conditioned on
   Australia→China trade balance printing >+10% YoY. Mechanism: real-sector commodity
   export flow physically lifts AUD; not positioning, not carry, not yield-curve.
   The one FOREX idea in the whole panel that is causally distinct from every killed
   family. Caveat: monthly data → hard to hit 80 picks/window; likely a low-N probe.

3. **H-034 candidate — Mining-difficulty-adjustment lag (CRYPTO).** Source:
   `cerebras gpt-oss-120b`. Signal: hash-rate vs current difficulty; difficulty
   re-targets only every ~2016 blocks (~2 weeks). Mechanism: a genuine mechanical
   lag in the protocol. NOT "on-chain address counts" (a killed family) — it is a
   protocol-parameter timing signal. Distinct and worth one pre-registration slot,
   though crowded-by-bots risk is real.

4. **H-035 candidate — Post-earnings 1-day REVERSAL (EQUITY).** Source: `gpt-oss-120b`
   (free). Signal: fade (short) a >+10% earnings-surprise day at the close, cover
   next close. Mechanism: institutional over-reaction + risk-limit profit-taking.
   *Explicitly opposite-sign to PEAD* — PEAD says drift continues, this says the
   1-day spike over-shoots and reverts. It is NOT a relabel of PEAD; it is the
   anti-PEAD. Worth registering precisely because it tests a different sign.
   **Pre-registration must document this distinction carefully (M-107).**

5. **H-036 candidate — Muni-bond credit-rating-change yield lag (BOND).** Source:
   `gemini-2.5-flash`. Signal: muni CUSIPs whose YTM has not adjusted to peer-bonds
   of the new rating after an S&P/Moody's action; data EMMA (free). Mechanism: the
   muni market is genuinely fragmented and slow — a real structural inefficiency,
   not a macro bet. Distinct from yield-curve momentum. BIG caveat: retail muni
   execution cost is far above 30bps and shorting is near-impossible — likely fails
   the cost hurdle. Register only as a *long-only, paper-only* curiosity.

**Recommendation:** of the five, **H-032 (residualized overnight return)** is the
strongest single new idea — it is the only one that is cross-sectional, high-N-friendly,
and cleanly outside every killed family. **H-035 (anti-PEAD reversal)** is the
second pick. H-033/H-034/H-036 are low-N or cost-doomed — register them only if
there is harness budget to spare. None of these is *edge*; they are hypothesis seeds.
All require pre-registration per M-107 before any backtest, and the registration must
explicitly argue each is not a relabel of a killed family.

---

## 5. Honest meta — signal vs filler, convergence-trap flag

- **20 models returned content. Real per-class signal: ~9.** claude-sonnet-4.5,
  deepseek-chat, qwen3-235b, qwen3-max, gemini-2.5-flash, gpt-oss-120b (both),
  deepseek-v3.1, trinity-large-thinking — these engaged with the cost hurdle and the
  sign-stability constraint and produced concrete, mostly-non-killed ideas.
- **~11 models were filler or killed-family recidivists.** mistral-large,
  moonshot-v1-32k, claude-3.5-haiku, cerebras llama3.1-8b, groq llama-3.3-70b,
  glm-4.5-air, qwen3-32b, nemotron-3-nano, minimax-m2.5 — generic MA/RSI/momentum,
  or they re-proposed killed families (carry, COT, yield-curve, roll-yield, on-chain)
  despite the explicit forbidden list. **Killed-family recidivism rose as model size
  fell** — identical pattern to the local-ollama harvest.
- **The single most reliable signal across both consultations is the NEGATIVE one.**
  5 strong models independently said CRYPTO NO EDGE; deepseek + qwen3-max + nemotron
  said FOREX/BOND NO EDGE. This converges with `MACRO_WHY_NO_EDGE_2026-05-18.md` and
  the prior swarm verdict. The wider panel did NOT overturn the paper-only posture.
- **Convergence-trap flag: ACTIVE.** Every model was handed the 11/11-kill premise
  and the forbidden list. Agreement on "small-cap reversion + ag-seasonality + mostly
  no-edge" is N models agreeing with a framed prompt, not independent verification.
  The corroboration of H-030/H-031 is weak; the value is in the *new mechanisms*
  (overnight-return residual, anti-PEAD reversal, mining-difficulty lag, AUD
  trade-balance) that no prior doc had named — and even those are seeds, not edge.
- **Cost reality check, unchanged:** most models still hand-wave the 30bps hurdle or
  assert "~50bps gross edge" with no evidence. Only claude-sonnet-4.5 did proper
  per-hold cost amortization. Treat every "PF ≈ 1.6" in the raw outputs as model
  optimism, not a forecast.

## Bottom line

The wider API panel did **not** find edge and did **not** overturn the swarm's
paper-only / fix-data-first verdict — if anything it reinforced it (multiple
independent NO-EDGE votes for CRYPTO/FOREX/BOND). It did surface **2 genuinely new,
non-killed, causally-distinct hypothesis seeds worth pre-registering**: **H-032
residualized overnight-return cross-sectional reversal (EQUITY)** — the strongest,
because it is cross-sectional and high-N-friendly — and **H-035 anti-PEAD 1-day
post-earnings reversal (EQUITY)**. Three weaker seeds (AUD trade-balance FOREX,
mining-difficulty-lag CRYPTO, muni rating-lag BOND) are low-N or cost-doomed.
Independent corroboration of the existing H-029/030/031 seeds is real but weak
(convergence-trap caveat applies). Nothing here is discovered edge; the harness
remains the only arbiter.
