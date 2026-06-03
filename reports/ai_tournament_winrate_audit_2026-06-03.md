# AI Tournament Leaderboard — Win-Rate Verification & Resolver Audit (2026-06-03)

Surface: https://findtorontoevents.ca/audit/model.html?id=fireworks_qwen (Goal #1)
Trigger: "fireworks_qwen supposedly has 90% win-rate — double-check each metric, then all strategies ≥70% WR."

## TL;DR verdict

The leaderboard arithmetic is **internally correct** (every metric reproduces from
the raw picks), BUT the headline numbers are **NOT a trustworthy real-money edge.**
The 80–90% win rates are an **artifact of the resolution engine**, not realized alpha.
All six ≥70%-WR "strategies" are AI *models* in a 4–14-day-old paper tournament,
resolved by a coarse once-a-day spot-price snapshot. Treat T1 tiers as UNPROVEN.

## Models audited (all ≥70% WR, rank-eligible)

| model | WR (LB / recomputed) | PF | n_picks | n_resolved | tier | data age |
|---|---|---|---|---|---|---|
| fireworks_qwen | 90.3% / 90.3% | 26.99 | 50 | 31 | T1 | 4 days |
| gpt4o_mini | 90.9% / 90.9% | 23.47 | 49 | 33 | T1 | 14 days |
| gemini_25_pro | 87.5% / 87.5% | 16.62 | 50 | 32 | T1 | 4 days |
| together_deepseek_v3 | 87.5% / 87.5% | 13.44 | 50 | 32 | T1 | 4 days |
| hyperbolic_llama | 78.1% / 78.1% | 8.90 | 50 | 32 | T1 | 4 days |
| nvidia_minimax_m2 | 73.5% / 73.5% | 4.66 | 67 | 49 | T1 | 6 days |

Recompute matched the leaderboard exactly. Trustworthiness filter
(`is_resolution_trustworthy`) flagged **0** timestamp anomalies and **0** TP/SL
violations across all six. Concentration is LOW (symbol HHI ≈ 0.05, well below the
0.30 gate) — so this is NOT the CRYPTO-78.9% concentration/leakage problem.
The problem is upstream, in how WIN/LOSS is decided.

## Root cause #1 — coarse single-snapshot resolver (the win inflator)

`tools/ai_tournament/price_tracker.py:resolve_pick()` (also the production DB path
`resolve_db_picks.py`, which imports the same function):

- Fetches **one current spot price per day** (GHA cron), then:
  `tp_hit = current_price >= tp` checked **before** `sl_hit = current_price <= sl`.
- **No intrabar path.** It never looks at the candle high/low — only the single
  spot value at the moment the job runs. (The docstring claims "Gap-through: fill
  at candle extreme" — the code does not implement this.)
- P&L is booked at the **barrier price**, not a realized fill:
  win pnl ≡ TP distance (−slippage), loss pnl ≡ SL distance. That's why win sizes
  are near-uniform (~+8.5%) and losses near-uniform (~−3%) across every model.

Consequence: a pick that dips through SL intraday but has recovered above SL by the
daily sample is left OPEN, and later books as a clean TP WIN. Intraday SL touches
are systematically invisible → losers are converted to winners.

## Root cause #2 — the barrier-asymmetry paradox (statistical impossibility)

Across ALL picks, models place TP **farther** than SL (reward:risk ≈ 2.2–2.4 : 1):

| model | mean TP dist | mean SL dist | R:R | breakeven WR |
|---|---|---|---|---|
| fireworks_qwen | 8.67% | 3.67% | 2.36 | 29.7% |
| gpt4o_mini | 8.66% | 4.09% | 2.12 | 32.1% |
| gemini_25_pro | 8.83% | 4.02% | 2.20 | 31.3% |
| together_deepseek_v3 | 8.69% | 3.86% | 2.25 | 30.8% |
| hyperbolic_llama | 8.80% | 3.89% | 2.26 | 30.6% |
| nvidia_minimax_m2 | 9.14% | 4.30% | 2.12 | 32.0% |

A **closer SL should be hit first more often** under any realistic price path, so an
unbiased resolver would yield WR *below* 50% — likely near the ~30% breakeven implied
by the R:R. An observed 80–90% WR with the SL closer than the TP is statistically
implausible and is the fingerprint of the snapshot resolver missing SL touches.
PF is then mechanically inflated: PF ≈ (WR·TP)/((1−WR)·SL); at WR 90%, R:R 2.4 →
PF ≈ 21+, with no realized-edge content.

## Root cause #3 — small n + young data + selection bias

- n_resolved 31–49, all **< 100** (repo's "proven" bar). fireworks_qwen has only
  **4 days** of picks. This is not a track record.
- Of 50 picks, ~16–19 remain OPEN. The OPEN cohort is dominated by **long-timeframe**
  picks (60d bonds, 30d SPY/INTC, 28d HG=F) while resolved picks closed in ~14h median.
  Fast-resolving volatile picks self-select into the resolved set → survivorship bias.

## Root cause #4 — Score is partly a bootstrap-floor artifact

Score = wr_ci_lo × pf_ci_lo. With only 3 losses, most bootstrap resamples contain
**zero losses**, so `bootstrap_pf_ci` returns its hard-coded **10.0 floor** for
pf_ci_lo. fireworks_qwen's score 7.510 = 0.751 × **10.0** — the PF lower bound is a
constant, not estimated. (`update_leaderboard.py:58`.)

## Smoking-gun corroboration — LONG vs SHORT split (all 6 models)

| direction | wins | losses | WR |
|---|---|---|---|
| LONG | 171 | 26 | **86.8%** |
| SHORT | 4 | 8 | **33.3%** |

Inflated WR is almost entirely LONG-side: over a 4–14d window a bull drift carries longs
to TP while the daily snapshot never catches intraday SL dips; shorts (need price to fall)
sit at a realistic 33%. Beta/regime coincidence laundered as alpha — not a repeatable edge.

## Swarm review (independent triangulation, evidence fed verbatim, no fetch)

- **DeepSeek:** "no legitimate scenario where 90% WR with a closer SL is a real edge under
  this resolver. Artifact confirmed." (look-ahead via insufficient sampling frequency)
- **Gemini:** agrees ("snapshot immortality"); raised a hole — for a single LONG snapshot
  the TP-before-SL order is irrelevant (a scalar can't be both ≥TP and ≤SL), and floated a
  SHORT operator bug. **Verified & refuted:** `resolve_pick():233-235` flips operators
  correctly; 0/209 sign-mislabels in data. Real bias = sparse daily sampling, not if/else.
- **Kilo:** agrees; cites repo precedent H-001 (85% WR from COT leakage → 30% when fixed).

## Cross-page audit (4 subagents, other /audit surfaces)

- **/audit/ai-tournament.html** — SAME tournament data; arithmetic faithful (0/46 model
  mismatches, 4882 resolved reconciles) but **launders the artifact into 21 "Tier-1"
  badges**; the 5 implausible models (n_resolved 31–33, PF 13–27) hold ranks 1–5. The n≥30
  CI gate does NOT neutralize it. Most dangerous surface.
- **/audit/ai_leaderboard.html** — DIFFERENT dataset (`swarm_picks.json`, intrabar resolver
  `outcome_resolver_swarm.py`), tournament artifact does NOT apply; true scale ~29 resolved
  / 41% WR / PF 1.79. Own bug: n inflated 2–5× by counting each pick once per duplicate
  `models_consulted` entry; single engine (claude-opus-4-7) posing as multi-engine ranking.
- **/audit/ (main)** — largely HONEST: banner drives off verdict-grade `asset_class_health`
  (M-067 invariant holds), 0 classes money-ready, only CRYPTO n>100 (340, WR 38.5%, PF
  0.97). COMMODITY PF 23.66/n=5 and ETF 100%/n=6 correctly gated INSUFFICIENT_DATA;
  `pick_summary_stats*` sidecars 5–9 days stale.
- **/audit/pick_funnel.html** — disputed CRYPTO 78.9% cell REFUTED and already banner-
  flagged; DB ground truth 39.4% WR / PF 0.37 / n=2001. Leakage (1864 dup signal-ts,
  EXPIRED→WON, claude_gainer_st 91.7%) confirmed from JSON; concentration persists under
  renamed sources (alpha_engine 97%); EXPIRED→WON still active in FOREX (~76% suspected).

## Recommendations

1. **Dashboard honesty (P0):** the `/audit/model.html` + leaderboard pages should
   carry a DISPUTED/UNPROVEN banner — "paper tournament, daily-snapshot resolution,
   n<100, WR not path-verified." Mirrors the existing CRYPTO-78.9% DISPUTED treatment.
2. **Fix the resolver (the real T2 blocker, per repo memory):** replace single-spot
   resolution with **intrabar OHLC path replay** — on each bar, if both TP and SL are
   inside [low, high], resolve to the *adverse* barrier (SL for the holder), not TP.
   This is the same intrabar fix flagged as the upstream T2 blocker repo-wide.
3. **Do not size up / promote** any of these models on these numbers. Re-evaluate
   only after (a) resolver fix and (b) n≥100 path-verified resolutions per model.
4. Replace the pf_ci_lo 10.0 floor with a proper capped/log-PF estimator so Score
   isn't pinned by a constant.
5. Fix `build_ai_leaderboard.py` n-inflation (dedupe (pick, engine) pairs before
   `_accumulate`) so /audit/ai_leaderboard.html stops counting one pick up to 8×.

## Reproducer

```
python3 - <<'PY'   # recompute from the live snapshot
import json,collections
picks=json.load(open('audit_dashboard/data/ai_tournament_picks_latest.json'))
# group by model_id, resolved = status!='OPEN', win = pnl_pct>0, pf=sum(win)/abs(sum(loss))
PY
```
Source files: `tools/ai_tournament/price_tracker.py:217` (resolve_pick),
`tools/ai_tournament/resolve_db_picks.py:41` (same logic, DB path),
`tools/ai_tournament/update_leaderboard.py:48,114` (PF + bootstrap floor).
