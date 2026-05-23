# Feedback on Blocker 2 – Placeholder Stats in HC Gate

## Summary
The current HC gate implementation on `alpha_engine/data/active_picks.json` is passing a large number of **placeholder** picks (e.g., `clone_hl_copy_*`). These rows have:
- `trust_tier=""` and `trust_score=null`
- `score == n == fwd_wr` across unrelated symbols, which is not a computed statistic but a static placeholder.
- An inflated pass‑rate (≈ 50 crypto picks) that does not reflect real edge.

The audit (`edge_report.md`) shows only **1 out of 31** active picks truly satisfy the HC gate (≈ 3 %). This discrepancy indicates the pipeline feeding the gate is broken or the gate criteria are being bypassed.

## Detailed Observations
| Class   | Longs | Shorts | Median Score | Naïve Gate Pass |
|---------|-------|--------|--------------|----------------|
| CRYPTO  | 75    | 53     | 21           | 71.0 (50)      |
| FOREX   | 24    | 9      | 15           | 52.0 (0)       |
| EQUITY  | 12    | 12     | 0            | 52.0 (0)       |
| COMMODITY| 9    | 5      | 4            | 51.0 (0)       |
| STOCKS  | 3     | 3      | 0            | 56.0 (0)       |
| FUTURES | 3     | 3      | 0            | 56.0 (0)       |

All crypto rows that pass are clones with identical `score`, `n`, and `fwd_wr` values (e.g., `clone_hl_copy_PensionFund_24M`). This pattern is a strong indicator of **placeholder data** that was never replaced by real calculations.

## Recommendations
1. **Fix the placeholder‑stat pipeline** before any further trading decisions. Identify the source of `clone_hl_copy_*` rows and replace them with genuine back‑test results.
2. **Run `hc_filter.js` against a fresh `dashboard_data.json`** and capture the single genuine HC‑gate pass (as referenced in `edge_report.md`). Include its `id` in the documentation.
3. **Consider dropping the `fwd_wr≥55` label requirement** temporarily and route non‑clone sources (e.g., `luxalgo/dna_winner`) to the account, but be aware this will change the label semantics.
4. **Document the chosen path** (a‑d) in a new markdown file and reference it from `TRADINGVIEW_MCP_GUIDE.md` or `mcp__tv_launch` once the launch command is verified.
5. **Update the edge‑scan catalog** (`updates/2026-04-17-edge-deepscan-5-filter-catalog.md`) with the corrected pick list and note the removal of placeholder rows.

## Action Items
- [ ] Identify and eliminate the generation of `clone_hl_copy_*` rows.
- [ ] Re‑run the HC gate on a clean dataset and record the real pass.
- [ ] Choose one of the options (a‑d) and update the documentation accordingly.
- [ ] Commit the feedback markdown and any related documentation changes to the `main` branch.

*Prepared by Roo, senior software engineer.*