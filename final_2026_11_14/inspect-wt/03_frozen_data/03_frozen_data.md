# Notes — Frozen data / stuck P/L / dead timestamps

**Verdict: FAIL.**

## 1. Zero-P/L root cause (peer-verified, `reports/zero_pnl_data_pipeline_audit_2026-06-05.md`)
> "`at_pick_outcomes`: **100% of the 28,218 zero rows are status=EXPIRED** ... Resolution_method =
> `TIME_EXPIRED` for every single one ... the time-expiry resolver writes `pnl_pct=0` instead of
> computing the actual close-vs-entry mark."
> "Bug is concentrated in the two `backfill_widened/updated` resolvers (32,817 rows, 85.0% combined
> zero share). Newer resolvers (`backfill_2026-06-01`, `universal_v2`, `signflip_purge`) are clean (<10%)."

Per-class zero share: FUTURES 98.4% · INDEX 99.0% · BOND 89.1% · COMMODITY 84.9% · FOREX 83.7% ·
ETF 83.1% · EQUITY 79.5% · CRYPTO 56.5% · MEME 25.0% · STOCK 12.1%.

## 2. Independent live measurement (this audit)
- 504 / 624 priced open picks (**81%**) display `0` or `None` P/L.
- Their true mark-to-market: median −0.04%, **mean −1.80%**; 125 rows actually down >5%.
- Dashboard-claimed sum −106pp vs real sum **−1,116pp**.

## 3. Dead timestamps / stale files (live, 16:15Z)
| File | generated | Age | Status |
|---|---|---|---|
| hyro_pick_performance.json | 2026-11-08T02:14 | **157h** | STALE (workflow "succeeds" daily) |
| hyrotrader_picks.json | (no field) | — | no timestamp at all |
| pick_funnel_snapshot.json | — | — | serves 404 HTML |
| strategy_tribunal_latest.json | — | — | 404 (Playwright-confirmed) |
| audit_surface_truth.json | 04:52Z | 11h | AGING (feeds the "0/9 money-ready" banner) |
| core payloads | 16:15Z | <1h | FRESH |

## 4. Fields that never update
- OPEN picks with `current_price = None` (10 incubator BTCUSDT rows from 2026-11-12T12:15–12:19Z).
- Regime: `regime_validation.active_regime_composition.with_regime_data = 0`;
  `data_coverage.closed_with_regime = 21` vs `closed_without_regime = 8,538` → **0.25% coverage**.
- DB health: 3,509 rows carry non-canonical `FORCE_CLOSED_TOXIC` status (tier red).

## 5. Backfill contamination caveat
Peer `reports/REAL_MONEY_MASTER_2026-06-05.md`: the **2026-06-04 `closed_at` backfill contaminated
~35,494 rows** ("99% of 'edges' were single-day batch artifacts"). All-time registry figures
(CRYPTO PF 0.232, n=23,636) may include those rows; the 7/14/30-day recomputes in this audit do not.
