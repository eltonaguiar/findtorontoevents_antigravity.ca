# audit3 vs audit2 — and the database gap that stops us tracking either

**Date:** 2026-11-19 · **Scope:** read-only review of `/audit2` and `/audit3`, plus a new
write path for audit3 state. No change to `/audit`, `/audit2` or `audit-dashboard.yml`.

---

## 1. Which surface actually finds winners

| | `/audit3` | `/audit2` |
|---|---|---|
| Size | `audit_dashboard/audit3.html` 719 lines + `alpha_engine/audit3_*.py` (1,901 + 830 + 649 + 321 lines) | `audit_dashboard/audit2.html` 116 lines + `audit2.js` 203 lines |
| Computes anything? | **Yes** — the whole tribunal | **No** — it `fetch()`es `audit3_ledger.json` and `audit2_forward.json` and renders them |
| Input | closed-pick canonical ledger (`dashboard_data.json`) | audit3's own output |
| Output | per-cell verdicts under 10 pre-declared gates | pods, trial budget, measures library, traps, retired-with-reason |

**audit2 cannot find a winner on its own.** It is a 319-line presentation layer over a file
audit3 writes; every number it shows originates in the tribunal. Its value is editorial:
it holds the positive side (what to forward-test next), the trial budget and the graveyard,
which audit3's kill ledger deliberately does not.

**audit3 is the only instrument.** Its measured gates are: G0 sample floor (n≥20 verdict,
n≥100 PROVEN), G1 one-sided exact binomial on WR, G2 bootstrap CI on net expectancy
(2,000 seeded resamples), G3 Benjamini-Hochberg FDR q≤0.10, G4 Deflated Sharpe ≥0.95 with
the global trial count (359 configurations, not just survivors), G5 chronological
split-half, G6 concentration, G7 slippage deducted *before* every statistic, G8 selection
alpha (pick net − direction-adjusted hold), G9 cost stress at 2× slippage.

So: **use audit3 to find, audit2 to decide what to test next.** Neither is money-ready and
audit3 says so on its own page.

---

## 2. The state today — 2026-11-19

Live `https://findtorontoevents.ca/audit3/audit3_ledger.json`, generated
`2026-11-19T16:53:50Z` from a source snapshot of `16:05:18Z`:

| metric | value |
|---|---|
| canonical closed rows scored | 8,613 |
| cells total / tested | 359 / 67 |
| PROVEN_T2 | **0** |
| CANDIDATE | **0** |
| WEAK | 59 |
| KILL | 8 |
| INSUFFICIENT_N | 292 |

By class: **CRYPTO KILL** (n=6,740), **EQUITY WEAK** (939), **ETF WEAK** (586),
**FOREX WEAK** (258), **COMMODITY KILL** (51), **BOND WEAK** (35), **FUTURES INSUFFICIENT_N** (4).

Forward clock: 430 forward rows, all `H-119` (SOLUSDT/BTCUSDT intrabar), net PF CI-lower-bound
**0.9213** and IR **0.043** → not promotable. Seven pods exist, all with `n_forward: 0`:
`POD-EQUITY-BREAKOUT` (`pre_registered`) plus six `observe` pods including
`POD-CRYPTO-POSITION`.

**G8 is structurally inert in CI.** `selection_alpha.available` is **false** in the deployed
ledger — the module needs the `crypto_ohlcv` / `fx_prices` price tables and the CI runner
cannot reach them. The section renders, the measurement is absent. G9 therefore reports
`unmeasured` on the live page even though the code path is correct.

### The day's actual results (from `ejaguiar1_stocks.at_pick_outcomes`, `resolved_at >= CURDATE()`)

| | n | avg PnL/trade | WR |
|---|---|---|---|
| all | 800 | **−0.137%** | 36.0% |
| crypto | 521 | −0.181% | 34.2% |
| EQUITY | 277 | −0.056% | 39.4% |
| FOREX | 2 | +0.007% | 50.0% |

Six-day trend (avg PnL / WR): 11‑14 −1.093%/15.1 → 11‑15 −0.911%/14.9 → 11‑16 −0.312%/5.4 →
11‑17 −0.738%/32.8 → 11‑18 −0.595%/36.4 → **11‑19 −0.137%/36.0**. Losses are shrinking five
days running but the book has not had a positive day in this window.

Best lines today by summed PnL (min 3 trades):

| strategy | class | n | avg | WR |
|---|---|---|---|---|
| `hs_lb_None` | crypto | 58 | +1.845% | 72.4% |
| `MeanReversionBB` | equity | 209 | +0.426% | 49.3% |
| `MeanReversionBB` | crypto | 21 | +1.095% | 61.9% |
| `clone_hl_copy_lb_None` | crypto | 15 | +1.314% | 66.7% |
| `GPX_Gen10_2a4b0b` | crypto | 8 | +1.875% | 75.0% |
| `GPX_Gen14_da88cc` | crypto | 5 | +3.000% | 100.0% |

`MeanReversionBB` on EQUITY is the only positive line today with a sample worth reading.

---

## 3. The finding that matters: the day's best line is invisible to audit3

`MeanReversionBB / EQUITY` (209 trades, +0.426%/trade, 49.3% WR today) **does not exist as a
cell in the 359-cell ledger.** Scanning every cell for the strategy name returns exactly one
row: `FOREX MeanReversionBB SHORT n=29 verdict=KILL`.

The reason is the denominator. The ledger scores 8,613 canonical rows kept from ~14,632 in
`dashboard_data.json` (excluded: `invalid_row` 5,802, `mirror_duplicate` 92,
`non_performance_exit` 43, `resolver_breakeven_fallback` 90). `at_pick_outcomes` holds
**63,137** resolved rows. audit3 is therefore scoring a curated subset, and the strategy that
made money today is outside it.

That is not a bug in the tribunal — the canonical view exists to stop double-counted and
non-performance exits polluting verdicts. It is a **tracking gap**: nothing joins the canonical
verdicts back to the resolved picks, so a strategy can be profitable in the database and
absent from the board at the same time.

---

## 4. Verdict on "is it synced to a database like ejaguiar1_stocks?"

**No.** `ejaguiar1_stocks` has 409 tables. Matching audit/forward/verdict/hypothesis/ledger
names returns five, none of them audit3:

| table | rows | what it is |
|---|---|---|
| `mystery_audit3`-style tables | — | absent |
| `miracle_audit3` | 424 | unrelated: `daily_scan` log, last write 2026‑05‑12, every line `Schema: FAILED` |
| `ai_strategy_forward_tests` | 0 | empty |
| `lm_walk_forward` / `walk_forward_results` | 0 | empty |
| `walk_forward_summary` | 10 | unrelated |

Closest real tables: `at_pick_outcomes` (63,137) and `at_pick_flow_daily` (1,241, last refreshed
2026‑11‑18, and it contains an `UNKNOWN` class row with 2 raw emissions). Neither carries a
cell id, a canonical hash or a gate verdict.

Consequences, all of them unanswerable today:

1. **No verdict history.** `audit3_ledger.json` is overwritten hourly. "When did CRYPTO flip to
   KILL?" cannot be answered; the live document even ships a `verdict_churn` block computed
   inside a single run (`n_tracked 438, n_flipped 2, churn_rate 0.0046`), which is the closest
   thing to history that exists.
2. **No forward-row accrual history.** 430 rows live only in `reports/forward_observations.jsonl`
   in git. Per-pod accrual rate per day requires `git log` archaeology.
3. **No join from a pick to its verdict.** You cannot ask which resolved picks came from a KILL
   cell, which is exactly the query that would have surfaced §3 automatically.
4. **Pre-registration integrity is not checkable in SQL**, only by reading
   `reports/hypothesis_registry.json` (106 entries).

---

## 5. What I changed, and why

New tool `tools/audit3_db_sync.py` (+ `tests/test_audit3_db_sync.py`) mirrors the five stateful
audit3 objects into `ejaguiar1_stocks` so §4's four questions become `SELECT`s.

| table | key | the question it answers |
|---|---|---|
| `audit3_ledger_snapshots` | `snapshot_id` = sha256(generated_at, git_sha, input_sha256) | one row per generator run: verdict counts, coverage, `selection_alpha_available`, forward fingerprint |
| `audit3_cell_verdicts` | `(snapshot_id, namespace, asset_class, strategy, direction)` | verdict history per cell; class verdicts land with `namespace='__class__'` |
| `audit3_pod_clocks` | `(snapshot_id, pod_id)` | per-pod `n_forward`, `eligible`, `promotion_blocked_by` over time |
| `audit3_forward_observations` | `observation_id` | append-only mirror of the JSONL; `first_seen_snapshot` records when each row appeared |
| `audit3_hypotheses` | `hypothesis_id` | registry status + `acceptance_criteria` JSON, so a pod joins to what it pre-registered |

Justifications, per design decision:

- **Content-addressed snapshot id, not a timestamp.** Two hourly runs on the same source
  produce the same `snapshot_id` and collapse into one row; a real regeneration produces a new
  one. This is what makes re-running safe and history trustworthy.
- **Upsert only.** Every statement is `CREATE TABLE IF NOT EXISTS` or
  `INSERT ... ON DUPLICATE KEY UPDATE`. No `DELETE`, `TRUNCATE`, `DROP` or `ALTER` appears
  anywhere in the module — a test asserts this on the emitted DDL. History cannot be lost by
  running it twice.
- **Dry run by default.** Nothing opens a socket without `--apply`. A test monkeypatches
  `apply_plan` to raise and asserts the default path never reaches it. There is no env var that
  can silently enable writing.
- **`%s` placeholders everywhere.** The only interpolated identifier is the table name, from the
  module's own constant. A test asserts no fixture value appears in any SQL string.
- **PK columns coerced to `''` not `NULL`.** MySQL treats `NULL` in a unique index as distinct,
  so a nullable strategy/direction would defeat idempotency and duplicate every class row.
- **Timestamps normalised to UTC `DATETIME` text.** Mixed `+00:00` offsets and bare dates in the
  registry would otherwise fail or skew on insert.
- **Registry mirrored too.** Without it, a pod's `n_forward` cannot be joined to the
  `acceptance_criteria` it was supposed to be judged against — the pre-registration rule is the
  only thing preventing post-hoc promotion.
- **`selection_alpha_available` stored per snapshot.** This records in the database that CI
  could not measure G8 on a given run, so "G9 unmeasured" is a recorded fact rather than a
  silent zero.

Deliberately **not** done:

- `--apply` has **not** been run against production. Creating five tables in `ejaguiar1_stocks`
  is a production write and needs the owner's go-ahead; the standing rule for this work is
  READ-ONLY DB.
- No CI workflow wired yet. The natural home is the existing `audit3-ledger` job, after its
  deploy step, gated on a repository secret. Not added because it would start writing on the
  next hourly run without approval.
- G8 was **not** made to compute in CI. That needs the price tables reachable from the runner —
  a separate change with its own credential question.
- Neither `/audit` nor `/audit2` was touched.

---

## 6. Verification

```
python3 -m pytest tests/test_audit3_db_sync.py -q      # 15 tests
python3 tools/audit3_db_sync.py --ledger /tmp/live_ledger.json --json-out /tmp/sync_plan.json
```

Dry run against the live 16:53Z ledger:

```
snapshot_id snap_401e94eff2eb08121f64
  audit3_ledger_snapshots                 1 rows
  audit3_cell_verdicts                  366 rows     # 359 cells + 7 classes
  audit3_pod_clocks                       7 rows
  audit3_forward_observations           430 rows
  audit3_hypotheses                     106 rows
dry run: no database connection was opened (pass --apply to write)
```

To enable, on the owner's approval:

```
python3 tools/audit3_db_sync.py --apply
```

Then §4's questions become, e.g.:

```sql
-- when did CRYPTO turn KILL, and did n grow?
SELECT s.generated_at, c.verdict, c.n, c.net_ci_lo_pct
FROM audit3_cell_verdicts c JOIN audit3_ledger_snapshots s USING (snapshot_id)
WHERE c.namespace='__class__' AND c.asset_class='CRYPTO' ORDER BY s.generated_at;

-- which cells touched CANDIDATE and fell back?
SELECT asset_class, strategy, direction, COUNT(DISTINCT snapshot_id) snaps
FROM audit3_cell_verdicts WHERE verdict='CANDIDATE' GROUP BY 1,2,3;
```

## 7. Recommended next steps

1. **Approve `--apply`** so the next hourly ledger starts writing history (highest value, lowest risk).
2. **Investigate `MeanReversionBB / EQUITY`** — 209 trades, +0.426%/trade today, absent from the
   canonical view. Either it is excluded for a real reason (worth documenting) or the canonical
   filter is dropping live edge.
3. **Make G8 compute in CI**, otherwise G9 stays `unmeasured` and the strongest gate in the
   tribunal never runs.
4. **Join audit3 verdicts to `at_pick_outcomes` pick ids** — the sync above gets the verdict side;
   the pick side needs a `cell_key` column on the outcomes rows.
