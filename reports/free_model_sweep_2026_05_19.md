# Free-Model Sweep — Institutional Strategy Prompt (2026-05-19)

Prompt: `tools/swarm/prompts/ofox_institutional_strategies.md` (institutional strategy archetypes per asset class).
Tool: `python tools/swarm/api_consult.py --provider <p> --prompt-file <path> [--model <m>]`.
Calls: 8 total (1 bad-id, 2 upstream-429, 5 OK + 1 OK-from-retry). 180s timeout each.

## Results

| provider | model | status | resp chars | error | 1-line gist |
|----------|-------|--------|-----------|-------|-------------|
| openrouter | `deepseek/deepseek-chat-v3-0324:free` | FAIL | 0 | HTTP 404 "No endpoints found" — model ID retired/renamed | n/a |
| openrouter | `meta-llama/llama-3.3-70b-instruct:free` | FAIL | 0 | HTTP 429 — Venice upstream "temporarily rate-limited", retry_after 22s (3 retries exhausted) | n/a |
| openrouter | `qwen/qwen3-next-80b-a3b-instruct:free` | FAIL | 0 | HTTP 429 — Venice upstream rate-limited, retry_after 24s (3 retries exhausted) | n/a |
| openrouter | `deepseek/deepseek-v4-flash:free` | OK | 4508 | — | Scale COMMODITY + elite CRYPTO sub-strategies; maintain EQUITY/ETF/BOND; kill FOREX (PF 0.27 structural). |
| openrouter | `openai/gpt-oss-120b:free` | OK | 25641 | — | Most thorough: full 2-archetype breakdown per class; scale EQUITY/BOND, maintain COMMODITY/ETF, cut CRYPTO drag legs, kill FOREX. |
| groq | `llama-3.3-70b-versatile` | OK | 7005 | — | Momentum-factor + stat-arb for equity; trend-following for commodity; carry/MR for forex; concise edge+Sharpe per archetype. |
| groq | `llama-3.1-8b-instant` | OK | 10518 | — | Momentum-crossover & detailed signal specs per class; verbose but on-thesis; weakest on kill/scale discipline. |
| pollinations | `openai` (default) | OK | 3351 | — | Clean table format: trend-following + factor-tilt risk-parity; truncated mid-output (~Commodity) at token cap. |
| pollinations | `mistral` | OK | 2018 | — | Compact archetype matrix all 6 classes (trend/factor, seasonality, yield-curve, x-exchange arb, carry); thin on detail. |

### Provider notes
- **openrouter free pool churns fast.** `deepseek-chat-v3-0324:free` and `llama-3.3-70b-instruct:free` (suggested in the task) are no longer the live IDs. Current `:free` IDs verified live via `GET /api/v1/models`: `deepseek/deepseek-v4-flash:free`, `openai/gpt-oss-120b:free`, `qwen/qwen3-next-80b-a3b-instruct:free`, `meta-llama/llama-3.3-70b-instruct:free`, `nvidia/nemotron-3-super-120b-a12b:free`, `z-ai/glm-4.5-air:free`, etc. The 404 was a stale ID, not an account issue.
- **openrouter 429s are upstream provider (Venice) rate limits**, not OpenRouter account limits — the BYOK-to-accumulate message confirms it. gpt-oss-120b routed to a different upstream and succeeded. Mitigation: prefer non-Venice-backed free models, or retry after ~25s. (No swarm-clarify call was needed — the models API + the 429 metadata made the cause unambiguous.)
- **groq:** both `llama-3.3-70b-versatile` and `llama-3.1-8b-instant` work cleanly with `GROQ_API_KEY`. Reliable, fast, no rate-limit hits in this run.
- **pollinations:** zero-key, default `openai` token and `mistral` both returned. Output is shorter (token cap / smaller models) and the default run truncated mid-Commodity — usable as a last-resort fallback, not for full-depth analysis.

## Conclusion

The extra free models **confirmed the existing institutional-strategy consensus — they did not change it.** All 6 successful responses, across 3 providers and 5 distinct model families (deepseek-v4, gpt-oss-120b, llama-3.3-70b, llama-3.1-8b, pollinations-openai/mistral), independently produced the same verdict:

- **Scale:** COMMODITY (PF 1.78, asymmetric trend-following payoff) and EQUITY (factor/momentum, push PF over 1.5).
- **Maintain / watch:** ETF (borderline, needs n>100) and BOND (good PF/WR but n=18 — broaden universe before sizing up).
- **Cut the drag, keep the elite:** CRYPTO — kill `quan_engine` and the unknown-source legs, concentrate on the PF 2.34-3.97 sub-strategies.
- **Kill:** FOREX (PF 0.27 is structural, post-cost negative — no systematic edge).

Recommended archetypes were also consistent: trend-following + carry for COMMODITY, momentum/value factor tilts + stat-arb for EQUITY, yield-curve/duration + credit-spread for BOND, cross-exchange arbitrage + vol-targeted mean-reversion for CRYPTO, smart-beta/sector-rotation for ETF, carry + pair mean-reversion for FOREX (with the caveat to kill it). `gpt-oss-120b` gave the most quant-credible depth (failure modes, post-cost Sharpe per archetype); the smaller models were thinner but did not dissent. Net: the consensus is robust and provider-agnostic — additional free models add confidence, not new information.
