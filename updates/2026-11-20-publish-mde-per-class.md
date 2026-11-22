# Publish MDE per asset class, and stop sizing studies off the observed mean (2026-11-20)

## What was broken

Two separate problems, both about power numbers nobody could act on.

1. **`mde_pct` and `required_n` were computed per cell, then never read.** In
   `alpha_engine/audit3_tribunal.py` every cell carried both, but
   `alpha_engine/audit3_edge_hunt.py` computed `power_analysis(rows)` — a
   per-asset-class table of realized net-pnl SD and the n that 80% power would
   need — and `render_text` never printed it. The JSON had it; the human output
   did not. A sample-size requirement that nobody reads cannot stop a claim
   being made on an underpowered cell.

2. **`required_n` at the cell level was circular.** It was sized from the
   cell's *observed* mean:

   ```python
   required_n = int(math.ceil((2.8 * sd / abs(mean_net)) ** 2))
   ```

   A lucky mean collapses n to something tiny; a near-zero mean inflates it to
   infinity. Either way the number describes the sample's luck, not the effect
   the study committed to detect. `required_n_mde` already existed in
   `audit3_edge_hunt.py` with a docstring saying exactly this — it just was not
   what the tribunal called.

## What changed

- `alpha_engine/audit3_tribunal.py` — declared `POWER_Z = 2.8` (80% power,
  two-sided 5%) next to `PROVEN_MIN_NET_CI_LO_PCT`, and split the two quantities
  in `evaluate_cell`:

  ```python
  if sd is not None and sd > 0:
      mde_pct = round(POWER_Z * sd / math.sqrt(n), 4)
      required_n = int(math.ceil((POWER_Z * sd / floor_pct) ** 2))
  ```

  `mde_pct` stays observational — the smallest effect *this* sample could
  detect, which shrinks as n grows. `required_n` is now sized against
  `floor_pct`, the materiality floor promotion already has to clear, so the
  effect size is declared rather than measured.

- `alpha_engine/audit3_edge_hunt.py` — `render_text` gained a section F that
  prints the per-class table with an explicit verdict per class:

  ```
  F. POWER (pre-declared MDE 0.05%/trade, z=2.8):
     CRYPTO     n=4182  sd=4.812% need n>=23187 — UNDERPOWERED (4182/23187)
     EQUITY     n=1010  sd=2.104% need n>=3491 — UNDERPOWERED (1010/3491)
  ```

  `powered` / `UNDERPOWERED (have/need)` / `sample size not well-defined` are
  the only three labels — a class is never silently omitted.

- Removed a duplicated `power_analysis` definition (the same function was
  defined twice in the file, lines 441 and 478) and a duplicated
  `power = power_analysis(rows)` call in `build_report`.

## Why UNDERPOWERED is the useful output

"No edge" and "no power" are different statements and the ledger currently
cannot distinguish them. At n=4,182 with a 4.8% per-trade SD, a true 0.05%/trade
edge is undetectable — so a WEAK verdict on CRYPTO is uninformative, not
evidence of absence. Publishing the ratio makes that visible per class instead
of leaving it as a footnote.

## Verification

- `python3 -m pytest tests/test_audit3_edge_hunt.py tests/test_audit3_tribunal.py -q`
  → **49 passed**.
- `required_n_mde` is kept: it remains the documented non-circular primitive for
  callers that want to size a pre-registered gate, and its docstring is the
  reference for why the observed mean must not be used.

## Not done

- No DB run of the edge hunt in this change, so the printed per-class numbers
  above are illustrative of the format, not this ledger's values.
- The `z=2.8` constant is duplicated conceptually with `POWER_Z` in
  `audit3_edge_hunt.py`; both are 2.8 but they are separate module constants.
