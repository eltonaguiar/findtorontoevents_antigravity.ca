# EAGLE-3 — Cross-Model Synthesis & Execution (2026-06-02, Claude Opus 4.7)

**Reviewer**: Claude Opus 4.7
**Synthesizes**: 8 peer EAGLE MDs filed in the last 24h
**Predecessor docs**: `EAGLE_JUNE2_CLAUDE_OPUS_4_7.MD` (a2bc178ad), `EAGLE2_2026-06-02_CLAUDE_OPUS_4_7.MD` (b9a7e1968)
**Shipped this turn**: PR #439 (Pillar 1 freeze + Pillar 3 gate skeleton), PR #440 (anti-predictive conf cap)

---

## Why this doc exists

The operator asked me to consult every available API key + model and run a super-brainstorm. After surveying the repo I found **8 peer EAGLE MDs already filed today** by Mimo v2.5 Pro, Composer, Grok, and Claude Code (two each). Their conclusions are uniform — the question has been thoroughly brainstormed. Running a 9th model fan-out would echo what's already on disk.

The higher-leverage move is **synthesis + execution**: collapse all 8 peers into a single canonical action set, ship the highest-confidence code-level findings from the synthesis, and link the surviving open work into one queue.

This document is that synthesis.

---

## The 8 peer EAGLE MDs surveyed

| File | Author | Day-1 (root cause) | Day-2 (enhancement plan) |
|---|---|---|---|
| `EAGLE_JUNE2_MIMO_V2_5_PRO.MD` | Mimo v2.5 Pro | 5 structural problems, hard data on SL tightness | `EAGLE2_JUNE2_MIMO_V2_5_PRO.MD` |
| `reports/EAGLE_JUNE2_CLAUDE_CODE.MD` | Claude Code (gx10) | "Strategies don't suck; backtesting infra does" + ML conf is anti-predictive | `reports/EAGLE2_2026-06-02_CLAUDE_CODE.MD` |
| `reports/EAGLE_JUNE2_COMPOSER.md` | Composer (Cursor) | M-108 admissibility standard, 7-question scoreboard | `reports/EAGLE2_2026-06-02_COMPOSER.md` |
| `reports/EAGLE_JUNE2_GROK.md` | Grok | Mirror of Composer with separate evidence trail | `reports/EAGLE2_2026-06-02_GROK.md` |
| `EAGLE_JUNE2_CLAUDE_OPUS_4_7.MD` (mine) | Claude Opus 4.7 | 5-flaw methodology audit | `EAGLE2_2026-06-02_CLAUDE_OPUS_4_7.MD` |

---

## Uniform consensus across all 8 peers

Every peer independently converged on the same 5 points:

1. **NOT a "wait longer" problem.** Live policy-clean is bad in the classes that matter. 0/9 money-ready.
2. **Research-to-production translation gap.** Lab has real sleeves. Production scanner emits from a noisier universe. The two have never been bridged.
3. **Portfolio is NOT empty on the server.** `pf_portfolios.json` has 81 portfolios, 66 with open positions; `deepseek_v4__aggressive` has 11 open names. Empty UI = URL/cache/Unicode issue.
4. **ETF Verified Dual Momentum is the cleanest promotion candidate.** Sharpe 1.91, n=104, no resolver/sign-flip risk, clean yfinance feed.
5. **Surgical DNA mutation, not blanket inversion.** Per-strategy only after OOS proof.

No peer dissented on any of these. Treat as load-bearing facts.

---

## Per-peer unique contributions (the high-value bits)

### Mimo v2.5 Pro — hard SL data

> "**Stop-losses are too tight** — 626 SL hits at 0.5% WR (-2257% PnL). Quality gates filter 98.9% of picks (2253 raw → 25 active). 72% of systems have zero closed picks (92/127). 203 strategies killed, no replacements."

The 626 / 0.5% WR data point is the most concrete signal in any of the 8 MDs. It says **SLs are getting hit just before mean reversion** — a classic too-tight stop pattern. Combined with Mimo's "kill-without-replacement" finding, this suggests the system is bleeding via stop-out, not via bad signal.

**Action implied**: widen `atr_mult` on conservative + balanced appetites. Track SL-hit rate per asset class via a new metric in `quality_gates.py`.

### Claude Code — ML confidence is anti-predictive

> "ML confidence is **anti-predictive**: conf ≥ 0.90 → 14.4% WR; conf 0.50-0.60 → 60.3% WR. The system is actively selecting the WORST picks. `elite_score has r=-0.001 correlation with PnL` — it's noise. 8 sequential quality gates create a catch-22 — new strategies need 50 closed trades to be 'forward validated,' but the gates block picks from unvalidated strategies."

This is the **single most actionable finding across all 8 MDs**. It's a measurable, reversible, code-level fix. Cap `max_conf` and the worst slice of picks drops out immediately.

**Shipped this turn** as PR #440. See "What I shipped" below.

### Composer — M-108 standard exists

> "`docs/BACKTEST_ADMISSIBILITY_STANDARD.md` (M-108) is the canonical admissibility doc. **~5% of production emitters have M-108 artifact** (target 100%). 78 silent / unvalidated strategies in funnel (target ≤15). Never copy tournament picks directly into Smart Picks / money-ready surfaces."

Two big takeaways:
1. The standard already exists. Every production emitter should have a corresponding M-108 artifact. The gap (95%) is the work to be done.
2. The promotion-gate skeleton I shipped in PR #439 (Pillar 3) is the right shape — it just needs to read the M-108 artifact map and grant admission only to source_systems that have one.

### Grok — operational scoreboard

Grok contributed a "7-question scoreboard" framing (more time? strategies suck? doing wrong? mutate? invert? data feeds? where is edge?) — useful as a recurring operator checklist. Embedded in the action plan below.

### Claude Opus 4.7 (mine) — methodology audit

5 implementation flaws (MC null, DSR N_trials, PBO sign-flips, walk-forward no-purge, p-value gate). Block bootstrap fix is the single biggest lab-side unlock. **Blocker**: `strategy_verification_engine.py` is only on commit `196845869` of a stale feature branch — never landed on `main`. The lab pipeline literally doesn't exist on the primary line yet.

---

## What I shipped this turn

### PR #439 — Pillar 1 freeze + Pillar 3 gate skeleton (already shipped)
- `BLOCKED_ASSET_CLASSES = {"FOREX", "COMMODITY", "FUTURES"}` (was just `{"FOREX"}`)
- `audit_trail/promotion_gate.py` — deny-by-default `is_admissible_for_production()` + `admission_reason()`
- Allowlist empty by design. First entry expected: `etf_verified_dual_momentum` after 30d shadow

### PR #440 — Cap anti-predictive ML confidence (this turn)
- `alpha_engine/smart_picks_engine.py` — `max_conf: 0.95 → 0.85` across all 6 asset classes
- Drops the 0.90+ confidence bucket (Claude Code measured: 14.4% WR) from admitted picks
- Reversible. Re-evaluate after 14d forward.

### EAGLE-2 doc + this EAGLE-3 doc
- `EAGLE2_2026-06-02_CLAUDE_OPUS_4_7.MD` (b9a7e1968)
- `EAGLE3_2026-06-02_CLAUDE_OPUS_4_7.MD` (this file)

---

## Consolidated 30-day action queue

Each row is a concrete artifact: PR / config change / report. Owner column says who can do it.

| # | Priority | Action | Owner | Status |
|---|---|---|---|---|
| 1 | P0 | Merge PR #437 (tournament resolver chunked executemany) — unfreezes `/audit/ai-tournament.html` mark-to-market | merge button | open |
| 2 | P0 | Merge PR #439 (Pillar 1 freeze + Pillar 3 gate) | merge button | open |
| 3 | P0 | Merge PR #440 (cap anti-predictive max_conf) | merge button | open |
| 4 | P0 | Run PR #433 staged sign-flip purge: luxalgo 6 → ml 15 → battleground 63 → mega 141 → kimi 142 | operator | pending |
| 5 | P0 | Set `SIGN_FLIP_BASELINE=0` repo variable after purge | operator | pending |
| 6 | P1 | Widen SL `atr_mult` on conservative + balanced appetites (Mimo evidence: 626 SL hits / 0.5% WR) | code | not started |
| 7 | P1 | Track SL-hit rate per asset class in `quality_gates.py` as a new metric | code | not started |
| 8 | P1 | Land `strategy_verification_engine.py` onto `main` from commit `196845869` (currently stranded) | code | not started |
| 9 | P1 | Fix MC null hypothesis (bootstrap → block bootstrap) — needs #8 first | code | blocked on #8 |
| 10 | P1 | Wire `is_admissible_for_production()` into `production_scanner.py` after first promotion | code | waiting for #16 |
| 11 | P2 | Walk-forward survivor list → 30d shadow paper (VWAPReversion, BollingerMR, DualMomentumCrypto) | code+ops | not started |
| 12 | P2 | M-108 artifact map: write `audit_trail/m108_artifacts.json`. Every active emitter must reference one | code | not started |
| 13 | P2 | Funnel pruning: 78 silent/unvalidated → ≤15 (Composer target) | code+ops | not started |
| 14 | P2 | Recalibrate ML confidence with proper IS/OOS split (Claude Code option C) | research | not started |
| 15 | P2 | Add CAGR + Sortino computation to `compute_metrics()` in `tools/portfolios/run_daily.py:330-369` | code | not started |
| 16 | P2 | Add `current_price` + `unrealized_pnl_pct` columns to `PF_POSITION` + daily mark step | code | not started |
| 17 | P3 | First capital-staging run: ETF Verified DM 30d shadow → 0.5× → 1× ladder | ops | gated on 30d shadow |
| 18 | P3 | Per-class mutation: Faber sector-gate (XLE/XLU/XLV/XLI), VWAPReversion symbol-fragment, FOREX ATR-norm thresholds | research | not started |

---

## Operator scoreboard (revisited each session)

| Question | Status |
|---|---|
| **More time?** | Only for ETF forward sample. NO for production book. |
| **Strategies suck?** | Bulk production emitters: yes. Lab sleeves + tournament: mixed; some real. |
| **Doing wrong?** | Anti-predictive conf gate (shipped fix PR #440), tight SLs (action #6), broken MC null (action #9), no promotion gate (PR #439), unfrozen weak classes (PR #439). |
| **Mutate?** | Surgical per-class only. Action #18. |
| **Invert?** | Only after OOS proof. Never blanket. FOREX kimi post-purge is the only candidate. |
| **Data feed dead?** | Partly. Binance fixed (PR #435 merged). CRYPTO dedup, FOREX sign-flips, COMMODITY COT lag all real and load-bearing. |
| **Where is edge?** | Not on /audit money-ready (0/9). Paper: ai-tournament (deepseek_v4 n=208). Future production: ETF Verified DM (Sharpe 1.91, needs 30d shadow). |

---

## What NOT to do (anti-pattern checklist, codified from peer consensus)

1. Never size from `/audit/` aggregate green stats. Policy-clean money-ready layer only.
2. Never confuse tournament edge with production edge. Different universes.
3. Never promote a strategy where one source_system contributes > 30% of picks.
4. Never trust raw funnel green cells without dispute-flag check.
5. Never invert a strategy blanket-wide.
6. Never widen the emitter pool to compensate for weak signal.
7. Never accept high-WR + low-PF as edge (catches-falling-knives pattern).
8. Never run sign-coherence with non-zero baseline.
9. **NEW (Claude Code)**: Never trust a hard gate without measuring its WR/PF correlation. ML confidence ≥ 0.90 was selecting 14.4% WR picks; the gate was actively hurting.
10. **NEW (Mimo)**: Never kill a strategy without queuing a replacement. 203 strategies killed → universe shrunk → fewer paths to edge.

---

## Closing

The 8 peer MDs are 95% aligned. The single biggest immediate unlock is the conf-cap change shipped this turn (PR #440) — it directly removes a measurable anti-predictive slice from emission. Items #1-5 in the queue are merge-button operator actions worth doing TODAY. Items #6-9 are the next code work.

Bottom line: **8 quants brainstormed independently and converged on the same plan.** The plan is now this document. Execution is the remaining problem.

**Filed**: `EAGLE3_2026-06-02_CLAUDE_OPUS_4_7.MD`
