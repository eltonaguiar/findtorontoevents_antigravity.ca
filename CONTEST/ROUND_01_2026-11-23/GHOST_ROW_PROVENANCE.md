# GHOST-ROW PROVENANCE

**Verdict: ghost rows were confined to the display / audit view layer and to a separate backtest-trade table (`bt_backtest_trades`) that no forward or walk-forward validator reads. The forward and walk-forward results are not a ghost-row artifact and need no relabel. The one backtest-family consumer that does read `bt_backtest_trades` raw (`tools/edge_extractor.py` → `edge_per_class.json`) is affected, but its output is not tracked in the repo and no test or gate consumes it.**

Measured on a non-shallow clone of `origin/main` at `31b340e` (2026-11-23T17:21:35Z). Every number below is either reproduced from a committed artifact with a `[SRC: ...]` reference or marked `UNMEASURED` with the reason.

---

## 1. The measured premise

| Claim | Source in the tree | Measured value | Reproduces? |
|---|---|---|---|
| "Hardcoded GREEN" | [`template.html:859`](audit_dashboard/template.html:859) said `Ghost rows: 0 (was 22,947)` unconditionally; the ghost tile's tier came from the JSON | **Real at the time, since fixed.** The literal survived until [`8ab22db96c7`](audit_dashboard/template.html:859) (2026-11-16) replaced it. Today's text reads the live count. The "GREEN" was `ghost_row_verdict()` defaulting a *zero* count to green ([`db_health_check.py:180-189`](tools/db_health_check.py:180)), i.e. a default that the real count overwrote: `db_health.json` now carries `tier: red` [SRC: audit_dashboard/data/db_health.json:63] | **Yes (historically); no longer hardcoded** |
| "Only 21% covered" | `selection_alpha.covered` [SRC: audit_dashboard/data/audit3_ledger.json:148] over `total_closed_picks` [SRC: audit_dashboard/data/audit3_ledger.json:106] | **3,133 / 14,941 = 20.97%** | **Yes** (if this is the 21% meant). Two other 21% figures exist and are *not* row-coverage-by-join: TP-fill of WON rows 38/185 [SRC: reports/peer_claude-freebuff-status-std_plan_2026-05-31.md:71], and the `rsi` field populated on 21.0% of OPEN rows [SRC: 2026-11-14/finpredict-v2_20261114-1602/MASTER_AUDIT.md:188] |
| "22,947 ghost rows" | [`db_health_check.py:192-259`](tools/db_health_check.py:192) over `bt_backtest_trades`; snapshot [SRC: audit_dashboard/data/db_health.json:69] | **22,947**, and it is exactly the sum of the 10 listed cohorts (all MEMECOIN / `meta_strategy`, top DOGEUSDT LONG pn=3,569). Cohorts are found per asset class with `pnl_pct IS NOT NULL LIMIT 500000`, grouped on `(strategy, symbol, direction, ROUND(pnl_pct,4))`, `HAVING COUNT(*)>1000 AND COUNT(DISTINCT entry_price)<5` | **Yes as a number**; it is a lower bound, not a census (see §5) |

The join key for the ghost test is `(strategy, symbol, direction, ROUND(pnl_pct,4))`, with `COUNT(DISTINCT entry_price)<5` as the anti-signal. Both sides are the *same* table: it is a self-join (group-by) over `bt_backtest_trades`, not a join between two tables.

---

## 2. The data flow

Two separate pipelines share nothing but a reader of `at_raw_picks`:

**(A) The dashboard / audit pipeline**
```
bt_backtest_trades (MySQL, ~32.7M rows [SRC: alpha_engine/audit3_evidence.py:718])
  └─ written by sync_all_picks_to_mysql.py:612-640 (_insert_bt_trade, from local SQLite source tables)
     and backfill.py:593 / import_backtest_trades.py:618 / backtest_justin_bravo.py:413
  ├─ tools/db_health_check.py:192-259  (ghost census, display metric only)
  │    → audit_dashboard/data/db_health.json  → dashboard_enhancements.js:769-776 (tile), 841-850 (banner)
  ├─ tools/edge_extractor.py:40-50 (FULL SCAN, raw) → reports/edge_per_class.json (untracked)
  │    → tools/hc_health_monitor.py:49, tools/_hc_noncrypto_diagnostic.py:33 (gate helpers, read dashboard picks not the JSON)
  ├─ alpha_engine/calculate_statistical_edge.py:33-51 (UNION of bt rows WHERE status='CLOSED' with at_signal_outcomes; prints only)
  └─ tools/cot_lag_corrector.py:128 (reads bt rows for one strategy; writes COT corrections)
```

**(B) The forward / walk-forward pipeline**
```
at_raw_picks / trading_picks (MySQL)  ──►  audit_trail/data/dashboard_payload.json (gitignored; built by dashboard_generator.py)
                                              ├─ alpha_engine/walkforward_validator.py:35-38 → :42-49 (recent_closed)
                                              ├─ alpha_engine/forward_validator.py:292-298 → active_picks.json / closed_picks.json
                                              └─ audit_dashboard/data/audit3_ledger.json (canonical scoring)
```

The two pipelines cross only at `at_raw_picks`: `sync_all_picks_to_mysql.py` writes the same local rows into `at_raw_picks` *and* `bt_backtest_trades` ([:619-641](sync_all_picks_to_mysql.py:619)). `dashboard_generator.py` never queries `bt_backtest_trades` (grep: only `bt_backtest_runs` at [:11367](audit_trail/dashboard_generator.py:11367), a different table).

---

## 3. The join type

The ghost-bearing step is a **GROUP BY self-aggregate with a HAVING filter**, not a SQL JOIN:

- [`tools/db_health_check.py:215-227`](tools/db_health_check.py:215) — `GROUP BY strategy, symbol, direction, ROUND(pnl_pct,4) HAVING COUNT(*)>1000 AND COUNT(DISTINCT entry_price)<5`.

What happens to unmatched rows depends on the consumer, and this is the whole answer:

- **Display tile:** nothing is dropped or kept per row; only the aggregate count is shown. Confined to display by construction.
- **Dashboard aggregates (the one place a join-like filter exists):** [`dashboard_generator.py:4985`](audit_trail/dashboard_generator.py:4985) calls `_is_historical_blocked_pick`, which at [:4820](audit_trail/dashboard_generator.py:4820) does `if sym and (asset_class, strategy, sym) in blocked['symbol_triples']: return True`. `_is_valid_resolved_pick` returns `False` for those rows, so they are **dropped (inner-join semantics)** from `resolved_closed`. The blocked set is a hand-maintained 13-tuple constant [`quality_gates.py:3034`](audit_trail/quality_gates.py:3034) whose comment [SRC: audit_trail/quality_gates.py:3019] says it is exactly for ghost cohorts "so the ghost rows stop polluting WR/PF/MDD". A retained-ghost join here would be the contamination case; it is the opposite.

So: **ghost rows are either ignored (display) or excluded (aggregates). Neither path retains them.**

---

## 4. The backtest input boundary

| Input path | Consumed by | Downstream of the ghost-bearing step? |
|---|---|---|
| `audit_trail/data/dashboard_payload.json` (`picks.recent_closed`) | [`walkforward_validator.py:35`](alpha_engine/walkforward_validator.py:35) | **No.** Built from JSON pick sources + `trading_picks`, not `bt_backtest_trades`; and ghosts are filtered out beforehand ([`dashboard_generator.py:4985`](audit_trail/dashboard_generator.py:4985)) |
| `alpha_engine/data/active_picks.json` / `closed_picks.json` | [`forward_validator.py:292`](alpha_engine/forward_validator.py:292), [:879](alpha_engine/forward_validator.py:879) | **No.** Same reason |
| `audit_dashboard/data/audit3_ledger.json` | the /audit3 scoring surface | **No.** Its denominator excludes a cohort literally described as "ghost rows, WON-vs-PnL sign contradictions, constant/zero pnl" [SRC: audit_dashboard/data/audit3_ledger.json:88] |
| `alpha_engine/data/survivor_backtest_results.json` | [`paper_trading/strategies/catered_symbol_strategies.py:24-29`](paper_trading/strategies/catered_symbol_strategies.py:24) | **No.** A separate backtest results file |
| `backtest_results/*.json` | standalone runners | **No.** No ghost-cohort join feeds these |
| `reports/edge_per_class.json` | [`tools/edge_extractor.py:174-175`](tools/edge_extractor.py:174) | **Yes** — it scans `bt_backtest_trades` raw with no ghost filter. But the file is **not tracked** (`git ls-files reports/edge_per_class.json` → empty), and its only readers are gate *helpers* that read dashboard picks, not the JSON. No test or gate asserts on it |

`bt_backtest_trades` itself is a *backtest-trade* store, so ghost rows do sit in a backtest-data table. That is not the same as contaminating backtest *results*: the forward/walk-forward validators read the live payload, and the results in `backtest_results/` are produced by runners that do not consume the ghost cohorts.

---

## 5. What remains unverified

- **Live recount.** The DB password in `/home/eaguiar2015/dbpasses.txt` no longer authenticates (`Access denied for user 'ejaguiar1_stocks'`), so I could not re-run the ghost SQL against MySQL. §1's count is from the committed `db_health.json` snapshot (2026-11-23T15:42:57Z), not a fresh census.
- **It is a lower bound.** The query samples `LIMIT 500000` per class and takes `ORDER BY n DESC LIMIT 10` cohorts [SRC: tools/db_health_check.py:222], and CRYPTO was sampled at 150,000 rows [SRC: audit_dashboard/data/db_health.json:63]. More ghosts can exist than 22,947; this does not weaken the provenance answer, which depends on *where* they go, not how many.
- **The 21% identity is inferred.** I matched 20.97% to the selection-alpha coverage; the brief did not say which 21% it meant, and two other 21% figures exist (§1).
- **`cot_lag_corrector.py`** reads ghost-able bt rows for one strategy and writes COT corrections; whether any ghost cohort is in that strategy is `UNMEASURED` (needs DB access).

**Note on the page's own text:** the /audit footer already states the position this measurement supports: "22,947 ghost rows remain quarantined out of the canonical view" [SRC: audit_dashboard/template.html:913]. Quarantine in the view, not removal from the raw table, matches what I measured.

**Programme tally:** not restated here.

---

## Amendments (2026-11-23, Block 55)

Block 54 named three exposures it could not verify. Each is now resolved against `origin/main`. **The original verdict stands** ("confined to display/audit"), with one material caveat and one now-closed `UNMEASURED`. Nothing here changes a result, a ledger, or a label.

### A. The `edge_extractor` path: untracked, unscheduled, ungated

- **Untracked, and not gitignored — simply never committed.** `git cat-file -e origin/main:reports/edge_per_class.json` → **exit 128** ("path does not exist in origin/main"); `git check-ignore -v reports/edge_per_class.json` → **exit 1** (no rule matches). `reports/edge_report_mysql.md`, the sibling output, is likewise absent (`git cat-file -e origin/main:reports/edge_report_mysql.md` → exit 128). So the file is untracked by omission, not by an ignore rule.
- **Every `edge_per_class` hit, classified.** Two are **writers**: [`tools/edge_extractor.py:175`](tools/edge_extractor.py:175) (`out_json = ... / "edge_per_class.json"`) and [`tools/edge_scanner.py:76`](tools/edge_scanner.py:76) (a Windows-path `json_path` that is written at :77-78). **No hit reads the JSON as a file.** [`tools/hc_health_monitor.py:49`](tools/hc_health_monitor.py:49) and [`tools/_hc_noncrypto_diagnostic.py:33`](tools/_hc_noncrypto_diagnostic.py:33) define a function *named* `passes_validated_edge_per_class`, but it consumes dashboard picks (`p.get("score")`, `trust_score`, `strat_fwd_wr`), not the JSON. The remaining hits ([`DAILY_IDEAS_PROMPTS.MD:1028`](DAILY_IDEAS_PROMPTS.MD:1028), `reports/*.md`, `CONTEST/...` itself) are **doc/comment**. **No gating consumer exists.**
- **Not scheduled.** `grep -rn 'edge_extractor' .github/` → exit 1 (no hits); same for `edge_scanner` and for `edge_per_class`/`edge_report_mysql` in `.github/`. Neither producer runs in CI, so its output cannot affect pass/fail.
- **It does not filter ghosts.** The query is [`tools/edge_extractor.py:46`](tools/edge_extractor.py:46): `SELECT asset_class, strategy, pnl_pct, direction, confidence, entry_time, exit_time FROM bt_backtest_trades` — no `WHERE`, no ghost predicate. Aggregation is per asset class ([`tools/edge_extractor.py:53`](tools/edge_extractor.py:53)) and per `(asset_class, strategy)` ([`tools/edge_extractor.py:110`](tools/edge_extractor.py:110)), emitting `win_rate`, `profit_factor`, `sharpe`, `expectancy` ([`tools/edge_extractor.py:95`](tools/edge_extractor.py:95)). It *counts* duplicates ([`tools/edge_extractor.py:146`](tools/edge_extractor.py:146)) but does not exclude them.
- **Consequence for the verdict: confirms it, with a caveat.** The path cannot change a verdict, a promotion, `money_ready`, a CI check, or an allocation. The caveat is real but confined to a human reader: the Markdown sibling ([`tools/edge_extractor.py:177`](tools/edge_extractor.py:177)) prints `WR=…, PF=…, Sharpe=…` per asset class computed over ghost-inflated rows. Ghost rows are ~22,947 concentrated duplicates, so a per-class WR there is not a performance estimate. It is a presentation hazard, not a gate.

### B. The `cot_lag_corrector` question: closed on strategy, empty intersection

- **What it reads.** [`tools/cot_lag_corrector.py:124`](tools/cot_lag_corrector.py:124) queries `bt_backtest_trades` (primary) with `WHERE (strategy = %s OR source_table = %s) AND status IN ('TP','SL','CLOSED','TIME')` bound to `MULTI_ASSET_COT_SOURCE` ([:80](tools/cot_lag_corrector.py:80), `= "multi_asset_cot"`) at [:129-134](tools/cot_lag_corrector.py:129); it falls back to `raw_picks` `WHERE source_system = %s` ([:157](tools/cot_lag_corrector.py:157)) only when the first returns nothing.
- **Does it gate?** Yes, this is a gating path: [`audit_trail/quality_gates.py:8425`](audit_trail/quality_gates.py:8425) calls it for `COMMODITY` picks only, and [:8429-8434](audit_trail/quality_gates.py:8429) `return False` (reject) when `COT_MATCH_GATE_ENABLED=1`; the default is `shadow` ([:8422](audit_trail/quality_gates.py:8422)), which tags `_cot_shadow_reject` without rejecting ([:8436](audit_trail/quality_gates.py:8436)).
- **Set comparison against the 10 ghost cohorts** (`db_health.json` `top_cohorts`, e.g. [:88-96](audit_dashboard/data/db_health.json:88)):

| Set | Members |
|---|---|
| Ghost cohorts' `strategy` (10/10) | `{meta_strategy}` |
| Ghost cohorts' `asset_class` (10/10) | `{MEMECOIN}` |
| Ghost cohorts' `symbol` | `{DOGEUSDT, WIFUSDT, PEPEUSDT, FLOKIUSDT, BONKUSDT, SHIBUSDT, ORDIUSDT}` |
| Corrector's `strategy` / `source_table` | `{multi_asset_cot}` |
| Corrector's asset class (gate scope) | `{COMMODITY}` |

  `{meta_strategy} ∩ {multi_asset_cot} = ∅`; `{MEMECOIN} ∩ {COMMODITY} = ∅`. **The intersection is empty on both `strategy` and `asset_class`.**
- **Residual, stated not worked around.** The corrector's `source_table = 'multi_asset_cot'` disjunct could in principle select a row whose `strategy` is not `multi_asset_cot`; ruling that out fully needs DB access (the ghosts are crypto-perp symbols while COT is commodity futures, but that is an inference, not a measurement). Even then, the gate is `COMMODITY`-scoped ([:8425](audit_trail/quality_gates.py:8425)) and in `shadow` by default, so it tags rather than rejects. Block 54's `UNMEASURED` becomes: **empty by static set comparison; a DB-verified source_table cross-check remains outstanding.**

### C. The live recount is a snapshot, not a census

- **`dbpasses.txt` is not tracked.** `git cat-file -e origin/main:dbpasses.txt` → **exit 128**; it exists only on disk at `/home/eaguiar2015/dbpasses.txt` (mode `-rw-------`, no value printed). `git check-ignore -v dbpasses.txt` → exit 1, i.e. it is not gitignored either; it is simply outside the repo. `.gitignore` covers `.env`-style files ([:71](.gitignore:71)) but names no `dbpasses.txt`.
- **Provenance of 22,947.** It is `checks.ghost_rows.data.total_ghost_rows` in [`audit_dashboard/data/db_health.json:84`](audit_dashboard/data/db_health.json:84), from a file with `generated_at` **2026-11-23T18:43:46Z** ([:2](audit_dashboard/data/db_health.json:2)). The `db_health.json:69` citation in Block 54 was correct at its base commit `31b340e`; the file is regenerated hourly by [`audit-dashboard.yml:264`](.github/workflows/audit-dashboard.yml:264) and has been refreshed since, so the number now sits at line 84. Sum of the 10 cohorts' `n` = 22,947 = `total_ghost_rows`.
- **Consequence.** If `bt_backtest_trades` has grown since 18:43Z, the true count is ≥ 22,947; independently, the per-class `LIMIT 500000` sample and the top-10 cohort cap mean the snapshot understates. Deletions since would push the other way. The net error direction is unquantified and its magnitude unknown; what is unaffected is *where* ghosts go, which is what the verdict rests on.

### Amended bottom line

Unchanged: ghosts are display-only or excluded from aggregates, and the forward/walk-forward results are not a ghost-row artifact. Added: the `edge_extractor` output is provably untracked, unscheduled and unread by anything that gates (its Markdown is a human-facing hazard only); the `cot_lag_corrector` gate's intersection with the ghost cohorts is empty on strategy and asset class; and 22,947 is a timestamped snapshot whose error direction is unquantified.
