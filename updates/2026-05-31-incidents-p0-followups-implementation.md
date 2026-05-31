# Incidents P0 Follow-ups — 2026-05-31

**Branch:** `fix/incidents-p0-followups-2026-05-31`  
**Builds on:** PR #126 (data integrity + FOREX consolidation + UNKNOWN backfill)

---

## 1. Ghost rows (`tools/dedup_trading_picks_ghosts.py`)

**Incident:** OVERALL #9 — 56k ghost rows in `trading_picks`.

**Finding (live DB 2026-05-31):** Zero cohorts match the strict ghost definition  
(same category/strategy/symbol/direction/pnl/entry_price with ≥50 rows and ≤1 distinct `created_at` day).  
The historical MATICUSDT/quan_engine burst appears already cleaned.

**Shipped:** Guarded dedup tool (dry-run default, `--apply --limit N`) + JSON report  
`tools/trading_picks_ghost_dedup_report.json`. Re-run after future writer regressions.

**Incident status:** RESOLVED (no active ghost cohorts; tool + report in repo)

---

## 2. Signal outcomes pipeline (`active_picks_sync` + `forward_validator`)

**Incidents:** OVERALL #15 (upstream writer), #10 (signal_outcomes stale)

**Already on main:**
- `alpha_engine/active_picks_sync.py` with `--apply` + `ACTIVE_PICKS_SYNC_APPLY=1`
- `.github/workflows/outcome-resolver.yml` runs sync per asset class hourly
- Git add pathspec fixed (`closed_picks.json` optional `-f` add)

**Added this PR:**
- `forward_validator.py`: opt-in inline sync via `FORWARD_VALIDATOR_ACTIVE_PICKS_SYNC=1`
- Updated `active_picks_sync.py` header (no longer “dry-run only”)

**Incident status:** IN_PROGRESS (CI path live; monitor `at_signal_outcomes` freshness on next cron)

---

## 3. trust_score backfill (`tools/backfill_trust_score.py --mysql`)

**Incident:** OVERALL trust_score NULL on 99.99% of closed picks

**Bug fixed:** MySQL path referenced non-existent `trust_tier` column → always no-op.

**New path:** Batch-fetch NULL rows → `enrich_picks_with_trust_score()` → UPDATE by id  
with backup table snapshot.

**Live apply (2026-05-31):** 2,119 rows enriched; backup `trust_score_backfill_bak_20260531_022847Z`

**Incident status:** IN_PROGRESS (~1,648 NULL remain on active/open rows — expected)

---

## 4. HC JS/Python parity (`tests/test_hc_js_python_parity.py`)

**Incident:** OVERALL #25 — HC eligibility drift between `hc_filter.js` and `dashboard_hc_rules.py`

**Shipped:**
- `tests/fixtures/hc_parity_corpus.json` — 6 canonical pick fixtures
- `tests/hc_parity_runner.js` — Node sidecar for `passesHighConvictionPick`
- `tests/test_hc_js_python_parity.py` — pytest parametrized cross-language assert  
  (uses live `config/hc_gate_params.json` on both sides)

**Verification:** `pytest tests/test_hc_js_python_parity.py -q` → 6/6 pass

**Incident status:** RESOLVED (parity corpus + CI test; extend corpus when gates change)

---

## Verification commands

```bash
export DB_PASS_STOCKS=...
python3 tools/dedup_trading_picks_ghosts.py
python3 tools/backfill_trust_score.py --mysql
pytest tests/test_hc_js_python_parity.py -q
node tests/test_hc_filter.js
python3 -c "import py_compile; py_compile.compile('alpha_engine/forward_validator.py', doraise=True)"
```

---

## Files changed

| File | Purpose |
|------|---------|
| `tools/dedup_trading_picks_ghosts.py` | Ghost cohort scan + capped delete |
| `tools/backfill_trust_score.py` | Fix MySQL backfill (no trust_tier) |
| `alpha_engine/forward_validator.py` | Opt-in active_picks_sync hook |
| `alpha_engine/active_picks_sync.py` | Docstring accuracy |
| `tests/fixtures/hc_parity_corpus.json` | HC parity fixtures |
| `tests/hc_parity_runner.js` | Node HC runner |
| `tests/test_hc_js_python_parity.py` | Cross-language parity tests |

---

**Generated:** 2026-05-31T02:30Z
