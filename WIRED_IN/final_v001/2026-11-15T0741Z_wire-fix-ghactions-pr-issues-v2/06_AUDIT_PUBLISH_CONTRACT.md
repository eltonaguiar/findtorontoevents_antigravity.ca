# 06 — Audit Publish Contract (`findtorontoevents.ca/audit`)

Every verdict here must render on `/audit`. The contract is split into sidecar
JSON (data), `template.html` columns (view), and the deploy list (delivery). A
missing piece is a broken promise; enforce it with the acceptance test below.

## 1. Sidecar JSON (data layer)

Written by the forward-ledger-sync workflow (see `03_MEASUREMENT_WIRING.md`):

| File | Required fields |
|------|-----------------|
| `audit_dashboard/data/dashboard_data.json` | picks with `strategy_id`, `asset_class`, `gate_state`, `net_pnl`, `excess_pp`, `n_closed`, `ci_low`, `ci_high` |
| `audit_dashboard/data/benchmark_prices.json` | daily `{date, SPY, BTC-USD, ...}` closes |
| `audit_dashboard/data/forward_clock.json` | `ledger_rows`, per-strategy `{trades, windows, interim_verdict}` |
| `audit_dashboard/data/pick_excess_returns.json` | per-pick `gross_pp`, `net_pp`, `benchmark`, `t_cluster` |
| `audit_dashboard/data/data_integrity_report.json` | ghost rows, dup groups, flat-close ratio, frozen cohorts |

Rules:
- `net_pp` must equal `gross_pp − class_cost`; never publish gross as "excess".
- `gate_state ∈ {KILLED, TESTING, SHADOW, PROMOTED}` exactly.
- Every number that appears in a column must exist in a sidecar (no client-side
  invention; the "numbers must trace to an artifact" rule).

## 2. Dashboard view (`audit_dashboard/template.html`)

- Columns: **Strategy · Class · Gate · Forward n · Net PnL · Excess vs Bench ·
  CI(low,high)**.
- The `excess_column.js` sort/filter and `forward_clock.js` panel mount via
  script tags (present only in PR #785 today).
- Shadow rows visibly labelled `SHADOW` / `NOT_MEASURED` — never blank-and-green.

## 3. Delivery (the 404 trap)

The three FTP site functions in `.github/workflows/audit-dashboard.yml` use a
hard-coded JS list. Add:
```
audit_dashboard/excess_column.js
audit_dashboard/forward_clock.js
```
at `:1167`, `:1303-1304`, `:1409-1410`, and in `tools/deploy_audit_files.py`.
Sidecars ship via the existing `audit_dashboard/data/*.json` glob.

## 4. Acceptance test (must pass before "live")

```bash
# 1. tags present in the durable source
git grep -q "forward_clock.js" origin/main -- audit_dashboard/template.html

# 2. sidecars exist and are fresh
python3 - <<'PY'
import json,os,time
for f in ["benchmark_prices.json","forward_clock.json","pick_excess_returns.json","data_integrity_report.json"]:
    p="audit_dashboard/data/"+f
    assert os.path.getsize(p)>0, p
    age=(time.time()-os.path.getmtime(p))/3600
    assert age<48, f"{f} stale {age:.1f}h"
print("sidecars ok")
PY

# 3. live assets serve (not 404), and the column renders
curl -fsS https://findtorontoevents.ca/audit/forward_clock.js >/dev/null
curl -fsS https://findtorontoevents.ca/audit/excess_column.js   >/dev/null
curl -fsS https://findtorontoevents.ca/audit/data/forward_clock.json | head
```

## 5. Reporting semantics (anti-misleading)

- A class with `n_closed < 100` is **never** shown as "profitable"; it shows
  `TESTING (n/100)`.
- A drawdown improvement with flat/negative wealth vs benchmark is labelled
  **"risk-reduced beta"**, not alpha.
- `money_ready` stays `[]` until a strategy is `PROMOTED`. /audit must reflect
  the empty truth, not a hopeful placeholder.
