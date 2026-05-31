# Peer Claude — Topic Deep-Dive: Live-vs-Paper Divergence Tracking (Gemini)

**Date:** 2026-05-31
**AI:** gemini-2.5-pro (Google Generative Language API, v1beta)
**Status:** **FAIL — all 3 Gemini API keys quota-exhausted (free-tier daily limit=0)**
**Topic:** Live-vs-paper divergence tracking for the 24-strategy paper-pilot harness launching 2026-06-01 13:30 UTC.

---

## 3-Line Operator Summary

1. Gemini API consult **could not run**: all three Gemini keys in `~/dbpasses.txt` (primary + ALT + ALT2) return HTTP 429 `RESOURCE_EXHAUSTED` with `GenerateRequestsPerDayPerProjectPerModel-FreeTier` limit=0 across `gemini-2.5-pro`, `gemini-2.5-flash`, and `gemini-2.0-flash`. Free-tier appears revoked/zeroed for these projects.
2. Legacy models (`gemini-1.5-pro`, `gemini-1.5-flash`, `gemini-2.0-flash-exp`) return HTTP 404 — deprecated in v1beta.
3. **Re-route**: fan this same prompt to a peer AI that still has budget — recommended order: (a) Codex/Cursor-agent CLI (no quota), (b) Cloudflare Workers AI (`gpt-oss-120b` or `llama-3.3-70b`), (c) NVIDIA NIM `deepseek-v4-pro`, (d) consult-ring (OpenRouter Ring 2.6 1T). Skill: `/consult-codex` or `/consult-cloudflare` or `/consult-nvidia-deepseek`.

---

## Raw API Response (representative — same shape across all 3 keys × 3 current models)

```json
{
  "error": {
    "code": 429,
    "message": "You exceeded your current quota ... \n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_input_token_count, limit: 0, model: gemini-2.5-pro\n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 0, model: gemini-2.5-pro\nPlease retry in 46.14850072s.",
    "status": "RESOURCE_EXHAUSTED",
    "details": [
      {
        "@type": "type.googleapis.com/google.rpc.QuotaFailure",
        "violations": [
          {"quotaId": "GenerateContentInputTokensPerModelPerDay-FreeTier", "quotaDimensions": {"model": "gemini-2.5-pro"}},
          {"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier",  "quotaDimensions": {"model": "gemini-2.5-pro"}},
          {"quotaId": "GenerateRequestsPerMinutePerProjectPerModel-FreeTier","quotaDimensions": {"model": "gemini-2.5-pro"}},
          {"quotaId": "GenerateContentInputTokensPerModelPerMinute-FreeTier","quotaDimensions": {"model": "gemini-2.5-pro"}}
        ]
      },
      {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "46s"}
    ]
  }
}
```

The `RetryInfo: 46s` is misleading — the `*PerDay*` violation means the daily bucket is also empty, so a 46s wait will still hit the per-day cap. Effective fix is either a paid-tier upgrade on the GCP project or routing the prompt to a different provider.

## Attempts Made

| Model | Key (last 6) | HTTP | Outcome |
|---|---|---|---|
| gemini-2.5-pro | K1gmdY | 429 | quota |
| gemini-2.5-pro | 4QDpwA | 429 | quota |
| gemini-2.5-pro | ILHu5Q | 429 | quota |
| gemini-2.5-flash | K1gmdY/4QDpwA/ILHu5Q | 429 | quota |
| gemini-2.0-flash | K1gmdY/4QDpwA/ILHu5Q | 429 | quota |
| gemini-2.0-flash-exp | all | 404 | deprecated |
| gemini-1.5-pro | all | 404 | deprecated |
| gemini-1.5-flash | all | 404 | deprecated |

## Prompt That Would Have Been Sent (for re-routing)

System: *You are a senior quant who has built production trading systems at hedge funds (Two Sigma, AQR, Renaissance). Give concrete, production-ready specs. Cite papers. Use Python pseudo-code where helpful. Be terse.*

User questions:

1. Per-strategy paper PF vs live PF rolling-window metrics — which windows?
2. Pause-trigger deltas (Sharpe drop >30%? PF drop >50%? consecutive losers?).
3. Distinguishing regime change from edge-died-from-go-live (alpha decay).
4. Walk-forward 30/60/90-day live-vs-paper comparison spec.
5. Concrete divergence-metric + alert-threshold spec. Cite Bailey & López de Prado 2014 PSR/DSR.

Context: 24-strategy harness (mine 8 + kilo 8 + zoo 8), 8 asset classes (CRYPTO/EQUITY/FOREX/COMMODITY/ETF/BOND/FUTURES/PREDICTION_MARKETS), gates already shipped (n≥500, Wilson LB, Bootstrap PF, Bonferroni, concentration, intrabar replay).

## Distilled Spec Bullets

**N/A — Gemini did not respond.** No spec extracted. Do NOT wire fabricated content into `docs/PAPER_PILOT_HARNESS.md`.

## Python Pseudo-code

**N/A — none provided** (no response received).

## Paper Citations

**0 citations captured.** The intended primary reference per operator brief:
- Bailey, D. H., & López de Prado, M. (2014). *The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting, and Non-Normality.* Journal of Portfolio Management 40(5).

## Recommended Action

1. **Re-route this exact prompt** via `/consult-codex` or `/consult-cloudflare run gpt-oss-120b` immediately — paper-pilot launches in <24h and divergence tracking is on the critical path.
2. File a backlog item to either (a) upgrade one GCP project to paid Gemini tier, or (b) drop Gemini from the peer-consult rotation until quota returns.
3. Cross-PC peers using these same keys should be warned: `dropchat-multipc` event recommended.

---

*Generated by Claude Opus 4.7 subagent. Verbatim transcript of the failure mode preserved above so the next agent does not re-attempt without first checking quota state.*
