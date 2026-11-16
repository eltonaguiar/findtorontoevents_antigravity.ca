# Regression guard for the int CSE new_picks dashboard crash

The generator crash itself is fixed on `main`: `audit_trail/dashboard_generator.py`
`collect_audit_events` now reads

```python
new_picks = cse.get("new_picks") if isinstance(cse, dict) else None
if isinstance(new_picks, list):
```

and skips a count. That was the failure in Unified Audit Dashboard run
`43896182188` (`TypeError: 'int' object is not subscriptable`), which stopped
HTML generation while the writer at `dashboard_generator.py` stores
`"new_picks": len(h_active)`.

What was missing on `main` is a test. This PR adds
`tests/test_dashboard_cse_new_picks.py`, which fails if anyone restores the
unguarded slice. No production code changes.

Local: `python3 -m pytest tests/test_dashboard_cse_new_picks.py -q` → 1 passed.
