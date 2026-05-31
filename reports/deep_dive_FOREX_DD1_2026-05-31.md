# FOREX Deep-Dive (DD1) — 2026-05-31

**Goal #1** — find proven edge across all asset classes on `/audit`. FOREX is currently
**FAIL+INSUFF-N** per PR #267 (14d n=40, WR 20%, PF 0.40) and degraded vs the M-067 baseline
(CLAUDE.md: PF 0.55, WR 40% n=53). Two open incidents (INCIDENT_FOREX #6/#7) sit on top
of this class.

This file is the **DD1 lane** of the parallel deep-dive sweep (sibling of
`deep_dive_FOREX_2026-05-31.md`). Numbers below are **live** from
`ejaguiar1_stocks.trading_picks` pulled 2026-05-31, joined against
`audit_dashboard/data/money_ready_verdict.json` 2026-05-31T20:09:25Z and
`pf_registry.by_asset_class_policy_clean_net` of the same vintage. All SQL inlined.

---

## 1. Per-source autopsy

### 1a. Volume + verdict per strategy (FOREX, 90d, closed only)

```sql
SELECT strategy, COUNT(*) n,
  ROUND(SUM(pnl_pct>0)*100.0/COUNT(*),1) wr,
  ROUND(SUM(CASE WHEN pnl_pct>0 THEN pnl_pct END)/
        NULLIF(ABS(SUM(CASE WHEN pnl_pct<0 THEN pnl_pct END)),0),2) pf,
  ROUND(AVG(pnl_pct),3) avg_pnl
FROM trading_picks
WHERE LOWER(category)='forex' AND closed_at > NOW() - INTERVAL 90 DAY
  AND status IN ('TP_HIT','SL_HIT','LOST','EXPIRED','TIME_EXIT')
GROUP BY strategy ORDER BY n DESC;
```

| Strategy | n | WR% | PF | Avg PnL | Verdict |
|---|---|---|---|---|---|
| `forex_rsi2_mean_reversion` | 664 | 44.9 | **0.38** | -0.153 | CHRONIC LOSER — volume leader, drives class-level FAIL |
| `myfxbook_retail_contrarian` | 364 | 46.4 | **3.81** | +0.207 | HIDDEN EDGE — contrarian asymmetry (loses small, wins big) |
| `ig_contrarian_sentiment` | 314 | 44.6 | **16.73** | +0.418 | HIDDEN EDGE (skew-driven, needs DSR + tail-risk audit) |
| `non_crypto_consensus` | 144 | 52.1 | 6.34 | +0.539 | PROMISING — only strategy >50% WR with n>=100; T2 candidate |
| `forex_carry_momentum` | 43 | **9.3** | 19.81 | +10.7 | OUTLIER — 4 huge wins mask 39 losses; do not trust PF |
| `cta_cross_asset_tsmom` | 32 | 21.9 | **0.03** | -0.684 | CONFIRMED KILL (matches per-task brief) |
| (blank) | 22 | 68.2 | 0.73 | -1.31 | category/strategy routing bug (CLAUDE.md note) |
| `fx_smart_carry_trade_momentum` | 21 | 52.4 | 1.62 | +0.105 | Near-T2, n too small; admissibility-harness candidate |
| `cta_fx_multifactor` | 10 | 60.0 | 26.85 | +0.304 | n too small; promising |
| `dxy_trend_filter` | **0 (90d)**, all-time **n=1** last 2026-03-13 | – | – | – | DORMANT — memory's "PF 1.63 n=995" is from a different cohort; emitter has not produced a closed pick in ~80 days |

### 1b. Loss concentration — top 3 worst symbol-strategy combos (n>=10, 90d)

| Strategy | Symbol | n | WR% | PF | Total PnL |
|---|---|---|---|---|---|
| forex_rsi2_mean_reversion | **NZDUSD=X** | 44 | 43.2 | 0.07 | **-114.74%** |
| cta_cross_asset_tsmom | NZDUSD=X | 10 | 10.0 | 0.01 | -20.30% |
| forex_rsi2_mean_reversion | EURJPY=X | 47 | 38.3 | 0.06 | -17.55% |
| forex_carry_momentum | USDJPY=X | 28 | **7.1** | 0.02 | -8.31% |

### 1c. Win concentration — top 3 best combos (same shape, DESC)

| Strategy | Symbol | n | WR% | PF | Total PnL |
|---|---|---|---|---|---|
| myfxbook_retail_contrarian | **NZDUSD=X** | 23 | 60.9 | 21.23 | **+85.84%** |
| ig_contrarian_sentiment | NZDUSD=X | 15 | 46.7 | 205.33 | +79.65% |
| ig_contrarian_sentiment | USDCAD=X | 36 | 50.0 | 85.70 | +48.04% |

**Cleanest signal in the report**: NZDUSD is the dominant carrier in both directions —
trend-following loses heavily (-114%), contrarian wins heavily (+85%). Same instrument,
opposite bias, opposite outcomes.

### 1d. Worst exit_reason mix

| Status | n | Avg PnL |
|---|---|---|
| LOST | 800 | -0.32% |
| TP_HIT | 718 | +1.27% |
| EXPIRED | 126 | -0.03% |
| TIME_EXIT | 17 | -0.00% |
| **SL_HIT** | **6** | **-17.6%** |

All 6 SL_HITs are blank-strategy rows from 2026-04-10 with leverage-multiplier /
direction-blind magnitudes (-76, -18 on GBPJPY/USDJPY). These are the resolver bugs PR
#207/#208 address, not strategy losses — should be filtered from verdict before any
kill decision.

### 1e. 14d activity — strategies actually emitting now

| Strategy | n | WR% | PF |
|---|---|---|---|
| forex_rsi2_mean_reversion | 16 | **6.3** | 0.06 |
| fx_smart_carry_trade_momentum | 6 | 50.0 | 1.47 |
| regime_accumulation | 5 | 40.0 | 1.19 |
| forex_carry_momentum | 5 | 0.0 | – |
| myfxbook_retail_contrarian | 1 | 0.0 | – |
| ig_contrarian_sentiment | 0 | – | – |
| non_crypto_consensus | 0 | – | – |

**Wiring-mix bug**: the three best strategies (myfxbook, ig, non_crypto_consensus) have
nearly stopped emitting while `forex_rsi2_mean_reversion` runs at production volume
with WR=6.3% / PF=0.06. The strategies that work are starved, the one that loses runs
unconstrained. Same pattern as the upstream wire-up backlog in
`project-money-ready-2026-05-31.md`.

---

## 2. External-replication options

1. **MyFXBook Retail Contrarian Composite** — 15-min retail long/short positioning on
   major crosses. Institutional contrarian (fade retail when crowding >70%) has
   academic Sharpe 0.8-1.3 (Pojarliev & Levich 2010). We already run
   `myfxbook_retail_contrarian` (PF 3.81 n=364). External-clone effort: wire OANDA
   position-book as a second sentiment feed.

2. **IG Client Sentiment (DailyFX)** — IG's own position book. In-house version is
   `ig_contrarian_sentiment` (PF 16.73 n=314, skew-heavy on NZDUSD). High correlation
   with MyFXBook so should be merged into a single composite, not run as parallel
   strategies. Academic basis: visibility-bias literature (Han/Hirshleifer/Walden).

3. **KMLM / DBMF (managed-futures ETFs, FX TSMOM component)** — Mount Lucas and
   iMGP DBi managed-futures ETFs carry FX exposure as part of CTA TSMOM book.
   If our in-house FX TSMOM (`cta_cross_asset_tsmom` PF 0.03,
   `forex_tsmom_12m` n=1) can't match KMLM's ~0.6 Sharpe, route FX budget into the
   ETF directly instead of running broken TSMOM in-house.

Fourth optional vector: **CADJPY long-only Wed/Thu** (Tokyo morning carry reset folk
edge). `non_crypto_consensus + CADJPY` shows 86.7% WR n=15;
`ig_contrarian_sentiment + CADJPY` shows 62.9% WR n=35. Worth a M-107 pre-registered
harness run before any production use.

---

## 3. 30 / 60 / 90 day rescue plan

### Days 0-30 — stop the bleed, harvest the wins

| Action | Target |
|---|---|
| Reduce `forex_rsi2_mean_reversion` allocation by ~80%; exclude NZDUSD and EURJPY symbols (the two PnL sinks). Do NOT full-kill — see Risk Register. | next 14d FOREX class WR moves 20% -> >35% |
| Promote `myfxbook_retail_contrarian` and `ig_contrarian_sentiment` to first-class `money_ready` filters with concentration gate (single-symbol <40%). | both strategies emit at >=2x current 14d rate |
| Wire `dxy_trend_filter` — currently 1 closed pick all-time. Likely a `production_scanner` registration miss. | n>=20 closes in 30d so historical PF 1.63 claim can be tested |
| Filter blank-strategy/category FOREX rows from verdict numbers (the 6 SL_HITs are PR #207/#208 territory, not strategy losses). | FOREX 90d MDD drops 82% -> <30% (cosmetic, but unblocks honest verdict) |

### Days 31-60 — promote survivors, register new candidates

- Register **myfxbook + ig as a sentiment-composite** strategy via hypothesis-registry
  (M-107 pre-reg). Composite fires only on intersection (both feeds agree).
- Pre-register **CADJPY-Wed/Thu**; run admissibility harness for n>=30 paper picks.
- **NZDUSD direction-bias analysis** — Bayesian split to confirm contrarian-on-NZDUSD
  is a stable regime, not a 90-day fluke. If stable: promote `NZDUSD_contrarian_only`.
- Backfill `forex_rsi2_mean_reversion` minus NZDUSD/EURJPY; if PF recovers to >1.2,
  keep the strategy with the exclusion list (mutate-before-kill rule).

### Days 61-90 — qualify for T2 or replace with external benchmark

- Class target: n>=100 clean, PF>=1.5, WR>=50, MDD<20. With contrarian-composite
  + carry-momentum + dxy-trend-filter wired and rsi2-MR pruned, ~n=120 in 90d.
- If T2 not met by day 90, route FX budget into KMLM/DBMF and demote in-house
  FOREX to research-only. Document in `updates/index.html`.
- Re-run leverage/direction-blind PnL audit (PR #207/#208) to confirm no resolver
  bug is inflating or deflating verdict numbers.

---

## 4. Risk register

| Risk | What goes wrong | Mitigation |
|---|---|---|
| Overfitting to NZDUSD | NZDUSD is ~90% of the +PF in this report. A 1-symbol "edge" with n=23 is data-mined. | DSR-adjust + 30d walk-forward before promotion; combine with EURJPY/USDCAD signals to get n>=3 instruments. |
| Regime shift kills contrarian feeds | Retail-sentiment contrarian works when retail is crowded one-way; in chop it goes flat. | Pair sentiment signal with DXY-volatility regime filter; suspend trades when ATR(20) on DXY drops below 25th pctile. |
| Correlation creep myfxbook x ig | Both feeds are retail composites of overlapping broker pools — NOT independent edges; running both double-counts size. | Merge into single sentiment-composite with `both_feeds_agree` gate. |
| Full-killing rsi2_mean_reversion loses volume base | This strategy is 40% of FOREX n. Without it the class falls to n<200/90d and stays INSUFFICIENT_N. | Symbol-exclusion list (no NZDUSD, no EURJPY) instead of full demote — `docs/MUTATION_THREE_AXIS_PROTOCOL.md`. |
| dxy_trend_filter rewire reveals it never worked | Memory's PF 1.63 n=995 may be from the deprecated AUDIT_HEALTH_SOURCE=recompute path that bypassed flicker-dedup. | M-107 pre-register + harness; accept verdict whatever it is. Same trap as the 78.9% CRYPTO Smart-Picks figure CLAUDE.md flags. |
| Resolver bug masks real edge | 6 SL_HITs at -17.6% avg are leverage/direction-blind bugs (PR #207/#208), not real losses. They distort verdict MDD (82%). | Filter via PR #207/#208 fix; re-run pf_registry once landed. |
| Day-of-week/session bias data-mined | CADJPY-Wed/Thu is a 35-row anecdote. | M-107 pre-registration mandatory before production. |

---

## 5. Acceptance criteria

### Class-level (CLAUDE.md tier thresholds)

| Tier | PF | WR | MDD | n |
|---|---|---|---|---|
| T1 (Renaissance) | >=2.0 | >=55% | <10% | >=100 |
| T2 (long-run) | >=1.5 | >=50% | <20% | >=100 |
| **Current FOREX** | 0.40 | 20.0% | 82.3% | 40 (14d) / 29 (policy-clean) | **FAIL+INSUFF-N** |

### FOREX-specific guardrails

1. **Single-symbol concentration <40%** — today NZDUSD-contrarian is ~50% of +PnL.
   Single-source artifact per `pf_registry.by_asset_class_policy_clean_net`.
2. **Strategy concentration <60%** — today rsi2_mean_reversion is 40% of n. Acceptable
   ceiling; >60% reverts class to FAIL regardless of metrics.
3. **MDD on direction-corrected pnl_pct** — until PR #207/#208 land, MDD=82.3% may be
   inflated by direction-blind rows. Re-run after merge.
4. **No single SL_HIT >=5%** post-resolver-fix. Current max -76% is a data bug.
5. **n_resolved >=100 in policy-clean-net** (not raw `trading_picks`).
6. **DSR-adjusted Sharpe >=0.6** before promoting any contrarian-composite or
   dxy_trend_filter rewire.
7. **M-107 hypothesis-registry entry** before backtest numbers are cited for any new
   candidate (NZDUSD-contrarian-only, CADJPY-Wed/Thu, dxy_trend_filter, composite).

---

## Bottom line

FOREX is FAIL+INSUFF-N at the class level but contains **two near-T2 edges**
(myfxbook + ig contrarian) drowned out by `forex_rsi2_mean_reversion` running
unconstrained on NZDUSD and EURJPY. Fix is not "kill more" — it is:
(a) prune two symbols from rsi2_mean_reversion,
(b) merge the two contrarian feeds into one composite,
(c) re-wire `dxy_trend_filter` so memory's PF 1.63 claim can be verified or falsified.

Expected 30-day outcome: FOREX 14d WR 20% -> ~40%, PF 0.40 -> ~1.1, n stable.
Not yet T2, but unblocks INSUFFICIENT_N and gets us on the curve.

Strategies analyzed: **10 named** (forex_rsi2_mean_reversion, myfxbook_retail_contrarian,
ig_contrarian_sentiment, non_crypto_consensus, forex_carry_momentum,
cta_cross_asset_tsmom, fx_smart_carry_trade_momentum, cta_fx_multifactor,
dxy_trend_filter, forex_tsmom_12m) + 2 external benchmarks (MyFXBook+IG composite,
KMLM/DBMF).

## Sources

- Live: `mysql.50webs.com / ejaguiar1_stocks.trading_picks` 2026-05-31
- `audit_dashboard/data/money_ready_verdict.json` 2026-05-31T20:09:25Z
- `audit_dashboard/data/pf_registry.json` `by_asset_class_policy_clean_net`
- PR #267 `reports/peer_claude-tick23-per-class-fresh-stats_2026-05-31.md`
- CLAUDE.md tier thresholds + `docs/MUTATION_THREE_AXIS_PROTOCOL.md`
- INCIDENT_FOREX #6/#7 (per task brief)
- Sibling file: `reports/deep_dive_FOREX_2026-05-31.md`
- Memory: `project-money-ready-2026-05-31.md`, `project-confidence-trust-edges-2026-05-31.md`
