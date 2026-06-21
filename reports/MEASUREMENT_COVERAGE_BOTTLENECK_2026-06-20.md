# The Honest-Ledger Coverage Bottleneck — the real root constraint (2026-06-20)
**Author:** claude-opus · **Source:** direct SQL on `at_signal_outcomes` during the FRM/CFA + cointegration loop · **Companion:** `reports/FRM_CFA_CONCEPTS_AUDIT_2026-06-20.md`

## The finding (SQL-verified)
The "honest intrabar first-touch ledger" the entire money-ready program promotes against is **95.7% placeholders.**

`at_signal_outcomes`: total **43,213** rows.
- **Genuine intrabar resolution** (`intrabar_ambiguous=0`, real OHLC path, `horizon_bars=168`): **1,837 rows (4.3%)**.
- **Placeholders** (`intrabar_ambiguous=1`, `horizon_bars=0` — no price path found, stamped TIME_EXIT): **41,335 rows (95.7%)**.

**Clean (resolvable) rows per class — these ARE the honest n's cited all session:**
| Class | CLEAN (ambiguous=0) | PLACEHOLDER (no path) |
|---|---|---|
| CRYPTO | 1,261 | 38,224 |
| FOREX | 148 | 277 |
| EQUITY | 144 | 282 |
| COMMODITY | 139 | 164 |
| MEMECOIN | 77 | 2,348 |
| FUTURES | 25 | 7 |
| ETF | 22 | 25 |
| BOND | 10 | 7 |

The clean counts match the per-class honest n's in `money_ready_verdict` / `build_intrabar_truth_by_class` exactly — so the verdict path correctly uses the clean set (no contamination there). The point is **why the clean set is so small.**

## Root cause: price-path data coverage
The intrabar resolver can only produce a genuine first-touch verdict where it has the OHLC **price path** to walk. Today that path source is essentially **`crypto_ohlcv` (1h, ~315 symbols, ~180 days)** and nothing else with comparable density. So:
- A pick is resolvable only if its symbol+date window has bars. CRYPTO has 1,261 such (recent, liquid, in-window) — but 38,224 CRYPTO picks fall outside the 180-day / 315-symbol coverage → placeholder.
- EQUITY/FOREX/COMMODITY/BOND have almost no dense intraday path feed → ~100-150 clean each, the rest placeholder. (EQUITY's `daily_prices` writer has 404'd since 2026-04-29 — see `MONEY_READY_NEXT_STEPS_BUILD_PLAN_2026-06-19.md`.)

**This single constraint explains the whole stuck state:**
- 0/10 promotable + tiny per-class n → because only ~1,837 trades are honestly resolvable, period.
- H-130/H-131 funding + H-132 cointegration all "window-limited / refuted on 180d" → same 180d crypto path coverage.
- Non-crypto classes can't accrue honest n → no path feed.
- CPCV (`build_cpcv_pbo_results.py`) + FDR (`fdr_control.py`) read the daily `pnl_pct` (17,529 rows, banned/inflating) instead of the honest `intrabar_pnl_pct` **because the honest clean set (~1,837 across 160 strategies ≈ 11/strategy) is too thin to run them on.** The "integrity fix" (swap to honest col) is blocked by the same coverage gap.

## Why this outranks every FRM/CFA concept
The FRM/CFA audit concluded we already have the rigor (CI-LB, DSR, PBO, White's, GARCH, cointegration) and the gaps are wiring + honesty + one edge avenue. This finding is deeper: **all of that rigor operates on ~1,837 honestly-resolved trades.** No gate, metric, or new strategy can manufacture signal from data we can't resolve. **Price-path coverage is the binding constraint upstream of everything.**

## The actual root lever (ranked)
1. **Backfill multi-year crypto 1h OHLCV** (currently ~180d) → instantly multiplies CRYPTO clean n far beyond 1,261 and lets H-130/H-131/H-132 get a fair multi-regime re-test. Highest leverage, lowest effort (extend the existing `refresh_crypto_ohlcv.py` pull).
2. **Restore the EQUITY price path** — `daily_prices` (404 endpoint, unmask shipped `9f501250`); then land an intraday/daily path the resolver can walk for equity first-touch. Unblocks EQUITY honest n (gates H-126 reversal).
3. **Land OHLC path feeds for FOREX / COMMODITY / BOND** (the cold classes) so their picks become resolvable at all.
4. THEN: feed the honest `intrabar_pnl_pct` (ambiguous=0) to CPCV/FDR + wire the orphaned DSR/White's into the promotion gate — they become viable once the clean set is large enough.

## Honest bottom line
The session's recurring theme — "edge scarcity + measurement-integrity uptime + forward-n accrual" — has a single dominant sub-cause: **we can only honestly resolve ~4% of our picks because we lack the price-path data for the rest.** Expanding price-path coverage (crypto history first, then equity/FX/commodity/bond feeds) is the highest-leverage move in the entire program — above any new strategy, gate, or FRM/CFA technique. Everything else is downstream.
