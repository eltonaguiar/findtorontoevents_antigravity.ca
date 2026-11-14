# Quick Wins — Proposed Fixes (2026-11-14)

Subtree: `finpredict`. Companion to `../updates/2026-11-14-prediction-system-audit.md`. All file paths and line numbers verified against the `finpredict` worktree by subagents (read-only); no pipeline files were edited. Fixes are **additive / labeling / guard-only** — no strategy rewrite.

## Folder layout

```
quick-wins/
  README.md            ← this file (priority matrix + how to apply)
  OVERALL.md           ← cross-cutting: honesty metrics, edge_ratio, INSUFFICIENT labels, stale sections, outlier PnL, Actions installs, mutual funds, gated rows
  by-asset-class/
    CRYPTO.md          ← live price wiring, entry-price sanity, kalshi, flat-3% cohort
    EQUITY.md          ← last-close provenance, n + Wilson CI
    ETF.md             ← parked-at-close label, hide empty UEPS tabs
    FOREX.md           ← purge 11 phantoms, stale price fallback, consensus threshold
    FUTURES.md         ← full ISO timestamps
    COMMODITY.md       ← current_price backfill
    BOND.md            ← price backfill, auto-expire unquoted seeds
    MUTUAL_FUNDS.md    ← remove/relabel unbuilt claim
```

## Priority matrix (impact ÷ effort)

| # | Fix | Class | Effort | Impact |
|---|---|---|---|---|
| 1 | Wire live Binance failover into dashboard crypto fetch | CRYPTO | S | H |
| 2 | Label unquoted rows (don't show 0% as "live") | CRYPTO / all | S | H |
| 3 | Surface honesty metrics (excluded n + CI) next to WR | OVERALL | S | H |
| 4 | Entry-price sanity gate (reject 0/absurd) | CRYPTO | S | H |
| 5 | Stop coercing None entry → 0.0 | CRYPTO | S | H |
| 6 | Emit full ISO timestamps for futures | FUTURES | S | H |
| 7 | Add last_quote / "last close" provenance | EQUITY/ETF | S | H |
| 8 | EQUITY headline: n + Wilson 95% CI | EQUITY | S–M | H |
| 9 | Bond price backfill + auto-expire unquoted seeds | BOND | S | H |
| 10 | Purge 11 frozen FOREX phantoms | FOREX | M | H |
| 11 | Hide gated/placeholder rows from active list | OVERALL | S | M–H |
| 12 | Refresh-or-drop stale `stock_forex_prices.json` | FOREX | M | M–H |
| 13 | Emit `INSUFFICIENT` when forward_trades==0 | OVERALL | S | M |
| 14 | Cap/flag outlier PnL (surface existing flags) | OVERALL | S | M |
| 15 | Refresh-or-remove dead sections/sidecars | OVERALL | M | M |
| 16 | Fix Actions install/Playwright failures | OVERALL | M | M |
| 17 | Relabel/purge flat-3% placeholder cohort | CRYPTO | M | M |
| 18 | Backfill commodity current_price | COMMODITY | M | M |
| 19 | Remove/relabel mutual-funds claim | MUTUAL_FUNDS | S | L |

## How to apply (recommended order)

1. **Labeling + honesty first (no risk):** QW-2, QW-3, QW-8, QW-7, QW-13, QW-14, QW-11 — these only change how data is *presented*, not what's resolved.
2. **Guard + gate (low risk):** QW-4, QW-5, QW-6, QW-10, QW-9, QW-19.
3. **Wire the live price path (medium risk):** QW-1, QW-12, QW-18, QW-17.
4. **Infra (isolated):** QW-16, QW-15.

## Guardrails

- Do **not** wire `alpha_engine/forced_resolution.py` for live resolution — its header warns it is research-only (survivorship-bias risk).
- The flat-3% cohort is produced *indirectly* via the asset-class default TP fallback (`dashboard_generator.py:8102`) — key the detector on "all wins == fallback TP%", not a magic `3.0` constant.
- `strong_signals.json` and `stock_forex_prices.json` have **no producer in this worktree** (orphan deploy refs) — refresh requires re-wiring a producer, or just delete the deploy entries.
- `edge_ratio` is only read by the hyrotrader panel, not the main dashboard (corrected from the earlier audit note).
