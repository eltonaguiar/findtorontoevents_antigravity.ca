# Wire the emitting pods to the forward clock (2026-11-20)

**Scope:** `alpha_engine/forward_observations_ingest.py`,
`tests/test_forward_observations_ingest.py`,
`docs/POD_EMISSION_AUDIT_2026-11-20.md` (new).

## What the audit found

An emission audit of every strategy in `reports/audit3_confirmatory.json` against
`trading_picks` and `at_signal_outcomes` (read-only) showed **15 of 23 registered
strategies have zero rows in both tables**, and — more importantly — three pods
whose strategies *do* emit had **no ingest condition**, so their rows could never
become forward observations:

| Pod | Live emitter | Rows | Before |
|---|---|---:|---|
| POD-FABER-TAA (`H-2026-11-19-03`) | `etf_faber_tactical` | 468 | unroutable |
| POD-ETF-DUAL-MOMENTUM (`H-2026-11-19-06`) | `etf_dual_momentum` | 393 | unroutable |
| POD-COMMODITY-ROLL-YIELD (`H-2026-11-19-05`) | `contango_roll_yield` | 10 | unroutable |

Without a condition, `classify()` returned `None` and the rows were counted as
`not_in_any_condition` — the forward clock could never start for these pods even
though the manifest already listed the emitter names.

## Change

Added strategy-keyed, direction-gated conditions for the three hypotheses:

- `H-2026-11-19-03` — `etf_faber_tactical` / `faber_taa` / `faber_taa_paper_pilot`, LONG, EQUITY+ETF
- `H-2026-11-19-06` — `etf_dual_momentum` / `etf_verified_dual_momentum`, LONG, EQUITY+ETF
- `H-2026-11-19-05` — `contango_roll_yield` / `commodity_basis_carry`, LONG+SHORT, COMMODITY

Feature-keyed pods (H-119) still match first, so the existing precedence is
unchanged.

## Verification

- `classify(None,"ETF",strategy="etf_faber_tactical",direction="LONG") == "H-2026-11-19-03"` (and the
  other two) — added as a test, including a direction-gating negative case.
- `pytest tests/test_forward_observations_ingest.py tests/test_forward_observations.py tests/test_audit3_forward_gate.py -q`
  → **55 passed**.

## Still open (product decisions, not wiring)

The other 15 strategies have **no emitter at all** — they cannot accrue until they
are implemented, renamed to a real emitter, or retired. The audit doc recommends a
CI invariant: a manifest entry whose strategies have 0 rows in `trading_picks`
must carry `status: unemitted_approved` or fail.
