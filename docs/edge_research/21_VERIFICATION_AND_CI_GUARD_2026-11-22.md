# 21 — Verification and CI guard (items 42–45)

Date: 2026-11-22. Scope: items 42, 43, 44, 45 only. Evidence file:
`reports/verification_20261122.json`. No rows inserted or modified; nothing pushed.

---

## 42 — Do the N2 pod rows ever resolve into `at_signal_outcomes`?

**VERDICT: STUCK (never resolves as-is).**

Resolution path, read from [`audit_trail/universal_pick_resolver.py`](../../audit_trail/universal_pick_resolver.py):

- The resolver reads JSON pick files listed in `SYSTEM_SOURCES` (line 138). It never
  reads `trading_picks`.
- It skips rows already closed ([`_is_closed_like_raw_pick()`](../../audit_trail/universal_pick_resolver.py:1161)).
- It needs `symbol`, `direction`, `entry_price`, and a price path (live snapshot,
  yfinance 1h bars for non-crypto, Binance klines for crypto, lines 1324–1408).
  It auto-computes TP/SL and then clamps SL to 2.5% (line 1659).
- Its time exit for EQUITY/ETF is 96h (`MAX_HOLD_HOURS_BY_CLASS`, line 78).
- Its only MySQL write is [`_write_outcomes_to_mysql()`](../../audit_trail/universal_pick_resolver.py:1180),
  which upserts into `at_pick_outcomes`. There is **no** `INSERT`/`UPDATE` of
  `at_signal_outcomes` anywhere in the file.

Schedule: `universal_pick_resolver` runs inside the
[`audit-dashboard.yml`](../../.github/workflows/audit-dashboard.yml:147) job (cron `10 */3 * * *`).

Per strategy (all rows have `take_profit IS NULL`, so no TP path exists):

| strategy | rows | ACTIVE | CLOSED | verdict | bad field |
|---|---|---|---|---|---|
| donchian-stock-breakout | 44 | 4 | 40 | **STUCK** | `take_profit = None` on 44/44 |
| adx-trend-scout | 44 | 6 | 38 | **STUCK** | `take_profit = None` on 44/44 |
| vol-contraction-scout | 44 | 0 | 44 | **STUCK** | `take_profit = None` on 44/44 |
| rs-breakout-scout | 43 | 6 | 37 | **STUCK** | `take_profit = None` on 43/43 |

The emitter writes `"take_profit": None` ([`build_row()`](../../tools/emit_equity_breakout_pod.py:209)).

Current state (read-only query):
`SELECT strategy,status,COUNT(*) n FROM trading_picks WHERE id LIKE 'n2\_%' GROUP BY strategy,status`
→ 175 n2_ rows, 159 CLOSED (latest `closed_at` 2026-11-19), 16 ACTIVE (all past the 96h hold).
`SELECT ... FROM at_signal_outcomes WHERE strategy IN (4 names)` → `()` (empty).
`SELECT ... FROM at_pick_outcomes WHERE strategy IN (4 names)` → `()` (empty).

Earliest resolution date: **never, while the write path is unchanged**. The 159 closed rows
would already be eligible if a closed-row mirror into `at_signal_outcomes` ran, but the only
code that would do that, [`_repair_signal_outcomes()`](../../tools/repair_data_integrity.py:269),
is referenced by **zero** workflow files.

What would have to change (not done here): the emitter must write a real `take_profit`, and
a closed-row mirror from `trading_picks` into `at_signal_outcomes` must actually run.

---

## 43 — Is the audit3 digest reproducible post-CI?

**VERDICT: NOT_REPRODUCIBLE_BY_DESIGN. Artifact: PROVISIONAL_PENDING_CI (does not exist yet).**

Artifact check: the upload step is at
[`.github/workflows/audit3-ledger.yml:252`](../../.github/workflows/audit3-ledger.yml:252)
(`audit3-canonical-rows`, 90-day retention). That step exists only on
`push/n1-n8-research-integrity` (commit `bbc4510b66f`, unmerged); it is **not in
`origin/main`**. For the four latest successful runs (45022690968 at 2026-11-22T12:31Z,
44996865303, 44994305292, 44968290977), `gh api .../actions/runs/<id>/artifacts` returned
`{"total_count":0,"artifacts":[]}`. So the artifact has never been produced.

Why the digest must change on every rebuild: at
[`alpha_engine/resolved_closed_view.py:323`](../../alpha_engine/resolved_closed_view.py:323)
the row list is sorted by `closed_at`, then hashed (`rows_sha256`, line 344). The row set is
the post-dedup, post-exclusion, post-cost-model output of the *current* inputs: every local
JSON source, the exclusion rules, and the gitignored `baby_strats_dashboard.json`. A rebuild
over different inputs produces a different row set, so it produces a different hash.
The hash is computed after the rows are written, over whatever was written.

Consequence: the digest identifies a **snapshot**, not a **dataset version**. It can never
serve as a cross-surface reconciliation key. Observed today: the live `/audit` digest was
`e346e65f…` (8,816 rows) at 09:58Z and `5a6ff492…` (8,792 rows) at 13:01Z, with no one
changing anything.

What the artifact buys: it makes each published digest's **bytes retrievable**. That is a
different, smaller property than reproducibility. It lets you check *what a digest described*,
not regenerate *the same digest*. It is not a fix for reproducibility.

---

## 44 — Four-surface reconciliation post-merge

**VERDICT: no surface authoritative (P0 restated and applied). No new cause found.**

| surface | rows | digest | timestamp |
|---|---|---|---|
| ledger (`audit3_ledger.json`) | 8,769 | `63609da5…` | 2026-11-20T01:57:23Z |
| dashboard_data | 8,827 | `ed25b59c…` | 2026-11-22T04:03:30Z |
| live /audit | 8,816 | `e346e65f…` | 2026-11-22T09:58:18Z |
| local regen | 10,968 | `c0942d9e…` | 2026-11-22T10:57:17Z |

All four were reachable. Re-fetching live /audit at 13:09Z returned 8,792 rows / `5a6ff492…`,
which is drift, not a correction.

Deltas: ledger→dashboard_data +58; dashboard_data→live −11; live→regen +2,152.
Key overlap: 8,033 shared, 1,990 only in regen, 289 only live.

Causes, from the established taxonomy:
- **temporal drift** — each surface has a different `generated_at`; the +58 was the 2-day gap.
- **gitignored local input** — `baby_strats_forward` 0 (live) vs 1,595 (regen); its source
  `battleground/data/baby_strats_dashboard.json` is gitignored ([`.gitignore:300`](../../.gitignore:300)).
- **overlapping reasons (not a partition)** — live has `resolver_breakeven_fallback=59`, regen
  has `zero_pnl_quarantined=567` and `paper_trade=1`; the "swing" 7,508 vs 5,994 is the same
  field at two timestamps overlapping `auto_expired`.
- **different populations** — regen `input_rows` 21,008 vs live 14,905.

Merge status of the three pushed branches (`git merge-base --is-ancestor`; `git rev-list --count origin/main..origin/<b>`):

| branch | sha | status | commits ahead |
|---|---|---|---|
| push/n1-n8-research-integrity | `532413a292e` | **PENDING** | 1 |
| push/edge-research-p0 | `68d887c8641` | **PENDING** | 1 |
| push/h119-nonpromotable | `78b9794ad77` | **PENDING** | 1 |

`origin/main` is at `8dc0fe805b12`. Nothing has merged since item 27.

---

## 45 — CI guard against unretrievable digests

**VERDICT: FAIL against today's state (correct result).**

Built: [`tools/digest_artifact_guard.py`](../../tools/digest_artifact_guard.py), the manifest
[`reports/published_digests_manifest.json`](../../reports/published_digests_manifest.json),
tests [`tests/test_digest_artifact_guard.py`](../../tests/test_digest_artifact_guard.py), and
the read-only workflow [`.github/workflows/digest-artifact-guard.yml`](../../.github/workflows/digest-artifact-guard.yml).

The guard distinguishes PASS (artifact matches), FAIL (no artifact), FAIL (hash mismatch) and
SKIP (no digests published, explicitly not a pass). It needs no secrets, no MySQL, does not
rebuild anything and commits nothing.

Test line: `13 passed in 0.16s`.

Guard run against the real manifest (`python tools/digest_artifact_guard.py --online`):

```
FAIL audit3 ledger (...): no_artifact published=63609da549a7 actual=None artifact=None
FAIL dashboard_data.json (...): no_artifact published=ed25b59c52a4 actual=None artifact=None
FAIL live /audit (...): hash_mismatch published=e346e65ffd4a actual=5a6ff492f797 artifact=url:https://findtorontoevents.ca/...
PASS local regen (...): match published=c0942d9e8f62 actual=c0942d9e8f62 artifact=audit_dashboard/data/resolved_closed_picks_net.json
```

Unretrievable digests: ledger `63609da5…`, dashboard_data `ed25b59c…`, live `/audit` `e346e65f…`
(the live one is retrievable in principle but has already drifted). Only the local regen digest
is backed by an artifact, and that file is absent from `origin/main`.
