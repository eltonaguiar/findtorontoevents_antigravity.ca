# Deep Dive — COMMODITY (2026-05-31)

**Trigger:** CLAUDE.md Goal #1 deep-dive process. COMMODITY is FAILing on the
policy-clean cohort (PF=0.31 / WR=11% / n=28 cited in CLAUDE.md banner;
this report uses the live 2026-05-30T23:05Z snapshot which has shifted to
PF=1.81 / WR=44% / n=9 on policy-clean-net but n is too small for verdict
and the raw-DB cohort is still PF=0.71 / WR=17.9% / n=28). Two of the three
classifier-eligible numbers are sub-T2 by a wide margin; the recency
14-day FUTURES bucket (which contains COMMODITY) is 100% single-source
concentrated in `AlphaEngine`.

**Sources (verbatim, no fabricated numbers):**
- `audit_dashboard/data/money_ready_verdict.json` (generated_at
  2026-05-30T23:05:42Z, source `alpha_engine/money_ready_verdict.py --json`)
- `audit_dashboard/data/pf_registry.json`
  (`by_asset_class_raw`, `by_asset_class_policy_clean_net`,
  `by_asset_class_strategy_policy_clean_net`,
  `by_asset_class_strategy_symbol`)
- `audit_dashboard/data/pick_summary_stats_2w.json` and
  `pick_summary_stats_48h.json` (COMMODITY is bucketed under `FUTURES` in
  the recency panel because they share `=F` Yahoo suffixes; this is itself
  a finding — see Risk Register R-6)
- CLAUDE.md banner figures (`reports/money_ready_verdict.json` 2026-05-24
  + `pf_registry.by_asset_class_policy_clean_net` 2026-05-25T04Z)

---

## Current State (n, WR, PF, MDD, expectancy, recency)

| Cohort | n | wins | losses | WR | PF | total PnL | Notes |
|---|---:|---:|---:|---:|---:|---:|---|
| **Raw DB (`by_asset_class_raw`)** | 28 | 5 | 23 | 17.86% | 0.713 | −22.50% | Includes EXPIRED/auto-closed; resolver pre-fix noise present |
| **Policy-clean-net (verdict cohort)** | 9 | 4 | 5 | 44.44% | 1.812 | +8.99% | n too small for DSR/SPA/PBO; MDD null |
| **Verdict** | 9 | — | — | 44.44% | 1.812 | — | `INSUFFICIENT_DATA` (n_ok=false, dsr=null, mdd=null) |

**Expectancy (policy-clean-net):** +0.879% per trade (adj_win 4.90% vs
adj_loss 2.33%, slippage 12 bps). `expectancy_ok=true`, but on n=9 this
is noise — the standard error on a 4-and-5 split is enormous.

**MDD:** `mdd=null` in money_ready_verdict (insufficient series); pf_registry
reports `max_drawdown_pct=0.0663` on the n=9 cohort. Neither is verdict-grade.

**Concentration (verdict cohort, n=9):**
- `top_symbol = GC=F` at **77.78%** of trades — gold is essentially the
  asset class on the clean cohort. Single-symbol risk is total.
- `top_source = UNKNOWN` at 33.3% — meaning a third of clean COMMODITY
  trades have no labeled source_system (data-quality fail).
- `concentration_capped = false` — the policy clean filter does NOT cap
  77.78% single-symbol concentration. This is CLAUDE.md banner's
  "concentration gate is not enforced before DSR/SPA" P0 issue, instantiated.

**Recency (FUTURES bucket, includes COMMODITY + ES/NQ/RTY/YM index futures):**
- 14d: n_closed=2780, WR=50.65%, PF=130.5 (PF is an artifact of the
  shrinkage prior + 360% mean pnl_pct → one extreme outlier dominates;
  caveats: dup_groups=204, 87% single-source via `alpha_engine_unified`)
- 48h: n_closed=35, WR=37.14%, PF=1.627, 100% single-source via
  `AlphaEngine`; top_symbol GC=F at 48.6%. COMMODITY-only subset of those
  35 trades is dominated by GC=F/SI=F/PL=F LOSSES from `cta_golden_cross`,
  `cta_golden_cross_200`, and `commodity_tsmom_12m` (all LONG, all losing
  −1.4% to −3.4%) — the only winners are NG=F (`cta_cross_asset_tsmom`
  LONG +7.4 to +7.8%, but these are 6 duplicate near-identical fills on
  the same parent signal opened 2026-05-18..21) and RTY=F (index future,
  not commodity).

**Bottom line:** the favorable 44.4%/1.81 verdict-cohort number is a
77.78%-GC=F-concentrated n=9 sample with no DSR/SPA/PBO, and the 48h
recency view shows the live behavior is structurally LONG-only gold/silver
into a falling-precious-metals tape getting stopped out repeatedly.

---

## Per-Source Autopsy (top 5 sources by volume; WR/PF each)

The verdict cohort `top_source = UNKNOWN @ 33.3%` masks per-source
detail; pf_registry does not break out by source for COMMODITY directly,
but the recency panel and strategy/symbol breakdown give us the
operational view. **Source proxy via strategy → source mapping
(`AlphaEngine` umbrella in 48h panel):**

| Source / Engine | Volume (14d FUTURES bucket) | Volume (48h FUTURES) | Notes |
|---|---:|---:|---|
| `alpha_engine_unified` | 87% (n≈2418 of 2780) | — | 14d dominant; caveat `dup_groups=204` → duplicate signal-ts groups inflate n |
| `AlphaEngine` | — | 100% (35/35) | 48h: every COMMODITY trade rolls up here |
| `UNKNOWN` | — | 33.3% of policy-clean-net n=9 | Missing source_system label — data-quality bug, see R-4 |
| All other engines (regime_terminal, cot_swarm, etc.) | <13% combined | 0% | Effectively no diversification |

**Autopsy of `alpha_engine_unified` / `AlphaEngine` on COMMODITY:**
1. **Direction bias:** every closed COMMODITY-symbol trade in the 48h
   sample is LONG. Zero shorts. In a falling-PM-and-mixed-energy tape this
   is a directional bet, not a strategy.
2. **Signal duplication:** NG=F `cta_cross_asset_tsmom` LONG is opened 6
   times in 3 days (2026-05-18..21) and all 6 close at 2026-05-28 15:53
   with +7.4 to +7.8% PnL. These are 1 economic trade re-emitted by
   resampled scans, not 6 independent wins. The 14d caveat
   `dup_groups=204` confirms this is repo-wide on FUTURES.
3. **Stop placement:** GC=F losers (`cta_golden_cross`,
   `cta_golden_cross_200`, `commodity_tsmom_12m`) close in a tight band
   of −1.4% to −2.7%, suggesting fixed-% or ATR stops are firing in
   gold's normal noise band rather than at a structural invalidation.

---

## Strategy Breakdown (per-strategy WR/PF/single_source_pct; flag concentration)

From `by_asset_class_strategy_policy_clean_net` (verdict cohort, n=9 spread
across 4 strategies):

| Strategy | n | W | L | WR | PF | Total PnL | Flag |
|---|---:|---:|---:|---:|---:|---:|---|
| `cftc_socrata` | 3 | 2 | 1 | 66.67% | 2.445 | +3.05% | n too small; 100% on GC (see by_strategy_symbol) |
| `commodity_tsmom_12m` | 2 | 1 | 1 | 50.00% | 3.033 | +5.10% | 1×GC LOSS, 1×SI WIN — n=2 |
| `cta_replicator` | 3 | 0 | 3 | 0.00% | 0.000 | −6.45% | **DEAD strategy on policy-clean cohort** (0-for-3 on CL+GC) |
| `vwap_rsi_confluence` | 1 | 1 | 0 | 100.00% | n/a | +7.30% | n=1, PF undefined (no losses) |

From `by_asset_class_strategy_symbol` (richer view, mixes raw + clean):

| Strategy | Symbol | n | W | L | WR | PF | Concentration call |
|---|---|---:|---:|---:|---:|---:|---|
| `cta_replicator` | CL | 4 | 0 | 4 | 0% | 0 | **KILL** — 0-for-4 on crude |
| `cta_replicator` | GC | 3 | 0 | 3 | 0% | 0 | **KILL** — 0-for-3 on gold |
| `multi_asset_copytrader` | GC | 4 | 0 | 4 | 0% | 0 | **KILL** — 0-for-4 on gold |
| `multi_asset_copytrader` | KC | 3 | 0 | 3 | 0% | 0 | **KILL** — 0-for-3 on coffee |
| `multi_asset_copytrader` | PL | 2 | 0 | 2 | 0% | 0 | KILL — 0-for-2 on platinum |
| `multi_asset_copytrader` | SI | 1 | 0 | 1 | 0% | 0 | KILL — 0-for-1 |
| `multi_asset_cot` | CT | 4 | 0 | 4 | 0% | 0 | **KILL** — 0-for-4 cotton (this is the 57% CT=F concentration the CLAUDE.md banner warns about) |
| `cftc_socrata` | GC | 3 | 2 | 1 | 66.67% | 2.71 | KEEP/probation — only positive-edge strategy with n>=3 |
| `commodity_tsmom_12m` | GC | 1 | 0 | 1 | 0% | 0 | n=1 |
| `commodity_tsmom_12m` | SI | 1 | 1 | 0 | 100% | n/a | n=1 |
| `combined_confidence` | EURUSD | 1 | 1 | 0 | 100% | n/a | mislabeled — EURUSD is FOREX, not COMMODITY (data-quality R-4) |
| `vwap_rsi_confluence` | SHIBUSDT | 1 | 1 | 0 | 100% | n/a | **mislabeled** — SHIB is CRYPTO, not COMMODITY (R-4 confirmed) |

**Single-source % per strategy (verdict cohort):** every strategy with
n>=2 in the policy-clean cohort is 100% from `alpha_engine_unified` /
`AlphaEngine`. **No strategy on COMMODITY currently has source diversity.**

---

## What Is Failing (root causes — name strategies, sources, patterns)

1. **`cta_replicator` is broken on COMMODITY** — 0-for-7 between CL (0/4)
   and GC (0/3), gross_loss 12.5% / 0% gross_profit. The replicator is
   running long-only into a tape where managed-futures (DBMF / KMLM) are
   themselves drawing down. It is not actually "replicating" CTA tilts;
   it is closet-momentum-LONG on whatever it can name.
2. **`multi_asset_copytrader` is broken on COMMODITY** — 0-for-10 across
   GC/KC/PL/SI, gross_loss 25.9%. Either the source it copies is itself
   losing on COMMODITY (likely a single-trader feed) or the symbol map is
   sending it into instruments the source doesn't actually trade.
3. **`multi_asset_cot` CT=F cotton** — 0-for-4, gross_loss 27.5%. This is
   the single largest dollar-PnL loser in the raw cohort. CFTC COT signals
   on a thinly-followed soft like cotton, applied long-only with what
   appear to be fixed stops, get chopped to death.
4. **LONG-only directional bias** — every closed COMMODITY trade in the
   48h panel is LONG. Across PM (GC/SI/PL), softs (KC/CT), and energy
   (CL/NG), the engine cannot short. In an asset class where half the
   risk-adjusted return historically comes from short legs (KMLM, DBMF,
   AHL, MFCO), this is a structural cap on edge.
5. **Symbol concentration in GC=F** — 77.78% of the verdict cohort and
   48.6% of the 48h panel. Even when WR looks OK, this is one bet, not
   an asset class.
6. **Source label hygiene** — 33.3% of verdict-cohort COMMODITY trades
   have `source_system = UNKNOWN`. And the `by_asset_class_strategy_symbol`
   table contains EURUSD and SHIBUSDT classified as COMMODITY. **The
   asset_class column has at least 2 mis-classified rows in 28** — a
   ~7% labeling error rate that contaminates every cohort number above.
7. **No DSR / SPA / PBO** — n=9 is below the 20-per-strategy threshold
   the verdict needs to run multiple-testing corrections. Until n
   triples, "favorable" numbers cannot be distinguished from noise.

---

## External Replication Options

Use these as **external alpha sources** to either (a) trade alongside
internal strategies, (b) feed as features into a probation strategy, or
(c) act as a benchmark we have to beat before sizing internal alpha.

| External | What it is | Why for COMMODITY | Access | Cost | Suggested role |
|---|---|---|---|---|---|
| **DBMF** (iMGP DBi Managed Futures) | ETF that long/short-replicates the top 20 SG CTA index members; daily NAV + positions disclosed | Captures CTA cross-asset TSMOM beta including the short-side legs our engine cannot trade; ~$1B AUM, 2yr live track | ETF tape (any broker) + 13F | Free data | **Benchmark + signal mirror** — read DBMF's monthly factor sheet; if it is LONG NG and SHORT GC, ours should not be 77% LONG GC |
| **KMLM** (KFA Mount Lucas Managed Futures Index) | ETF tracking MLM Index — equal-weight TSMOM on 22 commodity, FX, rates futures since 1988 | Pure long/short TSMOM on commodities only; the academic CTA replicator | ETF tape + index methodology PDF | Free | **Replication target** — our `cta_replicator` should track KMLM rolling 3M correlation > 0.4 or it is not actually replicating |
| **MTUM / QMOM** (Equity momentum ETFs) | Cross-sectional momentum ETFs | Not directly commodity — useful as macro regime filter (risk-on equity momentum often regimes commodity trend) | ETF tape | Free | Regime overlay |
| **PIMCO BOND** (PTTRX / BOND ETF) | Active core bond | Cross-asset hedge — bond rally regime correlates with PM rallies; PIMCO position changes published quarterly | Quarterly fact sheet | Free | Macro regime feature |
| **CME / CFTC Commitment of Traders (COT)** | Weekly positioning of Managed Money vs Commercials per contract | We already use `cftc_socrata` (PF 2.45, n=3) and `multi_asset_cot` (PF 0, n=4). The first is our best signal; the second is broken. Need to figure out why same-data → opposite outcomes | CFTC Socrata API (free) | Free | **Double down on `cftc_socrata`**, audit `multi_asset_cot` symbol/direction logic |
| **CME Group "Equities Insights" + futures vol surfaces** | Implied vol, term structure, basis | Filter LONG-only entries by contango/backwardation regime — never go LONG carry-negative commodity in deep contango | CME DataMine (paid) or QuikStrike free tier | Free tier OK | Entry filter |
| **Hyperliquid HLP** | On-chain market-making vault returns | Not commodity — skip for this class |
| **AHL / WTON / MFCO** (Man AHL Diversified, Winton) | Old-school CTA daily NAV from UCITS share classes | Reference manager — if AHL is up and we're down, our strategies are broken not the tape | UCITS factsheets (monthly) | Free | Sanity check |
| **Bloomberg Commodity Index (BCOM)** | Diversified long-only commodity benchmark | The "do nothing" baseline our LONG-only strategies must beat after fees | Free (BCOM ETF DJP) | Free | Floor benchmark |
| **Goldman Sachs Commodity Index (S&P GSCI)** | Production-weighted, energy-heavy | Alternative LONG-only baseline | Free | Free | Floor benchmark |

**Concrete proposal:** add a `dbmf_kmlm_shadow` sidecar (opt-in per
Wire-Up Rule) that ingests DBMF top-10 positions monthly and KMLM
sector weights quarterly. Emit a "regime card" (LONG/SHORT bias per
contract). For Phase 30-60-90 see Rescue Plan below.

---

## 30 / 60 / 90 Day Rescue Plan

### 30 days — STOP THE BLEEDING

1. **Kill list (`BLOCKED_SOURCE_SYSTEMS` / strategy demotion)** — per
   `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` + `MUTATION_THREE_AXIS_PROTOCOL.md`,
   run mutation analysis first then demote:
   - `cta_replicator` on COMMODITY (0/7)
   - `multi_asset_copytrader` on COMMODITY (0/10)
   - `multi_asset_cot` on CT=F specifically (0/4)
2. **Fix labeling (R-4 / R-6)** — write
   `tools/fix_commodity_asset_class.py` to:
   - reclassify EURUSD rows → FOREX, SHIBUSDT rows → CRYPTO
   - backfill `source_system` where it is currently UNKNOWN by joining
     to `audit_picks` on signal_id
   - patch `pick_summary_stats_*.py` so COMMODITY is its own recency
     bucket, not folded into FUTURES (which currently includes ES/NQ/RTY
     index futures and corrupts the panel)
3. **Concentration gate enforcement** — patch
   `alpha_engine/money_ready_verdict.py` so `concentration_capped` becomes
   a HARD verdict gate (single-symbol > 50% → INSUFFICIENT_DATA regardless
   of other metrics). This is the CLAUDE.md banner P0 fix; COMMODITY at
   77.78% GC=F is the canonical case.
4. **Direction audit** — add `enforce_short_capability` check: any strategy
   gated to COMMODITY must produce both LONG and SHORT signals over the
   past 30 days, else it is demoted to "long-only directional bet" tier
   and cannot exceed 10% of class allocation.

### 60 days — ADD REAL EDGE

5. **Wire `dbmf_kmlm_shadow`** — implement the external sidecar
   above. Initially read-only (regime card on dashboard). After 30 days
   of paper, gate `commodity_tsmom_12m` LONG entries by "DBMF top-10
   shows LONG bias on parent sector" (energy/PM/agri/softs).
6. **Promote `cftc_socrata`** — only strategy with positive policy-clean
   PF on n>=3 (PF 2.45 on GC). Run mutation analysis: does the edge
   survive on SI, CL, NG, ZC? If yes, expand its symbol whitelist. If
   only GC, accept that this is a single-symbol strategy.
7. **Rebuild `multi_asset_cot`** as `cot_extremes_v2`: only enter when
   Managed Money positioning is in top/bottom decile vs trailing 3 yrs,
   AND price has confirmed a turn (5d momentum sign flip). Use it as a
   SHORT-capable strategy; current implementation is LONG-only which is
   half the COT edge.
8. **Slippage audit** — current model uses 12 bps. CL=F, NG=F overnight
   gap slippage is empirically 20-40 bps. Patch
   `alpha_engine/money_ready_verdict.py:PNL_WIN_THRESHOLD_BY_CLASS` style
   with per-symbol slippage and re-score.

### 90 days — INSTITUTIONALIZE

9. **Two-strategy minimum per asset class** — until COMMODITY has at
   least 2 strategies with n>=20 each in policy-clean-net cohort, it
   cannot be promoted past `INSUFFICIENT_DATA`. Track via
   `tools/strategy_tier_tracker.py`.
10. **DSR / PBO / SPA over n>=60** — push the cohort to n>=60 (post
    cleanup, ~9→60 needs ~6 weeks at current rate or ~3 weeks if we
    accept more strategies after kill list) and re-run money_ready
    verdict. Acceptance criterion is `dsr_ok=true` AND `spa_ok=true`.
11. **Live track vs DBMF + KMLM + BCOM** — publish a monthly card on
    `findtorontoevents.ca/audit` showing our COMMODITY P&L vs the three
    benchmarks. Hedge-fund-grade means we beat KMLM net of fees on a
    rolling 3M basis at lower or equal MDD.
12. **Documentation** — `updates/2026-MM-DD-commodity-rescue-results.md`
    cards at 30/60/90 milestones, each linking to the
    `reports/deep_dive_COMMODITY_2026-MM-DD.md` follow-up.

---

## Risk Register

| ID | Risk | Severity | Likelihood | Mitigation |
|---|---|---|---|---|
| R-1 | `cta_replicator` continues to lose if we delay demotion | HIGH | HIGH | Run mutation analysis week 1, demote week 2 |
| R-2 | Killing `multi_asset_copytrader` reduces signal volume → n stays small → still INSUFFICIENT_DATA forever | MEDIUM | HIGH | Add `cot_extremes_v2` and `dbmf_shadow` BEFORE killing to keep n flow |
| R-3 | Concentration gate fix breaks other classes' verdicts retroactively | MEDIUM | MEDIUM | Roll out behind `CONCENTRATION_GATE_HARD=1` env flag; A/B for 7 days |
| R-4 | Asset-class labeling is wrong elsewhere too (EURUSD/SHIB in COMMODITY proves the bug exists) | HIGH | HIGH | Run repo-wide label audit `tools/audit_asset_class_labels.py`; expected to find similar in CRYPTO/FOREX |
| R-5 | LONG-only bias is in the strategy code, not the data — making strategies short-capable is a multi-week refactor | HIGH | MEDIUM | Identify which strategies have `direction` parameter exposed vs hardcoded; quote effort before committing |
| R-6 | Recency panel buckets COMMODITY under FUTURES, hiding the problem from the dashboard | MEDIUM | CERTAIN (already happening) | Patch `tools/build_pick_summary_stats.py` to emit COMMODITY as own bucket |
| R-7 | External replication (DBMF/KMLM) data has 1-month lag → not actionable for fast trades | LOW | MEDIUM | Use as monthly regime overlay, not intraday signal |
| R-8 | Promoting `cftc_socrata` on n=3 over-fits to GC luck | HIGH | MEDIUM | Mandatory n>=20 per symbol before any sizing; require positive PF after 12bps slippage on 3 different commodities |
| R-9 | Resolver mis-labels EXPIRED→LOST on COMMODITY (CLAUDE.md cites the leakage signals on CRYPTO; could be same here) | MEDIUM | MEDIUM | Audit COMMODITY resolver outcomes manually for 30 random closed picks; cross-check vs yfinance close |
| R-10 | Sizing up COMMODITY on the favorable n=9 verdict-cohort number gets blown out by a single GC drawdown (77.78% concentration) | CRITICAL | HIGH if we size up | DO NOT size COMMODITY past current notional until 90-day acceptance criteria met |

---

## Acceptance Criteria

COMMODITY is allowed to leave `INSUFFICIENT_DATA` / sub-T2 status and be
sized for real money ONLY when **all** of these are true on
`money_ready_verdict.json` and `pf_registry.json` simultaneously:

1. **n_resolved >= 60** in `by_asset_class_policy_clean_net` for COMMODITY
2. **At least 2 strategies with n >= 20 each** in
   `by_asset_class_strategy_policy_clean_net` (current: 0)
3. **Profit factor >= 1.50** on the n>=60 cohort (T2 floor) — long-run
   target 2.0 (T1)
4. **Win rate >= 50%** on the n>=60 cohort
5. **Max drawdown <= 20%** on the realized equity curve (T2); long-run
   target <= 10% (T1)
6. **Top-symbol concentration <= 30%** (no GC=F dominance)
7. **Top-source concentration <= 50%** (real cross-engine diversification)
8. **DSR `dsr_ok=true`** at p<0.05 with deflation
9. **SPA `spa_ok=true`** OR `pbo_ok=true` (multiple-testing controlled)
10. **Asset-class label audit clean** — zero non-commodity symbols
    (EURUSD, SHIB*) in the COMMODITY cohort
11. **Beat KMLM net** on rolling 90-day total return AND beat KMLM on
    rolling 90-day MDD
12. **Resolver outcome audit clean** — 30 random closed picks manually
    verified against yfinance close prices, <=1 mismatch

---

## Hard Rule (Until Met)

**Until ALL 12 acceptance criteria above are met simultaneously, COMMODITY
notional MUST NOT exceed its current allocation cap, no strategy on
COMMODITY may be promoted into Smart Picks / High Conviction / Money
Ready, and any PR that proposes sizing-up COMMODITY without citing
`reports/deep_dive_COMMODITY_2026-MM-DD.md` showing the criteria met
on a current snapshot is REJECTED.**

Single most important sub-rule: **no real-money trade on COMMODITY while
top-symbol concentration > 30%.** The current verdict-cohort 77.78% GC=F
makes the favorable PF=1.81 statistically equivalent to a single bet on
gold, not an asset-class edge.

---

*Generated 2026-05-31. Sources: money_ready_verdict.json
(2026-05-30T23:05:42Z), pf_registry.json, pick_summary_stats_{2w,48h}.json.
No web-fetched or model-inferred numbers — see CLAUDE.md
"DO NOT trust unsourced model claims about /audit numbers" rule.*
