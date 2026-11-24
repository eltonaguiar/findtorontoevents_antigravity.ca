# Surface baseline, 2026-11-22

Shared facts for the twelve class dossiers. Each dossier links here instead of repeating.
Evidence frozen in `_MANIFEST.json` (Phase 0, 2026-11-22T06:38Z). Raw captures live in `_raw/`
(not published). Numbers below are read from those captures, not recalled.

## 1. Page to fetch map (what each surface actually loads)

Measured from the captured HTML/JS (`_raw/audit*_page.html`, `_raw/audit2_audit2.js`) and
HTTP-probed on 2026-11-22.

| Surface | Fetches | HTTP | Notes |
|---|---|---|---|
| `/audit/` | `./data/dashboard_data.json`, `./data/money_ready_verdict.json`, `./data/denominator.json`, `./data/db_health.json`, `dashboard_enhancements.js`, `dashboard_freshness.js`, plus many per-system pick JSONs | 200 | Largest page (1.44 MB HTML). |
| `/audit/` | `./data/stock_prices.json`, `./data/stock_forex_prices.json`, `./data/regime_report.json` | UNMEASURED | Referenced but not probed this pass. |
| `/audit2/` | `../audit3/audit3_ledger.json` (canonical first, then `../audit/data/audit3_ledger.json`, then local copies), `audit2_forward.json`, `denominator.json`, `audit2_pods.json`, `audit2.js` | 200 | `[SRC: _raw/audit2_audit2.js:154]` LEDGER_PATHS order. |
| `/audit2/` | `audit3_ledger.json` (local), `reports/forward_observations.json` | **404** | `[SRC: _raw/audit2_page.html]` references that do not resolve. |
| `/audit3/` | `audit3_ledger.json`, `audit3_evidence.json` | 200 | Ledger 722,279 B; evidence 2,523,018 B. |
| `/audit3/` | `reports/audit3_confirmatory.json`, `reports/forward_observations.json` | **404** | Referenced in prose/fetch, not served. |

Measured route status: `/audit/` 200, `/audit2/` 200, `/audit3/` 200,
`/audit/audit3.html` **404** `[SRC: manifest:not_found]`.

## 2. Frozen artifact identities (sha256)

| Artifact | sha256 | generated_at |
|---|---|---|
| `/audit3/audit3_ledger.json` | `88606e1ec2e9a0bab4e4d59a8830f24e880a3de4da93238f09e7c0ad040dcd3f` | 2026-11-22T06:35:41Z |
| `/audit/data/audit3_ledger.json` | `88606e1ec2e9a0bab4e4d59a8830f24e880a3de4da93238f09e7c0ad040dcd3f` | 2026-11-22T06:35:41Z |
| `/audit2/audit2_forward.json` | `153bc7523a3a615b2ea27038460ad02f676620dc6eac318425d6fc2e51aae366` | 2026-11-22T06:35:41Z |
| `/audit/data/audit2_forward.json` | `d3411e35272c9428dd6b296f4ff0fa99e73fea6e1396e7a96abfd4bb8a13d1c6` | **2026-11-21T08:37:25Z** |
| `/audit/data/dashboard_data.json` | `888591a6a2889b6f88fcf54a77768b7e097f86aa2113b095934e910a3e5e699a` | 2026-11-22T04:00:19Z |
| `/audit/data/money_ready_verdict.json` | `b5387de55937258c4c46c4d27c72009de82032e8893f39d16221981b64894be3` | 2026-11-22T03:58:43Z |

`[SRC: manifest:consistency_checks]` The two `/audit3` ledger copies are byte-identical right now.
The two `audit2_forward` copies are **not** identical: `/audit/data/` is 22 hours stale.

## 3. Contradiction register

Each entry: both numbers, the population behind each, and where it was read.

### C1. CRYPTO profit factor, three ways (same word, different populations)
- `/audit` readiness: PF **0.26**, n=22,985 `[SRC: _raw/audit_data_dashboard_data.json → readiness.by_class.CRYPTO]`
- `/audit` money_ready_verdict: PF **0.2621**, n=22,287 `[SRC: _raw/audit_data_money_ready_verdict.json → classes.CRYPTO]`
- `/audit3` ledger class bucket: PF **0.7886**, n=6,926 closed rows `[SRC: _raw/audit3_audit3_ledger.json → classes[CRYPTO]]`
- Plan's recalled 0.83/0.92 values were **not** reproduced this pass → `UNMEASURED`.

Cause of the spread: different populations (all picks vs closed picks with prices vs
canonical-scored rows) and different cost models per class. The `/audit` PF uses the
dashboard's own aggregation; `/audit3` applies per-class round-trip slippage and the
canonical denominator (8,827 of 14,914 picks).

### C2. Three money-ready denominators
- `/audit` summary: `money_ready: []`, `watch: []`, `n_classes: 11` `[SRC: _raw/audit_data_money_ready_verdict.json → summary]`
- `/audit3` summary: `n_proven: 0`, `n_candidate: 0` classes; `n_proven_symbols: 0` `[SRC: _raw/audit3_audit3_ledger.json → summary]`
- `/audit2` echoes the ledger via `LEDGER_PATHS` `[SRC: _raw/audit2_audit2.js:154]` — it is not an independent count.

Zero money-ready on all three, but for different reasons: `/audit` = no class passes its gates;
`/audit3` = no cell reached PROVEN_T2. Same number, different claim.

### C3. COMMODITY WATCH vs KILL
- `/audit` readiness: `gate_state: BLOCKED`, `sample_tier: BELOW_T2` `[SRC: _raw/audit_data_dashboard_data.json → readiness.by_class.COMMODITY]`
- `/audit3` ledger: verdict **KILL**, PF 0.15, n=50, net expectancy CI [-5.004, -1.338] entirely < 0 `[SRC: _raw/audit3_audit3_ledger.json → classes[COMMODITY]]`
- `/audit3` kill tribunal also kills `futures_momentum` (n=23, PF 0.0) under COMMODITY.

Not a contradiction in logic (BLOCKED ≠ WATCH), but the plan asserted WATCH: that assertion is
not reproducible from today's payload. Recorded as: the surfaces disagree on *label*, and the
ledger has the only CI-based kill.

### C4. Two kill lists sharing one name
- `/audit3` `kill_tribunal.kills` contains CRYPTO/MomentumEMA n=73 PF 0.037 and CRYPTO `unknown` n=260 PF 0.54 `[SRC: _raw/audit3_audit3_ledger.json → kill_tribunal]`
- `/audit` dashboard has its own per-class gate states `[SRC: _raw/audit_data_dashboard_data.json → readiness]`
- `verdict_churn` flipped CRYPTO/`unknown` WEAK→KILL and CRYPTO/ARB WEAK→KILL this run `[SRC: _raw/audit3_audit3_ledger.json → verdict_churn]`

So "CRYPTO unknown killed" is true on the ledger and was WEAK one run ago. A verdict is a
snapshot, not a property.

### C5. Stale sidecars
- `/audit/data/audit2_forward.json` is 22 h behind `/audit2/audit2_forward.json` `[SRC: manifest:consistency_checks]`
- `/audit2/audit2_forward.json` embeds `gate_generated_at: 2026-11-21T00:45:30Z` while the ledger is 2026-11-22T06:35Z `[SRC: _raw/audit2_audit2_forward.json → sources]`
- Local `audit_dashboard/data/dashboard_data.json` is 2026-10-19; the live copy is 2026-11-22 `[SRC: manifest:entries]`

### C6. Ledger provenance is `/tmp`
`provenance.source_file = /tmp/audit3/dashboard_data.json` `[SRC: _raw/audit3_audit3_ledger.json → provenance]`.
Mitigation measured: `provenance.input_sha256` == sha256 of the live `/audit/data/dashboard_data.json`
(`888591a6…`) `[SRC: manifest:consistency_checks]`. The `/tmp` path is not reproducible, but the
input the ledger was built from is exactly the file now being served.

### C7. Class taxonomy is not one list
- canonical (money_ready_verdict): 8 classes, includes MUTUAL_FUND, no MEME `[SRC: alpha_engine/money_ready_verdict.py:255]`
- `/audit` payload: 11 keys, has `MEME`, `CHEAP_STOCKS`, `PENNY_STOCK`
- `/audit3` ledger: 7 class buckets (CRYPTO…FUTURES), 374 cells across 12 symbol/segment buckets
- projection-market picks (Kalshi/Polymarket) carry no SPORTS/INDEX class in the ledger `[SRC: _raw/audit3_audit3_ledger.json]`

### C8. CRYPTO is PASS and KILL on the same day (added 2026-11-22)
- `mega_mutation`/crypto: n 339, WR 67.0, PF 3.50, PASS_ALL_AXES `[SRC: reports/per_class_scrutiny_20261004.json:6]`
- CRYPTO class: n 6926, WR 39.39, PF 0.7886, KILL `[SRC: _raw/audit3_audit3_ledger.json:1556]`
- `/audit` policy_clean: n 22287, PF 0.2621 `[SRC: _raw/audit_data_money_ready_verdict.json:32]`
- Cause is measurable, not mysterious: the scrutiny engine uses GROSS `pnl_pct` with no cost model `[SRC: tools/per_class_scrutiny_engine.py:87]`, keys on a `(source_system, category)` pair `[SRC: tools/per_class_scrutiny_engine.py:74]`, runs at n>=30 `[SRC: tools/per_class_scrutiny_engine.py:199]`, and its "OOS" is a mid-date split of the same rows `[SRC: tools/per_class_scrutiny_engine.py:128]`. `PASS_ALL_AXES` is not `PROVEN_T2`.

### C9. The class population itself is contested (added 2026-11-22)
- The denominator's own note: exclusion reasons total 12,174 but total minus canonical is 6,087, because the publisher and the tribunal exclude different cohorts `[SRC: _raw/audit_data_denominator.json:36]`.
- 8,827 of 14,914 closed picks scored (59.2%) `[SRC: _raw/audit_data_denominator.json:39]`; `invalid_row` alone accounts for 11,782 exclusions `[SRC: _raw/audit_data_denominator.json:13]`.
- Measured bridge: CRYPTO DB gross PF 1.051 to net 0.996 at the ledger's cost, versus a published 0.789, a residual of +0.2077 `[SRC: reports/class_metric_reconciliation_20261122.md]`. Cost explains about 0.055; the rest is cohort.

### C10. `/audit` publishes one PF and sizes on another (added 2026-11-22)
- CRYPTO daily PF 0.2621 versus intrabar PF 0.9169, `pf_inflation_x` 0.29, `wr_inflation_pp` 5.3, `flag: false`, `sizing_source: intrabar_truth` `[SRC: _raw/audit_data_money_ready_verdict.json:14]`.
- ETF is the extreme: daily 1.8752 versus intrabar 0.0187, a 100.28x inflation `[SRC: _raw/audit_data_money_ready_verdict.json]`.
- BOND: daily WR 1.0 on n 2 versus intrabar WR 7.69% on n 26, 92.3pp `[SRC: _raw/audit_data_money_ready_verdict.json]`.

### C11. The backtest winners file is stale and self-declares low confidence (added 2026-11-22)
- Generated 2026-06-01, tiers TIER_2/TIER_3/REHAB, FOREX PF `null` with tier REHAB `[SRC: reports/eight_class_winners_20260601.json:1]`.
- Nothing in it has been re-run against the current ledger, and it must not be quoted as current performance.

## 4. Metric glossary (so a dossier number is unambiguous)

- **WR** win rate = wins / resolved. `/audit` counts flat as neither; `/audit3` uses `net pnl > 0` as the win definition `[SRC: _raw/audit3_audit3_ledger.json → provenance.win_definition]`.
- **PF (gross)** sum of winning pnl / sum of losing pnl, no costs.
- **PF (net)** same after per-class round-trip slippage. Always label which. `/audit3` `pf_basis: net`.
- **Net expectancy** mean net pnl per trade, with bootstrap 95% CI (2,000 resamples, seed 42) `[SRC: _raw/audit3_audit3_ledger.json → conventions]`.
- **Selection alpha** pick net return minus direction-adjusted buy-and-hold over the same window (M1b) `[SRC: _raw/audit3_audit3_ledger.json → selection_alpha.definition]`.
- **2×-cost stress** CI recomputed with slippage doubled; `stress_2x_ok` must be true to survive.
- **DSR** deflated Sharpe ratio against `n_trials` (374 cells / 66 scored) `[SRC: _raw/audit3_audit3_ledger.json → provenance.n_trials_dsr]`; threshold 0.95.
- **BH q** Benjamini-Hochberg within namespace; `fdr_q` 0.1.
- **Forward gate** PROVEN_T2 requires n≥100 forward rows, net PF CI-LB > 1.0 or IR ≥ 0.5, honest intrabar first-touch on 100%, benchmark coverage ≥ 90% `[SRC: _raw/audit3_audit3_ledger.json → forward_gate.rule]`.

## 5. Do not trust (without re-measurement)

- **`PROMOTED` sidecar status at n=0.** 3 of 7 sidecars are `PROMOTED` with zero trades; the status is sticky from a hardcoded set, not stats `[SRC: audit_trail/dashboard_generator.py:12256]` and `[SRC: _raw/audit_data_dashboard_data.json → sidecar_promotion_status]`.
- **`BOND` WR 100%.** n=2 `[SRC: _raw/audit_data_dashboard_data.json → readiness.by_class.BOND]`. A percentage on two trades.
- **`FUTURES` PF 1.87.** n=4, `dsr: null` `[SRC: _raw/audit3_audit3_ledger.json → classes[FUTURES]]`.
- **Any `/audit` class n.** `/audit` counts picks (22,985 CRYPTO) while `/audit3` counts canonical closed rows (6,926). Do not compare them.
- **`/audit2` numbers** as evidence: it re-serves the ledger and a forward file whose gate stamp is a day old.
- **`/tmp` provenance** as a reproducible path (see C6).
- **The plan's recalled CRYPTO PF 0.83/0.92** → `UNMEASURED` this pass.
