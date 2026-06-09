# Intrabar Edge-Hunt + Resolver Keyspace Gap — 2026-06-09

**Author:** Claude Opus 4.8 (autonomous edge-research loop)
**Type:** read-only discovery (no production mutation)
**Goal #1** (phenomenal performance across all asset classes on /audit)

## TL;DR

Swept **all** per-class strategies on **intrabar truth** (`COALESCE(CASE WHEN
intrabar_ambiguous=0 THEN trading_picks.intrabar_pnl_pct END, at_pick_outcomes.pnl_pct)`)
for the money-ready bar (n≥100, PF>1.5, WR>52%), excluding the 19 BANNED_SOURCES,
backfill resolvers, and per-class extreme-pnl artifacts.

**Result: 0 trustworthy new T2 leads.** The 2 filter-survivors are both refuted.
The decisive discovery is structural: **the current production outcome resolver
(`universal_v2`) is on a different primary-key keyspace than the intrabar columns,
so the clean cohort cannot be intrabar-validated at all through the join used by
`money_ready_verdict`.** This is the next resolver-plumbing target and it explains
why no clean intrabar edge surfaced.

## Sweep survivors — both REFUTED

| class | strategy | n | WR% | PF | avg% | n_intrabar | verdict |
|-------|----------|---|-----|----|----|-----------:|---------|
| crypto | `hs_lb_None` | 202 | 65.3 | 3.30 | +1.57 | **0** | REFUTED |
| equity | `MeanReversionBB` | 175 | 54.9 | 1.82 | +0.74 | **0** | REFUTED |

- **`hs_lb_None`**: strategy name is a null placeholder (`hs_lb` + `None`), already
  in `money_ready_verdict._OUTCOMES_ARTIFACT_STRATEGIES`. All 202 rows are
  `universal_v2`, resolved in a **3-day window** (2026-05-31 → 06-03), 102 distinct
  symbols, **0% join to trading_picks** (no intrabar possible). Single-snapshot
  resolver artifact, not edge.
- **`MeanReversionBB`**: `universal_v2`, **5-day window** (05-31 → 06-05), only **8
  distinct symbols** for n=175 (heavy concentration), 0% intrabar join. Fails
  money-ready on window length, concentration, and intrabar-validation.

Every strategy that **did** have intrabar coverage was *deflated below the bar* by
the COALESCE (luxalgo_confluence → PF 1.20 @ 41.2% WR on n=2055;
prediction_market_consensus 13.2→2.0; ml_enhanced_DYDXUSDT_15m 8.87→1.91). The only
filter-survivors are the strategies the intrabar fix **couldn't reach**.

## Structural finding — three disjoint resolver keyspaces

`at_pick_outcomes.pick_id` join rate to `trading_picks.id` (where intrabar lives),
WON/LOST + pnl_pct NOT NULL:

| resolver_version | n | trading_picks join% | in clean cohort? |
|------------------|--:|--------------------:|------------------|
| `backfill_widened_202…` | 4349 | 100% | **excluded (backfill)** |
| `backfill_2026-06-01` | 2973 | 80% | **excluded (backfill)** |
| **`universal_v2`** | **1528** | **0%** | **yes — dominant clean resolver** |
| `signflip_purge_20260…` | 367 | 100% | yes |
| `v2.2_sync_2026-06-05` | 325 | 100% | yes |
| `v2.1` | 62 | 0% | yes |

`pick_id` keyspaces are mutually incompatible:
- `universal_v2.pick_id` = **content hashes** (`03285aa77237e5ebaa23aa6d4fe55ea8`)
- `trading_picks.id` = **composite strings** (`::ATOM-USD::2026-05-27`, `ZROUSDT_15m_20260222_1338`)
- `at_raw_picks.id` = **UUIDs** (`00005e31-373d-…`); only 2% of outcomes join here

So `universal_v2` outcomes map to **neither** intrabar-bearing table.

### Why this matters
1. The intrabar `COALESCE` shipped in `money_ready_verdict` (commit `acc551cd8f`)
   is **correct and conservative**, but in the *clean* cohort it only reaches
   `signflip_purge` + `v2.2_sync` (692 rows @ 100% join). The dominant clean
   resolver `universal_v2` (1528 rows) is unreachable; backfill rows that DO join
   are excluded by the non-backfill filter.
2. This is *the* reason the clean+intrabar edge-hunt finds nothing: the clean
   cohort is mostly `universal_v2`, which has no intrabar truth attached.
3. It is hard evidence for the project thesis: **the measurement layer, not alpha,
   is the bottleneck** — even our best resolution upgrade can't see the cohort that
   matters.

## Next step (resolver-plumbing, for a future iteration)
Intrabar-resolve `at_pick_outcomes` rows **directly** — replay OHLC by
`(symbol, entry, tp, sl, resolved_at/created_at)` and write the result back keyed by
`at_pick_outcomes.pick_id` (its own hash keyspace), instead of joining `trading_picks`.
`tools/reresolve_intrabar.py` currently only knows the `trading_picks` keyspace; a
sibling pass over `at_pick_outcomes` (the universal_v2 population) would unlock
intrabar truth for the clean cohort. Until then, no clean-cohort PF/WR is
intrabar-validated and **no class should be sized up on these numbers**.

## Method (reproducible)
- DB: `ejaguiar1_stocks` via `tools.db_env.get_stocks_creds()`.
- Filters: `status IN ('WON','LOST')`, `pnl_pct IS NOT NULL`,
  `resolver_version NOT LIKE 'backfill%'`, `strategy NOT IN (BANNED_SOURCES ∪ {prediction_market_consensus})`,
  per-class `ABS(eff_pnl) ≤ cap` (FOREX 20 / COMMODITY 30 / BOND 25 / CRYPTO·MEME 95 / FUTURES 30 / else 50).
- `eff_pnl = COALESCE(CASE WHEN tp.intrabar_ambiguous=0 THEN tp.intrabar_pnl_pct END, apo.pnl_pct)`
  via `at_pick_outcomes apo LEFT JOIN trading_picks tp ON tp.id = apo.pick_id`.
- HAVING `n≥100`; lead gate `WR>52% AND PF>1.5`.
