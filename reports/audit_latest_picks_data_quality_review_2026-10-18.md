# Latest Audit Picks and Data-Quality Review — 2026-10-18

## Scope and evidence

This review examined the public production surfaces between 00:48 and 01:45 UTC on
2026-10-18:

- [`/audit/`](https://findtorontoevents.ca/audit/)
- [`/audit/data/dashboard_data.json`](https://findtorontoevents.ca/audit/data/dashboard_data.json)
- [`/audit/data/money_ready_verdict.json`](https://findtorontoevents.ca/audit/data/money_ready_verdict.json)
- [`/audit/data/pick_summary_stats_14d.json`](https://findtorontoevents.ca/audit/data/pick_summary_stats_14d.json)
- [`/audit/data/pick_summary_stats_48h.json`](https://findtorontoevents.ca/audit/data/pick_summary_stats_48h.json)
- [`/audit/pick_funnel.html`](https://findtorontoevents.ca/audit/pick_funnel.html)
- all 19 destinations in the dashboard's **Links** tab
- the public Alpha Engine and Rapid Fire active-pick feeds
- recent `audit-dashboard.yml` workflow runs

The dashboard payload was generated at `2026-10-18T00:48:56Z`; the recency
sidecars were generated at `00:55:15Z`; the money-ready verdict was generated at
`00:47:37Z`.

The read-only live-DB funnel helper could not authenticate in this shell because
no DB password was present. No database values below were guessed. DB-backed
claims come from the freshly published recency and money-ready sidecars, while
dashboard claims come from the published dashboard payload. Their disagreement
is itself a principal finding.

## Executive verdict

**The dashboard is not trustworthy enough for capital sizing.** The source
emitters are producing new picks, but the active/closed cohorts disagree across
published surfaces, recent terminal rows still claim fabricated `0.00%` returns,
three prominent dashboard links are now broken, and one production JavaScript
file does not parse.

No asset class is money-ready:

- `COMMODITY` is only `WATCH`.
- `CRYPTO`, `EQUITY`, and `FOREX` are `NOT_READY`.
- `ETF`, `FUTURES`, `BOND`, `MEME`, and `PENNY_STOCK` are
  `INSUFFICIENT_DATA`.

The best apparent recent numbers are not promotion evidence. ETF has only five
decisive closes in 48 hours and 15 in the money-ready cohort. FOREX's 48-hour
sidecar PF of 1.46 conflicts with an intrabar-truth PF of 0.611. CRYPTO's
48-hour PF of 1.186 is below Tier 2 and 98.5% of that cohort comes from one
source.

## P0/P1 findings

### P0-1 — Production JavaScript syntax error

The live `/audit/` page raises `Unexpected token ':'`. `node --check` isolated
the failure to the deployed `dashboard_enhancements.js`:

```js
const pfVal = (p.live_pf_net != null) ? htmlEscape(String(p.live_pf_net))
              : (p.live_pf_gross != null ? htmlEscape(String(p.live_pf_gross)) : null)
              : null;
```

The second `: null` is invalid syntax. Any enhancement initialized after that
script is unavailable even though earlier dashboard sections continue to render.

### P0-2 — Three Links-tab destinations regressed from 200 to 404

At approximately 01:13 UTC, all three GitHub Pages destinations returned 200.
After the Pages deployment completed around 01:41 UTC, these returned 404:

- Cross-System Monitor
- Alpha Engine
- QuanEngine Prop Firm Dashboard

This was reproduced with both a browser and `curl`. The route loss happened
during the review, which strongly implicates the latest Pages artifact rather
than old link text.

### P0-3 — Fabricated zero-return terminal rows remain visible

In `dashboard_data.json::picks.recent_closed`, the last 48 hours contain:

| Asset class | Zero-P/L terminal rows | Source | Exit reason |
|---|---:|---|---|
| FOREX | 29 | `signal_validation` / `MeanReversionBB` | `TIME_EXIT` |
| EQUITY | 9 | `stocksunify2` | `TIME_EXIT` |

All 38 have `exit_price == entry_price` and are displayed as `0.00%`. That is
not evidence of a flat market move; it is the historical no-live-price
placeholder signature.

The resolver now contains a 2026-10-17 heal-on-load rule that converts this
signature to `pnl_pct=null`, but the production payload proves that DB/dashboard
paths still bypass or fail to apply that repair. The dashboard's historical
noise filter also omits plain `CLOSED` from its terminal-status set, allowing
`status=CLOSED`, `exit_reason=TIME_EXIT`, `pnl_pct=0` rows through.

The recency rollup excludes these rows from decisive WR/PF, which is better than
counting them as losses or wins, but its per-pick table still presents `0.00%`
instead of **UNRESOLVED / NO MARK**.

### P0-4 — Active and closed cohorts disagree by surface

The main payload has 12 curated active picks and 4,017 `active_raw` rows. The
DB-backed 48-hour recency sidecar reports `n_active=0` for every class.

For closed rows in the same nominal 48-hour window:

| Class | Main payload recent closes | DB recency sidecar closes |
|---|---:|---:|
| CRYPTO | 154 | 133 |
| FOREX | 36 | 141 |
| EQUITY | 17 | 44 |
| ETF | 10 | 5 |
| FUTURES | 1 | 42 |
| BOND | 0 | 1 |
| COMMODITY | 2 | absent as a class |

The sidecar assigns recent metal/energy rows to `FUTURES`; the main payload calls
similar rows `COMMODITY`. It also says the decisive cohorts are 98.5–100%
`AlphaEngine`, while the main payload attributes the zero-P/L FOREX rows to
`signal_validation` and EQUITY rows to `stocksunify2`.

This is not a harmless presentation difference. It prevents a reviewer from
knowing which rows produced the reported WR/PF.

### P1-1 — `active_raw` is mostly stale history but is exposed as picks

`active_raw` is intentionally captured before stale expiry and gate filtering.
That makes it useful diagnostically, but dangerous if presented as an active
pick list.

| Class | Raw rows | Median age | At least 24h old | At least 72h old |
|---|---:|---:|---:|---:|
| CRYPTO | 3,490 | 1,464.8h | 3,294 | 3,165 |
| FOREX | 221 | 3,997.8h | 158 | 158 |
| EQUITY | 165 | 106.6h | 119 | 86 |
| COMMODITY | 63 | 1.7h | 19 | 16 |
| ETF | 44 | 6.4h | 21 | 11 |
| FUTURES | 21 | 62.1h | 14 | 10 |
| BOND | 11 | 34.6h | 10 | 0 |

The maximum raw ages exceed 4,700 hours in several classes and 5,700 hours in
CRYPTO/FOREX. Rename the control to **Raw emitted pool (includes expired and
rejected)** and never aggregate it as active exposure.

### P1-2 — Metric families remain irreconcilable

Examples from the same current publication:

- CRYPTO `asset_class_health`: `n=18,752`, WR 46.43%, PF 0.288.
- CRYPTO money-ready intrabar truth: `n=3,497`, WR 35.46%, PF 0.881.
- CRYPTO 14-day recency: `n=2,066`, WR 43.61%, PF 1.023.
- CRYPTO 48-hour recency: `n=131`, WR 47.33%, PF 1.186.

Each number can describe a different cohort, but the UI does not provide a
row-level cohort identifier or reconciliation count. Similar divergence appears
in FOREX, where the 48-hour PF is 1.46 but the sizing cohort PF is 0.611.

### P1-3 — Fresh deployment timestamps hide stale data

- `db_freshness.json` was last generated on 2026-05-23.
- `hourly_asset_class_24h_report.json` was last generated on 2026-04-11.
- `integrity_report.json` was last generated on 2026-03-11.
- `picks_now.json` was generated at 18:05 UTC, about 6h44m before the main
  dashboard snapshot.
- The Updates page was freshly deployed during this review but its rendered
  incident content said `Refreshed: 2026-10-17 00:39 EDT`, about 21 hours old.

HTTP `Last-Modified` is therefore not a valid proxy for data freshness.

### P1-4 — Workflow cancellation/queue pressure is still producing stale surfaces

Recent `audit-dashboard.yml` runs showed:

- one run pending from 01:32 UTC;
- the 00:58 run cancelled at 01:32;
- the 23:17 run still in progress;
- the latest successful run took from 22:18 to 00:10.

The job duration exceeds its schedule interval. Cancellation and overlap can
deploy mixed-generation HTML, JSON, and scripts, which is consistent with the
observed timestamp and JavaScript mismatches.

## Latest active picks

The curated Active surface contained 12 picks:

| Class | Count | Latest examples | Review |
|---|---:|---|---|
| CRYPTO | 3 | BTCUSDT SHORT, XRPUSDT SHORT, SOLUSDT SHORT | Fresh (~0.6h), all from `pm_kalshi_signals`; current equals entry, so 0% is normal at opening but source concentration is total. |
| EQUITY | 2 | SPY SHORT from `regime_terminal`; SPY SHORT from `alpha_engine` | Fresh (1.7–2.1h) but duplicated symbol/direction exposure should be concentration-capped. |
| COMMODITY | 2 | PA=F SHORT, GC=F SHORT | Fresh (0.1–0.6h); no reliable class-level edge yet. |
| FOREX | 2 | EURGBP=X LONG, GBPUSD=X SHORT | Fresh; policy-clean and intrabar performance remain below readiness. |
| ETF | 2 | TQQQ LONG, XLV LONG | About 31h old, with -1.62% and +0.01% unrealized P/L; verify hold-window policy and price freshness. |
| FUTURES | 1 | NQ=F LONG | Fresh; class remains insufficient and its closed NQ row has an implausible historical entry-price signature. |
| BOND | 0 | — | No active evidence. |

The five very fresh picks showing `0%` because current price equals entry are not
the same problem as a closed time-exit at `0%`. Active rows should say
**unchanged since entry**; terminal rows without a measured exit should say
**unresolved**.

## Latest closed picks and performance

### DB-backed 48-hour rollup

| Class | Closed | Decisive | WR | PF | Mean P/L | Verdict |
|---|---:|---:|---:|---:|---:|---|
| CRYPTO | 133 | 131 | 47.33% | 1.186 | +0.2216% | Below Tier 2; 7 duplicate groups and 98% single-source concentration. |
| FOREX | 141 | 141 | 36.88% | 1.460 | +0.1188% | Short-window PF conflicts with intrabar-truth PF 0.611; not ready. |
| FUTURES | 42 | 42 | 47.62% | 0.398 | -0.5722% | Losing. |
| EQUITY | 44 | 44 | 40.91% | 1.083 | +0.0790% | Weak rebound; 14-day PF is only 0.309. |
| ETF | 5 | 5 | low-n raw 40.0% | 0.377 | -0.9065% | Insufficient and losing. |
| BOND | 1 | 1 | low-n raw 0% | 0.000 | -0.4087% | No evidence. |
| COMMODITY | — | — | — | — | — | Taxonomy gap: recent commodity contracts are reported under FUTURES. |

### Latest rows worth manual review

- **CRYPTO:** DOT-USD SHORT closed +3.00%; OPUSDT LONG closed -2.11%;
  JUPUSDT LONG closed -1.38%. These are plausible TP/SL outcomes, but they do
  not overcome the weak policy-clean cohort.
- **FOREX:** recent USDCAD, GBPUSD, and EURUSD time exits have non-zero
  mark-to-market returns and are preferable to placeholder closes. Separately,
  29 `signal_validation/MeanReversionBB` time exits still show fabricated 0%.
- **EQUITY:** V, MA, JPM, and six other recent `stocksunify2` time exits show
  entry equal to exit and 0%. Treat them as unresolved, not flat trades.
- **COMMODITY:** CC=F +1.4064% and NG=F -1.9996% are plausible outcomes.
- **ETF:** the latest SPY time exit is -1.96%; the class has no adequate recent
  sample despite a strong-looking 15-row money-ready cohort.
- **FUTURES:** HG=F +0.6507% is plausible. The historical NQ=F row reports an
  entry of `0.0852` and exit `0.09793101` for an index future, indicating symbol
  or field contamination even though its computed +14.94% is arithmetically
  consistent.
- **BOND:** the latest row is from 2026-10-01; no 48-hour evidence exists in the
  main payload.

## Money-ready assessment

| Class | Sizing source | n | WR | PF | Current status |
|---|---|---:|---:|---:|---|
| CRYPTO | intrabar truth | 3,497 | 35.46% | 0.881 | NOT_READY |
| FOREX | intrabar truth | 547 | 30.71% | 0.611 | NOT_READY |
| EQUITY | intrabar truth | 229 | 55.90% | 0.837 | NOT_READY; high WR but losses outweigh wins |
| COMMODITY | intrabar truth | 227 | 40.09% | 1.028 | WATCH; approximately break-even before stronger cost proof |
| FUTURES | intrabar truth | 47 | 40.43% | 1.040 | INSUFFICIENT_DATA |
| ETF | insufficient intrabar | 15 | 73.33% | 1.825 | INSUFFICIENT_DATA |
| BOND | insufficient intrabar | 0 | 0% | 0 | INSUFFICIENT_DATA |

Do not loosen gates to manufacture a passing class. ETF is the best candidate
for further forward accumulation, not promotion. Apply the repository's
mutate-before-kill process to weak strategy families and require independent
forward cohorts after each mutation.

## Links-tab review

| Link | HTTP/render result | Data-quality note |
|---|---|---|
| Cross-System Monitor | **404** | Broke after the latest GitHub Pages deployment. |
| Rapid Fire (NOW) | 200; rendered | Scan showed zero current signals; raw active feed is `[]`. |
| Pump Watch | 200; rendered | Large populated tables; verify page-weight limits separately. |
| Audit Trail | 200 shell; data did not load | Still showed `Loading audit data` / `Prices: waiting for update`. |
| Fund-of-Funds | 200; rendered | Main table populated; displayed data about 52 minutes old. |
| Picks Now | 200; rendered | 25 picks, but source JSON was about 6h44m older than the main dashboard snapshot. |
| Edge Validation Roadmap | 200 | Static page last modified 2026-06-09; its “no current edge” message remains directionally correct. |
| Alpha Engine | **404** | Broke after the latest GitHub Pages deployment. |
| KIMI Rise of the Claw | 200; rendered | Populated live/back-test tables. |
| Algorithm Competition | 200 shell; data did not load | `LAST UPDATE -`, persistent `Loading...`, no table rows. |
| All Dashboards | 200; rendered | Directory tables populated. |
| HyroTrader | 200; rendered | Multiple populated tables; still research-only. |
| QuanEngine | **404** | Broke after the latest GitHub Pages deployment. |
| Wave 20 source | 200 | GitHub source link works. |
| Backtest source/results | 200 | GitHub source link works. |
| Updates & Changelog | 200 | Incident content about 21h old despite a fresh deploy timestamp. |
| Alpha Engine raw JSON | 200 | 18 active rows; latest source timestamp 01:17:57 UTC. |
| Rapid Fire raw JSON | 200 | Valid JSON but empty array. |
| GitHub Actions | 200 | Link works; audit workflow health is degraded by long/cancelled runs. |

## Did the system “would have made new picks” path work?

### Current result: partial pass

**EMIT stage: PASS.** The public Alpha Engine feed contained 18 active picks
across CRYPTO, FUTURES, COMMODITY, ETF, FOREX, and STOCKS. Its newest rows were
timestamped `01:17:57Z`, including SOLUSDT LONG, BNBUSDT LONG, XRPUSDT SHORT,
and ETHUSDT SHORT. This proves source systems can still generate new candidates.

**DASHBOARD active stage: PASS with expected snapshot lag.** The 00:48 dashboard
snapshot contained 12 gate-filtered active picks, with entries as recent as
00:43. Picks emitted at 01:17 occurred after that snapshot and should appear in
the next successful build.

**INGEST/LEDGER stage: FAIL or unproven.** The DB-backed 00:55 recency sidecar
reported zero active picks in every class. That contradicts both the source feed
and dashboard active list. Until the current feed IDs are found in
`at_raw_picks` with matching timestamps and gate traces, the end-to-end claim is
not validated.

**Rapid Fire stage: NO-SIGNAL, not a failure.** The scanner page and raw feed
both reported zero current signals. A no-signal market cannot prove that its
emission code would write a qualifying pick, so a deterministic replay fixture
is required.

## Fix plan

### Phase 0 — Stop further trust damage

1. Fix the extra ternary branch in live `dashboard_enhancements.js`.
2. Restore the three missing GitHub Pages directories from the Pages artifact.
3. Prevent money-ready promotion and real-capital sizing while any P0 data
   contract check is red.
4. Add a visible dashboard banner when any required script fails to parse or a
   critical linked surface returns non-200.

### Phase 1 — Make outcomes honest

1. Create one canonical `normalize_terminal_outcome()` used by resolver,
   recency builder, dashboard generator, and DB writer.
2. For `TIME_EXIT`/`EXPIRED` rows with no observed market price:
   - store `exit_price=NULL`;
   - store `pnl_pct=NULL`;
   - set `resolution_method='UNRESOLVED_NO_MARK'`;
   - never label the row WON/LOST.
3. Backfill the identified FOREX and EQUITY zero cohorts and all historical rows
   with the same signature.
4. Display `UNRESOLVED` rather than `0.00%`.
5. Recompute WR/PF only from decisive, price-observed rows.

Acceptance criteria:

- zero rows with terminal status, `exit_price=entry_price`, and `pnl_pct=0`
  unless an explicit independently observed flat price is attached;
- dashboard, 48-hour sidecar, and money-ready cohort agree on decisive row IDs;
- a row excluded from PF/WR cannot still appear as a measured 0% outcome.

### Phase 2 — Reconcile emit, ingest, gate, and display

1. Give every emitted pick a deterministic ID built from source, strategy,
   symbol, direction, and signal timestamp.
2. Upsert every source pick into `at_raw_picks` before dashboard rendering.
3. Emit one audit row per gate decision and expose:
   `emitted_at`, `ingested_at`, `gate_evaluated_at`, `displayed_at`.
4. Add an ingestion-lag SLO: 99% of source picks present in `at_raw_picks`
   within 15 minutes.
5. Rename `active_raw` in the UI to state that it contains expired and rejected
   history.

Acceptance criteria:

- the current Alpha Engine feed ID set is a subset of the ledger ID set;
- source, ledger, and dashboard counts reconcile with explicit reject/expiry
  counts;
- `n_active` differs between surfaces only when a documented gate explains it.

### Phase 3 — Canonicalize taxonomy and metrics

1. Define a single enum and alias map:
   `STOCKS -> EQUITY`, metal/energy contracts consistently to either
   `COMMODITY` or `FUTURES`, and no `UNKNOWN` for known sources.
2. Carry `cohort_id`, `resolver_version`, `resolution_method`, and
   `source_system` into every aggregate.
3. Publish one reconciliation table from raw rows to policy-clean rows to
   intrabar-truth rows.
4. Deprecate or regenerate the March–May freshness/integrity sidecars.

Acceptance criteria:

- no class disappears between the 48-hour and 14-day views;
- the sum of per-class rows equals the global total;
- every displayed PF/WR links to a row-ID manifest or reproducible cohort hash;
- source concentration is computed from non-UNKNOWN normalized sources.

### Phase 4 — Get better picks without relaxing evidence standards

1. Keep all classes paper-only.
2. Prioritize ETF forward accumulation, but require at least 100 clean,
   independent, post-cost closes before promotion.
3. For CRYPTO, dedupe same signal-time groups and cap single-source exposure
   before evaluating the apparent 48-hour improvement.
4. For EQUITY and FOREX, mutate entry timing, direction, and TP/SL separately;
   do not combine changes until each axis has an independent shadow cohort.
5. For COMMODITY/FUTURES, repair taxonomy before tuning strategy logic.
6. Record spread, fees, slippage, and first-touch intrabar resolution for every
   candidate.

Promotion criteria remain at least Tier 2: PF > 1.5, WR > 50%, MDD < 20%, plus
sample-size, concentration, DSR/PBO/SPA, recency, and forward-only checks.

## Validation plan

### Automated data-contract tests

1. Resolver fixture: no live price at max hold must produce null P/L and
   `UNRESOLVED_NO_MARK`.
2. Resolver fixture: observed time-exit price must produce direction-correct
   non-zero P/L.
3. Cohort fixture: the same row IDs must produce identical WR/PF in dashboard
   and recency builders.
4. Taxonomy fixture: GC=F/HG=F/NG=F map consistently; SPY/TQQQ remain ETF;
   stocks map to EQUITY.
5. Script gate: `node --check` every deployed JavaScript file.
6. Browser gate: zero `pageerror`, no persistent Loading shell, and meaningful
   table rows on every linked dashboard.
7. Link gate: all 19 Links-tab destinations must return 200 after the final
   deployment artifact is live.

### Deterministic “would have made new picks” replay

Build a write-disabled replay command that accepts an `--as-of` timestamp and a
frozen OHLC/input fixture:

1. Replay a known historical bar where at least one strategy must emit.
2. Assert the exact candidate ID, symbol, direction, entry, TP, SL, source, and
   signal timestamp.
3. Run active and smart gates with only data available at `--as-of`; assert the
   expected PASS/REJECT reasons.
4. Dry-run the ledger upsert and assert exactly one new row would be written.
5. Replay the same fixture again and assert idempotency: zero additional rows.
6. Replay a negative fixture and assert zero candidates.
7. Compare replay output to the next live cycle by deterministic ID.

The test passes only when the same pick is visible through:

`source emission -> at_raw_picks -> gate trace -> dashboard active`

within the 15-minute SLO. “The scanner printed a candidate” is not enough.

### Production verification

After fixes deploy:

1. Capture source-feed, ledger, gate-trace, dashboard, 48-hour, and
   money-ready timestamps from one build ID.
2. Re-run the 19-link rendered smoke test.
3. Confirm zero JavaScript errors.
4. Confirm the 38 known placeholder rows display unresolved or have measured
   market-price exits.
5. Wait for three consecutive hourly cycles and require:
   - no cancellation;
   - no mixed build IDs;
   - pick-count reconciliation;
   - at least one deterministic replay candidate propagated end to end;
   - no stale sidecar presented as current.

## Recommended order

1. JavaScript syntax and broken Pages routes.
2. Zero-P/L outcome honesty.
3. Emitter-to-ledger reconciliation and replay harness.
4. Taxonomy/cohort reconciliation.
5. Strategy mutations and forward accumulation.

Fixing strategy logic before the data contract would only optimize against
unreliable labels.
