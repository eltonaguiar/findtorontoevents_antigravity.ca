# Audit GHA: pymysql before resolver + goldmine HTML guards (2026-05-21)

## What was broken

1. **Resolver MySQL path** could fail on runners without `pymysql` preinstalled (install only appeared in later steps with `|| true`).
2. **`data/goldmine/stock_picks.json`** contained an Apache HTML 404 page, causing JSON parse warnings and empty goldmine_stocks feed.
3. **`kimi-goldmine-collector.yml`** used `curl -s`, which saved HTML error bodies as `.json` on HTTP 404.

## What changed

- `audit-dashboard.yml`: `pip install pymysql -q` immediately before `python -m audit_trail.universal_pick_resolver` (fail-hard, no `|| true`).
- `stock_picks.json`: replaced with `{"consensus_picks":[]}`.
- `universal_pick_resolver.py`: `_load_json_source()` skips HTML/non-JSON sources with a warning.
- `kimi-goldmine-collector.yml`: `curl -fsS` + Python JSON validator; writes empty schema on failure.

## Verification

```bash
python3 -c "import py_compile; py_compile.compile('audit_trail/universal_pick_resolver.py', doraise=True)"
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/audit-dashboard.yml'))"
```

Prior `UnboundLocalError` fix remains on main: `bd2014c20be`.
