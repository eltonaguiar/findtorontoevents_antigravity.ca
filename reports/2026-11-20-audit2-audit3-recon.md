# /audit2 and /audit3 — Scoped Recon

Seat: `subq-savant-1.4` · 2026-11-20 · read-and-report only. No code changed, nothing committed, no trading/scanner script run.

Every claim about the code below comes from a file I actually read in this session. Where I read only part of a file, I say so. Where I could not determine something, it is listed at the end rather than guessed.

---

## PART A — COMS check and status update

**1. Bus check (no replies).**

I ran `/home/eaguiar2015/AGENT_FOLDERFRAMEWORK/COMMUNICATION/coms check --agent subq-savant-1.4 --wait 3`. The inbox returned ~96 messages (10.1 KB). I filtered that output for `subq`, `audit2`, `audit3`, `schema drift`, `backtest import`, `bt_backtest_runs`, `status vocabulary`:

> No matches found for the search pattern.

**Nobody replied to my three threads.** The traffic on the bus is other agents' work (copilot-cli-deepseek-flash, buffy, opencode, moneyresearch) on the audit3 ledger, cost-gate arithmetic, the DSR annualisation defect, and the paper pilot. I am not claiming any of it as a response to my notes:

- `notes/subq-collaboration-standard-20261120` — no reply
- `notes/subq-schema-drift-20261120` — no reply
- `questions/subq-audit2-audit3-enhancement-20261120` — no reply

**2. Substantive replies.** None, so there is nothing to summarise or triage as actionable vs acknowledging. One adjacent item is worth flagging because it is relevant to my audit3 questions even though it was not addressed to me: a message from `copilot-cli-deepseek-flash` states that several gates in this repo are advisory (`continue-on-error`), so no CI gate can actually fail a build today. That matches what I read in the workflow myself — see Part B, gate column.

**3. Status update — POSTED.**

Sent to `status/subq-20261120` (my own topic, retained). The client confirmed:

```
sent status/subq-20261120 (qos1, retained — a later COMS check will receive it)
```

Content: schema review done (bt_backtest_runs frozen, bt_backtest_trades row-count divergence, mixed `trading_picks.status` vocabulary), three threads opened with no replies yet, next step per-class planning, pointer to this report.

**4. Retain discipline.** I retained only over `status/subq-20261120`. I know from the skill file (`/home/eaguiar2015/.agents/skills/coms-messaging/SKILL.md`, "Delivery semantics") that retain is last-writer-wins per topic and plain `send` is live-only and discarded if nobody is subscribed — so "posted" is all I can honestly claim. I cannot see subscribers and I am not claiming delivery.

---

## PART B — What /audit2 and /audit3 actually run

### B.1 `/audit2/` — the candidate & methodology library

**Entry point.** There is **no Python generator for `audit2.html`**. It is a hand-authored static page: [`audit_dashboard/audit2.html`](audit_dashboard/audit2.html:1) (115 lines) plus [`audit_dashboard/audit2.js`](audit_dashboard/audit2.js:1) (204 lines). What runs in CI is the sidecar build and the FTP upload, both inside [`audit3-ledger.yml`](.github/workflows/audit3-ledger.yml:180):

```yaml
180 | - name: Build audit2 pods sidecar
181 |   run: python3 tools/build_audit2_pods.py
183 | - name: Build audit2 forward summary
184 |   run: python3 tools/audit2_forward_summary.py
```

and the deploy at [`audit3-ledger.yml`](.github/workflows/audit3-ledger.yml:283):

```yaml
283 | for local, remote in [
284 |     ("audit_dashboard/audit2.html", "index.html"),
285 |     ("audit_dashboard/audit2.js", "audit2.js"),
286 |     ("audit_dashboard/data/audit2_forward.json", "audit2_forward.json"),
287 |     ("audit_dashboard/data/audit2_pods.json", "audit2_pods.json"),
288 | ]:
```

Note that `audit2.html` also appears in the per-site page lists of the main dashboard workflow ([`audit-dashboard.yml`](.github/workflows/audit-dashboard.yml:1286)), so it is deployed from two workflows.

**Inputs.**
- `audit3_ledger.json` — fetched client-side, tried at four paths in order: [`audit2.js`](audit_dashboard/audit2.js:138) (`["audit3_ledger.json", "../audit3/audit3_ledger.json", "../audit/data/audit3_ledger.json", "data/audit3_ledger.json"]`). The page's footer states this plainly: "Every live number on this page comes from `audit3_ledger.json`" ([`audit2.html`](audit_dashboard/audit2.html:112)).
- `audit2_forward.json` — fetched at [`audit2.js`](audit_dashboard/audit2.js:155).
- `audit2_pods.json` — uploaded by the workflow ([`audit3-ledger.yml`](.github/workflows/audit3-ledger.yml:287)), but the pod cards I read are rendered from a **hardcoded `PODS` literal** at [`audit2.js`](audit_dashboard/audit2.js:6) (6 pods, lines 6–25), not from that file. I read only lines 1–160 of `audit2.js`, so I cannot say whether lines 161–204 consume `audit2_pods.json`.

So audit2 is **derivative of audit3**: it does not compute anything itself, it renders audit3's ledger plus two sidecars.

**Sections rendered** ([`audit2.html`](audit_dashboard/audit2.html:46) onward):

| Section | Proves or displays? |
|---|---|
| Doctrine (blockquotes) | Displays — prose |
| Verdicts — per asset class table ([`:57`](audit_dashboard/audit2.html:57)) | **Proves** — carries verdict, n, net expectancy, net CI, 2× cost OK, DSR, required_n from the ledger |
| Candidate & observe pods ([`:69`](audit_dashboard/audit2.html:69)) | Displays — static registry with gates written as prose |
| Forward evidence clock ([`:75`](audit_dashboard/audit2.html:75)) | **Proves** — per-hypothesis forward rows vs a promotion condition |
| Trial budget & benchmarks ([`:83`](audit_dashboard/audit2.html:83)) | Displays counts; the benchmark table is a mapping |
| Measures library ([`:92`](audit_dashboard/audit2.html:92)) | Displays — definitions |
| Traps / graveyard ([`:97`](audit_dashboard/audit2.html:97)) | Displays — curated list |
| Retired with reason ([`:102`](audit_dashboard/audit2.html:102)) | Displays — curated list |
| Provenance & freshness ([`:107`](audit_dashboard/audit2.html:107)) | Displays — generator version, input sha, git sha; warns if the source path is `/tmp` ([`audit2.js`](audit_dashboard/audit2.js:129)) |

Only two of nine sections can fail: the class-verdict table and the forward clock. The rest is documentation. That is not a criticism — audit2 is explicitly the "methodology library" half ([`audit2.html`](audit_dashboard/audit2.html:41)).

### B.2 `/audit3/` — the quant kill tribunal

**Entry point.** [`audit3-ledger.yml`](.github/workflows/audit3-ledger.yml:200):

```yaml
200 | python3 -m alpha_engine.audit3_tribunal \
201 |   --picks /tmp/audit3/dashboard_data.json \
202 |   --out audit_dashboard/data/audit3_ledger.json $alpha_arg $history_arg
```

Cron: `23 */6 * * *` ([`audit3-ledger.yml`](.github/workflows/audit3-ledger.yml:18)) — 6-hourly, no push trigger, own concurrency group ([`:24`](.github/workflows/audit3-ledger.yml:24)). The module's own docstring declares the same invocation ([`alpha_engine/audit3_tribunal.py`](alpha_engine/audit3_tribunal.py:68)).

Three modules, three jobs:

| Module | Role | Regenerated by |
|---|---|---|
| [`audit3_tribunal.py`](alpha_engine/audit3_tribunal.py:1) | Computes every verdict; emits `audit3_ledger.json` | `audit3-ledger.yml:200` |
| [`audit3_selection_alpha.py`](alpha_engine/audit3_selection_alpha.py:1) | M1b — pick net return minus direction-adjusted buy-and-hold; G8 | `audit3-ledger.yml:165` (`continue-on-error: true`, `:151`) |
| [`audit3_edge_hunt.py`](alpha_engine/audit3_edge_hunt.py:1) | Beta accounting, mirror test, point-in-time replay, pre-registered battery | **Nothing in CI.** I grepped `.github/workflows/` for `audit3_edge_hunt` / `edge_hunt` — zero hits. Its only documented invocation is manual, in its own docstring ([`audit3_edge_hunt.py`](alpha_engine/audit3_edge_hunt.py:42)) |

**Inputs.**
- `https://findtorontoevents.ca/audit/data/dashboard_data.json` — fetched live over HTTP ([`audit3-ledger.yml`](.github/workflows/audit3-ledger.yml:41)). It is produced by `python -m audit_trail.dashboard_generator` ([`audit-dashboard.yml`](.github/workflows/audit-dashboard.yml:647)).
- `resolved_closed_picks_net.json` — the canonical resolved view, fetched optionally ([`audit3-ledger.yml`](.github/workflows/audit3-ledger.yml:65)); when it is absent the tribunal falls back to the payload slice and stamps `mode` rather than pretending the denominators match (module docstring at [`resolved_closed_view.py`](alpha_engine/resolved_closed_view.py:25), and audit2 surfaces that warning at [`audit2.js`](audit_dashboard/audit2.js:107)).
- Price tables, for selection alpha: `crypto_ohlcv`, `equity_daily_ohlcv`, `etf_daily_ohlcv`, `fx_prices`, `futures_daily_ohlcv` — mapped per class at [`audit3_selection_alpha.py`](alpha_engine/audit3_selection_alpha.py:52), with freshness tolerances at [`audit3_selection_alpha.py`](alpha_engine/audit3_selection_alpha.py:68).
- `reports/forward_observations.jsonl` — the forward clock ([`audit3.html`](audit_dashboard/audit3.html:246)).
- `audit3_verdict_history.json` — the repeated-looks / persistence gate ([`audit3-ledger.yml`](.github/workflows/audit3-ledger.yml:194)).

**Are the flagged-stale sources in the path?**

- **`bt_backtest_runs` (frozen 2026-03-06)** — yes in the repo, but *not* in audit3's verdict path. The only query is in the main dashboard generator: [`dashboard_generator.py`](audit_trail/dashboard_generator.py:11354) — `SELECT strategy, total_trades, wins, losses, win_rate, total_return, sharpe FROM bt_backtest_runs WHERE total_trades >= 5`. It feeds /audit's per-strategy metrics table, not audit3. audit3 consumes `dashboard_data.json` but only its `picks.recent_closed` rows ([`audit3-ledger.yml`](.github/workflows/audit3-ledger.yml:56)), so the frozen table reaches audit3 only if it contaminates the picks themselves, which this query does not do. Neither `audit-dashboard.yml` nor `audit3-ledger.yml` mentions `bt_backtest` at all in my grep.
- **`bt_backtest_trades` (34.6M vs 27.2M)** — same answer: it is read by [`tools/edge_extractor.py`](tools/edge_extractor.py:46), [`tools/cross_db_consistency.py`](tools/cross_db_consistency.py:107), [`tools/db_freshness_check.py`](tools/db_freshness_check.py:384) and [`tools/db_health_check.py`](tools/db_health_check.py:128), none of which is an audit2/audit3 generator. It does not determine any verdict on either page.
- **`trading_picks.status` (mixed vocabulary)** — **this one does bite, directly.** The tribunal's closed-row filter is [`audit3_tribunal.py`](alpha_engine/audit3_tribunal.py:537):

  ```python
  537 | status = str(r.get("status") or "").upper()
  538 | if status in ("OPEN", "PENDING", ""):
  539 |     drop["not_closed"] = drop.get("not_closed", 0) + 1
  ```

  This is a **deny-list of three values**, not an allow-list. Any other spelling — `CANCELLED`, `CANCELED`, `NO_FILL`, `INVALID_ENTRY`, `EXPIRED` — is treated as *closed* provided the row has a numeric `pnl_pct` ([`:533`](alpha_engine/audit3_tribunal.py:533)). Meanwhile [`resolved_closed_view.py`](alpha_engine/resolved_closed_view.py:93) carries a `_NON_PERFORMANCE_EXITS` set that treats exactly those spellings as non-performance. So the two components disagree about what a closed row is, and with a mixed status vocabulary the tribunal can score rows the canonical view excludes. That is a concrete consequence of the schema drift, not a hypothetical.

**Sections rendered** — ten tabs at [`audit3.html`](audit_dashboard/audit3.html:110):

| Tab | Line | Proves or displays? |
|---|---|---|
| Overview | [`122`](audit_dashboard/audit3.html:122) | **Proves** — per-class verdict table (`classTbl`, `:124`), selection-alpha coverage table (`alphaCovTbl`, `:126`), verdict legend, un-scored coverage statement, promotion pipeline |
| Kill Tribunal | [`141`](audit_dashboard/audit3.html:141) | **Proves** — kill list, each with a stated criterion set ([`audit3_tribunal.py`](alpha_engine/audit3_tribunal.py:2092)) |
| Strategy Cells | [`148`](audit_dashboard/audit3.html:148) | **Proves** — strategy × direction cells, filterable by class/verdict/min-n |
| Symbols | [`161`](audit_dashboard/audit3.html:161) | **Proves** — symbol × direction cells, n ≥ 20 |
| Sections × Class | [`173`](audit_dashboard/audit3.html:173) | **Displays a proxy** — the page says so itself: section membership is rebuilt from row fields, "a proxy for the live gate — not the gate's own decision" ([`:177`](audit_dashboard/audit3.html:177)) |
| Source Families | [`187`](audit_dashboard/audit3.html:187) | Displays — name-based bucketing, and the page admits it cannot judge an individual trader ([`:190`](audit_dashboard/audit3.html:190)) |
| Evidence Registry | [`198`](audit_dashboard/audit3.html:198) | **Displays only, by design** — "Prior backtests are evidence, not verdicts… nothing on this tab can promote a strategy" ([`:215`](audit_dashboard/audit3.html:215)) |
| Hypotheses | [`225`](audit_dashboard/audit3.html:225) | **Proves** — status enum, open/registered table |
| Forward Evidence | [`235`](audit_dashboard/audit3.html:235) | **Proves** — "the only rows that can promote a pod" ([`:237`](audit_dashboard/audit3.html:237)) |
| Method & Limits | [`254`](audit_dashboard/audit3.html:254) | Displays — declared gates G0–G9 ([`audit3_tribunal.py`](alpha_engine/audit3_tribunal.py:16)) and provenance |

The nine gates G0–G9 are declared in the docstring ([`audit3_tribunal.py`](alpha_engine/audit3_tribunal.py:18)) and are enforced in code — sample floor, one-sided binomial, bootstrap CI, BH FDR, DSR, split-half, concentration, cost realism, selection alpha, 2× cost stress. Whether they can *fail a build* is separate: the selection-alpha step is `continue-on-error: true` ([`audit3-ledger.yml`](.github/workflows/audit3-ledger.yml:151)), and the price-freshness SLA is the one place I saw an explicit `exit 1` for a gate ([`audit3-ledger.yml`](.github/workflows/audit3-ledger.yml:142)).

**Asset-class handling today — it already exists, in three places.**

1. Per-class verdict table on the overview ([`audit3.html`](audit_dashboard/audit3.html:123)).
2. `classes`, `segments`, `cells`, `symbols` in the ledger payload ([`audit3_tribunal.py`](alpha_engine/audit3_tribunal.py:2086)).
3. Section × asset class cross-tab ([`audit3.html`](audit_dashboard/audit3.html:173)).

The field is `asset_class` on the closed row, canonicalised through [`symbol_identity`](alpha_engine/audit3_tribunal.py:89). And there **is** already a canonical per-class rollup worth reusing: [`resolved_closed_view.py`](alpha_engine/resolved_closed_view.py:270) `class_rollup(rows)` returns per class `n`, `wins`, `losses`, `flat`, `win_rate_pct`, `profit_factor`, `mean_gross_pct`, `mean_net_pct`, `mean_cost_bps` — keyed off the shared cost model at [`resolved_closed_view.py`](alpha_engine/resolved_closed_view.py:48) (`CRYPTO 9.97`, `FOREX 2.0`, `FUTURES/COMMODITY 15.0` bps). It is consumed by the canonical view assembly at [`resolved_closed_view.py`](alpha_engine/resolved_closed_view.py:258) (`"classes": class_rollup(rows)`).

**Where a per-asset-class strategy panel would slot in.**

- **audit2** — additive. New `<section>` in [`audit2.html`](audit_dashboard/audit2.html:67), after the Verdicts block; render it in `renderLedger()` ([`audit2.js`](audit_dashboard/audit2.js:99)), reading `d.classes` (already there) joined against `d.cells` (already in the payload at [`audit3_tribunal.py`](alpha_engine/audit3_tribunal.py:2088)). No restructuring: the payload already carries both.
- **audit3** — additive. New tab button at [`audit3.html`](audit_dashboard/audit3.html:114) (next to "Sections × Class"), a `<section>` after [`audit3.html`](audit_dashboard/audit3.html:185), and a payload key beside [`audit3_tribunal.py`](alpha_engine/audit3_tribunal.py:2086) — grouped from the existing `cells` list by `asset_class`, reusing `class_rollup` for the per-class totals. Nothing in the existing structure has to move.

---

## PART C — Reality-check: "enhancing with some strategies per asset class"

**These surfaces do not generate signals.** audit3's own banner says it is a "quant kill tribunal" ([`audit3.html`](audit_dashboard/audit3.html:96)) and its verdict enum is PROVEN_T2 / CANDIDATE / WEAK / KILL / INSUFFICIENT_N ([`audit3_tribunal.py`](alpha_engine/audit3_tribunal.py:42)). audit2 is described as "the positive side of /audit3's kill tribunal: what is worth forward-testing, and the measurement kit to judge it" ([`audit2.html`](audit_dashboard/audit2.html:41)).

**So which reading is feasible?**

**(a) A per-class verdict table — feasible, and partly already built.** audit2's verdict block is exactly that shape today: `Asset class | Verdict | n | Net expectancy/trade | Net 95% CI | 2× cost OK | DSR | required_n` ([`audit2.html`](audit_dashboard/audit2.html:62)), rendered from `d.classes` at [`audit2.js`](audit_dashboard/audit2.js:110). Extending it to *strategies within a class* is a join of two fields the ledger already emits — `classes` and `cells` ([`audit3_tribunal.py`](alpha_engine/audit3_tribunal.py:2086)) — with per-cell n and CI already computed per cell (G0/G2). The n and CI columns are the honest part: many cells will be `INSUFFICIENT_N` at n under 20 ([`audit3_tribunal.py`](alpha_engine/audit3_tribunal.py:98)), and a panel that shows them as rows is more truthful than one that hides them.

**(b) A per-class signal/strategy feed (new picks) — not supported, and it would damage the audit.** No generator on either page emits picks; audit3 only reads a closed-pick ledger and writes a JSON sidecar ([`audit3_tribunal.py`](alpha_engine/audit3_tribunal.py:12)). Putting a live feed on the judge would make the page both the thing and the judge of the thing.

**That independence concern is real, and the repo already states it.** The Evidence Registry tab's own text: "Prior backtests are **evidence, not verdicts**… nothing on this tab can promote a strategy" ([`audit3.html`](audit_dashboard/audit3.html:215)). The tribunal's doctrine is "innocent until proven guilty" and "nothing is removed from the closed-pick ledger by this module" ([`audit3_tribunal.py`](alpha_engine/audit3_tribunal.py:48)) — that stance only means something if the page has no stake in which strategies get emitted. A feed would give it one.

**Does `audit_dashboard/` already have a per-class section?** In `template.html` (the /audit page, not audit2/audit3) there are 73 `asset_class` references — per-class spans populated from `performance.asset_class_health` ([`template.html`](audit_dashboard/template.html:1125)), a per-class OOS table ([`:1288`](audit_dashboard/template.html:1288)), a "SUPREME EDGE … per asset class" block ([`:1560`](audit_dashboard/template.html:1560)), and an explicit two-figures-per-class warning — headline PF vs recent-window PF differ (CRYPTO 1.25 vs 0.89) ([`:1282`](audit_dashboard/template.html:1282)). `dashboard_enhancements.js` has 5 (`:165`, `:641`, `:909`, `:913`, `:978`); `audit3.html` has 13. So per-class is a well-trodden shape on /audit and thin on audit2/audit3 — which is precisely the gap a panel would fill, and precisely why it should reuse `class_rollup` rather than invent a fourth per-class aggregate.

---

## PART D — Backtesting / metrics tracking: is it a viable alternative?

**Is it building on sand?** For anything that reads `bt_backtest_runs` — yes. Its consumers in this repo are real: [`dashboard_generator.py`](audit_trail/dashboard_generator.py:11354) pulls strategy/trades/wins/sharpe from it into the /audit strategy table, and [`temp_crypto_backtests.py`](temp_crypto_backtests.py:10) queries it directly. If it has not advanced since 2026-03-06, then every sharpe and win-rate on that table describes a book that stopped existing eight months ago, and a metrics-tracking layer on top would faithfully track a frozen series. What would have to be fixed first: the write path into `bt_backtest_runs` (whoever runs backtests must be writing rows), and the row-count reconciliation on `bt_backtest_trades` — the 34.6M vs 27.2M divergence is the same class of problem, and ghost rows are a known issue here ([`tools/cleanup_ghost_rows.py`](tools/cleanup_ghost_rows.py:9): "12 cohorts totalling 276,145 ghost rows across bt_backtest_trades"; [`template.html`](audit_dashboard/template.html:913) reports 22,947 still quarantined).

**Where the PBO / WFE / DSR machinery lives, and whether CI runs it:**

| Module | Location | In `.github/workflows/`? |
|---|---|---|
| `cpcv_overfit_detector` | [`tools/cpcv_overfit_detector.py`](tools/cpcv_overfit_detector.py:1) | **No** |
| `run_anti_overfit_audit` | [`tools/run_anti_overfit_audit.py`](tools/run_anti_overfit_audit.py:1) | **No** |
| `wfe` | [`tools/wfe.py`](tools/wfe.py:1) | **No** |
| `probabilistic_sharpe_engine` | [`probabilistic_sharpe_engine.py`](probabilistic_sharpe_engine.py:1) (repo root) | **No** |

I grepped `.github/workflows/` for each name: zero hits for all four. They are runnable but unwired — effectively dead code from CI's point of view. That is consistent with what a peer reported on the bus today: every gate in CI is currently advisory, so even the gates that *are* wired cannot fail a build.

**Verdict: metrics/backend is the better near-term investment than a UI panel — but not on `bt_backtest_runs`.**

Reason, not a hedge: a UI panel renders numbers that already exist and are already aggregated; the marginal information is layout. The metrics layer is where the actual defects are, and they are measurable ones — an audit surface where the reported PBO comes from synthetic peer strategies, or where a DSR was fed an annualised Sharpe where a per-period one belonged, is producing numbers that are wrong rather than merely badly arranged. A panel built on top of those would display them more prominently, which is the opposite of what an audit page is for. The concrete first step is not a new metrics system: it is making one existing gate blocking, and reconciling the denominators (`bt_backtest_trades` row count, `trading_picks.status` vocabulary) so that any metric computed downstream has one meaning. The `status` disagreement in Part B — deny-list at [`audit3_tribunal.py`](alpha_engine/audit3_tribunal.py:537) vs `_NON_PERFORMANCE_EXITS` at [`resolved_closed_view.py`](alpha_engine/resolved_closed_view.py:93) — is a two-file fix that changes what every verdict on /audit3 means.

---

## What I could NOT determine

- Whether `audit2.js` lines 161–204 consume `audit2_pods.json` — I read only lines 1–160, and the pod cards I saw come from a hardcoded literal ([`audit2.js`](audit_dashboard/audit2.js:6)) while the workflow uploads the JSON ([`audit3-ledger.yml`](.github/workflows/audit3-ledger.yml:287)).
- Whether `bt_backtest_runs` is *actually* frozen at 2026-03-06, whether `bt_backtest_trades` really holds 34.6M vs 27.2M, and what the current `trading_picks.status` value distribution is. I took these as given from the task brief — this recon did not query the databases, and I would not report a DB number I had not measured.
- Which of the four validation modules are invoked from anywhere *outside* `.github/workflows/` (cron, manual scripts, other agents) — I only established that no workflow references them.
- Whether any subscriber is registered on `status/subq-20261120`. COMS retain is last-writer-wins per topic and I can only observe that my send printed `sent … (qos1, retained)`; I cannot see the subscriber list.
- The full content of `audit3.html` beyond line 261 (it is 783 lines) and of `audit3_tribunal.py` beyond the ranges I read.
