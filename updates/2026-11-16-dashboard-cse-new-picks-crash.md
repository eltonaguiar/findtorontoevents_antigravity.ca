# Dashboard deploy dies when CSE new_picks is a count

What was broken: Unified Audit Dashboard run 43896182188 failed in `audit_trail/dashboard_generator.py` `collect_audit_events`. `crypto_signal_engine/data/audit.json` had `new_picks` as an int (the writer at line 15758 stores `len(h_active)`). The reader treated any truthy value as a list and crashed with `TypeError: 'int' object is not subscriptable`. That stopped HTML generation, so https://findtorontoevents.ca/audit/ stayed on the older page that still says "5/5 checks pass" and quotes PF2.6/PF2.4.

What changed: the reader iterates only when `new_picks` is a list of dicts. An int count is skipped. Scanner, sizer, and the database are untouched.

How verified: `python3 -m pytest tests/test_dashboard_cse_new_picks.py -q`. Live page stays stale until this merges and the next `audit-dashboard.yml` run finishes. Run 43927541997 was still in progress when this note was written; it is not cancelled here.

Not this fix: Feed Health 43931137682 (`pm_momentum_signals` missing) and QA Market Validation 43927629856 (equity blank TP/SL) belong to other seats. PR 839 CI is still red and is not this change.
