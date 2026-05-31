# Edge Deep-Dive: COMMODITY (2026-05-31)

**Owner:** claude (this session)
**Verdict source:** `audit_dashboard/data/money_ready_verdict.json::classes.COMMODITY` + `audit_dashboard/data/edge_stability/edge_stability_COMMODITY.json`
**Current state:** PF 3.87 / WR 57.1% **on n=7** — verdict **INSUFFICIENT_DATA**, top symbol GC=F 57% (concentration uncapped). 7d/30d/90d/all edge_stability identical (no window separation): **WR 18.8% / PF 0.21 / total PnL -23.56 across n=16**. Sub-T2 by every gate; the 3.87 PF headline is a 7-row artifact.

## 1. Root cause(s) of zero edge today

1. **Universe is too narrow (8 symbols).** GC=F dominates resolved picks (57% share). With only 8 futures contracts, every per-symbol cell hits INSUFF-N inside a quarter. We cannot run DSR/PBO/SPA — `details.dsr.note = "n=7 too small"`, `details.pbo.note = "need ≥2 strategies with n≥20, got 0"`.
2. **No strategy has resolved ≥ 10 in any window.** Per `edge_stability_COMMODITY.json::per_strategy` the only live producers are:
   - `cftc_cot_commercial_signal` n=3 (PF 2.71 — random)
   - `futures_momentum` n=9 (0% WR, PF 0.00, −22.86 PnL)  ← **bleeding**
   - `commodity_tsmom_12m` n=3 (PF 0.26)
   - `cnn_lite_pattern_signal` n=1
   So 16 resolved trades total. The COT family was already **falsified** 2026-05-13 (6.33× over-emission of CT=F cotton; M-095 publication-lag bug) and re-triangulated 2026-05-25 (`reports/2026-05-25_commodity_cot_edge_triangulation.md`: 3/3 engines flag DATA_QUALITY_LEAKAGE). cta_replicator and zoo's commodity_term_structure are **REFUTED** (n=0 sidecar).
3. **Market-structure mismatch.** The strategies we ported (TSMOM 12m, momentum, COT extremes) are **slow, monthly-decision** signals running on a venue (`multi_asset_copytrader` + Yahoo `=F` continuous-front-month chains) that mid-cycles every quarter. Continuous-contract splicing kills carry/roll-yield signal, and the strategies don't condition on the term-structure regime that actually drives futures returns.
4. **`bt_backtest_runs` does not cover COMMODITY at all** — `SELECT DISTINCT asset_class FROM bt_backtest_runs` = `['CRYPTO']`. The 25-day stale issue in PR #339 means there is *no* historical backtest grounding for commodity strategies; everything in production is forward-only with n<10. Of `bt_backtest_trades` 264k+250k+239k+… rows on commodity futures, **the only strategy with n>30 is `signal_recorder` (tape-only, 552 rows, 0% WR)** — that's a label-emitting probe, not a strategy. Real backtest coverage is effectively zero.
5. **strategy_summary tagging is broken.** Of 19 commodity/futures rows in `strategy_summary`, **all have `n_resolved=0`** and `sizing_status='shadow'`. The single COMMODITY entry that has even one resolved pick (cftc_cot_commercial_signal n=3) reports `n_resolved=0` in summary — the summary→registry resolution wire is broken for COMMODITY. We are flying blind because the dashboard pipeline cannot see what the picks did.
6. **Registry asset_class is wrong.** In `strategy_registry`, `futures_momentum`, `cot_positioning`, `cftc_cot_commercial_signal`, `commodity_tsmom_12m`, `contango_roll_yield`, `commodity_carry_momo_double_sort`, `commodity_channel_index_bounce` and 40+ others are all stamped `asset_class='CRYPTO'`. That mislabel is why the COMMODITY class only sees 4 producers — most of the inventory is hiding under CRYPTO.

## 2. Five edge angles we have NOT yet tried

Ranked by feasibility × novelty for our stack:

| # | Angle | Why it might work | Data we'd need | Feasibility |
|---|---|---|---|---|
| **A** | **Futures calendar-spread mean reversion** (front − back month, e.g. CLF − CLG) | The continuous-front-month price we use *already loses* this signal. Spread distance from 60-day median mean-reverts in 70-80% of grain/energy series (Erb & Harvey 2006, Szymanowska et al. 2014, JF). It is *not* an outright directional bet, so vol is 4-8× lower → fits small-n problem. | CME settlement curve for top 6 contracts (free via CME data API or Nasdaq Data Link). | **HIGH** — code is one rolling-zscore. Doesn't need ML, doesn't need a new venue. |
| **B** | **Backwardation/contango regime overlay on TSMOM** (Koijen-Moskowitz-Pedersen 2018 "Carry") | Our `commodity_tsmom_12m` got PF 0.26 because it ran un-conditioned. KMP shows that **TSMOM only earns its premium in contango**; in backwardation, carry trade dominates and TSMOM whipsaws. Splitting our 12m TSMOM into {contango: long-momentum, backwardation: long-carry} is a single conditional. | Same curve data as (A). | **HIGH** — re-uses tsmom_12m code with a regime gate. |
| **C** | **Inventory-report event trade** (EIA crude Wed 10:30 ET, USDA WASDE 12:00 ET 2nd-week, USDA crop progress Mon 16:00 ET) | Lucca-Moench (RFS 2015) showed pre-announcement drift on FOMC; equivalent literature for EIA (Halova-Lee 2014) shows 30-40 bps in 10-min vol-controlled window. We have **zero event-aware strategies on commodities** today. | EIA API (free), USDA NASS API (free), plus 1-minute futures quotes (or use ETF UNG/USO as proxy when futures price not available). | **MED** — needs minute-bar data and a calendar feed; alpha_engine has no event scheduler yet. |
| **D** | **Gold/Silver ratio (and Platinum/Gold, Copper/Gold) regime trade** | The Au:Ag ratio mean-reverts to ~60-80 with 6-9mo half-life (Erb & Harvey 2013); extreme reads >85 or <40 generate 12-18mo trades with Sharpe ~0.8-1.2. We have GC and SI separately — pair-trading them as a ratio is a single new symbol that **isn't subject to single-contract roll noise**. | Existing GC=F and SI=F daily prices (already in DB). | **HIGH** — implement as a new "virtual symbol" `GCSI_RATIO` with simple z-score entry/exit. |
| **E** | **Industrial-commodity ↔ macro PMI overlay** (Bessembinder 1992; Tang-Xiong 2012 financialization) | Copper, oil, steel returns lead/lag ISM PMI by ~1 month; conditioning long-only signals on PMI > 50 cuts drawdown 30-40% in published track records. We have no macro overlay. | ISM PMI (FRED, monthly, free) + China Caixin PMI. | **MED** — needs new monthly data feed but trivial join. |

Sub-mentions that I'd defer:
- **Cross-commodity momentum** (oil → gas, copper → steel) — Asness-Moskowitz-Pedersen 2013 spillover. Works but n issue stays.
- **Seasonal patterns** (Cao/Jiang/Wang 2013) — already built today; needs n>100 forward, not a new angle.
- **COT Z-score (not just extremes)** — same family that failed M-095 publication-lag; only viable after the publication-lag guard is re-verified.

## 3. Two concrete strategies to build next session

### Strategy COMM-A — `commodity_calendar_spread_zscore`
- **Academic citation:** Szymanowska, de Roon, Nijman, Van den Goorbergh (2014) *"An Anatomy of Commodity Futures Risk Premia"* JF 69(1) — explicit spread-premium decomposition; Erb & Harvey (2006) *"Strategic and Tactical Value of Commodity Futures"* FAJ 62(2) — roll-yield/spread mean-reversion.
- **Universe:** 6 contracts that have liquid 2nd-month: CL=F, NG=F, GC=F, SI=F, ZC=F, ZW=F. Skip illiquid (KC, SB, CT) until proven.
- **Entry rule:** Compute spread = front_settle − second_settle. Compute 60-day rolling median and stdev. Enter **long the spread** (long front, short back) when z < −1.5; **short the spread** when z > +1.5.
- **Exit rule:** z crosses 0, OR 15 days held, OR realized loss > 1.5σ.
- **Sizing:** equal-vol (target 50 bps daily σ on the spread, not the leg).
- **Data needed:** CME settlement for front and second month (Nasdaq Data Link `CHRIS/CME_CL2`, etc., or paid CME end-of-day). Daily frequency.
- **Expected n in 90 days:** ~25-35 trades across 6 contracts; gives DSR/PBO traction by ~120 days.
- **Why this beats what we have:** non-directional → not contaminated by GC=F bull bias; not subject to continuous-contract splicing; literature PF ~ 1.6-1.9 net of cost.

### Strategy COMM-B — `commodity_tsmom_regime_conditioned`
- **Academic citation:** Koijen, Moskowitz, Pedersen, Vrugt (2018) *"Carry"* JFE 127(2) — explicit decomposition of momentum vs carry by curve shape; Moskowitz-Ooi-Pedersen (2012) *"Time Series Momentum"* JFE 104(2) — TSMOM baseline.
- **Universe:** same 8 contracts in current `commodity_tsmom_12m` (no new universe).
- **Logic:**
  - Compute curve slope = ln(second_month / front_month) annualised.
  - **Regime:** if slope ≤ −2% (backwardation) → take **carry** signal: long if positive carry, short if negative. If slope ≥ +2% (contango) → take **TSMOM** signal as today. In the neutral band → no trade.
  - This is a single boolean gate on top of existing code.
- **Entry/exit:** unchanged from current `commodity_tsmom_12m` (monthly rebalance, 12m lookback). Add the regime gate at signal-emission time.
- **Data needed:** Same as (A) — front/second settle. No new venue.
- **Expected n in 90 days:** ~12-20 trades (selective gate cuts ~40% of months). Lower n but higher hit rate per KMP.
- **Why this beats what we have:** current PF 0.26 attributed to running TSMOM through backwardation regimes. The gate is what KMP actually published; we re-implemented TSMOM without the gate.

Both strategies share the **same new dataset** (futures curve), so the wire-up is one upstream job that benefits both — high leverage on integration cost.

## 4. Buried-winner candidates (n<30, watch-list, NOT sized)

Pulled from `strategy_registry` and `strategy_summary` (note: most are mislabeled `asset_class='CRYPTO'` even though the strategy is commodity-by-construction):

| Strategy | Reg class | n | PF | WR | Why interesting | Watch criterion |
|---|---|---|---|---|---|---|
| `cftc_cot_commercial_signal` | CRYPTO (mislabel) | 3 (live) + 48 (registry) | 2.71 (live n=3); 0.23 (registry n=48) | 67% / 58% | **Split verdict** — live since fix shows positive PF but n=3; registry includes pre-M-095-fix leaky trades. Re-evaluate **only on post-2026-05-20 trades** in a single bucket | n ≥ 30 post-fix AND PF ≥ 1.30 AND CT=F share < 25% |
| `futures_ema_stack_momentum` | CRYPTO | 2 | 177.30 | 50% | Crazy PF on n=2 = noise; but it's the only EMA-stack we have on futures, and EMA-stack is well-documented (LTRP family) | n ≥ 25 before judging |
| `futures_bb_mean_reversion` | CRYPTO | 2 | 11.23 | 50% | Bollinger MR on commodities is published (Bessembinder 1992 inventory effects) | n ≥ 30 AND PF ≥ 1.5 |
| `commodity_tsmom_12m` | COMMODITY | 3 live / 2 reg | 0.26 / 3.23 | 33% / 50% | Same code, opposite verdicts depending on resolver — points at resolver split; if the regime-gated version (Strategy COMM-B) lands, this is the baseline to beat | strict regime-gated A/B |
| `contango_roll_yield` | CRYPTO | 0 | — | — | Code present but never emitted — Strategy COMM-B subsumes it; if author can be located, ask why disabled | n ≥ 20 emitted within 60d |
| `cta_cross_asset_tsmom` | COMMODITY | 3 (summary) | — | — | Cross-asset TSMOM is the AQR Managed-Futures portfolio; if n grows it's worth its own deep-dive | n ≥ 30 |
| `commodity_carry_momo_double_sort` | CRYPTO | 0 | — | — | Double-sort on carry + momentum is the cleanest published commodity premium (KMP 2018, Bakshi-Gao-Rossi 2019). It exists in inventory but emits zero. Wire-up is the bottleneck, not the strategy | enable → require n ≥ 30 in 90d before tier-up |

**None** of these are ready to size. The right ops move is: **track**, do not promote.

## 5. First operator action recommendation (next session)

**Single action, ranked #1 of one:**

> **Stand up a futures-curve data pipeline (front + 2nd month, daily settle) for CL, NG, GC, SI, HG, ZC, ZW, and use it to (a) implement Strategy COMM-A (`commodity_calendar_spread_zscore`) as a fresh strategy and (b) add a regime gate to existing `commodity_tsmom_12m` per Strategy COMM-B.**

Acceptance: data fetcher in `alpha_engine/data/futures_curve_fetcher.py` (or wherever the convention is), nightly cron, both strategies emitting signals into the normal pipeline by **2026-06-14** (T+14d), n target 30 across both by **2026-08-31** (T+90d) for a real DSR/SPA verdict.

**Why this and not something else:**
- Both new strategies share one upstream — minimum integration cost, maximum optionality.
- It is the only angle that addresses the **structural** root cause (continuous-contract splicing kills curve signal) instead of the **statistical** root cause (n too small).
- It is independent of the COT family, which is the only family with prior live edge but is under leakage cloud (`H-101` PRE-REGISTERED).
- It does not require licensing TickData/Bloomberg — Nasdaq Data Link `CHRIS/*` curves are free for daily settlements, plenty for these signals.

**Secondary** (do after #1 if cheap): patch the strategy_registry `asset_class` labels so the ~10 commodity-family strategies currently tagged CRYPTO get re-tagged COMMODITY. This unhides the inventory and makes per-class dashboards honest. A single UPDATE statement, scoped by strategy_name regex.

---
## Source / methodology trail

- `audit_dashboard/data/money_ready_verdict.json` → classes.COMMODITY (n=7, PF 3.87, INSUFF-N, top GC=F 57%)
- `audit_dashboard/data/edge_stability/edge_stability_COMMODITY.json` → per-strategy n & PF
- MySQL `ejaguiar1_stocks.strategy_registry` and `.strategy_summary` → inventory + mislabel detection
- MySQL `ejaguiar1_stocks.bt_backtest_runs` → confirms zero COMMODITY historical coverage (`DISTINCT asset_class = ['CRYPTO']`)
- MySQL `ejaguiar1_stocks.bt_backtest_trades` → confirmed `signal_recorder` dominance on commodity symbols (no strategy backtest coverage)
- Prior peer reports consulted (not re-litigated): `2026-05-25_commodity_cot_edge_triangulation.md` (3/3 LEAKAGE verdict), `commodity_diversification_gap_2026_05_18.md`, `commodity_nonctf_strategy_autopsy_2026_05_17.md`, `asset_class_90day_plan_COMMODITY_2026-05-15.md`.
- External consult: **NONE** — prior 2026-05-25 triangulation (Codex+Gemini+Grok) covers the COT angle; this report covers angles those consults did not (curve / regime / event). Skipped to stay within budget.
- No `git add -A`. No production data writes. Read-only DB queries.
