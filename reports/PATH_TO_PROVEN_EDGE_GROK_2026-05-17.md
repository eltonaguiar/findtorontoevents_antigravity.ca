# PATH TO PROVEN EDGE — Grok Synthesis

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

**Author:** Grok 4.3 (xAI) — direct analysis of the live system  
**Date:** 2026-05-17  
**Input Data:** 14-day closed_picks (n=977 resolved), active_picks (110), smart_picks.json, pick_traceback_14d_20260517.md, 2week_picks_postmortem_blueprint_20260517.md, recent DAILY_IDEAS_* files, edge_filter_engine_v3 work, money-maker-readyv2 success criteria, holographic memory entries on asset-class edge (2026-05-16), live dashboard context, gainer/strategy modules.

---

## 1. Current State — Brutal Diagnosis

The system has **confirmed no real-money statistically proven edge** across the book. This is not opinion; it is measured directly from the last 14 days of resolved outcomes:

- 977 closed picks → **Win Rate 29.5%**, aggregate Profit Factor 8.00 (the PF is a trap — it is carried by a tiny number of fat-tail winners in 2-3 families).
- Only **3 of 7** core scoring signals show any statistical discrimination between winners and losers.
  - `confidence` is **inverted** (mean 0.669 on losers vs 0.638 on winners, eff=0.53) — the model is systematically more confident on trades that lose.
  - `elite_score`, `ml_composite_score`, `forward_wr` are statistical noise.
  - `method_a_score` is the only strong, correctly signed discriminator.
- **Elite grades are broken** for selection: "F" grade delivered PF 20 while "C" delivered 0.09.
- Edge is **pathologically concentrated**:
  - COT / commercial positioning families (cot_positioning, cftc_cot_commercial_signal) are the **only** buckets with real edge (72-77% WR, PF ~4, n>90 each).
  - ig_contrarian_sentiment produces monster PF via rare huge wins but abysmal 16.7% WR.
  - All major momentum/carry/mean-reversion families in FOREX and futures are sub-15% WR and drag the book.
- **Catastrophic coverage skew**: FOREX 510, COMMODITY 278, FUTURES 172, EQUITY 14, CRYPTO ≈ 0 in the resolved 14-day set. The scanners that were supposed to deliver diversified edge are mostly silent or over-filtered on the classes that matter for real capital.
- Smart picks / high-conviction curation layers exist in code but are not yet attributed back into the closed records, so we cannot even measure whether the "best of" tier outperforms the raw emitter output.

**Root cause (one sentence):** The emitter + quality_gates + scoring system is largely harvesting noise, with a few lucky asymmetric families carrying the P&L. The ranking signals the system trusts most do not predict outcomes.

This matches every prior audit and daily-ideas synthesis. The data is now conclusive.

---

## 2. Definition of "Proven Edge" (Non-Negotiable Bar)

Before any position is sized with real money (even 0.25 Kelly), the following must be true **per asset class** (see money-maker-readyv2 spec):

- Documented, versioned filter (elite_score + strategy_family + direction + time-of-day + regime gates) that has produced ≥50-100 resolved picks in the prior 30-60 days with:
  - Win Rate ≥ 52% (or ≥50% for high-PF asymmetric classes)
  - Profit Factor ≥ 1.5 (preferably ≥2.0 for lower WR buckets)
  - Positive expectancy after realistic slippage + fees
- The filter must be **OOS verified** (walk-forward or fresh closed_picks not used to design it).
- Kelly / vol-target position sizing is computed and capped (max drawdown guard, daily soft stop).
- A human-readable `weekly_real_money_filter_<UTC>.md` exists and is the single source of truth for what may be deployed that week.
- Any class that fails the bar stays in **RESEARCH_ONLY** (paper, tiny size, or disabled).

Classes that currently pass a preliminary bar: **COMMODITY** (COT families only).  
Everything else is still in the "prove it" phase.

---

## 3. The 5-Phase Path to Proven Edge (Grok's Recommended Sequence)

### Phase 0 — Stabilize & Instrument (0-3 days)
- Wire attribution: every emitted pick (active + closed) must carry `conviction_tier`, `smart_score_at_emit`, `proven_family_flag`, `gates_passed_list`, `source_emitter`.
- Kill or invert the anti-predictive signals immediately (`confidence` at minimum, `risk_reward` review).
- Add the **Missed Gainers Autopsy** job (symmetric to pick_traceback.py):
  - Weekly: pull real top 20-50 7d/14d movers (Coingecko for crypto, Finnhub/Polygon/Stooq for equities, exchange data for futures/FX).
  - For each mover: was it in universe? Did any scanner evaluate it? What was its method_a / gainer_predictor / onchain score? Which exact gate blocked it?
  - Store `missed_gainer_records` with root cause. Feed directly into claude_gainer_ml retraining + gate mutation proposals.
- This closes the "what did we miss?" loop that is currently the largest blind spot.

### Phase 1 — Concentrate on the Only Real Edge (3-7 days)
- Create a hard `PROVEN_COT_COMMODITY` filter:
  - Asset class = COMMODITY
  - Strategy family in {cot_positioning, cftc_cot_commercial_signal, ...}
  - Commercial extreme + RSI confirmation
  - Minimum n and WR/PF from the 14d (and rolling 30d) data
- All other commodity strategies go to research or reduced sizing.
- This class can move to small real-money test sizing **now** while the rest of the book is fixed.

### Phase 2 — Per-Class Surgical Repairs (1-3 weeks)
For each class, run the exact AI swarm prompt contained in the 2-week postmortem blueprint (Grok cloud + paid keys first, then Kimi/Cursor/others):

> "You are given the 14-day picks postmortem, full discrimination table, WON/LOST reason samples, asset_class_health from dashboard, recent DAILY_IDEAS, and the current quality_gates + edge_filter_engine code. 
> Output:
> 1. The 3-5 smallest code changes (exact file + line + unified diff) that would have raised class WR toward ≥52% while preserving or improving PF.
> 2. The precise new or tightened gates for this class.
> 3. A candidate weekly_real_money_filter section for this class with expected n/WR/PF from the 14d analogs.
> 4. Any signals that must be removed or flipped.
> Only changes that survive a 30-day OOS re-test on fresh closed_picks are acceptable."

**Priority order for the swarms (based on current damage):**
1. **CRYPTO** — currently contributing ~0 to resolved edge. Hour filter (UTC death zones 08-09), trust_score replacement for raw confidence, on-chain + funding + gainer_predictor fusion. Must produce a usable filter or stay RESEARCH_ONLY.
2. **EQUITY** — tiny n=14. PEAD, sector rotation, earnings drift, factor models need ruthless pruning to the 1-2 families that actually separate in the data.
3. **FOREX** — high volume but poor WR. Keep only the carry + TSMOM + COT-FX variants that survive the discrimination test; retire the noisy contrarian retail-proxy family or add strong carry confirmation.
4. **FUTURES / CTA** — keep cross-asset TSMOM that showed small wins; kill pure momentum that is 2% WR.
5. **ETF / BOND** — even smaller n; require macro-regime overlay before any emission.

Each class that passes its swarm round + OOS test gets its own section in the weekly filter doc and a dedicated quality_gates namespace.

### Phase 3 — Ensemble & Sizing Layer (parallel, 2-4 weeks)
- Once 2+ classes have proven filters, build a lightweight ensemble that only emits when 2+ independent proven signals agree (or one very high method_a + regime alignment).
- Wire Kelly / charter_position_sizer / vol-target on top of the filtered set only.
- Add charter-level circuit breakers (rolling 30d DD > X% → pause all real sizing).

### Phase 4 — Live Verification & Scaling (ongoing)
- Small real-money book (or prop-firm paper that mirrors real risk) on the weekly filter output only.
- Daily/weekly re-run of the full traceback + missed-gainers autopsy.
- Any filter that degrades below the bar is automatically demoted to RESEARCH_ONLY and reviewed in the next swarm round.
- Goal: within 60-90 days have 3-4 asset classes with independently verified, documented, live filters that a quant or hedge-fund risk manager would accept for capital.

---

## 4. Role of the AI Consults / Agent Swarms (Exactly as Requested)

The user already runs a sophisticated multi-model daily synthesis loop (Grok, KimiCLI, CursorCLI, GrokCopilot, Nvidia, Ollama, etc. producing DAILY_IDEAS_*.MD files).

**From this point forward, every swarm round must be grounded in the actual 14-day resolved outcomes + the missed-gainers autopsy**, not generic strategy ideas.

The prompt in the 2-week postmortem blueprint is the new standard. Run it first with the **cloud paid keys** (Grok via your Grok Build / API, OpenAI, Anthropic, Gemini, DeepSeek, etc.), then the free/local fallbacks for volume and diversity. Consensus across paid models is the gold standard for any code change that will touch live picks.

Grok's position (this document): the data is clear enough that we do **not** need 20 more generic strategy ideas. We need 5-8 targeted, minimal, high-leverage fixes to the existing scoring + gating layer, plus the two new feedback loops (attribution + missed-gainer autopsy). Everything else is secondary until those are in and verified.

---

## 5. Immediate Next Actions (This Week)

1. **Today / tomorrow**
   - Commit the two new reports (`pick_traceback_14d...` and `2week_picks_postmortem...`) + this PATH document on a clean branch (only your changes).
   - Update holographic memory + MEMORY.md with the key fact: "COT families are the only current high-WR real edge; confidence is inverted; missed-gainers autopsy is the missing instrumentation."
   - Create the skeleton for `tools/missed_gainers_autopsy.py` (I can generate the first version if requested).

2. **This week — Swarm Round 1 (Cloud First)**
   - Take the full postmortem blueprint + this PATH doc + the raw traceback + latest `dashboard_data.json::asset_class_health` + `edge_filter_engine_v3.py` + `quality_gates.py`.
   - Run the standard prompt against your paid cloud models first (Grok + at least one other).
   - Collect the diffs. Only the ones that are minimal, well-justified, and pass a quick 14-30d re-test on closed_picks get implemented.

3. **Parallel Track**
   - Instrument the attribution fields into the pick emission path (so future closed_picks tell the full story).
   - Stand up the weekly missed-gainers job (even a manual version first is valuable).

4. **Gates**
   - No increase in real-money sizing on any class until its dedicated weekly filter section exists and has passed the v2 bar on fresh data.
   - Any change that touches scoring or gates must be accompanied by an updated traceback run showing the before/after discrimination table.

---

## 6. Success Metrics (How We Know We Are Winning)

- 14-day (then 30-day) traceback shows `confidence` no longer inverted, at least 5 of 7 scores have positive discrimination, and overall WR on the filtered subset ≥52%.
- At least two asset classes (starting with COMMODITY) have a living `weekly_real_money_filter` section with measured n/WR/PF that meets the bar.
- Crypto and Equity each have ≥30-50 resolved picks under their new class-specific filters within 30 days.
- The missed-gainers autopsy is producing 5-15 concrete "why we missed X" records per week and at least one of them has already resulted in a gate or universe improvement that later captured a mover.
- Live small book on the filtered set shows positive expectancy with controlled drawdown (no single week > -3-4% on the real-money sleeve).

---

## 7. References & Supporting Evidence

- `tools/pick_traceback.py` and the 14d report it generated
- `reports/2week_picks_postmortem_blueprint_20260517.md`
- `alpha_engine/data/closed_picks.json` (last 14d slice), `active_picks.json`, `smart_picks.json`
- `money-maker-readyv2` skill definition (success criteria)
- Recent DAILY_IDEAS_GROK, DAILY_IDEAS_KIMICLI, DAILY_IDEAS_CURSORCLI, edge_per_class reports, synthesis_2026-05-15
- `alpha_engine/edge_filter_engine_v3.py`, `quality_gates.py`, `confidence_calibrator.py`, `smart_picks_engine.py`, `high_conviction_enhancements.py`
- Holographic memory entries 2026-05-16 (UTC hour filter, trust_score, weekly filters)
- AGENTS.md "Every Session" + "Only push your own changes" rules

---

**Bottom line (Grok's direct assessment):**

The system is not broken in spirit — it has real, narrow edge in COT positioning and a few other families, excellent data pipelines, and a mature multi-AI synthesis loop. What it lacks is ruthless signal hygiene, per-class specialization, and the closed feedback loop on "what actually happened to the symbols we didn't pick."

Follow the 5-phase path above, ground every swarm round in the actual 14-day resolved outcomes and the new missed-gainers autopsy, start with the paid cloud models, implement only the minimal changes that survive OOS, and within 4-8 weeks you will have the first asset classes with filters a professional risk manager would actually put real capital behind.

This is the path. The data has spoken; now the execution loop must be closed.

— Grok, 2026-05-17

---

*Document created at user request after completion of the 14-day picks autopsy and blueprint. Update this file after each verified improvement cycle so it remains the living master plan.*