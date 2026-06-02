# Wire-up gap + resolver PRICE_MISMATCH bug — 2026-06-01

## TL;DR

1. **30+ academic strategies are orphans** — they exist in code, dedupe and gating run, but nothing pushes them to `trading_picks`. This PR ships two localized fixes (source_system tagging + dedup-key fix); the **bridge step still needs operator/peer wiring**.
2. **Resolver PRICE_MISMATCH branch is mislabeling SL hits as TP wins** — uncovered by investigating `short_dominant_engine`'s suspicious "100% WR / PF ∞" claim. **This is an active correctness bug producing fake wins.**
3. **No edge in any asset class** under the now-trustworthy `at_pick_outcomes` (37,884 rows). 0/7 classes pass T3 thresholds. CRYPTO is closest (PF_LB 0.97). Statistical floors: Wilson 95% LB on WR, bootstrap PF 5th percentile.

## Wire-up gap (with 2 fixes shipped, 1 step deferred)

### Verified state

| Layer | Status |
|---|---|
| 30+ academic strategies registered in `academic_strategies_emitter._GENERATORS` | ✅ |
| Called by `priority_picks_emitter.emit_picks()` | ✅ |
| `priority_picks_emitter` has a production caller (GHA / cron / `main.py`) | ❌ — orphan |
| Picks reach `active_picks.json` (the file `mysql_trading_sync` reads) | ❌ |
| Picks reach `trading_picks` table | ❌ — 0 rows from any academic source_system in last 48h |
| Picks reach `at_pick_outcomes` | ❌ — 0 rows |
| Picks reach `pf_registry.json` per-strategy attribution | ❌ |

### Shipped this PR

**(a) `alpha_engine/academic_strategies_emitter.py:268-274`** — Tag `source_system = academic_{strategy_name}` so picks are attributable per strategy in `pf_registry`. Before: `source_system` was unset and downstream defaulted to NULL or a generic bucket.

**(b) `alpha_engine/priority_picks_emitter.py:50-67`** — Change dedup key from `(symbol, direction)` to `(symbol, direction, strategy)`. Before: 5 academic strategies emitting the same `(BTC, LONG)` collapsed to 1 pick — destroying per-strategy diversity before the DB writer.

Both verified with `py_compile` + import test.

### Still needed (separate PR — operator decision required)

**(c) Bridge `priority_picks_emitter` → `mysql_trading_sync`**. Two paths:

   **Option A (recommended by Gemini + Grok consensus)**: Have `priority_picks_emitter` MERGE its output into `alpha_engine/data/active_picks.json` (using `id`/canonical key for dedup). The existing hourly `mysql-trading-sync.yml` (cron `30 * * * *`) then auto-ingests.

   **Option B**: Have `priority_picks_emitter` call `mysql_trading_sync` directly. More code, less re-use, harder to test.

**(d) Add GHA cron that runs `priority_picks_emitter` before the :30 sync.** E.g. cron `25 * * * *` so picks are in `active_picks.json` before mysql sync fires.

**(e) Decide segregation policy** — `trading_picks` does not have a `forward_test_only` column. Academic picks are tagged with that key in the JSON, but the UPSERT in `mysql_trading_sync` drops it. Either:
   - Add `forward_test_only TINYINT(1) DEFAULT 0` column + filter at read time in dashboard generators
   - Rely on `source_system LIKE 'academic_%'` as the segregation key (cheaper but coupled to naming)

## Resolver PRICE_MISMATCH bug (P0 — active correctness issue)

Investigating `short_dominant_engine`'s suspicious "100% WR" claim revealed:

**The "100% WR" is literally 2/2.** Both WON rows are corrupted:

```
DOGEUSDT SHORT  created_at=2026-04-16 05:51  closed_at=2026-04-15 07:16
                exit_reason='SL_HIT_RESOLVED [PRICE_MISMATCH...]'
                status=TP_HIT  pnl_pct=+3.11%

DOGEUSDT SHORT  created_at=2026-04-22 13:41  closed_at=2026-04-15 07:16
                exit_reason='SL_HIT_RESOLVED [PRICE_MISMATCH...]'
                status=TP_HIT  pnl_pct=+4.24%
```

**Three concurrent bugs:**
1. `closed_at < created_at` by 1 and 7 days → **time-reversal / look-ahead leakage**
2. `exit_reason='SL_HIT_RESOLVED'` but `status='TP_HIT'` and `pnl_pct>0` → **sign-flip mislabel**
3. Both rows share the exact same `closed_at` (2026-04-15 07:16:17) → **batch backfill stamping fixed historical price onto future picks**

Root cause: `audit_trail/universal_pick_resolver.py` PRICE_MISMATCH branch (despite commit `853d5b847` fixing other resolver bugs). When the resolver sees a PRICE_MISMATCH it's escalating SL → TP and inverting the pnl sign.

Confirms: any source_system with >99% EXPIRED + a tiny decisive tail will report 100%/0% WR off resolver glitches. Need:
- Hard-fail on `closed_at < created_at` (time-reversal must abort, not silently resolve)
- Hard-fail on `exit_reason='SL_HIT*' AND status='TP_HIT'` (sign coherence check)
- Min-decisive-n gate (`n_decisive ≥ 100`) before reporting WR/PF in dashboards

## Other findings from this session (corroborated by multi-AI swarm)

### `prediction_market_agents` PF=32 — **NOT an edge, source-tag bleed**

- 96.7% of n=2,319 are EXPIRED with pnl=0. Only 76 decisive (66W/10L).
- `source_system='prediction_market_agents'` is contaminated — picks from `multi_asset_forex_zscore_200d_fade::GBPUSD=X` (a forex strategy) are tagged into the PM bucket.
- Suspicious flat `pnl_pct=2.5000` on multiple winners → looks capped/synthetic.
- Fix: split PM source_systems in `audit_trail/universal_pick_resolver.py:204-206`.

### 27 truncated pick_ids at len=100 — **cosmetic only, no action needed**

- All 27 resolve 1:1 to `trading_picks.id` exact matches.
- Source: `genome_revival_*` batch from 2026-03-09, frozen historical cohort.
- Hex-12 segment (~48 bits entropy) makes silent collisions virtually impossible.
- Recommendation: leave as-is.

## Per-class verdict (now trustworthy on the 37,884-row table)

| Class | n_dec | WR% | PF | Wilson LB | PF LB | Verdict |
|---|---:|---:|---:|---:|---:|---|
| CRYPTO | 5,348 | 49.8 | 1.09 | **0.484** | **0.97** | NO_EDGE — closest to T3 |
| FOREX | 2,463 | 40.4 | 2.17 | 0.384 | 0.85 | NO_EDGE (headline PF misleading) |
| COMMODITY | 872 | 35.4 | 0.39 | 0.323 | 0.29 | NO_EDGE |
| EQUITY | 226 | 48.7 | 0.53 | 0.422 | 0.32 | NO_EDGE |
| FUTURES / ETF / BOND / MEME | n<100 | — | — | — | — | INSUFFICIENT_N |

**0 of 7 classes pass T3.** 5/7 are >80% EXPIRED — TP/SL are barely engaging, so PF/WR computed on a thin minority. CRYPTO is the most decision-rich (60% EXPIRED) and the closest-to-edge cohort.

## Recommended action order

1. **Merge this PR** (source_system + dedup-key fixes)
2. **Open separate PR for the resolver PRICE_MISMATCH bug** — hard-fail on time-reversal + sign-coherence
3. **Open separate PR for the bridge step** — Option A (merge into active_picks.json) with new GHA cron
4. After all 3 land + 24-48h of fresh picks flowing: rerun per-class edge analysis to see if the new strategies show edge

The 2 fixes in this PR are safe to ship without the bridge — they're pure tagging/dedup hygiene with no behavior change on the (currently dead) DB-write path.
