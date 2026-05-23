# Commit Log

## 2026-03-06
- Added automatic stale‑pick filter to audit dashboard (`audit_dashboard/template.html` and `audit_dashboard/index.html`).
- Filters out active picks older than 168 hours with unrealized PnL within ±0.5 %.
- Prevents old February 28 entries from persisting while keeping Age and PnL columns.
