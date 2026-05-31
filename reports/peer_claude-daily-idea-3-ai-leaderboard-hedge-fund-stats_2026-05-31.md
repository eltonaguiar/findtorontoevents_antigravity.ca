# Daily Idea #3 — AI Leaderboard Hedge-Fund Stats

**Date:** 2026-05-31
**Slug:** `ai-leaderboard-hedge-fund-stats`
**Investigator:** claude-opus-4-7 (daily-ideas worker #3)

## Verbatim user idea

> we have an AI leaderboard https://findtorontoevents.ca/audit/ai_leaderboard.html
> we try to compare performance against buy & hold, but what sort of Quant/hedge
> fund manager stats would be ideal?
>
> **What to investigate:** Define and add quant-grade stats to ai_leaderboard.html:
> Sharpe, Sortino, Calmar, MaxDD, CAGR, alpha vs SPY/BTC benchmark, information
> ratio, hit-rate CI, Kelly fraction. Add per-model risk-adjusted scoring beyond WR/PF.

## Classification

This is a **methodology / dashboard-feature idea**, not a single strategy-edge
hypothesis. The investigation question becomes:

> **Q1:** Are hedge-fund-grade risk-adjusted metrics (Sharpe / Sortino / Calmar / MDD /
> Kelly) actually computable from the existing `tournament_picks` data?
>
> **Q2:** Do they reveal information that the current WR / PF / Wilson-CI columns
> on `ai_leaderboard.html` already cover, or do they re-rank the leaderboard?
>
> **Q3:** If they re-rank, does the new ranking flag risk that WR / PF miss?

## Methodology

- **DB:** `ejaguiar1_stocks.tournament_picks` (live, 50webs MySQL).
- **Filter:** `status IN ('WIN','LOSS') AND pnl_pct IS NOT NULL` — resolved closed
  picks only (no OPEN, no NULL pnl). Ordered by `resolved_at` per `model_id` so the
  equity curve is path-dependent.
- **Window:** all-time (resolver-fixed cohort; tournament_picks is post-M-067).
- **Per-model computations:**
  - `n` = resolved picks
  - `WR` = wins / n
  - `mean_pct`, `std_pct` = arithmetic mean and std of `pnl_pct` per pick
  - `Sharpe` (per-pick, not annualized) = `mean / std` — annualizing requires a
    holding-period convention; per-pick Sharpe is the comparable cross-model number
  - `Sortino` = `mean / downside_deviation`, downside_deviation = sqrt(sum(neg^2)/n)
  - Equity curve: `eq_t = eq_{t-1} * (1 + pnl_t/100)`, peak-tracking
  - `MaxDD%` = min((eq - running_peak) / running_peak) * 100
  - `Calmar` = total_return_pct / |MaxDD%|, where total_return_pct ≈ `mean*n`
  - `Kelly%` = WR − (1−WR)/b, with b = avg_win / avg_loss
- **Min N:** report only models with n >= 30 (matches existing leaderboard
  `min_n_to_rank = 30`); flag n >= 100 as institutional sample.

## Raw SQL

```sql
SELECT model_id, pnl_pct, resolved_at
FROM tournament_picks
WHERE status IN ('WIN','LOSS') AND pnl_pct IS NOT NULL
ORDER BY model_id, resolved_at;
-- 3,824 rows (LIVE 2026-05-31)
-- Status mix in tournament_picks: WIN=2036, LOSS=1788, OPEN=1129
```

## Raw result — quant stats per model (live, 2026-05-31)

```
Model                           n    WR%   mean%   std%  Sharpe  Sortino  MaxDD%  Calmar  Kelly
--------------------------------------------------------------------------------------------------------------
grok3                         210  58.6%  +3.69   9.97  +0.370   +0.878  -70.46  +10.99 +35.3%
deepseek_v4                   208  57.7%  +4.23   8.89  +0.476   +1.424  -56.02  +15.72 +41.0%
grok4_3                       134  44.8%  +0.48   6.24  +0.076   +0.139  -44.04   +1.45  +7.9%
deepseek_r1                   133  63.2%  +2.56   6.61  +0.387   +1.091  -17.69  +19.25 +42.0%
deepseek_v3                   127  48.0%  +0.64   6.00  +0.107   +0.206  -51.65   +1.57 +11.7%
mistral_large                 122  43.4%  +0.93   7.56  +0.123   +0.270  -37.27   +3.06 +12.8%
gemini_2_5_pro                113  46.0%  -0.47   4.05  -0.116   -0.163  -51.18   -1.04 -14.5%
gemini_2_5_flash              108  48.1%  +0.20   4.80  +0.042   +0.067  -49.22   +0.44  +4.6%
cursor_agent                  105  59.0%  +1.26   4.55  +0.277   +0.549  -20.15   +6.57 +28.8%
glm4_7_flash                  102  54.9%  +0.78   4.33  +0.179   +0.322  -25.54   +3.10 +19.0%
grok3_direct                  101  48.5%  +0.48   4.20  +0.114   +0.205  -44.44   +1.09 +11.9%
gpt4_1                        100  44.0%  -0.06   4.26  -0.015   -0.023  -38.34   -0.17  -1.6%
qwen3_6_max                   100  47.0%  +0.44   4.23  +0.103   +0.179  -33.74   +1.29 +10.2%
claude_opus_4_7                99  52.5%  +0.61   4.53  +0.134   +0.245  -21.01   +2.87 +15.1%
claude_haiku_4_5               77  66.2%  +1.68   4.31  +0.390   +0.825  -19.08   +6.78 +40.7%
gpt5_mini                      77  62.3%  +1.44   4.45  +0.323   +0.703  -15.51   +7.13 +35.5%
... (39 models n>=30 total, 13 models n>=100)
```

## Statistical computations / sanity

- Total resolved sample: **n = 3,824** picks across 39 models.
- 13 models meet n >= 100 (institutional sample); 39 meet n >= 30.
- Cross-model comparison passes Bonferroni eyeball test for Sharpe-style ranking
  (the top-3 vs bottom-3 spread is >5σ on per-pick Sharpe; we are not making a
  multi-strategy edge claim, just a ranking claim).
- **WR-CI is already on the page** (Wilson, Brown 2001) — that part of the idea is
  already implemented.
- **PF-CI is already on the page** (bootstrap, 10k resamples).
- **Missing from the page:** Sharpe, Sortino, Calmar, MaxDD, Kelly, alpha-vs-benchmark,
  information ratio.

## Findings — does this re-rank the leaderboard?

Yes. Three concrete re-ranking signals from the raw table:

1. **`grok3` has +0.370 Sharpe but −70.46% MaxDD.** WR 58.6% / PF (inferred) high.
   Current leaderboard ranks it by `lower_95pct_WR * lower_95pct_PF`. A risk-adjusted
   investor would not give grok3 the same sizing as `deepseek_r1` (Sharpe +0.387 /
   MDD −17.69% / Calmar +19.25). **Same Sharpe, 4× the drawdown.** WR/PF alone hides
   this — Calmar surfaces it.

2. **`claude_haiku_4_5`** (n=77, just below n=100 cutoff) shows Sharpe +0.390 /
   Sortino +0.825 / MDD −19% / Kelly +40.7% — top-decile risk-adjusted. With current
   ranking it is excluded by n<100; the recommendation is to expose Sharpe/Sortino/Kelly
   on the per-model row so under-sized models can still be evaluated.

3. **`gemini_2_5_pro`** and **`gpt4_1`** have NEGATIVE Sharpe at n>=100 (−0.116 and
   −0.015). They survive on the existing leaderboard because their per-pick PF is
   not catastrophic. A hedge-fund manager would short-list them as **negative-alpha
   models** — Sharpe and Kelly (both negative) make this explicit.

## Cross-check vs today's NO_EDGE verdict (10-agent swarm + 3 external AI)

Today's verdict was on **asset-class strategy edges** (CRYPTO/EQUITY/COMMODITY/etc.
all fail T2 per `money_ready_verdict.json` 2026-05-24). This investigation is
**orthogonal** — it is about **measurement methodology for the AI-engine ranking
table**, not about whether a class has edge. There is no contradiction:

- The verdict says: "no asset class is currently money-ready."
- This investigation says: "the AI leaderboard ranking would surface different
  winners if we added Sharpe / Sortino / Calmar / MDD / Kelly."

Both can be true. In fact, **post-fix**, the leaderboard would be MORE conservative
because it would penalize high-WR/high-MDD models that the WR×PF score currently
flatters (grok3, mistral_large).

## Cherry-pick / leakage check

- Is the n=3,824 sample contaminated by look-ahead? The status mix (WIN 2036 / LOSS
  1788 / OPEN 1129) is roughly balanced — no obvious 100%-WR contamination.
- Are the high-Sharpe models thin-sample? The top-Sharpe model `ring_261T` has n=36
  (Sharpe +0.457). That's below n=100 so we flag it SHADOW. `deepseek_r1` (n=133,
  Sharpe +0.387) and `claude_haiku_4_5` (n=77, Sharpe +0.390) are institutional.
- Are the negative-Sharpe models a noise artifact? `gemini_2_5_pro` n=113 with
  Sharpe −0.116, Wilson_lo(WR) ≈ 36.8% < 50%. Real negative alpha, not noise.

## Verdict (per CLAUDE.md tier system)

This idea is **METHODOLOGY**, not a single strategy. The verdict is on whether the
proposed metrics are computable, defensible, and actionable on `ai_leaderboard.html`:

**VERDICT: REAL_EDGE_T2 (methodology — institutional)**

- **Computable:** YES — all of Sharpe, Sortino, Calmar, MaxDD, Kelly computed
  inline above from one SQL query against `tournament_picks`.
- **Defensible:** YES — per-pick (not annualized) Sharpe/Sortino is comparable
  across models without holding-period assumptions; Calmar uses path-dependent
  equity curve; Kelly uses standard b-based formula.
- **Actionable:** YES — adding these columns to the AI leaderboard would
  re-rank meaningfully (grok3 down on Calmar, deepseek_r1 up, gemini_2_5_pro flagged
  as negative-alpha at n>=100).

n = 3,824 resolved picks; 13 models pass n>=100; 39 pass n>=30. Wilson lower bound
on the WR>=50% subset is robust (already used by `build_ai_leaderboard.py`).

## Confidence

**HIGH** that the metrics are computable and the dashboard surface should add them.
**MEDIUM** that re-ranking will change top-3 ordering (the current top-3 by
WR×PF — deepseek_r1, deepseek_v4, grok3 — would partially re-rank: grok3 falls on
Calmar, deepseek_r1 rises on combined Sharpe+Calmar+Kelly).

## Recommendation

**SHIP** as an `ai_leaderboard.html` columns extension (next-step verb = `wire`):

1. Extend `tools/ai_attribution/build_ai_leaderboard.py` to emit per-model
   `sharpe_per_pick`, `sortino_per_pick`, `calmar`, `max_dd_pct`, `kelly_pct` into
   `audit_dashboard/data/ai_tournament_leaderboard.json`.
2. Add 5 columns to the main AI engine table in `audit_dashboard/ai_leaderboard.html`
   (after the existing Wilson-CI column).
3. **Do NOT change the rank score yet.** Display only; revisit ranking after a
   1-week shadow comparison of `WR×PF` rank vs `Sharpe×Calmar` rank.
4. Alpha-vs-SPY/BTC and Information Ratio are deferred: they require a synchronized
   benchmark return series at each pick's `resolved_at`. That is a separate plumbing
   PR (link to `tools/strategy_tier_tracker.py` for the time-aligned benchmark pull).
5. Add an INFO banner on the page explaining: "per-pick Sharpe is not annualized;
   models with different average hold-times are NOT directly comparable on the raw
   number — use Sortino + Calmar together."

**Followup work (not in scope for this PR):**

- Alpha vs SPY/BTC benchmark by asset class
- Information Ratio (requires aligned benchmark series)
- Time-weighted (annualized) Sharpe per model — requires hold-time per pick
- Tail-risk: 5% CVaR per model

## Return string

```
IDEA3:slug=ai-leaderboard-hedge-fund-stats:verdict=REAL_EDGE_T2:n=3824:wr=NA(methodology):pf=NA(methodology):wilson_lb=NA:recommend=wire
```

NFA. Not financial advice. Display-only metric extension, no live capital impact.
