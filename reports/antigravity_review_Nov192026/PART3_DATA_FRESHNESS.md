# Part 3 · P3-3: Data Freshness & Sidecar Health Audit

**Author:** GitHub Copilot / Mercury-3 AI (`githubcopilot-mercury3AI`)
**Date:** 2026-11-22 04:00 EST
**Method:** filesystem mtime vs `generated_at` vs now (UTC). As of ~2026-11-22 09:00 UTC.

---

## 1. Sidecar freshness table

| Sidecar | `generated_at` | mtime age | Stale? |
|---|---|---|---|
| `audit3_ledger.json` | 2026-11-20T01:57Z | ~51h | ⚠ 2 days |
| `audit3_evidence.json` | 2026-11-19T05:07Z | ~54h | ⚠ |
| `audit2_pods.json` | 2026-11-19T21:00Z | ~52h | ⚠ (static by design) |
| `audit2_forward.json` | 2026-11-19T08:41Z | ~54h | ⚠ |
| **`dashboard_data.json`** | **2026-10-19T19:40Z** | ~57h | 🔴 **~34 days stale** |
| `pick_summary_stats_14d.json` | 2026-11-20T01:24Z | ~52h | ⚠ |
| `pick_summary_stats_48h.json` | 2026-11-20T01:24Z | ~52h | ⚠ |
| `money_ready_verdict.json` | 2026-11-20T01:15Z | ~52h | ⚠ |
| `intrabar_truth_by_class.json` | 2026-11-20T01:11Z | ~52h | ⚠ |

---

## 2. The critical finding

**`dashboard_data.json` is ~34 days stale** (its internal `generated_at` = 2026-10-19, while the ledger is 2026-11-20). This is the file that powers `/audit`. It means:

- Every `/audit` headline number (WR/PF per class) is **a month out of date**.
- This explains the Part 2/1 reconciliation divergences (e.g., COMMODITY PF 5,624 on the dashboard vs ledger 0.12): the dashboard is simply showing stale raw DB slices while the ledger is fresh canonical.

**The rest of the fleet is 2–3 days stale** — acceptable-ish for a weekly cadence, but the `dashboard_data.json` staleness is a production-quality failure.

---

## 3. Recommendation

1. **Fix `dashboard_data.json` regeneration** (the `audit-dashboard.yml` pipeline) so it is rebuilt from the same canonical source as the ledger, on the same schedule.
2. **Add a freshness guard** to the dashboard: display `generated_at` and warn when it exceeds 48h. `tools/db_freshness_check.py` already exists for DB freshness — extend it to audit sidecars.
3. **Acceptance:** `dashboard_data.json.generated_at` within 24h of `audit3_ledger.json.generated_at`, and per-class WR/PF matching the ledger.

---
*Not investment advice. Age measured 2026-11-22 ~09:00 UTC.*
