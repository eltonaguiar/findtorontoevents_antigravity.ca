# Path to a Proven Statistical Edge — 2026-05-17

Built from `tools/pick_traceback.py` (976 resolved picks, last 14 days) + a
3-cloud-model swarm consult (deepseek, xai, cerebras) + an out-of-sample
verification that **overturned the swarm's lead recommendation**.

## The core question: does ANY score separate winners from losers?

`pick_traceback.py` runs a discrimination test — for each score the pipeline
attaches to a pick, mean over WON vs over LOST picks, standardised gap `eff`:

| Score | mean(WON) | mean(LOST) | eff (0-14d) | verdict |
|-------|-----------|------------|-------------|---------|
| method_a_score | 41.5 | 27.2 | **1.14** | looked like the edge |
| risk_reward | 1.40 | 1.57 | 1.06 | strong, inverted |
| confidence | 0.638 | 0.669 | 0.53 | real, inverted |
| ml_score | 0.630 | 0.659 | 0.29 | weak, inverted |
| **elite_score** | 24.7 | 25.2 | **0.06** | **NOISE** |
| ml_composite_score | 24.7 | 25.2 | 0.06 | NOISE (= elite_score) |
| forward_wr | 0.0 | 0.0 | 0.0 | NOISE (unpopulated) |

The dashboard ranks/surfaces picks by **`elite_score` — the noise one** (eff
0.06; it does not separate winners from losers at all). `method_a_score`, which
*did* separate them in the last 14 days (eff 1.14), is computed but not the
primary ranker.

## The verification that changes everything

The swarm's #1 recommendation was: re-rank the gate on `method_a_score`. Before
acting on it, `method_a_score`'s discrimination was checked on the **prior**
14-day window:

| Window | mean(WON) | mean(LOST) | eff | direction |
|--------|-----------|------------|-----|-----------|
| days 0-14 | 41.5 | 27.2 | 1.14 | winners higher ✅ |
| **days 14-28** | 40.1 | **43.8** | **0.42** | **winners LOWER ❌ — inverted** |

**`method_a_score`'s edge is not stable — it inverts sign between consecutive
windows.** The eff 1.14 is regime-specific noise, not a durable signal.
Re-ranking the gate on it would have fitted the gate to the last 14 days.

→ **The honest result: the system has NO score that stably discriminates
winners from losers.** That is the root cause of the 29.4% WR / 0.74 PF book.
There is no "use the better score" fix — no better score exists yet.

## What the swarm got right (still actionable)

3/3 cloud models converged on what a profitable desk has that this one does not:

1. **A walk-forward / bootstrap validation harness.** 14 days is too short to
   claim any edge; every candidate signal must clear eff-stability across ≥3
   consecutive windows *before* it touches the gate. This is the missing piece
   that would have caught `method_a_score` automatically.
2. **A transaction-cost model.** PF 0.74 is pre-cost — "0.74 PF implies costs >
   edge" (deepseek/xai). Every gate metric must run on post-cost pnl.
3. **A regime filter.** `elite_grade` WR is non-monotonic (A 50%, B 33%, C 10%,
   D 35%, F 26%) — the system is regime-blind; a score that works bull-side
   inverts bear-side, exactly the `method_a_score` pattern.
4. **Edge-based position sizing** (Kelly / vol-adjusted) — equal-weight sizing
   on a no-edge book guarantees the PF bleed.
5. **Exit logic** — `risk_reward` inverted (winners have *lower* R:R) suggests
   winners are cut early / losers held long.

## The minimum honest path (revised, post-verification)

Ranked. Note step 1 is NOT "re-rank on method_a_score" — that was disproven.

1. **Build the walk-forward eff-stability harness.** A score is admissible to
   the gate only if its WON-vs-LOST `eff` is ≥0.30, same sign, across ≥3
   consecutive 14-day windows. Run it on every existing score + every new
   candidate. Today: **zero scores pass.** That is the gate to fix first.
2. **Cost model.** Per-class slippage + commission; rerun every metric post-cost.
3. **Hunt for a stable signal.** With the harness live, test candidate features
   (the qlib factors added in PR #1178: `pv_corr30`, `vol_ratio`,
   `realized_vol30`; regime-conditioned variants; interaction terms). Keep only
   what clears step 1.
4. **Isolate ONE asset class** where a step-1-passing signal exists, post-cost
   PF ≥1.15 on ≥200 trades, top-symbol concentration <30%.
5. **30-day paper-forward** at production latency before any real capital.

## On the two external-AI blueprints (Mercury 2, deepai.org)

Both proposed generic green-field plans — Mercury a new `model_signals` +
`picks` MySQL schema with FK trace-back; deepai a 6-step "data pipeline" plan.

**Verdict: conceptually fine, implementation unnecessary.** The trace-back they
propose to *build* already exists — every pick in `closed_picks.json` carries
its `reason`, `strategy`, `source_system`, grades and scores (94-100% field
coverage). `tools/pick_traceback.py` extracted the full attribution **without
any new schema**. Mercury's `model_signals` table would duplicate data the repo
already has. This is the recurring external-AI pattern (see PR #1155): plausible
designs that ignore the existing codebase. The bottleneck was never missing
infrastructure — it is that no stored score has a stable edge, which only a
verification harness (step 1) surfaces.

## Deliverables this run

- `tools/pick_traceback.py` — discrimination test + per-tier blueprint, reusable.
- `reports/pick_traceback_2026-05-17.md` — full per-pick / per-tier trace.
- This document — the verified path.

**Next concrete action:** build the walk-forward eff-stability harness (step 1).
Until it exists, every "we found an edge" claim — including this session's
earlier `cot_positioning` and `method_a_score` findings — is in-sample noise.
