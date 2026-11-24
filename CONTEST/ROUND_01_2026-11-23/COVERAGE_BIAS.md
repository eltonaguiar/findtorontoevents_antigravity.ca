# COVERAGE BIAS — is the measured fifth a representative fifth?

**Block 56 · 2026-11-23 · measured at `origin/main` = `85c0c9c3d3c77b9e45a0fdd384d8d0d9dbc0bd09`**

Short answer: the "fifth" is **not** one sample. It is the product of two different
selections stacked on top of each other, and each one is biased in a different
direction. The first fifth (which picks are scoreable at all) is **outcome-selected**.
The second fifth (which scoreable picks get a price benchmark) is **class-skewed**.
Net: **BIASED** for the price-dependent verdicts, and **not representative** of the
closed-pick population in a way that is knowable even before prices are fetched.

---

## The number

### What the brief said, and what reproduced

The brief quoted: **`covered` = 3,133 of `total_closed_picks` = 14,941 → 20.97%**,
"source: `audit3_ledger.json`, `coverage.denominator` block".

Measurement falsifies three parts of that provenance:

| Brief says | Measured |
|---|---|
| `covered` = 3,133 | `3,133` is **`selection_alpha.covered`**, not a `coverage.*` field. At HEAD it is **3,190**. |
| `total_closed_picks` = 14,941 | At HEAD (`audit_dashboard/data/audit3_ledger.json`) it is **14,997**. `14,941` is a mid-day snapshot value. |
| both live under `coverage.denominator` | `coverage.denominator` has keys `mode, loaded_from_sidecar, fallback_reason, canonical_schema, canonical_rows_sha256, canonical_kept_rows, canonical_excluded_by_reason, share_of_canonical_pct, note` — **no `covered` and no `total_closed_picks`**. |

Exact JSON paths at HEAD:

- `selection_alpha.covered` = **3,190**
- `selection_alpha.n_universe` = **3,500**
- `coverage.total_closed_picks` = **14,997**
- `coverage.scored_rows` = **8,886**
- `coverage.denominator.canonical_kept_rows` = **8,886**
- `coverage.unscored_rows` = **6,111**

### Where 3,133 / 14,941 actually came from

Both values occur together in exactly one ledger revision, commit
`602ad22ada6f1453aea55ee21feb3aaee32d0184` ("refresh kill-tribunal ledger",
2026-11-23T12:35:38Z):

- `selection_alpha.covered` = 3,133
- `coverage.total_closed_picks` = 14,941
- 3,133 / 14,941 = 20.97%

So the figure is real, but it is a **cross-section of two unrelated quantities
taken from a stale snapshot**, not a defined coverage rate. The same ratio a few
hours earlier (`095e8a14985`, 2026-11-19) was 2,228 / 14,637 = 15.22%.

The two quantities are not in a part–whole relation. `selection_alpha.covered`
counts picks inside a 3,500-row **display universe**; `coverage.total_closed_picks`
counts the **entire** closed-pick table. Dividing them happens to give a small
percentage, but that percentage is not "how much of the record the verdicts rest on".

### The three coverage rates that are actually defined (HEAD)

| Ratio | Value | What it means |
|---|---|---|
| `selection_alpha.covered / n_universe` | **3,190 / 3,500 = 91.14%** | How much of the display universe got a price benchmark |
| `selection_alpha.covered / canonical_kept_rows` | **3,190 / 8,886 = 35.90%** | How much of the scoreable record got a price benchmark |
| `selection_alpha.covered / total_closed_picks` | **3,190 / 14,997 = 21.27%** | The brief's ratio, at HEAD |
| `coverage.scored_rows / total_closed_picks` | **8,886 / 14,997 = 59.25%** | How much of the record is scoreable at all |

The last two are the ones that matter, and they measure different things.

---

## What "covered" means

### The price-coverage ("covered") producer

`alpha_engine/audit3_selection_alpha.py` (the ledger names it as the source:
`selection_alpha.source = "alpha_engine/audit3_selection_alpha.py (needs the price tables)"`).

**Universe** — [`main()`](alpha_engine/audit3_selection_alpha.py:399-400) reads
`data["picks"]["recent_closed"]` and keeps rows whose `net_pnl` is not `None`.
That list is capped at 3,500 by [`audit_trail/dashboard_generator.py:285`](audit_trail/dashboard_generator.py:285)
(`MAX_CLOSED_PICKS = 3500`).

**Numerator** — [`alpha_for()`](alpha_engine/audit3_selection_alpha.py:383) returns
`"covered": len(per)`. A row lands in `per` only if it survives every check at
[lines 301–325](alpha_engine/audit3_selection_alpha.py:301-325):

```python
if t0 is None or t1 is None or pnl is None:        # 301
    missing["no_timestamp"] += 1; continue
if t0 >= t1:                                       # 304
    missing["degenerate_window"] += 1; continue
...
if series is None:                                 # 317
    missing[f"no_price:{klass}"] += 1; continue
p0 = _close_at(series, int(t0.timestamp() * 1000), tol)   # 321
p1 = _close_at(series, int(t1.timestamp() * 1000), tol)   # 322
if not p0 or not p1:                               # 323
    missing[f"no_bar:{klass}"] += 1; continue
```

So a pick is "covered" iff it has **entry and exit timestamps**, a **non-null PnL**,
an **entry timestamp strictly before exit**, **a price series for its symbol in its
class's OHLC table**, and **a bar within tolerance of both timestamps**. Price tables
per class are mapped at [lines 52–67](alpha_engine/audit3_selection_alpha.py:52-67);
tolerances at [lines 68–70](alpha_engine/audit3_selection_alpha.py:68-70).

**The 310 uncovered rows at HEAD** (`selection_alpha.missing`, which sums to
3,500 − 3,190 = 310):

| Reason | Count | Note |
|---|---|---|
| `no_timestamp` | 120 | no entry/exit stamp or no PnL |
| `no_price:FOREX` | 47 | symbol absent from `fx_prices` |
| `no_bar:ETF` | 44 | symbol present, bar missing at the stamps |
| `no_bar:FOREX` | 43 | |
| `no_bar:EQUITY` | 38 | |
| `no_bar:CRYPTO` | 10 | |
| `no_bar:COMMODITY` | 3 | |
| `no_price:COMMODITY` | 3 | |
| `no_price:FUTURES` | 1 | |
| `no_price:EQUITY` | 1 | |

The `no_bar:*` cases are a **stale-table** problem, not a missing-symbol problem:
`bar_coverage` at HEAD shows every class with a `last_bar` of 2026-11-22/23 except
FOREX (12 of 17 instruments found; `AUDJPY, CHF, JPY, NZDJPY, USDZAR` missing).

### The "scoreable" producer (the other fifth)

`coverage.denominator` says `mode = "canonical"`, source
`dashboard_data.resolved_closed_picks_net`. In the shipped payload
[`docs/audit_review_2026-11-22/_raw/audit_data_dashboard_data.json`](docs/audit_review_2026-11-22/_raw/audit_data_dashboard_data.json)
that block reports `input_rows: 14914, kept_rows: 8827` with
`excluded_by_reason: {invalid_row: 5891, mirror_duplicate: 93, non_performance_exit: 44,
resolver_breakeven_fallback: 59}`.

The ledger additionally names the two big excluded cohorts
(`coverage.excluded_cohorts`): `integrity_excluded` = **6,013** ("ghost rows,
WON-vs-PnL sign contradictions, constant/zero pnl") and `auto_expired` = **9,356**
("resolved by timeout instead of TP/SL"). These overlap, so they do not sum to the gap
(the ledger's own `coverage.statement` says so).

### The two selections are nested, not parallel

```
total_closed_picks                 14,997
 └─ excluded from canonical        6,111   (not scoreable: integrity / auto_expired / dupes …)
 └─ canonical (scoreable)          8,886
      └─ outside the 3,500 display universe   5,696
      └─ in the display universe             3,500   (MAX_CLOSED_PICKS cap)
           └─ price-covered (selection_alpha) 3,190
           └─ price-missing                    310
```

(6,111 + 5,696 = 11,807 = 14,997 − 3,190.)

The 3,500-row universe is chosen by
[`_build_recent_closed_picks()`](audit_trail/dashboard_generator.py:7031) with
**two class-reservation passes** (500 track-record slots,
[line 286](audit_trail/dashboard_generator.py:286); 2,000 non-crypto slots balanced
across 7 asset classes, [line 287](audit_trail/dashboard_generator.py:287)) and then
**most-recent-first fill** ([Pass 3, line 7135](audit_trail/dashboard_generator.py:7135)).
It is explicitly designed *not* to be a random sample.

---

## The uncovered set

Two uncovered sets have to be described, because there are two fifths.

### A. Uncovered by price (310 of 3,500, within the universe) — CLUSTERED

Per class, from the single ledger file (`classes[].n` = canonical rows, `classes[].alpha_n` = price-covered):

| Class | Canonical n | Price-covered n | Rate |
|---|---|---|---|
| CRYPTO | 6,961 | 1,682 | **24.2%** |
| EQUITY | 958 | 744 | 77.7% |
| ETF | 591 | 545 | 92.2% |
| FOREX | 282 | 132 | **46.8%** |
| COMMODITY | 51 | 45 | 88.2% |
| BOND | 37 | 37 | 100.0% |
| FUTURES | 6 | 5 | 83.3% |
| **Total** | **8,886** | **3,190** | 35.9% |

(The 3,500-row universe is a subset of the 8,886 canonical rows, so per-class
universe counts are ≤ canonical counts; they come from a separately timestamped
payload snapshot and are not used in this table to avoid mixing snapshots.)

This is **strongly clustered**: the miss rate is essentially a function of asset
class. CRYPTO alone supplies 1,682 of 3,190 covered rows (52.7%) and has the
lowest rate; FOREX is second-lowest. BOND, ETF, COMMODITY, FUTURES, EQUITY are all
≥ 77%. The ledger's own gate flags this: `classes[].alpha_gate.alpha_coverage_ok`
is **false** for CRYPTO, FOREX and FUTURES, **true** for EQUITY, ETF, COMMODITY, BOND.

The dominance is structural, not incidental: the universe cap reserves no crypto
slots, yet CRYPTO is 52.4% of the universe, so it dominates the count; its lower
price-coverage rate then drags the aggregate down.

### B. Uncovered by scoreability (6,111 of 14,997) — CLUSTERED by cohort

The excluded rows are not diffuse. The ledger names them as two cohorts:
`integrity_excluded` (6,013) and `auto_expired` (9,356, overlapping). `auto_expired`
means the pick was resolved by timeout, with no win or loss to record. These are
excluded **because of how they ended**, so the exclusion is a function of outcome,
not of data quality.

Per-class composition of the excluded set is **UNMEASURED**: the canonical rows file
(`resolved_closed_picks_net.json`, referenced by `rows_file` in the payload) is not
shipped in the repo, so individual excluded rows cannot be re-inspected from
`origin/main`. The exclusion reasons themselves are in the shipped payload.

### C. Strategy and date distribution of the uncovered set

Strategy mix of the **uncovered** rows is **UNMEASURED** for the same reason (no
per-row join available). What is measurable:

- **Date:** `coverage.window` = `2026-02-17 15:13:13 EST` → `2026-11-23T15:24:06Z`
  for the full closed table. The universe spans `2026-02-21T07:08:50Z` →
  `2026-11-22T03:25:31Z`, with its mass in the last two months:
  2026-10 = 998, 2026-11 = 1,167 of 3,500 (62%).
- **Symbol set:** `bar_coverage.missing_symbols` is short and structured
  (`ARBUSD`; `AUDJPY, CHF, JPY, NZDJPY, USDZAR`; `HE=F`; `QQQ`; `6E=F`).

So the uncovered set clusters on **asset class** (both fifths), **cohort/outcome**
(the scoreability fifth), **recency** (the universe), and a **short symbol list**.
It is not diffuse.

---

## Bias test

### 1. Class mix

Comparing the 3,500-row universe with the 8,827-row canonical population
(`resolved_closed_picks_net.classes`), and the price-covered 3,190 with both:

| Class | Population % | Universe % | Covered % | Covered share ÷ population share |
|---|---|---|---|---|
| CRYPTO | 78.5 | 52.4 | 52.7 | **0.67×** (under-represented) |
| EQUITY | 10.8 | 22.3 | 23.3 | **2.15×** |
| ETF | 6.7 | 16.8 | 17.1 | **2.56×** |
| FOREX | 3.0 | 5.8 | 4.1 | 1.38× |
| COMMODITY | 0.6 | 1.4 | 1.4 | 2.49× |
| BOND | 0.4 | 1.1 | 1.2 | 2.77× |
| FUTURES | 0.0 | 0.1 | 0.2 | 3.46× |

The population is four-fifths CRYPTO; the measured set is about half CRYPTO and
roughly double the EQUITY/ETF share. A verdict computed on the measured set is a
verdict about a book that is **much more balanced than the book actually is**. The
implied full-population composition (above, "Population %") is dominated by CRYPTO.

### 2. Temporal distribution

The universe is **recency-weighted** by construction (Pass 3, most-recent-first),
so covered picks skew to recent closes. The exact covered-vs-uncovered date split is
**UNMEASURED** (no per-row covered flag is shipped). What is measurable: the full
closed window starts 2026-02-17; the universe starts 2026-02-21 and puts 62% of its
rows in Oct–Nov 2026. Older picks are systematically under-sampled.

### 3. Outcome distribution

- **Universe vs population** (measurable from the shipped payload):
  universe WR 39.57%, mean net −0.410%; population WR 40.85%, mean net −0.335%.
  Close on the headline, per class also close (CRYPTO 36.7 vs 39.9; EQUITY 45.7 vs 46.4;
  ETF 43.5 vs 43.7; COMMODITY 20.0 vs 20.0). So **within the scoreable set** the
  universe's outcome mix is close to the population's.
- **Covered vs uncovered by price**: the 310 uncovered rows are exactly the ones
  where the benchmark could not be computed. Their outcome distribution is
  **scoreable** (they have a PnL) but the *alpha* test cannot run on them, so whether
  they would have shown alpha is **UNMEASURED**.
- **Uncovered by scoreability (6,111)**: these are **largely unscorable by
  construction** (auto-expired timeouts have no win/loss; integrity failures have
  contradictory outcomes). This is the worse bias: the excluded set is excluded
  *because* of how it resolved, so the measured set cannot tell you anything about
  them. That is a different and more serious problem than a scoreable skew.

---

## Verdict

**BIASED.**

Reasoning, unhedged:

1. The "20.97%" is not a coverage rate. It divides a display-universe count by the
   whole-table count. The two defined rates are 21.27% (of all closed) and 35.90%
   (of scoreable), and 91.14% (of the display universe).
2. The measured set is **class-skewed relative to the population**: CRYPTO 0.67×,
   EQUITY 2.15×, ETF 2.56×. Any cross-class aggregate from `selection_alpha` describes
   a rebalanced book, not the real one.
3. Within the price-measurable universe it is **not uniform**: CRYPTO 24.2% vs BOND
   100% coverage. The gate itself marks CRYPTO, FOREX and FUTURES as
   `alpha_coverage_ok = false`.
4. The scoreability fifth is **outcome-selected** (auto-expired / integrity-failed),
   which no amount of extra bar data fixes.

### Ledger verdicts that need a coverage caveat (identify only; do not relabel)

- `classes[]` for **CRYPTO** (`KILL`, `alpha_n` 1,682), **FOREX** (`WEAK`, α_n 132),
  **FUTURES** (`INSUFFICIENT_N`, α_n 5) — these have `alpha_coverage_ok = false` and
  rest on the non-representative subset.
- `classes[].alpha_pct` / `alpha_ci` / `beta_dominant` for **all** classes, because
  the class aggregate is computed on a set whose class mix differs from the
  population (the CRYPTO `KILL` in particular is a verdict on the most-covered
  class, not on the class as it exists).
- `selection_alpha.by_class`, `by_slice`, `by_strategy` (all 39 strategy cells) and
  `selection_alpha.overall` (α = −0.3135%, CI [−0.5171, −0.1221]) — every one is
  computed over the 3,190-row price-covered subset.
- `selection_alpha.gate` (`tested` 445, `demoted` 0) and every `alpha_gate` object
  downstream.
- `segments` (6 cells) and `cells` inherit the same subset.

`coverage.*` itself (the 59.25% scoreable rate) is a statement about the full table
and does not need this caveat; it needs the different caveat that 6,111 rows are
unscored *by outcome*.

---

## Provenance

All paths resolve at `85c0c9c3d3c77b9e45a0fdd384d8d0d9dbc0bd09` (`origin/main`).

| Claim | Path / source |
|---|---|
| `covered`=3,190, `n_universe`=3,500, `bar_coverage`, `missing`, `gate` | `audit_dashboard/data/audit3_ledger.json` → `selection_alpha.*` |
| `total_closed_picks`=14,997, `scored_rows`=8,886, `unscored_rows`=6,111, `excluded_cohorts`, `window`, `resolver_anomalies`, `denominator` | `audit_dashboard/data/audit3_ledger.json` → `coverage.*` |
| 3,133 / 14,941 snapshot | `git show 602ad22ada6f1453aea55ee21feb3aaee32d0184:audit_dashboard/data/audit3_ledger.json` |
| 2,228 / 14,637 snapshot | `git show 095e8a149858b758b0d85bf7df343b3d23166e0d:audit_dashboard/data/audit3_ledger.json` |
| Universe of 3,500 rows, `resolved_closed_picks_net` counts/classes, per-class WR/PF/mean | `docs/audit_review_2026-11-22/_raw/audit_data_dashboard_data.json` (`picks.recent_closed`, `resolved_closed_picks_net`) |
| Cap and selection logic | `audit_trail/dashboard_generator.py:285,286,287,7031,7135` |
| Coverage computation | `alpha_engine/audit3_selection_alpha.py:52-70,301-325,383` |
| Gate threshold | `alpha_engine/audit3_tribunal.py:1164,1165,1244-1252` |
| Sidecar copy of the ledger | `docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json`, `.../audit_data_audit3_ledger.json` |

**UNMEASURED** (and why): per-row covered/uncovered join and therefore per-row class,
strategy and date distribution of the uncovered set; the alpha of the 310 price-missing
rows; the class composition of the 6,111 unscoreable rows. Cause: the canonical rows
file (`resolved_closed_picks_net.json`) and the full current `dashboard_data.json`
are not shipped in the repo, and the price tables are live MySQL, so the selection-alpha
join cannot be re-run offline from `origin/main`.

---

## Amendment

**Block 57 · 2026-11-23 · appended only; nothing above is edited and the BIASED verdict stands.**

Re-measured at `origin/main` = `ce214306b5caf6e52d231f13930cc99f0b7349d2`. Block 56 measured at
`85c0c9c3d3c7`; `git diff --stat 85c0c9c3d3c7 origin/main -- audit_dashboard/data/audit3_ledger.json
audit_dashboard/data/denominator.json docs/audit_review_2026-11-22/_raw/audit_data_dashboard_data.json
alpha_engine/audit3_selection_alpha.py audit_trail/dashboard_generator.py` is empty, so every input
below is the same file Block 56 read.

### Re-verified figures

| Figure | Block 56 | This measurement | Delta |
|---|---|---|---|
| `selection_alpha.covered` | 3,190 | 3,190 | none |
| `selection_alpha.n_universe` | 3,500 | 3,500 | none |
| `coverage.scored_rows` | 8,886 | 8,886 | none |
| `coverage.total_closed_picks` | 14,997 | 14,997 | none |
| covered / universe | 91.14% | 91.14% | none |
| scored / closed | 59.25% | 59.25% | none |
| covered / scored | 35.90% | 35.90% | none |
| covered / closed | 21.27% | 21.27% | none |
| scoreable but outside the 3,500 cap | 5,696 | **5,386** | **−310 (corrected)** |
| `selection_alpha.by_strategy` cells | 39 | **38** | **−1 (corrected)** |

The 11,807 non-covered total is right; its split was not. Measured: **6,111** unscoreable +
**5,386** scoreable-but-outside-the-cap (8,886 − 3,500) + **310** price-missing inside the universe
= 11,807. `5,696 = 5,386 + 310` counts the price-missing rows twice, and the nested diagram above
is short by 310 for the same reason. `by_strategy` holds 38 cells at n ≥ 20, not 39.

### 1. Exclusion-reason taxonomy in code

There are two published taxonomies, and only one of them is a partition of the 6,111 gap.

| Reason label | Where it is produced | Count at `origin/main` |
|---|---|---|
| `invalid_row` | [`build_view()`](alpha_engine/resolved_closed_view.py:200) — `drops[default_exclusion_reason(pick) or "invalid_row"] += 1` | 5,917 |
| `mirror_duplicate` | [`build_view()`](alpha_engine/resolved_closed_view.py:204), key at [`dedupe_key()`](alpha_engine/resolved_closed_view.py:91) | 98 |
| `non_performance_exit` | [`default_exclusion_reason()`](alpha_engine/resolved_closed_view.py:124), reason set at [63–73](alpha_engine/resolved_closed_view.py:63) | 43 |
| `resolver_breakeven_fallback` | [`default_exclusion_reason()`](alpha_engine/resolved_closed_view.py:126) | 53 |
| `integrity_excluded` (cohort) | [`dashboard_generator.py:17119`](audit_trail/dashboard_generator.py:17119) → `coverage.excluded_cohorts` | 6,013 |
| `auto_expired` (cohort) | [`dashboard_generator.py:17138`](audit_trail/dashboard_generator.py:17138) → `coverage.excluded_cohorts` | 9,356 |
| `no_numeric_pnl` | [`build_view()`](alpha_engine/resolved_closed_view.py:208) | 0 published |

The four canonical reasons sum **exactly** to `coverage.unscored_rows` = 6,111
([`coverage.denominator.canonical_excluded_by_reason`](audit_dashboard/data/audit3_ledger.json)).
The two cohorts overlap and are **not** a partition (the ledger's own `coverage.statement` says so).
`audit_dashboard/data/denominator.json` lists the same four reasons at **double** their per-block
value (`invalid_row` 11,834 = 5,917 × 2, …): that file sums two blocks. Read one block, as
[`METRIC_DEFINITIONS.md` §8](docs/audit_review_2026-11-22/METRIC_DEFINITIONS.md) already warns.

### 2. Why each reason cannot be scored, mechanically

- **`invalid_row`** (5,917) is the catch-all for a row the caller's validity predicate rejected
  and the coarse classifier could not name ([`resolved_closed_view.py:106–135`](alpha_engine/resolved_closed_view.py:106)).
  The predicate is [`_is_valid_resolved_pick()`](audit_trail/dashboard_generator.py:4924) with these
  branches: paper-trade / `expired_no_pnl` / `_auto_expired`
  ([4934–4938](audit_trail/dashboard_generator.py:4934)); missing `pnl_pct`
  ([4940–4942](audit_trail/dashboard_generator.py:4940)); PnL corrupt against recorded prices
  ([4948](audit_trail/dashboard_generator.py:4948)); impossible non-crypto move
  ([4956](audit_trail/dashboard_generator.py:4956)); entry-vs-exit magnitude > 100×
  ([4963](audit_trail/dashboard_generator.py:4963)); placeholder exit ≤ 0
  ([4971–4978](audit_trail/dashboard_generator.py:4971)); historically blocked symbol/strategy
  ([4985](audit_trail/dashboard_generator.py:4985)); non-performance exit reason
  ([4989](audit_trail/dashboard_generator.py:4989)); `STALE*` or `INVALID_ENTRY`
  ([4991](audit_trail/dashboard_generator.py:4991)); `RESOLVE_FAILED*`
  ([4999](audit_trail/dashboard_generator.py:4999)); non-performance terminal status
  ([5003](audit_trail/dashboard_generator.py:5003)); hold under 60 s
  ([5013](audit_trail/dashboard_generator.py:5013), constant at [4890](audit_trail/dashboard_generator.py:4890));
  unknown exit reason with no close marker ([5017–5030](audit_trail/dashboard_generator.py:5017)).
  So `invalid_row` mixes both kinds: *no outcome exists* (missing PnL, expired markers) and
  *an outcome exists but was discarded as untrustworthy* (corrupt price, placeholder exit,
  micro-hold, blocked symbol). The split between those branches is **UNMEASURED** (see §4).
- **`mirror_duplicate`** (98): an outcome exists, but the row is the same economic trade as another
  row already counted, under the dashboard's own key of (symbol, direction, entry, PnL)
  ([`dedupe_key()`](alpha_engine/resolved_closed_view.py:91)). Discarded as a copy, not lost.
- **`non_performance_exit`** (43): the exit reason is `""`, `UNKNOWN`, `MANUAL`, `CANCELLED`,
  `INVALID_ENTRY`, `NO_FILL`, `NOT_FILLED` or `STALE*` ([`resolved_closed_view.py:63–73`](alpha_engine/resolved_closed_view.py:63),
  [:124](alpha_engine/resolved_closed_view.py:124)): a cancel, a non-fill or a stale exit.
  **No trade outcome exists.**
- **`resolver_breakeven_fallback`** (53): `RESOLVE_FAILED*` ([`resolved_closed_view.py:126`](alpha_engine/resolved_closed_view.py:126)):
  no exit price was ever resolved and PnL was forced to 0. **No outcome exists**; the zero is fabricated.
- **`auto_expired` cohort** (9,356, overlapping): the staleness pass stamps `status = EXPIRED`,
  `exit_reason = "STALE (auto-expired >Nh)"` and `expired_no_pnl` when PnL is 0
  ([`dashboard_generator.py:9738–9744`](audit_trail/dashboard_generator.py:9738)), and
  [`_is_auto_expired_pick()`](audit_trail/dashboard_generator.py:4865) (0 PnL **and** a stale-ish
  exit/status, patterns at [4526](audit_trail/dashboard_generator.py:4526)) splits them out at
  [9764–9789](audit_trail/dashboard_generator.py:9764). A timeout is neither win nor loss: **no
  outcome exists**.
- **`integrity_excluded` cohort** (6,013, overlapping): ghost rows, WON-vs-PnL sign contradictions,
  constant/zero PnL. Outcomes exist but are internally contradictory: discarded.

### 3. Shipped artefacts searched for per-row / per-class exclusion counts

Searched `audit_exports/`, `reports/`, `data/`, `audit_dashboard/data/`,
`docs/audit_review_2026-11-22/_raw/` (5,316 JSON/JSONL files matched by content, plus a
`git ls-files` check for the rows file). **No per-class or per-row counts of the excluded rows exist
anywhere at `origin/main`.** What does exist is aggregate only:

| Artefact | What it carries | Field |
|---|---|---|
| `audit_dashboard/data/audit3_ledger.json` | the four canonical reasons (5,917 / 98 / 43 / 53) | `coverage.denominator.canonical_excluded_by_reason` |
| same | the two overlapping cohorts (6,013 / 9,356) | `coverage.excluded_cohorts` |
| same | resolver anomalies over 24,353 scanned rows: stale exit beyond stop 46, clamped loss 23, expired zero-PnL **3,554**, closed rows missing `closed_at` 3 | `coverage.resolver_anomalies` |
| same | 628 denylisted-strategy hits, by class CRYPTO 496 / COMMODITY 121 / FOREX 11 | `denylist_hits.by_class` |
| `audit_dashboard/data/denominator.json` | the four reasons summed over two blocks (12,222) | `exclusion_reasons` |
| `docs/.../_raw/audit_data_dashboard_data.json` | one snapshot earlier: 5,891 / 93 / 44 / 59 = 6,087 of 14,914 kept 8,827; `summary.integrity_excluded` 5,994, `auto_expired_excluded` 9,277 | `resolved_closed_picks_net.counts`, `summary` |
| `reports/2026-11-21-audit123-collective-review.json` | prose review quoting the ledger, no counts of its own | — |

`denylist_hits.by_class` is **not** the excluded set: it counts picks whose strategy hit the
denylist, in a different population. The rows file itself (`resolved_closed_picks_net.json`,
[`ROWS_FILENAME`](alpha_engine/resolved_closed_view.py:42)) is **not tracked** (`git ls-files` returns
nothing), and the payload only ships it as `rows_embedded: false`
([`payload_block()`](alpha_engine/resolved_closed_view.py:317)). `picks.recent_closed` ships only the
3,500 kept rows.

### 4. UNMEASURED

The class composition, strategy mix and date distribution of the 6,111 unscoreable rows remain
**UNMEASURED**: no shipped row carries an exclusion reason next to its asset class.
The artefact that would measure them is a published `resolved_closed_picks_net.json` whose excluded
rows keep `exclude_reason` + `asset_class` (or the generator wired to embed
[`summarize_excluded()`](audit_trail/excluded_cohorts.py:31) output in the payload/sidecar, which is
already written and tested but not called by [`dashboard_generator.py`](audit_trail/dashboard_generator.py:14902)).
No distribution is inferred here.
