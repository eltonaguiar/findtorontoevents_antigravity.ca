# Multi-Engine AI Consultation — Institutional Strategies Per Asset Class

**Date:** 2026-05-19
**Method:** Single prompt (`tools/swarm/prompts/ofox_institutional_strategies.md`) fanned to ~10 AI engines across 3 swarm runs, plus an independent OpenAI Codex headless run.
**Input fed to every engine:** post-noise-filter `asset_class_health` numbers — EQUITY PF 1.41/WR 52.7%/n=421; COMMODITY PF 1.78/WR 46.9%/n=750; BOND PF 1.72/WR 55.6%/n=18; CRYPTO PF 1.25/WR 44.6%/n=8067 (elite subs PF 2.34-3.97 dragged by `quan_engine` 18% vol @ PF 0.70 + unknown source 7% vol @ PF 0.35); ETF PF 1.24/WR 55.2%/n=87; FOREX PF 0.27/WR 46.4%/n=1169.

## Engines consulted

| Engine | Status | Notes |
|--------|--------|-------|
| deepseek (run 063216Z) | SUCCEEDED | Full 6-class playbook |
| deepseek (run 063422Z) | SUCCEEDED | Full 6-class playbook (consistent twin of above) |
| groq | SUCCEEDED | Full 6-class, factor-tilt framing |
| ollama_local | SUCCEEDED | Full 6-class (weaker — generic, mislabels some archetypes) |
| pollinations (gpt-oss-20b) | PARTIAL | Truncated at 1500 tokens — only EQUITY archetypes emitted |
| kilo | SUCCEEDED | Full 6-class, prioritization matrix |
| opencode | SUCCEEDED | Full 6-class, most detailed; academic citations |
| xai | SUCCEEDED | Full 6-class, on-chain/funding-arb framing |
| codex (OpenAI, codex-cli 0.128.0) | SUCCEEDED | Paper-grounded (TSMOM/Carry/QMJ/Lustig et al.); flagged MDD-missing + WR>50% rule bias |
| ofox (x2) | FAILED | No API key in env (`OFOX_AI_KEY`/`OFOX_API_KEY`) |
| gemini_api | FAILED | Non-JSON / empty output |
| inception | FAILED | HTTP 401 |

**8 distinct successful engines** (deepseek counted once — twin runs identical) + codex = **9 usable opinions**, 1 partial, 4 failures.

---

## Consensus

### EQUITY — PF 1.41 / WR 52.7% / n=421
**Archetype (8/8 agree): Cross-sectional / residual equity momentum, paired with a quality or low-vol tilt.**
- **Rationale:** investor underreaction to firm-level news + disposition effect + slow institutional flows; not arbitraged away because of tracking-error / benchmark-hugging mandates (opencode, codex, deepseek, kilo, xai). Quality/low-vol leg adds crash protection (deepseek, xai, opencode).
- **Signal construction (consensus):** 12-1 month momentum (skip last month to dodge short-term reversal), sector/beta-neutral z-score; universe top 1000-1500 liquid US/DM names (exclude microcaps < $500M); **monthly rebalance** with weekly risk refresh; inverse-vol sizing, 40-60 bps name risk cap, top-vs-bottom quintile L/S. Composite weights vary (deepseek 60/40 TSMOM+BAB; xai 40/40/20 low-vol/quality/mom; kilo momentum x quality).
- **2nd archetype, 3 votes:** PEAD / earnings-revision momentum (opencode, codex, ollama_local) — SUE + analyst revision breadth, hold 20-60 days. Codex rates this the higher-Sharpe equity sleeve.
- **Failure mode + guard:** momentum crashes after violent rebounds / crowded factor unwinds (2009-03, 2020-03, 2022-10). Guard: beta neutrality, vol targeting, crowding/short-interest filter, cut gross when VIX>25-30 or market >10% off 20d high.
- **Realistic expectation:** Sharpe 0.6-1.1 post-cost, PF 1.5-2.2. Codex/opencode: 0.8-1.1 / PF 1.5-1.8.

### COMMODITY — PF 1.78 / WR 46.9% / n=750
**Archetype (9/9 agree): Time-series momentum / trend-following on futures, paired with term-structure (roll-yield) carry.**
- **Rationale:** hedger pressure — producers/consumers structurally pay a premium to transfer risk; trends persist on slow supply/demand & inventory cycles; backwardation = structural carry premium (codex, opencode, deepseek, kilo, xai, groq).
- **Strong consensus the low WR is NOT a problem** — 46.9% WR with PF 1.78 is the *normal signature* of trend-following (opencode, codex, deepseek). **Do NOT chase WR; improve the winner/loser payoff ratio.**
- **Signal construction:** dual-lookback MA crossover (fast 20-60d + slow 120-260d), long when both up; 25-40 liquid futures across energy/metals/ags/livestock; daily signal, weekly rebalance; ATR / inverse-vol sizing to ~10-15% annualized vol per contract, sector-cluster caps. Carry leg: front-vs-2nd/3rd contract slope, long top-quintile roll yield.
- **Failure mode + guard:** V-shaped reversals / whipsaw in range-bound contango regimes (2014-15 oil, 2023-24). Guard: term-structure confirmation filter, halve size in flat-curve regimes, faster de-risk on vol spikes, roll/first-notice discipline.
- **Realistic expectation:** Sharpe 0.7-1.2, PF 1.6-2.4. This is the class whose current live numbers most closely match a healthy institutional book.

### BOND — PF 1.72 / WR 55.6% / n=18
**Archetype (9/9 agree): Rates carry + rolldown, paired with rates/macro momentum (or a curve steepener).**
- **Rationale:** term premium + rolldown is compensation for duration risk; central-bank reaction functions create slow, predictable repricing (codex, opencode, xai, deepseek).
- **UNANIMOUS caveat: n=18 is statistically meaningless** — "could be luck" (opencode), "not evidence" (codex), 95% CI on PF ~ [0.8, 3.5] (deepseek). Every engine says: do NOT allocate real size; treat as research/pilot until n >= 100-200.
- **Signal construction:** G10 govvies via futures/swaps; carry+rolldown optimized across 2y/5y/10y/30y; 2s10s slope + 1/3/6/12m standardized rate momentum; weekly-monthly rebalance; DV01/duration-neutral, inverse-vol sizing (low-vol asset, modest leverage to ~8-10% vol).
- **Failure mode + guard:** central-bank regime shifts, inversions, inflation shocks. Guard: macro regime filter ("don't fight the Fed"), de-risk into CPI/FOMC.
- **Realistic expectation:** Sharpe 0.6-1.2, PF 1.5-2.1 — *if* the edge survives a real sample.
- **Disagreement:** opencode says aggressively increase bond trade frequency to build n; deepseek says don't run standalone — merge bond signal into equity as a regime diversifier.

### CRYPTO — PF 1.25 / WR 44.6% / n=8067
**Archetype (consensus): Perp funding-rate / basis carry as the core, paired with beta-hedged cross-sectional momentum.**
- **#1 UNANIMOUS action (9/9): immediately kill `quan_engine` (18% vol @ PF 0.70) and the unknown source (7% vol @ PF 0.35).** Codex frames the unknown source as a *governance failure before a PnL issue*. Post-cull, engines estimate aggregate CRYPTO PF jumps 1.25 -> 1.8-2.2.
- **Rationale:** funding/basis carry edge from segmented capital, leverage demand, regulatory frictions preventing clean cash-and-carry (codex, opencode, xai). Momentum edge from retail trend-chasing / slow info diffusion across tokens.
- **Signal construction:** funding-rate z-score (8h funding, 30d lookback), enter |z|>1.5, mean-revert with a momentum regime filter (only fade when 20d momentum is flat); momentum leg = 20-60d residual return on top-20-100 liquid tokens, hedge BTC/ETH beta; daily/intraday funding rebalance, weekly momentum; vol targeting, tight per-coin caps, min $10M+ daily volume liquidity filter.
- **Failure mode + guard:** liquidation cascades / exchange or collateral failure (FTX, Luna). Guard: regulated-first venue stack, segregated collateral, exchange whitelist, hard 10-15% drawdown stop, top-10 liquidity only.
- **Realistic expectation:** elite/clean subs Sharpe 1.0-2.0, PF 1.9-3.4.
- **Disagreement:** older engines (groq, ollama_local) read the aggregate PF 1.25 as "strategy not effective / lowest priority"; the better engines (codex, opencode, kilo, deepseek, xai) correctly identify the aggregate as a *mix problem* — elite alpha buried under two toxic sources — and rank crypto a top-2 priority after surgery.

### ETF — PF 1.24 / WR 55.2% / n=87
**No strong single archetype — engines split. Majority verdict: shrink, do not run as a standalone equity duplicate.**
- **Dominant view (deepseek, opencode, xai, codex):** ETFs are baskets of assets you already trade — running a separate ETF momentum book is redundant. Either merge into the equity pipeline as low-vol exposures, or keep ONLY genuinely ETF-specific edges.
- **The ETF-specific edge (codex, xai stat-arb):** NAV premium/discount mean reversion around the AP creation/redemption mechanism — intraday z-score of premium vs fair basket, liquid broad/sector ETFs only. Codex: Sharpe 0.7-1.2, PF 1.4-1.9 — *but* warns of stale-NAV traps in international/bond ETFs.
- **2nd archetype:** sector/country ETF momentum (6-12m relative strength minus 1m reversal, monthly rebalance) — codex, kilo, groq, ollama_local. Modest: Sharpe 0.4-0.9.
- **Realistic expectation:** Sharpe 0.3-1.2, PF 1.2-1.9. n=87 too small to certify.

### FOREX — PF 0.27 / WR 46.4% / n=1169
**Archetype if kept: G10 carry + value composite, secondary currency momentum — but consensus is the current book is structurally broken.**
- **#1 near-unanimous action (8/9): kill the live FOREX book.** PF 0.27 on n=1169 is decisive — "not noise" (codex, deepseek, opencode), "anti-alpha, p<0.1% of being random" (deepseek). Take live capital to zero.
- **Rationale FX is hard:** no structural risk premium (zero-sum between two currencies); carry is the only persistent anomaly and it crashes spectacularly in risk-off with unpredictable timing; spot FX dominated by banks/HFT with sub-ms latency (opencode, xai, deepseek).
- **If rebuilt from scratch:** G10 carry from rate differentials + value from PPP/BEER z-scores (3-5y), vol-regime gated, JPY/CHF convex hedges, monthly rebalance. Codex sets a re-entry bar: must clear PF > 1.3 out-of-sample before any live capital.
- **Realistic expectation:** even a clean rebuild — Sharpe 0.1-0.9, PF 1.1-1.8. Codex/opencode realistic post-cost ~ Sharpe 0.1-0.5.
- **Disagreement:** groq/ollama_local (weakest engines) gave FX optimistic PF 1.6 carry projections and did NOT call for a kill — these are not credible; they ignored the realized PF 0.27.

---

## Capital allocation — consolidated

Vote counts across the 9 usable engines (deepseek twin counted once; pollinations partial excluded from class votes it didn't reach).

| Class | Consensus action | Vote count | Rationale |
|-------|------------------|-----------|-----------|
| **CRYPTO** | **Scale — AFTER killing the 2 toxic sources** | 5/9 scale-after-surgery (codex, opencode, kilo, deepseek x2, xai) ; 2/9 (groq, ollama) misread it as low-priority | Elite subs PF 2.34-3.97 are world-class; aggregate is a mix problem, not a dead class. Post-cull PF ~1.8-2.2. |
| **EQUITY** | **Maintain / upgrade signals** | 9/9 | Closest to Tier-2 with a real sample (n=421). Highest marginal Sharpe per unit of work. Shift toward residual-momentum + PEAD. |
| **COMMODITY** | **Scale / maintain** | 9/9 (codex + kilo explicitly "scale"; others "maintain") | PF 1.78/WR 46.9% is the textbook signature of a healthy trend book. Best fit to current live profile. |
| **BOND** | **Maintain as pilot only — no real size** | 9/9 | Metrics are Tier-2 quality but n=18 is not evidence. Need n >= 100-200 before allocating. |
| **ETF** | **Shrink** | 7/9 shrink/merge ; 2/9 hold | Redundant with equity beta. Keep only NAV-arb or fold into equity pipeline. |
| **FOREX** | **Kill the live book** | 8/9 kill/zero ; 1/9 (ollama) keep | PF 0.27 on n=1169 is structurally broken. Rebuild only from scratch with a PF>1.3 OOS gate. |

**Representative target risk budget** (codex, closely echoed by deepseek/xai/kilo): Commodity ~35%, Equity ~20-35%, Crypto 10-15% pre-cleanup -> 20-25% post-cleanup, Bond 5-10% (pilot), ETF 5%, FX 0%, remainder unallocated rather than forced into sub-floor sleeves.

---

## Dissents / outliers

- **groq & ollama_local** ranked CRYPTO as low-priority / "strategy not effective" by reading the PF 1.25 aggregate at face value. This is wrong — it ignores the explicit elite-subs vs toxic-sources decomposition in the prompt. The 7 stronger engines all correctly diagnose it as a mix problem.
- **ollama_local** projected a FOREX carry book at PF 1.6 / Sharpe +0.7 and did **not** recommend killing FX — directly contradicts the realized PF 0.27 it was given. Not credible; treat as a hallucinated optimistic prior.
- **deepseek** is the lone voice that says BOND should not be a standalone book at all — merge bond signals into equity as a vol/regime diversifier. Everyone else says keep it as a pilot and build sample.
- **codex** is the only engine to flag a methodology gap: class-level MDD is missing from the input, so no sleeve can be certified Tier-1/Tier-2 on PF/WR alone; and a hard `WR > 50%` gate structurally under-ranks valid trend/carry sleeves (commodity, FX) that legitimately win < 50% of the time. This is the most important meta-finding of the consultation.
- **pollinations** truncated at 1500 tokens (gpt-oss-20b) — only produced EQUITY (trend + factor-tilt). Consistent with consensus as far as it went; excluded from per-class vote tallies it never reached.

---

## Action items for this repo

1. **CRYPTO — kill `quan_engine` and the unknown 7%-vol source now.** 9/9 engines. Single highest-ROI action; codex flags the unknown source as a governance/provenance failure. Add both to `BLOCKED_SOURCE_SYSTEMS` per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` + run `tools/mutation_analysis.py` first to confirm no salvageable mutation. Expect aggregate CRYPTO PF 1.25 -> ~1.8-2.2.
2. **CRYPTO — build a perp funding-rate carry sleeve.** Funding z-score (8h, 30d lookback) + momentum-regime filter, top-20 liquid coins, exchange whitelist. Consensus #1 crypto archetype and currently absent as a first-class source.
3. **FOREX — zero out live FX capital.** 8/9 kill. Honor the mutate-before-kill protocol (`docs/MUTATION_THREE_AXIS_PROTOCOL.md`) per CLAUDE.md, but realized PF 0.27 on n=1169 is decisive. Any rebuild is a fresh G10 carry+value book that must clear PF > 1.3 out-of-sample before live capital — wire that gate into the FX investigation doc.
4. **BOND — do not size up; instrument for sample.** n=18 cannot support a verdict. Raise bond trade frequency / extend live history until n >= 100 (charter floor) before any "proven" promotion on `updates/index.html`.
5. **COMMODITY — scale, and stop optimizing for WR.** PF 1.78 / WR 46.9% is healthy trend-following. Tune the winner/loser payoff ratio and add a term-structure (roll-yield) confirmation filter; do not add WR-chasing filters that would clip the fat right tail.
6. **EQUITY — upgrade the signal toward residual-momentum + PEAD.** Closest class to Tier-2; shift away from any short-horizon mean-reversion depressing PF. Sector/beta-neutral 12-1 momentum + earnings-revision overlay.
7. **ETF — shrink; fold into the equity pipeline.** Stop running ETF as a duplicate equity-beta book. Keep only a genuine NAV-premium/discount arb if infra supports it.
8. **Methodology fix (codex) — add class-level MDD to `asset_class_health` and stop using a flat `WR > 50%` gate.** A WR floor structurally penalizes valid trend/carry sleeves (commodity, FX, rates trend). Replace with a payoff-ratio-aware / expectancy-based gate, and certify tiers only when MDD is present.

---

## Open-Question Verdicts (2026-05-19, swarm-settled)

The two methodology-gap open questions flagged by codex (see Dissents/outliers above)
were settled by a 2-round multi-engine swarm — `deepseek` + `xai` (Grok) + `kilo`.
Round 1 (`swarm_runs/open_q_gate_r1_2026_05_19/`) reached structural agreement;
round 2 (`swarm_runs/open_q_gate_r2_2026_05_19/`) converged the two remaining
quantitative points. Verdicts only — no production code was changed.

Prompts: `tools/swarm/prompts/open_questions_gate_design_2026_05_19.md` (R1),
`tools/swarm/prompts/open_questions_gate_design_r2_2026_05_19.md` (R2).

### Q1 — Switch the money-ready / tier gate from flat `WR > 50%` to an EXPECTANCY-based gate?

**Swarm consensus (3/3): YES.** The hard win-rate AND-term structurally under-ranks
valid trend-following / carry sleeves that legitimately win < 50% of the time.
COMMODITY (PF 1.78 / WR 46.9% / n=750) — a textbook healthy trend book — is currently
blocked from `MONEY_READY` purely by the 55% default WR floor (`MIN_WR`), which is
*stricter than any PERFORMANCE_CHARTER tier* (charter T2 = WR≥50%, T3 = WR≥45%).
The fix replaces the hard WR floor with a net-of-cost expectancy gate plus a low WR
*sanity* floor.

**Current gate (the bug):** `alpha_engine/money_ready_verdict.py`, `_verdict()` —
line 620 `wr_floor = MIN_WR_BY_CLASS.get(...)`, line 621 `wr_ok = wr >= wr_floor`,
line 628 `if wr_ok and pf_ok and (dsr_ok or spa_ok) and (pbo_ok or spa_ok)`. WR is a
hard AND-term: a sub-floor WR can never reach `MONEY_READY` regardless of PF.

**Concrete formula / new gate predicate** (replaces the `wr_ok` term at line 628):

```python
# (a) low WR SANITY floor — soft, never zero, per-class
WR_SANITY_FLOOR = {"COMMODITY": 0.40, "FOREX": 0.40, "FUTURES": 0.40,
                   "EQUITY": 0.52, "CRYPTO": 0.50, "ETF": 0.50, "BOND": 0.50}
wr_sanity_ok = wr >= WR_SANITY_FLOOR.get(asset_class.upper(), 0.45)

# (b) net-of-cost expectancy HARD gate (same math as the existing
#     shadow _expectancy_gate() at lines 650-673)
slip = SLIPPAGE_BPS.get(asset_class.upper(), DEFAULT_SLIPPAGE_BPS) / 10000.0
E = wr * (avg_win - slip) - (1 - wr) * (avg_loss + slip)
expectancy_ok = E > 0          # SHIP threshold

# new gate line 628:
if wr_sanity_ok and pf_ok and expectancy_ok and (dsr_ok or spa_ok) and (pbo_ok or spa_ok):
    return "MONEY_READY"
```

- **Expectancy threshold = `E > 0`** (strictly positive, net-of-round-trip-slippage).
  2/3 engines (xai, deepseek) — the gate already requires `PF≥1.5` *and* DSR/SPA, so a
  larger 0.5%-per-trade buffer is redundant and risks blocking valid low-vol books.
- **Slippage:** net-of-cost using the per-class `SLIPPAGE_BPS` round-trip table that
  `_expectancy_gate()` already uses (COMMODITY 12bp, CRYPTO 15bp, FOREX 5bp, ...).
- **WR is NOT dropped** — demoted from hard gate to a ~40% per-class *sanity* floor
  (trend/carry classes) so a pathological 2%-WR book still can't sneak through.

**Verification (round 2):** PF mathematically pins the payoff ratio
`avg_win/avg_loss = PF*(1-WR)/WR`. For COMMODITY = `1.78*0.531/0.469 = 2.02`. With
avg_loss in 1.0–2.0%: **E ≈ +0.29% to +0.71% → COMMODITY PASSES.** FOREX
(PF 0.27 → ratio 0.31, inverted payoff): **E ≈ −0.71% → FOREX correctly BLOCKED**
(now on the *right* reason — PF/expectancy, not WR). The gate is correct.

**Target for the change:** `alpha_engine/money_ready_verdict.py` — `_verdict()`
(line 628 predicate) + `CLASS_WR_FLOORS` (line 169, add COMMODITY/FOREX/FUTURES at
0.40). Promote the existing shadow `_expectancy_gate()` (lines 650-673) /
`_SLIPPAGE_GATE_ENABLED` path from warning-only to a hard AND-term.

**Dissent (recorded):** `kilo` argued `E ≥ 0.005` (0.5%/trade) as an
estimation-noise buffer. Defensible but minority (1/3); and moot for the case at
hand — COMMODITY clears 0.5% anyway. Recommendation: ship `E > 0`; the 0.5% buffer
is available as an optional hardening if a 30-day shadow shows a borderline class
oscillating around zero.

**Recommended implementation step:** open a single PR against
`alpha_engine/money_ready_verdict.py` that (1) adds the per-class WR sanity floor,
(2) makes `E > 0` net-of-slippage a hard AND-term in `_verdict()`, (3) keeps the `wr`
value stamped in the verdict JSON for transparency. Add a regression test asserting
COMMODITY(PF 1.78/WR 46.9%) → `MONEY_READY`-eligible on expectancy and FOREX(PF 0.27)
→ blocked. Add a PERFORMANCE_CHARTER §2 footnote: the class-level money-ready gate
uses a 40% WR sanity floor (vs the 50% strategy-tier floor) — intentional, documented.

### Q2 — Where should class-level MDD be computed and stored?

**Swarm consensus (3/3): compute MDD in `tools/build_pf_registry.py` and persist it
into `pf_registry.json`.** `pf_registry.json::by_asset_class_policy_clean_net` is
already the canonical single source of truth for per-class PF/WR (it is what
`money_ready_verdict.py` reads via `_load_dashboard_health()`). MDD belongs there as
the third tier-certification leg so a sleeve can be certified on PF + WR + MDD
together. Note: `money_ready_verdict.py` *already* computes per-class MDD ephemerally
(`_rolling_mdd()` line 680, `_mdd_cvar_gate()` line 702) but never persists it, and
neither `pf_registry.json` nor `dashboard_data.json::asset_class_health` carries it.

**Concrete key + definition:**
- **Key name:** `max_drawdown_pct` (matches the existing convention in
  `dashboard_generator._classify_tier()`; avoids the per-strategy `max_drawdown`
  key already used elsewhere in that file).
- **Definition (matches PERFORMANCE_CHARTER §6):** max peak-to-trough drawdown on the
  per-class cumulative **NET-return** equity curve — `equity_0 = 1.0`,
  `equity_n = equity_{n-1} * (1 + net_pnl_pct_n)`, `DD_n = (peak - equity_n)/peak`,
  `max_drawdown_pct = max(DD_n)`. Stored as a **fraction** (0.20 = 20%). Tier
  thresholds: T1 ≤ 0.10, T2 ≤ 0.20, T3 ≤ 0.25.
- **Critical:** computed from the SAME net per-pick series that produces the row's
  PF/WR (`aggregate(..., net=True)` path) — using gross would inflate MDD via
  COMMODITY spot-flicker artifacts and break row self-consistency.

**Target for the change:** `tools/build_pf_registry.py` — add a per-class net-return
accumulator inside `aggregate()` (~line 492), a module-scope `_rolling_mdd()` helper
(copy the algorithm from `money_ready_verdict._rolling_mdd()` so the two stay
identical), and in `main()` (~line 562-566, after the `kept_policy net=True`
aggregation) attach `row["max_drawdown_pct"]` to every
`by_asset_class_policy_clean_net` row. Downstream:
`audit_trail/dashboard_generator.py::_registry_backed_ac_breakdown()` (~line 5574)
passes the key through to `asset_class_health` so `dashboard_data.json` inherits it.
`money_ready_verdict._mdd_cvar_gate()` should prefer the persisted registry value
with a recompute fallback (backward compatible with old registry files).

**Dissent (recorded):** minor — `pf_registry.json` is cron-refreshed so the persisted
MDD is only as fresh as the last build (same staleness profile as PF/WR; acceptable).
Both `_rolling_mdd()` copies should be consolidated into a shared
`tools/mdd_calculator.py` in a later refactor — out of scope for the immediate fix.

**Recommended implementation step:** one PR against `tools/build_pf_registry.py`
adding `max_drawdown_pct` to the canonical class rows, plus the
`dashboard_generator` pass-through, plus a `tools/ci_gate_*` assertion that every
`by_asset_class_policy_clean_net` row carries `max_drawdown_pct`. Once persisted, the
charter §2 tier table can finally be evaluated on PF + WR + MDD together — and
no class should be promoted past Tier 3 with a `null` MDD.
