# 10 — Survivorship / point-in-time audit (items 20–22)

All numbers below trace to [`reports/survivorship_audit_20261122.json`](../../reports/survivorship_audit_20261122.json)
or to a `file:line`. Nothing is estimated silently; anything I could not measure is
marked `UNMEASURED`.

## 1. Universe inventory

| Universe | Where | n | How it was assembled |
|---|---|---|---|
| 79-symbol panel (N1, 12-1 momentum) | [`data/cache/asset_class_review/*_5y.csv`](../../data/cache/asset_class_review) — used at [`tools/momentum_12_1.py:33`](../../tools/momentum_12_1.py:33) | 79 | `glob` of whatever CSVs exist on disk **today** |
| Equity breakout | [`tools/pod_equity_breakout_backtest.py:49`](../../tools/pod_equity_breakout_backtest.py:49) | 13 | hardcoded US ETF / large-cap tuple |
| Breakout cost sweep | [`tools/breakout_cost_sweep.py:27`](../../tools/breakout_cost_sweep.py:27) | 13 | imports the same `SYMBOLS` |
| Breakout backtest | [`tools/breakout_backtest.py:64`](../../tools/breakout_backtest.py:64), [`:66`](../../tools/breakout_backtest.py:66) | — | hardcoded equity + crypto lists, filtered to tickers present on disk |
| KIMI backtest engine | [`KIMI_RISEOFTHECLAW/backtest_engine.py:57`](../../KIMI_RISEOFTHECLAW/backtest_engine.py:57) | — | hardcoded STOCKS_ETF/CRYPTO/FOREX/PENNY assembled today; includes since-delisted names (NKLA, CLOV), so effective membership is silently filtered by fetch success |
| S&P 500 snapshot | [`data/universe/sp500_tickers.txt:1`](../../data/universe/sp500_tickers.txt:1) | 502 | **static current-constituent snapshot** ~2026-06 (comment says "minor drift acceptable") |

Every list is a **today's-constituents** list. None is point-in-time.

## 2. Survivorship test (79-symbol panel)

| Count | Value |
|---|---|
| `n_symbols_total` | 79 |
| `n_series_ending_before_panel_end` | **0** |
| `n_series_starting_after_panel_start` | **0** |
| `n_series_with_multiday_gaps` | 10 (all 10 FX pairs) |
| `n_zero_or_suspicious_volume` | 20 (10 FX + 9 futures + `SI_F`, `GC_F`, …) |
| `n_stale_close_run ≥ 5` | 0 |

Zero series end early and zero start late. A true point-in-time universe would
contain **some** series that stop mid-window (delisted, acquired, renamed); this
panel contains **none**. That is the pure signature of a current-constituent
universe. The FX/futures zero volume is a *data-shape* artefact (FX has no
central volume; contract rolls create gaps), not delisting evidence.

## 3. Bias direction and the evidenced lower bound

- Equal-weight CAGR over all 79 series: **0.068645**.
- Equal-weight CAGR over series present at both ends: **0.068645**.
- Gap: **0.0 pp/yr**.

The gap is **0.0 by construction** because the "both ends" set is all 79 symbols.
So this is a **zero lower bound**, not proof of zero bias. The honest statement:
the panel is *internally* consistent, but its *absolute* upward bias from
excluding names that never listed into the cache or were delisted before it was
built is `UNMEASURED` — there is no survivorship-free benchmark offline.

Direction: **upward (panel flattered)**, by an amount ≥ 0 pp/yr and unknown above
that. The direction is argued from construction (only living, still-liquid names
were cached), not from the measured gap.

## 4. Per-verdict consequence

| Strategy | Verdict | Standing | Why |
|---|---|---|---|
| N1 R1 12m momentum | KILL | UNCHANGED | PIT re-run identical; excess +0.97pp, null pct 61.2 |
| N1 R2 sector momentum | KILL | UNCHANGED | identical; excess −11.3pp, pct 35.4 |
| N1 R3 SPY 200d filter | KILL | UNCHANGED | identical; excess −6.8pp, pct 53.4 |
| 12-1 momentum L/S | KILL | CONSERVATIVE | bias flatters momentum longs ⇒ KILL is even more right |
| Equity breakout | KILL | CONSERVATIVE | bias flatters breakouts |
| FX carry | KILL | CONSERVATIVE | lost despite favourable data |
| Cross-venue basis | KILL | CONSERVATIVE | crypto majors all survive |
| Funding carry | MARGINAL | **UNSAFE** | a marginal *survive* is exactly what survivorship could flip; unproven |

Rule of thumb: a KILL on flattered data is conservative; a MARGINAL/positive on
flattered data is unsafe.

## 5. Point-in-time attempt

- Local historical membership / delisting records: **none**. The only universe
  files are [`data/universe/sp500_tickers.txt`](../../data/universe/sp500_tickers.txt)
  (current snapshot) and `data/penny_universe_seed.json` (seed list).
- One credential-free fetch attempted and failed:
  `FETCH_FAILED: HTTPError HTTP Error 404: Not Found`
  (URL: `https://raw.githubusercontent.com/fja05680/sp500/master/S%26P%20500%20Historical%20Components%20%26%20Changes(08-01-2024).csv`).
- Built the best available approximation: a **first-observation universe**
  ([`tools/pit_universe.build_pit_universe()`](../../tools/pit_universe.py)). It
  removes left-censoring (a symbol is not counted before its first close) and
  right-censoring (not counted after its last close). It **cannot** capture
  delisting-with-poor-returns bias. On this cache its size is 79 at every tested
  date.

## 6. N1 re-run on the PIT universe

Same rules, same parameters, only the universe changed (R1 candidate pool
restricted to the PIT set at each rebalance date; R2/R3 untouched).

| Rule | n | CAGR orig → PIT | maxDD | Sharpe | vs SPY | null pct | Verdict |
|---|---|---|---|---|---|---|---|
| R1 | 33 → 33 | 18.05% → 18.05% | −46.4% | 0.590 | +0.97pp | 61.2 | KILL → KILL |
| R2 | 30 → 30 | 5.76% → 5.76% | −23.1% | 0.413 | −11.3pp | 35.4 | KILL → KILL |
| R3 | 19 → 19 | 10.24% → 10.24% | −12.0% | 0.861 | −6.8pp | 53.4 | KILL → KILL |

Survivorship contribution = original − PIT = **0.0** for all three (the rules
payload is byte-identical). N1's conclusion **SURVIVES** unchanged. The random
null percentile for the PIT run is **61.2 / 35.4 / 53.4** (R1/R2/R3), all below
the 95 gate. Mean PIT universe size 79 ⇒ SUFFICIENT (≥ 30).

## 7. What this changes

Honestly: **not much for the KILLs, and it exposes a hole in the methodology.**
The PIT re-run is uninformative *because* the universe is identical at every
date — the cache simply contains no dead names to remove. That means the whole
programme's backtests are run on a universe that cannot, by construction, show
the survivorship penalty. Every KILL is therefore safe (bias only helped the
strategies), but **any positive or marginal result should be treated as
unproven** until a genuinely historical universe is available. The one verdict
that this audit flags as unsafe is funding carry (MARGINAL). To actually measure
the magnitude, the cache would need to be rebuilt from a historical constituent
source that includes delisted tickers.
