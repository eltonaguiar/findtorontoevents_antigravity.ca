# CRYPTO + COMMODITY remediation

**Scope:** CRYPTO and COMMODITY only, from the 2026-11-14 audit (`finpredict-v2_20261114-1602`).
**Audit clock:** 2026-11-14T16:05Z (Saturday). **Repo (read-only):** `finpredict-v2`. **Live payload:** `generated_at = 2026-11-14T14:30:07Z`, `repo_sha = 1b2c98e`.
**Rule:** every number is copied from the audit evidence, or recomputed from the archived payload with the counting rule shown. Line numbers were verified with `grep -n`/`read` against this worktree. Unknown provenance is marked `UNVERIFIED`.

Evidence used: `MASTER_AUDIT.md`, `sub/B_dashboard_freshness.md`, `sub/C_crypto.md`, `sub/D_non_crypto.md`, `sub/E_statistical.md`, `raw/live_data_dashboard_data.json`, `raw/pf_registry.json`, `raw/money_ready_verdict.json`, `raw/audit_surface_truth.json`.
Code verified in: `audit_trail/dashboard_generator.py`, `audit_dashboard/template.html`, `alpha_engine/{asset_class,contract_type,inverse_strategies,inverse_loser_mutations,prediction_market_consensus,kalshi_signals,production_scanner,active_picks_sync}.py`, `genome/mape_evolver.py`, `tools/sync_summary_picks_json.py`, `schema-baseline.sql`.

**Core diagnosis (one sentence):** the payload has no quote-provenance contract, so an unquoted row is published as `current_price == entry_price` and `pnl_pct = 0.0`; CRYPTO and COMMODITY then add three more problems — an append-only inverse-mutation zombie factory, zero-entry rows that are authorised by the ingest filter, and a display-only COMMODITY bucket whose 44 rows are all `commodity_future` contracts that never get re-quoted.

**Recomputed inventory (from `raw/live_data_dashboard_data.json`, `generated_at 14:30:07Z`):**

| Population | Rows | Quoted (price differs from entry) | Exact `current==entry` | `current_price` null |
|---|---:|---:|---:|---:|
| CRYPTO `active_raw` | 3,577 | 68 of 402 OPEN (16.9%) | 5 OPEN | 329 OPEN (81.8%) |
| CRYPTO `active_raw` EXPIRED | 3,100 | — | 154 | 2,841 (C:53) |
| COMMODITY `active_raw` | 44 | 9 (1 real `SL_HIT` + 8 OPEN prior-session marks) | 3 | 32 (72.7%) |
| All `active_raw` OPEN | 691 | 175 (25.3%) | 31 | 485 (70.2%) |

Counting rule: `quoted` = `current_price > 0` and `abs(current-entry)/entry >= 1e-9`; `exact` = same but `< 1e-9`; `null` = `current_price <= 0`. These reproduce the audit's 334/402 crypto frozen count (329 null + 5 exact) and the 3,851 unique IDs / 4,148 rows (MASTER_AUDIT:110).

---

## Quick wins (P0)

All P0 items are ≤1 day, additive/reversible, and do not change entry prices, resolver output, or any trading decision.

| ID | Fix | Audited problem | Primary location | Effort | Risk | Expected impact |
|---|---|---|---|---|---|---|
| **P0-1** | Quote-provenance contract: stamp `quote_status` / `quote_source` / `quote_at` / `quote_age_hours` on **`picks.active` and `picks.active_raw`**; never leave an identity price unmarked | 19/20 curated picks are `pnl_pct == 0.0`; XRP and BTC are exact `current == entry` (0.9842 / 66,300) while Binance showed +1.28% / +0.95% at 16:03Z (C:100-101); 485/691 OPEN raw rows have no price | `audit_trail/dashboard_generator.py:1618-1846` (miss path `:1739-1755`), final pass at `:16953` and `:17481-17485` | S | Low — additive fields; UI reads defensively | XRP/BTC stop rendering 0.00%: a re-quote shows the real mark, and a miss renders `UNQUOTED`. The 485 null OPEN rows become countable instead of invisible |
| **P0-2** | `UNQUOTED` / `STALE` / `LAST CLOSE` render contract in the active table (PnL cell, status cell, Current cell, Age cell) | The PnL cell prints `+0.00%` for any `pnl_pct == 0` (`audit_dashboard/template.html:5075`, `:8889-8905`); the status cell prints `FLAT` (`:8883-8887`); the Current cell has a green "live" dot whenever `_livePrice` exists (`:9134-9145`) | `audit_dashboard/template.html:8889-8905`, `:8883-8887`, `:9134-9145`, `:9222-9227` | S | Low — pure render guard; flag `QUOTE_BADGE_V2=0` | 0.00% stops being a claim. Frozen rows read `UNQUOTED`, clock-expired rows read `STALE`, weekend futures read `LAST CLOSE Fri 13 Nov` |
| **P0-3** | Clock-expiry must not publish `pnl_pct = 0.0`: tag `resolution_kind="clock_expired"`, keep the price, null the mark | 3,377 `EXPIRED` rows are inside `active_raw`, 3,099 with null price and 173 with `current == entry` (B:120, :243). The April fossils `CL=F 112.05999755859375`, `GC=F 4702.7001953125`, `ZN=F 111.015625` (timestamp `2026-04-03T00:06:41Z`) carry `exit_reason="STALE (auto-expired >5414h)"`, `_auto_expired=True`, `expired_no_pnl=True` | `audit_trail/dashboard_generator.py:9596-9605` (auto-expire), `:9618-9650` (metric split), `:9722-9723` (entry=0 allowed) | S | Low — these rows are already excluded from metrics by `_is_valid_resolved_pick()` (`:4848-4864`); this only stops the false 0.00% display | The 16 stale COMMODITY rows and 2,995 auto-flagged crypto EXPIRED rows are labelled STALE with no PnL claim; the April CL=F/GC=F prices stop reading as a flat April trade |
| **P0-4** | Raw-inventory truth block: add `picks.active_raw_open`, `summary.active_raw_counts`, and duplicate-ID tags; keep `active_raw` untouched | 4,148 raw rows / 3,851 unique IDs (MASTER_AUDIT:110); 218 duplicate IDs and 55 IDs conflicting across ledgers (C:172); the tile says "20 of 4,148" (`audit_dashboard/template.html:5628`) although only 691 are OPEN | `audit_trail/dashboard_generator.py:17481-17485`, `:17537-17538`; `audit_dashboard/template.html:5628`, `:5122-5125`, `:10274-10277` | S | Low — additive counts + badges; no row removal | Tile becomes "20 of 691" with `expired=3,377`, `unpriced=485`, `zero_entry=85`, `dup_id_groups`, `dup_id_rows` visible; the 44-row COMMODITY "inventory" is split 27 OPEN / 16 EXPIRED / 1 SL_HIT |
| **P0-5** | Stop emitting zero-entry rows: `prediction_market_consensus` must keep `None` (not `0.0`); `mape_evolver` must not emit tradeable picks without an entry; dashboard tags `_invalid_entry` | 85 zero-entry rows: mape_evolver 28, genetic_programmer 21, ensemble_evolver 10, neat_neural 8, hyperparam_dna 8, genome 4, failure_evolver 3, prediction_market_consensus 3 (C:166). One is **XRPUSDT SHORT entry 0.0** at 13:54:51Z (recomputed) | `alpha_engine/prediction_market_consensus.py:160`, `:479`, `:588-591`; `genome/mape_evolver.py:497-511`; `audit_trail/dashboard_generator.py:9722-9723` | S | Low–Medium — changes one emitter's null-vs-zero contract; gate already rejects `entry <= 0` | No new `entry=0.0` rows; the XRP phantom disappears from the raw inventory. Existing 85 rows get a `NO ENTRY` badge, not a PnL |
| **P0-6** | Fix `summary_picks` WR denominator (same-predicate numerator/denominator) | COMMODITY reports **240.2%** WR (3,476 W / 3,466 L vs `resolved=1,447`); CRYPTO 98.3%; 8/11 classes >100% (E:292-299). Root cause `wins`/`losses` count all marked rows, `resolved` counts terminal statuses | `tools/sync_summary_picks_json.py:63-65`, `:161` | S | Low — diagnostic file, not a sizing source (B:358) | Impossible WR disappears; COMMODITY/CRYPTO publish a computable `wins / (wins + losses)` with the old `resolved` kept as a separate field |
| **P0-7** | Quarantine the inverse-mutation zombies **in the view** (not in the file): `active_raw_open` excludes EXPIRED; tag `_quarantined` for `inverse_mutations` rows older than 7 d | 2,267 `inverse_mutations` / `inverse_luxalgo_confluence` rows: 2,231 EXPIRED, 2,255 `pnl 0`, 2,254 null price; 20 symbols × 167 days, one per symbol per day since 2026-05-23 (C:152-160). They are 71% of crypto null-price rows | Dashboard tag at `audit_trail/dashboard_generator.py:17481-17485`; emitter fix is P1-2 | S | Low — display tag only; `INVERSE_RAW_QUARANTINE=0` rolls back | Default "Show All Picks" uses `active_raw_open`, which excludes the 2,231 EXPIRED inverse rows as part of the 3,377 EXPIRED rows dropped from the default view; the crypto raw view no longer reads as a 3,577-row book. The 26 OPEN + 7 SL_HIT + 3 TP_HIT stay visible |

### P0-1 — Quote provenance (CRYPTO + COMMODITY)

**Problem (audited):** `picks.active` has 19/20 rows at `pnl_pct == 0.0`; XRP `0.9842 → 0.9842` and BTC `66,300 → 66,300` are exact copies of entry while Binance at 16:03Z showed 0.9716 and 65,672 (C:100-101). 485/691 OPEN `active_raw` rows have no price at all; 31 more are exact identity. The enrichment loop already exists, but on a quote miss it `continue`s and leaves whatever the source carried (`audit_trail/dashboard_generator.py:1739-1755`), and nothing distinguishes "live quote happened to equal entry" from "never quoted". A local re-run of `_enrich_live_pnl()` on the exact frozen XRP/BTC rows produces `0.9842→0.9622 (+2.24%)` and `66,300→65,506.23 (+1.20%)`, so the arithmetic path works; the published 14:30Z freeze is an invocation/timing or total-fetch miss, not an arithmetic bug (exact cause `UNVERIFIED`).

**Verified location:** `audit_trail/dashboard_generator.py:1618` (`_enrich_live_pnl`), `:1681-1688` (carried price accepted, never marked), `:1739-1755` (miss path), `:1821-1822` (only a successful quote writes `current_price`/`pnl_pct`), `:16953` (`picks.active` construction), `:17481-17485` (`picks.active_raw` assembly).

**Change (safe default):**
- On a quote hit set `quote_status="LIVE"`, `quote_source` from the fetcher (`binance`/`binance_vision`/`coinbase`/`coingecko`/`yfinance`/`stock_prices_cache`), `quote_at` = fetch start (UTC ISO), `quote_age_hours = 0`.
- On a miss set `quote_status="UNQUOTED"`, `quote_source="none"`, `quote_at=None`, and `_price_is_entry = (current_price == entry_price)`. **Do not mutate `pnl_pct`** in the enrichment loop (matches the peer contract in `equity_etf.md` P0-1) — the renderer and summary decide display.
- Add a **final pass** over every published pick immediately before serialization, applied to both `payload["picks"]["active"]` and `payload["picks"]["active_raw"]`, so `collect_all_picks()` early returns cannot skip it.
- Add `quote_status`/`quote_source`/`quote_at`/`quote_age_hours` to the closed-pick keep-list at `audit_trail/dashboard_generator.py:279-309` so they survive `_slim_closed_pick`.
- Rollout guard: `QUOTE_STATUS_ENABLED=1` (default). `0` restores today's shape. No schema change.

**Expected metric/UX impact:** XRP/BTC either show the live mark (+1.28% / +0.95% at 16:03Z; +2.24% / +1.20% at the 16:21Z local re-run) or render `UNQUOTED`; they can no longer render `+0.00%` with no provenance. 485 OPEN null rows become an explicit count. No return numbers are invented.

**Risk + rollback:** additive keys; every consumer must tolerate unknown keys. Rollback is the env flag; no data migration.

**Effort:** S.

**Validation:**
```bash
python3 - <<'PY'
import sys; sys.path.insert(0, '.')
import audit_trail.dashboard_generator as g
g._fetch_prices_with_failover = lambda syms: {}
g._fetch_equity_prices = lambda syms: {}
p = [{"symbol":"XRPUSDT","asset_class":"CRYPTO","direction":"SHORT",
      "entry_price":0.9842,"current_price":0.9842,"pnl_pct":0.0,"status":"OPEN",
      "strategy":"kalshi_mtf_consensus","source_system":"pm_kalshi_signals",
      "timestamp":"2026-11-14T13:53:28Z"}]
out = g._enrich_live_pnl(p)[0]
assert out["quote_status"] == "UNQUOTED", out
assert out["quote_source"] == "none", out
assert out.get("_price_is_entry") is True, out
print("ok")
PY
# and after a build, no active row may be 0.00% without provenance:
python3 - <<'PY'
import json
d=json.load(open('audit_trail/data/dashboard_payload.json'))
bad=[]
for p in d['picks']['active'] + d['picks']['active_raw']:
    if (p.get('pnl_pct') == 0.0 or p.get('pnl_pct') == -0.0) and 'quote_status' not in p:
        bad.append((p.get('symbol'), p.get('source_system')))
assert not bad, bad[:10]
print("provenance ok")
PY
python3 -m pytest tests/test_dashboard_generator.py tests/test_dashboard_payload_contract.py -q
```

### P0-2 — `UNQUOTED` / `STALE` / `LAST CLOSE` render contract

**Problem (audited):** the PnL cell has one formatter: `pnl_pct == 0` becomes `+0.00%` (`audit_dashboard/template.html:5075`, `:8889-8905`). The status cell turns the same value into `FLAT` (`:8883-8887`). The Current cell shows a green live dot whenever `p._livePrice` exists (`:9139`), and the non-crypto client path copies a server `current_price` into `_livePrice` when it differs by >1e-5 from entry (`:4718-4731`), so SB=F (18.41 vs 18.40999984741211, ~2.7e-11) stays unmarked while a genuinely re-quoted futures close would get the live dot. The Age cell shows only signal age (`:9222-9227`), never quote age — which is exactly why "NEAR 1.9h ago" is read as "price is 1.9h fresh" when the price may be older.

**Verified location:** `audit_dashboard/template.html:5075` (`fmtPct`), `:8889-8905` (PnL cell), `:8883-8887` (status cell), `:9134-9145` (Current cell), `:9222-9227` (Age cell), `:4718-4731` (server price → `_livePrice`). `audit_dashboard/index.html` is generated from `template.html` and currently mirrors these line numbers (verified 8889 / 9134 / 9222); patch `template.html`, not the generated file.

**Change (safe default):**
- PnL cell: if `p.quote_status === 'STALE'` render `<span class="badge-stale">STALE</span>`; if `'UNQUOTED'` render `<span class="badge-unquoted">UNQUOTED</span>`; if `'LAST_CLOSE'` render the PnL with a grey `LAST CLOSE` chip and no green/red claim.
- Status cell: `STALE` before the `FLAT` branch; add `NO ENTRY` when `_invalid_entry`.
- Current cell: replace the green dot with a neutral dot for `LAST_CLOSE`; show `—` for `UNQUOTED`/`STALE` instead of a copied entry price.
- Age cell: render `2.0h · quote 1.6h` (signal · quote) and a tooltip with `quote_at`/`quote_source`.
- Client re-mark functions (`:4325`, `:4459`, `:4669`, `:4727`, `:4821`) must set `quote_status="LIVE"` + `quote_at=Date.now()` on success and must not overwrite a server `LAST_CLOSE` unless a live price was actually fetched.
- Apply the same PnL branch to the closed-row renderer: `buildClosedColsFromActiveList` already skips `_livePrice` and maps Current→Exit (`audit_dashboard/index.html:9393-9400`), but the PnL cell is shared, so a closed `STALE`/`UNQUOTED` row must use the badge too.
- Rollout guard: `QUOTE_BADGE_V2=1` (default); `0` restores today's cells.

**Expected impact:** XRP/BTC never show a green `+0.00%`; PA=F/SB=F read `LAST CLOSE Fri 13 Nov`; the April CL=F/GC=F rows read `STALE`; users can see that "1.9h" is signal age, not quote age.

**Risk + rollback:** display-only, no arithmetic change. Rollback via env flag.

**Effort:** S.

**Validation:**
```bash
rg -n "quote_status === 'UNQUOTED'|badge-unquoted|LAST CLOSE" audit_dashboard/template.html
npx playwright test tests/audit_verified_edge_active_picks.spec.ts --project="Desktop Chrome"
npx playwright test tests/audit_crypto_comprehensive.spec.ts --project="Desktop Chrome"
# manual fixture: load /audit with the 14:30Z payload and assert no active row
# containing XRPUSDT/BTCUSDT renders "+0.00%" without a badge.
```

### P0-3 — Clock expiry must not publish 0.00%

**Problem (audited):** auto-expiry sets `status="EXPIRED"` and `exit_reason="STALE (auto-expired >Nh)"` but leaves `pnl_pct` at `0.0` (`audit_trail/dashboard_generator.py:9596-9605`). The April fossils are the proof: `futures_mean_reversion::CL=F::2026-04-03` has `entry=current=exit=112.05999755859375`, `commodity_momentum::GC=F::2026-04-03` has `4702.7001953125`, `futures_mean_reversion::ZN=F::2026-04-03` has `111.015625`; all three are `EXPIRED`, `_auto_expired=True`, `expired_no_pnl=True`. The metric helper already excludes them (`:4848-4864`), but the raw payload still shows a 0.00% mark. 3,377 such rows exist.

**Verified location:** `audit_trail/dashboard_generator.py:9570-9605` (auto-expire + flags), `:9618-9650` (split from `real_closed`), `:4848-4864` (`_is_valid_resolved_pick` already excludes them).

**Change:**
- In the auto-expire branch, when `pnl_val == 0`, set `p["resolution_kind"]="clock_expired"`, `p["quote_status"]="STALE"`, `p["pnl_display"]=None`; leave `pnl_pct` untouched for backward compatibility (metrics already ignore the row).
- In the final pass (P0-1), if `_auto_expired` or `expired_no_pnl`, force `quote_status="STALE"` and `pnl_display=None` regardless of `pnl_pct`.
- Do **not** clear `current_price`/`exit_price`: keeping the last observed price is the audit trail.
- Rollout guard: `RESOLUTION_KIND_ENABLED=1` (default); `0` restores old fields.

**Expected impact:** the auto-expired subset of the 3,377 EXPIRED rows stops claiming 0.00%; the 16 stale commodity rows and the April CL=F/GC=F/ZN=F fossils read `STALE` with their last price shown as history, not as a mark.

**Risk + rollback:** New field only; `pnl_pct` unchanged, so no metric moves. Rollback via env flag.

**Effort:** S.

**Validation:**
```bash
python3 - <<'PY'
import json
d=json.load(open('audit_trail/data/dashboard_payload.json'))
raw=d['picks']['active_raw']
fossil=[p for p in raw if p.get('id','').startswith('futures_mean_reversion::CL=F::2026-04-03')]
assert fossil, 'fixture row missing'
assert fossil[0].get('resolution_kind')=='clock_expired', fossil[0]
assert fossil[0].get('quote_status')=='STALE'
exp=[p for p in raw if p.get('status')=='EXPIRED']
assert all(p.get('quote_status')=='STALE' for p in exp if p.get('_auto_expired') or p.get('expired_no_pnl'))
print('ok', len(exp))
PY
```

### P0-4 — Raw-inventory truth + duplicate IDs

**Problem (audited):** `picks.active_raw` is 4,148 rows but only 3,851 unique IDs; 3,377 are EXPIRED; 218 IDs are duplicated and 55 IDs conflict across `active_raw`/`recent_closed` (MASTER_AUDIT:110, C:172). The commodity sample contains the same ID three times: `multi_asset_cot_positioning::CL=F::2026-11-14_1306` from `multi_asset_cot`, `orphan_emitter_forex_futures`, and `multi_asset_copytrader`; `consensus_CL=F_BUY_20261114_1424` appears twice with `current_price=88.55999755859375` and `None`. The tile prints "20 of 4,148" (`audit_dashboard/template.html:5628`), which reads as 4,128 gated-out live picks.

**Verified location:** `audit_trail/dashboard_generator.py:17481-17485` (raw pool assignment), `:17537-17538` (counts), `:9825-9877` (`_dedup_picks` key uses source+symbol+direction+strategy, not ID), `audit_dashboard/template.html:5628`, `:5122-5125`, `:10274-10277`.

**Change:**
- After `payload["picks"]["active_raw"]` is assigned, compute `picks.active_raw_open` = rows with `status in OPEN/ACTIVE`, `entry_price > 0`, and not `_auto_expired`.
- Add `summary.active_raw_counts = {total, open, expired, auto_expired, unpriced, zero_entry, dup_id_groups, dup_id_rows, cross_ledger_conflict_rows, unique_ids}`.
- Tag `_dup_id=True` and `_dup_id_count=N` on every member of a duplicated ID group; tag `_cross_ledger_conflict=True` for IDs present in both `active_raw` and `recent_closed` with differing `status`/`pnl_pct`.
- In `_dedup_picks(active, keep_most_recent=True)`, dedupe by `id` first (keep highest score, then newest), then by the existing 4-tuple.
- UI: use `active_raw_open.length` for the "of N" count and add a `DUP ×N` badge in the symbol cell (`audit_dashboard/template.html:7444`, `:7471`).
- Rollout guard: `ACTIVE_RAW_OPEN_VIEW=1` (default).

**Expected impact:** the tile reads "20 of 691"; the operator sees `expired=3,377`, `unpriced=485`, `zero_entry=85`, plus the duplicate-ID group/row counts instead of a mysterious 4,148. No row is removed, so every audit question remains answerable.

**Risk + rollback:** additive fields; one dedupe-key change in the curated path only. Rollback via flag; the dedupe change is a 5-line revert.

**Effort:** S.

**Validation:**
```bash
python3 - <<'PY'
import json
from collections import Counter
d=json.load(open('audit_trail/data/dashboard_payload.json'))
raw=d['picks']['active_raw']
c=d['summary']['active_raw_counts']
assert c['total']==len(raw), (c['total'], len(raw))
assert c['unique_ids']==len({p.get('id') for p in raw if p.get('id')})
assert len(d['picks']['active_raw_open'])==c['open']
assert c['open']==sum(1 for p in raw if str(p.get('status','')).upper() in ('OPEN','ACTIVE'))
print(c)
PY
rg -n "active_raw_open|_dup_id_count" audit_trail/dashboard_generator.py audit_dashboard/template.html
```

### P0-5 — Zero-entry rows (XRP entry 0.0)

**Problem (audited):** 85 crypto rows have `entry_price <= 0` (C:166). The named XRP phantom is `pm_consensus_XRPUSDT_202611141354`, SHORT, `entry_price=0.0`, `take_profit=0.0`, `stop_loss=0.0`, `status=OPEN`, timestamp `2026-11-14T13:54:51Z`. The merge path explicitly coerces `None` to `0.0` (`alpha_engine/prediction_market_consensus.py:589-591`). The genome evolver writes picks with no entry field at all (`genome/mape_evolver.py:497-511`). The dashboard filter explicitly permits `entry_price=0` (`audit_trail/dashboard_generator.py:9722-9723`: “entry_price=0 is allowed (for prediction markets, tests, etc)”).

**Verified location:** `alpha_engine/prediction_market_consensus.py:160` (returns `0.0` on total price failure), `:479` (`entry_price or None` in one path), `:588-591` (merge re-introduces `or 0`), `genome/mape_evolver.py:497-511`, `audit_trail/dashboard_generator.py:9722-9723`.

**Change:**
- `alpha_engine/prediction_market_consensus.py:589-591`: keep `None` for `entry_price`/`take_profit`/`stop_loss`; keep `status="SIGNAL"`. Do not coerce to `0`.
- `genome/mape_evolver.py:497`: add `"pick_type": "signal_only"`; if `trades[-1]` has an entry price, copy it, otherwise emit the row without `entry_price` and let the dashboard keep it out of tradeable inventory.
- Dashboard: in `_normalize_pick`/`collect_all_picks`, if `status in {"SIGNAL","PENDING_SIGNAL"}` or `entry_price <= 0`, set `_invalid_entry=True` (and `pick_type="signal_only"` when applicable); keep the row in `active_raw` for auditability but exclude it from `active_raw_open` and from the curated active gate (the gate already rejects `entry<=0`).
- Do not change `_is_valid_pick` to drop the row (that would hide evidence).
- Rollout guard: `ZERO_ENTRY_SIGNAL_ONLY=1` (default).

**Expected impact:** no new `entry=0.0` rows; the XRP phantom shows `NO ENTRY` instead of a fake 0.00% trade; the 85 existing rows are counted and labelled, not silently traded.

**Risk + rollback:** the only behavioural change is `None` vs `0.0` in one emitter and one status field; the dashboard gate already treats both as non-tradeable. Rollback via env flag and a one-line revert.

**Effort:** S.

**Validation:**
```bash
python3 - <<'PY'
import sys; sys.path.insert(0,'.')
from alpha_engine.prediction_market_consensus import _extract_trade_levels
# total price failure path must return 0.0 (emitter signal), but the merge must not coerce to 0
print(_extract_trade_levels("XRPUSDT","SHORT",0.67,[],1))
PY
rg -n '"entry_price"\] = .*or 0' alpha_engine/prediction_market_consensus.py && exit 1 || echo "merge no longer coerces None->0"
python3 - <<'PY'
import json
d=json.load(open('audit_trail/data/dashboard_payload.json'))
z=[p for p in d['picks']['active_raw'] if float(p.get('entry_price') or 0) <= 0]
assert all(p.get('_invalid_entry') for p in z), z[:3]
assert not [p for p in d['picks']['active_raw_open'] if float(p.get('entry_price') or 0) <= 0]
print('zero-entry rows labelled:', len(z))
PY
```

### P0-6 — `summary_picks` WR denominator

**Problem (audited):** COMMODITY reports 240.2% WR (3,476 wins / 3,466 losses against `resolved=1,447`); CRYPTO 98.3% (10,262 / 13,746 vs 10,444); 8/11 classes >100% (E:292-299). The SQL counts `wins` and `losses` over every row with a non-null `pnl_pct` (including still-open rows) while `resolved` counts only terminal statuses, then divides wins by resolved.

**Verified location:** `tools/sync_summary_picks_json.py:63-65` (the three SUM expressions), `:161` (`win_rate_pct = 100*wins/resolved`), `:16` (existing `RESOLVED` frozenset that can be reused).

**Change:**
- Compute `outcomes = wins + losses` and `win_rate_pct = 100*wins/outcomes` when `outcomes > 0`.
- Restrict `wins`/`losses` to the same terminal-status predicate: `wins = status='WON' OR (pnl>0 AND status IN RESOLVED)`; `losses = status='LOST' OR (pnl<0 AND status IN RESOLVED)`.
- Keep the current `resolved` field unchanged for compatibility and add `outcomes` + `data_quality="wins_gt_resolved"` when the old invariant fails.
- If any class still yields `>100`, emit `win_rate_pct=null` rather than an impossible value (fail closed, not fail pretty).
- Rollout guard: `SUMMARY_PICKS_WR_V2=1` (default); `0` writes the legacy formula.

**Expected impact:** COMMODITY moves from an impossible 240.2% to a computable WR over the same outcomes; CRYPTO from 98.3% to a valid number. The file stops being obviously wrong in a published `/audit/data/` path.

**Risk + rollback:** diagnostic-only surface (B:358); no trading path reads it. Rollback via env flag.

**Effort:** S.

**Validation:**
```bash
python3 tools/sync_summary_picks_json.py
python3 - <<'PY'
import json
d=json.load(open('audit_dashboard/data/summary_picks.json'))
bad=[(c['asset_class'],c['win_rate_pct']) for c in d['asset_classes'] if c['win_rate_pct'] and c['win_rate_pct']>100]
assert not bad, bad
print([(c['asset_class'],c['win_rate_pct'],c.get('outcomes')) for c in d['asset_classes']])
PY
```

### P0-7 — Inverse-zombie quarantine in the view

**Problem (audited):** 2,267 rows from `inverse_mutations` / `inverse_luxalgo_confluence`: 2,231 EXPIRED, 2,255 `pnl==0.0`, 2,254 null price; 20 symbols, 167 emission days, first 2026-05-23, last 2026-11-13, essentially one row per symbol per day (C:152-160). They are 71% of all crypto null-price rows and the dominant reason the raw book looks like 3,577 rows of flat crypto.

**Verified location:** `audit_trail/dashboard_generator.py:4062` (source registration), `:17481-17485` (raw pool), `:9540-9617` (auto-expiry), display source selection in `audit_dashboard/template.html:5122-5125`, `:10274-10277`.

**Change:**
- In the P0-4 post-pass, tag rows where `source_system == "inverse_mutations"` or `strategy.startswith("inverse_")` with `_inverse_emitter=True`; if `status` is `EXPIRED`/empty or `_auto_expired` is set, or `age_hours > 168`, set `_quarantined=True` (OPEN and resolved TP_HIT/SL_HIT rows stay).
- `picks.active_raw_open` excludes `_quarantined` rows. `picks.active_raw` keeps all of them.
- The Show All Picks default uses `active_raw_open`; add a filter chip "Inverse zombies (N)" that re-enables them.
- Rollout guard: `INVERSE_RAW_QUARANTINE=1` (default).

**Expected impact:** the visible raw pool drops from 4,148 to 691 before any other filter, and the crypto view stops being dominated by a 167-day inverse re-emission. Nothing is deleted; one chip restores the full pool.

**Risk + rollback:** display selection only. Rollback via env flag or the chip.

**Effort:** S.

**Validation:**
```bash
python3 - <<'PY'
import json
d=json.load(open('audit_trail/data/dashboard_payload.json'))
raw=d['picks']['active_raw']; op=d['picks']['active_raw_open']
inv=[p for p in raw if p.get('source_system')=='inverse_mutations']
assert inv, 'fixture missing'
assert not [p for p in op if p.get('_quarantined')], 'quarantined rows leaked into open view'
print('inverse rows', len(inv), 'quarantined', sum(1 for p in inv if p.get('_quarantined')))
PY
```

---

## Structural (P1)

| ID | Fix | Audited problem | Primary location | Effort | Risk | Expected impact |
|---|---|---|---|---|---|---|
| **P1-1** | Server quote pipeline v2: re-quote every OPEN row (not just curated), persist a per-build quote snapshot, and fail the build if coverage < threshold | 485/691 OPEN raw rows have no `current_price`; `active_raw` is a pre-enrichment snapshot (`:9538`), so only rows that survived into `active` can ever be enriched; 86% null raw price (B:195) | `audit_trail/dashboard_generator.py:9538`, `:14548-14551`, `:17481-17485`; fetchers `:1179-1615` | M | Medium — more network calls; add per-symbol cache + budget | Every OPEN row carries a quote or an explicit `UNQUOTED`; coverage becomes a CI metric instead of a silent gap |
| **P1-2** | Fix inverse emission at the source: stable ID from the *source* pick, bounded merge (no unbounded OPEN accumulation), and a single writer | Two writers target `alpha_engine/data/inverse_picks.json` with different semantics: `inverse_strategies.run()` merges/appends (`:547-560`), `inverse_loser_mutations.run()` overwrites (`:398-400`); IDs are date-only (`alpha_engine/inverse_strategies.py:410,436`; `alpha_engine/inverse_loser_mutations.py:231`) so each day creates a new ID | `alpha_engine/inverse_strategies.py:410`, `:436`, `:439`, `:547-560`; `alpha_engine/inverse_loser_mutations.py:231`, `:398-400` | M | Medium — changes emission volume; keep one release of legacy IDs via mapping | Stops creating ~15–18 new zombie rows/day; `inverse_picks.json` stops growing without bound; OPEN count becomes bounded |
| **P1-3** | COMMODITY: keep the bucket, add `canonical_asset_class="FUTURES"`, and label it "COMMODITY (futures)" + a `FUTURES` rollup | 44/44 COMMODITY rows are `=F`; `contract_type="commodity_future"` on all 44; `alpha_engine.asset_class.normalize_asset_class()` returns `futures` for every one (D:380). The two surfaces disagree | `audit_trail/dashboard_generator.py:3286-3313` (`_COMMODITY_ROOTS`), `:3418-3501` (`=F` routing), `:8343` (`contract_type` stamp); `alpha_engine/asset_class.py:214-215`; `alpha_engine/contract_type.py:1-14` | S–M | Low — additive field + label; routing changes only if `CLASS_NORMALIZE_ENFORCE=1` and `COMMODITY_DISPLAY_BUCKET=0` | The tile shows `class_mismatch=44` and a `COMMODITY (futures)` label; a `FUTURES_ROLLUP` gives the canonical statistic without rewriting history |
| **P1-4** | Split `EXPIRED` into `resolution_kind`: `price_resolved` / `clock_expired` / `never_priced`; surface it in the API and UI | Two different events both write `status="EXPIRED"`: a real flat time-exit (`alpha_engine/active_picks_sync.py:205-225`) and a stale clock expiry (`audit_trail/dashboard_generator.py:9596-9605`). The 3,377-row count mixes them | `audit_trail/dashboard_generator.py:9596-9605`; `alpha_engine/active_picks_sync.py:205-225`; `audit_trail/universal_pick_resolver.py` resolution paths | M | Low–Medium — additive enum; keep `status` for compatibility | Per-class "EXPIRED" counts become interpretable; `never_priced` is the real data-quality metric |
| **P1-5** | Ledger-level ID integrity: dedupe by ID across `active_raw` + `recent_closed`, quarantine conflicting pairs, and stop double-counting | 218 duplicate IDs; 55 IDs conflict across ledgers with different status/PnL (C:172). `_dedup_picks` keys on source+symbol+direction+strategy (`:9825-9877`), so the same ID from different `source_system` survives | `audit_trail/dashboard_generator.py:9825-9877`, `:9888-9932`; post-pass `:17481-17485` | M | Medium — could hide a legitimate re-issuance; require an explicit conflict list | Removes the "same trade counted 2–4×" class of errors from counts and PF; conflicts become a reviewed list |
| **P1-6** | Futures/commodity quote calendar: `LAST_CLOSE` on weekends/holidays, exchange-aware `quote_at`, no live dot when the market is shut | The audit is a Saturday; PA=F 1006.0 and SB=F 18.41 equal the 2026-11-13 closes exactly (D:352-353, :372-373); the current cell can still show a live dot for a close | `audit_trail/dashboard_generator.py:1480-1615`; `audit_dashboard/template.html:4096-4131`, `:9134-9145`, `:4718-4731` | M | Low — display + provenance | The hottest-looking commodity rows stop implying an intraday mark; users get an as-of date |
| **P1-7** | Optional MySQL provenance columns + JSON feature advertisement | No quote columns in `trading_picks` (`schema-baseline.sql:6072-6094`); no payload feature list, so consumers cannot tell whether `quote_status` exists | `schema-baseline.sql:6072-6094`; DB writers; payload meta | S | Low — nullable columns, no backfill | Provenance survives DB round-trips; consumers can gate on `payload.meta.features` |
| **P1-8** | Publish CRYPTO/COMMODITY performance only with n + cohort label + artifact flag; block "WATCH" from a 229-row intrabar cohort when policy-clean n=14 | CRYPTO policy-clean `n=21,988`, WR 42.35%, PF 0.2595, z=−22.69, and `single_source_pct=0.989` with `is_single_source_artifact=True`; COMMODITY is `WATCH` on intrabar n=229 WR 40.17% PF 1.0256, but policy-clean is n=14 WR 14.29% PF 0.1718 (E:202-212; `raw/pf_registry.json`) | `alpha_engine/money_ready_verdict.py` output; `tools/build_audit_surface_truth.py`; class tile in `audit_dashboard/template.html:908` | S | Low — labelling/eligibility only | The page stops implying a commodity edge from a 229-row intrabar cohort, and CRYPTO's "discovery-tier single-source artifact" is stated next to the number |

### P1-1 — Server quote pipeline v2

**Problem (audited):** `_enrich_live_pnl(active)` runs at `:14551` on the post-expiry curated list only. `picks.active_raw` is a shallow snapshot taken at `:9538` **before** that call, so any row removed by auto-expiry (the 3,377 EXPIRED rows, including the April CL=F/GC=F/ZN=F fossils) is never re-quoted; and 485 of the 691 OPEN rows that *are* in `active` still have no price in the published file. The fetchers already implement Binance → vision → Binance.US → CoinGecko failover (`:1179-1470`) and yfinance → FMP for `=F`/equity (`:1480-1615`), so the missing piece is invocation coverage and observability, not a new data source.

**Verified location:** `audit_trail/dashboard_generator.py:9538`, `:14548-14551`, `:17481-17485`, `:1179-1470`, `:1480-1615`, `:1739-1755`.

**Change:**
- Add `_enrich_open_prices(active_raw_open)` that reuses the same fetchers but only touches `status in OPEN/ACTIVE` rows and writes `quote_status`/`quote_source`/`quote_at`; do not touch EXPIRED rows (they are history).
- Batch crypto by symbol (one `/ticker/price` call; CoinGecko in 50-ID chunks) and `=F` via one yfinance batch, so the extra cost is ~3 HTTP calls, not 691.
- Persist `audit_dashboard/data/quote_snapshot.json` = `{symbol: {price, source, asof, status}}` for the build, with `generated_at`.
- CI gate: after the build, compute `open_quote_coverage = quoted_open / total_open`; fail the job (or `::warning::`) if `< 0.95` for crypto majors or `< 0.80` overall. This is the tripwire that would have caught the 14:30Z freeze.
- Rollout guard: `QUOTE_PIPELINE_V2=1` (default); `0` keeps the current curated-only path.

**Expected impact:** 485 null OPEN rows become quoted or explicitly UNQUOTED; a silent total fetch failure fails the build instead of publishing 0.00%; the archived snapshot makes every later "why was it 0%" question answerable.

**Risk + rollback:** more outbound calls from CI (already hits Binance/yfinance); add a 60 s budget and cache per build. Rollback via flag.

**Effort:** M (1 day for the pass + gate; another day for the snapshot and tests).

**Validation:**
```bash
python3 - <<'PY'
import json
d=json.load(open('audit_trail/data/dashboard_payload.json'))
op=[p for p in d['picks']['active_raw_open']]
q=[p for p in op if p.get('quote_status') in ('LIVE','LAST_CLOSE')]
print('coverage', len(q), '/', len(op), round(len(q)/max(1,len(op)),3))
assert len(q)/max(1,len(op)) >= 0.80
PY
test -s audit_dashboard/data/quote_snapshot.json && python3 -c "import json;d=json.load(open('audit_dashboard/data/quote_snapshot.json'));print(len(d))"
```

### P1-2 — Inverse emission: stable IDs, bounded merge, single writer

**Problem (audited):** `inverse_luxalgo_confluence` is a hard-coded “pass” mutation (`alpha_engine/inverse_strategies.py:94-99`) and re-emits the same 20-symbol universe every day. The ID is `f"{inverse_name}::{symbol}::{now_str}"` where `now_str` is `%Y-%m-%d` (`:410`, `:436`), so each calendar day is a new ID; the merge keeps **every** existing OPEN pick and appends the new ones (`:547-560`), which is why `alpha_engine/data/inverse_picks.json` contains 2,282 entries across 167 days. `inverse_loser_mutations.py` writes the **same path** with `"w"` (full overwrite, `:398-400`) and uses a date-only ID too (`:231`). Whichever job runs last wins, so the file is non-deterministic.

**Verified location:** `alpha_engine/inverse_strategies.py:94-99` (config), `:410` (`now_str`), `:436` (`pick_id`), `:439` (dedupe check), `:547-560` (merge), `alpha_engine/inverse_loser_mutations.py:231` (ID), `:398-400` (overwrite), `alpha_engine/production_scanner.py:4406` (caller), `alpha_engine/scanner.py:2687` (second caller).

**Change:**
- Stable ID: `f"{inverse_name}::{symbol}::{source_pick_id}"` where `source_pick_id = pick.get("id")`; fall back to `f"{strategy}::{round(entry,8)}"` only when the source has no ID. This makes re-running on the same source pick idempotent.
- Bounded merge: `MAX_OPEN_AGE_DAYS = 7` and `MAX_OPEN_PER_STRATEGY = 1`. Existing OPEN picks older than the cap get `status="EXPIRED"`, `exit_reason="SUPERSEDED"` **in the file** (kept once for audit), then are not re-added.
- Single writer: move the write into one function/module and have `production_scanner`/`scanner` call that only. Add a file lock or `os.replace` atomic write.
- Rollout guard: `INVERSE_EMISSION_MODE=bounded` (default) vs `legacy`. Keep a one-time mapping of old date IDs → source IDs so the dashboard does not double-show the transition day.

**Expected impact:** new zombie rows/day drop from ~15–18 to 0; `inverse_picks.json` stops growing; the 2,267 historical rows remain as evidence but stop expanding.

**Risk + rollback:** emission volume changes; if a downstream system depends on daily new IDs, it will see one per source pick instead. Rollback via `INVERSE_EMISSION_MODE=legacy` and the old ID formula.

**Effort:** M.

**Validation:**
```bash
python3 - <<'PY'
import json, collections
d=json.load(open('alpha_engine/data/inverse_picks.json'))
ids=[p.get('id') for p in d]
print('rows',len(ids),'unique',len(set(ids)))
by=collections.Counter(p.get('strategy') for p in d)
print(by.most_common(5))
# after two consecutive runs, the file size must not grow:
PY
python3 -m pytest tests/test_inverse_wrapper.py -q
```

### P1-3 — COMMODITY: keep the bucket, add the canonical class

**Decision:** **keep COMMODITY as a display bucket; do not merge its rows into FUTURES.** Add `canonical_asset_class="FUTURES"` and label the bucket "COMMODITY (futures)".

**Why not merge:** (1) `contract_type="commodity_future"` is already stamped on 44/44 rows and `alpha_engine/contract_type.py:1-14` explicitly says the distinction is additive and must not change the existing COMMODITY/FUTURES routing; (2) `_derive_asset_class` intentionally routes commodity roots to COMMODITY (`audit_trail/dashboard_generator.py:3474-3501`), and 7 closed rows reclassify COMMODITY→FUTURES (D:63), so a naive union double-counts; (3) the sample sizes are tiny either way (policy-clean COMMODITY n=14, FUTURES n=13), so merging to ~27 still fails the Tier-2 charter (`n>=100`) and buys no statistical power; (4) a rewrite would break the historical `summary_picks`/`pf_registry` per-class series and the existing COMMODITY caveats on the page.

**Problem (audited):** 44/44 COMMODITY rows are `=F`; `normalize_asset_class()` returns `futures` for all of them (D:380), while the dashboard tile and `pf_registry` say COMMODITY. The two truth surfaces disagree, which is why a reader cannot tell whether "COMMODITY" is a real class or a futures sub-bucket.

**Verified location:** `audit_trail/dashboard_generator.py:3286-3313` (`_COMMODITY_ROOTS`), `:3418-3501` (`=F` routing and `contract_type` precedence), `:8343` (`contract_type` stamp), `:8300` (`current_price`), `alpha_engine/asset_class.py:214-215`, `alpha_engine/contract_type.py:1-14` and `:53-80`.

**Change:**
- In `_normalize_pick`, set `canonical_asset_class = alpha_engine.asset_class.normalize_asset_class(pick).upper()` (verified: returns `futures` for every `=F`, so the payload field is `FUTURES`, including GC/CL/PA/SB/SI/HG/HE/NG/ZS). Also emit `class_label_raw = asset_class`, `class_mismatch = (canonical_asset_class != asset_class)`, and `class_mismatch_reason` — the **same field contract** as `forex_futures.md` P0-3. Do not create a second canonical field.
- Keep `asset_class="COMMODITY"` for display. All 44 raw rows and the 7 closed COMMODITY→FUTURES rows will be `class_mismatch=True`; that is the honest state, not an error.
- **Enforcement exception:** `forex_futures.md` P1-1 plans to flip `CLASS_NORMALIZE_ENFORCE=1`. If that ships without an exception, all 44 COMMODITY rows move to FUTURES and the COMMODITY tile disappears. Add `COMMODITY_DISPLAY_BUCKET=1` (default) so enforcement keeps COMMODITY as a display alias. The operator can merge later with one flag (`0`), without a historical rewrite.
- Add a separate `FUTURES_ROLLUP` panel that groups by `canonical_asset_class` and de-duplicates on `symbol+strategy+direction+timestamp`, so the FUTURES statistics can be seen without moving rows.
- `pf_registry`/`money_ready`: add a `by_canonical_asset_class` block; keep `by_asset_class` unchanged.
- Rollout guard: `COMMODITY_DISPLAY_BUCKET=1` (default); `0` merges into FUTURES on the next build.

**Expected impact:** a reader sees that all 44 COMMODITY rows are futures, without losing the COMMODITY history; the canonical FUTURES rollup becomes available for a future n≥100 test.

**Risk + rollback:** additive fields and a label; no row moves. Rollback via flag.

**Effort:** S–M.

**Validation:**
```bash
python3 - <<'PY'
import json, sys; sys.path.insert(0,'.')
from alpha_engine.asset_class import normalize_asset_class
d=json.load(open('audit_trail/data/dashboard_payload.json'))
rows=[p for p in d['picks']['active_raw'] if (p.get('asset_class') or '').upper()=='COMMODITY']
print('commodity rows', len(rows))
assert all(p.get('canonical_asset_class')=='FUTURES' for p in rows), [p.get('canonical_asset_class') for p in rows][:3]
assert all(normalize_asset_class(p)=='futures' for p in rows)
print('ok')
PY
rg -n "COMMODITY \(futures\)|canonical_asset_class" audit_dashboard/template.html audit_trail/dashboard_generator.py
```

### P1-4 — Split `EXPIRED` semantics

**Problem (audited):** the same status string is produced by two different events. A real flat time exit writes `EXPIRED` with `exit_reason=TIME_EXIT` (`alpha_engine/active_picks_sync.py:205-225`); the dashboard's clock expiry writes `EXPIRED` with `exit_reason="STALE (auto-expired >Nh)"` and `expired_no_pnl=True` (`audit_trail/dashboard_generator.py:9596-9605`). There are 3,377 `EXPIRED` rows in `active_raw`, of which 3,099 have no price — so "EXPIRED" currently conflates "flat trade" with "never priced".

**Verified location:** `audit_trail/dashboard_generator.py:9570-9605`; `alpha_engine/active_picks_sync.py:205-225`; `audit_trail/universal_pick_resolver.py:1297-1344` (price-based resolution).

**Change:**
- Add `resolution_kind` with `price_resolved` (TP/SL/force/time exit with a real exit price), `clock_expired` (stale, no exit price), `never_priced` (no entry/current at any point).
- Set it where each event happens; keep `status` and `expired_no_pnl` unchanged for compatibility.
- Publish `summary.resolution_kinds` and show it in the data-quality panel.
- Rollout guard: `RESOLUTION_KIND_ENABLED=1` (default).

**Expected impact:** the operator can finally answer "how many of the 3,377 EXPIRED rows were real trades?" (answer: the `price_resolved` subset) without SQL.

**Risk + rollback:** additive enum. Rollback via flag.

**Effort:** M.

**Validation:**
```bash
python3 - <<'PY'
import json, collections
d=json.load(open('audit_trail/data/dashboard_payload.json'))
print(collections.Counter(p.get('resolution_kind') for p in d['picks']['active_raw']))
assert d['summary'].get('resolution_kinds')
PY
python3 -m pytest tests/test_universal_pick_resolver.py -q
```

### P1-5 — Ledger-level ID integrity

**Problem (audited):** `active_raw` has 218 duplicate IDs (max 4 repeats) and 55 IDs appear in both `active_raw` and `recent_closed` with conflicting status/PnL (C:172). Examples: `clone_hl_copy_PensionFund_24M::NEARUSDT::2026-03-19_1150` is EXPIRED 0.0 in raw vs WON +3.4483 in closed; `aggregated_picks_ETHUSDT…crypto_funding_confluence` is OPEN −3.71 vs closed LOST −2.0 SL_HIT.

**Verified location:** `audit_trail/dashboard_generator.py:9825-9877` (`_dedup_picks`), `:9888-9932`, `:17481-17485` (raw pool), `:16953-16956` (closed list).

**Change:**
- Build a single `id → row` index over `active_raw + recent_closed`; when the same ID has two different `(status, pnl_pct)` pairs, keep the resolved row for metrics, tag both `_id_conflict=True`, and emit the pair into `audit_dashboard/data/id_conflicts_YYYY-MM-DD.jsonl`.
- For duplicate IDs within `active_raw`, keep one row for counts, keep all for display with `_dup_id_count`.
- Do not delete either side; the conflict log is the review artifact.

**Expected impact:** the same trade stops being counted 2–4×; 55 conflicts become a reviewable list instead of an invisible inconsistency.

**Risk + rollback:** metric counts can move (downward) on the first run; that is the point. Rollback by disabling the index build.

**Effort:** M.

**Validation:**
```bash
python3 - <<'PY'
import json, collections
d=json.load(open('audit_trail/data/dashboard_payload.json'))
raw=d['picks']['active_raw']; closed=d['picks']['recent_closed']
ids=collections.Counter(p.get('id') for p in raw if p.get('id'))
print('dup id groups', sum(1 for v in ids.values() if v>1))
conf=[p for p in raw if p.get('_id_conflict')]
print('conflicts', len(conf))
PY
```

### P1-6 — Futures/commodity quote calendar

**Problem (audited):** the audit is a Saturday. The two curated commodity picks are exact Friday closes: PA=F 1006.0 = Yahoo 2026-11-13 close; SB=F 18.41 = 18.40999984741211 (D:352-353, :372-373). The Current cell can still mark these as live if the client-side path copies a server price (`audit_dashboard/template.html:4718-4731`), and `quote_at` does not exist to say "Friday close".

**Verified location:** `audit_trail/dashboard_generator.py:1480-1615` (`_fetch_equity_prices`, yfinance/FMP), `audit_dashboard/template.html:4096-4131` (`PRICE_APIS`), `:9134-9145` (Current cell), `:4718-4731` (server-price → `_livePrice`).

**Change:**
- For `=F` symbols, prefer the daily bar’s date: `quote_at` = bar timestamp at 21:00Z, `quote_status="LAST_CLOSE"` when the exchange session is closed.
- Add a tiny XNYS/CME session calendar (or read `exchangeTimezoneName`/`currentTradingPeriod` when available) and never set `LIVE` outside the session.
- UI: grey dot + `LAST CLOSE Fri 13 Nov`; no red/green PnL claim for `LAST_CLOSE` unless the user opts into "mark to last close".
- Rollout guard: `FUTURES_QUOTE_CALENDAR=1` (default).

**Expected impact:** the two commodity rows stop looking like intraday trades; the 3 identity rows in the commodity pool are labelled LAST CLOSE rather than UNQUOTED (they are real Friday closes).

**Risk + rollback:** display/provenance only. Rollback via flag.

**Effort:** M.

**Validation:**
```bash
python3 - <<'PY'
import json
d=json.load(open('audit_trail/data/dashboard_payload.json'))
for p in d['picks']['active']:
    if (p.get('asset_class') or '').upper()=='COMMODITY':
        print(p['symbol'], p.get('quote_status'), p.get('quote_at'))
        assert p.get('quote_status') in ('LAST_CLOSE','LIVE')
PY
rg -n "LAST_CLOSE|quote_at" audit_dashboard/template.html
```

### P1-7 — Schema migration + feature advertisement

**Problem (audited):** `trading_picks` has no quote columns (`schema-baseline.sql:6072-6094`), so provenance is lost as soon as a pick round-trips through MySQL; and the payload has no feature list, so a consumer cannot tell whether `quote_status` is present.

**Verified location:** `schema-baseline.sql:6072-6094`; top-level payload dict at `audit_trail/dashboard_generator.py:16850` (add a new `meta` key; there is no `meta` block today).

**Change (DDL, nullable, no backfill):**
```sql
ALTER TABLE trading_picks
  ADD COLUMN quote_status VARCHAR(16) DEFAULT NULL,
  ADD COLUMN quote_source VARCHAR(32) DEFAULT NULL,
  ADD COLUMN quote_at DATETIME DEFAULT NULL,
  ADD COLUMN canonical_asset_class VARCHAR(20) DEFAULT NULL,
  ADD COLUMN resolution_kind VARCHAR(20) DEFAULT NULL,
  ADD INDEX idx_quote_status (quote_status);
```
- Add `payload["meta"]["features"] = ["quote_status_v1","canonical_asset_class_v1","resolution_kind_v1"]` so consumers can feature-detect.
- Rollout: apply the DDL before deploying the writer; old readers ignore the columns. Rollback = drop the columns (safe because nothing depends on them).

**Expected impact:** provenance survives DB sync; consumers stop guessing.

**Risk + rollback:** a nullable `ALTER` on a large table can lock; run with `ALGORITHM=INPLACE, LOCK=NONE` or during the low-traffic window. Rollback by dropping.

**Effort:** S.

**Validation:**
```bash
mysql -e "SHOW COLUMNS FROM trading_picks LIKE 'quote_status';" "$DB_NAME"
python3 - <<'PY'
import json
d=json.load(open('audit_trail/data/dashboard_payload.json'))
assert 'quote_status_v1' in d['meta']['features']
print('ok')
PY
```

### P1-8 — Publication discipline for CRYPTO/COMMODITY

**Problem (audited):** CRYPTO is `NOT_READY`: policy-clean n=21,988, WR 42.35%, PF 0.2595, z=−22.69, `single_source_pct=0.9895`, `is_single_source_artifact=True` (`raw/pf_registry.json`; E:202). COMMODITY is `WATCH` on the intrabar cohort n=229 WR 40.17% PF 1.0256, but policy-clean n=14 WR 14.29% PF 0.1718; the same file flags `single_source_pct=0.6429` and `is_single_source_artifact=True` (`raw/money_ready_verdict.json`, `raw/audit_surface_truth.json`).

**Verified location:** `raw/pf_registry.json::by_asset_class_policy_clean_net`; `raw/money_ready_verdict.json::classes`; `raw/audit_surface_truth.json::by_asset_class`; class tile copy `audit_dashboard/template.html:908`.

**Change:**
- Every class tile must print `n`, `cohort` (policy-clean vs intrabar), and `single_source_pct`; if `is_single_source_artifact`, show a red `SINGLE-SOURCE ARTIFACT` chip.
- Do not allow `WATCH` when `policy_clean_n < 30`; downgrade to `INSUFFICIENT_DATA` and show the policy-clean number next to the intrabar one.
- Sizing remains `false` for both classes (already true for CRYPTO via `verdict=NOT_READY`; add an explicit `sizing_allowed=false` for COMMODITY when `policy_clean_n<30`).
- Rollout guard: `CLASS_COHORT_LABELS=1` (default).

**Expected impact:** no user can read "COMMODITY WATCH" without also seeing "policy-clean n=14, PF 0.17, single-source 64%"; CRYPTO's 21,988-row statistic is labelled as a single-source artifact, not an edge.

**Risk + rollback:** labelling/eligibility only; no return number changes. Rollback via flag.

**Effort:** S.

**Validation:**
```bash
python3 - <<'PY'
import json
d=json.load(open('audit_trail/data/dashboard_payload.json'))
for ac in ('CRYPTO','COMMODITY'):
    h=d['performance']['asset_class_health'][ac]
    print(ac, h.get('cohort'), h.get('single_source_pct'), h.get('sizing_allowed'))
    assert h.get('sizing_allowed') is False
PY
rg -n "SINGLE-SOURCE ARTIFACT|policy_clean_n" audit_dashboard/template.html
```

---

## Feature flags and migration summary

| Flag | Default | Effect when `0`/`legacy` | Introduced by |
|---|---|---|---|
| `QUOTE_STATUS_ENABLED` | `1` | no `quote_status` stamping | P0-1 |
| `QUOTE_BADGE_V2` | `1` | old PnL/status/current cells | P0-2 |
| `RESOLUTION_KIND_ENABLED` | `1` | no `resolution_kind` | P0-3, P1-4 |
| `ACTIVE_RAW_OPEN_VIEW` | `1` | tile counts `active_raw.length` again | P0-4 |
| `ZERO_ENTRY_SIGNAL_ONLY` | `1` | emitters may write `entry=0.0` again | P0-5 |
| `SUMMARY_PICKS_WR_V2` | `1` | legacy `wins/resolved` formula | P0-6 |
| `INVERSE_RAW_QUARANTINE` | `1` | inverse zombies back in the default raw view | P0-7 |
| `QUOTE_PIPELINE_V2` | `1` | curated-only enrichment | P1-1 |
| `INVERSE_EMISSION_MODE` | `bounded` | date-only IDs + unbounded merge | P1-2 |
| `COMMODITY_DISPLAY_BUCKET` | `1` | COMMODITY rows merge into FUTURES when `CLASS_NORMALIZE_ENFORCE=1` | P1-3 |
| `FUTURES_QUOTE_CALENDAR` | `1` | no `LAST_CLOSE` semantics | P1-6 |
| `CLASS_COHORT_LABELS` | `1` | old tile copy | P1-8 |

**Schema migration:** only P1-7. Nullable columns, no backfill, safe with old readers. P0 needs **no** migration.

---

## Do-not-do

1. **Do not delete `EXPIRED` rows from `active_raw` or `recent_closed`.** They are the audit trail; the 5,414-hour-old CL=F fossil is the proof the resolver never touched it. Filter the view, tag the row, keep the record.
2. **Do not rewrite `asset_class="COMMODITY"` to `"FUTURES"`.** 44 rows would move into a 3-row bucket, break the historical per-class series, and double-count the 7 closed rows that already reclassify COMMODITY→FUTURES. Add `canonical_asset_class` instead.
3. **Do not use `pnl_pct = 0.0` as a “no data” sentinel.** That is the bug being fixed. Use `pnl_display=None` + `quote_status`.
4. **Do not overwrite `entry_price` with a live quote.** Entry is the execution record; a stale entry is a separate finding (e.g. the ETH 1,931.0 entry 1.63% above market, C:115). Fix the entry at the emitter; never rewrite it in the dashboard.
5. **Do not remove the zero-entry filter at `audit_trail/dashboard_generator.py:9722-9723` without adding the `signal_only` route.** Simply rejecting `entry<=0` would drop legitimate prediction-market signals; simply allowing it is what produced the XRP phantom.
6. **Do not rely on the browser re-quote as the only fix.** `PRICE_APIS` (`audit_dashboard/template.html:4096-4131`) is best-effort and CORS/geo-dependent; JSON consumers and no-JS views never run it.
7. **Do not dedupe `active_raw` by dropping rows.** It is the diagnostic pool; tag `_dup_id`/`_dup_id_count` and expose the counts.
8. **Do not change `alpha_engine/asset_class.normalize_asset_class()` =F→futures globally.** It feeds genome promotion (`genome/progressive_promotion.py:31`); add a canonical field instead.
9. **Do not lower quality gates, the per-class visibility floor, or the kill list to make CRYPTO look populated.** The current 3 curated crypto rows are the honest gate output.
10. **Do not backfill `quote_at`/`quote_source` retroactively.** A fabricated provenance timestamp is worse than none; leave old rows `UNQUOTED` until they are re-quoted.
11. **Do not push this audit branch to `main` as-is.** Repo rule: only push branches where every changed file is yours, and document every fix under `updates/` (AGENTS.md).
12. **Do not treat `summary_picks` as a performance source even after P0-6.** It is a count surface; trust `money_ready_verdict` + `pf_registry.by_asset_class_policy_clean_net` (B:358, `audit_surface_truth.json::trust_hierarchy`).

---

## UNVERIFIED

- **Build-time cause of the XRP/BTC freeze at 14:30Z.** A local 16:21Z re-run of `_enrich_live_pnl()` on the exact frozen rows updates them correctly (XRP 0.9842→0.9622, +2.24%; BTC 66,300→65,506.23, +1.20%), and `_fetch_prices_with_failover` resolves 3/3 symbols from Binance. Whether the CI runner had a total egress failure, a partial symbol failure, or an invocation/ordering defect is not determinable from the artifacts. The code that must make the failure observable is verified; the CI logs for that run were not inspected in this subtask.
- **Whether end users actually see live crypto PnL in the browser.** `PRICE_APIS` can re-quote crypto client-side (`audit_dashboard/template.html:4096-4131`, `:4785-4800`), but CORS/geo availability was not tested. The audit's 0.00% finding is certain for the published JSON; the rendered DOM was not verified for crypto (C did not run Playwright; B replicated logic in Python).
- **Whether `current_price == entry_price` with `pnl=0` is an intentional sentinel or a bug** (C:218). The effect is confirmed; intent is not.
- **Exact intraday exit prints for closed commodity resolutions** (C:217, D:376). Daily-close reconstruction cannot reproduce intraday TP/SL, so small gaps are expected.
- **Provenance/consumers of `summary_picks.json`** beyond diagnostics (B:358).
- **Which writer produced the 2,282-row `inverse_picks.json` history.** Both `inverse_strategies.run()` (merge/append) and `inverse_loser_mutations.run()` (overwrite) target the same path; the file state is order-dependent.
- **Root cause of the absurd-low `inverse_luxalgo_confluence` entries** (BTC 0.2608, 0.3322, 1.334; ETH 0.092; AVAX 0.1544). The inverse pick deep-copies the source entry (`alpha_engine/inverse_loser_mutations.py:189`, `:206`), so the corruption is upstream in `luxalgo_confluence`; the producing unit/lookup bug was not traced (C:219).
- **MySQL row counts behind `file:mysql:at_pick_outcomes`** — the source of 98.9% of CRYPTO's policy-clean 21,988 rows (`raw/pf_registry.json::single_source_pct`). Not queried.
- **Whether the 14:30Z build hit Binance HTTP 451.** The Actions audit records 451s in the Alpha Engine workflows (MASTER_AUDIT:54), but the dashboard job's own logs were not re-read.
- **Visual rendering after the P0-2 change.** The exact pixel states (badge colors/contrast) require a browser pass; the data logic is deterministic.
