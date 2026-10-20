# Task 10 — benchmark_closed_ledger.py (money-ready plan)

**Date:** 2026-10-19
**Owner lane:** independent module (no shared files with the Tasks 1–9 / Part C
renderer-and-screener work running in parallel).

## What was missing

Plan Task 10 required benchmarking *every closed-pick ledger* against SPY
buy-and-hold and a random-entry Monte-Carlo, but no such module existed. A win
rate alone cannot separate edge from coin flip (50% WR @ 2:1 R:R beats 60% @
1:2), and no closed ledger had any benchmark-derived field.

## What was built

`alpha_engine/benchmark_closed_ledger.py` — self-contained (stdlib stats core,
optional yfinance for price fetch):

- Groups `recent_closed` rows into (strategy, asset_class) ledgers.
- **Paired bootstrap vs same-window benchmark** (10k seeded resamples of
  (trade, benchmark) return pairs): CI on mean excess, `frac_positive`,
  `pass_95` gate (plan C.3 Step 2: ≥95% of samples must beat the benchmark).
- **Random-entry Monte-Carlo** (10k permutations, same hold lengths): percentile
  of realized total vs the null distribution — Task 10's
  `random_entry_mc_pctile` column. ~1.0 = timing edge; ~0.5 = coin flip.
- Benchmark mapping is explicit: EQUITY/ETF→SPY, CRYPTO→BTC-USD, unmapped
  classes fall back to SPY *with a note*.
- Task 9 convention respected: WR/Wilson hidden below n=20.
- Fail-soft: missing timestamps or missing price series degrade that ledger to
  trade-level stats with the reason in `notes`; never an exception.
- Wilson formula duplicated from the Task 9 card-side implementation
  **on purpose** (module docstring says so): importing the 577 KB
  `quality_gates.py` for one formula would couple two independently-evolving
  branches.

## Verification

- `tests/test_benchmark_closed_ledger.py` — **28 tests, all pass**
  (pytest exit 0). Covers Wilson values, PF-undefined → None (no Infinity in
  JSON), deterministic seeded bootstrap/MC, timestamp dialects
  (Z / +00:00 / naive-UTC), as-of-close weekend lookback, loader shapes
  (dashboard nested + flat list), degradation paths, report assembly
  (strict `allow_nan=False` serialization), and CLI end-to-end via tmp files.
- `py_compile` clean.
- **Real-data smoke run** (exit 0):
  `python3 -m alpha_engine.benchmark_closed_ledger --picks audit_dashboard/data/dashboard_data.json --fetch SPY BTC-USD --out reports/benchmark_ledger_proof_2026-10-19.json`
  → 170 ledgers, 67 with full proof (paired + MC), 4 pass_95, 12 in MC top
  decile.

## Real-data findings (reports/benchmark_ledger_proof_2026-10-19.json)

- **`mega_mutation_macd_rsi_m048` (CRYPTO, n=57, PF 5.11):** excess +5.88% vs
  BTC same-windows, frac+=1.00, MC percentile 0.99 — the only decent-n ledger
  clearing *both* gates. Caveat: class verdict is still NOT_READY, and crypto
  carry regime was inverted in June (see method review), so treat as candidate
  for pre-registered paper pilot, not live.
- **Divergence example (why both tests are needed):** `forex_rsi2_mean_reversion`
  passes paired (beats same-window FOREX-proxy benchmark) but MC percentile
  0.13 — random entries would have done better. Conversely
  `gap-and-go-stocks` and `donchian-stock-breakout` (EQUITY) hit MC 1.00
  (timing beats all random entries) but fail paired — gains track the
  benchmark window rather than beating it.
- `adx-trend-scout` (ETF sleeve from the method review): PF 1.76 but excess
  +0.10%, frac+ 0.68, MC 0.66 — profit factor alone would overrate it.

## Not in this pass

- Wiring results into `dashboard_generator.py` / system cards (left to the
  renderer-owning branch to avoid merge conflict; the module writes a
  standalone JSON the dashboard can later consume).
- No live-site or pipeline changes.

## Addendum (2026-10-19, after external review): random-entry MC was broken — fixed (v3)

External review flagged `luxalgo_confluence/CRYPTO`: cum_return −26% vs BTC
+44%, WR 42%, PF 1.03 — yet MC percentile 1.0 with 660/1211 trades skipped.
Investigation (measured, not assumed):

1. **v1 bug — full-history, benchmark-path nulls.** Nulls were sampled with
   `randrange(0, n - hold)` across the whole benchmark series, long-only.
2. Heavy-tail hypothesis **rejected by data**: top single trade = 4% of the
   observed total; dropping it leaves percentile 1.0 (obs 3.10 vs null max
   2.49).
3. **Real residual bug — cross-asset scale.** Nulls ran on the BTC/SPY
   *benchmark* path while realized returns came from the trades' own symbols
   (altcoins, penny stocks). Any volatile instrument pins at 1.0 against a
   low-vol benchmark path regardless of timing skill.
4. **Skips explained:** same-day round trips collapse to hold=0 bars on daily
   closes (`xi - ei >= 1` filter) — 660 of 1211 for this ledger. Now reported
   explicitly (`n_skipped`); obs_total uses exactly the simulatable subset.

**v3 fix (`random_entry_mc`):** per-symbol own-price nulls
(`series_by_sym`), window-matched per symbol, direction-aware (shorts
negate the path), skips + `n_benchmark_fallback` reported. CLI gains
`--fetch-picks` (fetches one yfinance series per distinct pick symbol,
`MAX_OWN_FETCH=400`, USDT/PERP → USD mapping).

**Pass gate (CI, 33/33 green):** `test_mc_coin_flip_lands_near_median` — a
no-skill random-entry ledger must land near the 50th percentile;
`test_mc_same_asset_null_not_calm_benchmark` — volatile-asset coin flips must
not pin at 1.0 (the old cross-asset bug);
`test_mc_short_sign_negates_null_path` — sign symmetry (long/short);
`test_mc_window_matched_not_full_history` — regression vs v1;
`test_mc_reports_skips_and_keeps_obs_like_for_like`.

**Effect on the real report** (rerun with `--fetch-picks`, 144 own series):
luxalgo_confluence percentile **1.0 → 0.568** (coin flip, exactly right for
PF 1.03); `n_mc_top_decile` 12 → 9; **no n≥20 ledger pins at 1.0** (remaining
1.0s are all n≤13, flagged `*` on the panel); 239 trades used the documented
benchmark fallback. The paired gate — the honest headline — is unchanged:
**6 of 170 ledgers clear it (4 within the full-proof subset)**.

**Panel (`/audit/benchmark_proof.html`):** paired bootstrap is the headline
("N of M" banner + `vs bench (pp)` column per row); MC table is labelled
"same-asset nulls (fixed 2026-10-19)" and kept supporting; n<20 MC percentiles
muted with `*` (mirrors the WR-hide convention); headless-Chromium smoke:
headline renders, 0 page errors, zero READY/ENTER tokens in panel + sidecar.
