# Per-class verdict panel on /audit2 — implementation plan

**Seat:** `subq-savant-1.4` · 2026-11-20 · plan only, nothing committed, no production code changed.
**Grounding:** [`reports/2026-11-20-audit2-audit3-recon.md`](../reports/2026-11-20-audit2-audit3-recon.md) plus live read-only queries I ran in this session against `ejaguiar1_stocks` (`mysql.50webs.com`).
**Status:** not approved by anyone. Nobody has replied on COMS to my three threads, so this is one agent's proposal, not a consensus.

---

## 1. ELI5

The audit pages judge trading strategies, but they only speak in one voice: a total verdict for the whole book, per asset class. Right now you cannot ask "which *strategies inside crypto* survive, and which are just noise that happens to be crypto?" without reading the raw ledger yourself. So we build a small, honest panel on /audit2 that shows, for each asset class, the strategies inside it with their sample size, expected profit, confidence interval, profit factor, win rate and a verdict word — every number labelled with where it came from. The point is not to make the page prettier; it's to make a class-level verdict *auditable* — you can see which strategies are carrying a class and which are dragging it, and you can see when a class verdict rests on too few trades to mean anything.

---

## 2. What is actually true today

Numbered, each with a citation:

1. **/audit2 is static HTML + JS that renders audit3's ledger.** There is no Python generator for `audit2.html`; it is hand-authored ([`audit_dashboard/audit2.html`](../audit_dashboard/audit2.html:1), 115 lines) plus [`audit_dashboard/audit2.js`](../audit_dashboard/audit2.js:1) (204 lines). It fetches `audit3_ledger.json` client-side, trying four paths in order ([`audit2.js`](../audit_dashboard/audit2.js:138)), and the page footer states it plainly: "Every live number on this page comes from `audit3_ledger.json`" ([`audit2.html`](../audit_dashboard/audit2.html:112)).
2. **/audit3 is tribunal-driven, 6-hourly, with no push trigger.** Cron `23 */6 * * *` ([`.github/workflows/audit3-ledger.yml`](../.github/workflows/audit3-ledger.yml:18)), own concurrency group ([`:24`](../.github/workflows/audit3-ledger.yml:24)), entry point [`audit3-ledger.yml:200`](../.github/workflows/audit3-ledger.yml:200) running `python3 -m alpha_engine.audit3_tribunal`.
3. **`audit3_edge_hunt.py` is in zero workflows.** Grepped `.github/workflows/` for `audit3_edge_hunt` / `edge_hunt` — zero hits. Its only documented invocation is manual, in its own docstring ([`alpha_engine/audit3_edge_hunt.py`](../alpha_engine/audit3_edge_hunt.py:42)). Same is true of `cpcv_overfit_detector`, `run_anti_overfit_audit`, `wfe`, `probabilistic_sharpe_engine`.
4. **Per-class rollup already exists and is already in the payload.** `class_rollup(rows)` at [`resolved_closed_view.py`](../alpha_engine/resolved_closed_view.py:270) returns per class `n`, `wins`, `losses`, `flat`, `win_rate_pct`, `profit_factor`, `mean_gross_pct`, `mean_net_pct`, `mean_cost_bps`, and is consumed at [`resolved_closed_view.py:258`](../alpha_engine/resolved_closed_view.py:258) (`"classes": class_rollup(rows)`).
5. **Both payloads already carry `classes` and `cells`.** The ledger's top-level keys include `classes`, `cells`, `segments`, `symbols` (emitted around [`audit3_tribunal.py:2086`](../alpha_engine/audit3_tribunal.py:2086)–`2088`). So the panel needs no new computation on the server side — it is a join of two fields that are already shipped.
6. **audit2's verdict block is already per-class.** `Asset class | Verdict | n | Net expectancy/trade | Net 95% CI | 2× cost OK | DSR | required_n` ([`audit2.html`](../audit_dashboard/audit2.html:62)), rendered from `d.classes` at [`audit2.js`](../audit_dashboard/audit2.js:110). The panel is an extension of an existing shape, not a new one.
7. **`trading_picks` has no `asset_class` column.** Verified by `DESCRIBE trading_picks` on the live DB: the columns are `id, symbol, direction, strategy, entry_price, take_profit, stop_loss, confidence, elite_score, trust_score, category, source_system, status, pnl_pct, exit_price, created_at, closed_at, exit_reason, updated_at, …`. The class is derived from `symbol` at read time ([`audit3_tribunal.py:89`](../alpha_engine/audit3_tribunal.py:89) via `symbol_identity`). Any DB-side per-class query must use `category` as a proxy and say so.

---

## 3. The decision: verdict table, not signal feed

**We are building a verdict table. We are not building a strategy feed, and we are not generating signals on an audit surface.**

This is a deliberate refusal of one reading of "enhancing with some strategies per asset class" — the reading where the audit page starts suggesting picks. The independence argument is that the audit page's authority comes from *judging without emitting*:

- The Evidence Registry tab says it in its own words: "Prior backtests are **evidence, not verdicts**… nothing on this tab can promote a strategy" ([`audit_dashboard/audit3.html`](../audit_dashboard/audit3.html:215)).
- The tribunal's doctrine is "innocent until proven guilty" and "nothing is removed from the closed-pick ledger by this module" ([`alpha_engine/audit3_tribunal.py`](../alpha_engine/audit3_tribunal.py:48)).

A page that both emits and judges has a stake in which strategies get emitted, and its verdicts stop being trustworthy. That refusal serves the user better than compliance would: you get the *diagnostic* value (which strategies carry a class, which are noise) without losing the one property that makes the page worth reading — that it has nothing to gain from the answer.

What the user actually wants to see — per-class composition — is fully achievable inside the verdict-table reading. That is what this plan builds.

---

## 4. Phases

Each phase has an exit condition and is independently useful if the next never happens.

### Phase A — settle the denominator

**The measured problem.** Two components define "a performance-scored closed row" differently:

| | Tribunal ([`audit3_tribunal.py:537`](../alpha_engine/audit3_tribunal.py:537)) | Canonical view ([`resolved_closed_view.py:93`](../alpha_engine/resolved_closed_view.py:93), `:153`–`:160`) |
|---|---|---|
| Mechanism | deny-list of 3 statuses | deny-list of 5 statuses **plus** an `exit_reason` deny-list plus `STALE*` prefix |
| Excludes by status | `OPEN`, `PENDING`, `""` | `OPEN`, `PENDING`, `CANCELLED`, `CANCELED`, `INVALID` |
| Excludes by exit_reason | — (never reads `exit_reason`) | `""`, `UNKNOWN`, `MANUAL`, `CANCELLED`, `CANCELED`, `INVALID_ENTRY`, `NO_FILL`, `NOT_FILLED`, and anything starting `STALE` |
| Requires | numeric `pnl_pct`, dedupe on id | numeric `pnl_pct`, dedupe on (symbol, direction, entry, pnl), plus paper/expired/resolver-fallback exclusions |

**Set difference, contested by status:** *empty*. Live `trading_picks.status` values among rows with a numeric pnl are `TIME_EXIT` (33,560), `OPEN` (15,710), `TP_HIT` (7,098), `LOST` (5,662), `SL_HIT` (3,908), `EXPIRED` (2,396), `ACTIVE` (13). No row today carries `CANCELLED`, `CANCELED` or `INVALID`, so the status clauses disagree on **zero rows**.

**The real difference is the exit-reason clause.** The tribunal never looks at `exit_reason`; the canonical view drops rows on it. Measured on the live DB:

- Tribunal filter keeps **52,637** rows; canonical filter keeps **47,669**. Delta **4,968**.
- Cause split: **4,868** rows with `exit_reason IS NULL`, **100** rows with a `STALE*` prefix.
- By class (`category`, the DB's class-ish column): crypto 4,913 (4,818 null-exit, 95 stale), equity 31, ETF 11, FOREX 9, FUTURES 3, commodity 1.

**Verdict: real, but narrower than the recon implied.** It is not cosmetic — ~4.9k rows is ~9.4% of the tribunal's denominator, and it is 9 of 11 classes. But the *status* half of the claim is currently vacuous, and the whole disagreement is dormant in the default path: the live ledger shows the tribunal ran with `mode: canonical`, `loaded_from_sidecar: true`, `canonical_kept_rows: 8769`, `share_of_canonical_pct: 100.0`, with `canonical_excluded_by_reason: {invalid_row: 7394, mirror_duplicate: 95, non_performance_exit: 43, resolver_breakeven_fallback: 71}`. In canonical mode the tribunal consumes the canonical rows, so the two agree by construction. The disagreement bites only in the `payload_slice` fallback (sidecar missing or hash mismatch), where the tribunal applies its own 3-value deny-list to the raw payload.

**Do the two read the same rows at all?** `class_rollup()` reads the canonical rows list; the tribunal reads either the same canonical sidecar (default) or the raw payload slice (fallback). So they *can* read the same rows, and today they do — but nothing enforces it. That is exactly why Phase A is worth doing: the agreement is currently an accident of the sidecar being present, not a guarantee.

**The fix.** One canonical predicate — `is_performance_scored_row(pick) -> bool` — in `resolved_closed_view.py`, and have the tribunal call it instead of its inline deny-list, in both modes.

**Exit condition:** a test that runs both consumers over one fixture containing `exit_reason=None`, `STALE_*`, `CANCELLED`, and a normal row, and asserts both produce the same kept-row count. Fails today (4,968-row gap reproduced on fixture), passes after.

### Phase B — the per-class verdict panel

Additive `<section>` on /audit2 after the Verdicts block ([`audit2.html`](../audit_dashboard/audit2.html:67)), rendered inside `renderLedger()` ([`audit2.js`](../audit_dashboard/audit2.js:99)), fed by `d.classes` joined to `d.cells`.

Per asset class, a table with one row per strategy cell: **class · strategy · direction · n · net mean · net CI · PF · win rate · verdict word · provenance**.

Provenance labelling is mandatory — e.g. `net mean: class_rollup (cost CRYPTO 9.97 bps)`, `CI: G2 bootstrap`, `verdict: G0–G9 tribunal`. The repo already has a precedent for why: /audit and /audit3 disagreed by 3× on the same class while both being arithmetically correct, purely from unattributed numbers ([`resolved_closed_view.py:77`](../alpha_engine/resolved_closed_view.py:77)).

Honest presentation: many cells will be `INSUFFICIENT_N` at n < 20 ([`audit3_tribunal.py:98`](../alpha_engine/audit3_tribunal.py:98)). Show them as rows. A panel that hides them is lying about coverage.

**Exit condition:** panel renders on the live page with real data, and its per-class `n` reconciles exactly against a terminal `class_rollup()` run on the same payload.

### Phase C — wire the dead validator

Add `audit3_edge_hunt.py` to [`audit3-ledger.yml`](../.github/workflows/audit3-ledger.yml) as `continue-on-error: true` at first, mirroring how `audit3_selection_alpha.py` is wired at [`:165`](../.github/workflows/audit3-ledger.yml:165) (with `:151` setting the flag). Rationale: its output should exist and be inspectable before anybody gates on it. Note a peer's observation on the bus — several gates in this repo are advisory, so a `continue-on-error` step cannot fail a build today. That is a reason to wire it now and make it blocking later, not a reason to skip it.

**Exit condition:** edge-hunt output appears in the payload with a key of its own.

### Phase D — backtest freshness

`bt_backtest_runs` frozen 2026-03-06 (~259 days) and `bt_backtest_trades` 34.6M vs 27.2M are **taken from the task brief — I did not query them in this session**, and I will not present them as measured.

First action is **diagnosis, not repair**: determine whether the import job exists and is broken, or was retired. Check [`audit_trail/import_backtest_trades.py`](../audit_trail/import_backtest_trades.py) and whatever schedules it; check whether `bt_backtest_runs` has any writer at all. Also relevant: ghost rows are a known issue here — [`tools/cleanup_ghost_rows.py`](../tools/cleanup_ghost_rows.py:9) documents "12 cohorts totalling 276,145 ghost rows across bt_backtest_trades", and [`template.html`](../audit_dashboard/template.html:913) reports 22,947 still quarantined. The 34.6M vs 27.2M divergence is plausibly the same phenomenon, which is a hypothesis to test, not a conclusion.

**Exit condition:** a named owner and a stated intent — fix or retire — written down, with the evidence that decided it.

---

## 5. What I will NOT do

- **No signal generation on an audit surface.** No picks, no "buy this" on /audit2 or /audit3. See §3.
- **No per-class panel built on an unverified denominator.** Phase B depends on Phase A or on an explicit, visible statement of which denominator it used.
- **No full sweep of all 414 DB tables.** Only what a phase needs.
- **No refactor of production code in this task**, and no commit or push.
- **No claim that `bt_backtest_runs` is frozen** until I have queried it — it is a brief-supplied number today.
- **No fourth per-class aggregate.** Reuse `class_rollup()`; /audit already has per-class spans, an OOS table and a SUPREME EDGE block, and a fifth implementation would be a fifth way to disagree.

---

## 6. Test plan

1. **Phase A filter agreement (deterministic unit test).** Fixture with four rows: normal closed, `exit_reason=None`, `exit_reason="STALE_OPEN_BACKFILL"`, `status="CANCELLED"`. Assert `len(tribunal_filter(fixture)) == len(canonical_filter(fixture))`. Fails before the fix, passes after. No DB, no network.
2. **Panel reconciliation test.** Load a captured `audit3_ledger.json`, extract the panel's per-class rows from the rendered DOM string (or from the render function's return value), and assert each class's `n`, `net mean`, `PF`, `win rate` equal `class_rollup(rows)[cls]` for the same payload. Exact equality on `n`; tolerance on floats.
3. **Live-surface verification without a browser.** Fetch the deployed `audit3_ledger.json` and `audit2.js`-rendered output over HTTP, compare the payload JSON's `classes` block against the numbers embedded in the served HTML. A mismatch means the page is rendering a stale or different payload — which is precisely the failure mode the provenance footer ([`audit2.js`](../audit_dashboard/audit2.js:129)) already warns about when the source path is `/tmp`.

---

## 7. Honest risks

- **The panel reads as an endorsement.** A table listing strategies per class looks like a menu even when it says `KILL`. *Mitigation:* the verdict word is a column, not a colour; the section header states the panel is diagnostic, and no row links to a trade action.
- **6-hourly refresh, no push trigger.** A fix may not appear on the live page for hours ([`audit3-ledger.yml:18`](../.github/workflows/audit3-ledger.yml:18)). *Mitigation:* use `workflow_dispatch` for immediate redeploy during development, and never verify against the live page right after a change without checking `generated_at` in the payload.
* **Other agents may be editing the same files.** I posted a claim-your-files standard (`notes/subq-collaboration-standard-20261120`) and nobody has replied. *Mitigation:* claim files explicitly before editing, keep each phase's edits minimal and separate, and re-read a file immediately before applying a diff rather than trusting an earlier read.
- **Phase A could make the tribunal stricter and change existing verdicts.** Dropping 4,968 more rows could move a class from CANDIDATE to INSUFFICIENT_N. *Mitigation:* land Phase A with a before/after diff of the ledger's `classes` block, published, so the verdict churn is visible rather than silent. The ledger already has a `verdict_churn` key for exactly this.
- **The DB is a shared live system and my numbers are a snapshot.** `trading_picks` had 148,295 rows with 68,347 carrying a pnl at the time I queried. *Mitigation:* every number in this plan is dated and attributed to a query, and the tests in §6 use fixtures, not the live DB.

---

## 8. Sequencing

1. **Phase A** first — everything downstream divides by its denominator, and its test is cheap and deterministic.
2. **Phase B** next — it is the actual deliverable, and it is additive (no existing structure moves).
3. **Phase C** — independent, small, can run in parallel with B.
4. **Phase D** — diagnosis only, no dependency on A–C.

**Depends on what:** B depends on A for an honest denominator (or on stating which one it used). C and D depend on nothing.

**If time is short, drop in this order:** D (diagnosis can wait), then C, then B. **Never drop A** — a panel on an unsettled denominator is worse than no panel, because it looks authoritative.

---

## Appendix — provenance of the numbers in this plan

| Number | Where it came from |
|---|---|
| 52,637 / 47,669 / 4,968 kept-row delta | My query, this session, `ejaguiar1_stocks` @ `mysql.50webs.com`, read-only |
| 4,868 null-exit + 100 STALE | Same query, cause-split |
| Per-class delta (crypto 4,913 … commodity 1) | Same query, grouped by `category` (proxy — no `asset_class` column exists) |
| 148,295 total / 68,347 with pnl | Same session, `SELECT COUNT(*), SUM(pnl_pct IS NOT NULL)` |
| Status vocabulary and counts | Same session, `GROUP BY status WHERE pnl_pct IS NOT NULL` |
| `canonical_kept_rows: 8769`, `mode: canonical`, excluded-by-reason | `audit_dashboard/data/audit3_ledger.json`, generated 2026-11-20T01:57:23Z |
| `bt_backtest_runs` frozen 2026-03-06, 34.6M vs 27.2M | **Task brief only — NOT measured by me.** Treat as unverified. |
| Code behaviour (filters, cron, dead modules) | Files read directly; line numbers as cited |
