# DATA INTEGRITY — the honest crypto ledger's `entry_price` is systematically corrupt (2026-07-03)

**Author:** claude (fable) · **Severity: P0** — this is the root cause behind months of edge candidates that pass the battery and then dissolve. Bigger than any single strategy.

## Finding
`at_signal_outcomes.entry_price` does not match the market price at signal time. Checked 1,416 CRYPTO rows (post-2026-05-20, honest cohort) against the `crypto_ohlcv` 1h bar at each `created_at` (matched bar is within 0.6h median — not a gap artifact):

| entry vs bar close | share |
|---|---|
| ≤2% (clean) | **29%** |
| 2–5% (borderline) | 21% |
| **>10% (gross error)** | **37%** |
| **>50% (catastrophic / scale bug)** | **7%** |

- Only **5–10% of entries fall within the bar's actual high-low range** — i.e. ~90% of recorded entries are outside the price band the asset traded in that hour.
- The offset is **directional and systematic**: median **(entry−close)/close = +1.27%** (LONG +1.35%, SHORT +1.06%). Means are blown to +19% / +12,000% by the catastrophic outliers.

## Why it matters (it manufactures fake directional edges)
`intrabar_pnl_pct` is resolved relative to `entry_price`. A **systematically +1.3%-high entry**:
- **inflates every SHORT** (short entered at a phantom-higher price → looks more profitable), and
- **deflates every LONG** (bought too high → looks worse).

This mechanically produces the CRYPTO **LONG 0.55 / SHORT 1.40** split I earlier attributed to "bearish regime" — **a large part of that asymmetry is a data artifact, not alpha.** Concretely: luxalgo SHORT reads **PF 1.56** on the ledger but **0.51–0.89** on a bar-clean replay (and doesn't beat random shorts) — a gap consistent with the +1.3% short-inflation. Every SHORT-crypto "edge" this program has surfaced is suspect for the same reason.

## Evidence chain
1. Matched bar is contemporaneous (median 0.6h gap) → not a stale-bar/gap artifact.
2. 90% of entries outside the bar H-L range + 7% off by >50% → `entry_price` is corrupt, not a legitimate finer-grained fill.
3. Systematic +1.3% sign → not zero-mean noise; it biases directional PnL.
4. Ledger PF (1.56) vs bar-clean replay (0.7–0.9) gap matches the bias direction/magnitude.
5. **CLINCHER — the resolver's PnL rides the phantom entry:** across 205 SHORT rows, `corr((entry−close)/close, intrabar_pnl_pct) = +0.16`; shorts with **more-inflated** entries resolve to mean **+1.65%** PnL vs **−1.03%** for low-offset shorts — a 2.7% swing driven purely by the entry offset. This proves `intrabar_pnl_pct` is computed off the contaminated `entry_price`, so the bias flows directly into every verdict.

## Remediation (P0, before ANY ledger-based edge is trusted)
1. **Root-cause `entry_price`** ingestion: the +1.3% systematic bias suggests entry is stamped at signal-generation (a moment before `created_at`, higher in a falling tape) rather than at fill; the >50% outliers are decimal/scale/symbol-mapping bugs. Fix at the writer.
2. **Re-resolve `intrabar_pnl_pct` from bar-aligned entries** (use the `crypto_ohlcv` open/close at `created_at` as the entry, not the stored `entry_price`) into a NEW column/sidecar table (non-destructive; backup `at_signal_outcomes` to `ejaguiar1_backups` first). Then re-run every per-class + per-strategy verdict on the clean cohort.
3. **Quarantine gross rows** (|entry−bar|>10%, 37%) from all verdict-grade queries immediately as a stopgap.
4. Apply the same check to EQUITY/FOREX/COMMODITY (their price feeds differ; verify independently).

## The corrected picture (clean bar-aligned entry replay, first-touch, net 16bp, dedup)
| cohort | contaminated ledger PF | **clean-entry PF** |
|---|---|---|
| CRYPTO LONG (n=432) | 0.55 | **0.66–0.69** (bug deflated) |
| CRYPTO SHORT (n=157) | 1.40 | **1.05–1.14** (bug inflated) |

The bug inflated shorts ~+0.3 PF and deflated longs ~−0.1 PF — most of the apparent L/S asymmetry. With clean entries there is **no promotable directional edge**: LONG still loses (~0.67), and SHORT is only ~1.1 (regime-level in a bearish window, near the random-short baseline — not a durable signal edge). This is the honest crypto picture once the entry bug is removed.

## Bottom line
The program's "no durable edge / everything dissolves" pattern now has a concrete mechanical cause on top of small-sample + regime: **the entry price the PnL is measured from is wrong ~71% of the time and biased +1.3% in the short-favoring direction.** Fixing `entry_price`/re-resolving the ledger is the single highest-leverage action — above any strategy, gate, or new-data work. Until then, treat all ledger directional PnL (especially SHORT-crypto) as unverified. See `FALSIFICATION_luxalgo_short_2026-07-03.md` and the two-control checklist in memory `feedback-entry-price-contamination-regime-2026-07-03`.
