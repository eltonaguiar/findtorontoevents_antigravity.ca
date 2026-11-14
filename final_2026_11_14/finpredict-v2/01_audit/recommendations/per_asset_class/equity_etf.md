# EQUITY + ETF remediation

**Scope:** EQUITY and ETF only, from the 2026-11-14 audit (`finpredict-v2_20261114-1602`).
**Audit clock:** 2026-11-14T16:05Z (Saturday). **Repo (read-only):** `finpredict-v2`.
**Rule:** every number below is copied from the audit evidence or recomputed from the cited code path. Unknown provenance is marked `UNVERIFIED` — not estimated.

Evidence used: `MASTER_AUDIT.md`, `sub/B_dashboard_freshness.md`, `sub/D_non_crypto.md`, `sub/E_statistical.md`.
Code verified in: `audit_trail/dashboard_generator.py`, `audit_trail/fetch_stock_prices.py`, `audit_trail/asset_classification.py`, `alpha_engine/asset_class.py`, `audit_dashboard/index.html`, `tools/sync_summary_picks_json.py`.

**Core diagnosis (one sentence):** the payload has no quote-provenance contract, so “0.00%” is an arithmetic identity (`current_price == entry_price`) presented as a live mark; on top of that, four different populations are all called “active” and three different cohorts are all called “EQUITY”, so the class tiles, EDGE badges and per-class PF cannot agree.

---

## Quick wins (P0)

All P0 items are ≤1 day, reversible, and do not change any trading signal or resolver output.

| ID | Fix | Audited problem | Primary location | Effort | Risk | Expected impact |
|---|---|---|---|---|---|---|
| **P0-1** | Stamp `quote_status` / `quote_source` / `quote_at` on every active pick; never treat a carried or cache price as a mark | 19/20 curated picks have `pnl_pct == 0.0`; 7/20 have `current_price == entry_price` bit-identical (`sub/B_dashboard_freshness.md:105`, `MASTER_AUDIT.md:140`); 86% of `active_raw` has no `current_price` (`sub/B_dashboard_freshness.md:195`) | `audit_trail/dashboard_generator.py:1681-1688`, `:1739-1755`, `:1821-1822` | S | Low — additive fields only, UI reads them defensively | Removes the false “flat market” reading for EQUITY (94 OPEN / 40 frozen) and ETF (30 OPEN / 15 frozen); exposes how many rows are actually quoted |
| **P0-2** | Weekend/holiday semantics: render `LAST CLOSE Fri 13 Nov` instead of a green live dot | Audit is a Saturday; all 10 ETF entries equal the Yahoo 2026-11-13 close to full float precision (`sub/D_non_crypto.md:228`); ADBE entry = 11-13 close exactly (`sub/D_non_crypto.md:120`) | `audit_dashboard/index.html:4453-4466`, `audit_dashboard/index.html:4509-4510`, `audit_dashboard/index.html:9134-9145`; `audit_trail/fetch_stock_prices.py:20-23` | S | Low — display-only; kill switch `QUOTE_BADGE_V2=0` | Users stop reading Friday’s close as a Saturday move; no more “live” dot when XNYS is closed |
| **P0-3** | `UNQUOTED` badge contract: hide PnL and show `—` / `UNQUOTED` when no live quote exists | 40/94 EQUITY OPEN rows are frozen at 0%/null and 15/30 ETF OPEN rows likewise (`MASTER_AUDIT.md:98-99`); client re-marks any non-null `current_price` as live (`audit_dashboard/index.html:4719-4732`) | `audit_dashboard/index.html:8889-8905` (PnL cell), `:8841-8845` (price cell), `:9134-9145` (Current cell) | S | Low — pure render guard | 0.00% disappears as a claim; the frozen cohort becomes countable instead of invisible |
| **P0-4** | Fix `summary_picks` WR denominator and canonical class labels | 8/11 classes report WR >100% (EQUITY **162.4%**, ETF **232.9%**, INDEX **1141.2%**) because `wins`/`losses` are counted over all rows with PnL while `resolved` counts terminal statuses (`sub/E_statistical.md:276-299`); `INDEX`/`MANAGED_FUTURES` pass through unnormalized (`tools/sync_summary_picks_json.py:18-22`) | `tools/sync_summary_picks_json.py:63-65`, `:161`; label map `:18-22` | S | Low — file is diagnostic, not a sizing source (`sub/B_dashboard_freshness.md:358`) | Eliminates arithmetically impossible class WR; removes `INDEX`/`MANAGED_FUTURES` from this surface (`STOCKS` in `audit_surface_truth` is handled in P1-5) |
| **P0-5** | Publish the active population split: `open_count` (raw OPEN) vs `curated_count` (`picks.active`) and `frozen_at_entry_count` | EQUITY tile says 2 active vs 94 raw OPEN; ETF says 10 vs 30 (`sub/D_non_crypto.md:24`); `performance.by_asset_class` says EQUITY 58 vs 2 curated (`sub/B_dashboard_freshness.md:228`) | `audit_trail/dashboard_generator.py:15400-15455` (`ac_breakdown`), `:16800-16815` (`final_active_picks`), `:17764-17772` (gate + floor); `:14331-14370` (per-class floor) | S | Low — additive summary fields; keep old keys | Ends the “2 vs 94 vs 58” dispute without changing which picks are shown; the operator sees curation vs inventory |
| **P0-6** | Symbol-authoritative ETF/BOND routing (do not trust a non-UNKNOWN upstream label blindly) | EQUITY contains ETFs `SPY`, `QQQ`, `XLE`, `XLK` (9 rows) (`sub/D_non_crypto.md:78`); ETF contains bond fund `VCSH` while `HYG/JNK/EMB/TLT` sit in BOND (`sub/D_non_crypto.md:80`, `sub/D_non_crypto.md:244`) | `audit_trail/dashboard_generator.py:3645-3680` (`_coerce_asset_class` trusts any stamped class), `:3565-3570` (canonical sets); `alpha_engine/asset_class.py:28-53` | S | Medium-low — changes class bucketing for a small set; ship behind `ASSET_CLASS_SYMBOL_AUTHORITY=1` | Moves equity ETFs out of EQUITY and VCSH out of ETF; makes “EQUITY” mean operating companies, not “anything with a ticker” |
| **P0-7** | Quarantine stale EQUITY zombies from the active/raw view (do not delete) | 82 EQUITY raw rows are >30d stale; 85 are `_auto_expired` (`sub/D_non_crypto.md:98-102`); the raw feed is append-only and still counts 3,377 `EXPIRED` rows as inventory (`sub/B_dashboard_freshness.md:120`, `:243`) | `audit_trail/dashboard_generator.py:9540-9617` (auto-expire), `:9773-9813` (post-gate staleness), `:17459-17525` (`active_raw` assembly) | S | Low — add `quarantined: true`, don’t remove; kill switch `ACTIVE_RAW_QUARANTINE=0` | Cuts the visible EQUITY raw count from 182 to the honest ~100 dated/open set and stops zombies feeding default sort/filters |

### P0-1 — Quote provenance contract

**Problem (audited):** `picks.active` shows `pnl_pct == 0.0` on 19/20 rows; 7 are exact `current_price == entry_price` and the other 13 differ only in float noise (`sub/B_dashboard_freshness.md:105`, `:226`). Audited per class: EQUITY 40/94 OPEN frozen, ETF 15/30 OPEN frozen (`MASTER_AUDIT.md:98-99`). The code currently writes `current_price` only inside the `fetched` hit path (`audit_trail/dashboard_generator.py:1739-1755`), and on a miss it `continue`s, leaving the upstream value — which is commonly entry — untouched (`:1752-1755`). A carried `current_price` is stored as a fallback (`:1681-1688`) but is never marked as carried.

**Verified location:** `audit_trail/dashboard_generator.py:1681-1688` (carried price accepted), `:1739-1755` (no-quote path leaves pick untouched), `:1821-1822` (only successful quotes update the row). Closed-pick whitelist that must also carry the new fields: `audit_trail/dashboard_generator.py:279-309`.

**Change (safe default):**
- In the enrichment loop, on a miss set:
  `p["quote_status"]="UNQUOTED"`, `p["quote_source"]="none"`, `p["quote_at"]=None`, and **do not change `pnl_pct`**. If `current_price == entry_price` and no fresh quote was fetched, set `p["_price_is_entry"]=True`.
- On a hit set `quote_status="LIVE"` (or `LAST_CLOSE`, see P0-2), `quote_source` from the fetcher (`stock_prices_cache` / `yfinance` / `fmp` / `binance` / `er_api`), `quote_at` from the quote’s own timestamp, and `quote_age_hours`.
- Add the four keys to `_CLOSED_PICK_KEEP_FIELDS` so closed rows do not silently drop them.
- Do the stamping in a **final pass over every published active pick** (immediately before `payload` serialization at `audit_trail/dashboard_generator.py:16953`), not only inside the enrichment loop, so the early returns at `audit_trail/dashboard_generator.py:1720-1721` and `:1730-1731` cannot skip it.
- Default-on; kill switch `QUOTE_STATUS_ENABLED=0` restores today’s shape.

**Expected impact:** EQUITY 40 and ETF 15 false-flat rows become explicit `UNQUOTED`; no return numbers change; EDGE/Track readers can exclude unquoted rows instead of treating 0.0 as a trade outcome.

**Risk + rollback:** additive keys, no consumer requires them. Rollback = flip env var; no data migration.

**Effort:** S.

**Validation:**
```bash
python3 - <<'PY'
import audit_trail.dashboard_generator as g
from datetime import datetime, timezone
picks = [{"symbol":"ADBE","asset_class":"EQUITY","entry_price":243.08,
          "current_price":243.08,"pnl_pct":0.0,"strategy":"x","direction":"LONG",
          "timestamp":"2026-11-14T12:44:52Z"}]
# monkeypatch fetchers to simulate a total quote miss, then assert provenance
g._fetch_equity_prices = lambda syms: {}
g._fetch_prices_with_failover = lambda syms: {}
out = g._enrich_live_pnl(picks)   # actual wrapper, dashboard_generator.py:1618
assert out[0]["quote_status"] == "UNQUOTED"
assert out[0]["quote_source"] == "none"
print("ok")
PY
python3 -m pytest tests/test_dashboard_payload_contract.py -q
```

### P0-2 — Weekend/holiday “LAST CLOSE” semantics

**Problem (audited):** the audit ran on Saturday 2026-11-14. Every curated ETF entry equals the Yahoo 2026-11-13 close exactly: USO 145.58, XLF 58.68, XLE 64.96, EFA 104.17, XLK 170.28, XLV 188.85, VLUE 189.18, XOP 184.80, KWEB 22.93, VCSH 77.25 (`sub/D_non_crypto.md:228`). ADBE active entry 243.08 equals the 11-13 close (`sub/D_non_crypto.md:120`). The server cache records only a file-level `updated_at` (`audit_trail/fetch_stock_prices.py:100-105`), and the dashboard reads it without any as-of check (`audit_trail/dashboard_generator.py:1505-1544`). The browser then applies those prices as `_livePrice` and returns early (`audit_dashboard/index.html:4453-4466`) and renders a green live dot (`:9139`).

**Verified location:** `audit_trail/fetch_stock_prices.py:20-23` (`last_price` or `previous_close`), `audit_trail/fetch_stock_prices.py:100-105` (only `updated_at`); `audit_trail/dashboard_generator.py:1505-1544` (cache accepted unconditionally); `audit_dashboard/index.html:4453-4466`, `audit_dashboard/index.html:4509-4510` (`regularMarketPrice` with no timestamp), `audit_dashboard/index.html:9139` (green live icon).

**Change:** carry the quote’s own time, not the fetch time.
- Prefer `meta.regularMarketTime` from the Yahoo v8 spark response (`audit_dashboard/index.html:4509`) and `data.updated_at` for the pre-baked tier (`audit_dashboard/index.html:4448`).
- Compute `quote_status` as `LIVE` only if the quote timestamp is inside an XNYS regular session and within N minutes; otherwise `LAST_CLOSE` with `quote_at` set to the session close.
- Render `LAST CLOSE Fri 13 Nov` (America/New_York) and a neutral grey marker; never the green live dot for `LAST_CLOSE`.
- Holiday calendar may be data-driven (`exchangeTimezoneName` / `currentTradingPeriod` already present in Yahoo `meta`); if absent, use a static XNYS holiday list in a small module. Default-on; kill switch `QUOTE_BADGE_V2=0`.

**Expected impact:** the entire Saturday panel stops implying live marks; the user sees a truthful as-of date for all 10 ETF and 2 EQUITY curated rows.

**Risk + rollback:** display-only change; the PnL arithmetic is unchanged. Rollback via env var.

**Effort:** S.

**Validation:**
```bash
# Simulate a closed-market quote and assert the badge text/state
npx playwright test tests/audit_verified_edge_active_picks.spec.ts --project="Desktop Chrome"
# manual: open /audit with a fixture date of 2026-11-14 and assert "LAST CLOSE" present
```

### P0-3 — `UNQUOTED` badge contract

**Problem (audited):** 0.00% is currently rendered as a real observation. The Current cell prints any non-null `current_price` (`audit_dashboard/index.html:9134-9145`), the PnL cell formats `0.0` as `0.00%` (`:8889-8905`), and the client re-applies server prices with only a `<0.00001` difference guard (`:4719-4732`).

**Verified location:** `audit_dashboard/index.html:9134-9145`, `:8889-8905`, `:8841-8845`, `:4719-4732`.

**Change:** one shared `quoteBadge(p)` helper:
```
UNQUOTED  -> Current: "—"; PnL: "—"; tooltip: "No live quote; not marked to market"
LAST_CLOSE-> Current: price + " (last close <date>)"; PnL: computed, muted, "as of close"
LIVE      -> today’s behaviour
STALE     -> price + "STALE <age>"
```
Gate the PnL arithmetic on `quote_status != "UNQUOTED"`; keep `pnl_pct` in the payload for auditability but do not present it. Add the badge to the Closed table via `buildClosedColsFromActiveList` (`audit_dashboard/index.html:9393-9408`) so closed rows do not regain a live-price column by accident.

**Expected impact:** the EQUITY 40 / ETF 15 frozen cohort becomes visibly unquoted; “0.00%” is no longer a performance claim in either tab.

**Risk + rollback:** render-only. Rollback = remove helper / env flag.

**Effort:** S.

**Validation:**
```bash
npx playwright test tests/audit_verified_edge_active_picks.spec.ts tests/audit_remote_tabs_no_errors.spec.ts --project="Desktop Chrome"
```

### P0-4 — `summary_picks` denominator + canonical labels

**Problem (audited):** `win_rate_pct` uses `wins / resolved` while `wins` and `losses` are counted across a larger PnL-bearing population. Results: EQUITY **162.4%** (1332 W / 2148 L vs resolved 820), ETF **232.9%** (170/183 vs 73), INDEX **1141.2%** (`sub/D_non_crypto.md:21`, `sub/E_statistical.md:288-299`). `_norm_class` only remaps `MEMECOIN`/`PENNY`; `INDEX` and `MANAGED_FUTURES` pass through unchanged (`tools/sync_summary_picks_json.py:18-22`). `STOCKS` is not present in `summary_picks`; its single tournament row is a separate `audit_surface_truth` issue (`sub/D_non_crypto.md:69`).

**Verified location:** `tools/sync_summary_picks_json.py:61-65` (three different populations in one query), `:161` (`100.0 * wins / resolved`), `:18-22` (label normalizer), `:123` (local JSON path uses the same normalizer).

**Change:**
- Compute `win_rate_pct = wins / (wins + losses)` and publish `resolved` separately; or restrict all three counters to terminal statuses.
- Replace `_norm_class` with `alpha_engine.asset_class.normalize_asset_class` (maps `stocks→equity`, `penny→equity`, `meme→crypto`); map `index→futures` to match `_ASSET_CLASS_HINTS` (`audit_trail/dashboard_generator.py:3370`); drop any remaining label not in the canonical 7; keep `raw_category` for audit.
- Keep the file diagnostic; add `"valid_for_sizing": false` to the payload so no consumer mistakes it for a trust surface.

**Expected impact:** no class can exceed 100% WR; `INDEX`/`MANAGED_FUTURES`/`STOCKS` disappear from this surface; EQUITY/ETF numbers become comparable to `recent_closed`.

**Risk + rollback:** the file is generated by `.github/workflows/audit-dashboard.yml:627` with `|| echo` (non-fatal), and no tab fetch was found (`sub/B_dashboard_freshness.md:358`). Rollback is a revert of one script.

**Effort:** S.

**Validation:**
```bash
python3 tools/sync_summary_picks_json.py --dry-run | python3 -c "
import json,sys
d=json.load(sys.stdin)
bad=[c for c in d['asset_classes'] if c['win_rate_pct'] is not None and c['win_rate_pct']>100]
assert not bad, bad
assert {c['asset_class'] for c in d['asset_classes']} <= {'CRYPTO','FOREX','EQUITY','ETF','BOND','FUTURES','COMMODITY'}
print('ok', d['n_asset_classes'])
"
```

### P0-5 — Population split (`open_count` vs `curated_count`)

**Problem (audited):** four populations are all presented as “active”: curated `picks.active` = 20, raw OPEN = 691, `performance.by_asset_class.active` = 158, `concentration_summary.total_active` = 263 (`MASTER_AUDIT.md:84-91`). Per class: EQUITY 2 curated vs 94 OPEN; ETF 10 vs 30 (`sub/D_non_crypto.md:24`). The counts differ because they are computed at different stages: `ac_breakdown` iterates `active + _closed_fallback` before final curation (`audit_trail/dashboard_generator.py:15400-15451`), while `picks.active` is `final_active_picks` after `_is_pre_score_active_candidate`, the direction-conflict filter (`:16800-16814`), `passes_active_gate` (`:14266-14296`) and the per-class visibility floor (`:14331-14370`, default 2 per class).

**Verified location:** `audit_trail/dashboard_generator.py:15400-15455`, `:16800-16815`, `:17764-17772`, `:14331-14370`; `audit_dashboard/index.html:9353-9373` (column defs) and `:9222-9227` (Age cell).

**Change:**
- Add to each class object: `open_count` (status OPEN in the raw snapshot), `curated_count` (published `picks.active`), `frozen_at_entry_count` (`quote_status=="UNQUOTED"`), `stale_over_30d_count`.
- Rename the `performance.by_asset_class.active` key to `pre_gate_open` (keep `active` as an alias for one release) and stamp `population: "pre_gate"`.
- In the tile tooltip show all four numbers; default sort remains curated.
- No pick admission changes.

**Expected impact:** the operator can reconcile 2 / 58 / 94 without reading JSON; the per-class visibility floor (`_below_gate`, `_visibility_floor`) becomes visible instead of looking like a real edge.

**Risk + rollback:** additive; old keys retained. Rollback = ignore new fields.

**Effort:** S.

**Validation:**
```bash
python3 -m pytest tests/test_audit_dashboard_payload.py tests/test_dashboard_payload_contract.py -q
# assert curated_count == len(picks.active) per class and open_count >= curated_count
```

### P0-6 — Symbol-authoritative ETF/BOND routing

**Problem (audited):** EQUITY contains `SPY`, `QQQ`, `XLE`, `XLK` (9 rows, e.g. `SPY cta_golden_cross_200`, `QQQ regime_terminal`) (`sub/D_non_crypto.md:78`). ETF contains `VCSH`, while `HYG/JNK/EMB/TLT/SHY` are BOND (`sub/D_non_crypto.md:80`, `:244`). The canonical `ETF_SYMBOLS` set omits `VCSH` and the crypto ETFs `IBIT`/`BITO`; the secondary classifier’s BOND regex includes broad equity ETFs `VTI|SCHB|ITOT` (`audit_trail/asset_classification.py:241-243`).

**Verified location:** `audit_trail/dashboard_generator.py:3645-3680` (`_coerce_asset_class` returns any non-UNKNOWN upstream label unchanged), `:3565-3570` (canonical sets consulted only after upstream hints); `alpha_engine/asset_class.py:28-35` (BOND set includes `VCSH`? — no: `VCSH` is absent), `:37-53` (ETF set: `SPY/QQQ/XLE/XLK/EFA/USO/XOP` present; `KWEB`, `VCSH`, `IBIT`, `BITO`, `VLUE` absent), `:55-60` (small EQUITY set), `:191-260` (category wins before symbol sets); `audit_trail/asset_classification.py:229-232` (ETF regex), `:241-243` (BOND regex includes `VTI|SCHB|ITOT`).

**Change:**
- Add to `ETF_SYMBOLS`: `VCSH` is **not** an ETF fix — move it to `BOND_SYMBOLS` (it is a short-term corporate bond fund); add `KWEB`, `VLUE`, `IBIT`, `BITO` to `ETF_SYMBOLS`, plus a `crypto_etf` tag for `IBIT`/`BITO` (still class ETF).
- Remove `VTI|SCHB|ITOT` from `_BOND_PATTERNS` and route them to ETF.
- In `_coerce_asset_class`, if the symbol is in a canonical ETF/BOND set, let the symbol override a stamped `EQUITY`/`ETF` label; keep the upstream label in `asset_class_upstream` for audit.
- Ship behind `ASSET_CLASS_SYMBOL_AUTHORITY=1` (default on for ETF/BOND symbols only), kill switch documented.

**Expected impact:** EQUITY stops carrying 9 ETF rows; ETF stops carrying a bond fund; `IBIT`/`BITO` cannot silently fall into CRYPTO/unknown; the EQUITY closed cohort drops below 738 only because rows move class, not because rows are deleted (state this in the release note).

**Risk + rollback:** class-key moves affect per-class PF and counts. Rollback = env var to 0; historical rows are not rewritten.

**Effort:** S.

**Validation:**
```bash
python3 -m pytest tests/test_asset_class.py tests/test_asset_class_crypto_guard.py tests/test_outcome_resolver_asset_class_persist.py -q
python3 - <<'PY'
from alpha_engine.asset_class import normalize_asset_class
cases={"SPY":"etf","QQQ":"etf","XLE":"etf","XLK":"etf","VCSH":"bond","IBIT":"etf","BITO":"etf","VTI":"etf"}
for s,want in cases.items():
    got=normalize_asset_class({"symbol":s,"category":"equity"})
    assert got==want,(s,got,want)
print("ok")
PY
```

### P0-7 — Quarantine stale EQUITY zombies

**Problem (audited):** EQUITY `active_raw` = 182 rows: 94 OPEN, 85 EXPIRED, 3 SL_HIT; 82 are >30d stale (45%); 85 are `_auto_expired` with `expired_no_pnl` (`sub/D_non_crypto.md:98-102`). The raw payload also contains 3,377 `EXPIRED` rows globally (`sub/B_dashboard_freshness.md:120`) and 2,838 zombies age>30d with `pnl==0` (`:255`).

**Verified location:** `audit_trail/dashboard_generator.py:9540-9617` (auto-expire sets `EXPIRED` and appends to closed), `:9773-9813` (post-gate staleness removes from `active` but does not quarantine the raw snapshot), `:17459-17525` (`active_raw` assembly).

**Change:** in the raw snapshot assembly, add `quarantined: true`, `quarantine_reason: "auto_expired"|"stale_30d"`; exclude quarantined rows from the default raw sort/filter and from any count labelled “open”. Keep them retrievable behind `?include_quarantined=1`. Default-on; kill switch `ACTIVE_RAW_QUARANTINE=0`.

**Expected impact:** EQUITY raw view drops from 182 to the honest dated/open set (~100); the 85 auto-expired rows stop being counted as inventory. No rows deleted.

**Risk + rollback:** counts change; some downstream consumers read `active_raw` without a filter. Mitigate by adding `quarantined` and keeping row order stable; rollback = env var.

**Effort:** S.

**Validation:**
```bash
python3 -m pytest tests/test_dashboard_payload_contract.py -q
# after build: assert no row with quarantined=true is counted by summary.open_count
```

---

## Structural (P1)

| ID | Fix | Audited problem | Primary location | Effort | Risk | Expected impact |
|---|---|---|---|---|---|---|
| **P1-1** | One canonical classifier used by generator, sync, resolver and build scripts | Four class inventories in one payload (7/9/11/8 classes); `STOCKS`, `INDEX`, `MANAGED_FUTURES`, `SPORTS`, `PENNY_STOCK`, `MEME` are non-canonical emissions (`sub/D_non_crypto.md:20`, `:43-53`); `COMMODITY` is 44/44 `=F` futures (`sub/D_non_crypto.md:380`) | `alpha_engine/asset_class.py:102-120`, `:191-260`; `audit_trail/dashboard_generator.py:3392-3404`, `:3645-3680`; `audit_trail/asset_classification.py:224-260` | M | Medium — class counts shift; requires a one-release dual-write of `asset_class_raw` | Single taxonomy; no more “INDEX vs EQUITY” phantom surfaces |
| **P1-2** | Rebuild EDGE from a windowed, policy-clean ledger with normalized keys and explicit `n` | EDGE = 0/20 populated; 19/20 active strategies have n=0 closed trades in `recent_closed`; only `etf_faber_tactical` has n=1 (`sub/B_dashboard_freshness.md:180`); `recent_closed` is capped at 3,500 (`audit_trail/dashboard_generator.py:273`) and its EQUITY/ETF median close age is 120.1d (`sub/B_dashboard_freshness.md:129-130`) | `audit_dashboard/index.html:2955-3113` (`buildVerifiedEdgeIndex`), `:3125-3180` (`getVerifiedTier`), `:2972-2976`/`:3132-3134` (exact keys), `:3047-3049` (normalized fallback only for TRACK); `tools/build_pf_registry.py:1114-1116` | M | Medium — badge semantics change; keep old badge as `EDGE_LEGACY` for one release | EDGE becomes an actual statistic with `n`, not a blank cell or an n=1 accident |
| **P1-3** | Apply identical cohort windows/gates to active and closed; publish both windows | The staleness filter is applied to `active` only (`audit_trail/dashboard_generator.py:9773-9813`); `recent_closed` keeps 2,221 rows >30d (`sub/B_dashboard_freshness.md:135`); 738 EQUITY / 567 ETF closes have median age 120.1d (`MASTER_AUDIT.md:245-249`); open-pick survivorship is 63% (`sub/E_statistical.md:243-248`) | `audit_trail/dashboard_generator.py:9773-9813`, `:6948-7078`, `:14116-14197`, `:16863-16872` (`valid_closed_picks`) | M | Medium-high — changes every derived WR/PF; must be dual-published, not silently replaced | No look-ahead/survivorship regression: a filter that excludes an active row must exclude its closed twin, and “recent” means one window for both |
| **P1-4** | Quote pipeline v2: per-symbol `as_of`, XNYS session calendar, stale-cache rejection, full symbol universe | Cache read ignores `updated_at` (`audit_trail/dashboard_generator.py:1505-1544`); `fetch_stock_prices.py` writes only a file-level timestamp (`:100-105`); `stock_prices.json` covers only 1/2 active EQUITY and 2/10 active ETF symbols (`sub/B_dashboard_freshness.md:227`) | `audit_trail/fetch_stock_prices.py:9-56`, `:100-105`; `audit_trail/dashboard_generator.py:1505-1600`; `audit_dashboard/index.html:4368-4379` (`_KNOWN_STOCKS` excludes `USO,KWEB,EFA,XLV,VLUE,VCSH,XOP`) | M | Medium — new fetcher paths can rate-limit; build behind a cache-first, fail-closed contract | Every EQUITY/ETF row has a usable quote or an explicit `UNQUOTED`; no stale cache can masquerade as fresh |
| **P1-5** | Remove/relabel phantom classes on every surface | `STOCKS` appears only in `audit_surface_truth.tournament.closed_by_class` (n=1); `INDEX` appears only in `summary_picks` (resolved 17, WR 1141.2%); `MANAGED_FUTURES` has 0 resolved and no picks (`sub/D_non_crypto.md:69-71`); `SPORTS` is 2 rows filtered client-side (`:72`) | `tools/sync_summary_picks_json.py:18-22`; `audit_trail/dashboard_generator.py:6745-6755`, `:9716` | M | Low-medium — consumers may key on the old labels; dual-publish one release | Class list matches `alpha_engine/asset_class.py`; no phantom class can be cited as a cohort |
| **P1-6** | ETF sample-size gate: do not present PF/WR as edge below Tier-2 n | ETF policy-clean n=15, WR 73.33%, PF 1.8358, z=+1.81, does **not** survive the 9-class Bonferroni threshold (`sub/E_statistical.md:208`, `:212`); the same payload shows daily-vs-intrabar PF inflation 84.99× (`sub/D_non_crypto.md:242`) | `audit_trail/dashboard_generator.py:11687-11688` (Tier-2 floor `n>=100`), `:6331-6333`; `audit_dashboard/index.html:3115-3180` (badge thresholds) | S/M | Low — display policy only | ETF stops looking like the only profitable class; `INSUFFICIENT_N` is shown instead of a headline PF |
| **P1-7** | EQUITY closed-ledger integrity pass: impossible entries + stale resolves | 2 impossible AAPL entries: 2026-11-13 entry 315.9799 vs day range 355.75–360.83 (−11.2% below the low); 2026-11-03 entry 316.22 vs 325.33–334.50 (`sub/D_non_crypto.md:115-117`); 649/738 EQUITY closes are >30d old (`sub/D_non_crypto.md:107`) | `audit_trail/universal_pick_resolver.py:693-722` (`_per_pick_price`), `:888-909` (`check_tp_sl`), `:1297-1506` (resolve loop); `audit_trail/dashboard_generator.py:4850` (`_is_valid_resolved_pick`) | M | Medium-high — resolver changes affect realized outcomes; do not retro-edit history | Suspicious entries are flagged/excluded from class stats rather than silently counted; does not rewrite past rows |

### P1-2 — Where EDGE is computed and why 19/20 strategies have n=0

**Verified code path:**
- `audit_dashboard/index.html:2955-2956` — `var closed = (D && D.picks && D.picks.recent_closed) || [];` (the only source).
- `:2972-2976` — combo key is the literal `strategy + '||' + symbol`; `:2976` builds the strategy key from the literal strategy string.
- `:3027` — VERIFIED requires the exact strategy key with `n>=30`, `WR>=55`, `PF>=1.5`; `:3020` GOLDEN requires the exact combo key.
- `:3047-3049` — the normalized (`_normStratKey`) and source-system fallbacks are explicitly **only for TRACK rendering**; they do not feed GOLDEN/VERIFIED.
- `:3125-3134` — `getVerifiedTier` looks up `goldenCombos[s+'||'+sym]` and `verifiedStrats[s]` with the literal strings.

**Why the active universe has no history there:** the curated active rows come from fresh emitters (`ueps`, `regime_terminal`, `etf_dual_momentum`, `etf_sector_momentum`, etc.) whose closed history is either in `pf_registry` or in rows outside the 3,500-row `recent_closed` cap (`audit_trail/dashboard_generator.py:273`, `:6948-7078`). The published closed feed is dominated by old rows — EQUITY and ETF median close age 120.1d (`sub/B_dashboard_freshness.md:129-130`) — so a freshly named strategy has `n=0` even when the same economic strategy has history under a different name or in the registry.

**Change:** build the index from `pf_registry.by_asset_class_strategy_*` (or a windowed, policy-clean closed slice), keyed by both the literal and `_normStratKey` form; require a minimum `n` (config, default 10) before any badge; store `n`, `wr`, `pf`, `window_start`, `window_end` on the badge; if `n` is below threshold render `EDGE n<10` rather than blank.

**Expected impact:** EDGE goes from 0/20 populated to an honest, sample-aware badge; users can see that most active strategies have no closed history instead of reading a blank as a UI bug.

**Risk + rollback:** badges can become more conservative (fewer GOLDEN). Keep `EDGE_MODE=legacy|v2`; default `legacy` for one release, then flip.

**Effort:** M.

**Validation:**
```bash
npx playwright test tests/audit_verified_edge_active_picks.spec.ts tests/audit_remote_tabs_no_errors.spec.ts --project="Desktop Chrome"
# new unit test: tests/test_edge_index_windowed.py
python3 -m pytest tests/test_edge_index_windowed.py -q
```

### P1-3 — No look-ahead / survivorship regression (mandatory rule)

**Problem (audited):** the active staleness filter runs at `audit_trail/dashboard_generator.py:9773-9813`; the closed feed is then built from `all_closed_including_expired` (`:9647`) and capped at 3,500 (`:273`, `:6948-7078`) with no equivalent window. 2,221 of 3,500 closed rows are >30d old (`sub/B_dashboard_freshness.md:135`); 63.2% of picks never resolve (`sub/E_statistical.md:243-248`); the policy-clean registry drops 1,777 rows for policy exclusions (`sub/E_statistical.md:234`).

**Rule to implement:** any new filter that can hide an active row (staleness, quote status, class gate, dedup, conflict resolution) must be applied to the closed comparison cohort with the same predicate and window, and both counts must be published: `active_eligible`, `active_published`, `closed_eligible`, `closed_published`, plus `window_start`/`window_end`. If the cohorts cannot be made identical, the statistic must be labelled `mixed_cohort` and must not be used for EDGE or class PF.

**Where:** `audit_trail/dashboard_generator.py:9773-9813` (active), `:6948-7078` (closed), `:14116-14197` (non-crypto stats), `:16863-16872` (summary counts). Add a shared `_cohort_window()` helper and assert equality in a test.

**Impact:** prevents the classic failure where a “recent” EDGE is computed from 120-day-old closes while the active row is 3 hours old.

**Risk + rollback:** dual-publish first; do not replace old keys in the same release.

**Effort:** M.

**Validation:**
```bash
python3 -m pytest tests/test_dashboard_payload_contract.py tests/test_asset_class_edge_invariants.py -q
# new test asserts: for every active row excluded by predicate P, the closed
# cohort also excludes rows matching P, or the metric is stamped mixed_cohort
```

### P1-4 — Quote pipeline v2 (as-of + calendar + universe)

**Problem (audited):** `stock_prices.json` is 1.91h fresh but covers only 1/2 active EQUITY and 2/10 active ETF symbols (`sub/B_dashboard_freshness.md:227`); the file has only one `updated_at` for all symbols (`audit_trail/fetch_stock_prices.py:100-105`); the generator never checks it (`audit_trail/dashboard_generator.py:1505-1544`); the browser `_KNOWN_STOCKS` set excludes 7 of the 10 curated ETFs (`audit_dashboard/index.html:4368-4379`).

**Change:**
1. `fetch_stock_prices.py`: write `{"prices": {"SPY": {"price":..., "as_of":"...", "session":"2026-11-13"}}}` (or a parallel `as_of` map for backward compatibility), populated from yfinance metadata.
2. Generator: reject cache entries older than `QUOTE_CACHE_MAX_HOURS` (default 24h) and mark `quote_status="STALE"` instead of silently using them.
3. Add all curated ETF symbols to the browser fetch set (or make the set data-driven from `asset_class=="ETF"` + canonical ETF symbols), so the client tier does not depend on a hardcoded list.
4. Add the XNYS session/holiday helper and use it to classify `LIVE` vs `LAST_CLOSE`.

**Expected impact:** 10/10 ETF and 2/2 EQUITY curated rows have a usable quote or an explicit `UNQUOTED`; Friday’s close is labelled as such; stale cache cannot be presented as fresh.

**Risk + rollback:** new fetcher path may rate-limit; keep tier order and cache-first behaviour, fail closed to `UNQUOTED`. Rollback = revert the module.

**Effort:** M.

**Validation:**
```bash
python3 -m pytest tests/test_asset_class_freshness_report.py tests/test_dashboard_payload_contract.py -q
python3 - <<'PY'
import json
d=json.load(open("audit_trail/data/stock_prices.json"))
assert "updated_at" in d
for sym, v in list(d.get("prices", {}).items())[:5]:
    assert isinstance(v, dict) and v.get("as_of"), (sym, v)
print("ok")
PY
```

### P1-5 — Phantom class elimination

**Problem (audited):** `STOCKS` appears only in `audit_surface_truth.tournament.closed_by_class` (n=1, WR 1.0); `INDEX` only in `summary_picks` (resolved 17, wins 194, WR 1141.2%); `MANAGED_FUTURES` total 2 / resolved 0; `SPORTS` is 2 rows filtered client-side (`sub/D_non_crypto.md:69-72`). Canonical maps are `stocks→equity`, `penny→equity`, `meme→crypto` (`alpha_engine/asset_class.py:102-109`).

**Change:** in every payload writer, run the canonical normalizer and drop classes not in `_LOWER_TO_UPPER` (`alpha_engine/asset_class.py:111-120`); keep `asset_class_raw`; for `SPORTS`, use a separate `is_sports` flag rather than an asset class. Add a payload invariant test that the class set is a subset of the canonical 7.

**Impact:** one class list everywhere; no phantom cohort can be quoted.

**Risk + rollback:** consumers keyed on `STOCKS`/`INDEX` break; dual-publish one release.

**Effort:** M.

**Validation:** `python3 -m pytest tests/test_dashboard_payload_contract.py tests/test_audit_dashboard_payload.py -q`.

### P1-6 — ETF significance policy

**Problem (audited):** ETF policy-clean n=15, WR 73.33%, PF 1.8358, z=+1.81; the 9-class Bonferroni threshold is |z|=2.773, so it does not survive (`sub/E_statistical.md:208`, `:212`). The same payload’s `intrabar_daily_divergence` reports PF inflation 84.99× for ETF (`sub/D_non_crypto.md:242`). The project’s own Tier-2 floor is n≥100, WR≥50, PF≥1.5 (`audit_trail/dashboard_generator.py:11687-11688`).

**Change:** suppress class-level PF/WR headline when `n < 100`; show `INSUFFICIENT_N (n=15)` and keep the raw numbers in a tooltip; do not let a class with n<100 feed EDGE, readiness or “best class” ordering. Applies to BOND (n=1), FUTURES (n=13), COMMODITY (n=14), ETF (n=15). Default-on; kill switch `CLASS_MIN_N_POLICY=legacy`.

**Impact:** removes the false impression that ETF is the profitable class; aligns tile, badge and registry.

**Risk + rollback:** more conservative display; no data change.

**Effort:** S/M.

**Validation:** `python3 -m pytest tests/test_asset_class_health_n_guard.py tests/test_audit_dashboard_payload.py -q`.

### P1-7 — EQUITY closed-ledger integrity

**Problem (audited):** two impossible AAPL entries: `vt_equity_two_day_rsi_reversal::AAPL::2026-11-13` entry 315.9799, exit 320.7652, marked WON, closed 2 minutes later, against a day range 355.75–360.83; a second AAPL pick dated 2026-11-03 entry 316.22 against 325.33–334.50 (`sub/D_non_crypto.md:115-117`). 649/738 EQUITY closes are >30d old; `current_price` is null on 738/738 closed rows (`sub/D_non_crypto.md:107-108`). The resolver is entry-anchored and SL-first (`audit_trail/universal_pick_resolver.py:614-690` per `sub/E_statistical.md:265-268`), so a bad entry can produce a fake TP.

**Change:**
- At resolve time, reject an entry outside the entry-day `[low, high]` (or prior session) with `_entry_impossible=True`; exclude from class PF but keep for audit.
- Add a daily backfill report that samples 100 closed EQUITY rows per day and re-checks entry/exit against the same OHLC source used for resolution.
- Do not retro-edit historical statuses; quarantine them (`integrity_excluded`) and publish both `raw` and `clean` counts.
- Default flag `EQUITY_ENTRY_SANITY=1`; kill switch.

**Impact:** the two impossible AAPL rows stop contributing to EQUITY’s +238.4% sum; the class view becomes defensible without rewriting history.

**Risk + rollback:** may reduce EQUITY n slightly; no live signal change. Rollback = flag.

**Effort:** M.

**Validation:** `python3 -m pytest tests/test_outcome_resolver_asset_class_persist.py tests/test_asset_class_edge_invariants.py -q` plus a new `tests/test_equity_entry_sanity.py`.

---

## Do-not-do

1. **Do not backfill `current_price` or `pnl_pct`** from `entry_price` or from a stale cache to make the display non-zero. That converts an identity into a fabricated observation (see `audit_trail/dashboard_generator.py:1681-1688`).
2. **Do not delete the 2,221 >30d closed rows.** Window or label them; deletion destroys the audit trail and hides the survivorship problem (`sub/B_dashboard_freshness.md:135`).
3. **Do not merge ETF into EQUITY or BOND into ETF** to reconcile counts. That makes the taxonomy worse and breaks the canonical map (`alpha_engine/asset_class.py:102-109`).
4. **Do not quote ETF PF 1.84 as an edge.** n=15, z=+1.81, fails the 9-class Bonferroni threshold (`sub/E_statistical.md:208`, `:212`); the same payload reports an 84.99× daily-vs-intrabar PF inflation (`sub/D_non_crypto.md:242`).
5. **Do not apply a new staleness/quote/quality filter only to `picks.active`.** The identical predicate must run on the closed comparison cohort, or the resulting WR/PF is a survivorship artifact (`audit_trail/dashboard_generator.py:9773-9813` vs `:6948-7078`).
6. **Do not change TP/SL ordering, resolver anchors, or retro-edit outcomes** as part of a display/classification fix. Those are P1-7 and require a separate validation path (`audit_trail/universal_pick_resolver.py:614-690`).
7. **Do not render a green “live” dot on a closed market.** Friday’s close is not Saturday’s live price (`audit_dashboard/index.html:9139`).
8. **Do not compute EDGE from the 3,500-row capped feed and call it “verified”.** It is a capped, 120-day-median slice (`audit_trail/dashboard_generator.py:273`, `sub/B_dashboard_freshness.md:129-130`).

---

## UNVERIFIED

- **Headline EQUITY n=8, WR 75%, PF 8.86** (`MASTER_AUDIT.md:238`): the aggregator that produces this exact cohort was not located in repo source; it exists only in the audited live payload. All code paths traced here produce n=738 (`recent_closed`), n=759 (`non_crypto_performance`) or n=461 (`pf_registry`). Do not “fix” the n=8 number until the producer is identified.
- **`IBIT`/`BITO` live presence in ETF.** The audit prompt references crypto ETFs in ETF, but the archived dump used here does not list them in `picks.active`/`active_raw`, and neither `alpha_engine/asset_class.py` nor `audit_trail/asset_classification.py` contains those symbols. The classification gap is verified; the live row count is not.
- **`stock_prices.json` as-of semantics.** The file has only a file-level `updated_at` (`audit_trail/fetch_stock_prices.py:100-105`); whether each value is Friday’s close or an intraday print on any given run is not recorded.
- **Weekend/holiday workflow ordering.** Whether `fetch_stock_prices.py` runs on weekends and whether the cache is rebuilt before the dashboard is not traced in this pass; no XNYS calendar/helper exists in the audited source.
- **Exact definition of “frozen”.** The audit uses “current==entry or null” (`MASTER_AUDIT.md:95-99`); there is no `frozen` flag in the code. P0-1/P0-3 define an explicit, testable status instead.
- **EQUITY 82 stale / 94 OPEN / 40 frozen and ETF 30 OPEN / 15 frozen** are copied from `sub/D_non_crypto.md:98-102` and `MASTER_AUDIT.md:98-99`; they were not recomputed from a fresh live payload in this planning pass.
- **Yahoo `meta.regularMarketTime` availability through the public CORS proxies** (`api.allorigins.win`, `corsproxy.io`) is not verified; the fallback is the file-level `updated_at` from the pre-baked tier.
- **Exact source of `STOCKS` in `audit_surface_truth.tournament.closed_by_class`.** The label is verified in the payload (`sub/D_non_crypto.md:69`), but the DB/view that emits it was not traced.
