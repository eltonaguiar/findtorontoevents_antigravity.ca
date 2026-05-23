---
name: hypothesis-registry
description: Use when registering a new trading-strategy hypothesis, running the admissibility harness on one, or recording a verdict. Operational workflow for reports/hypothesis_registry.json (rule M-107 — pre-register before any backtest).
---

# hypothesis-registry — register, test, record a strategy hypothesis

Operational skill. For the *why* (the reasoning, what a harness is, the history),
use the companion skill `hypothesis-registry-explained`.

## The one hard rule (M-107)

**Pre-register the hypothesis in `reports/hypothesis_registry.json` and commit it
to `main` BEFORE any backtest touches data.** Registering after you have peeked
at results is p-hacking and the verdict is worthless. No exceptions.

## File

`reports/hypothesis_registry.json` — one JSON file, the canonical registry.
Top-level keys group hypotheses (`hypotheses`, `fork2_new_signals`,
`local_harvest_2026_05_19`, etc.). IDs are `H-NNN`, sequential, never reused.

## Workflow

### 1. Pick the next free ID
Read the registry, scan every list under every key, take `max(H-NNN) + 1`.
Never reuse an ID — even a killed hypothesis keeps its number forever.

### 2. Write the entry — every field is mandatory
```json
{
  "id": "H-0NN",
  "asset_class": "CRYPTO|EQUITY|FOREX|COMMODITY|FUTURES|BOND|ETF",
  "family": "short_snake_case_signal_family",
  "description": "EXACT signal definition — entry, exit, data source, universe, timeframe. No ambiguity: someone else must be able to build it from this text alone.",
  "test_statistic": "walk_forward eff via edge_stability_harness.is_admissible()",
  "acceptance_criteria": {"eff_floor": 0.3, "min_windows_admissible": 3, "same_sign": true, "cost_survival_min": 0.6},
  "economic_prior": "The CAUSAL mechanism — WHY this should work. Not a backtest curve, a cause. A sound prior is not an edge, but a hypothesis with no causal prior is data-dredging.",
  "status": "UNTESTED",
  "registered_at": "YYYY-MM-DD",
  "data_sample_lock": null,
  "result": {"verdict": "UNTESTED", "reason": "Pre-registered per M-107 before backtest."},
  "banned_check": "Proof this is NOT a re-test of a killed family. Name the killed families it is distinct from."
}
```

### 3. Commit the registry to `main` — BEFORE building anything
This is the timestamp that proves pre-registration. Local repo is drift-heavy;
commit via the GitHub contents API against `origin/main`, not local git.

### 4. Build the research tool
`tools/hNNN_<family>.py` — fetch FREE data (api-failover chain for crypto;
yfinance for the rest; cache under `tools/cache/`). Compute the signal
**look-ahead-free** (signal at time *t* uses only data strictly before *t*).
Build a resolved-pick record series — use a continuous-position / multi-asset
book for harness density (the legitimate H-008/H-014 pattern), not a sparse
self-selected subset.

### 5. Run the harness
Import `tools/edge_stability_harness.py` **UNMODIFIED** — never touch
`EFF_MIN` / `MIN_WINDOW_N` / `MIN_STABLE_WINDOWS`. Run `is_admissible()` on the
record series. Apply the post-cost gate (30 bps crypto round-trip; net edge
must keep ≥60% of gross).

### 6. Record the verdict
Write `reports/hNNN_<family>_<date>.md` (n, windows scored, per-window eff,
same-sign check, pooled WR, gross/net edge, cost-survival %, honest next_step).
Update the hypothesis's `result` block + `status` in the registry. Commit.

## Verdicts

- **ADMISSIBLE** — eff≥0.30, same sign, ≥3/5 windows, cost-survival≥60%. Real edge candidate. (0 so far.)
- **REJECTED** — harness scored ≥5 windows but failed (sign-split or sub-floor eff or cost). A genuine kill.
- **UNTESTED** — fewer than 5 windows of ≥80 picks. Data-gap, NOT a pass. Note exactly what density was missing.

## Hard don'ts

- Don't re-test a killed family on the same/similar data — read each killed entry's `next_step`.
- Don't modify the harness thresholds to make something pass.
- Don't backtest before the registry commit lands.
- Don't claim edge from inflated dashboard tiles — the canonical view is `pf_registry.json` (policy-clean, deduped).
- Don't reuse an ID.

## Reference
- Registry: `reports/hypothesis_registry.json`
- Harness: `tools/edge_stability_harness.py`
- Canonical ledger: `audit_dashboard/data/pf_registry.json`
- Verdict context: `reports/EDGE_HUNT_EXHAUSTED_2026-05-18.md` (kill log)
