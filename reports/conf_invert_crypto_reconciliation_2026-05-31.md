# CONFIDENCE_INVERT_CRYPTO — qwen vs zoo reconciliation (2026-05-31)

**Operator decision item #3** — qwen recommended enabling `CONFIDENCE_INVERT_CRYPTO=1` in `.github/workflows/smart-picks-tracker.yml`; zoo Agent-2's STOP report said live data refutes a global inversion. This doc reconciles.

## Verdict: **REJECT qwen's flag. Use targeted 0.8-bucket dampener instead.**

## What the env var actually does

`alpha_engine/smart_picks_engine.py:23-36`:

```python
def _effective_confidence_for_ranking(pick, conf):
    conf = max(0.0, min(1.0, float(conf or 0.0)))
    if os.environ.get("CONFIDENCE_INVERT_CRYPTO", "0") == "1":
        ac = str(pick.get("asset_class") or pick.get("category") or "").upper()
        if ac == "CRYPTO":
            return 1.0 - conf
    return conf
```

It applies a **global linear inversion** (`1.0 - conf`) to every CRYPTO pick's ranking confidence. Top-ranked candidates flip from highest-conf to lowest-conf. This is justified ONLY if WR is monotonically inverted across all buckets.

## Live data (re-verified 2026-05-31, `trading_picks` closed picks)

### CRYPTO
| conf bucket | n     | WR     | avg pnl |
|-------------|-------|--------|---------|
| 0.4         | 522   | 48.7%  | -5.13%  |
| 0.5         | 544   | 47.1%  | +0.93%  |
| 0.6         | 1,297 | 41.9%  | -0.01%  |
| 0.7         | 954   | 42.3%  | +0.11%  |
| **0.8**     | **551** | **22.0%** | **+1.66%** |
| 0.9         | 96    | 37.5%  | -2.98%  |
| **1.0**     | **169** | **52.1%** | **+2.78%** |

**Shape:** NOT monotonic inversion. 0.4→0.8 trends down (48.7%→22.0%), but 1.0 bounces back to **52.1% WR / +2.78% avg-pnl** — the best cohort by avg-pnl in CRYPTO. This is a **localized 0.8-bucket failure** with a partial 0.9 dip.

### FOREX
| conf | n | WR |
|---|---|---|
| 0.6 | 557 | 43.8% |
| 0.7 | 321 | 41.7% |
| 0.8 | 641 | 44.8% |
| 0.9 | 98 | 49.0% |
| 1.0 | 29 | 72.4% |

Flat-to-positive monotonic. **No inversion.** (Flag is CRYPTO-only anyway, but confirms the calibrator is class-specific.)

### EQUITY
n too small per bucket to be decisive (largest bucket n=39 at 0.7); high-conf 1.0 has WR 15.4% on n=26 — weak negative but non-decisive.

## Counterfactual: what would `1 - conf` actually do to CRYPTO ranking?

Inverting maps the top-ranked cohort from **conf=1.0 (52.1% WR / +2.78% avg-pnl)** to **conf=0.4 (48.7% WR / -5.13% avg-pnl)**. The flag would actively *demote the best cohort* and promote a worse-WR-and-negative-pnl cohort. Net expected effect: **WR loss and pnl loss**.

## qwen's premise vs reality

qwen's recommendation appears to derive from the cached `/audit/incidents.html` claim ("conf≥0.9 → WR 14.4%; conf 0.5-0.6 → WR 60.3%") — that claim is **stale and refuted by live DB** (see memory file `project-confidence-trust-edges-2026-05-31.md`). The live evidence shows zoo Agent-2 is correct: there is no global inversion.

## Recommendation

1. **Do NOT enable `CONFIDENCE_INVERT_CRYPTO=1`.** Leave default-off.
2. **Replace** with a targeted 0.8-bucket dampener — multiply effective-confidence by ~0.5 (or hard-block) when `0.75 <= conf < 0.85` and `asset_class == 'CRYPTO'`. Preserves the 1.0-cohort edge (+2.78% avg-pnl) and removes the 22% WR sink.
3. Investigate *why* the 0.8 bucket is broken (likely a single strategy clustering at conf≈0.80 — run `tools/mutation_analysis.py` on CRYPTO closed-picks filtered to `confidence BETWEEN 0.75 AND 0.85`).
4. After remediation, re-run this reconciliation; only revisit a full inversion if monotonicity actually emerges.

## Sources

- Live re-verification: `mysql.50webs.com:ejaguiar1_stocks.trading_picks` (closed picks, `LOWER(category)` filter), 2026-05-31.
- Code: `alpha_engine/smart_picks_engine.py:23-36`.
- Baseline memory: `project-confidence-trust-edges-2026-05-31.md`.
- Disputed source: `audit_dashboard/incidents.html` (cached, pre-fix; do not cite).

## Assigned to

Operator review — this is a production-scoring-path change. Do not admin-merge.
