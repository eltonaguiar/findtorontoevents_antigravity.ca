# Attribution Probe — Does the AI-tournament edge survive alpha-vs-beta? (2026-06-03)

Applied the #111 return-attribution gate (PR #495) to the live tournament ledger
(`audit_dashboard/data/ai_tournament_picks_latest.json`, 5036 resolved picks) via
`tools/attribution_probe.py`. **Read-only, leakage-free, no DB/ledger mutation.**

## Method (and a data caveat)
`resolved_at` is **batch-stamped** — only ~4 distinct resolved days for 5k picks — so a
daily time series does not exist (same temporal-structure gap as the missing `signal_ts`).
Time-series attribution is therefore impossible on this data. Instead a **cross-sectional,
leakage-free** benchmark is used: for each pick on symbol *s*, the benchmark return is the
**average-agent return on that same symbol** (mean pnl across all models' picks on *s*). A
model's alpha is its excess over the crowd on the symbols it itself chose. Gate: alpha>0 AND
t>=2.0 AND info-ratio>=0.10.

## Headline result
- **`nvidia_deepseek_v4_pro`** — the project's "best edge" (leaderboard PF 3.46): **alpha does
  NOT survive** (n=52, alpha 2.27, **t=1.74 < 2.0**, IR 0.38, **crowd_beta 0.49**). Roughly half
  its return is crowd/beta and the residual alpha is not statistically significant.
- **Every large-sample model fails**: gpt4o (n=271, t=0.99, beta 0.69), cursor_agent (n=127,
  t=1.66, beta 0.84), ring_261T (n=143, t=0.52, beta 1.04), mercury (n=114, beta 0.89). High n →
  crowd_beta 0.7–1.0: these models *are* the crowd.
- The **only 10 models that "pass"** are all **small-n** (26–97 picks): groq_kimi_k2 (n=29, alpha
  7.68), gpt4o_mini (n=33), fireworks_qwen (n=31), gemini_25_pro (n=32), etc. — the exact tiny-n
  sleeves the bootstrap-CI gate (PR #481) already flagged as noise. Their giant "alpha" is
  small-sample variance, not durable skill.

## Conclusion
**No tournament model has BOTH an adequate sample AND surviving alpha.** Under leakage-free
attribution the headline edge is **crowd/beta, not transferable stock-selection skill** — exactly
KTD-Fin's (arXiv 2605.28359) finding, and consistent with `money_ready=[]`. The "PF 3.46 deepseek_v4
edge" should NOT be cited as proven edge.

## Actions
- Demote the "deepseek_v4 = best edge" framing in EAGLE2 docs to "highest paper PF, but fails
  leakage-free attribution (t=1.74, beta 0.49)."
- Promotion prerequisite (already gated via #111): require alpha t>=2.0 + IR>=0.10 at n>=100 on
  out-of-cutoff data before any sleeve is sized.
- Logged as INCIDENT_OVERALL (tournament edge unattributed).

## Reproduce
`python3 tools/attribution_probe.py`
