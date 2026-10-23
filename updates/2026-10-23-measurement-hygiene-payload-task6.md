# Task 6: Emit top-level `measurement_hygiene` payload block — 2026-10-23

## What was added

`generate()` in [`audit_trail/dashboard_generator.py`](../audit_trail/dashboard_generator.py:18743)
now emits a **top-level** `measurement_hygiene` payload key (NOT nested under
`payload["summary"]`), immediately before the payload is sanitized/written via
`_write_text_file`.

Shape (flag `MEASUREMENT_HYGIENE_V1=1`):
- `enabled: true`
- `banner_text`: `"Measurement ≠ permission — only ledgers passing n≥100, PF≥1.5, CI-LB≥1.2, MDD≤20% are shown."`
- `excluded_ledgers`: list of `"{strategy}|{symbol}"` for every ledger whose gate verdict != `"OK"`
- `gate_definitions`: the four gate thresholds (`n`, `pf_net`, `pf_net_ci_lb`, `mdd`)

When the flag is OFF, the block collapses to `{"enabled": false}`. The legacy
`payload["summary"]["measurement_hygiene"]` block is left untouched.

## Bug found while verifying (latent, pre-existing)

`generate()` raised `TypeError: 'int' object is not subscriptable` at
[`dashboard_generator.py:11061`](../audit_trail/dashboard_generator.py:11061)
because `crypto_signal_engine/data/audit.json` contains `new_picks` as an
**int** (a count) instead of a list. The `collect_events`/audit source-3
loop did `cse["new_picks"][-20:]`, which crashes on an int. This would also
break any dashboard build whenever that sidecar file is in the count shape.

Fixed with a defensive guard:
- Only iterate `new_picks` when it is a non-empty list; otherwise skip the
  source gracefully.

## Verification

- TDD: wrote [`tests/test_measurement_hygiene_payload.py`](../tests/test_measurement_hygiene_payload.py)
  first; watched it fail (missing top-level key), then implemented.
- Run: `MEASUREMENT_HYGIENE_V1=1 python3 -m pytest tests/test_measurement_hygiene_payload.py -q --tb=long`
  → `1 passed`.
- Instrumented `audit_trail/data/dashboard_payload.json`: top-level
  `measurement_hygiene` present, `enabled=True`, exact `banner_text`,
  `excluded_ledgers` is a list (n=458), `gate_definitions` has all 4 keys,
  and `payload["summary"]["measurement_hygiene"]` remains present.
- Disclaimer invariant: `audit_dashboard/template.html` already renders a
  persistent "not financial advice" footer (line ~18843), so the measurement
  banner is never the only disclaimer on the page.
