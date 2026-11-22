# Ops Runbook — Dashboard Freshness + FX Backfill

**Author:** GitHub Copilot / Mercury-3 AI (`githubcopilot-mercury3AI`)
**Date:** 2026-11-22 06:00 EST
**Scope:** two production fixes identified in Part 3 (`PART3_DATA_FRESHNESS.md`) and Part 2 (`PART2_MEASUREMENT_FIXES.md`).

---

## Fix A — `dashboard_data.json` is ~34 days stale

**Symptom:** `audit_dashboard/data/dashboard_data.json` has `generated_at` = 2026-10-19, while `audit3_ledger.json` = 2026-11-20. The `/audit` headline WR/PF is a month old, and diverges from the ledger.

**Root cause:** the `audit-dashboard.yml` pipeline regenerates the dashboard from a raw DB slice, not the canonical resolved view; it appears to have not run (or been silently skipped) for ~a month.

**Fix steps:**
1. Confirm the hourly cron (`audit-dashboard.yml`, cron `:10`) is actually dispatching — check `gh run list --workflow=audit-dashboard.yml --limit 5`.
2. Regenerate from the canonical view (`audit_trail/dashboard_generator.py`) so `asset_class_health` matches `audit3_ledger.json`.
3. Add a **freshness guard**: display `generated_at` on `/audit` and warn when age > 48h; extend `tools/db_freshness_check.py` to audit sidecars.
4. **Acceptance:** `dashboard_data.json.generated_at` within 24h of the ledger; per-class WR/PF match the ledger.

---

## Fix B — `fx_prices` stale to 2026-02-09 (blocks FOREX)

**Symptom:** FOREX `POD-FOREX-USDJPY-MOMENTUM` (Sharpe 2.02) and the DSR-0.966 `forex_rsi2_mean_reversion` cell cannot be forward-tested; only 12/17 FX instruments measured.

**Fix steps:**
1. Run the existing backfill: `python3 tools/fx_backfill.py` (verify it targets the live price table).
2. Re-run the tribunal (`alpha_engine/audit3_tribunal.py`) so FOREX cells get measured bars.
3. **Acceptance:** audit3 coverage shows FOREX ≥ 90% instruments measured (vs 12/17 now); forward clock gains FOREX rows.

---

## Sequencing

1. **A first** (1–2 h) — it fixes what every visitor sees on `/audit`.
2. **B second** (needs market-data API access) — unlocks the FOREX candidate.
3. Then the CI fix (PR #1048) merges so the gate pipeline is green.

---
*Not investment advice. Ops runbook only.*
