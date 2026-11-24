# Dashboard generate no longer dies on an integer new_picks count

What was broken: `audit-dashboard.yml` run 43896182188 failed in "Generate dashboard payload and build HTML". `audit_trail/dashboard_generator.py` `collect_audit_events` did `cse["new_picks"][-20:]`. `crypto_signal_engine/data/audit.json` stores `new_picks` as an int count. A non-zero count is truthy, so the slice raised `TypeError: 'int' object is not subscriptable` and skipped the commit/deploy steps.

What changed: iterate `new_picks` only when it is a list of dicts. An int count is skipped. The rest of `generate()` is unchanged.

Files:
- edited: `audit_trail/dashboard_generator.py`
- added: `tests/test_collect_audit_events_new_picks.py`
- added: `updates/2026-11-16-dashboard-audit-events-int.md`

How verified: `python3 -m pytest tests/test_collect_audit_events_new_picks.py -q`.

Impact: the audit-event feed omits CSE rows when the file has a count instead of pick objects. It does not change picks, sizing, or the database. The in-progress run 43927541997 started before this fix and can still fail the same way. Do not stack another `workflow_dispatch` on top of it.
