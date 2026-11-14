# GLOBAL QUICK-WINS — 2026-11-14 audit (systemic, highest leverage first)

Context verified: live `dashboard_data.json` @14:30Z, paylag ≈4586s. All numbers below from 2026-11-14 audits.

---

## 1. Gate the data-hygiene guardian in CI (make integrity gates non-optional)
- **Problem:** Only 7,914/16,126 closed picks (49%) pass integrity gates; headline WR 41.8% / PF 0.94 / compounded −99% is computed on a survivor-biased sample. The guardian exists but is not enforced.
- **Fix:** In `.github/workflows/audit-dashboard.yml`, run `python tools/pi_data_hygiene.py` (exit 1 on findings) as a pre-publish step BEFORE dashboard regen, and fail the job on findings so the leak is visible.
- **Impact:** high · **Effort:** S · **Risk:** low (guardian already returns non-zero).
- **Target:** `.github/workflows/audit-dashboard.yml` (verified), `tools/pi_data_hygiene.py` (verified).
- **<1h:** YES.

## 2. Publish true payload staleness instead of the misleading 5-min refresh
- **Problem:** `payload_lag_seconds≈4586` (≈76 min) while the HTML 5-min meta-refresh reloads the same data — the dashboard looks "fresh" when it re-serves a stale snapshot.
- **Fix:** In `audit_trail/dashboard_generator.py`, emit `payload_lag` into the payload and have `dashboard_freshness.js` render a color-coded banner from it (it already computes per-section ages; wire `payload_lag` in as a source). Stop the meta-refresh from implying regeneration.
- **Impact:** high (trust) · **Effort:** S · **Risk:** low.
- **Target:** `audit_trail/dashboard_generator.py`, `audit_dashboard/dashboard_freshness.js` (both verified).
- **<1h:** YES.

## 3. Stop pinning crypto current_price to entry — surface true price age
- **Problem:** BTC/XRP `current_price` pinned to entry (stale); the "1.9h ago" banner reflects signal age, not price freshness.
- **Fix:** In `alpha_engine/universal_price_enricher.py`, when both Binance and yfinance fetches fail, set `current_price=None` + a `price_freshness` flag instead of falling back to entry; the dashboard label should read *price* age, not signal age.
- **Impact:** high (data integrity) · **Effort:** S/M · **Risk:** med (crypto rows may show unset price until next successful fetch).
- **Target:** `alpha_engine/universal_price_enricher.py` (verified).
- **<1h:** mostly YES (small enricher edit + one label change).

## 4. Disclose survival bias: render dual-cohort headline numbers
- **Problem:** Headline WR/PF/compounded hide the 49% gate-passing sample; readers misread as full-population performance.
- **Fix:** In `audit_trail/dashboard_generator.py`, emit both RAW and GATE-PASSING cohort summaries + counts, and add one caveat line to the template next to the headline.
- **Impact:** med/high (honesty) · **Effort:** S/M · **Risk:** low.
- **Target:** `audit_trail/dashboard_generator.py` (verified).
- **<1h:** YES.

## 5. Preserve auto-expired picks as a tagged cohort instead of silent removal
- **Problem:** 8,888 auto-expired picks are removed pre-resolution, silently deflating/inflating survivor stats and hiding churn.
- **Fix:** In `alpha_engine/active_picks_sync.py:131` `compute_verdict`, keep expired rows with `exit_reason=AUTO_EXPIRED` (+ a cutoff) so the hygiene gate can report both populations; do not drop them before resolution.
- **Impact:** med/high · **Effort:** M · **Risk:** med (ripples into resolver/backtests).
- **Target:** `alpha_engine/active_picks_sync.py` (verified; `compute_verdict` @ line 131).
- **<1h:** NO.

## 6. Workflow hygiene: disable 20 never-run + triage stale failures
- **Problem:** 364–365 workflows; 20 never run; many stale; failures cluster in trading/price/DB pipelines.
- **Fix:** Add a small nightly cron job (or extend audit-dashboard.yml) that queries `gh api` for workflows with no run in 30d and disables them; also add `workflow_dispatch` rerun of stale failed jobs. Keep it additive — no deletion.
- **Impact:** med (CI signal-to-noise) · **Effort:** M · **Risk:** low if disable-only.
- **Target:** `.github/workflows/audit-dashboard.yml` (verified).
- **<1h:** NO.

## 7. Annotate "1.9h ago" banner as signal-age, and co-display price-age
- **Problem:** Single banner conflates signal age with price freshness (compounds #3).
- **Fix:** In `audit_dashboard/dashboard_freshness.js`, relabel the banner to "signal age" and add a second age chip for price data (using the #3 flag).
- **Impact:** low/med · **Effort:** S · **Risk:** low.
- **Target:** `audit_dashboard/dashboard_freshness.js` (verified).
- **<1h:** YES.

---

### Verifiability footnote (2026-11-14, worktree `finpredict-v3`)
All cited target paths verified present via `ls`/`grep`:
- `tools/pi_data_hygiene.py` — EXISTS (has `sys.exit(main())` @ line 324).
- `alpha_engine/universal_price_enricher.py` — EXISTS (Binance endpoints + yfinance fallback).
- `alpha_engine/active_picks_sync.py` — EXISTS (`compute_verdict` @ line 131).
- `audit_trail/dashboard_generator.py` — EXISTS.
- `audit_dashboard/dashboard_freshness.js` — EXISTS (per-section EST age engine).
- `.github/workflows/audit-dashboard.yml` — EXISTS (91,496-byte workflow; confirmed via `ls`).

Nothing in this file is UNVERIFIED; all six anchors confirmed on-disk.
