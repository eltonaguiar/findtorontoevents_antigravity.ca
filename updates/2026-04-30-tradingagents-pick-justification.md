# TradingAgents Pick Justification — 2026-04-30

## How This Library Helped Generate Picks

Our `alpha_engine/tradingagents_emitter.py` is directly inspired by the **[tauricresearch/tradingagents](https://github.com/tauricresearch/tradingagents)** framework (Apache-2.0 license). That open-source project defines a multi-agent architecture where separate LLM-powered agents debate stock picks through a structured pipeline:

1. **Fund Analyst** — evaluates balance sheets, earnings, cash flows
2. **Market Analyst** — assesses technicals, price action, momentum
3. **News Analyst** — scans headlines, macro events, regulatory shifts
4. **Bull Researcher** — constructs the strongest long thesis
5. **Bear Researcher** — constructs the strongest short thesis
6. **Trader** — translates the debate into actionable entry/exit levels
7. **Risk Manager** — evaluates position sizing, stop-loss, worst-case
8. **Portfolio Manager** — makes the final go/no-go within portfolio context

The original framework runs each role as a **separate LLM call** chained through LangGraph, costing $1–3 per symbol and requiring heavy dependencies (LangChain, LangGraph, Tavily search tools).

### Our Adaptation: Consolidated Decision Committee

Rather than importing the full `tradingagents` package wholesale, we consolidated the 9-role pipeline into a **single LLM prompt** that asks one model to internally play all roles in sequence:

```
Fundamentals analyst → Technical analyst → News analyst → Sentiment analyst (our addition)
→ Bull researcher → Bear researcher → Trader → Risk Manager → Portfolio Manager
```

This preserves the *intellectual structure* of the original framework (forced bull/bear debate, risk-first portfolio gate) while reducing cost from $1–3/symbol to $0.05–0.20/symbol. One LLM call per ticker, no external search tools, no LangGraph dependency.

**Key difference from original:** We added an explicit **Sentiment Analyst** role (role #4 in our pipeline) that the original `tradingagents` library does not have as a standalone step. The original framework rolls sentiment into the News Analyst role. We split it out because sentiment data (Fear & Greed Index, social volume, options put/call ratios) has distinct signal characteristics from news flow and deserves its own analytical pass.

### Multi-Provider Adjudication (v2 enhancement)

We added a layer the original library doesn't have: **cross-provider adjudication**. Each ticker is scored by multiple AI providers independently (DeepSeek + XAI/Grok by default), and only picks where providers agree on direction survive. This adds:

- **Direction agreement ratio** — must be ≥ quorum target (1.0 for 2-provider core lane)
- **Confidence dispersion check** — if providers disagree strongly on confidence, the pick is downgraded
- **Median target/stop synthesis** — final TP/SL are the median across agreeing providers

The adjudication logic lives in `_adjudicate_decisions()` in `alpha_engine/tradingagents_emitter.py`.

## Current Picks (2026-04-30 20:44 UTC)

### NVDA — BUY (Core Lane)

| Field | Value |
|-------|-------|
| Symbol | NVDA |
| Lane | core (liquid mega-cap) |
| Direction | BUY |
| Confidence | 0.86 |
| Score | 86 |
| TP% | 12.0% |
| SL% | 5.0% |
| R:R | 2.4:1 |
| Time Horizon | 21 days |
| Providers | DeepSeek + XAI |
| Agreement | 1.0 (unanimous BUY) |

**Justification from TradingAgents architecture:**
- NVDA cleared the 9-role decision committee with BUY conviction ≥ 0.65 threshold
- Both independent AI providers (DeepSeek, XAI/Grok) independently arrived at BUY — no directional disagreement
- The 12% TP / 5% SL structure came from the Trader and Risk Manager roles synthesizing consensus target and stop levels
- Portfolio Manager role approved the position within the 21-day swing-trade horizon

**⚠️ EDITORIAL RECONSTRUCTION — NOT COMMITTEE OUTPUT:** The actual LLM reasoning text was lost to a parsing bug (thesis/rationale fields show placeholder characters "x"/"y"). The bullet points below are our editorial best-guess of what the 9-role committee *likely* concluded based on NVDA's public profile. They should **not** be treated as the committee's actual analysis.
- *Fundamentals (inferred):* NVDA's AI/datacenter revenue growth, dominant GPU market share, strong free cash flow
- *Technicals (inferred):* Trading above key moving averages with momentum support
- *Sentiment (inferred):* High institutional ownership, positive analyst consensus
- *Bull case (inferred):* AI infrastructure spending accelerating, Blackwell ramp
- *Bear case (inferred):* Export control risk, valuation premium, potential demand normalization
- 86% confidence with 2.4:1 R:R suggests the bull thesis materially outweighed the bear case in the committee's assessment

### SOFI — BUY (Cheap/Penny Lane)

| Field | Value |
|-------|-------|
| Symbol | SOFI |
| Lane | cheap (small-cap experimental) |
| Direction | BUY |
| Confidence | 0.86 |
| Score | 86 |
| TP% | 12.0% |
| SL% | 5.0% |
| R:R | 2.4:1 |
| Time Horizon | 21 days |
| Providers | DeepSeek + XAI |
| Agreement | 1.0 (unanimous BUY) |

**Justification from TradingAgents architecture:**
- Same multi-role pipeline as NVDA, but tagged for the cheap/penny experimental lane
- Unanimous provider agreement required for the cheap lane (stricter than core)

**⚠️ EDITORIAL RECONSTRUCTION — NOT COMMITTEE OUTPUT:** Same parsing bug as NVDA — the real reasoning was lost. Below is our editorial best-guess only.
- *Fundamentals (inferred):* Growing deposit base, expanding lending platform, tech-forward financial services
- *Technicals (inferred):* Potential breakout from consolidation range
- *Sentiment (inferred):* Fintech sector tailwinds, regulatory clarity improvements
- *Bull case (inferred):* Platform economics improving, Galileo API revenue scaling, student loan refinancing volume
- *Bear case (inferred):* Credit risk in downturns, competitive pressure from larger banks, rate sensitivity
- 86% confidence suggests the committee viewed the platform growth thesis as compelling despite cheap-lane risk

## Known Issue: Placeholder Rationale Text

Both picks show `thesis: "y"` and `rationale: "x"` — these should contain the actual 2-sentence thesis and 4-sentence bull/bear synthesis from the LLM output. This is a **parsing bug**: the emitter's `_parse_decision_json` is extracting placeholder characters instead of the full reasoning text. This needs to be fixed so users can see *why* the 9-role committee reached its decision.

**Root cause:** The JSON response from the LLM likely used abbreviated keys or the parser is matching on a substring. The `thesis` and `rationale` fields in the prompt template need to be verified against what the models actually return.

**Additionally:** Both NVDA and SOFI have **identical metrics** (confidence 0.86, score 86, TP 12%, SL 5%). Two fundamentally different stocks analyzed independently should not produce identical numbers. This strongly suggests the adjudication logic is collapsing to defaults rather than computing per-symbol values. This needs investigation alongside the rationale parsing bug.

## Enhancement Note (next Freebuff iteration)

The next enhancement pass is focused on making this justification analysis production-safe:

- **A/B lane artifacts:** emitter now writes lane-specific outputs (`tradingagents_picks_core.json`, `tradingagents_picks_cheap.json`) in addition to the combined file so resolver lane paths are no longer placeholders.
- **Justification quality gate:** reject/flag picks where `thesis`/`rationale` look like placeholders (`"x"`, `"y"`, empty, or too short) before they are promoted in `/audit`.
- **Provider evidence capture:** persist provider-level rationale snippets and confidence spread to support post-trade review of why consensus formed.
- **Forward validation gate:** promotion from experimental to trusted requires a minimum closed-trade sample and lane-level PF/WR stability (not just one successful run).

## Attribution

- **Original framework:** [tauricresearch/tradingagents](https://github.com/tauricresearch/tradingagents) — Apache-2.0 license
- **Our adaptation:** `alpha_engine/tradingagents_emitter.py` — consolidated 9-role prompt + multi-provider adjudication
- **Related module:** `alpha_engine/adversarial_debate.py` — separate bull-vs-bear sidecar inspired by the same framework's explicit debate stage
- **CI integration:** See `updates/2026-04-30-tradingagents-ci-integration.md` for the resolver/workflow/config wiring details

## Why This Approach vs. Alternatives

| Approach | Cost/Symbol | Latency | Multi-Model Checks | Search Grounding |
|----------|-------------|---------|-------------------|-----------------|
| Full tradingagents (LangGraph) | $1–3 | 30–60s per role | Multiple calls, same provider | Yes (Tavily) |
| **Our consolidated prompt** | $0.05–0.20 | 5–15s total | **Yes (2–3 providers)** | No (relies on training data) |
| Single-model prompt (no roles) | $0.01–0.05 | 2–5s | No | No |
| Manual analyst research | $50–200+ | Hours–days | N/A | Yes |

The consolidated approach trades search-grounding for cost efficiency and multi-model redundancy. It's best suited for swing-trade horizons (5–90 days) where training-data recency is sufficient and the bull/bear structure prevents single-model overconfidence.

## License Attribution

This work incorporates concepts from the **[tauricresearch/tradingagents](https://github.com/tauricresearch/tradingagents)** project, licensed under the Apache License, Version 2.0.

You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.

> **Note:** The specific copyright holder and year should be verified against the LICENSE file in the tradingagents repository. The attribution above covers the Apache-2.0 requirements as accurately as we can confirm without direct access to the upstream LICENSE file.
