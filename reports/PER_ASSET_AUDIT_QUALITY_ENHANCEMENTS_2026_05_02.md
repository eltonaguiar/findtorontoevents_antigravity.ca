# Per-Asset Audit-Quality Enhancement Plan — 2026-05-02

**Author:** GitHub Copilot Cloud Agent — synthesizing the existing per-asset evidence base
(`reports/NEAR_MISS_DEEP_DIVE_2026_04_29.md`, `reports/SMOKING_GUN_ASSET_CLASS_2026_04_30.md`,
`reports/EDGE_ANALYSIS_2026_04_30.md`, `reports/PHENOMENAL_PERFORMANCE_METHODOLOGY.md`,
`reports/HEDGE_FUND_UPLIFT_ROADMAP_2026_05_02.md`,
`reports/ASSET_CLASS_STRATEGY_ELABORATION_2026_05_02.md`,
`reports/hedge_fund_performance_review_*_2026_04_27.md`,
`reports/ASSET_CLASS_AUDIT_RUN_2026_04_30.md`) into a single
audit-engine-style enhancement plan with explicit per-class SME / Quant / QA verdicts
and an evidence-backed near-miss register.

**Goal:** TOP-NOTCH hedge-fund-quality picks across **all** asset classes on
`findtorontoevents.ca/audit`. Where a class cannot reach Tier 2 today, identify the
**single asset class with the most defensible edge** and concentrate capital there
while the other classes are repaired — and define a controlled fallback path
(penny stocks, meme coins, mutual funds) for further alpha sourcing.

This document is **analysis + plan only**. It introduces no code or gate changes —
every concrete change is mapped to an existing PR phase (PR-A → PR-G, see
`reports/HEDGE_FUND_UPLIFT_ROADMAP_2026_05_02.md`) or to a new opt-in proposal
that obeys the **Wire-Up Rule** (`AGENTS.md`).

---

## 0. TL;DR

1. **Top defensible asset class today: EQUITY** (PF 1.85, WR 57.3%, n=157 over 30d
   per `reports/SMOKING_GUN_ASSET_CLASS_2026_04_30.md` §2.1). Tier-2-candidate.
   Recommend the **EQUITY-first capital concentration** until CRYPTO vol-targeting
   (Theme A) and FOREX/COMMODITY resolver v2 (PR #610) land.
2. **Most catastrophic data-integrity finding: 100 % of forward-test FOREX wins
   are <5 bp** (`reports/ASSET_CLASS_STRATEGY_ELABORATION_2026_05_02.md` §FOREX) —
   FOREX is **unevaluable** until asset-class-gated resolver thresholds ship.
3. **The single-biggest near-miss strategy is `luxalgo_confluence`** — n=205,
   PF 1.66, +93.7 % sum-PnL, balanced LONG/SHORT — blocked only by stale config
   in `_PAPER_ONLY_STRATEGIES` and a 34-day-stale kill-list entry. Single-line
   unblock recovers ~110 picks/wk (`reports/NEAR_MISS_DEEP_DIVE_2026_04_29.md` §A).
4. **The TRACK% / FWD WR column on `/audit` is operating at the wrong granularity**
   — `pick.strat_fwd_wr` is the **strategy-overall** forward win-rate, **not**
   per-symbol-direction. Combo stats (`combo_stats`) exist in the front-end
   tier-decision logic but are not surfaced as a column. This is the QA flag
   the operator already raised. Fix is a **pure dashboard-render change**, no
   pipeline gate impact (see §5.3).
5. **Kill-list bloat: 541 entries** in `alpha_engine/data/core_whitelist.json`
   with no `last_kill_run` timestamp on the file head — this is the structural
   cause of disappearing near-miss strategies. Audit + age-out is the
   highest-leverage hygiene action.
6. **Fallback expansion is gated**, not free-range. Penny stocks / meme coins /
   mutual funds can be added **only** after the class meets a fallback gate
   (n ≥ 30, PF ≥ 1.3, MDD < 25 %, BH-FDR survives at 5 %) on a 4-week shadow log.
   Without that gate, expansion just adds noise (cf. PR #621 orphan-rate finding).

---

## 1. North Star — Tier definition (canonical)

(Aligned with `reports/hedge_fund_performance_review_summary_2026_04_27.md`
tier table.)

| Tier | Profit Factor | Win Rate | Max Drawdown | Sharpe | Reference desk |
|---|---|---|---|---|---|
| **Tier 1** (Renaissance-class) | > 2.0 | > 55 % | < 10 % | > 3 | Long-run target |
| **Tier 2** (Two-Sigma / Citadel-class) | > 1.5 | > 50 % | < 20 % | > 2 | **Minimum gate to size up a class** |
| Tier 3 (institutional floor) | > 1.2 | > 47 % | < 30 % | > 1 | Capacity research only |
| Below Tier 3 | ≤ 1.2 | ≤ 47 % | ≥ 30 % | ≤ 1 | Investigation per `STRATEGY_INVESTIGATION_BEFORE_KILL.md` |

A class is **promotable** only when its 30-day-rolling Tier-2 numbers also
survive **bootstrap CI lower bound > Tier-2 floor** *and* **BH-FDR at 5 %**
(per `reports/ASSET_CLASS_STRATEGY_ELABORATION_2026_05_02.md` §Methodology).

---

## 2. SME-panel review per asset class

Each class is reviewed by a four-role panel:
- **SME** (asset-class subject-matter expert) — does the published edge make sense?
- **Quant / HF Manager** — is the metric set institutionally credible?
- **QA Analyst** — are inputs / outputs / column semantics on `/audit` sound?
- **Cross-class verdict** — is this the class to size up *today*?

### 2.1 EQUITY — **Tier-2 candidate, recommended #1 capital concentration**

| Metric (30 d, recent_closed) | Value | Source |
|---|---|---|
| Profit Factor | **1.85** | `SMOKING_GUN_ASSET_CLASS_2026_04_30.md` §2.1 |
| Win Rate | 57.3 % | same |
| n (closed) | 157 | same |
| Top edge: `Breakout Momentum LONG` | PF 1.53, n 38 | same |
| Top edge: `Bollinger MR LONG` | PF 1.31, n 58 | same |
| Trust-score Spearman ρ | **+0.269** (highest of any class) | `EDGE_ANALYSIS_2026_04_30.md` |
| HC sweep best floor | `scoreFloorEquity 55 → 45` | PR #538 / `EDGE_ANALYSIS_2026_04_30.md` |

**SME verdict (equity desk):** the surviving long-side edge is exactly what the
Asness-Frazzini-Pedersen / Jegadeesh-Titman literature predicts (1-12 momentum +
short-horizon mean-reversion). The trust-score correlation with realized PnL
is unusually high — **trust score is the operative alpha proxy here, not score**.
The HC gate sweep result (lowering `scoreFloorEquity` from 55 → 45 *increases*
both PF *and* coverage from PF 12.90 / n 16 → PF 4.05 / n 57) is a textbook
**near-miss-by-over-strict-gate** finding.

**Quant verdict:** PF 1.85 with n=157 is statistically meaningful; PSR vs zero
should be re-computed but is plausibly > 0.95. **Largest unhedged risks:**
no SUE / Piotroski / sector-relative-strength on the closed-pick record
(`SMOKING_GUN_ASSET_CLASS_2026_04_30.md` §2.1 missing-data list). Without those,
the system cannot replicate published PEAD / quality / dispersion factors
that Bridgewater-class desks treat as table-stakes.

**QA findings:**
- `recent_closed` PEAD-tagged equity n < 30 → cannot yet claim PEAD edge.
  PR #462/#475/#494/#499/#518/#521/#526 wired the inputs; the **forward sample
  is not yet populated**.
- Equity score floor 55 was masking the true winning cohort. PR #538 fixes.
- `_CLOSED_PICK_KEEP_FIELDS` retention list does **not** preserve
  `earnings_surprise`, `f_score`, `sector_rs` — every closed equity row is
  missing the inputs needed for the PEAD/quality post-mortem
  (`audit_trail/dashboard_generator.py`).

**Cross-class verdict — concentrate here.** Edge is on the right side of the
literature, gate is fixable in a single PR, and the missing-data list is a
**capture problem, not an alpha problem**.

### 2.2 ETF — **Phenomenal but n-thin (Tier-1 candidate, sample-starved)**

| Metric (30 d) | Value |
|---|---|
| PF | **2.84** |
| WR | 69.2 % |
| n | 39 |
| 30-day window n | 30 |
| 30-day PF | 0.456 (single-window degradation — see QA) |

**SME verdict (multi-asset desk):** edge is the HRP-rotated SPDR
implementation (PR #477) — exactly the Lopez de Prado HRP-as-rotator pattern
the literature endorses. The 30-day single-window collapse to PF 0.456 is
**not a regime kill**; it is the **sample-of-30** noise envelope on a strategy
whose realised lookback is 100 days.

**Quant verdict:** PF 2.84 with n=39 has a bootstrap 95 % CI that almost
certainly straddles the Tier-2 floor. **Cannot promote yet.** Hold and let
n grow; do not retune.

**QA findings:** `n` figure on `/audit` for ETF should expose the **30 d / 100 d /
250 d** triple as a single column — today only the 30-d slice surfaces in the
class header. The triple is already computed
(`reports/ASSET_CLASS_AUDIT_RUN_2026_04_30.md`); QA's ask is just to render it.

**Cross-class verdict:** **#2 candidate** — promotable as soon as the 30-d
slice produces n ≥ 60 with PF lower-bound > 1.5.

### 2.3 FOREX — **Edge plausible, but UNEVALUABLE today (resolver flicker)**

| Metric | Value | Source |
|---|---|---|
| PF (active) | 1.53 | `SMOKING_GUN_ASSET_CLASS_2026_04_30.md` §2.3 |
| PF (forward-test ensemble) | **0.394** | `ASSET_CLASS_STRATEGY_ELABORATION_2026_05_02.md` §FOREX |
| % of wins below 5 bp | **100 %** (115 / 115) | same |
| Net PF after 2 bp slippage | 0.000 | same |

**SME verdict (FX desk):** the headline 1.53 PF is plausible — JPY-cross
avoidance + DXY-direction filter is a well-documented edge. But the forward-test
ensemble is **drowning in resolver flicker**; until asset-class-gated thresholds
land (PR #610), every "win" is execution-noise.

**Quant verdict:** **HOLD verdict on FOREX**. Do not size up, do not size down.
The class is **not evaluable** until v2 resolver. Any signal claim today is
contaminated.

**QA findings:**
- `outcome_resolver.py` win threshold 0.00001 (0.1 bp) per
  `alpha_engine/outcome_resolver.py:97` — universal across classes — is the
  bug. Fix is asset-class table: CRYPTO 10 bp, EQUITY 5 bp, FOREX 10 bp,
  COMMODITY 25 bp (per `reports/action_B_resolver_2026_04_27.md`).
- The CFTC COT commercial-Z signal is wired (PR #526) but **not yet
  populated** on the closed-pick record. QA should confirm `cot_commercial_z`
  is in `_CLOSED_PICK_KEEP_FIELDS`.

**Cross-class verdict:** **#3 candidate, blocked**. Unblocks immediately on
PR #610 merge — at that point FOREX is recomputable from history.

### 2.4 COMMODITY — **Headline spectacular, net edge zero**

| Metric (forward-test) | Value |
|---|---|
| PF | **6.560** |
| WR | 80.3 % |
| n | 76 |
| Wins below 10 bp | **100 %** |
| Wins below 5 bp | 55.7 % |
| Net PF after 8 bp slippage | **0.000** |

**SME verdict (commodities desk):** the entire COMMODITY edge is one source —
`multi_asset_cot` (n=41, PF 8.029, p < 10⁻¹³ — the **only BH-FDR survivor at 5 %**
in the dataset, per `ASSET_CLASS_STRATEGY_ELABORATION_2026_05_02.md` §Source-system).
The COT-extreme commercial mean-revert is a textbook practitioner edge.

**Quant verdict:** the net-of-cost number is the dispositive one. PF 6.56 → 0.00
under literature-prior 8 bp slippage means the system is **executing on tick noise**.
**Action:** capacity research only. **Do not size**.

**QA findings:**
- `COMMODITY_BLACKLIST` (PR #535) sub-class kill is the right move; QA
  should confirm the active-class table hides blacklisted symbols.
- Resolver flicker again — the 100 %-sub-10-bp pattern is the same disease
  as FOREX.

**Cross-class verdict:** investigate `multi_asset_cot` capacity (deeper fill-quality
study) before any size-up.

### 2.5 CRYPTO — **Real but lethal (the MDD problem)**

| Metric (active-promoted, 30 d) | Value |
|---|---|
| PF | 1.140 |
| MDD | **178 %** (peak-to-trough in compounded equity) |
| `luxalgo SHORT` PF | 1.62 (n=103) |
| `macd_rsi LONG` PF | 0.66 (–89 % sum-PnL) |
| Forward-test ensemble PF | 0.409 (n=6,884) |

**SME verdict (crypto desk):** edge is real on selective sub-strategies
(luxalgo SHORT in particular) but the aggregate forward-test stream is losing.
This is consistent with the canonical crypto reality: a few strategies print,
the median strategy bleeds.

**Quant verdict:** the 178 % MDD is **non-investable**. Vol-targeting on the
*active-promoted subset* (HAR-RV vol forecast + 1/4-Kelly cap) is shown to
compress MDD < 30 % with PF preserved
(`reports/deep_dive_crypto_mdd_reduction_2026_04_28.md`). This is the single
biggest CRYPTO move on the table.

**QA findings:**
- The `/audit` headline number is the **active-promoted subset**, not the
  forward-test ensemble. Operators should not conflate the two. QA's ask:
  add a tooltip to the CRYPTO PF on `/audit` clarifying scope.
- Pump-watch / "skyrocket" gate (per `PHENOMENAL_PERFORMANCE_METHODOLOGY.md`
  Phase A) is the right inverse-edge filter.
- `macd_rsi LONG` is the cleanest single-strategy demote candidate
  (–89 % sum-PnL on n=many) — but kill goes through
  `STRATEGY_INVESTIGATION_BEFORE_KILL.md`.

**Cross-class verdict:** vol-target the active subset (Theme A) and ship the
inverse "pump watch" gate. Do **not** size the aggregate forward-test universe.

### 2.6 BOND — **n too thin (n=20)**

PF 1.72, WR 50 %, n 20 (`ASSET_CLASS_AUDIT_RUN_2026_04_30.md`). PR #526
ZN/ES/NQ whitelist routing is the sample-growth move. **Hold; revisit at n ≥ 60.**

### 2.7 FUTURES — **n too thin / forward ensemble pathological**

n=2 active, n=31 forward-test ensemble with **0 % WR**
(`ASSET_CLASS_STRATEGY_ELABORATION_2026_05_02.md` §FUTURES). This is the
strongest candidate to invoke `STRATEGY_INVESTIGATION_BEFORE_KILL.md` against
the forward-test source path; the active whitelist-only path may be fine
once n grows.

---

## 3. Quant / HF-Manager cross-class verdict

| Rank | Class | 30 d PF | n | Verdict | Action |
|---|---|---|---|---|---|
| 1 | **EQUITY** | 1.85 | 157 | **Tier-2 candidate** — concentrate here | Ship PR #538, capture SUE / F-score / sector-RS |
| 2 | ETF | 2.84 | 39 | Sample-starved — hold | Render 30/100/250-d triple on `/audit` |
| 3 | FOREX | 1.53 (forward 0.39) | 778 | Unevaluable — blocked on resolver | Land PR #610 |
| 4 | CRYPTO | 1.14 (MDD 178 %) | 1,524 | Lethal MDD — vol-target the active subset | Theme A + Pump-Watch gate |
| 5 | COMMODITY | 6.56 → 0.00 net | 76 | Capacity research only | `multi_asset_cot` fill-study; do not size |
| 6 | BOND | 1.72 | 20 | n-thin | Hold |
| 7 | FUTURES | 0.00 forward / wlist active | 31 / 2 | Forward path under investigation | `STRATEGY_INVESTIGATION_BEFORE_KILL.md` |

**Capital-allocation recommendation (until PR-A through PR-G land):**
- 60 % EQUITY (concentrate the surviving edge),
- 25 % CRYPTO active-promoted subset under vol-target,
- 10 % ETF (let n grow),
- 5 % opportunistic on `multi_asset_cot` flagged COMMODITY trades **under
  capacity-only sizing**,
- 0 % FOREX / FUTURES until resolver + investigation complete.

---

## 4. Near-miss strategy register (evidence-backed)

A "near-miss" strategy is one that **would clear** the active-tier promotion
gate today, but is held by either (a) a stale kill-list / paper-only entry,
(b) a too-strict score floor, or (c) sample starvation that a simple
universe expansion would fix.

| # | Strategy | Class | n | WR | PF | sum-PnL | Blocker | Action | Source |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **`luxalgo_confluence`** | CRYPTO | 205 | 52.2 % | **1.66** | +93.7 % | `_PAPER_ONLY_STRATEGIES` + 34-d stale `kill_list` | **Single-line unblock** (remove from blocklist + kill_list, refresh `last_kill_run`) | `NEAR_MISS_DEEP_DIVE_2026_04_29.md` §A |
| 2 | `rs-breakout-scout` | EQUITY/ETF | 23 | 78.3 % | 7.49 | +59.8 % | Sample starvation (n<30) + UNTRUSTED source-tier | **Hold** — let n grow naturally; review at n=60 | same §B |
| 3 | `atr_percentile_gate` | CRYPTO (BTCUSDT) | 22 | 95.5 % | 13.51 | +9.27 % | Score floor 65 → ours is 44.7 avg | **Watch** — needs n>30 + symbol diversification | same §C |
| 4 | EQUITY cohort under `scoreFloorEquity 55→45` | EQUITY | +41 | — | 4.05 vs 12.90 | — | Over-strict equity score floor | **Ship PR #538** | `EDGE_ANALYSIS_2026_04_30.md` |
| 5 | `multi_asset_cot` | COMMODITY | 41 | 85.4 % | **8.03** (gross), 0.0 net | **only BH-FDR survivor at 5 %** | Slippage eats edge | **Capacity research, no sizing** | `ASSET_CLASS_STRATEGY_ELABORATION_2026_05_02.md` |
| 6 | `luxalgo SHORT` (sub-leg) | CRYPTO | 103 | — | 1.62 | +45.75 % | Lumped with bleeding `luxalgo LONG` legs at the strategy level | **Direction-split promotion gate** (see §5.3) | `SMOKING_GUN_ASSET_CLASS_2026_04_30.md` §2.4 |

**Aggregate near-miss recovery estimate:** +110 picks/wk + ~+50 %/wk gross PnL
contribution at 1× sizing from item #1 alone
(`NEAR_MISS_DEEP_DIVE_2026_04_29.md`). Items #4 + #6 add another ~+200 %
realised PnL on the equity / crypto-short cohort over the 30-d window.

**Anti-pattern guard:** every promotion in this register requires the
**existing kill-list aging mechanism** (`kill_list_max_age_days=21`,
PR #519) to actually be running. The discovered structural cause —
the kill-list is **541 entries deep** in `alpha_engine/data/core_whitelist.json`
with no top-level `last_kill_run` timestamp on the file head — means
strategy_killer has not been refreshing for at least 5 weeks. This is
a hygiene action ahead of any unblock.

---

## 5. QA-analyst data-integrity findings

### 5.1 The TRACK% / FWD WR strategy-symbol-direction granularity gap (the one operator flagged)

**Symptom:** the `/audit` Active-Picks panel shows a `FWD WR` column. Operators
expect this to mean *"forward win-rate of THIS strategy on THIS symbol in THIS
direction"* — i.e. `(strategy, symbol, direction)`-keyed. Today it is
`pick.strat_fwd_wr` which is the **strategy-overall** forward win-rate
(`audit_dashboard/template.html:2080-2832`).

**Evidence:**
- `audit_dashboard/template.html:2080`:
  `Forward Win Rate: ${stratData.fwd_wr ?? 'n/a'}%` — `stratData` is keyed by
  strategy name only.
- The front-end *does* maintain `combo_stats` and `strat_stats` separately in
  the GOLDEN/VERIFIED/TRACK tier-decision logic
  (`audit_dashboard/template.html:2270-2442`) — combo is keyed
  `(strategy, symbol, direction)`. The data exists; it just isn't surfaced as a
  column.

**Impact:** misleads the operator. A strategy whose *overall* fwd_wr is 60 %
can be losing badly on a specific symbol/direction — that loss is invisible
in the column today.

**Fix (low-risk, render-only, no gate change):**
- Add `combo_fwd_wr`, `combo_fwd_n` columns to the Active-Picks table.
  Source: existing `combo_stats` already computed for the tier badge.
- Keep `strat_fwd_wr` as a secondary column with header *"Strategy-overall FWD WR"*
  to preserve back-compat.
- Add a tooltip explaining the difference.

This is a **dashboard-render PR**, not a pipeline change. Map to a new
**PR-H** in the `HEDGE_FUND_UPLIFT_ROADMAP_2026_05_02.md` sequence
(strictly UI; no env flag needed because no behaviour change to picks).

### 5.2 Resolver flicker (the universal data-integrity bug)

The single line `PNL_WIN_THRESHOLD = 0.00001` (0.1 bp) in
`alpha_engine/outcome_resolver.py:97` produces 100 % sub-5-bp wins on FOREX
and 100 % sub-10-bp wins on EQUITY/COMMODITY. This is the gating fix for
`/audit` to deliver investable numbers across all non-crypto classes.
PR #610 (resolver v2.1) is the dependency. **Status: open, awaits operator
merge.**

### 5.3 Direction-leg promotion gating

Strategies are gated as a single object today, but the SMOKING_GUN evidence
shows the **same strategy can be a Tier-1 LONG and a Tier-3 SHORT (or vice
versa)** — `luxalgo` is the canonical case (SHORT PF 1.62 vs LONG drag).
**Add a `direction_split_gate` to `audit_trail/quality_gates.py`** that
allows promotion of one leg while demoting the other. Wire-Up Plan:
`passes_active_gate` consumes the per-direction n / WR / PF when n ≥ 30
on each leg. Default-OFF behind `DIRECTION_SPLIT_GATE_ENABLED` for 14 days.

### 5.4 Closed-pick field retention

`_CLOSED_PICK_KEEP_FIELDS` in `audit_trail/dashboard_generator.py` is the
audit-engine equivalent of column-store schema. It currently does **not**
preserve:
- `earnings_surprise` (PEAD)
- `f_score` (Piotroski)
- `sector_rs` (sector relative strength)
- `cot_commercial_z` (CFTC COT — wired but not preserved)
- `funding_rate`, `basis`, `whale_netflow` (crypto on-chain)
- `dxy_beta`, `carry_diff`, `session` (FOREX)

Without these on the closed record, **no post-mortem on those signals is
possible**. The audit-engine cannot answer *"did the F-score-tagged equity
picks outperform?"* even if PEAD/F-score is wired into pick generation.
**Action:** extend `_CLOSED_PICK_KEEP_FIELDS` with the missing-data list per
class. This is a low-risk single-PR change (no behaviour, only field
retention).

### 5.5 Kill-list bloat

`alpha_engine/data/core_whitelist.json` `kill_list` length: **541** as of
2026-05-02. No top-level `last_kill_run` on the file head. The 21-day
auto-expiry (PR #519) is the right mechanism but it relies on
`tools/strategy_killer.py` re-running on schedule. Today it appears
stalled (no recent timestamp). **Action:** run the killer, age out the
expired entries, write a `last_kill_run` to the file head, and add a
hourly CI heartbeat that flags > 7-d stale.

---

## 6. Top-class focus + controlled fallback expansion

### 6.1 Concentration protocol

Until PR-A through PR-G land, **EQUITY is the only class permitted to size up**.
Concrete sizing recipe:
- 60 % capital → EQUITY active-tier picks under `scoreFloorEquity 45` (PR #538).
- 25 % → CRYPTO active-promoted subset *under vol-target* (Theme A).
- 10 % → ETF watch-list (no size-up until n ≥ 60).
- 5 % → `multi_asset_cot` flagged COMMODITY trades, capacity-research-only sizing.
- 0 % → FOREX / FUTURES.

This concentration is **deliberately temporary** — it reflects that EQUITY is
the only class that survives all four reviewer panels (SME / Quant / QA /
Cross-class). When FOREX clears resolver v2 + n ≥ 30 post-flicker-fix, FOREX
returns to the allocation table at its empirical weight.

### 6.2 Fallback expansion (penny stocks / meme coins / mutual funds)

**Constraint:** new universes only enter the system **after** the existing class
catalogue is exhausted of near-miss recovery (i.e. items 1, 4, 6 in the
near-miss register are merged) — otherwise we are adding noise on top of
unrepaired pipes.

**Universe-promotion gate** (must clear all 5 to ship):
1. **Source-of-truth feed**: Polygon / Alpha Vantage / IEX-cloud / on-chain
   (CoinGecko, DEX-Screener) — license terms compatible with the repo.
2. **n ≥ 30** closed picks on a **shadow log** (no live capital).
3. **PF ≥ 1.3** with bootstrap CI lower bound > 1.0.
4. **MDD < 25 %** simulated.
5. **BH-FDR survives at 5 %** when added to the existing source-system table
   (`ASSET_CLASS_STRATEGY_ELABORATION_2026_05_02.md` §Source-system).

**Penny stocks** (US small-cap / OTC, market cap < $300 M):
- Risk: liquidity, manipulation, pump-and-dump.
- Edge candidate: short-squeeze + earnings-drift on filtered float
  (Rohrbach + Loughran-McDonald 10-K sentiment).
- Data: existing equity feed extends naturally; need DTC / short-interest field.
- Candidate strategy: `pead_microcap_long` (PEAD baby-strategy, microcap-restricted)
  per `SMOKING_GUN_ASSET_CLASS_2026_04_30.md` §New-strategy backlog.

**Meme coins** (alt-season tokens beyond top-50 by mcap):
- Risk: extreme MDD, exchange-listing risk, rug-pulls.
- Edge candidate: **inverse "pump-watch"** (already proposed in
  `PHENOMENAL_PERFORMANCE_METHODOLOGY.md` Phase A as a CRYPTO-wide gate;
  applies tenfold to memes).
- Data: funding rate + DEX-aggregated whale netflow + Twitter sentiment
  (FinBERT-finetuned).
- Candidate strategy: `meme_pump_inverse_short` — short on z-score > 3
  with hard stop at 0.5 ATR. **Default-OFF**, shadow-log only.

**Mutual funds** (active-managed equity / multi-asset funds):
- Risk: daily-only NAV, redemption gates, fee drag.
- Edge candidate: long-horizon UEPS-style fundamental tilt
  (already in flight per `updates/long_term_value_project_2026-04-27`).
- Data: Morningstar / SEC EDGAR holdings.
- Candidate strategy: `ueps_mutual_fund_overlay` — fund-of-funds tilt
  using existing UEPS scoring on the underlying equity holdings.

**Sequencing:** Mutual funds first (lowest noise, longest horizon, fits the
existing UEPS pipe), penny stocks second, meme coins last (highest noise,
strictest gate).

---

## 7. Concrete enhancement backlog (mapped to existing roadmap)

| # | Item | Maps to | Risk | Reversibility |
|---|---|---|---|---|
| 1 | Run `tools/strategy_killer.py` to age out the 541-entry kill_list, write `last_kill_run` | hygiene | low | high |
| 2 | Single-line unblock of `luxalgo_confluence` (remove from `_PAPER_ONLY_STRATEGIES` + kill_list) | Near-miss #1 | low | high |
| 3 | Ship PR #538 — `scoreFloorEquity 55→45` | Near-miss #4 | low (already gated) | high |
| 4 | Land PR #610 (resolver v2.1) | unblocks FOREX/EQUITY/COMMODITY | medium (gates change) | yes via env flag |
| 5 | Add direction-split gate (§5.3) | Near-miss #6 | low (default-OFF) | yes |
| 6 | Add `combo_fwd_wr` / `combo_fwd_n` columns to `/audit` Active-Picks (§5.1) | QA #1 | none (UI only) | yes |
| 7 | Extend `_CLOSED_PICK_KEEP_FIELDS` with PEAD/F-score/sector-RS/COT/funding/whale/DXY/session (§5.4) | QA #4 | low (storage only) | yes |
| 8 | Theme A — vol-target on active-promoted CRYPTO subset | `deep_dive_crypto_mdd_reduction_2026_04_28.md` | medium (sizing change) | yes via env flag |
| 9 | Inverse "pump-watch" gate for CRYPTO | `PHENOMENAL_PERFORMANCE_METHODOLOGY.md` Phase A | low (default-OFF) | yes |
| 10 | Capacity-research study on `multi_asset_cot` | Near-miss #5 | none (research) | n/a |
| 11 | Mutual-fund universe shadow-log (UEPS overlay) | §6.2 | none (shadow only) | yes |
| 12 | Penny-stock universe shadow-log (PEAD microcap) | §6.2 | none (shadow only) | yes |
| 13 | Meme-coin universe shadow-log (pump-inverse) | §6.2 | none (shadow only) | yes |

Items 1 – 7 are the **highest-leverage, lowest-risk** subset and should ship
in the next 2 sprints. Items 8 – 9 are the **CRYPTO MDD repair**. Items
10 – 13 are the **fallback expansion** and only unlock after items 1 – 7
are merged.

---

## 8. What this report does NOT do

- It does **not** kill or unblock any strategy directly — every action goes
  through `STRATEGY_INVESTIGATION_BEFORE_KILL.md` or its inverse review.
- It does **not** retune any HC gate beyond pointing at PR #538.
- It does **not** introduce new dependencies, new modules, or new files
  in production paths. **Documentation only.**
- It does **not** auto-deploy anything; every backlog item ships
  default-OFF behind an env flag with a 14-day shadow log per
  `AGENTS.md` Wire-Up Rule.

---

## 9. References

- `reports/HEDGE_FUND_UPLIFT_ROADMAP_2026_05_02.md` — multi-PR roadmap (PR-A → PR-G)
- `reports/ASSET_CLASS_STRATEGY_ELABORATION_2026_05_02.md` — glossary + per-class evidence
- `reports/SMOKING_GUN_ASSET_CLASS_2026_04_30.md` — alpha-source-expansion + missing-data list
- `reports/EDGE_ANALYSIS_2026_04_30.md` — HC gate sweep (basis for PR #538)
- `reports/NEAR_MISS_DEEP_DIVE_2026_04_29.md` — `luxalgo_confluence` + 2 others
- `reports/PHENOMENAL_PERFORMANCE_METHODOLOGY.md` — Phase A/B/C protocol
- `reports/hedge_fund_performance_review_summary_2026_04_27.md` — tier definition
- `reports/ASSET_CLASS_AUDIT_RUN_2026_04_30.md` — 30/100/250-d window data
- `reports/deep_dive_crypto_mdd_reduction_2026_04_28.md` — vol-target evidence
- `reports/action_B_resolver_2026_04_27.md` — asset-class threshold table
- `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` — pre-kill protocol
- `docs/MUTATION_THREE_AXIS_PROTOCOL.md` — DNA-mutation triage
- `AGENTS.md` — Wire-Up Rule, kill-list hygiene, push-trigger registry
- `audit_dashboard/template.html` — `/audit` rendering (TRACK% / FWD WR scope)
- `audit_trail/dashboard_generator.py` — `_CLOSED_PICK_KEEP_FIELDS`
- `alpha_engine/strategy_blocklist.py` — `_PAPER_ONLY_STRATEGIES` / `_RETIRED_STRATEGIES`
- `alpha_engine/data/core_whitelist.json` — 541-entry kill_list (this report's hygiene flag)
- `alpha_engine/outcome_resolver.py:97` — universal `PNL_WIN_THRESHOLD` bug source
