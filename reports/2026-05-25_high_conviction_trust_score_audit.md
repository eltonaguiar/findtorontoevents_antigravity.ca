# HIGH CONVICTION overlay — `trust_score` NULL-rate audit (P0)

**Date:** 2026-05-25
**Investigator:** read-only sweep agent
**Trigger:** `reports/2026-05-25_audit_ui_edge_audit.md` flagged HC overlay's CRYPTO 60.3% / EQUITY 68.1% stats as unreproducible because the underlying `trust_score` column is empty.
**Scope:** read-only DB inventory + code trace; no mutations.

---

## 1. DB inventory — `ejaguiar1_stocks.trading_picks`

Live query 2026-05-25 (n = 48,348 rows).

### Overall
| metric | value |
|---|---|
| total rows | 48,348 |
| non-NULL `trust_score` | **17** |
| populated rate | **0.04%** |

### By status (the load-bearing one)
| status | total | non-NULL trust_score | % |
|---|---:|---:|---:|
| TIME_EXIT | 29,865 | 5 | 0.02% |
| active | 5,317 | 12 | 0.23% |
| OPEN | 4,159 | 0 | 0.00% |
| **LOST** | **3,262** | **0** | **0.00%** |
| **WON** | **2,559** | **0** | **0.00%** |
| SL_HIT | 1,094 | 0 | 0.00% |
| TP_HIT | 839 | 0 | 0.00% |
| EXPIRED | 604 | 0 | 0.00% |
| LOSS | 185 | 0 | 0.00% |
| WIN | 139 | 0 | 0.00% |
| CLOSED | 116 | 0 | 0.00% |
| CLOSED_SL | 87 | 0 | 0.00% |
| CLOSED_TP | 82 | 0 | 0.00% |

**Closed-book (WON/LOST/CLOSED/TP_HIT/SL_HIT/CLOSED_TP/CLOSED_SL/WIN/LOSS/TIME_EXIT/EXPIRED) populated rate: 5 / 38,852 = 0.013%.** The HC overlay cites WR stats over this exact cohort, which is empty for the gate column.

### By category
| category | total | non-NULL | % |
|---|---:|---:|---:|
| crypto | 18,243 | 15 | 0.08% |
| forex | 15,769 | 1 | 0.01% |
| commodity | 9,357 | 0 | 0.00% |
| equity | 2,484 | 1 | 0.04% |
| (empty) | 1,228 | 0 | 0.00% |
| futures/index/bond/meme/stocks/etf/penny | 1,267 | 0 | 0.00% |

### Distribution (where populated)
n=17, min=1, max=90, mean=17.12. Histogram: `1×3, 2×5, 3×5, 6×1, 82×1, 85×1, 90×1`. The 82/85/90 values are **schema-broken** — `trust_score` is a 0-10 scale per `alpha_engine/trust_score.py:202`, but the column is `INT` (`mysql_trading_sync.py:77`) and at least 3 writes pushed 0-100-scale values in. So even the 17 "populated" rows include corrupt data; the truly schema-valid populated count is ~14.

### Top source_systems
| source_system | total | non-NULL | % |
|---|---:|---:|---:|
| multi_asset_copytrader | 18,058 | 0 | 0.00% |
| cta_replicator | 4,532 | 0 | 0.00% |
| non_crypto_consensus | 3,244 | 0 | 0.00% |
| prediction_market_agents | 2,488 | 4 | 0.16% |
| polymarket_whale_tracker | 2,179 | 0 | 0.00% |
| luxalgo_filters | 2,020 | 0 | 0.00% |
| copy_trader_polymarket | 1,852 | 0 | 0.00% |
| ml_crypto_predictor | 1,620 | 7 | 0.43% |
| short_dominant_engine | 1,617 | 0 | 0.00% |
| multi_asset_cot | 1,479 | 0 | 0.00% |
| ml_crypto_pred | 1,452 | 0 | 0.00% |
| alpha_engine | 1,056 | 0 | 0.00% |
| ml_strategy_reviver | 404 | 2 | 0.50% |

**No source-system writes `trust_score` at a rate > 0.5%.** Even the top three (`ml_strategy_reviver`, `ml_crypto_predictor`, `prediction_market_agents`) are essentially noise.

### By month
| month | total | non-NULL | % |
|---|---:|---:|---:|
| 2026-05 | 15,511 | 14 | 0.09% |
| 2026-04 | 24,532 | 3 | 0.01% |
| 2026-03 | 5,266 | 0 | 0.00% |
| 2026-02 | 306 | 0 | 0.00% |
| (null) | 2,733 | 0 | 0.00% |

**No month has ever exceeded 0.1% populated.** This is not a regression — the writer has never functioned end-to-end.

---

## 2. Code trace

### Where `trust_score` is **computed**
`alpha_engine/trust_score.py` — pure function `compute_trust_score(pick, ...)` returning 0-10 score + breakdown + label. Wired into `enrich_picks_with_trust_score(picks)` which mutates the list in-place.

### Where it is **called** in the production scanner
`alpha_engine/production_scanner.py:5755-5767` (post-scan enrichment) and `:6147-6153` (pre-write enrichment with comment "HC filter gate 7 requires trust_score >= 6. Without this, all active picks have trust_score=0 and HC filter returns 0 passes."). Both call sites operate on the **in-memory `active` list**.

### Where the writer is supposed to persist it
`alpha_engine/mysql_trading_sync.py:77` declares `trust_score INT`. The INSERT/UPSERT (`:94-:110`) includes it. The row-mapper (`:282`) reads `pick.get("trust_score")` from JSON.

### The break — **`alpha_engine/active_picks_sync.py:373-390`**
This is the live closer that writes terminal-status rows into `closed_picks.json` and `at_raw_picks` MySQL. The entry dict it builds is **hardcoded to 11 fields**: `id, symbol, direction, asset_class, strategy, entry_price, exit_price, pnl_pct, status, exit_reason, closed_at, resolved_at, _writer`. It does **NOT** carry forward `trust_score`, `elite_score`, `confidence`, or any enrichment from the source `OPEN` row. So every transition from OPEN -> WON/LOST loses the trust_score forever.

Additionally, `production_scanner.py`'s in-memory enrichment never round-trips back to the JSON file the syncer reads. JSON probe confirms it:

```
alpha_engine/data/active_picks.json: n=54  with_trust_score=0 (0.00%)
alpha_engine/data/closed_picks.json: n=992 with_trust_score=0 (0.00%)
```

So `mysql_trading_sync.py` faithfully syncs `None`, and the DB column is rightly NULL.

### Dead code suspicion
- `production_scanner.py:5755-5767` — enriches the in-memory `active` list, but the persisting writer for that batch (whichever feeds `mysql_trading_sync` or `active_picks_sync`) does not pick up the mutated dict. Effectively dead w.r.t. the DB column.
- `production_scanner.py:6147-6153` — even with the explicit "HC filter gate 7 requires trust_score >= 6" comment, enrichment happens but the next write path (closer) discards it.
- The 17 non-NULL rows in the DB likely came from a one-off `mysql_trading_sync.py` run with a JSON that happened to include `trust_score` (e.g. dev test) — not the steady-state pipeline.

---

## 3. Front-end check — quantify the gap

`audit_dashboard/template.html` cites:

- Line 875: "CRYPTO conf>=0.90 -> 14.4% WR; conf 0.50-0.60 -> **60.3% WR**" — this is a **confidence**-bucket stat (not trust_score). Reproducible from `confidence` column independently. **Not affected.**
- Line 877: EQUITY 0.85-0.90 -> 20% WR — also confidence, not trust_score. **Not affected.**
- HC overlay UI (`audit_dashboard/hc_filter.js:336`, `template.html:7220`, `:13013`): the **gate** `trust >= 6` reads `pick.trust_score`.
- `template.html:9496-9501`: **client-side recompute** — `p.trust_score = min(10, round((trust.w*7 + freshness + edge + regime) * 10) / 10)`. So for **active picks shown in the live table**, the JS overwrites whatever came from the JSON. The gate evaluates against the recomputed value, not the DB value. **The active-picks HC filter works** (independently of the DB column).
- BUT: the "Closed Picks" tab includes a `trust_score` column with delta (`:8875, :7905`) showing **at_issue vs current**. Both are NULL for ~100% of closed rows, so the column renders empty / "—" and the cited closed-book HC WR stats (per the sweep report: CRYPTO WR 60.3% on N=562, EQUITY 68.1%) **cannot be reproduced** from `trading_picks` because only 5 closed rows (0.013% of 38,852) have a non-NULL value.

**Gap quantification:**
- Claimed: "HIGH CONVICTION closed-book WR 60.3% over N=562 CRYPTO picks"
- Actual: N with non-NULL `trust_score` in closed crypto rows = **<5** (out of 15 total crypto-with-trust; most are `active`)
- The cited 60.3% is **either** computed from the confidence-band cohort (line 875 of template.html) and mis-labeled as "trust_score", **or** synthesized client-side from a different field and labeled as `trust_score` in marketing copy. Either way: **not reproducible from DB**.

---

## 4. Verdict

**(a) Trust_score writer is broken.** The closer (`alpha_engine/active_picks_sync.py:append_to_closed_picks_json` at line 353-398) constructs a fresh dict with 11 hardcoded fields and **drops every enrichment from the source row, including `trust_score`**. This is the root cause — every WON/LOST/TIME_EXIT row in the DB came through this writer and lost its trust_score.

Secondary cause: `production_scanner.py` enriches in-memory only; the subsequent JSON serialization (or `mysql_trading_sync.py` read of `active_picks.json`) does not preserve the mutated `trust_score`. JSON files on disk confirm 0% populated even for `active` rows.

---

## 5. Recommended minimum-risk fix

**One-line patch** at `alpha_engine/active_picks_sync.py:390` — add `trust_score` (and ideally `elite_score`, `confidence`) to the persisted entry by reading them from the source `t` dict:

```python
# After line 389 ("_writer": "active_picks_sync_live",)
"trust_score": t.get("trust_score"),
"elite_score": t.get("elite_score"),
"confidence":  t.get("confidence"),
```

Prerequisite: confirm `fetch_active_picks` (or whatever populates `t`) actually carries `trust_score` from the source `OPEN` row in `at_raw_picks`. If `at_raw_picks` itself doesn't have it, the fix has to land one layer upstream — at the writer that inserts into `at_raw_picks` in the first place. Likely candidate: the JSON-to-MySQL bridge in `mysql_trading_sync.py:282` is fine; what's broken is that **`active_picks.json` has 0% trust_score populated** (verified via direct read). So the upstream fix is: in `production_scanner.py`, persist the enriched `active` list back to `data/active_picks.json` after the `enrich_picks_with_trust_score()` call at line 6152.

**Two-line patch** at `alpha_engine/production_scanner.py:6153` (after the existing enrichment call):

```python
# Persist enrichment so downstream writers (mysql_trading_sync, active_picks_sync) see it
(SCRIPT_DIR / "data" / "active_picks.json").write_text(json.dumps(active, indent=2, default=str))
```

(adjust to whatever the file's existing save-pattern is — there is likely already an atomic-write helper).

### Interim UI mitigation (until backfill ships)
Until the writer fix lands AND a backfill of the 38,852 historical closed rows runs, the HC overlay's closed-book WR claims must be **removed or relabeled** as "based on active-picks live data, closed-book stats unavailable pending backfill". The current presentation implies the 60.3% / 68.1% figures are reproducible from `trading_picks`, which they are not.

### Backfill plan (separate PR)
Run `alpha_engine/trust_score.compute_trust_score` against each historical closed row (joining `at_issue_strat_fwd_wr` etc. from `pick_feature_store`) and `UPDATE trading_picks SET trust_score = ? WHERE id = ?`. Estimated 38,852 rows; ~10 min at 100 rows/sec.

---

## Appendix — files touched (read-only)

- `tools/db_env.py` (creds loader)
- `alpha_engine/trust_score.py` (compute function)
- `alpha_engine/production_scanner.py:5740-5770, 6140-6160` (enrichment call sites)
- `alpha_engine/mysql_trading_sync.py:77, 94-110, 282, 302, 422` (DB writer)
- `alpha_engine/active_picks_sync.py:353-398` (**root cause** — closer drops trust_score)
- `audit_dashboard/template.html:875, 1277, 7220, 8811, 9496-9502, 13013` (UI references + client-side recompute)
- `audit_dashboard/hc_filter.js:28, 336` (gate threshold + read)
- `alpha_engine/data/active_picks.json` (0% trust_score populated)
- `alpha_engine/data/closed_picks.json` (0% trust_score populated)
