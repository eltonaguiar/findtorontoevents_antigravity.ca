# Hedge-Fund Enhancement PR (2026-05-02) — Codebase Review & Suggestions

**Source document:** `HEDGE_FUND_ENHANCEMENT_PR_2026_05_02.docx` (Kimi agent-swarm master PR; 10 chapters, 44 tables, 35 numbered recommendations, ~258 engineering hours, projected +35% / +60% portfolio P&L lift).

**Reviewer:** Claude Opus 4.7 — read-only audit against the live repo on `origin/main` at branch creation time.

**Scope:** Compare each load-bearing claim and proposed code change to the current state of the codebase, flag what is *already shipped*, what is *partially shipped*, what is *missing*, and what carries operational risk under the project's Wire-Up Rule and Strategy Demotion Protocol (`AGENTS.md`, `CLAUDE.md`, `TESTING_PROTOCOL.MD`, `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`, `docs/MUTATION_THREE_AXIS_PROTOCOL.md`).

---

## TL;DR

The DOCX is a substantively faithful, evidence-graded restatement of work the repo has been pursuing since the Apr-22 hedge-libs leverage audit. **Roughly 40% of its proposals are already coded** (modules exist), **another ~25% are coded but not wired** (the same orphan pattern that motivated the Wire-Up Rule), and **~35% are net-new**.

The single biggest risk is that the DOCX recommends *direct* gate replacements ("abolish WINNER_FILTER", "replace `elite_score` with `ml_score ≥ 0.82`", "suspend Crypto C-Tier", "eliminate four asset classes") with no shadow-mode or rollback plan. The repo's standing rule is **production-behaviour changes ship default-OFF behind feature flags + 14-day shadow**. The DOCX's own `hf_quality_gates.json` change list (Rec 1, 3, 16, 20) is compatible with that — feature-flagging it is a one-line discipline, not an architecture change.

**My recommended sequencing diverges from the DOCX in three places:**

1. Land the **resolver / schema / `track_calculator.py`** triplet first (Recs 16, 18, 29, 30). Until `track_wr` is produced, every gate in `hc_filter.js` that consumes `strat_fwd_wr` is operating on permanently-zero inputs. This is the gating dependency for *every other* gate-tuning recommendation in the document.
2. **Demote** the DOCX's "Phase 0 emergency hotfix" framing to "Phase 1 shadow rollout". The +173% annual alpha-bleed claim and 0% WINNER_FILTER accuracy are credible, but the n=500 shadow-blocked sample has selection-mechanism risk (see `.tmp_research/deepseek_response.md` §4) and the project rule has 14 days of shadow as a non-negotiable cost-of-doing-business.
3. **Reject** the "eliminate four asset classes" recommendation (Rec 31) in its current form. The same data that says FOREX/COMMODITY are loss-making also says the resolver fix has not landed yet, so the noise share (63–67% per `reports/action_B_resolver_2026_04_27.md`) makes any P&L attribution unreliable. Re-run the analysis post-resolver.

The other 30+ recommendations are largely accept-with-modifications.

---

## 1. What is already shipped

Cross-checked against `origin/main`.

| Rec(s) | DOCX claim | Code state | Evidence |
|---|---|---|---|
| 32, 33 | New `alpha_engine/statistical_rigor.py` with bootstrap CIs, BH-FDR, PSR | **Shipped**, ~220 LOC, 20 tests green | [alpha_engine/statistical_rigor.py](alpha_engine/statistical_rigor.py), [updates/2026-05-02-hedge-fund-grade-uplift-foundation.md](updates/2026-05-02-hedge-fund-grade-uplift-foundation.md#L29) |
| 32, 34 | New `alpha_engine/hrp_allocator.py` (HRP, quarter-Kelly, correlation gates) | **Shipped**, ~260 LOC; wire-up to `regime_position_sizer.py` is Week-3 in the foundation update | [alpha_engine/hrp_allocator.py](alpha_engine/hrp_allocator.py) |
| 5, 33 | New `alpha_engine/decay_tracker.py` (rolling 90/365d Sharpe, demotion ladder) | **Shipped**, ~150 LOC | [alpha_engine/decay_tracker.py](alpha_engine/decay_tracker.py) |
| 35 | Kill-switch ladder (5-tier) | **Module shipped** (decay_tracker has the ladder); **not wired** to a circuit-breaker that halts pick generation | — |
| 8, 26 | 8 researcher personas under `ml_crypto_predictor/researchers/` | **Shipped** in foundation PR (vol_targeting / reconciliation / hmm_regime / risk_parity / factor_overlay / multiple_testing / meta_orchestrator / transaction_cost) | [updates/2026-05-02-hedge-fund-grade-uplift-foundation.md](updates/2026-05-02-hedge-fund-grade-uplift-foundation.md#L42) |
| (Rec 16 partial) | Resolver thresholds asset-class-gated | **Partially shipped**: `alpha_engine/outcome_resolver.py` has v2 logic with asset-class thresholds; the live yfinance-on-every-run path and `MAX_RESOLVE_RETRIES` cap are not yet in main | [reports/action_B_resolver_2026_04_27.md](reports/action_B_resolver_2026_04_27.md) |
| Reference | Reconciliation report | **Shipped**: `alpha_engine/reconciliation_report.py` (foundation PR) | — |

**Implication:** Recs 32 / 33 / 34 / 35 / 5 / 8 / 26 are now blocked on **wire-up**, not on construction. They count as orphan modules under the Wire-Up Rule and a follow-up PR must add at least one production caller for each.

---

## 2. What is partially shipped

| Rec(s) | DOCX claim | Reality |
|---|---|---|
| 1 | Replace `elite_score` gate with `ml_score ≥ 0.82` | `config/hf_quality_gates.json` already documents this preference (`note_elite_vs_ml`: "ml_score predicts PnL better than elite_score; keep elite gate optional"). The whole gate file is `"enabled": false` today. Real change: enable + flip the threshold. |
| 2 | `round(elite_score, 2)` defensive coercion | `alpha_engine/hedge_fund_quality_gate.py` exists; no rounding patch yet. Trivial. |
| 3 | Lower R:R floor 1.5 → 1.25 | The JSON already caps R:R at 2.0 with a comment that closed-book data shows 1.0–1.5 strongest. Lowering the floor is consistent with the comment but contradicts the upper-band cap; needs a single coherent narrative. |
| 16, 18 | Resolver `MAX_RESOLVE_RETRIES=3` + 5bp scalp floor + alias map | Resolver v2 lands the gated thresholds; the retry cap and 5bp scalp floor are still in the Apr-27 action plan, not main. **Highest priority gating dependency.** |
| 29, 30 | `track_calculator.py` + 12-field schema enforcement | **Module not in main.** `hc_filter.js:302` still reads `p.strat_fwd_wr || p.forward_wr || 0` — the value `outcome_resolver.py` never produces. Gate 3 has been silently inoperative. |

---

## 3. What is genuinely net-new (and accept-with-modifications)

| # | Rec | Verdict |
|---|---|---|
| 17 | Forex carry sleeve (Burnside et al. 2011, Sharpe 0.86) | **Accept** as opt-in sidecar; gate behind same Wire-Up Rule plan. Carry alone is high-vol; pair with the 2021 factor-momentum overlay (Rec 18) before sizing. |
| 24 | Crypto perp funding-rate arb (He & Manela 2024) | **Accept with shadow-mode**. The 115.9% / 6mo number from Li et al. 2025 is on a single venue and requires an executable basis; treat as research until a paper-trading scorecard exists. The repo already has `alpha_engine/funding_rate_arb.py` listed in the audit-dashboard push paths — confirm it's wired before accepting a *new* implementation. |
| 25 | CEF NAV discount mean reversion | **Defer**. Sharpe 1.862 from CUNY (2021) is on annual-rebalance horizons; doesn't fit the 4–24 hour pick generation cadence. |
| 26 | Meme coin pilot (5% hard cap) | **Reject** as written. The 74% XGBoost accuracy claim (IJRASET 2025) is Tier-3 sourcing per the DOCX's own grading; the 40% pump-and-dump rate the document acknowledges is a deal-breaker without execution-guarded entry. |
| 27 | Penny-stock reversal (2% cap) | **Defer**. Da et al. (2014) Management Science alpha is real, but the DOCX itself flags "deal-breaking transaction-cost constraints". No transaction-cost layer is wired into pick scoring today. |
| 28 | Gold/silver ratio MR | **Accept**, low-effort, low-risk; needs a one-symbol scanner. |
| 23 | Commodity triple-screen (Fuertes et al. 2015) | **Accept** post-resolver fix. Until the resolver lands, COMMODITY data is 67% noise per `action_B_resolver_2026_04_27.md` and any backtest is uninterpretable. |
| 22 | Futures accumulation mode (lower gates, n=2 sample) | **Reject** as written. n=2 is below any acceptable shadow-mode minimum. |
| 21 | Yield curve steepener (62% WR, 2.8% avg 6M) | **Accept** as a strategy researcher persona under `prediction_market_agents/` style; the bond agent (`bond-agent.yml`) is the natural caller. |

---

## 4. What I recommend rejecting outright (or rewriting)

### Rec 31 — "Asset class triage: ELIMINATE Crypto C-Tier + Forex + Commodities + Futures"

**Reject in current form.** This is the largest claimed lift in the entire deck (+8% / +15%, Grade A+). Two reasons:

1. **Pre-resolver data.** The −77.79% PnL drag for those four classes is computed on resolver-corrupted data (see `reports/action_B_resolver_2026_04_27.md`: 63–67% noise share for FOREX/COMMODITY because `PNL_WIN_THRESHOLD=0.00001` is not asset-class-gated and the live close is not refreshed). Any elimination decision based on this data inherits the 67% noise rate.
2. **Strategy demotion protocol.** Project rule (`TESTING_PROTOCOL.MD` §7, `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`, `docs/MUTATION_THREE_AXIS_PROTOCOL.md`): **no `BLOCKED_SOURCE_SYSTEMS` expansion** without the 3-axis mutation analysis (`tools/mutation_analysis.py` on the closed-book CSV). The DOCX does not produce that analysis.

**Rewrite as:** "Suspend allocation (max position size = 0) but continue paper-tracking. Re-evaluate after 30 days of post-resolver clean data + mutation analysis."

### Rec 1 (extreme form) — "Abolish WINNER_FILTER, immediate hotfix"

**Reject the "immediate hotfix" framing.** The 0%-accuracy / 100%-blocked-picks-were-winners claim is internally suspicious (a perfect inverse signal is rare and usually points to selection bias in the shadow-block sample). The deepseek peer-review at `.tmp_research/deepseek_response.md` §4 makes the same point. **Run 14 days of shadow with the filter disabled, log counterfactual outcomes, then decide.**

### Rec 22 — "Futures accumulation mode (n=2 expert judgment)"

**Reject.** Below the project's minimum n=10 for any scoring-path change.

---

## 5. Priority sequencing (replaces the DOCX's "Phase 0/1/2" framing)

| Wave | Items | Gating dependency | Why first |
|---|---|---|---|
| **Wave 1 — unblocking infra** | Recs **16, 18, 29, 30** (resolver retry cap + scalp floor + alias map; `track_calculator.py`; 12-field schema) | None | Until `track_wr` is produced and resolver noise drops below 5%, every downstream gate-tuning, asset-class-elimination, and decay-ladder claim is uninterpretable. |
| **Wave 2 — wire-up of already-shipped foundation** | Recs **32, 33, 34, 35, 5, 8, 26** | Wave 1 | Modules exist on main; need callers in `audit_trail/dashboard_generator.py`, `alpha_engine/regime_position_sizer.py`, and a real circuit-breaker on `production_scanner.py`. |
| **Wave 3 — feature-flagged gate replacement** | Recs **1, 2, 3, 6, 7, 20** (`elite_score` → `ml_score`; R:R floor; bond floor; round; conditional unban) | Wave 1 | All ship under `hf_quality_gates.json` `enabled=false` first; flip after 14-day shadow. |
| **Wave 4 — new strategies** | Recs **17, 21, 23, 24, 28** | Wave 1, transaction-cost layer | Each ships as opt-in sidecar with `## Wiring Plan`. |
| **Defer / reject** | Recs **22, 25, 26, 27, 31** | n/a | See §4 above. |

This converts the DOCX's nominal 12-week / 258-hour plan to a roughly 8–10 week executable sequence with explicit dependency links and per-wave acceptance criteria.

---

## 6. Compliance checklist for the eventual PRs

For every PR that lands a piece of the DOCX, the author must confirm:

- [ ] **Wire-Up Rule** (`CLAUDE.md`): module has at least one production caller, OR PR body has `## Wiring Plan` and is labeled opt-in/sidecar.
- [ ] **Default-OFF + 14-day shadow** for any production-behaviour change; rollback path documented.
- [ ] **Audit-dashboard push-paths** (`AGENTS.md`): if the new file is invoked by `audit-dashboard.yml`, add it to `paths:` in the same PR.
- [ ] **Mutation 3-axis protocol** for any `BLOCKED_SOURCE_SYSTEMS` expansion or strategy demotion.
- [ ] **Updates `.MD`** (`AGENTS.md` "Document Every Fix"): each PR ships with `updates/<date>-<slug>.md` covering what was broken, what changed, how it was verified.
- [ ] **No `index.html` overwrites** — edit `audit_dashboard/template.html` only.
- [ ] **`tools/deploy_sports_files.sh`** if any sports-pipeline file changes (irrelevant for most of these recs but flagged for completeness).

---

## 7. Specific file-level diffs the DOCX gets right

These are the cleanest, lowest-risk changes from §10.3 of the DOCX and should land first:

1. **`audit_dashboard/hc_filter.js:302`** — `var fwdWr = Number(p.track_wr || p.strat_fwd_wr || p.forward_wr || 0);` Reads new field with fallback. **Zero behaviour change** until `track_calculator.py` populates `track_wr`.
2. **`alpha_engine/hedge_fund_quality_gate.py`** — add `round(elite_score, 2)` coercion (Rec 2). One-line, defensive.
3. **`alpha_engine/outcome_resolver.py:97`** — make `PNL_WIN_THRESHOLD` asset-class-keyed (the existing v2 hook); add `MAX_RESOLVE_RETRIES=3` with FLAT closure. Resolves the 63–67% FOREX/COMMODITY noise share.
4. **`config/hf_quality_gates.json`** — add forex `autoRelax` floor + bond-specific keys, leave `"enabled": false`. Wave-3 candidate.

Items 1–3 are unconditional wins. Item 4 is the feature-flag scaffolding for Waves 3+.

---

## 8. References

- `e:\findtorontoevents_antigravity.ca\.tmp_research\kimi_docx_extracted.txt` — DOCX as plain text (492 paragraphs)
- `e:\findtorontoevents_antigravity.ca\.tmp_research\kimi_pr658_master.md` — PR #658 master MD (1,573 lines, near-line-for-line port of the DOCX)
- `e:\findtorontoevents_antigravity.ca\reports\KIMI_DOCX_VS_PR658_GAPS_2026_05_02.md` — prior gap analysis (orphan-footnote finding)
- `e:\findtorontoevents_antigravity.ca\updates\2026-05-02-hedge-fund-grade-uplift-foundation.md` — what already shipped on `copilot/research-revolutionary-strategies` (statistical_rigor / hrp_allocator / decay_tracker / reconciliation_report + 8 personas)
- `e:\findtorontoevents_antigravity.ca\reports\action_B_resolver_2026_04_27.md` — resolver fix plan and noise-share measurement
- `e:\findtorontoevents_antigravity.ca\reports\HEDGE_LIBS_LEVERAGE_AUDIT_2026_04_22.md` — 20/21 orphan rate that motivated the Wire-Up Rule
- `e:\findtorontoevents_antigravity.ca\.tmp_research\deepseek_response.md` — independent peer review flagging selection-mechanism risk on WINNER_FILTER claim
- `AGENTS.md`, `CLAUDE.md`, `TESTING_PROTOCOL.MD`, `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`, `docs/MUTATION_THREE_AXIS_PROTOCOL.md`

No production code was modified by this review.
