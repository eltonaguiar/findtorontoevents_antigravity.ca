# Preventative Plan for Dashboard Data Integrity Issues

## Overview
This document outlines a comprehensive plan to prevent future occurrences of inaccurate or misleading price displays in the audit dashboard (e.g., the “impossible prices” observed in the Momentum Riders portfolio). The focus is on data validation, UI rendering safeguards, testing, and operational monitoring.

## 1. Data Validation Layer
1. **Schema Enforcement** – Define a JSON schema for portfolio objects (including `recent_closed` trades) that requires:
   - `entry_price`, `exit_price`, `take_profit`, `stop_loss` to be positive numbers.
   - `exit_price` must differ from `entry_price` for a closed trade unless the trade is a no‑op.
   - `pnl_pct` and `pnl_usd` to be consistent with price differences.
2. **Server‑Side Checks** – In `audit_dashboard/portfolio_manager.py` (or the data‑generation script), validate each trade against the schema before writing to the JSON file. Log any violations and skip malformed records.
3. **Automated Linting** – Add a CI step that runs a JSON‑schema validator on `audit_dashboard/data/*.json`.

## 2. UI Rendering Safeguards
1. **Explicit Null Handling** – Update `audit_dashboard/claudes_test.html` (and any other rendering templates) to:
   - Use a dedicated formatter for prices:
     ```js
     const fmtPrice = (v) => (v && v > 0) ? fmtUsd(v) : '—';
     ```
   - Guard every display of `exit_price`, `current_price`, and `pnl_usd` with a check for `null`/`undefined`.
2. **Consistent Placeholders** – Show a clear placeholder (`—`) for missing data instead of `$0.00`.
3. **Unit Tests for Rendering** – Write JavaScript unit tests (e.g., using Jest) that feed edge‑case data (zero, null, negative) and assert the correct placeholder appears.

## 3. Data Refresh & Feed Monitoring
1. **Health Checks** – Implement a lightweight health‑check endpoint that verifies the price feed returns non‑zero, recent timestamps for all symbols used in the dashboard.
2. **Alerting** – Integrate with the existing monitoring system (e.g., Prometheus + Alertmanager) to trigger an alert if any `exit_price` equals `entry_price` for a closed trade.
3. **Fallback Logic** – If the live price feed fails, fall back to the last known good price and annotate the UI with a “stale data” badge.

## 4. Documentation & On‑boarding
1. **Developer Guide** – Add a section to `audit_dashboard/README.md` describing the data schema, validation steps, and UI rendering expectations.
2. **Code Review Checklist** – Include items such as “Validate price fields before rendering” and “Ensure placeholder handling for missing values”.

## 5. Continuous Integration / Deployment
1. **Pre‑Commit Hook** – Add a pre‑commit hook that runs the JSON schema validator and the JavaScript lint/tests.
2. **Automated Regression Tests** – In the CI pipeline, spin up a headless browser (e.g., Playwright) to load `claudes_test.html` and verify that no `$0.00` placeholders appear for price fields.

## 6. Timeline & Ownership
| Phase | Tasks | Owner | Estimated Time |
|-------|-------|-------|----------------|
| **Phase 1** – Validation Layer | Implement schema, add server‑side checks, CI lint step | Data Engineering | 2 days |
| **Phase 2** – UI Safeguards | Refactor formatters, add guards, write JS tests | Front‑End Team | 1 day |
| **Phase 3** – Monitoring | Health checks, alert rules, fallback logic | Ops / Reliability | 1 day |
| **Phase 4** – Docs & CI | Update README, add pre‑commit hook, regression tests | DevOps | 1 day |

## 7. Review & Sign‑off
- **Stakeholders**: Lead Engineer, QA Lead, Product Owner
- **Sign‑off Criteria**:
  - All new trades pass schema validation.
  - Dashboard displays `—` for any missing price.
  - No regression failures in CI.
  - Monitoring alerts fire correctly on simulated feed failures.

---
*Prepared by Kilo Code on 2026‑03‑10.*