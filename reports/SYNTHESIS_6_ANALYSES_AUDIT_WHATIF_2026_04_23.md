# Synthesis: 6 parallel what-if analyses on `/audit` picks — 2026-04-23

Six different agents (Cursor, Google Antigravity, Claude Code, Roo Code/Deepseek, GitHub Copilot, MiniMax M2.7 via Freebuff, Grok Code Fast via Kilo — counting 6 + my own) produced parallel analyses answering "if we had traded yesterday's `/audit` picks, which AC wins, and what's the IDEAL filter — especially for BOND/ETF currently marked no-validated-edge."

This synthesis ranks each agent's contribution by axis, calls out factual errors, and recommends the merge order.

---

## 1. Axis map — who answered what

| Agent | Primary axis | Main deliverable |
|---|---|---|
| **Cursor (PR #361)** | Code path & policy rationale | `tools/audit_what_if_entry_day.js` + scoping methodology; confirmed `filterHcStrict` → `passesValidatedEdgePerClass` **intentionally drops BOND/ETF/FUTURES** |
| **Google Antigravity (PR #362 sibling)** | Per-AC filter thresholds from ledger | Reused `tools/what_if_trade_analysis.py`; EQUITY 84% WR, ETF "not dead" at `FWD WR>=60%` |
| **Claude Code (me, PR #362)** | Per-AC filter thresholds + BOND symbol drill | Same ledger; BOND edge on `ZN=F + futures_momentum` n=8 PF 25.9; ETF edge on `strat_fwd_wr>=60` n=22 PF 6.73 |
| **Roo Code / Deepseek** | Data supply hygiene | Non-crypto data-starved claim — but **based on wrong data source** (see §3) |
| **GitHub Copilot** | Realized yesterday HC performance | Ran `hc_filter.passesHighConvictionPick` in Node on `dashboard_payload.json`: HC yesterday = 21 picks, WR 81%, +44 pnl |
| **MiniMax M2.7** | Per-AC confidence sweet spots + UI transparency | Concrete confidence bands: CRYPTO 0.85-0.90, EQUITY AVOID 0.85-0.90 (20% WR!), FOREX 0.75-0.80 |
| **Grok Code Fast** | Portfolio-level rules | Consensus_score > 0.7, 20% per-AC exposure cap, direction diversity, timeframe prioritization |

---

## 2. Convergent findings (5-of-6 or 6-of-6 agree)

- **EQUITY has clear edge** (6/6 agree). 84% WR on last-50; PF 1.43 all-time; `Breakout Momentum` is the workhorse strategy.
- **CRYPTO needs tightening** (6/6 agree). Confidence ≥ 0.85-0.90 band profitable; avoid DOGE/OP/LINK/ADA (same symbols in `hedge_fund_quality_gate` from PR #346).
- **COMMODITY: only `futures_momentum` survives** (5/6 agree). Kill `cot_positioning`, `cta_commodity_momentum_term`, `cftc_cot_commercial_signal`.
- **FOREX: edge is thin but positive in recent windows** (5/6 agree). Tighten via confidence + symbol selection (`USDJPY=X`, `USDCHF=X` positive; `EURJPY=X`, `AUDUSD=X` drags).
- **BOND/ETF: intentional drop in `filterHcStrict`** (Cursor's unique clarification, accepted). The "no validated filter" label is policy, not bug.

---

## 3. Divergent findings + factual errors

### 3a. Roo Code used the wrong data source (CRITICAL)

Roo Code's claim: "Non-crypto classes have 0-34 closed picks — no statistics are reliable." That's based on `alpha_engine/data/closed_picks.json`, which I verified contains:
- 6,031 rows total
- **5,285 NULL asset_class** (effectively crypto with missing tags)
- 4 COMMODITY, 2 FOREX, 1 EQUITY (the only non-crypto tags)

The **correct** source is `audit_dashboard/data/dashboard_data.json.picks.recent_closed` (3,500 rows with full AC coverage: 1,648 CRYPTO / 790 FOREX / 607 COMMODITY / 357 EQUITY / 78 ETF / 17 BOND) — matches `audit_trail/data/dashboard_payload.json` which GitHub Copilot used correctly.

**Impact:** Roo Code's "non-crypto data-starved" conclusion is wrong. The data exists; it's in the dashboard payload.

**Remaining Roo findings with merit** (generalize beyond their wrong premise):
- Confidence ≥ 0.90 sweet spot (MiniMax independently confirms for CRYPTO specifically)
- SHORT bias on crypto worth investigating (matches memory `feedback_long_source_bias.md`)
- "Don't trust marketing WR" (matches `feedback_confidence_is_not_edge.md`)

### 3b. MiniMax's claim: "params aren't in `config/hc_gate_params.json`"

**Also wrong.** I just verified the file contains:
- `forwardWRMinPctBond: 40`, `forwardWRMinPctETF: 40`, `forwardWRMinPctCommodity: 40`, `forwardWRMinPctFutures: 40`
- `scoreFloorBond: 35`, `scoreFloorCommodity: 35`

The params DO exist. What's missing is the **validated-edge certification** — `passesValidatedEdgePerClass` drops those classes regardless of whether the params would admit picks. MiniMax's code reference is right; the interpretation is wrong.

### 3c. Antigravity + me: "ETF is NOT dead"

Ledger PF for ETF = 1.16 on n=78. Filter `strat_fwd_wr>=60` gives PF 6.73 on n=22. **Both are in-sample optimizations.** Without purged K-Fold CV, we can't promote.

Cursor's read ("strict drops ETF by design, for a reason") and MiniMax's read ("exclude from HC until n ≥ 30 validated") are more conservative and arguably correct pending OOS evidence.

### 3d. MiniMax's unique value-add: per-AC confidence danger zones

| AC | Sweet spot | Avoid |
|---|---|---|
| CRYPTO | 0.85-0.90 (82% WR) | — |
| **EQUITY** | ≥ 0.90 OR < 0.85 | **0.85-0.90 = 20% WR (danger!)** |
| **FOREX** | 0.75-0.80 (49% WR) | **0.70-0.75 = 25% WR (danger!)** |

These are the **most actionable new findings** in the set — specific, testable bucket findings that can go straight into `hc_filter.js` as "reject confidence in danger band" rules. Independent of BOND/ETF policy debate.

### 3e. Grok Code Fast's unique value-add: portfolio-level rules

| Rule | Purpose |
|---|---|
| `consensus_score > 0.7 AND total_systems > 1` | Require multi-source agreement |
| 20% exposure cap per AC | Diversification |
| Confidence-weighted position sizing | Risk proportional to edge |
| 1h/4h > 15m | Noise reduction |
| Direction diversity: 60/40 LONG/SHORT | Regime-balanced |

**Orthogonal to per-AC filters.** Can layer on top of whatever the HC gate decides. Most useful for position-sizing + diversification, not filter logic.

---

## 4. The integrated recommendation

The 6 analyses collectively suggest a **layered approach** rather than any single filter:

### Layer 1 — Current HC gate (already shipping)
Keep `hc_filter.passesHighConvictionPick` + `filterHcStrict` as is. Cursor's PR #361 formalizes this as the canonical reference.

### Layer 2 — Per-AC confidence danger zones (NEW, MiniMax-sourced)
Add rejection bands for EQUITY `confidence ∈ [0.85, 0.90)` and FOREX `confidence ∈ [0.70, 0.75)`. These are specific enough to unit-test and small enough to shadow-mode quickly. **High-leverage, low-risk.**

### Layer 3 — Portfolio rules (NEW, Grok-sourced)
Consensus threshold + per-AC exposure cap + direction-diversity. Layer these at the EXECUTION step, not the pick-generation step (per memory `feedback_gate_at_execution_not_generation.md`).

### Layer 4 — BOND/ETF pilot (DEFERRED)
The Antigravity + my data evidence is compelling but in-sample. **Run purged K-Fold CV** using `alpha_engine.integrations.purged_cv_core` (PR #346 ecosystem) before proposing any change to `passesValidatedEdgePerClass`. Shadow-mode for 2 weeks after OOS validates.

### Layer 5 — Data hygiene (from Roo, partially valid)
Fix the 5,285 NULL `asset_class` rows in `alpha_engine/data/closed_picks.json` so downstream consumers that read that file (several still exist) aren't misled. Separate PR; doesn't block Layers 1-3.

---

## 5. PR merge decision

| PR / file | Source | Decision |
|---|---|---|
| **#361** (Cursor — `/audit` tool + methodology) | Cursor | **MERGE** — tool + methodology only, aligned with conservative consensus |
| **#362** (my + Antigravity analysis) | Me + Antigravity | **KEEP OPEN** — valid data findings but require OOS validation before wiring into filter code |
| `updates/2026-04-23-whatif-asset-class-hc-filter-synthesis.md` (Roo Code) | Roo Code | **FLAG data-source error in file header** — keep the generalizable findings (confidence 0.90 + SHORT bias) but demote the "non-crypto is starved" claim. Ideally close its PR if it has one. |
| (GitHub Copilot response) | Copilot | No PR to merge; findings consistent with consensus. |
| (MiniMax response) | MiniMax / Freebuff | No PR. **Open a small PR implementing the per-AC confidence danger-zone rule** (Layer 2). High ROI. |
| (Grok Code Fast response) | Grok / Kilo | No PR. Queue portfolio-rules PR (Layer 3) for a later round. |

---

## 6. What I'm shipping now

1. **This synthesis doc** (source of record for the 6-agent round).
2. **Recommend merge of Cursor's PR #361** (tool + methodology; safe, conservative).
3. **Keep PR #362 open** with a comment pointing to §4-5 of this doc as the consolidated roadmap.
4. **Queue** the MiniMax confidence-danger-zone rule as a small follow-up PR if no other agent ships it in the next round.

## 7. Risks + caveats

- **Survivorship bias in "what won yesterday"**: yesterday's +44 pnl on 21 HC picks is one day. Don't treat as policy signal.
- **In-sample optimization**: Antigravity + mine + MiniMax + Grok all suggested filters from the ledger they observed. None has done purged K-Fold. Before ANY of these ship to live picks, run OOS CV.
- **Concept drift**: `futures_momentum` is the workhorse in 3+ analyses. If it fails, commodity + bond edges collapse simultaneously.
- **MiniMax confidence danger-zone needs shadow-mode first**: the `[0.85, 0.90)` EQUITY avoid-band is based on one closed-trade sample. Confirm out-of-sample before enforcing.

---

## 8. Addendum — 7th agent: OpenCode Big Pickle

A 7th agent (OpenCode Big Pickle) independently read `audit_dashboard/data/whatif_analysis.json` and the Roo Code `.md`, then proposed:

- **Primary axis: `strat_fwd_wr >= 70`** (stricter than my `>=60` cut).
- **SHORT bias for crypto** (+10pp edge) — corroborates memory `feedback_long_source_bias`.
- **Time-of-day filter**: best 21:00–23:59 UTC (45–72% WR), death zone 08:00–09:00 UTC (17–19% WR) — corroborates memory `project_clean_data_symbol_wr.md` (22 UTC = 61.2% WR).
- **Block RANGING / TRENDING_DOWN regimes** (6.2% WR or worse).
- **Remove confidence gates entirely** — claims confidence is anti-predictive below 0.85 on crypto.

### Where Big Pickle *conflicts* with MiniMax

Big Pickle: "remove confidence gates." MiniMax: "add confidence danger-zone rejections." These are NOT opposites. Reconciliation:

- **Big Pickle is right for CRYPTO** — confidence below 0.85 is noise, so the existing low floor is wasted.
- **MiniMax is right for EQUITY/FOREX** — there IS a danger band (0.85–0.90 EQUITY, 0.70–0.75 FOREX) where WR inverts.

The combined rule: "confidence gate should be AC-specific, not a flat floor." This is a concrete unit-testable change to `hc_filter.js` and becomes the highest-ROI Layer 2 update.

### Big Pickle's unique value-adds

1. **TOD filter** (new — no other agent proposed it). Adding to Layer 3 as an execution-step rule.
2. **Regime blocklist** (block RANGING / TRENDING_DOWN) — cheap to implement, aligns with existing regime plumbing.

### Big Pickle inherits Roo's wrong premise

Big Pickle cited Roo's file (`updates/2026-04-23-whatif-asset-class-hc-filter-synthesis.md`) as a source for "bonds: 0 closed picks." That's Roo's wrong-data-source claim propagating. The dashboard payload has 17 BOND closed picks with full AC tags. Treat Big Pickle's "non-crypto data-starved" framing as secondhand error.

### Updated layered plan with Big Pickle folded in

| Layer | Rule | Source |
|---|---|---|
| 2a | AC-specific confidence policy: no floor for CRYPTO; EQUITY reject [0.85, 0.90); FOREX reject [0.70, 0.75) | MiniMax + Big Pickle (reconciled) |
| 2b | SHORT bias on CRYPTO (require SHORT on red BTC 4h, or +10pp score) | Big Pickle + `feedback_long_source_bias` |
| 3a | TOD execution filter: skip new entries 08:00–09:00 UTC, prefer 21:00–23:59 UTC | Big Pickle |
| 3b | Regime blocklist: skip entries when current regime ∈ {RANGING, TRENDING_DOWN} | Big Pickle |
| 3c | Portfolio rules: consensus > 0.7, 20% per-AC cap, direction diversity | Grok |

Layers 1, 4, 5 unchanged from §4.

---

## 9. Addendum — 8th agent: GitHub Copilot Cloud (PR #365)

GitHub Copilot Cloud filed `updates/2026-04-23-asset-class-pick-analysis.md` (PR #365) with arguably the highest-data-quality analysis in the set — 444 lines driven from `audit_trail/data/dashboard_payload.json` + `hc_edge_baseline.json` + `universal_resolved_picks.json` + `data/live_picks.db` (25,279 live_picks + 129,374 pick_history rows).

### Unique findings NOT covered by any other agent

1. **FOREX P&L asymmetry is structural, not filter-able.** 47.5% WR but **profit_factor = 0.26** — avg_loss ($2.55%) is 3.4× avg_win ($0.74%). Root cause: `alpha_engine/config.py` uses `forex: (-0.005, 0.0075, 7)` → SL 0.5%, TP 0.75%. Absolute moves too small — spread drowns the edge. **This is a TP/SL config fix, not an HC gate fix.**

2. **`quan_engine` MATICUSDT data artifact.** Of 1,001 `quan_engine` picks, **755 are MATICUSDT LONG all hitting fixed 2.5% TP** (WR = 100%). Remaining ~250 picks have ~12% WR. Inflates system-level stats. **Relates to memory `project_confidence_rho_matic_artifact`** (660 MATIC 0%-WR ghost rows that flip confidence→WR ρ from +0.023 to -0.127) — same symbol, possibly same underlying data-pipeline bug.

3. **Measured HC lift per AC** (from `hc_edge_baseline.json` audited 2026-04-15):
   | AC | Ungated WR | HC WR | Lift |
   |---|---|---|---|
   | CRYPTO | 50.6% | 60.3% | **+9.7pp** |
   | EQUITY | 39.1% | 68.1% | **+29.0pp** ⭐ |
   | FOREX | 48.0% | 65.8% | **+17.8pp** |
   EQUITY +29pp is the largest observed lift — justifies Cursor's strict path being the primary hero filter for EQUITY.

4. **Source-system cumulative-PnL blacklist candidates** (capped):
   - `kimi_signal_tracking` **-522.7%** ← worst in fleet
   - `claude_gainer_st` -204.3%
   - `alpha_engine_fast` -126.5%
   - `rapid_fire` -41.6%
   - `paper_trading` -19.5%
   - `ml_crypto_pred` -13.7%

   These should be added to `BLOCKED_SOURCE_SYSTEMS` — but per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` + `docs/MUTATION_THREE_AXIS_PROTOCOL.md`, demotion requires mutation-analysis first. Don't skip the kill protocol.

5. **Consensus-only filter**: `aggregated_picks` with 3+ system agreement had **88.9% WR** yesterday. This matches Grok's Layer 3 "consensus_score > 0.7" proposal with a concrete measurement.

### Where Copilot Cloud reinforces prior findings

- **ETF this week: 84.6% WR, +2.50% avg** — corroborates Antigravity (85% WR last-20) + my data (n=78 PF 1.16). 3-way agreement that ETF is NOT dead.
- **EQUITY premium filter (score≥50, conf≥0.65): 84.6% WR last 7 days** — corroborates MiniMax "EQUITY ≥0.90 OR <0.85" (different threshold, same direction).
- **FOREX strategy-level edge exists** (Bollinger MR 69.2%, forex-rsi-ema-scout 61.5%) but killed by TP/SL config. Suggests Copilot's TP/SL fix is more leveraged than more filter tightening.
- **CRYPTO `dna_rapid_fire_mutations` 11.8% WR today** — corroborates convergent 6/6 "CRYPTO needs tightening".

### Where Copilot Cloud *disagrees* with Cursor's conservative read

Cursor: "ETF drop in `filterHcStrict` is policy, not bug. Don't second-guess without OOS."

Copilot: "ETF is performing best this week at 84.6% WR. `hc_edge_baseline.json` rejected it at N=19 — but N has grown to 75+. **Run `audit_trail/hc_edge_revalidation.py` with ETF threshold setting.**"

Reconciliation: Copilot is right that the rejection is stale (2026-04-15, N=19). Cursor is right that we shouldn't change the strict gate without OOS. Compromise: re-run `hc_edge_revalidation.py` on current N=75+ data → IF it passes with purged K-Fold CV → ship ETF admission. This becomes a concrete unblock condition for Layer 4.

### Unified blocker list for any live change

Copilot's analysis crystallizes the pre-conditions for anything shipping to `hc_filter.js` / `passesValidatedEdgePerClass`:

1. **Run `audit_trail/hc_edge_revalidation.py`** with purged K-Fold CV on current data (N=75+ for ETF, N=17 for BOND).
2. **Fix FOREX TP/SL config** (`alpha_engine/config.py` → TP 1.5–2.0%, SL 0.7–1.0%). Independent of filter logic. Highest-leverage single change in this entire synthesis.
3. **Fix `quan_engine` MATICUSDT artifact** before any source-system-weighted filter is built on top of `universal_resolved_picks.json`.
4. **Shadow-mode Layer 2a** (AC-specific confidence) + Layer 3a/3b (TOD + regime) for 2 weeks before enforcement.

### Updated merge-decision table (from §5)

| PR / file | Source | Decision |
|---|---|---|
| #361 (Cursor) | Scope-pure tool + methodology | **MERGED** (2026-04-23T20:06Z) |
| #362 (Antigravity + me) | Per-AC filter findings | **KEEP OPEN** pending OOS |
| #365 (Copilot Cloud) | 444-line docs-only report | **MERGE** — docs-only, zero risk, highest-data-quality single doc in the set |
| Roo synthesis | Wrong data source | **FLAGGED** with correction banner (committed) |
| #364 (this synthesis) | Cross-agent consolidation | **KEEP OPEN** as living audit trail |

### New highest-ROI follow-up (replaces earlier §4 Layer 2 ordering)

1. **FOREX TP/SL config fix** — 1-line change in `alpha_engine/config.py`, unit-testable, shadow-mode friendly. Likely recovers 200+ FOREX picks/week from losing to break-even/winning.
2. **ETF HC revalidation** — `audit_trail/hc_edge_revalidation.py` rerun with N=75+. If purged K-Fold approves, ship ETF admission to `passesValidatedEdgePerClass`.
3. **Source-system blacklist update** — per kill protocol, mutation-analyze `kimi_signal_tracking` / `claude_gainer_st` / `alpha_engine_fast` before demoting.
4. **Layer 2a AC-specific confidence rule** (MiniMax + Big Pickle reconciled).
5. **Layer 3 portfolio rules** (Grok + Big Pickle TOD + regime blocklist).

(1) is now the single highest-leverage change across all 8 analyses.
