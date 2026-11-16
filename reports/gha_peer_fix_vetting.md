# Peer fix vetting — Windows "antigravity" coordinator (2026-11-16 03:11 EST)

Scope: analysis only. No files edited, nothing pushed, `dbpasses.txt` not read.
Worktree: `ghactions-v4` @ `c115895bbe7` (== `origin/main`).

## Verdict table

| Fix | Proposal | Verdict | Key evidence |
|-----|----------|---------|--------------|
| 1 | `universal_pick_resolver.py`: write `NULL` instead of `0` for `TIME_EXPIRED` picks | **STILL VALID** (partial; needs a 2-line coordinated change) | `audit_trail/universal_pick_resolver.py:1398`, `:1607`, `:1168-1170`, `:1181-1182`; `audit_trail/mysql_schema.sql:281` |
| 2 | Trigger `hf_stats.by_asset_class` + `prediction_market_consensus` refresh | **Split:** prediction market = **ALREADY DONE**; hf_stats = **STILL VALID** (real staleness bug) | `audit-dashboard.yml:127-132`; `dashboard_generator.py:1907-1963`; `tools/data/hf_stats_summary.json` (tracked, stale) |
| 3 | Filter `TIME_EXPIRED` from the `active` count in `dashboard_generator.py` | **ALREADY DONE** for the published count; raw-pool counts are by design | `quality_gates.py:7657-7661`; `dashboard_generator.py:17592-17593`; live payload |
| 4 | Ingest `WIRED_IN/` into `dashboard_generator.py` | **ALREADY DONE** (landed 2026-11-15) | `dashboard_generator.py:4284-4292`, `:4326-4331`; `universal_pick_resolver.py:264-267`; commit `5ed7db2bda2` |

---

## Fix 1 — NULL instead of 0 for TIME_EXPIRED

**Where TIME_EXPIRED is produced and written**

- JSON-side TIME_EXIT resolution, with price: `universal_pick_resolver.py:1583-1641`.
  The no-usable-price branch sets `pnl_out = 0.0` + `_mtm = "breakeven_fallback"` at `:1606-1608`.
- JSON-side TIME_EXIT resolution, no live price: `universal_pick_resolver.py:1374-1422`.
  Same fabricated zero at `:1397-1399`.
- `_priceless_close()` (`:278-297`) already detects "no trustworthy price" and its docstring
  says consumers must see `None`, but the fallback still publishes `0.0`.
- MySQL writer `_write_outcomes_to_mysql()` (`:1089-1216`):
  - maps `TIME_EXIT`/`EXPIRED` → `status='EXPIRED'`, `resolution_method='TIME_EXPIRED'` (`:1150-1152`, `:1160-1161`);
  - **skips** any row whose `pnl_pct is None` (`:1168-1170`);
  - coerces a missing pnl to `0` (`:1181-1182`) and upserts it (`:1111-1123`).

**Is NULL safe?** Yes at the schema level: `at_pick_outcomes.pnl_pct` is `DECIMAL(10,4)` with no
`NOT NULL` (`audit_trail/mysql_schema.sql:281`). Downstream consumers audited:

- `tools/strategy_kill_switch.py:278` — `WHERE status IN ('WON','LOST')`; EXPIRED rows never read.
- `tools/pmc_pilot_monitor.py:84-87` — `status IN ('WON','LOST','FLAT')`; EXPIRED never read.
- `alpha_engine/money_ready_verdict.py:540-541` — `status IN ('WON','LOST') AND pnl_pct IS NOT NULL`.
- `tools/cross_validate_kill_candidates.py:71,110` — explicit `pnl_pct IS NOT NULL`.
- `tools/mysql_resolve_at_pick_outcomes.py` — only stale `OPEN` rows.
- `AVG()`/`SUM()` ignore NULL (the desired "unmeasured" semantics); `float(x or 0)` handles `None`.

No consumer assumes numeric `0` for EXPIRED rows. NULL is not a new state — the writer already
emits it for other paths, and `alpha_engine/sign_flip_purge.py` / `mysql_resolve_at_pick_outcomes.py`
can write NULL.

**Why it is only "partial" / needs coordination**

1. Changing only the emission (`:1398`, `:1607`) is not enough: `:1168-1170` drops `None`-pnl rows,
   so the row would vanish from `at_pick_outcomes` rather than be stored as NULL. Both must change together.
2. `tools/hf_stats.py:538-540` skips `pnl_pct is None`; today those TIME_EXIT rows enter hf_stats as
   `0.0` and count in `n`/WR/PF. NULLing them changes hf_stats denominators — coordinate with Fix 2.
3. Do **not** NULL measured TIME_EXIT rows that have a real exit price (`_mtm="measured"` /
   `"fallback"`); only the `breakeven_fallback` path is unmeasured.
4. No existing test covers this path (`tests/test_universal_pick_resolver.py` is 107 lines and does
   not touch TIME_EXIT or MySQL), so a regression test should be added with the change.

**Recommendation:** implement as a targeted change — emit `None` for `_mtm == "breakeven_fallback"`
only, relax the writer skip to admit `resolution_method == 'TIME_EXPIRED' AND pnl_pct IS NULL`,
and add a unit test asserting `pnl_pct is None` + `resolution_method == 'TIME_EXPIRED'`.

---

## Fix 2 — hf_stats.by_asset_class + prediction_market_consensus refresh

**prediction_market_consensus — ALREADY DONE**

- `audit-dashboard.yml:127-132` ("Refresh prediction-market inputs") runs
  `alpha_engine/prediction_market_consensus.py` (plus polymarket/kalshi/orchestrator) every dashboard build.
- Also run by `alpha-engine-live.yml:316` and `polymarket-signals.yml:76`.
- Live proof: `https://findtorontoevents.ca/audit/data/dashboard_data.json` (generated 2026-11-16T07:58Z)
  has a populated top-level `consensus` (50 picks) and pm systems (`pm_polymarket_re_signals` 5 active,
  `pm_kalshi_re_signals` 9 active, `polymarket_signals` 3 active).

**hf_stats.by_asset_class — STILL VALID (real staleness bug)**

- `_hf_stats_summary()` (`dashboard_generator.py:1907-1963`) serves
  `tools/data/hf_stats_summary.json` whenever its **mtime** is ≤ 24h, else recomputes from
  `dashboard_data.json::picks.recent_closed` via `tools/hf_stats.py:524-578`.
- That cache file **is tracked in git** (`git ls-files` confirms) and was last committed in
  `5ed7db2bda2` (2026-11-15 13:51). It is **not** in the `audit-dashboard.yml` commit list, so CI never updates it.
- CI checkout resets mtime to "now", so `cache_fresh` is always true on a fresh runner → the dashboard
  serves the committed snapshot forever.
- Live proof of staleness: live `hf_stats.hf_metrics.n = 1746` and
  `hf_stats.rolling_current.end_date = "2026-06-02"` exactly match the committed cache, while the live
  `picks.recent_closed` ledger runs to 2026-11-16. The 30-day rolling window is ~5 months frozen.
- Note `validate-hf-asset-class.yml:64` writes `audit_trail/data/hf_asset_class_report.json`, but only
  uploads it as a CI artifact — it does not feed `dashboard_data.json::hf_stats`.

**Recommendation:** make `_hf_stats_summary` validate content, not mtime — e.g., compare the cache's
`generated_at`/window against `dashboard_data.json`, or delete the tracked cache and rely on in-build
recompute (then optionally commit the refreshed cache). Coordinate with Fix 1 because both change the
same hf_stats denominators.

---

## Fix 3 — filter TIME_EXPIRED from the active count

**ALREADY DONE for the published count.**

- Bucket routing: `collect_all_picks` sends resolved rows to `closed` via
  `_looks_resolved_source_pick` (`dashboard_generator.py:5248-5320`, called at `:8964-8995`);
  `_is_closed_status` (`:5410-5412`) matches `_CLOSED_STATUSES` (`:4470-4482`: `time_exit`, `expired`, ...).
- Staleness auto-expiry moves aged picks out of `active` (`:9624-9672`).
- `_is_active_pick` (`:868-873`) treats only `OPEN/ACTIVE/PENDING/LIVE` as active.
- The display gate rejects every other status: `audit_trail/quality_gates.py:7657-7661`
  (`status not in {"OPEN","ACTIVE","PENDING","LIVE",""}` → reject).
- Published counts are post-gate: `dashboard_generator.py:17592-17593`
  (`total_active_picks` = `len(payload["picks"]["active"])`, `total_active_raw_picks` = raw pool).

**Live proof:** published `picks.active` = 11, **all status OPEN**; `summary.total_active_picks` = 11.
The 4157 figure is `total_active_raw_picks`, the documented pre-expiry/pre-gate "Show All Picks" pool
(`:17514-17523`, `:17534-17535`) — it contains 3361 EXPIRED rows by design, for transparency.

**Caveat:** the literal status string `TIME_EXPIRED` is not in `_CLOSED_STATUSES` (only
`time_exit`/`expired`), so such a row would be bucketed OPEN at load. It is still rejected by the
display gate, but it would inflate pre-gate diagnostics (`total_active_final`, `:16870`/`:16918`;
resolution-coverage panel) until `:17592` overwrites the published count.

**Recommendation:** no change needed. If the coordinator wants the raw pool relabeled, treat it as a
separate UX/coordination item — do not "fix" the published count, which is already correct.

---

## Fix 4 — WIRED_IN integration

**ALREADY DONE.**

- `dashboard_generator.py:4284-4292` — `JSON_PICK_SOURCES` entry for
  `wired_in_childlike` (active + closed files), spec pointer `WIRED_IN/2026-11-15T0150Z_childlike-airport/`.
- `dashboard_generator.py:4326-4331` — `wired_in_childlike` in `_PAPER_ONLY_SYSTEMS` (display only,
  excluded from forward-tested metrics).
- `universal_pick_resolver.py:264-267` — matching `SYSTEM_SOURCES` entry so the cards actually resolve.
- Introduced by `5ed7db2bda2` ("Cross-system aggregation 2026-11-15 13:51 UTC"), on `origin/main`.
- Live proof: `systems[]` contains `wired_in_childlike` (3 active picks); `active_raw` has 3 wired OPEN rows.
- No producer workflow exists — the cards are static shadow fixtures by design; do not add one.

---

## Git history / duplicate-work check

`origin/main` == `HEAD` == `c115895bbe7`; branch `fix/gha-disable-broken-workflows` is even with origin.

```
git log --oneline -10 origin/main -- audit_trail/universal_pick_resolver.py audit_trail/dashboard_generator.py
3ce350d60ab feat(audit): wire PM reverse-engineered signals into pick feed + resolver, ...
5ed7db2bda2 Cross-system aggregation 2026-11-15 13:51 UTC [skip ci]
```

- `git log -S "wired_in_childlike"` → `5ed7db2bda2` (Fix 4 landed 2026-11-15).
- `git log -S "TIME_EXPIRED"` → `5ed7db2bda2` (the enum mapping, not the NULL fix).
- No peer commit has attempted Fix 1, so it is not duplicated work.

## Bottom line

- **Fix 1:** worth doing, but as a coordinated 2-part change (emission + writer skip) with a test; not a one-liner.
- **Fix 2:** prediction-market half is already wired; hf_stats half is a genuine frozen-cache bug worth a PR.
- **Fix 3:** already correct on the published count; only raw-pool labeling is debatable.
- **Fix 4:** already shipped 2026-11-15; close it.
