# audit3 v2 gates: expectancy-primary, 2× cost stress, hash provenance (2026-11-19)

Response to `AUDIT3_FEEDBACK_2026-11-19.md` (arena.ai). Full grading in
`docs/AUDIT3_FEEDBACK_RESPONSE_2026-11-19.md`; this file records the code fixes.

## What was broken

1. **The win-rate gate made premia cells unpromotable.** `q_value` came from
   `binom_sf(wins, n)` — a one-sided test of WR > 50% — and PROVEN_T2 additionally
   required a Wilson lower bound above 0.5. A trend/carry cell that loses 65% of the
   time and makes money cannot clear either, at any sample size. WR is only break-even
   at a 1:1 payoff; the ledger's own EQUITY class (60% WR, PF 0.97) is the mirror image.
2. **Trial accounting told two stories.** `summary.n_cells_tested = 45` vs
   `provenance.n_cells_scored_with_dsr = 59` (60 cells have n ≥ 10): DSR was published
   on cells excluded from the BH/Bonferroni family, so the multiplicity correction
   quoted next to it was not the one that produced it.
3. **No hash provenance.** The ledger identified its input only by
   `source: /tmp/audit3/dashboard_data.json`.
4. **No cost-stress view.** A single flat slippage constant per class, with no way to
   see how much of an edge survives doubled costs.
5. **Reconstructed section proxies could be promoted.** Segment membership is rebuilt
   from row fields (`trust_tier`, `grade`, `score`, R:R), not the live gate decision,
   yet a proxy could reach PROVEN_T2.
6. **Public schema spec named the DB host and the credential-resolution path.**

## What changed

- **`evaluate_cell`**: `p_value` = one-sided bootstrap **P(net mean ≤ 0)** with the
  standard **+1 resolution correction**, so a 2,000-resample run reports a floor of
  1/2001 rather than 0 (a zero p gave the top cell a BH q of exactly 0 — infinite
  certainty from a finite simulation); `p_wr` reported as a descriptor; `p_harm` =
  bootstrap `P(net mean ≥ 0)`. BH and the kill gate now operate on expectancy.
- **PROVEN_T2** requires n ≥ 100, net-CI lower bound ≥ **0.05%/trade**
  (`PROVEN_MIN_NET_CI_LO_PCT`),  stable halves, symbol share ≤ 60%, source share ≤ 90% (aggregates), BH q ≤ 0.10,
  DSR ≥ 0.95. Single-emitter cells can be PROVEN but carry `single_source: true`
  and an explicit "not sizing-eligible until replicated" reason — a flag, not a
  block, so the gate does not become unpromotable in the other direction.
- **DSR** is computed and published only for cells with n ≥ 20, so
  `n_cells_dsr_scored == n_cells_tested`; `provenance.registry_note` states the single-N
  rule.
- **Cost stress**: every cell carries `net_ci_pct_2x` and `stress_2x_ok` (2× class
  slippage). Report-only, surfaced as a `2× cost` column on the page.
- **Segments** cap at CANDIDATE with reason `reconstructed section proxy: CANDIDATE is
  the ceiling`.
- **Provenance** gains `generator_version` (`audit3.v2`), `input_sha256`, `git_sha`.
- **`docs/FINANCE_DB_SCHEMA_SPEC.md`** redacted: `mysql.50webs.com` → `<DB_HOST>`,
  credential resolver path removed.
- **`/audit3/`**: `2× cost` column on the class table, provenance rows for version /
  sha256 / git sha, and G1 now described as an expectancy test with WR as descriptor.

## Verification

- `pytest tests/test_audit3_expectancy_gates.py tests/test_audit3_coverage_alpha.py
  tests/test_audit3_tribunal.py tests/test_audit3_evidence.py
  tests/test_audit3_edge_hunt.py tests/test_audit3_selection_alpha.py -q` — see PR.
- New tests: a 33%-WR / 3.0:-0.6 cell is now **PROVEN_T2** with `p_wr > 0.9` and
  `p_value < 0.01`; a 75%-WR / negative-expectancy cell is not promoted; DSR is absent
  on sub-floor cells; a reconstructed segment cannot exceed CANDIDATE; `2×` stress is
  stricter than `1×` and self-consistent; provenance carries the hash.
- Ledger regenerated from the 04:04Z payload; `audit3.v2` conventions block present.
- `/audit3/` inline JS syntax-checked with `node --check`.

Kill rule unchanged (net CI entirely < 0 **and** BH harm q ≤ 0.10). No picks, signals,
sizing or emission paths touched; `/audit`, `/audit2` and `audit-dashboard.yml` untouched.
