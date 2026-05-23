# `/audit` enhancement — full review package (shipped + remaining)

**Date:** 2026-04-20
**Purpose:** single-document review package for external AI review. Covers both (a) changes shipped to `main` today, and (b) remaining plan (Phases 2, 4, 6) for sign-off before implementation.

---

## PART A — Context: what `/audit` is and what we found today

`findtorontoevents.ca/audit` is a trading-signal dashboard surfacing picks across several feeds: **Active Picks**, **Smart Picks**, **Verified Alpha**, **High Conviction**, **Closed Picks**. Backed by ~3,500-row `recent_closed` pick history + current active pool.

**Empirical findings from today's effectiveness audit ([docs/AUDIT_EFFECTIVENESS_AUDIT_2026_04_20.md](AUDIT_EFFECTIVENESS_AUDIT_2026_04_20.md)):**

- Aggregate: **WR 39.9%, PF 0.76, −982.5%** across the 3,500 closed picks → product is net-negative at pool level
- **PROVEN trust tier was INVERTED**: WR 26.7% / PF 0.52 (worse than UNTRUSTED at 48.0% / 1.37). Root cause: 790 of 790 PROVEN-tagged closes were `claude_gainer_st` (realized WR 26.7%)
- **High Conviction proxy has real edge**: PF 1.61 / WR 51.6% / n=62
- **Smart Picks / Track% were retroactively unauditable** — no feed-membership flag stamped on closed picks
- **FOREX pnl unit chaos** — decimal (0.0003) and percent (1.28) values co-existed in same payload
- **Blocklist was leaking** — excluding already-blocked strategies flips aggregate PF from 0.72 → 1.10 (`+155%` on same window). Product is profitable on paper; enforcement was the gap.

**Session peer-review discipline:** every major change was vetted by multiple AI reviewers (engineer, product, statistical, ops, formal, quant) before commit; 3 blockers + 7 should-fix items were caught and fixed pre-ship.

---

## PART B — Changes SHIPPED TO MAIN today (for review)

### B.1 Enforcement hardening (blocklist + hygiene)

**Commit `0b2f5d01b`** — `alpha_engine/feed_hygiene.py`
Wired composite-pair check into `is_valid_active_pick`: previously only `is_blocked_strategy(name)` was called (dead code for composites). Now `is_blocked_pick(pick)` catches `(source_system, strategy)` pairs like `(kimi_signal_tracking, default)` on forex.

**Commit `de7a05dbd`** — `alpha_engine/strategy_blocklist.py`
Added `_RETIRED_SYSTEM_STRATEGY_PAIRS` composite blocklist. First entry: `(kimi_signal_tracking, default)` — accounted for 98% of FOREX bleed (-816% of -833%). Blocking this flips FOREX aggregate from -816% to +17%.

**Commit `faba0b66a`** — blocklist enforcement expansion
- `copy_hl_lb_None` is in `_RETIRED_STRATEGIES` but was still emitting via `copy_trader_intel` (n=233, -766%) and `alpha_engine` (n=45, -40%) → added both composite pairs
- `st_obv_support_divergence` promoted from paper-only to retired (17% WR, 35.9pp drop from baseline)
- 9 new closed-pick schema fields added to `_CLOSED_PICK_KEEP_FIELDS` for retroactive auditability

**Commit `45d567454`** — luxalgo_confluence + golden_combo paper-flags
Kimi fact-check caught Gemini's `mine_consensus_edge.py` math errors (summing averaged percentages). Paper-flagged 6 strategies pending validation.

**Commit `77910d1dc`** — 14 strategies paper-flagged
PR #262 baby-strategy batch, PR #265 commodity strategy, plus 3 Gemini-decay candidates (`st_fear_greed_contrarian`, `st_obv_support_divergence`, `crypto_mtf_ema_slope_alignment_v1`).

**Commit `75ae5dbc4`** — `st_fear_greed_contrarian` hard-retired
Gap-check found 640 closed picks under this `st_`-prefix variant (10.5% WR, −381% PnL) — #1 historical-damage driver. Promoted from paper-only to retired.

**Commit `75ae5dbc4`** — `audit_trail/mysql_client.py::mysql_fetch_closed_non_crypto`
7 closed rows were mis-tagged EQUITY (`LINKUSDT`, `GC=F`, `BCH-USD`). Root cause: `_cat_map.get(cat_raw, "EQUITY")` silently defaulted unknown DB categories. Fixed to derive from symbol via `resolve_asset_class` first.

**Commit `67f1a038e`** — `alpha_engine/feed_hygiene.py` + tests
- **Reject anonymous strategies at ingest:** `""`, `"unknown"`, `"default"`, self-named (`strategy == source_system`) → now rejected
- **Default `entry_time`** from `timestamp` / `created_at` / `opened_at` / `generated_at` when missing
- **Normalize FOREX pnl units:** decimal values (|v|<0.05) on `=X` symbols rescaled ×100 to percent form
- 22 unit tests covering all three

**Commit `fb72ac9f6`** — `.github/workflows/dynamic-alpha-engine.yml`
ALPHA ENGINE Dynamic Runner was failing 40+ consecutive runs due to push-lock contention ("Run Alpha Engine" succeeded, "Commit results" died in retry loop). Two fixes:
1. `concurrency:` group serializes the workflow against itself (cron fires every 30min but runs take 45+min)
2. Retry loop bumped 5→10 attempts with wider backoff (max ~8min total)

### B.2 Scoring recalibration

**Commit `cb54fee16` — Phase A: `classify_pick_quality_v2`**
`audit_trail/quality_gates.py` had two divergent "smart pick" definitions: `classify_pick_quality` used a single global score threshold; `passes_smart_gate` used per-asset floors. v2 delegates to `passes_smart_gate` after cloning `status="ACTIVE"`, so analytics on closed picks match production semantics.
- 3 tier outputs: SMART / ACTIVE / REJECTED (does NOT conflate — the v1 proposal's Grok-style `v2` which demoted SMART-gate failures to REJECTED was caught in peer review and rejected)
- 4 unit tests pass

**Commit `75e41adc4` — Phase B: `calculate_smart_score` piecewise**
Replaced linear `min(base * 0.3, 30)` in smart-score base term with piecewise:
- `raw ≤ 40`: base = `raw * 0.10` (empirically negative-EV decile)
- `raw ≤ 70`: base = `raw * 0.20`
- `raw > 70`: base = `min(raw * 0.30, 30)`
- Copy-trader (`_is_copy_pick` or `copy_hl_*` prefix) on non-BTC-major: base ×= 0.8 (mirrors existing `elite_scorer.py` cap)
- 12 unit tests pass; known discontinuities at 40 and 70 flagged in commit message

**Commit `77910d1dc` — PROVEN sticky-preserve fix**
`audit_trail/stamp_pick_quality.py::stamp_picks` used to preserve existing PROVEN tags forever (never demoted even if current WR fell below 0.55). Now demotes when current `_assign_trust_tier(wr, n)` doesn't return PROVEN. BANNED/UNTRUSTED remain sticky as intended.

**Commit `534269141` — force-demote `claude_gainer_st`**
Added `_FORCE_DEMOTED_STRATEGIES` narrow-override set. `claude_gainer_st` was 778 of 790 PROVEN closes at 26.7% WR / PF 0.52 — demote trumps any sticky-preserve logic.

**Commit `0c650f9cb` — revert `rr >= 1.00` loosening**
Gemini agent shipped (into our branch) a loosening of ETF/Bond RR from 1.20 to 1.00 — violates v1.1 R:R ≥ 1.5 spirit. Reverted at 6 call sites. Also paper-flagged `copy_hl_whale` (same lineage as retired `copy_hl_lb_None`).

### B.3 Dashboard UI fixes

**Commit `2e7c5421d`** — `audit_dashboard/template.html` frontend errors
- `HYPEUSDT`: added to `_NOT_ON_BINANCE` skip set (was 4× CORS failures per page load)
- `BOME` etc.: `fetchStockPrices` now excludes known crypto even if `asset_class` mis-tagged as EQUITY
- Null-guarded two inline `onclick` handlers referencing possibly-absent tab elements (fixes `TypeError: Cannot read properties of null`)

**Commit `52cdcb61e` — Phase 0: descriptive legend + hide n=0 Guide band**
- Hid the "Maximum Conviction Combo" card that advertised 71.3% WR / PF 13.21 / n=94 — Cursor health pipeline found **n=0** matching picks in current window → unreproducible claim
- Added `#tier-trust-legend` below tab bar: descriptive color-coded feed explanations. **NO point estimates.** Footer: "Risk-adjusted metrics pending; no headline claims until Phase 4."

### B.4 Per-pick stamping + activation gates (shipped this afternoon)

**Commit `ed9c5bb85` — Phase 1: at-issue stamping**
New `audit_trail/feed_membership.py`:
- `is_smart_pick_per_pick(pick)` — clones `status="ACTIVE"`, delegates to `passes_smart_gate`
- `is_verified_alpha_per_pick(pick)` — `trust_tier="PROVEN"` AND `source in VERIFIED_ALPHA_SOURCES` AND strategy NOT in `_FORCE_DEMOTED_STRATEGIES` (auto-propagates human overrides)
- `evaluate_hc_tier(pick)` — PLACEHOLDER thresholds labeled in docstring (Phase 3 parity-tests)
- `VERIFIED_ALPHA_SOURCES = {"claws_of_doom"}` — deliberately narrow; `claude_gainer_st` removed to match the force-demote

`audit_trail/stamp_pick_quality.py::stamp_picks`:
- Imports hoisted above the per-pick loop (security reviewer caught redundant N dict-lookups)
- Stamps `is_smart_pick` / `is_verified_alpha` / `hc_tier` with OVERWRITING semantics
- Snapshots `at_issue_*` twins exactly once on ACTIVE→CLOSED transition, frozen thereafter
- Per-pick try/except isolation — one bad pick can't abort the loop

11 unit tests pass.

**Commit `b0d5b56b7` — Phase 5: Wilson LB + hysteresis**
`audit_trail/guide_band_activation.py`:
- `wilson_lower_bound(wins, n, z)` — standard formula, `wins > n` raises `ValueError`
- `should_activate_guide_band(wins, n, currently_active, min_n=50, activate_at=0.52, deactivate_below=0.45, alpha=0.05, k=1)`:
  - `min_n=50` gives ~70% power for one-sample `p=0.50 vs 0.65` (methodology reviewer recomputed; was incorrectly documented as 80%)
  - `activate_at=0.52` raised from 0.45 (DeepSeek power analysis: 0.45 at n=20 only discriminates WR 0.78 vs 0.50)
  - `deactivate_below=0.45` gives ~0.07 hysteresis gap ≈ 1 SE of phat at n=50 (was 0.05, too tight)
  - Bonferroni: `k > 1` adjusts activate bar via `1 - alpha/k`

`audit_trail/dashboard_generator.py`:
- Reads state from `audit_dashboard/data/guide_band_state.json`
- Counts `(wins, n)` on PROVEN + confidence 0.8-0.9 slice of `recent_closed`
- Calls `should_activate_guide_band`, writes `summary["guide_band_proven_conf_80_90"]`
- **Atomic write** via tmp + `os.replace` (security reviewer)

`audit_dashboard/template.html`:
- Inline script conditionally renders activated state with live Wilson LB / n / wins when `summary.guide_band_proven_conf_80_90.active === true`
- Falls back to "insufficient sample" caveat otherwise (backward-compat with old payloads)

10 unit tests pass.

**Commit `09e1dd058` — Phase 3: HC evaluator parity test**
`tools/hc_parity_test.js` — Node CLI reusing `audit_dashboard/hc_filter.js` via `require()`. No headless browser; stdin/stdout JSON. `hc_filter.js` already guards on `typeof window` so no stubs needed.

`tools/hc_parity_test.py` — pipes full 3,500 `recent_closed` through both Node and Python evaluators, diffs pick-by-pick. Exits non-zero on any divergence. Writes `tools/data/hc_parity_baseline.json`.

`.github/workflows/hc-parity.yml`:
- Schedule: Mon 15:00 UTC (slot unused by other crons)
- **ALSO triggers on PR paths** touching `hc_filter.js` / `hc_gates_python.py` / `feed_membership.py` / the parity tests themselves (v1.1 governance reviewer: catches drift at PR review, not just weekly)
- `concurrency:` group prevents dispatch/cron collision
- Validation-only; no auto-commit

Local run result: 3,500 picks, **0 divergences**. JS 0.22s, Python 0.02s.

### B.5 Analytics & governance docs (shipped for posterity)

- `docs/AUDIT_EFFECTIVENESS_AUDIT_2026_04_20.md` — headline: PF 0.76 aggregate; HC is real edge
- `docs/AUDIT_ADDITIONAL_FIXES_2026_04_20.md` — blocklist-leakage flip finding
- `docs/AUDIT_DATA_PIPELINE_GAP_CHECKS_2026_04_20.md` — upstream source-file health + forward_wr dead-field audit
- `docs/GEMINI_WALKTHROUGH_REVIEW_2026_04_19.md` — reconciliation of Gemini's claims against independent verification
- `docs/POST_GEMINI_ACTIONS_2026_04_19.md` — blocklist candidates + `forward_win_rate` dead-field audit + PROVEN regression diagnosis
- `docs/REMAINING_ENHANCEMENT_PROPOSALS_V3_2026_04_20.md` — 6-reviewer-vetted plan that drove today's work
- `docs/PHASES_1_3_5_QA_CRITERIA_2026_04_20.md` — pass criteria the 4 reviewers evaluated before today's Phase 1/3/5 commits
- `updates/2026-04-20-bug-cycle-closeout.md` — user-facing recap of fixed / investigated-false-positive / scope-corrected items
- `updates/2026-04-20-remaining-roadmap-phases-1-6.md` — public roadmap entry (Phase 0 live; 1-6 tracked)

### B.6 Test suite

**59/59 unit tests pass** across:
- `tests/test_classify_pick_quality_v2.py` (Phase A, 4 tests)
- `tests/test_calculate_smart_score_recalibration.py` (Phase B, 12 tests)
- `tests/test_feed_hygiene_additional_fixes.py` (anonymous strategy + entry_time + FOREX pnl, 22 tests)
- `tests/test_stamp_feed_membership.py` (Phase 1, 11 tests)
- `tests/test_guide_band_activation.py` (Phase 5, 10 tests)

---

## PART C — Remaining plan (for reviewer sign-off)

### Phase 2 — Historical backfill

**Effort:** ~1 day
**User-visible:** partial (analytics accuracy; no UI change until Phase 4)
**Blocked by:** Phase 1 shipped + at least one full dashboard regen cycle

#### Goal
The 3,500-row `recent_closed` window has zero `is_smart_pick` / `is_verified_alpha` / `hc_tier` fields populated. Phase 1 stamps forward; Phase 2 backfills history.

#### Proposed approach
`tools/backfill_feed_membership.py` — one-shot script:

1. Iterate `recent_closed`:
   - If pick has both `at_issue_trust_tier` AND `at_issue_strat_fwd_wr`: compute the 3 flags against that point-in-time state, stamp live and `at_issue_*` twins
   - Else: stamp `is_smart_pick = null` (explicit null, NOT False) — analytics must exclude nulls from denominators
2. Cross-reference blocklist @ `T_open(pick)` via `git show <sha>:alpha_engine/strategy_blocklist.py` to get point-in-time retirement state
3. Publish coverage ratio to `health_report.json`: `{"phase2_backfill": {"stamped": N, "null_stamped": M, "total": 3500}}`

#### Open questions for reviewers
1. **Blocklist point-in-time fidelity:** git-log gives commit timestamps but not the exact retired-strategy set at `T_open(pick)`. Walking commits is O(commits × picks). Feasible but slow — acceptable one-shot, or too expensive?
2. **null vs False semantics:** downstream analytics must exclude nulls from denominators. Needs audit before shipping.
3. **One-shot vs idempotent re-runnable:** idempotent is safer (new at-issue twins keep appearing as Phase 1 runs), but more plumbing.
4. **Output destination:** mutate `dashboard_data.json` in-place (risky hot file), or sidecar + next regen merge? **This is our hardest open question** — we want reviewer preference.

#### Risks
- Look-ahead leak if we forward-fill from current state (DeepSeek reviewer caught this in v2 → null-stamp unknowns)
- `claude_gainer_st` picks must stamp `is_verified_alpha=False` even for historical rows where trust_tier was still PROVEN (force-demote override)

---

### Phase 4 — Risk-adjusted metrics pipeline (GATES any future banner)

**Effort:** ~3-5 days
**User-visible:** **YES** — unlocks the banner deferred from v2
**Blocked by:** Phase 2

#### Goal
Mercury-quant reviewer's non-negotiable: **no PF banner ships without risk-adjusted companion metrics**. This phase builds that machinery.

#### Required metrics per feed (HC / Smart Picks / Verified Alpha / Active)
1. **Sharpe** (annualized)
2. **Max drawdown** (% equity) + duration
3. **Net-of-cost PF** with explicit fee/slippage assumption
4. **Expectancy in R-multiples**
5. **Regime decomposition:** 3×3 (F&G × BTC-trend) with amber flag on n<10 cells
6. **95% CI on PF** via block-bootstrap on `strategy_id` (NOT iid — trades aren't independent)

#### Proposed files
- `tools/risk_adjusted_metrics.py` — `compute_feed_metrics(feed) -> dict`
- `tools/regime_decomposition.py` — `decompose_by_regime(picks) -> grid`
- `tools/block_bootstrap_ci.py` — block = `strategy_id`
- `docs/FEED_RISK_METRICS_METHODOLOGY.md` — fee assumptions, bucket defs, bootstrap N, zero-loss PF
- `docs/FEED_COST_ASSUMPTIONS.md` — operator-editable defaults
- `audit_trail/dashboard_generator.py` — call into above, stash under `summary.feed_risk_metrics`, `as_of` timestamp
- `audit_dashboard/template.html` — banner with progressive disclosure

#### Open questions for reviewers
1. **Block-bootstrap block:** `strategy_id` vs `(strategy_id, symbol, direction)` vs weekly time-bucket?
2. **Fee/slippage defaults** (provisional):
   - Crypto spot: 0.10% RT + 0.05% slip
   - Crypto perp: 0.06% RT + 0.10% slip
   - Forex major: 0.5 pip + 0.1 pip
   - Equity: $0 + 0.05% slip
   - Bond ETF: $0 + 0.10% slip
   Are these defensible?
3. **Regime bucket granularity:** 3×3 = 9 cells; HC has only 62 picks total → many cells will be amber-flagged. Acceptable UX honesty, or collapse to 2×2?
4. **Zero-loss PF:** cap at 5.0 with footnote, or "no losses in current window" text?
5. **Weekly refresh vs live:** Mercury wanted weekly `as_of` to avoid moving goalposts; dashboard regens every 30min. Cache or live?
6. **Banner copy — nested vs disjoint:** HC ⊂ Smart ⊂ Active (DeepSeek). Show hierarchical (nested) or disjoint (Active\Smart, Smart\HC)?

#### Risks
- **Survivorship bias**: "post-block PF 1.10" is in-sample fit — must be labeled retrospective
- **Power at n=62**: CIs will be wide; must display prominently, no bare point estimates
- **Fees eat the edge**: PF 1.10 gross likely becomes sub-1.0 net

---

### Phase 6 — MFE/MAE schema + writer plumbing

**Effort:** ~2-3 days
**User-visible:** No (data infrastructure)
**Blocked by:** intra-trade price-history availability scoping

#### Goal
Maximum Favorable / Adverse Excursion enables "could the user have held through the DD?" — currently unanswerable. Without MFE/MAE, defensible position-sizing recommendations are impossible (Mercury reviewer).

#### Proposed approach
1. **Schema expansion** in `_CLOSED_PICK_KEEP_FIELDS`: `max_favorable_excursion_pct`, `max_adverse_excursion_pct`, `mfe_at_bar_count`, `mae_at_bar_count`
2. **Forward writer** in `alpha_engine/outcome_resolver.py`: at TP/SL resolution, fetch intra-trade 1m/5m candles, compute MFE/MAE, stamp on closing pick
3. **Backfill** (separate script): Binance klines for crypto (1m back ~9 months, coarser beyond); yfinance 1h for non-crypto (60-day window); record `mfe_source` granularity marker

#### Open questions for reviewers
1. **Historical granularity tradeoffs:** 1h bars smooth over intra-bar extremes. Acceptable with a "low-fidelity" marker, or null-stamp for older picks?
2. **Non-crypto backfill:** yfinance intraday is 60-day limited. Document as permanent data gap?
3. **Forward-path API latency:** 200-pick resolution batches × 2 calls = 400 req per cycle. Rate-limit plan?
4. **UI display:** MFE/MAE columns on `/audit` or just internal Phase 4 enrichment?

#### Risks
- Binance rate limits (1200 req/min); 3,500-pick backfill = 7,000 req → paginate
- Silent fetch failures → must null-stamp, not infinite loop
- Sign-flip bugs if shorts not carefully handled (`entry - min(low)` for shorts vs `max(high) - entry` for longs)

---

## PART D — Sequencing + open asks for reviewers

### Sequencing

| Phase | Effort | User-visible | Prereq |
|---|---|---|---|
| 2 — Backfill | 1 d | Partial | Phase 1 + 1 regen cycle |
| 4 — Risk-adjusted metrics | 3-5 d | **YES (banner)** | Phase 2 |
| 6 — MFE/MAE | 2-3 d | No | Data-availability scoping |

**Total:** ~7-9 engineering days. Some overlap: Phase 6 scoping can run during Phase 2.

### ASKS for reviewers

1. **Phase 2 output destination** — in-place mutation of `dashboard_data.json` vs sidecar file merged by next regen. Precedents in this repo?
2. **Phase 4 block-bootstrap block definition** — `strategy_id` alone sufficient, or need `(strategy_id × symbol × direction)`?
3. **Phase 4 regime bucketing** — 3×3 amber-flag-heavy, or 2×2 until HC has more history?
4. **Phase 4 fee defaults** — sane? industry references?
5. **Phase 6 granularity** — 1h fallback acceptable, or null-stamp older picks?
6. **Cross-cutting** — given today's Phase 1/3/5 review surfaced 3 blockers + 7 should-fix items, what's the likely-blocker pattern for Phase 2/4/6 we should pre-empt?
7. **Shipped work (Part B)** — is there anything we already shipped today that should be rolled back or revised before building on it?

### Lessons we'll apply (from Phase 1/3/5 peer review)

1. Stale docstrings/governance contradictions are blockers (VERIFIED_ALPHA_SOURCES case)
2. Recompute all statistical claims in-doc (n=50 power claim was wrong at first)
3. Auto-propagate human overrides (`_FORCE_DEMOTED_STRATEGIES`) into every new computation
4. Atomic file writes (tmp + `os.replace`) for any new state file
5. Per-pick exception isolation
6. PR-triggered CI on paths that matter
7. Label placeholders as PLACEHOLDER with citation path to validation phase

---

## PART E — Cross-references

**Governance docs:**
- `docs/STRATEGY_FACTORY_V1_1_AMENDMENTS.md` — S-stage ladder
- `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` — escalation path

**Today's audit artifacts:**
- `docs/AUDIT_EFFECTIVENESS_AUDIT_2026_04_20.md`
- `docs/AUDIT_ADDITIONAL_FIXES_2026_04_20.md`
- `docs/AUDIT_DATA_PIPELINE_GAP_CHECKS_2026_04_20.md`

**Roadmap history:**
- v1: `docs/REMAINING_ENHANCEMENT_PROPOSALS_2026_04_20.md`
- v2: `docs/REMAINING_ENHANCEMENT_PROPOSALS_V2_2026_04_20.md`
- v3 (6-reviewer-vetted): `docs/REMAINING_ENHANCEMENT_PROPOSALS_V3_2026_04_20.md`

**QA criteria (used for Phase 1/3/5):**
- `docs/PHASES_1_3_5_QA_CRITERIA_2026_04_20.md`

**Public updates:**
- `updates/2026-04-20-bug-cycle-closeout.md`
- `updates/2026-04-20-remaining-roadmap-phases-1-6.md`

---

## PART F — External reviewer feedback (AI; 2026-04-20)

Structured pass: **what works**, **gaps / nits**, **answers to Part D asks**, **rollback / revise**. This is advisory input for human reviewers; it does not replace sign-off from stats, product, or ops.

### F.1 What’s strong

- **Traceability:** Parts A–E tie empirical findings (aggregate PF, PROVEN inversion, blocklist leakage) to shipped mitigations and to forward work, without mixing “done” and “planned.”
- **Statistical hygiene:** Phase 2’s explicit **null** for unknown at-issue state and rejection of look-ahead forward-fill matches how serious backtests should fail closed.
- **Governance alignment:** Phase 4 correctly treats risk-adjusted metrics and net-of-cost assumptions as **gates** for any future headline/banner, not as optional polish.
- **Operational realism:** Survivorship / wide CI at small *n* / fees eating edge are called out as first-class risks, not footnotes.
- **Review discipline:** The captured lessons (stale docstrings, wrong power claims, atomic writes, path-triggered CI) are the right “blocker pattern” to institutionalize.

### F.2 Gaps, ambiguities, or reviewer nits

- **Part B duplicate SHA:** `75ae5dbc4` appears twice under different bullets (retire `st_fear_greed_contrarian` vs MySQL category fix). Confirm both landed in one commit or split SHAs so external reviewers do not chase a red herring.
- **Extreme aggregate %:** “−982.5%” (and similar) should stay **defined once** in the effectiveness audit doc (pool definition, compounding vs sum of legs, leverage). One pointer sentence in Part A would pre-empt “is this a bug?” questions.
- **Phase 2 blocklist archaeology:** Git history gives **commit-time** snapshots, not continuous time. Consider documenting acceptable error budget (e.g. only picks opened within ±N days of a blocklist change get manual review) or a materiality rule so the O(commits × picks) approach is bounded.
- **Phase 4 bootstrap:** `strategy_id`-only blocks address **cross-strategy** clustering but may miss **serial correlation within** a strategy across time. Worth planning a **sensitivity** path (e.g. weekly or monthly blocks, or hybrid) as methodology appendix material—not necessarily v1 UI.
- **“Done” criteria:** Phase 2 would benefit from a numeric **coverage / null-rate** target (e.g. “≥X% of rows non-null for `is_smart_pick` where at-issue fields exist”) so completion is objective.

### F.3 Answers to Part D reviewer asks (recommended defaults)

| Ask | Recommendation |
|-----|------------------|
| **1 — Phase 2 output destination** | Prefer **sidecar + merge on regen** (or a dedicated merge step) over hot in-place edits to `dashboard_data.json`. Matches the **atomic write** discipline already used for `guide_band_state.json`, reduces partial-write risk, and keeps diffs auditable. If in-place is unavoidable, require tmp + `os.replace` and a single writer. |
| **2 — Block-bootstrap block** | Start with **`strategy_id`** as the primary block (interpretable, matches stated dependence). Add **reported sensitivity** with **time blocks** (e.g. week) when sample size allows. Consider **`(strategy_id, symbol)`** if diagnostics show within-strategy symbol clustering; full `(strategy_id, symbol, direction)` only if data supports it and blocks are not too sparse. |
| **3 — Regime bucketing (3×3 vs 2×2)** | For **HC (n≈62)**, use **pooled headline metrics** on the full HC slice and treat regime grid as **exploratory** with amber / sparse-cell warnings. A **2×2** (or collapsed F&G **or** trend) is reasonable for HC-only views; keep **3×3** for larger feeds (Smart / Active) where cells can support inference. |
| **4 — Fee defaults** | Treat tabled values as **editable defaults**, not empirical facts. Crypto/perp/FX spreads vary by venue, tier, and period—UI should show **assumption + range** and cite `FEED_COST_ASSUMPTIONS.md`. Net PF below 1.0 under conservative fees is an expected outcome to surface, not hide. |
| **5 — Phase 6 granularity** | **1h (or coarse) with explicit `mfe_source` / fidelity flag** is acceptable for historical rows; **null-stamp** where history cannot support the computation. Document yfinance / non-crypto limits as a **known gap**, not a silent best effort. |
| **6 — Cross-cutting blocker pattern** | Expect the same failure modes: **(a)** Python/JS/dashboard **semantic drift** on any new field, **(b)** **look-ahead** and **label leakage** in backfills, **(c)** **copy** that over-claims (banners without CI / net-of-cost), **(d)** **workflow contention** (mitigated for alpha engine; watch any new cron). Pre-empt with path-triggered CI, parity tests where two evaluators exist, and “fail closed” nulls. |
| **7 — Roll anything back in Part B?** | **No blanket rollback** recommended on the basis of this package alone: changes are test-backed and causally linked to identified bugs. **Monitor** smart-score v2 and PROVEN demotion for **second-order effects** (feed ranking shifts, support burden). **Clarify product language** around narrow `VERIFIED_ALPHA_SOURCES` so it is not read as “only one strategy can ever be verified.” |

### F.4 Verdict

**Package is reviewer-ready:** scope, sequencing, and risk register are coherent; remaining work is appropriately gated (Phase 2 before Phase 4 banner). Address the duplicate-SHA nit and optional “aggregate % definition” pointer before wide distribution if you want zero avoidable confusion.

---

**End of review package.**
Reviewers: please respond in structured format per section (what's right / what's wrong / what's missing / verdict). Part B is shipped and running on main; Part C is not yet implemented. **Part F** adds advisory AI feedback; merge or supersede with human reviewer consensus.
