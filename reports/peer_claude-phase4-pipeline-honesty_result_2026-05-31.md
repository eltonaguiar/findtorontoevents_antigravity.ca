# Phase-4 End-to-End Strategy Tracking Pipeline Honesty — Result (2026-05-31)

**Auditor:** Claude Opus 4.7, READ-ONLY pipeline validation.
**DB:** `ejaguiar1_stocks` @ mysql.50webs.com, pulled 2026-05-31 ~05:40Z.
**Files inspected:**
- `audit_dashboard/data/pf_registry.json` (generated_utc 2026-05-31T01:57:17Z)
- `audit_dashboard/data/anti_overfit_audit.json` (generated_at 2026-05-11T21:42:54Z)
- `tools/strategy_tier_tracker.py`
- `tools/refresh_strategy_stats.py`

## Layer-by-layer verdict

| # | Layer | Verdict | Notes |
|---|---|---|---|
| 1 | `at_strategy_stats` table | DRIFT | Fresh (last_updated 2026-05-31 04:52Z, 175 rows) but `strategy` column stores confidence-tier labels ("STRONG"/"MODERATE"), not strategy names. No workflow cron calls `refresh_strategy_stats.py`. |
| 2 | `pf_registry.json` | PASS-with-DRIFT | Fresh (01:57Z today). PF math internally consistent. But sourced from JSON file mirrors (`alpha_engine/data/closed_picks.json`, `battleground/data/closed_picks.json`, etc.), not the live `trading_picks` DB; n drifts vs DB by 20-80% for sampled strategies. |
| 3 | `closed_picks` / `trading_picks` honesty | FAIL | **640 / 7093 (9%) closed picks have NULL `pnl_pct`** (resolver coverage hole). 134 picks have empty `direction=''` (unparseable). 1 BTCUSDT row stored with `category='forex'` (sanity-check fail). |
| 4 | `anti_overfit_audit.json` (DSR sidecar) | FAIL (STALE) | `generated_at` 2026-05-11T21:42:54Z — **20 days old**. PR #156 fix did not re-run the audit. |
| 5 | `strategy_tier_tracker.py` | PASS | Runs cleanly, no ImportError. Output reflects pf_registry 2026-05-31T01:57:17Z; tier ladder sensible. |

## Layer 1 — `at_strategy_stats` (DRIFT)

```
COUNT(*) = 175, MIN/MAX(last_updated) = 2026-05-31 04:52:22 (all rows refreshed in one batch)
```

Top-5 rows by `total_picks` returned by the table:
```
strategy=STRONG    asset_class=CRYPTO  total=2332 wins=873  WR=0.3817
strategy=STRONG    asset_class=CRYPTO  total=1852 wins=683  WR=0.3776   <- duplicate strategy/asset
strategy=STRONG    asset_class=CRYPTO  total=1829 wins=673  WR=0.3768
strategy=STRONG    asset_class=CRYPTO  total=1434 wins=454  WR=0.3170
strategy=MODERATE  asset_class=CRYPTO  total=1396 wins=415  WR=0.3235
```

Recomputed from `trading_picks` grouping on `strategy` column, top-5:
```
strategy=luxalgo_confluence      category=crypto   n=1906 w=835
strategy=forex_rsi2_mean_reversion category=forex  n=664  w=297
strategy=futures_momentum        category=commodity n=583 w=227
strategy=myfxbook_retail_contrarian category=forex n=364 w=169
strategy=ig_contrarian_sentiment category=forex   n=314 w=140
```

**Drift:** the `at_strategy_stats.strategy` column is not the actual strategy name — it stores the tier/confidence bucket ("STRONG"/"MODERATE"), with duplicate `(STRONG, CRYPTO)` rows that imply the unique key is `(strategy, source_system, asset_class)` but `source_system` is not surfaced in the top-5 query. The table is *populated*, but its semantics do not match what downstream consumers (e.g. /audit dashboards, strategy-tier-tracker) read as "strategy". This is the wave-3 wire-up failure mode.

**Cron status:** `grep -rln "refresh_strategy_stats\|refresh_strategy_stats_mysql" .github/workflows/` returns 0 hits. `tools/refresh_strategy_stats.py` exists but has no scheduler. Freshness today is from a manual / one-shot invocation, not a recurring refresh.

`audit-dashboard.yml` is running on schedule (last success 2026-05-31T03:23:29Z) but it does not call the refresh.

## Layer 2 — `pf_registry.json` (PASS-with-DRIFT)

`generated_utc = 2026-05-31T01:57:17Z`. Counts: raw_rows=3272, closed_rows=2276, after_flicker_filter=724, policy_clean_rows=434. Source files = `{alpha_engine,battleground,mercury2,paper_trading,ml_battleground/*}/data/closed_picks.json`. **It does not read the live `trading_picks` MySQL table.**

Recompute from live DB (`trading_picks` where category='crypto', source_system=X, closed_at IS NOT NULL, pnl_pct IS NOT NULL):

| strategy | pf_registry (raw) | live DB | drift |
|---|---|---|---|
| `battleground_luxalgo` | n=37, WR=32.4%, PF=0.29 | n=49, WR=61.2%, PF=1.75 | n +32%, WR +89%, **PF +500%** |
| `copy_trader_intel`    | n=34, WR=55.9%, PF=1.94 | n=6,  WR=33.3%, PF=2.13 | n -82% |

These are **not bugs in pf_registry's math** — the numbers internally match the file inputs. They expose the architectural drift: pf_registry's "live edge" picture is based on per-engine JSON snapshots that drift from the MySQL `trading_picks` table that production picks actually emit into. Downstream `strategy_tier_tracker.py` and the audit dashboard inherit this drift.

Methodology stamp in registry: `policy_clean = flicker dedup + policy exclusions`; net cohort drops 996 not-closed, 1552 spot-flicker, 102 dup, 188 policy-excluded. None of that explains the n=6 vs n=34 gap on copy_trader_intel — only a file-vs-DB sync gap does.

## Layer 3 — closed-pick honesty post PR #158 (FAIL)

`SELECT COUNT(*) FROM trading_picks WHERE closed_at IS NOT NULL AND pnl_pct IS NULL` => **640** rows. Of 7093 closed rows, 9.0% are unresolved. Top sources:

```
source_system=copy_trader_intel    status=LOST       count=276
source_system=alpha_engine         status=LOST       count=76
source_system=battleground_luxalgo status=LOST       count=38
source_system=regime_terminal      status=LOST       count=37
source_system=luxalgo_filters      status=TIME_EXIT  count=22
source_system=paper_trading        status=SL_HIT     count=19
```

PR #158 fixed SHIBUSDT resolution, but `copy_trader_intel` alone shows 276 closed-without-pnl rows. The resolver's pnl backfill is not running on the LOST-status legacy rows.

USDT-suffix non-crypto audit:
```
WIFUSDT     category=meme     1
DOGEUSDT    category=meme    17
SHIBUSDT    category=meme     7
BTCUSDT     category=forex    1   <- sanity-check FAIL
```

The 25 meme rows are arguably correct (memecoin classification). The BTCUSDT row with `category='forex'` is unambiguously wrong and indicates the symbol->category mapper has at least one mis-route.

Direction integrity: 134 closed picks have `direction=''` (empty string), making LONG/SHORT pnl-sign verification impossible from data alone. Sampled IDs (`f1ed3b0fb089`, `25f7398b5b04`, `07626b139836`) all show pnl signs that imply SHORT but `direction` is empty — these are stored correctly by the resolver but unauditable downstream.

pnl_pct recompute on last-100 closed (entry_price>0, exit_price not null): 57/100 "mismatch", of which:
- ~43 are NULL stored pnl_pct (resolver coverage hole, same as above)
- ~14 are sign-inverted because `direction=''` makes naive LONG-only recompute wrong; spot-checking shows the stored sign is correct, so this is a **data-quality (empty direction) failure**, not a pnl bug.

Zero rows showed an unambiguous pnl_pct math error after accounting for empty direction.

## Layer 4 — `anti_overfit_audit.json` / DSR sidecar (FAIL — stale)

```
$ jq '.generated_at' audit_dashboard/data/anti_overfit_audit.json
"2026-05-11T21:42:54.542173+00:00"
```

That is **20 days old** as of 2026-05-31. PR #156 (DSR / anti_overfit sidecar fix) merged but did not include a workflow trigger to regenerate the JSON. The dashboard surfaces stale DSR figures.

Spot-check skipped — file does not contain freshly computed DSR values to validate against today's trading_picks.

## Layer 5 — `strategy_tier_tracker.py` (PASS)

Runs cleanly:
```
[strategy_tier_tracker] wrote reports/strategy_tier_tracker_20260531T054030Z.md
Source: audit_dashboard/data/pf_registry.json generated 2026-05-31T01:57:17Z
```

Output is well-formed, tier thresholds match CLAUDE.md MAJOR GOALS (T1 PF>2.0/WR>55; T2 PF>1.5/WR>50; T3 PF>1.2/WR>45; min n=30). No ImportError. CRYPTO class verdict FAIL (n=333, PF=0.89, WR=37.5%), COMMODITY INSUFF_DATA — consistent with `money_ready_verdict.json` headline. **The script is honest within its inputs**; it simply inherits the file-vs-DB drift from layer 2.

## Recommendations (NOT applied — docs-only PR)

1. **at_strategy_stats refresh cron** — add a step to `.github/workflows/audit-dashboard.yml` (or a dedicated workflow) that runs `python3 tools/refresh_strategy_stats.py` so the table doesn't decay between manual invocations. *And* fix the upstream `refresh_strategy_stats_mysql()` so it keys by actual strategy name, not confidence tier. (Schema-level rename of column would also remove the semantic trap.)
2. **pf_registry MySQL sync** — extend `pf_registry` builder to read from `trading_picks` MySQL as a source on equal footing with the per-engine JSON files, OR run a job that syncs each engine's `closed_picks.json` <- DB so the file snapshots can't drift. Pin a `db_rows / file_rows` audit line in the registry.
3. **Resolver coverage** — backfill `pnl_pct` for the 640 LOST/TIME_EXIT/SL_HIT closed rows. Priority: `copy_trader_intel` (276), `alpha_engine` (76), `battleground_luxalgo` (38).
4. **BTCUSDT=forex** — single-row data fix + audit query `SELECT id FROM trading_picks WHERE symbol='BTCUSDT' AND category!='crypto'`.
5. **Empty direction** — backfill or block-on-insert for the 134 rows with `direction=''`.
6. **anti_overfit_audit refresh** — add a workflow step that regenerates the JSON on the same cadence as `audit-dashboard.yml`. Until then, the dashboard's DSR column lies.

## Honest one-liner

The pipeline RUNS. Layers 1, 2, 5 are technically green. Layer 3 has a **9% NULL-pnl resolver hole** that quietly drops trades from every downstream stat. Layer 4 has been stale for 20 days. The biggest hidden risk is layer 2's **JSON-vs-DB drift**, which causes `strategy_tier_tracker.py` to report institutional-grade verdicts off a stale snapshot — not off today's live signal book.
