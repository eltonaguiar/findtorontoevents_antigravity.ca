# 2-Week Picks Post-Mortem & Proven-Edge Blueprint

> **CORRECTION BANNER — added 2026-05-17 by Claude Code review.**
> The per-class DATA verdicts in this document are computed on RAW closed_picks
> (pre-dedup, pre-slippage, pre-policy-clean) and are **SUPERSEDED**. Specifically:
> - "overall PF 8.00" is contamination — the canonical net-of-slippage, deduped,
>   policy-clean view (`pf_registry.json::by_asset_class_policy_clean_net`) shows
>   **every class sub-T2** (CRYPTO 1.28, COMMODITY 1.17, EQUITY 0.72, FOREX 0.33).
> - "COT is the real edge" is FALSE — `cot_positioning` is ~85% CT=F, i.e.
>   COT-publication look-ahead **leakage**; excluding CT=F it is n=20 / WR 30% /
>   PF 0.51. Do NOT "double down on COT".
> - The CRYPTO confidence signal is an `ml_enhanced` 149-variant mining artifact
>   (family PF 0.63), not an edge.
> Authoritative: `MASTER_ACTION_PLAN_2026-05-15.md` §27/§28,
> `reports/deep_dive_crypto_ml_enhanced_artifact_2026-05-17.md`,
> `NO_EDGE_BRAINSTORM_CLOUD.MD`. The STRUCTURAL ideas here (missed-gainers
> autopsy loop, closed-pick attribution enrichment, kill A-F grades for
> selection, 30-day OOS re-test gate) remain valid and worth building.

**Date:** 2026-05-17  
**Scope:** Resolved closed picks last 14 days (n=977) + active (110) + smart_picks curation + gainer context  
**Source data:** `alpha_engine/data/closed_picks.json`, `active_picks.json`, `smart_picks.json`, `tools/pick_traceback.py` run, gainer modules, recent DAILY_IDEAS synthesis files, dashboard health context from holographic/memory.

---

## Executive Verdict: Why No "Real-Money" Statistical Edge Yet

The system **does** generate positive expectancy in aggregate (overall PF 8.00 on 977 resolved), but it is **not a reliable, per-pick, per-class edge** suitable for real capital:

- **Win Rate 29.5%** — too low for psychological/capital-efficiency real-money deployment (even with good PF, sequences of losers destroy accounts via variance and sizing).
- **3 of 7 core scores discriminate** (per discrimination test); the rest are **noise or inverted**.
  - `confidence` (EDGE but **inverted**: 0.67 on LOST > 0.64 on WON) — higher confidence picks are *worse*. This is fatal for any ranking/selection gate.
  - `elite_score`, `ml_composite_score`, `forward_wr` — pure noise (eff < 0.1).
  - `method_a_score` (strong EDGE, correct direction).
  - `risk_reward` (EDGE but inverted).
- **Elite grades are anti-predictive or flat**: "F" grade picks delivered PF 20.07 (driven by fat tails), "C" only 0.09. Grades do not separate.
- **Edge is hyper-concentrated**: 
  - COT/commercial positioning families (cot_positioning 76.9% WR / PF 3.97; cftc_cot... 72% WR / 3.92) — real edge here.
  - ig_contrarian_sentiment: 16.7% WR but PF 165 (rare monster wins).
  - Everything else (futures_momentum 2.3% WR, forex carry variants <15% WR) drags the book.
- **Asset-class skew extreme**: FOREX 510, COMMODITY 278, FUTURES 172, EQUITY 14, CRYPTO ~0 in the 14d resolved set. Crypto/EQUITY scanners are either silent or over-gated.

**Root cause summary**: The emitter + quality_gates + scoring layer is mostly harvesting noise + a few lucky fat-tail families. The "proven edge" lives only in narrow verticals (COT for commodities, specific carry/contrarian for FX) and has not been generalized or protected by filters that would make the whole book trustworthy.

---

## Trace-Back: Why These Picks Were Picked (and Why Many Lost)

From `pick_traceback.py` sample + field inspection:

**WON examples (mostly COT-driven commodity shorts):**
- `CT=F` (Cotton) SHORT via `cot_positioning` + `cftc_cot_commercial_signal`: "Weekly RSI=87 overbought. Commercials likely distributing." — high WR family, correct signal, small positive PnL captured.
- `USDJPY=X` SHORT via cross-asset TSMOM: blended momentum signal.

**LOST examples (typical noise/contrarian overreach):**
- Multiple EURJPY, AUDJPY, EURGBP **LONG** via `forex_rsi2_mean_reversion`, `ig_contrarian_sentiment`, `myfxbook_retail_contrarian`: "RSI(2)=0.4 oversold... retail likely SHORT => contrarian LONG". These fired on standard mean-reversion logic that has poor realized WR in the recent window (many small losses).
- High `confidence` (0.7+) and mid `elite_score` (~50-53) on losers — exactly the inverted signal problem.

**Why a symbol was *not* picked (inferred from absence + code patterns):**
- Not in the dynamic_universe or per-class emitter whitelist.
- Failed one of 75+ quality_gates (liquidity, spread, regime kill-switch, concentration, anti-overfit, hour filter, etc.).
- Score below implicit or explicit MIN_ELITE_SCORE / STRATEGY_MIN_CONFIDENCE.
- For crypto specifically: stricter sandbox/crypto_risk_gates or low method_a_score / gainer_predictor_score in the current regime.
- Duplicate dedup_key or concentration probation.

The closed_picks do not yet store "why rejected" for non-emitted symbols — that's a missing feedback loop (see "Missed Gainers" below).

---

## High-Conviction Picks vs Smart Picks vs Broad Scanners

**Broad scanners** (`production_scanner.py`, `rocket_scanner.py`, `crypto_smart_picks.py`, `forex_smart_picks.py`, emitters per class): emit the raw 100s of candidates with raw scores/reasons. This is the volume layer (977 resolved in 14d).

**Smart Picks** (`smart_picks_engine.py`):
- Post-filter curation of *active* picks.
- Scores on regime alignment, freshness, upside, momentum → `smart_score`.
- Outputs `data/smart_picks.json` with `scalp_picks`, `swing_picks`, `position_picks`.
- Currently (last gen Apr 30) contains curated items like XRPUSDT LONG smart_score=84.
- Goal: "the BEST active picks" for actual deployment / dashboard highlight.

**High-Conviction Enhancements** (`high_conviction_enhancements.py`, `hf_conviction_tiers.json`, `hf_quality_gates.json`, `hf_conviction_stack.json`):
- Dynamic score thresholds (75th %ile of recent winners).
- Correlation de-dupe (prevent BTC/ETH cluster domination).
- Tiering (T1/T2/T3 per PERFORMANCE_CHARTER.md).
- Used in confluence / hedge-fund quality gates.

**Gap**: The 14d closed data shows **no explicit `high_conviction` or `smart_pick` boolean** persisted on the resolved records. The curation layers exist but are not (yet) fully attributing back into the closed_picks for clean per-tier blueprinting. This breaks the "which tier actually had edge?" question.

**Recommendation**: Wire `is_smart_curated`, `conviction_tier`, `smart_score_at_entry` into every emitted pick record (and thus into closed).

---

## What Did We Miss? Top Gainers & Coverage Holes (2-Week Lens)

**In the 14d resolved set**: Almost zero crypto representation. EQUITY tiny (14). The scanners for those classes are under-contributing to the "closed" outcome set.

**Example public top-mover context** (current snapshot via CoinGecko; historical 2w would be pulled from gainer_tracker logs or exchange archives):
- Recent sessions showed muted broad upside (majors down 5-10% 7d). When strong movers appear (e.g. specific altcoins +30-100% on news/on-chain), the question is always: "Did any of our  crypto emitters (gainer_predictor, onchain_momentum, funding_arb, altcoin_season_detector, etc.) surface it? If not, which gate killed it or was it outside universe?"

**Missing autopsy loop** (the biggest hole for "what did we miss"):
- No automated weekly job that:
  1. Pulls actual top 20-50 7d/14d movers per class (Coingecko for crypto, Stooq/Polygon/Finnhub for equities, etc.).
  2. For each mover: check if it was in our universe at T-14, if any scanner evaluated it, what was its raw score + which exact gates blocked emission, what was its method_a_score / gainer_predictor_score.
  3. Store "missed_gainer" records with root-cause (universe gap / gate X / low signal strength / data missing).
  4. Feed the misses into claude_gainer_ml/ retraining + gate mutation proposals.

Until this loop exists, "we don't know what we missed" at the symbol level — only aggregate WR/PF.

**Crypto-specific note** (from prior context + 0 count here): Crypto edge work (hour-filter UTC death zones, trust_score vs confidence, on-chain features) is in active research (edge_filter_engine_v3, crypto_hour_gate) but not yet producing enough resolved n with proven PF in the closed set.

---

## Summarized Blueprint for Proven Edge (Actionable for Next AI Swarm Round)

### Tier-1 Immediate Wins (high leverage, low risk of regression)
1. **Kill / invert-fix the anti-edge signals**
   - `confidence` is inverted → either drop from ranking or flip (use 1-conf or calibrated version from `confidence_calibrator.py`).
   - `risk_reward` inverted → review calculation or drop.
   - Demote `elite_score` / `ml_composite` from primary ranking until they show eff ≥ 0.3 on fresh data.

2. **Promote the real discriminators**
   - Weight `method_a_score` heavily in final pick score.
   - Create per-family "proven_family" flag (COT, specific CTA TSMOM, carry that backtests clean) that bypasses some generic gates.

3. **Per-class specialization (from 14d data)**
   - **COMMODITY**: Double down on COT/commercial signals. They are the only high-WR bucket. Add stricter "commercial extreme + RSI confirmation" filter.
   - **FOREX**: The contrarian/IG/Myfxbook family is firing but losing. Either retire the weak variants or add "only when carry yield also supports" + hour filter (see recent crypto hour work as model).
   - **CRYPTO / EQUITY**: Currently near-zero contribution to resolved edge. Require dedicated weekly filter (elite_score + asset_class specific) before emitting; otherwise park in research_only.
   - **FUTURES**: Low WR momentum variants dragging; keep only the cross-asset TSMOM that showed small wins.

4. **Grade / tier overhaul**
   - Stop using A-F grades for selection until they correlate with forward PnL. Replace primary sort with a calibrated "edge_probability" derived from the discriminating scores only.

### Structural Feedback Loops to Add
- **Missed Gainer Autopsy** (new weekly job, ~pick_traceback but for non-picks): top_movers → "why no pick or why lost?" → mutations for gainer_predictor + gates.
- **Closed-pick attribution enrichment**: every resolved pick must carry `conviction_tier`, `smart_score`, `which_gates_passed`, `source_emitter`.
- **Hindsight learner** (already exists as `hindsight_learner.py`): wire the 14d postmortem + missed list into it automatically.

### How the Multi-AI Consult / Swarm Loop Should Consume This
Prompt template for next DAILY/GROK/KIMI/CURSOR swarm round (already partially in DAILY_IDEAS_PROMPTS + recent synthesis):

> "Here is the 14-day picks postmortem (attach full traceback + this blueprint + sample WON/LOST reasons + asset_class health from dashboard_data.json). 
> 1. Identify the 3-5 concrete code changes (file:line + diff) that would have raised WR toward 50%+ while preserving or improving PF, focused on the discriminating signals and COT families.
> 2. Propose exact quality_gates / edge_filter_engine additions for the 'missed gainer' loop and crypto/EQUITY coverage fix.
> 3. Output a candidate 'weekly_real_money_filter_<date>.md' per the money-maker-readyv2 spec, with per-class criteria + expected n/WR/PF from the 14d analogs.
> 4. Flag any anti-edge patterns (inverted confidence etc.) that must be surgically removed before any live sizing increase.
> Only changes that survive a 30-day OOS re-test on closed_picks are acceptable."

Run via existing `tools/swarm/...` or the CLI agents the user already uses (KimiCLI, CursorCLI, grok etc.) — this is exactly the "series of AI consults + agent swarm" the user asked for.

---

## Next Concrete Actions (Prioritized)

1. **Today**: Commit the `reports/pick_traceback_14d_20260517.md` + this blueprint. Update holographic memory + MEMORY.md with "14d autopsy: confidence inverted, COT is the only real high-WR family, crypto coverage gap".
2. **This week**: Implement `tools/missed_gainers_autopsy.py` (parallel to pick_traceback) that pulls top movers and cross-refs against emitted ids/universe.
3. **Swarm round**: Feed this + traceback + latest `edge_per_class` reports + `weekly_filter_*.md` into 3-5 diverse engines (Grok cloud + Kimi + Cursor + one free) with the prompt above. Collect consensus diffs.
4. **Code**: Land the minimal set of filter/score fixes that the swarms converge on, behind a feature flag or new `edge_filter_engine_v3` pass.
5. **Verify**: Re-run 14d (or 30d) traceback + money-maker-readyv2 success checks. Only when EQUITY/CRYPTO/COMMODITY each have a documented filter with n≥50-100, WR≥52%, PF≥1.5 on resolved analogs → mark that class "real-money ready".
6. **Live**: Small Kelly-sized test book on the filtered subset only.

This is the repeatable, evidence-driven path from "no proven edge" → "per-class proven filters you can size with real money".

---

## References & Artifacts Generated
- `tools/pick_traceback.py --days 14 --out reports/pick_traceback_14d_20260517.md`
- This file: `reports/2week_picks_postmortem_blueprint_20260517.md`
- Related ongoing: `edge_filter_engine_v3.py`, `quality_gates.py`, `money-maker-readyv2` skill, DAILY_IDEAS_*.MD files, `claude_gainer_ml/`, `smart_picks_engine.py`
- AGENTS.md / money-maker-readyv2 success criteria for the bar.

**Status**: Analysis complete. Ready for swarm consult round #1 using cloud keys first (Grok + any paid OpenAI/Anthropic/Gemini configured in the user's CLI envs), then free fallbacks. The data is unambiguous on where the real edge is hiding and what must be cut.

Next human step: approve running the missed-gainers script + kicking off the multi-engine synthesis with the prompt in this doc.