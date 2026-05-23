# tests/test_quant_auditor_fixtures/

Sample inputs for testing the `quant-performance-auditor-fast` and
`quant-performance-auditor-deep` agents end-to-end. Each fixture is a
trimmed-down `dashboard_data.json` shaped to exercise one or two rules.

## Fixtures

| File | Exercises | Expected verdict |
|---|---|---|
| `happy_path.json` | All classes meet T2; no alerts | `APPROVE` |
| `unit_mismatch_pnl.json` | `pnl_pct: 52.7` (percent, not decimal) | `REJECT` w/ `rule_id: range:pnl_pct` |
| `forex_stressed.json` | FOREX PF 0.29, WR 45.7, n=1263 | `REJECT` w/ `rule_id: charter:tier-floor` |
| `cross_class_pollution.json` | `multi_asset_copytrader` 5-class drag | `REJECT` w/ `rule_id: charter:cross-class-pollution` (deep only) |
| `borderline_wr.json` | WR 0.495 vs 0.50 floor (delta 0.005) | `WARN` |
| `expired_override.json` + `overrides/EXPIRED.yaml` | Override past `expires_at` | `REJECT` w/ `rule_id: ci:expired-override` |
| `missing_n.json` | Claim cites WR/PF without `resolved_n` | `REJECT` w/ `rule_id: charter:missing-n` |
| `empty_dashboard.json` | All required keys missing | `INSUFFICIENT_DATA` |

## Adding a fixture

1. Build a minimal JSON that contains only the keys the rule under test
   reads (look at the agent profile's "Authoritative inputs" list).
2. Add a row to the table above with the expected `verdict` + `rule_id`.
3. If the fixture pairs with an override, drop a `<ticket_id>.yaml` in
   the same directory (NOT in the repo's `overrides/` — that one is
   production).

## Running

These are stable fixtures, not Python tests. The agent runs against them
via:

```bash
QUANT_AUDITOR_INPUT=tests/test_quant_auditor_fixtures/<fixture>.json \
  claude code agent quant-performance-auditor-fast
```

(Wrapper script TBD; for now invoke via the Claude Code agent UI with
the fixture path manually pasted into the prompt.)

## Why fixtures live here, not in the agent profile

The agent profiles must remain prose. Test data in YAML/JSON belongs in
the repo's test tree so it survives profile rewrites and shows up in
git blame when behaviour changes.
