# Forward-Only Edge Audit — 2026-04-30

**Goal:** Answer the operator's honest question: "If I put real money in there, would I have made a profit?"
**PR:** feat/forward-edge-audit-2026-04-30
**Status:** Shipped (B16 from `reports/REMAINING_ACTION_ITEMS_2026_04_30.md`)

## What shipped

- **`tools/forward_edge_audit.py`** — New read-only analytics tool that produces a daily artifact with:
  - Per-strategy Win Rate, Profit Factor, after-cost net PnL
  - Wilson 95% confidence interval lower bound on WR (guards against small-sample promotion)
  - Symbol concentration (top-3 share) to flag single-stock / single-pair risk
  - Capacity estimate (picks/week from closed_at timestamps)
  - Two pass/fail gates: `after_cost_mean_pnl > 0` AND `wilson_lb_wr ≥ 50%`

- **`tools/data/transaction_costs.json`** — Per-asset-class round-trip cost config (bps). Tunable by the operator without code changes. Defaults: CRYPTO 30bp, EQUITY 10bp, FOREX 8bp, COMMODITY 15bp.

- **`tests/test_forward_edge_audit.py`** — 44 tests covering all math functions, aggregation logic, artifact generation, and integration against the live `dashboard_data.json`.

- **`reports/feedback/B16-*.md`** — Multi-AI review files (§5 protocol).

## Key findings from first run (2026-04-30)

**5 strategies pass both gates (n ≥ 10):**

| Strategy | AC | WR% | Wilson lb% | After-cost PnL/trade | picks/wk |
|---|---|---|---|---|---|
| st_fear_greed_contrarian | CRYPTO | 90.9% | 80.4% | +0.955% | 37.1 |
| rs-breakout-scout | EQUITY | 77.8% | 54.8% | +2.481% | 2.0 |
| mega_mutation_macd_rsi_m048 | CRYPTO | 88.2% | 65.7% | +4.342% | 11.7 |
| multi_period_rsi_confluence_eth | CRYPTO | 81.8% | 52.3% | +0.517% | 11.0 |
| combined_confidence | FOREX | 90.0% | 59.6% | +0.132% | 3.1 |

**Asset-class after-cost reality:**

| Asset Class | Total n | WR% paper | After-cost sum |
|---|---|---|---|
| CRYPTO | 1231 | 42.3% | **−122.2%** |
| EQUITY | 144 | 55.6% | **+132.9%** |
| FOREX | 845 | 47.3% | **−44.6%** |
| COMMODITY | 647 | 43.0% | **−94.2%** |

After realistic transaction costs, only EQUITY produces a positive aggregate after-cost PnL across the entire closed book. This does not mean EQUITY is the only tradeable class — it means the EQUITY strategies in the closed book happen to have better per-trade edge than the friction costs.

**Zero-WR strategies flagged for kill-list review:** `goldmine_6x_consensus` (EQUITY, n=17, 0% WR), `battleground_ml_relaxed_mut` (CRYPTO, n=16, 6.2% WR after noise filter), others listed in the artifact.

## Wire-Up Rule compliance

This tool is an **opt-in sidecar**. No production caller yet.

**Wiring Plan:** B17 (`HC button audit + after-cost gating`) will:
1. Read `reports/forward_edge_audit_<date>.json`
2. Add `after_cost_net_per_trade` + `wilson_lb_wr` fields to each pick in `audit_trail/dashboard_generator.py`'s payload
3. Use these fields to tighten the HC gate

Expected PR/date: next loop iteration (B17, immediately after B16 merges).

## Caveat: forward-only filtering is approximate

`strategy_promotion_log.json` does not exist in the repo. All `recent_closed` picks
are included in the analysis. A future action item should add promotion-date logging
to the resolver pipeline so strict forward-only filtering is possible.

## Usage

```bash
# Run with default settings
python tools/forward_edge_audit.py

# Specify date and output dir
python tools/forward_edge_audit.py --date 2026-05-01 --output-dir reports/

# Use alternate data file (e.g. for backtesting)
python tools/forward_edge_audit.py --data-file /path/to/dashboard_data.json
```

Output files:
- `reports/forward_edge_audit_<date>.md` — human-readable
- `reports/forward_edge_audit_<date>.json` — machine-readable (for B17 wiring)
