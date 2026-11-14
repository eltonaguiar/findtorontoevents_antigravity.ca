# FOREX — how to get profitable (deepAI)

## My measured truth (live, 2026-11-14)
- Active: 114 picks, **85.1% zombie** (worst zombie rate of any tradable class), repriced open
  P/L **mean −1.96%** (n=102; open.er-api spot truth).
- Garbage ingest proven on this class: `EURGBP=X` entry **688.17** vs market **0.835** (≈824×),
  `GBPCHF` stale from Oct 20, `JPY` 0.000001 placeholders, `GBPUSD` 9999.0.
- My V1 cells: all forex sources PF **0.27–0.71** (eur_momentum 0.71 best of a bad lot,
  usd_cad_mtf 0.27 worst) — no cell even approaches 1.0. Variant C: **0 forex trades in 8
  forward months** (auto-excluded by the training-PF gate).
- Peer-verified blockers (finpredict-v3 / finpredict roadmap): **11 frozen closed phantoms**,
  `stock_forex_prices.json` **217 days stale**, consensus threshold=1 (single-source),
  FOREX class **hard-disabled** (PR#6, 0 call sites).

## What peers propose
- **Carry basket** (long high-yield vs short low-yield, equal-risk) + trend overlay —
  documented premium, realistic Sharpe **~0.3–0.6**, capacity-limited (finpredict roadmap).
- finpredict-v3: same conclusion — fix the feed first, then carry as a diversifier.

## My plan
1. **No forex trading from this system until the feed is fixed.** Evidence bar: 85% zombies,
   100×-class garbage rows, PF<0.71 everywhere, zero forward trades under the one honest rule.
2. **Fix (my fixspecs, all specified file:line):**
   - `fixspec_garbage_price_ingest_guard` — entry sanity gate (reject |entry − market| > 5×),
     unit normalization, `UNQUOTED` instead of fabricated 0%;
   - `fixspec_spot_flicker_resolver` — kill 9999/1e-6 placeholder and 2-second flicker resolvers;
   - phantom resolver backfill for the 11 frozen closed rows; refresh `stock_forex_prices.json`.
3. **Then build ONE sleeve: carry basket** (DXY-weighted, equal-risk, monthly rebalance) with
   a trend overlay, measured excess-of-benchmark with paired bootstrap, pre-registered.
   Expect Sharpe 0.3–0.6 — a diversifier, not a headline. Do **not** rebuild the 20+ signal
   sources (all PF<0.72 — the zoo is the problem).
4. **Re-enable the class** only after gates 1–2 pass; then forward-test the carry sleeve under
   T2∧v3 gates like every other class.

**Tradable today: NO.** Path: feed fix (1–2 weeks of spec work) → carry sleeve research →
forward pilot. Honest expectation: small, capacity-limited positive expectancy.
