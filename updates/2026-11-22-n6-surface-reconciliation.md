# N6 — Reconcile the four "closed pick" surfaces

Date: 2026-11-22
Scope: establish who writes each surface and when, attribute every delta, rule on which
surface (if any) is authoritative, and make one narrow improvement.
No commits, no staging, no pushes (orchestrator commits).
`reports/forward_observations.jsonl` untouched — md5 verified `fb4c12cf33fe18153661669df5540a55`
before and after.

## Verdict in one line

The four surfaces are **four different populations produced at four different times by the
same mutable pipeline**, and the largest delta is explained by the regeneration being run from
a working tree that is not what production runs. No published count is reproducible from the
tree; see §4 for the ruling and §5 for the one change made.

---

## 1. Who writes each surface, and when

| Surface | Writer (file:line) | Trigger / workflow | Timestamp | Rows | Digest |
|---|---|---|---|---|---|
| **A** [`reports/audit3_ledger.json`](reports/audit3_ledger.json) | **Does not exist.** The real path is [`audit_dashboard/data/audit3_ledger.json`](audit_dashboard/data/audit3_ledger.json), written by [`alpha_engine/audit3_tribunal.py`](alpha_engine/audit3_tribunal.py) (invoked at [`audit3-ledger.yml`](.github/workflows/audit3-ledger.yml:200) with `--out`), committed at [`audit3-ledger.yml`](.github/workflows/audit3-ledger.yml:293) | `audit3-ledger.yml`, cron `23 */6 * * *` ([line 18](.github/workflows/audit3-ledger.yml:18)) | `generated_at` `2026-11-20T01:57:23Z`; `source_generated_at` `2026-11-20T01:17:09Z` (worktree copy). Committed value on `origin/main`: `2026-11-22T07:10:35Z` from a payload generated `2026-11-22T04:00:19Z` | 8,769 (committed: 8,827) | `63609da5…2c08` (committed: `ed25b59c…7e01`) |
| **B** [`audit_dashboard/data/dashboard_data.json`](audit_dashboard/data/dashboard_data.json) | [`audit_trail/dashboard_generator.py`](audit_trail/dashboard_generator.py:18913) (`external_data_path.write_text`), payload block built at [`dashboard_generator.py:14907`](audit_trail/dashboard_generator.py:14907) via [`alpha_engine/resolved_closed_view.py`](alpha_engine/resolved_closed_view.py) `build_view` | `audit-dashboard.yml`, cron `10 */3 * * *` ([line 13](.github/workflows/audit-dashboard.yml:13)); **gitignored** ([`.gitignore:222`](.gitignore:222)), never committed (`git log --all` empty) | local mtime 2026-11-22 06:53:12Z, payload `generated_at` 2026-11-22T04:00:19Z (this checkout is behind the run that wrote it) | 8,827 | `ed25b59c…7e01` |
| **C** live `/audit/data/resolved_closed_picks_net.json` | Same writer as B (`_write_canonical_view`, [`dashboard_generator.py:14918`](audit_trail/dashboard_generator.py:14918)); deployed by FTP `data/*.json` glob ([`audit-dashboard.yml:1242`](.github/workflows/audit-dashboard.yml:1242)) | `audit-dashboard.yml` → FTP to 50webs/GoDaddy | HTTP `last-modified` 2026-11-22 10:02:38Z; `generated_at` 2026-11-22T09:58:18Z | 8,816 | `e346e65f…e346` (verifies internally) |
| **C′** live `/audit/data/dashboard_data.json` | Same as B | Same | HTTP `last-modified` 10:02:44Z; `generated_at` 2026-11-22T09:55:10Z | block 8,816 | `e346e65f…e346` |
| **C″** live `/audit3/audit3_ledger.json` | Same as A | `audit3-ledger.yml` → FTP ([line 332](.github/workflows/audit3-ledger.yml:332)) | `generated_at` 2026-11-22T07:10:35Z | 8,827 | `ed25b59c…7e01` |
| **D** freshly regenerated (this session, N4's run) | [`audit_trail/dashboard_generator.py`](audit_trail/dashboard_generator.py) `collect_all_picks()` + `build_view(validity=_is_valid_resolved_pick)` + `write_view`, run locally **without** `AUDIT_DB_PASS` | none (manual) | local mtime 2026-11-22 10:57:17Z | 10,968 | `c0942d9e…5dd8` |

**Timestamps first, as instructed.** They were not written minutes apart by one cron:

- The **live** copies (C, C′, C″) are the freshest real surfaces: 09:55–10:02Z today.
- The **committed ledger** on `origin/main` (A) is from 07:10Z, built on a payload from 04:00Z.
- The **local copy of A** in this worktree is from **2026-11-20T01:57Z** (two days old) and its
  `source_generated_at` is 2026-11-20T01:17Z. It is a stale worktree artifact, not a current
  surface. That alone explains the "8,769 vs 8,827" row delta as **stale data**, not a
  mechanism disagreement (see §2.1).
- The local copy of B is 06:53Z with a 04:00Z payload; the live copy is 09:55Z. Same workflow,
  different runs.
- D was produced at 10:57Z by this session, from this working tree, with no MySQL.

## 2. Accounting for the deltas

### 2.1 A(8,769) vs B(8,827): +58, and the excluded-cohort swing

- 8,827 is `summary.total_resolved` in the 04:00Z payload. 8,769 is the ledger's
  `canonical_kept_rows`, which is simply `resolved_closed_picks_net.counts.kept_rows` copied
  from that same payload ([`audit3_tribunal.py:756`](alpha_engine/audit3_tribunal.py:756)).
  The two numbers are the **same field read at two different times**: 8,827 at 04:00Z, 8,816 at
  09:55Z. The 8,769 value is from the 2026-11-20 01:17Z payload. So +58 is **two days of
  drift**, not a definitional gap.
- The "excluded" asymmetry (ledger 7,508 vs dashboard 5,994) is **not** a ±1,514 swing in one
  quantity. They are two different fields with similar names:
  - `5,994` = `summary.integrity_excluded` = `total_closed - len(_filter_valid_resolved_picks(closed))`
    ([`dashboard_generator.py:14988`](audit_trail/dashboard_generator.py:14988),
    [`:17119`](audit_trail/dashboard_generator.py:17119)). It equals the sidecar's
    `invalid_row + non_performance_exit + resolver_breakeven_fallback` = 5,891 + 44 + 59 = 5,994.
  - `7,508` = `integrity_excluded` as reported in the 2026-11-20 ledger, i.e. the same field on
    the older payload.
  - Both are **overlapping** with `auto_expired` (`cohorts_overlap: true`); the ledger says so
    itself. They do not sum to the gap. The closed-book identity holds exactly at each
    timestamp: `resolved + integrity + mirror = total` → `8,827 + 5,994 + 93 = 14,914` (04:00Z)
    and `8,816 + 5,995 + 94 = 14,905` (09:55Z).
  - Remaining difference 7,508 → 5,994 over two days is 1,514 rows that moved from the
    integrity cohort into the resolved/normalised book as upstream resolvers rewrote picks
    (auto-expiry, dedup, status normalisation). It is the same direction as the +58 resolved
    drift and is not independently verifiable from the tree because no historical payload is
    retained.

### 2.2 B(8,827) vs C(8,816): −11

- **One deploy behind, plus real churn.** C is 09:58Z, B is 04:00Z. Over that window
  `total_closed` fell 14,914 → 14,905 (−9), `auto_expired` fell 9,277 → 9,221 (−56),
  `integrity_excluded` rose 5,994 → 5,995 (+1), and resolved went 8,827 → 8,816 (−11).
- It is not a pure lag: the later surface has *fewer* rows, which a monotone append-only book
  cannot do. New picks were also added (64 `kimi_signal_tracking` rows in C are absent from the
  regen sidecar D, the newest one closed 09:22Z). So C is a *different* book, not B plus time.
- Mechanically this is expected: the book is rebuilt from mutable JSON files every run and
  rows can be re-classified, expired, or dropped between runs.

### 2.3 D(10,968) vs all published surfaces: +~2,100

This is the largest gap and the one that matters for reproducibility. **It is not MySQL.**
Without `AUDIT_DB_PASS` the regeneration should be *smaller*, not larger, so the "no MySQL"
caveat cannot explain a surplus. Evidence from comparing D with C row-by-row
(`(join_key or id)`):

- D ∩ C = 8,494; D-only = 2,474; C-only = 322.
- D-only by class: CRYPTO 2,415, FOREX 26, EQUITY 17, FUTURES 8, ETF 6, COMMODITY 2.
- D-only by source system: `baby_strats_forward` **1,595**, `alpha_engine` 318,
  `dna_winner_picks` 141, `ml_strategy_reviver_inverse` 85, …
- `baby_strats_forward` rows come from [`battleground/data/baby_strats_dashboard.json`](battleground/data/baby_strats_dashboard.json)
  ([`dashboard_generator.py:9241`](audit_trail/dashboard_generator.py:9241)). That file is
  **gitignored** ([`.gitignore:300`](.gitignore:300)), 5.6 MB, mtime 2026-06-06 in this
  checkout, and holds 284 strategies / 12,812 forward trades locally. The live run has **zero**
  `baby_strats_forward` rows in its sidecar. A local untracked file that CI does not have is
  exactly the kind of input that makes a local regeneration non-reproducible.
- D also carries 318 `alpha_engine` rows C lacks and C carries 32 D lacks; D has 21
  `kimi_riseoftheclaw`/ 29 `kimi_signal_tracking` rows fewer than C. The local JSON pool and
  the CI pool are simply different snapshots.
- Hypothesis (b) from the brief, *different validity filter*, is **falsified** as the main
  cause: D was built with `dg._is_valid_resolved_pick`, the same predicate the production
  pipeline calls ([`dashboard_generator.py:14907`](audit_trail/dashboard_generator.py:14907)).
  The working tree does add `zero_pnl_quarantined` to `resolved_closed_view.py`, which only
  *removes* rows (D has 28 zero-PnL rows vs C's 81), so it works against a surplus.
- Hypothesis (c), *older code revision or older payload*, is partly true for the ledger
  (committed 07:10Z built on a 04:00Z payload) but not for the live copies.
- `donchian-stock-breakout`: 48 rows in D and 48 in C, all `source_system: kimi_riseoftheclaw`,
  closed 2026-03-09 → 2026-11-05. **N2's 44 MySQL rows are not in either sidecar** (they are
  `source_system: kimi_riseoftheclaw_equity_breakout`, `id: n2_…`, closed 2026-11-16; zero
  `n2_` rows in D, zero `kimi_riseoftheclaw_equity_breakout` rows in C). They are invisible
  here because the MySQL merge in `collect_all_picks()` only pulls *non-crypto* closed history
  and the live sidecar's export/dedupe already had 48 donchian rows from the JSON source.
  This confirms the brief's caution: N2's inserts are not in the local collection path.

### 2.4 Digest mismatch is expected, by design

[`resolved_closed_view.py:323`](alpha_engine/resolved_closed_view.py:323) hashes the `rows`
list after sorting by `closed_at`, and the file is rewritten each build. Any two runs with a
single different row produce a different digest. So digest inequality carries **no**
information about correctness on its own; what it does carry is that no published digest can
be re-verified from the repository.

## 3. What the ledger actually says about its own digest

The committed ledger (`origin/main`) is honest about this: `mode: canonical`,
`loaded_from_sidecar: true`, `canonical_rows_sha256 = ed25b59c…` (the payload block's value),
and it scores the fetched live sidecar. The worktree copy adds `digest_stale: true` and a note
that the regenerated sidecar does not reproduce the published digest. Both statements are
consistent with what §2 found.

## 4. Ruling: which surface is authoritative?

Candidates, ruled on rather than picked:

- **`audit3_ledger.json`** (published digest + explicit denominator contract): the best
  *documented* surface, and its `coverage.denominator` block is the only place that names its
  population, cost model and win definition. But its rows are copied from whatever payload the
  sidecar held at fetch time, and the sidecar is never retained. It is authoritative *about its
  contract*, not *about the count*.
- **`dashboard_data.json`**: what the pages render, but gitignored and overwritten every 3
  hours; the live copy and the local copy differ by 11 rows within 6 hours. It is a display
  snapshot, not a record.
- **The live `/audit/...` copy**: freshest and internally self-consistent (its digest verifies
  for its own rows), but it is simply the latest FTP overwrite of a file that is gone on the
  next deploy. Verifiable *now*, unreproducible *later*.

**Ruling: none of them is authoritative for a quotable count, and that is a P0.**
Every surface is an un-versioned regeneration of a mutable book; the rows file has never been
committed (`git log --all` empty for it, and `dashboard_data.json` is gitignored by
[`.gitignore:222`](.gitignore:222)). A digest over a file that is regenerated every run and
retained nowhere is not a reproducibility contract. Until the rows file is retained by CI,
**no published closed-pick count should be quoted as fact**; quote the live number with its
timestamp, or nothing.

The live surface is the least-wrong *operational* number (freshest, self-verifying); the
ledger is the least-wrong *methodological* one (it states its denominator). Neither is
reproducible.

## 5. The one change made

**Changed:** one additive step in [`audit3-ledger.yml`](.github/workflows/audit3-ledger.yml:252)
that uploads `/tmp/audit3/resolved_closed_picks_net.json` (the sidecar the ledger just scored)
as the `audit3-canonical-rows` artifact, `retention-days: 90`, `if: always()`,
`if-no-files-found: warn`.

Why this and not committing the file: committing the rows file from the 3-hourly dashboard job
adds ~3.8 MB per run to git history (the same repo-bloat class the 2026-05-22 fix removed for
`dashboard_data.json`), and the live file changes every run, so the digest would still point at
a moving target. An artifact keeps the exact bytes behind each published digest for 90 days at
zero git cost. No `push:` trigger was added; `[skip ci]` behaviour is untouched
(the workflow's commit step is unchanged). YAML parses (15 steps, both artifact steps present).

Verification of constraints: `reports/forward_observations.jsonl` md5 still
`fb4c12cf33fe18153661669df5540a55`; no published digest was overwritten; no row was deleted.

## 6. What remains unresolved

1. **No retained historical payload.** The 7,508 → 5,994 cohort move and the exact composition
   of the 8,769 book cannot be verified after the fact; only current copies exist.
2. **The rows file is still not versioned.** The artifact helps for future runs but the
   existing published digests (`63609da5…`, `ed25b59c…`, `e346e65f…`) remain unverifiable.
3. **Local vs CI input divergence.** Untracked/gignored inputs (`baby_strats_dashboard.json`,
   other pick JSON) make a local regeneration non-reproducible by construction; D's 10,968 is a
   local book, not a claim about the production book.
4. **Zero-PnL handling differs** between the worktree predicate (quarantined) and the published
   sidecar (81 zero-PnL rows in C survived the live run's older code).
5. **`reports/audit3_ledger.json` does not exist**; the brief's path is wrong and should be
   `audit_dashboard/data/audit3_ledger.json`.
