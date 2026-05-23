# Long-Term EQUITY Pick Integration Audit — 2026-05-08

**Author:** Claude Opus 4.7 (1M context)
**Scope:** Verify integration status of the long-term-pick code path (UEPS, Penny Skyrocket, TradingAgents, Mercury2, Concept Taxonomy) on `findtorontoevents.ca/audit`.
**Repo:** `eltonaguiar/findtorontoevents_antigravity.ca`, branch `main`.
**Mode:** Read-only investigation. No source files modified.

---

## 1. PR Landing Verification (PR #545–#549)

All 5 PRs **MERGED to `main`** on 2026-04-30:

| PR | Title | Merged | Status |
|----|-------|--------|--------|
| #545 | feat(audit): wire equity × POSITION lane (PEAD + bond credit-spread + TF classifier) | 2026-04-30 19:57 UTC | ✅ Landed |
| #546 | feat(audit): wire penny skyrocket detector into /audit | 2026-04-30 20:05 UTC | ✅ Landed (workflow currently FAILING — see §4) |
| #547 | fix(audit): UEPS sync_to_active_picks() output now persisted across runs | 2026-04-30 20:18 UTC | ✅ Landed (superseded by direct JSON_PICK_SOURCES wire — see §3) |
| #548 | feat(audit): concept taxonomy Phase 1 (assign_concept_fields helper) | 2026-04-30 20:12 UTC | ✅ Landed (but only partially effective — see §5) |
| #549 | docs: 2026-04-30 session record + remaining action items queue | 2026-04-30 21:17 UTC | ✅ Landed (docs only) |

Note: PR #549 in the update post is described as "Long-Term timeframe dropdown alias in template.html". The actual merged PR #549 is a docs commit. The dropdown alias (`<option value="LONG_TERM">Long-Term (1y+)</option>`) IS present in `audit_dashboard/template.html:1139` and the matching JS guard in `template.html:6757-6758`, so the feature is live, just not under the PR number cited in the update post.

---

## 2. Live Pick-File Health (read-only inspection of repo HEAD)

| File | Exists | Last write | Row count | Notes |
|------|--------|-----------|-----------|-------|
| `audit_dashboard/data/ueps_picks.json` | ✅ | 2026-05-08 17:08 UTC | 22 long, 0 swing, 0 short | Active. UEPS cron (4-hourly) is healthy — `gh run list ueps-pick-runner.yml` shows 5/5 success. |
| `alpha_engine/data/skyrocket_picks.json` | ❌ **MISSING** | n/a | n/a | File never created. Workflow registered, scan runs, but `_save_picks()` only writes when picks list is non-empty (line 382 of `alpha_engine/strategies/skyrocket_detector.py`: `if save and picks:`). 5+ days of empty scans = 5+ days of `git add` 128 errors. |
| `alpha_engine/data/tradingagents_picks.json` | ❌ MISSING | n/a | n/a | Emitter is opt-in (`TRADINGAGENTS_EMITTER_ENABLED=1`) and **no workflow exists** to run it on a schedule. `ls .github/workflows/*tradingagents*` returns nothing. |
| `mercury2/data/active_picks.json` | ✅ | 2026-05-08 14:32 UTC | 6 active | Healthy. `mercury2-scan.yml` is succeeding hourly. |
| `mercury2/data/closed_picks.json` | ✅ | 2026-05-08 14:32 UTC | 382 closed | Healthy. |
| `mercury2/mercury2_fast_picks.json` | ⚠️ STALE | 2026-03-10 00:21 UTC (~2 months stale) | 47 picks | `mercury2_fast` workflow is no longer refreshing this file. |
| `skyrocket_detector/data/alerts.json` | ✅ | 2026-05-08 18:03 UTC | 2 alerts | This is the **CRYPTO** ML detector (different module) used purely as ML enrichment in `dashboard_generator.py:2811` — NOT the EQUITY skyrocket lane. |
| `alpha_engine/data/active_picks.json` | ✅ | 2026-05-08 14:32 UTC | 118 picks | Carries CRYPTO/STOCKS/EQUITY/FOREX picks. **Zero rows have `concept_family` or `pick_type` stamped.** UEPS is NOT here — the 22 UEPS picks live exclusively in `ueps_picks.json` and reach `dashboard_data.json` via the JSON_PICK_SOURCES loader. |
| `audit_dashboard/data/dashboard_data.json` | ✅ | 2026-05-08 14:32 UTC | 65 active + 222 active_raw + 3500 recent_closed | Aggregator JSON consumed by `template.html`. |

---

## 3. JSON_PICK_SOURCES Registry Cross-Check (`audit_trail/dashboard_generator.py`)

All 5 long-horizon sources ARE registered:

| Source | Line | Path | Status |
|--------|------|------|--------|
| `mercury2` | 3519 | `mercury2/data/active_picks.json` + `mercury2/data/closed_picks.json` | ✅ EMITTING (108 closed in dashboard_data) |
| `tradingagents` | 3956–3960 | `alpha_engine/data/tradingagents_picks.json` | ⚠️ REGISTERED but **NO emitter workflow + file missing**. Resolver is also wired (`audit_trail/universal_pick_resolver.py:223`). 0 rows visible. |
| `skyrocket_detector` | 3971–3975 | `alpha_engine/data/skyrocket_picks.json` | ⚠️ REGISTERED but file missing → 0 rows visible. Workflow runs but fails at `git add` step daily. |
| `ueps` | 3984–3988 | `audit_dashboard/data/ueps_picks.json` | ✅ EMITTING. 38 rows in `picks.active_raw` (22 active + 16 visible in `picks.active`). |
| `revival_mercury2` | 3614 | `genome/data/revival_mercury2_picks.json` | (separate Mercury2 sibling) |

The PR #547 path (`sync_to_active_picks()` writes to `alpha_engine/data/active_picks.json`) is now redundant — `_extract_picks()` reads `ueps_picks.json` directly via the `long_picks/swing_picks/short_picks` schema branch (lines 7194–7221).

---

## 4. CI Health (`gh run list`)

| Workflow | Last 5 conclusions | Verdict |
|----------|---------------------|---------|
| `ueps-pick-runner.yml` | 5× success | ✅ HEALTHY (4-hourly cron firing) |
| `mercury2-scan.yml` | 5× success | ✅ HEALTHY (hourly cron firing) |
| `skyrocket-detector.yml` (CRYPTO ML — ML enrichment only) | 5× success | ✅ HEALTHY |
| `penny-skyrocket-runner.yml` (EQUITY penny lane — what we care about) | **5× failure** since 2026-05-04 | ❌ BROKEN |

**Penny-skyrocket failure root cause** (verified from `gh run view 25563493178 --log-failed`):
```
fatal: pathspec 'alpha_engine/data/skyrocket_picks.json' did not match any files
##[error]Process completed with exit code 128.
```
The scanner is gated by `if save and picks:` at `alpha_engine/strategies/skyrocket_detector.py:382` — the JSON is only written when at least one pick survives the score≥50 gate. Empty days (the common case for the 60-symbol penny watchlist) leave the file uncreated, then the workflow's `git add` step exits 128. The fix is one of:
- Always write the JSON (even with empty picks: `{"count": 0, "picks": []}`), OR
- Make the workflow tolerant: `git add ... 2>/dev/null || true` and `git diff --cached --quiet && exit 0`.

The earlier session (commit `0b6fcf7e8db` 2026-05-08 T+100m, `ea9dccbe901` T+160m) already diagnosed this as "git-push race" + drafted a `safe_commit_push.sh` patch. That patch is **drafted, not applied** — penny-skyrocket has zero bytes of pick data on /audit.

---

## 5. Concept Taxonomy (PR #548) — Two-Layer Bug

### Bug A: `_normalize_pick()` drops `pick_type`

`audit_trail/dashboard_generator.py:6961–7184` builds the normalized pick dict with a hard-coded field whitelist. **`pick_type` is NOT copied** from `raw`. UEPS source rows DO carry `pick_type="long_term_value"` (verified in `audit_dashboard/data/ueps_picks.json` row schema, line `pick_type: long_term_value`), but after `_normalize_pick()` the field is None.

### Bug B: Concept registry only matches `ueps_` prefix, not bare `ueps`

`alpha_engine/concept_registry.py:186`:
```python
if pick_type == "long_term_value" or source_lc.startswith(("value_screener", "ueps_")):
    return "long_term_value"
```
The dashboard's `dashboard_source_system` rewrites `source_system="value_screener"` → `source_system="ueps"` (no underscore). So neither branch fires:
- `pick_type == "long_term_value"` fails because of Bug A.
- `source_lc.startswith("ueps_")` fails because the actual value is exactly `"ueps"`.

Result: **all 38 UEPS rows in `dashboard_data.json` are stamped `concept_family="standard"`** instead of `long_term_value`. Verified empirically:
```
concept_family: {'standard': 287}    # active + active_raw, ALL "standard"
LONG_TERM filter would show: 0 of 287 active+active_raw picks
UEPS picks loaded: 38; with pick_type=long_term_value: 0
```

### Bug C: Concept dropdown lists wrong families

`audit_dashboard/template.html:1140` lists: `breakout_momentum, mean_reversion, trend_following, value_quality, sentiment_driven, statistical_arb, meme_coin, cta_systematic, standard`.

The registry actually emits: `long_term_value, skyrocket, tradingagents, penny_stock, meme_coin, mercury2, reverse_engineer, standard`.

**Only `meme_coin` and `standard` overlap.** A user picking "Value/Quality" or "Trend Following" filters to zero rows because no pick has those families. The `long_term_value`, `skyrocket`, `tradingagents`, `penny_stock`, `mercury2`, `reverse_engineer` chips that PR #548 was supposed to expose are **not user-selectable**.

### Bug D: `recent_closed` (3500 rows) has zero `concept_family` stamping

`assign_concept_fields()` is called inside `_normalize_pick()` (line 7149), which IS hit for both active and closed paths. But `dashboard_data.json` shows `concept_family: '<none>'` on 3500/3500 closed rows vs `'standard': 287` on active+active_raw. Likely a separate code path bypasses `_normalize_pick()` for the closed loader (the closed-pick file usage at line 7457 traverses different shape). Result: historical performance aggregation by concept family is impossible — the dashboard cannot answer "what is the realized PF of `concept_family=skyrocket` over the last 30 days?".

---

## 6. POSITION classification (PR #545 outcome)

PR #545 added `time_horizon_days` → POSITION mapping in `cross_aggregation/timeframe_classifier.py:202–223`. The classifier IS fired for every pick at line 7029 of dashboard_generator.

Live counts:
- `active`: 16 EQUITY × POSITION (vs **0 baseline pre-PR #545**) — PR #545 working.
- `recent_closed`: 0 EQUITY × POSITION of 277 EQUITY closed. **The fix is forward-only** — historical closed rows don't get reclassified. So the historical-perf pane on /audit still shows EQUITY × POSITION as a sample-size-zero bucket.

The `LONG_TERM` filter dropdown alias (`f.timeframe === 'LONG_TERM'`) requires `pick_type === 'long_term_value'` to match (template.html:6757–6758). Because of Bug A above, this filter is **broken** — it returns 0 rows even though 22 UEPS POSITION-class picks are loaded.

---

## 7. Top-5 Highest-Leverage Integration Fixes

Ranked by ROI (closes the largest gap in long-term EQUITY pick visibility per LOC of work):

### #1 — Fix `_normalize_pick()` to copy `pick_type` and `holding_horizon` from raw
**Where:** `audit_trail/dashboard_generator.py:6961` dict literal.
**Effort:** 2 lines. Add `"pick_type": raw.get("pick_type"), "holding_horizon": raw.get("holding_horizon"),`.
**Unblocks:** Bug A → fixes the `LONG_TERM` filter (currently 0 hits), enables `concept_family=long_term_value` derivation, makes UEPS picks discoverable on /audit.

### #2 — Patch `concept_registry.py` to match bare `"ueps"` and `"value_screener"` strings
**Where:** `alpha_engine/concept_registry.py:186`.
**Effort:** 1 line. Change `source_lc.startswith(("value_screener", "ueps_"))` to `source_lc in ("value_screener", "ueps") or source_lc.startswith(("value_screener_", "ueps_"))`.
**Unblocks:** Bug B → 38 UEPS picks correctly tagged `long_term_value` regardless of #1. Defense-in-depth with #1.

### #3 — Fix `penny-skyrocket-runner.yml` to tolerate empty-scan days
**Where:** `.github/workflows/penny-skyrocket-runner.yml:74` AND/OR `alpha_engine/strategies/skyrocket_detector.py:382`.
**Effort:** Either (a) drop the `and picks` guard in `_save_picks` so the file is always written (even with `count: 0`), or (b) wrap the `git add` step with `|| true` and skip commit on empty diff. The committed change in `0b6fcf7e8db`/`ea9dccbe901` already drafted patches — push them.
**Unblocks:** 5+ consecutive daily failures stop. Penny skyrocket lane begins emitting on /audit.

### #4 — Replace concept dropdown options with the actual registry families
**Where:** `audit_dashboard/template.html:1140`.
**Effort:** ~10 lines of HTML. Replace the 9 stale options with the 8 real families: `long_term_value, skyrocket, tradingagents, penny_stock, meme_coin, mercury2, reverse_engineer, standard`.
**Unblocks:** Bug C → users can actually filter by concept on /audit, which is the entire point of PR #548. With fixes #1 + #2 in place, the chips become useful immediately.

### #5 — Stamp `concept_family` on closed-pick rows (the 3500 in `recent_closed`)
**Where:** Whatever code path produces `picks.recent_closed` in `dashboard_data.json` — likely a separate adapter that bypasses `_normalize_pick()`. Trace from `picks.recent_closed` populator near line 7457 (`for sys_name, active_path, closed_path in JSON_PICK_SOURCES`).
**Effort:** ~5 lines, ensure the closed-pick branch also calls `assign_concept_fields()`.
**Unblocks:** Bug D → historical-perf aggregation by concept family becomes possible. /audit can finally answer "is `mercury2` net-positive across 108 closed trades?", "is `skyrocket` worth keeping?", etc. — which is what the Concept Taxonomy work was for.

---

## 8. Bonus integration debt (not in top 5)

- **`tradingagents_picks.json` has no scheduled emitter.** PR #544 ships the emitter module but no workflow. Either schedule it or remove the `JSON_PICK_SOURCES` registration to avoid noise.
- **`mercury2_fast_picks.json` is 2 months stale.** The `mercury2-fast-scan.yml` workflow exists but evidently isn't refreshing the file. 47 frozen picks.
- **PR #547's `sync_to_active_picks()` path is dead code** now that PR `B28` (2026-05-01) wires UEPS directly via JSON_PICK_SOURCES. Worth deleting to reduce confusion.
- **EQUITY × POSITION on closed rows is permanently 0** unless we run a one-shot backfill pass that re-classifies historical closed picks using `classify_timeframe()` on their original raw JSON. Low ROI but valuable for a single-shot historical-perf snapshot.

---

## Sources verified

- `git log --oneline --all` (2026-05-08), `gh pr view 545..549`, `gh run list` for all 4 workflows
- `audit_dashboard/data/ueps_picks.json` (2026-05-08 17:08 UTC)
- `audit_dashboard/data/dashboard_data.json` (2026-05-08 14:32 UTC) — 65 active, 222 active_raw, 3500 recent_closed
- `alpha_engine/data/active_picks.json` (2026-05-08 14:32 UTC) — 118 rows, 0 stamped
- `mercury2/data/active_picks.json`, `mercury2/data/closed_picks.json`, `mercury2/mercury2_fast_picks.json`
- `audit_trail/dashboard_generator.py` lines 3507–4014 (JSON_PICK_SOURCES), 6961–7184 (`_normalize_pick`), 7186–7221 (`_extract_picks` UEPS branch)
- `alpha_engine/concept_registry.py:160–211` (`get_concept_family`)
- `cross_aggregation/timeframe_classifier.py:160–254` (`classify_timeframe` + `STRATEGY_TIMEFRAME` + `SYSTEM_TIMEFRAME_DEFAULT`)
- `audit_dashboard/template.html:1139–1140` (filter chips), 6755–6779 (`matchFilter`)
- `gh run view 25563493178 --log-failed` (penny-skyrocket failure root cause)
- `alpha_engine/strategies/skyrocket_detector.py:343–402` (`scan` + `_save_picks` empty-pick gate)
- `updates/long_term_value_project_2026-04-27/PROJECT.md` + `findings/SYNTHESIS.md`
