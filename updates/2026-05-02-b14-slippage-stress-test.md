# B14 — Liquidity / Slippage Stress Test (2026-05-02)

**Queue item:** B14 (Order 14 in `reports/REMAINING_ACTION_ITEMS_2026_04_30.md`)
**Branch:** `feat/b14-slippage-stress-2026-05-02`
**Risk:** LOW — read-only offline analysis tool

## What this PR ships

### `tools/slippage_stress_test.py` (new)
Simulates 1×, 2×, 3×, and 5× volume-spike slippage scenarios on the full
closed-pick pool in `audit_dashboard/data/dashboard_data.json`.

**Market impact model:** Linear (conservative/worst-case). Doubling position
size doubles round-trip slippage. Square-root model (Almgren-Chriss) would
give ≈ 1.41× at 2× volume — future upgrade.

**Per-strategy output:**
- `SURVIVES_2X`: paper PnL positive AND net PnL positive at 2× cost
- `FAILS_2X`: positive on paper but negative at 2× cost (concentration risk)
- `ALREADY_LOSING`: negative paper PnL (no slippage needed to explain losses)
- `INSUFFICIENT_DATA`: fewer than `--min-n` (default 5) closed picks

**Breakeven multiplier**: cost multiplier at which net sum_pnl crosses zero.
Example: `luxalgo_confluence` breakeven = 1.54 — profitable up to 1.54× base
slippage, then turns negative. At 2× it loses 34.33% net.

### `tests/test_slippage_stress_test.py` (new, 31 tests)
All 31 pass (`python -m pytest tests/test_slippage_stress_test.py -v`).
Covers: cost-deduction math, PF edge cases (inf/None), breakeven multiplier,
ALREADY_LOSING label, INSUFFICIENT_DATA label, asset-class filter, 
`picks.recent_closed` fallback, 2× multiplier doubling, Markdown render.

### `reports/slippage_stress_2026-05-02.json` + `.md` (sample run outputs)
Included to show the operator what the tool produces on today's data.

## Key findings from first run (CRYPTO, n≥5, 1514 closed picks)

| Status | Count |
|--------|------:|
| SURVIVES_2X | 8 |
| FAILS_2X | 17 |
| ALREADY_LOSING | 21 |
| INSUFFICIENT_DATA | 79 |

**Top SURVIVES_2X strategies:**
- `mega_mutation_macd_rsi_m048`: WR 88.2%, PF 11.5, breakeven mult **15.5×** — very robust
- `claude_ml_moderate_mut`: WR 67.3%, PF 3.3, breakeven mult 3.9×
- `MeanReversionBB`: WR 70.0%, PF 3.7, breakeven mult 4.5×

**Critical FAILS_2X findings:**
- `luxalgo_confluence` (n=249): profitable on paper (+115%) but **fails at 1.54×**
  — the most-traded CRYPTO strategy is very close to its slippage breakeven
- `strong consensus (alpha_engine, ml_crypto_pred)` (n=92): fails at 1.13× breakeven

## Wire-Up Rule

**OPT-IN SIDECAR.** No production caller in this PR.

**Wiring plan:**
- Target caller: `audit_trail/dashboard_generator.py`
- Target function: `generate()` → new payload section `picks.slippage_stress`
- Expected wire-up PR: B14-dashboard-panel (target: 2026-05-16, after operator
  validates the stress test output on 2 cron cycles)

## Usage

```bash
# CRYPTO only
python tools/slippage_stress_test.py --asset-class CRYPTO

# All asset classes, min 10 closed picks per bucket
python tools/slippage_stress_test.py --min-n 10

# Custom output paths
python tools/slippage_stress_test.py \
    --out reports/slippage_stress_custom.json \
    --report reports/slippage_stress_custom.md
```

## Prerequisites

Reads:
- `audit_dashboard/data/dashboard_data.json` (already present)
- `tools/data/transaction_costs.json` (already present, from B16)

No new dependencies.
