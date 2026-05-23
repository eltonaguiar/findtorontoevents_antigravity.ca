# DB Pick Traceback — `ejaguiar1_stocks.at_raw_picks`

**Date:** 2026-05-18
**Scope:** read-only SELECT trace of pick lineage + symbol-universe coverage gap
**DB:** `ejaguiar1_stocks` @ mysql.50webs.com (147,067 rows in `at_raw_picks`)
**Goal #1** — phenomenal performance across all asset classes on `/audit`.

---

## 1. Per-class pick stats

### All-time (`at_raw_picks`)

| asset_class | total | resolved | WR* | distinct sym | date range |
|---|---|---|---|---|---|
| CRYPTO | 110,025 | 71,207 | 42.8% | 458 | (epoch-zero) → 2026-05-19 |
| EQUITY | 14,828 | 11,619 | 69.3% | 115 | 2026-02-16 → 2026-05-19 |
| FOREX | 7,844 | 6,733 | 83.0% | 22 | 2026-02-17 → 2026-05-19 |
| FUTURES | 3,970 | 3,716 | 48.3% | 18 | 2026-03-11 → 2026-05-19 |
| UNKNOWN | 3,348 | 1,861 | 0.0% (no WON/LOST) | 73 | 2026-03-04 → 2026-05-19 |
| MEMECOIN | 3,179 | 2,628 | 38.6% | 35 | (epoch-zero) → 2026-05-11 |
| **`''` (blank enum)** | **2,964** | 687 | n/a | 13 | 2026-04-09 → 2026-05-19 |
| PENNY_STOCK | 716 | 543 | 36.0% | 246 | 2026-02-17 → 2026-05-12 |
| ETF | 193 | 156 | 63.9% | 18 | 2026-02-19 → 2026-05-19 |

*WR = WON/(WON+LOST). The `WON/LOST` enum is only used by a subset of sources;
many "resolved" rows carry status `CLOSED`/`EXPIRED` with no WON/LOST label — see §5.

### Last 30 days — symbols actually traded

| asset_class | picks 30d | distinct symbols 30d |
|---|---|---|
| CRYPTO | 26,915 | **131** |
| EQUITY | 4,987 | **37** |
| FOREX | 4,553 | **13** |
| FUTURES | 1,805 | **17** |
| `''` blank | 1,620 | 8 |
| UNKNOWN | 671 | 16 |
| MEMECOIN | 211 | 5 |
| ETF | 62 | **7** |
| PENNY_STOCK | 56 | 52 |

---

## 2. Pick traceability assessment

Sampled one resolved pick per class (latest WON/LOST). Lineage fields present
on the row:

| field | present? | notes |
|---|---|---|
| `source_system` | yes | e.g. `smart_money`, `AlphaEngine`, `meta_strategy`, `incubator_gainer` |
| `strategy` | yes | e.g. `smart_money_consensus`, `cta_cross_asset_tsmom`, `regime_mild_bull` |
| `symbol` / `asset_class` / `direction` | yes | |
| `entry_price` / `take_profit` / `stop_loss` / `risk_reward` | mostly | |
| `status` / `exit_price` / `exit_reason` / `pnl_pct` / `closed_at` | partial | see gaps below |
| `dedup_hash` | yes (UNIQUE) | char(64), good idempotency key |
| `created_by` | yes | `aggregator` vs `full_sync` — provenance of the *write path* |
| gate flags `was_stale/was_banned/was_demoted/was_wr_suppressed` | yes | on-row gate verdict |
| `aggregation_run_id` | yes (FK → `at_aggregation_runs`) | ties pick to a scan run |
| `raw_payload` (JSON) | **type-degraded** | column is `json` but stored values come back as **strings**, not parsed objects — payload is opaque without a second JSON-decode |

**Verdict: lineage is ~80% reconstructable from a single row.** You can trace
`source_system → strategy → gate flags → outcome` directly. The gate-rejection
side is reconstructable via `at_filter_log` (818,190 rows, joins on
`aggregation_run_id` + `symbol`). What is **missing / broken** for full traceability:

1. **`at_pick_audit_trail` is EMPTY (0 rows)** and **`at_pick_outcomes` is EMPTY (0 rows)** — the two tables explicitly designed for per-pick lineage and outcome history are not being written. All lineage currently has to be inferred from `at_raw_picks` + `at_filter_log`.
2. **`raw_payload` is stored as a JSON-encoded string**, not a real JSON object — the scanner-level feature vector / signal detail is there but un-queryable (`JSON_EXTRACT` won't work without `CAST`).
3. **`exit_reason` is sometimes blank** even on WON/LOST rows from `meta_strategy`/`full_sync` (crypto + memecoin samples) — only `aggregator`-written rows carry `TP_HIT`/`SL_HIT`/`TIME_EXIT`.
4. **`at_filter_log.raw_pick_id` is NULL** on the rows sampled — the rejection log is *not* linked back to a surviving pick id, only loosely joinable by run+symbol.
5. **`at_aggregation_runs` is stale** — latest run is dated **2026-04-16** while `at_raw_picks` has rows through 2026-05-19. The current write path no longer registers aggregation runs, so `aggregation_run_id` on recent picks points at runs that may not exist → run-level lineage is broken for the last month.

---

## 3. Symbol-universe coverage gap (the key finding)

| class | traded 30d | plausible liquid universe | blind to | coverage |
|---|---|---|---|---|
| CRYPTO | **131** | ~400–500 liquid USDT perps (Binance lists 400+) | ~270–370 | **~26–33%** |
| EQUITY | **37** | S&P 500 (+ liquid mid-caps) ≈ 500+ | ~463+ | **~7%** |
| FOREX | **13** | ~28 major+minor pairs (G10 crosses) | ~15 | ~46% |
| FUTURES | **17** | ~25–30 liquid CME/ICE contracts | ~10 | ~60% |
| ETF | **7** | ~50–100 liquid sector/factor ETFs | ~45–90 | **~7–14%** |
| MEMECOIN | **5** | dozens of liquid meme pairs | many | low |
| PENNY_STOCK | 52 (n=56 picks, ~1 pick/symbol) | thousands | — | broad but not repeated — effectively noise |

**Biggest missed-symbol finding — EQUITY is the worst coverage gap.** With a
69.3% WR (the system's best resolved class) the EQUITY scanner traded only **37
symbols in 30 days** and is dominated by 4 names (BAC 814, AMZN 801, NVDA 764,
MSFT 716 picks = 62% of EQUITY volume). It is blind to ~93% of the S&P 500. The
class with the strongest edge has the narrowest aperture — that is the single
highest-leverage gap for Goal #1.

**Crypto top-mover cross-check** (CoinGecko top-100 by mcap, 7d change — quiet
market, top gainer HYPE +14.8%):

| mover | 7d % | in picks 30d? |
|---|---|---|
| HYPE | +14.8 | PICKED (470) |
| DEXE | +9.5 | **MISSED** |
| NEAR | +5.8 | PICKED (1412) |
| JST | +3.3 | **MISSED** |
| QNT | +3.0 | **MISSED** |
| ATOM | +2.1 | PICKED (214) |
| TRX | +1.7 | PICKED (652) |
| ZEC | +1.1 | PICKED (18) |
| HTX, M, USYC, OUSG, USTB, STABLE, FIGR_HELOC | — | **MISSED** |

8 of 15 top-mover candidates were never picked. Several (USYC/OUSG/USTB/STABLE
= tokenized treasuries / stablecoins) are correctly out of universe. But
**DEXE, JST, QNT, HTX** are real liquid trading pairs and were missed —
genuine universe blind spots, not noise.

---

## 4. Why symbols are not picked — root-cause diagnosis

`at_filter_log` (818k rows) records *why* a candidate was dropped. Last-30d
`filter_reason` breakdown:

| filter_reason | n (30d) | meaning |
|---|---|---|
| `staleness` | ~95,000 | signal older than freshness window |
| `no_consensus` | ~34,000 | fewer than threshold sources agreed (e.g. "LONG:1 SHORT:0 < threshold 2") |
| `demoted_system` | 5,124 | source system demoted |
| `incubator_strategy` | 3,660 | strategy still in incubation, not promoted |
| `wr_suppressed` | 1,044 | strategy WR below floor |
| `concentration_cap` | 984 | per-symbol position cap hit |
| `regime_mismatch` | 499+ | direction vs market regime conflict |
| `banned_purge` | 732 | banned source |

**Two distinct causes of un-picked symbols:**

1. **Gate filtering (visible, intentional).** For symbols the scanner *does*
   see, the dominant kill reason is **`no_consensus`** — the multi-source
   consensus threshold (≥2 agreeing sources) silences the long tail. In
   CRYPTO, **87 distinct symbols appeared in `at_filter_log` but were never
   picked in 30d** (200 rejected vs 131 picked) — e.g. ARKM, EIGEN, BLUR,
   CFX, KAVA, KSM, MOVE, NEIRO. These are scanned but consensus-starved.

2. **Scanner-universe narrowness (the bigger, invisible cause).** For EQUITY
   and ETF the gap is *not* in `at_filter_log` at all — only 29 EQUITY and 6
   ETF symbols ever appear in the rejection log. **Symbols the scanner never
   ranked simply never enter the pipeline** — no filter row, no pick row, no
   trace. The EQUITY scanner universe is effectively a hardcoded ~37-name
   mega-cap list, not S&P 500. ETF is a ~7-name list (QQQ/SPY/TLT + a few
   sector XLs). DEXE/JST/QNT/HTX never appear in *either* table → the crypto
   scanner universe is a curated ~200-symbol list, not the full Binance
   liquid set.

**So: the un-picked-symbol root cause is split.** Gate filtering (`no_consensus`,
`staleness`) suppresses the *scanned* tail. But the dominant structural cause
is a **narrow, near-static scanner universe** — EQUITY/ETF especially are
running curated short lists, and the absence of any `at_filter_log` row for
most of the S&P 500 / ETF universe proves those symbols are never even
candidates. There is no whitelist *table* in the DB; the universe is defined
in scanner code upstream.

---

## 5. Resolution gaps per class

| class | OPEN | stale OPEN (>14d) | resolved w/ NULL pnl_pct | resolved w/ NULL exit_price |
|---|---|---|---|---|
| CRYPTO | 38,818 | **29,289** | 19,946 | 19,951 |
| EQUITY | 3,209 | 1,385 | 5,816 | 5,817 |
| `''` blank | 2,277 | 1,579 | 0 | 0 |
| UNKNOWN | 1,487 | 1,080 | 1,736 | 1,736 |
| FOREX | 1,111 | 587 | 1,128 | 1,131 |
| MEMECOIN | 551 | 546 | 759 | 759 |
| FUTURES | 254 | 1 | **1,038** | 1,038 |
| PENNY_STOCK | 173 | 154 | 395 | 396 |
| ETF | 37 | 0 | 24 | 24 |

**Findings:**

- **CRYPTO has a massive resolution backlog** — 29,289 picks OPEN for >14 days
  that should have hit a TP/SL/timeout long ago. The crypto resolver is not
  closing out a huge tail.
- **~31,000 picks are marked resolved but have NULL `pnl_pct` AND NULL
  `exit_price`** (system-wide) — these are `EXPIRED`-status rows with no
  outcome computed. They are "resolved" only in status, not in P&L. Any WR
  computed off WON/LOST excludes them, so headline WRs are survivorship-biased.
- **FUTURES orphan-source issue confirmed.** `alpha_engine_unified` is the
  only futures source that resolves cleanly (1,249 LOST / 1,161 WON, 0 NULL
  pnl). But its **970 `EXPIRED` rows are 100% NULL-pnl**, and every other
  futures source (`multi_asset_scanner` 30/30, `live_picks_tracker` 18/18,
  `signal_recorder` 12/23, `AlphaEngine`/`alpha_engine` stuck at OPEN) emits
  picks that **never get a P&L resolved** — orphan emitters with no resolver
  coverage. `orphan_emitter_forex_futures` literally appears as a source name.
- **`UNKNOWN` class shows 0% WR because it has zero WON/LOST rows** — 1,861
  "resolved" rows are all `EXPIRED`/`CLOSED` with no outcome label. The class
  is a resolution dead-end.
- **The blank `''` asset_class enum (2,964 rows)** is a data-integrity bug —
  pre-class-inference rows from `Predictions`, `alpha_engine_unified`,
  `incubator_gainer`, `ml_crypto_pred`. Symbols are DOGE/PEPE/SHIB/WIF/BONK →
  these are CRYPTO/MEMECOIN picks that lost their asset_class tag on write.

---

## Summary of root causes

1. **Narrow scanner universe** (biggest gap) — EQUITY trades 37 of ~500 S&P
   names (~7% coverage) despite being the best class (69% WR); ETF trades 7;
   CRYPTO ~131–200 of ~400+ liquid pairs. Symbols outside the curated list
   never produce a pick *or* a filter-log row.
2. **`no_consensus` gate** suppresses the scanned long tail (≥2-source
   threshold) — 87 crypto symbols scanned-but-never-picked in 30d.
3. **Broken lineage tables** — `at_pick_audit_trail` and `at_pick_outcomes`
   empty; `at_aggregation_runs` stale since 2026-04-16; `raw_payload` stored
   as opaque string.
4. **Resolution backlog** — 29k stale-OPEN crypto picks; ~31k resolved rows
   with NULL P&L; FUTURES orphan emitters with no resolver.
5. **`''` blank asset_class** — 2,964 untagged crypto/meme rows (write bug).

---

*Generated read-only. No production files modified. Reproduce with the queries
in this report against `ejaguiar1_stocks.at_raw_picks` / `at_filter_log`.*
