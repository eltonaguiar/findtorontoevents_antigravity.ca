# Collective review — /audit, /audit2, /audit3

Generated 2026-11-21T05:27:56Z.
Models: LiteLLM local proxy (:4000) + SubQ savant-1.4. Raw text, unedited.

## local_structure — `ULTRA_FREE_CLOUD_LARGE`

1. **Contradiction in Total Rows**:
   - The ledger indicates a total of `16,372 closed picks` but specifies `unscored_rows` as `7,603`, which adds to `total_resolved` `8,769`. This leads to a contradiction since `16,372 = 8,769 + 7,603` per the current reporting, but various exclusions and statuses do not sum clearly.
   - **Source**: audit3 ledger, `total_closed_picks` vs `unscored_rows`.

2. **Metric Claim without Data**:
   - "Scores the published canonical view; /audit counts the same rows" appears to be referenced yet lacks a connection to data or the auditor's scoring logic which should be detailed explicitly to support this claim.
   - **Source**: audit3 ledger, statement in coverage.

3. **Metrics Computation Defect**:
   - The metric `alpha_pct` appears to be calculated as `-0.2681` but without clear presentation of the supporting data used for this computation relative to `pick_net_pct`, which is reported as `-0.2237`. Since these are metrics dealing with the same entities, inconsistencies must be clarified with clear source linkage.
   - **Source**: audit3 ledger, `overall.alpha_pct` and `overall.pick_net_pct`.

4. **Missing Data References**:
   - The fetch URL `./data/strategy_ic_analysis.json?` is assumed required but there is no evidence that files are present to substantiate claims regarding `strategy` data within the dashboard.
   - **Source**: HEADINGS section - scattered mentions of strategies without corresponding data sources verified to exist. 

5. **Inconsistent Configuration Parameters**:
   - The `n_positive_segments` in the summary reports as `0`, but references to winning or positive metrics must quantify these parameters accurately by comparing them against established metrics within the `n_cells` or forward evidence aggregates.
   - **Source**: audit3 ledger, summary section.

6. **Discrepancies in File Access**:
   - Numerous URLs (e.g., `https://api.coingecko.com/api/v3/coins/`) indicated seem either suspicious or require further validation; failure to confirm these nodes might jeopardize overall dashboard reliability.
   - **Source**: Fetches section, overall access to the nodes without direct verification ties to data points in the audit.

7. **Potential Legacy Data Impact**:
   - The term ‘stale_exit_beyond_planned_stop’ and various other stale exit occurrences needs elucidation to clarify their direct impact on metrics being computed for `forward_gate`. These should be benchmarked back to primary data.
   - **Source**: audit3 ledger, resolver_anomalies section.

8. **Dead URLs or Severed Links**:
   - While detailed callouts regarding API endpoints such as `https://api.github.com/` exist throughout the fetch lists, several appear to link to an unreachable or deprecated service. Direct API link checks are necessary for each.
   - **Source**: FETCHES section for external service checks, though specific dead links will need current validation against live checks. 

These defects, ranked by their potential impact and clarity needed in reporting, outline specific areas that require immediate attention to ensure reliability and correctness in the dashboard's structure and data integrity.

## local_data_consistency — `ULTRA_PAID_OLLAMA_MINIMAX_M3_CLOUD`

# Defects: audit2.html vs its data files

Ranked by consequence.

---

## 1. The "Forward evidence clock" table is unsupported and miscounts denominators

**Page** (`audit2.html`, Forward evidence clock):
> "A pod can only promote on forward rows dated after its registration. Rows here come from `reports/forward_observations.jsonl`."
> Table headings: *Hypothesis · Forward rows · Benchmark leg · Intrabar first-touch · Status*

**Data** (`audit2_forward.json`):
```
"by_hypothesis": { "H-119": { "n": 430, "benchmark_leg": 343, "intrabar": 430, "pods": [] } }
```

- Only one hypothesis (H-119) has any forward rows at all; every pod in `audit2_pods.json` maps to a pod-hypothesis (`H-2026-11-19-0x`, `H-BABY-…-001`) that does **not** appear in `audit2_forward.json`. So every pod's forward-row count is zero and the table can only render "0 rows" for the six pods on the page.
- `H-119` is not a pod in `audit2_pods.json` (`"pods": []` in the forward file), so a reader who sees "Forward rows 430" against H-119 has no pod to attach it to. The table's column *Hypothesis* vs *Status* invents a pairing that neither file provides.
- **"Benchmark leg 343"** vs **"Forward rows 430"** is a denominator switch with no label: 343/430 = 79.8% coverage. Anyone reading "Benchmark leg: 343" next to "Forward rows: 430" will read it as a count, not a coverage shortfall. The ledger's own `forward_gate.H-119.benchmark_coverage = 0.798` and its ineligibility reason `"benchmark_leg_ret coverage 80% < 90%"` make this the actual disqualifier.
- **"Intrabar first-touch 430"** is presented alongside the other two as if all three were counts of independent facts. In `audit3` `forward_gate.H-119.intrabar_first_touch_all = true` is a boolean, and `intrabar: 430` means all 430 were intrabar-resolved, not "430 intrabar events." A reader will misread this column.
- **"Status"** column has no source. `audit2_forward.json` has no status field. The only place `H-119` status lives is `audit3 fenceforward_gate.H-119.eligible = false`, and it is ineligible for two reasons (PF CI-LB 0.9213 ≤ 1.0 **and** benchmark coverage 80% < 90%). Rendering this row without those two reasons loses the only decision-relevant content.

**Consequence:** the section advertises a clock that reads "ready" but the sole populated row is doubly ineligible.

---

## 2. Footer freshness claim contradicts the ledger's timestamp

**Page** (`audit2.html` footer):
> "the pod registry is a static snapshot dated **2026-11-19** because `reports/` is not web-served."
> Header sub: "Every **live** number on this page comes from `audit3_ledger.json`."

**Data:**
- `audit2_pods.json` → `"generated_at": "2026-11-19T21:00:00Z"` (matches).
- `audit2_forward.json` → `"generated_at": "2026-11-19T08:41:27.989419+00:00"` — also 2026-11-19. So the forward file is *older* than the pod registry by ~12 hours, but the page never says which file the "Forward evidence clock" section reads from. The page cites `reports/forward_observations.jsonl` as the source; that path does not exist in the supplied data (the only forward file is `audit2_forward.json`). Between the pod registry (21:00) and the ledger (`generated_at 2026-11-20T01:57:23Z`, `source_generated_at 2026-11-20T01:17:09Z`) the "live" numbers are dated 2026-11-20, while the "static" snapshot is dated 2026-11-19. The page does not date the ledger's expiry; the word "live" next to a ledger whose `last_closed_at` is `2026-11-20T00:40:53Z` is accurate but the reader has no idea the file was cut ~1h17m earlier.

**Consequence:** a reader comparing section dates will see "pod registry 2026-11-19" and "ledger 2026-11-20" and correctly conclude the pod side is stale, but is given no signal that the forward file is even older.

---

## 3. "Trial budget" text says "measured slippage" but the only slippage in scope is ex-post net-PnL ratios

**Page** (Trial budget & benchmarks caption):
> "Cost gate: average net PnL must be at least 3× the measured slippage. ETF slippage measured ≈234% of per-trade PnL (monthly cadence only); CRYPTO ≈37%."

**Data:** The supplied ledger JSON has **no** slippage field, no cost gate, and no CRYPTO/ETF slippage ratio. There is no way to compute "234%" or "37%" from any of the four files provided. The 3× gate is stated in the caption but not shown as a table column, so the page's "Gate" column values (whatever they render) cannot be checked.

**Consequence:** two fabricated-looking percentages on a surface labelled "methodology library" will be quoted. If they came from a file not in the bundle, that file must be named; if not, they cannot be reproduced.

---

## 4. "Net expectancy/trade", "required_n", and "DSR" columns in the Verdicts table have no source field

**Page** (Verdicts table headers):
> `n · Net expectancy/trade · Net 95% CI · 2× cost OK · DSR · required_n`

**Data:** `audit3_ledger.json.summary` exposes `n_cells_tested` (67), `n_cells_dsr_scored` (66), `n_weak` (59), `n_kill` (8), `n_insufficient` (295), `n_proven` (0). It does **not** expose per-class net expectancy, per-class CI, DSR per class, or `required_n`. If the table is populated per asset class, its columns have no matching field in the ledger at the granularity the table claims.

**Reader trap:** `n_cells_dsr_scored = 66` vs `n_cells_tested = 67` — the page's "DSR" column will silently drop one cell, and a reader comparing row sums to the header will think one class is missing. The `summary_scope` field (`"cell-level: n_proven/n_candidate count strategy cells only; symbol and class buckets are counted separately"`) explicitly warns that `n_kill = 8` is **cells**, not the same denominator as `n_kill_classes = 2` or `n_kill_symbols = 11`. A table that lists "Verdict… n" per asset class must specify whether the n is cells, symbols, or classes. It does not.

---

## 5. The `n_candidate = 0` / `n_proven = 0` facts are present in the ledger but not surfaced in the page's verdict area

**Data** (`audit3_ledger.json.summary`):
```
n_candidate: 0, n_candidate_symbols: 0, n_proven: 0,
n_proven_classes: 0, n_proven_symbols: 0,
n_proven_segments: 0, n_positive_segments: 0
```

**Page:** The header sub says "what is worth forward-testing," and the "Candidate & observe pods" section intro says "Pre-registered before forward data… may confer confirmatory status." Nothing in the supplied HTML shows the global `n_candidate = 0` / `n_proven = 0`. A reader of the "Verdicts" table and the pods list would come away believing there are candidates under observation. The ledger says there are zero of each at every granularity (cell, symbol, class, segment).

**Consequence:** the page's lead sentence ("The positive side of /audit3's kill tribunal") oversells — the ledger's positive side is empty.

---

## 6. "Proven" vs "tested" wording

**Page** (`audit2.html`, Per-class verdicts header):
> "reconciled against the canonical rollup"

**Data:** `coverage.canonical_mode = "canonical"` and `loaded_from_sidecar = true`, with `canonical_kept_rows = 8769` and `canonical_rows_sha256 = 63609da…`. But `coverage.scored_share_of_valid_note` explicitly states:
> "not comparable: … the ratio exceeded 100% (110.41%)"

and `scored_share_of_valid_pct = null, status = "not_comparable"`. So the "canonical rollup" is one of **two** views in the ledger; the page presents it as the single reconciled source. The word "reconciled" is doing work the data does not support — the two views are declared incomparable on one axis (share-of-valid) while identical on another (8769 rows).

**Reader trap:** `n_weak = 59` (cells) vs `n_weak_symbols = 58` vs `n_insufficient = 295`. A reader will read "59 weak" as a strategy count; 58 of those are at the symbol level, and 295 were never computable.

---

## 7. "Kill rate 11.94%" has a denominator that does not divide

**Data** (`audit3_ledger.json.summary`):
- `n_kill: 8`, `kill_rate_pct: 11.94`.
- 8/11.94% = 67.0 = `n_cells_tested`. So the kill rate is **kills ÷ tested cells**, not kills ÷ total. `n_cells_total = 362`, so kills ÷ total = 2.21%.
- The page's Verdicts table has a "Verdict" column ("KILL" is one enum value per CSS) — an asset-class row badged KILL will be read alongside `kill_rate_pct 11.94` as if 11.94% of class-level strategies died, when in fact that's cells within the tested subset.

**Consequence:** the only headline risk number on the surface uses a denominator (67) different from the one printed next to it (362) or the one in the lede (8,769 rows).

---

## 8. Forward gate `H-119` row is misrepresented if the page maps it to a pod

`audit3_ledger.json.forward_gate.H-119` carries:
- `eligible: false`
- `reasons: ["net PF CI-LB 0.9213 <= 1.0 and IR 0.043 < 0.5", "benchmark_leg_ret coverage 80% < 90%"]`
- `note: "descriptor only: excess vs benchmark is reported, not gated"`

The page's Forward evidence clock columns *Benchmark leg* and *Intrabar first-touch* line up with `benchmark_coverage 0.798` and `intrabar_first_touch_all true`, but the page never renders `excess_vs_benchmark_pct 1.1646` — which the ledger explicitly warns is not gated. If a reader sees "Benchmark leg: 343" and the only gate text is elsewhere, they may read the +1.16% excess as a pass signal when the ledger says it is *not a gate*.

---

## 9. Pod `evidence` strings contain numbers not present in any supplied file

For each pod in `audit2_pods.json`, the `evidence` string cites results (e.g. `Sharpe 3.10, DSR 21.4, PBO 0.18`, `FXMom USDJPY n=42, Sharpe 2.018, MC p=0.48`, `FaberTAA SPY n=11 Sharpe 1.743`). None of these appear in `audit3_ledger.json`, `audit2_forward.json`, or `audit2_pods.json` (the pods file only repeats them). There is no source path for the pod-level Sharpe/PF/DSR/PBO figures. The pod file's own `note` admits: "Not evidence-grade; audit3 is the decision surface." So the page's "Candidate & observe pods" cards restate unbacked numbers without that disclaimer.

Additionally, `POD-CRYPTO-VWAP-REVERSION` evidence says `"DSR 21.4"` — DSR above 1 is not on the usual scale (DSR is a proba / Sharpe-like statistic; 21.4 is in the ballpark of a raw Sharpe, not a DSR). The same string says `"PBO 0.18 — CONTESTED: … CSCV PBO to 0.84-0.97"` — i.e. the pod contradicts itself in a single sentence and the page renders both halves without flagging.

---

## 10. Stale artifact: `fx_prices` blocker

`POD-FOREX-USDJPY-MOMENTUM.evidence`: "FX data blocker (fx_prices stale to 2026-02-09)". `audit3_ledger.json.coverage.window.last_closed_at = 2026-11-20T00:40:53Z`. The FX feed is >9 months stale relative to the ledger cut. The pod is badged `observe`, so the staleness does not gate promotion on the page — but the page's "Forward evidence clock" would happily show 0 forward rows for this pod as if it just registered, not as if its data source has been broken since February.

---

## Summary of contradictions (file → field → page claim)

| # | File | Field / value | Page claim | Defect |
|---|---|---|---|---|
| 1 | `audit2_forward.json` | `by_hypothesis.H-119.pods = []`; no pod-hypothesis IDs | Table joins H-119 to pod status | 430 rows shown against a non-pod; 6 pods show 0 |
| 1 | `audit2_forward.json` | `benchmark_leg 343` vs `n 430` | "Benchmark leg" column | denominator mislabeled as count |
| 1 | `audit2_forward.json` | `intrabar: 430` (all) | "Intrabar first-touch" column | boolean rendered as count |
| 2 | `audit2.html` footer | "static snapshot dated 2026-11-19" | — | forward file (08:41Z) predates pod snapshot (21:00Z) by 12h; not disclosed |
| 2 | `audit2.html` footer | `reports/forward_observations.jsonl` | — | path not present in supplied data |
| 3 | *(none supplied)* | — | "3× measured slippage", "234%", "37%" | no source field |
| 4 | `audit3_ledger.json.summary` | `n_cells_dsr_scored 66` vs `n_cells_tested 67` | "DSR" column | row will be silently missing |
| 4 | `audit3_ledger.json.summary` | `n_kill 8` (cells) vs `n_kill_classes 2` vs `n_kill_symbols 11` | Verdicts table `n` column | denominator ambiguous |
| 5 | `audit3_ledger.json.summary` | `n_candidate 0`, `n_proven 0` (all scopes) | "what is worth forward-testing" | surface has no positive-side content |
| 6 | `audit3_ledger.json.coverage` | `scored_share_of_valid_pct_status: "not_comparable"` | "reconciled against the canonical rollup" | two views declared incomparable |
| 7 | `audit3_ledger.json.summary` | `kill_rate_pct 11.94` = 8/67, not 8/362 | headline number next to total 362 | denominator switch |
| 8 | `audit3_ledger.json.forward_gate.H-119` | `eligible false`; two reasons; `note` says excess is descriptor-only | Forward clock row | only decision-relevant content is dropped |
| 9 | `audit2_pods.json.pods[*].evidence` | Sharpe/DSR/PBO/MC p values | rendered as evidence | no backing file; DSR 21.4 not on a DSR scale; VWAP pod self-contradicts |
| 10 | `audit2_pods.json` POD-FOREX | `fx_prices stale to 2026-02-09` | "n>=100 forward rows" gate | blocker since Feb vs ledger cut Nov 20 |

## local_plain_reader — `ULTRA_PAID_OLLAMA_LOKER_V2_1_CLD_CDR_480B`

Only two page sources are actually present (`audit3.html`, `audit2.html`), so a three-way disagreement cannot be checked; `audit2.html` links to `/audit3` as a separate surface, but that target is not in the input.

**What each claims**
- `audit3.html`: a "quant kill tribunal" ledger, "The only pipeline that can promote anything," scoring live/forward rows only; the evidence registry "cannot be re-scored… nothing on this tab can promote a strategy"; forward counts come from `reports/forward_observations.jsonl` "as read by the tribunal's `forward_gate_block()`"; footer: "regenerated by `alpha_engine/audit3_tribunal.py`."
- `audit2.html`: the companion candidate/methodology page; "Every live number on this page comes from `audit3_ledger.json`"; pod registry "is a static snapshot dated 2026-11-19 because `reports/` is not web-served."

**Defects, ranked**
1. **Cost-gate contradiction inside `audit2.html`.** "2× cost OK = the net-expectancy CI still excludes zero at twice the class slippage (a required gate for PROVEN_T2 / CANDIDATE)" vs. "Cost gate: average net PnL must be at least 3× the measured slippage." The promotion threshold is defined two different ways on the same page.
2. **Freshness contradiction between pages.** `audit3.html` says forward row count/fingerprint come from `reports/forward_observations.jsonl` "as read by the tribunal's `forward_gate_block()`" (live read), while `audit2.html` says the pod registry is static because "`reports/` is not web-served." One of these is false.
3. **Claims with no data behind them.** `audit2.html` asserts "Every live number on this page comes from `audit3_ledger.json`," yet both verdict tables render only "—" and the Measures/Traps/Retired tables are empty. `audit3.html` likewise renders "loading ledger…", "Loading…", "Loading registry…" and blank Kill list / cell sections while claiming verdicts and a sole promotion pipeline.
4. **Unsourced load-bearing number.** `audit2.html`: "ETF slippage measured ≈234% of per-trade PnL (monthly cadence only)" — no file, field, sample, or denominator cited, and it sits next to the 2×/3× gate it would make unmeetable.

**Least-trusted number: the ≈234%.** It has no provenance, no sample, and it contradicts the page's own gate arithmetic — if slippage is 234% of per-trade PnL, the "3× the measured slippage" net-PnL requirement is unreachable, so every verdict on the page inherits an unsupported, self-defeating input.

## subq_audit2 — `subq-savant-1.4`

## Defects, ranked by consequence

**1. The forward evidence clock tracks a hypothesis no pod owns.**
`audit2_forward.json` has exactly one entry: `by_hypothesis.H-119` with `n: 430`, `pods: []`. The six hypotheses in `audit2_pods.json` (`H-BABY-EQUITY-VT-PATTERN-SWEEP-001`, `H-2026-11-19-01` … `-05`) appear nowhere in the forward file. So the section whose stated rule is "A pod can only promote on forward rows dated after its registration" shows 430 rows for an orphan hypothesis while every registered pod has zero forward rows. An operator reading this would think forward evidence exists for the pods; it does not.

**2. Benchmark leg covers 343 of 430 rows, and the page prints both numbers without comment.**
`n: 430`, `benchmark_leg: 343` — 87 rows (20%) have no benchmark leg. `POD-EQUITY-BREAKOUT`'s gate is "IR>=0.5 vs a matched SPY leg", which can only be computed on the 343. Any excess-return or IR figure must use 343 as the denominator; using 430 silently dilutes it. The table shows the two counts side by side as if independent.

**3. Two different cost gates on the same page.**
Verdicts table caption: "2× cost OK = … at twice the class slippage (a required gate for PROVEN_T2 / CANDIDATE)". Cost-gate text under Trial budget: "average net PnL must be at least 3× the measured slippage." A pod cannot be judged against both. Worse, the printed slippage numbers fail the 3× gate arithmetically: "ETF slippage measured ≈234% of per-trade PnL" means net PnL ≈ 0.43× slippage; "CRYPTO ≈37%" gives ≈2.7×. Neither class reaches 3×.

**4. The promotion rule cannot be evaluated with the data shown.**
"A pod can only promote on forward rows dated after its registration" — `audit2_forward.json` contains only counts (`n`, `benchmark_leg`, `intrabar`, `pods`), no row dates, and the pod registry carries no per-pod registration timestamp. The rule is unenforceable as presented.

**5. `DSR 21.4` is not a usable DSR value.**
`POD-CRYPTO-VWAP-REVERSION` evidence: "Sharpe 3.10, DSR 21.4, PBO 0.18". A deflated Sharpe ratio is a probability-like statistic; 21.4 is off by orders of magnitude and inconsistent with the `DSR` column in the verdicts table. Either the units differ between the two places or one is wrong — an operator can't compare pods on DSR as displayed.

**6. Provenance statements contradict each other.**
Footer: "Every live number on this page comes from `audit3_ledger.json`." Forward section: "Rows here come from `reports/forward_observations.jsonl`." Pods section data comes from `audit2.js` per `audit2_pods.json`'s own `source` field. Three sources claimed for one page, and the forward file actually supplied is `audit2_forward.json`, not `forward_observations.jsonl` — a reference an operator cannot resolve, made worse by the footer's admission that `reports/` is not web-served.

**7. An unbacked universal claim sits in Doctrine.**
"Volatility scaling is free alpha. Simply scaling positions by inverse realized vol improves Sharpe by 0.3+ for any momentum strategy." No data, no citation, and "any" is unfalsifiable as stated. It is the kind of claim that gets baked into sizing decisions before it is tested.

**8. Every table body is a placeholder.**
All rows render as `—` / "loading ledger…" and depend on `audit2.js`, which is not part of this review set. Nothing on the page can be checked as rendered; only the static text and the two JSON files are reviewable.

**9. Minor: forward counts are older than the pod registry.**
`audit2_forward.json` `generated_at` 2026-11-19T08:41Z vs `audit2_pods.json` 2026-11-19T21:00Z — 12 hours apart on the same day. If the registry was regenerated after the forward counts, the two are not a consistent snapshot.

**10. Minor: underpowered Sharpe figures presented as evidence.**
`POD-FABER-TAA`: "SPY n=11 Sharpe 1.743; QQQ n=7 Sharpe 1.652". At n=7–11 the standard error on a Sharpe estimate is roughly 0.3–0.4; the two figures are indistinguishable from each other and from zero. They are listed as evidence for a pod whose own gate is n>=100.

## subq_audit3 — `subq-savant-1.4`

We need audit page vs ledger. Need identify concrete defects: contradictions between page and data file, stale/missing artifacts, claims with no data behind them, dead links, denominators changed, metrics cannot be computed as shown. Need cite file and exact text/field. Rank by consequence. Silent if section sound.

We have full HTML and partial ledger summary/coverage/selection_alpha/forward_gate. Need compare.

Let's parse carefully.

Key counts:
summary:
n_cells_total 362
n_cells_tested 67
n_cells_dsr_scored 66
n_proven 0
n_candidate 0
n_weak 59
n_kill 8
n_insufficient 295
n_kill_symbols 11, n_proven_symbols 0
n_symbol_cells 69
n_rows 8769
kill_rate_pct 11.94

Page headline:
tested = s.n_cells_tested || 0 (67)
headline = `${s.n_proven} of ${tested} tested cells survive every gate` -> 0 of 67. okay.
subline:
`${s.n_rows.toLocaleString()} closed picks · ${s.n_cells_total} strategy cells (${tested} with n ≥ ${conv.wr_floor_n}) · ${s.n_symbol_cells} symbol cells · ${s.n_kill} strategies and ${s.n_kill_symbols} symbol cells killed. ${s.n_weak} keep observing...`
Potential contradiction: says "8 strategies ... killed" but summary has n_kill_classes 2 and n_kill_symbols 11. n_kill may refer strategy cells? It says "n_kill": 8. "n_kill_classes":2. The subline says "8 strategies and 11 symbol cells killed". Is n_kill strategies? summary_scope says "cell-level: n_proven/n_candidate count strategy cells only; symbol and class buckets are counted separately". n_kill maybe strategy cells? Not explicit. Could be "8 strategies" okay if n_kill counts strategy cells. But tribunal entries include scopes strategies, symbols, segments, class aggregates. Need not overreach.

Kill rate: kill_rate_pct 11.94. How computed? 8/67 = 11.94%. Yes 8/67=11.9403. So kill rate denominator tested cells. Page KPI "Kill rate" displays `(s.kill_rate_pct||0)+'%'` = 11.94%. Fine, though no denominator shown; could be defect? It says kill rate red. But 11.94 is 8/67. Okay.

Coverage:
scored_rows 8769
total_closed_picks 16372
unscored_rows 7603
scored_share_of_total_pct 53.56
statement: "audit3 scores 8,769 of 16,372 closed picks (53.6%). The other 7,603 are not in this ledger: the publishing dashboard reports 7,508 integrity-excluded and 9,176 auto-expired rows, and no surface scores any of them. Those cohorts overlap, so they do not sum to the gap — read them as reasons rows are missing, not as a partition. This run scores the canonical resolved view (sha256 63609da549a7…)."

Page coverage:
covStatement = cov.statement. KPI:
['Judged here', sharePct==null ? pad(cov.scored_rows) : sharePct+'% of the closed book', ...] => "53.56% of the closed book"
['Scored rows', pad(cov.scored_rows!=null?cov.scored_rows:s.n_rows), 'blue'] => 8,769
['Published closed picks', pad(cov.total_closed_picks), ''] => 16,372
['Not scored here', pad(cov.unscored_rows), 'amber'] => 7,603

Excluded cohorts table: integrity_excluded n 7508, auto_expired n 9176. Note says overlap. Fine.

But denominator section has canonical_excluded_by_reason invalid_row 7394 etc, canonical_kept_rows 8769. Not shown in covRows? covRows from excluded_cohorts + resolver_anomalies + row_drops. It does not include denominator canonical_excluded_by_reason. But statement covers cohorts. Could be okay.

Potential contradiction: valid_closed_picks 7942 and scored_share_of_valid_note says ratio exceeded 100% (110.41%) not comparable. The page displays only share of total (53.56), not share of valid. It also sets `% of the closed book`, which is total_closed_picks. Fine.

Selection alpha:
available true, covered 3162, n_universe 3500. Page alphaNote: "Selection alpha = pick net return minus ... (M1b; 3,162/3,500 picks priced)." It uses `(sa.covered||0).toLocaleString()}/${(sa.n_universe||0).toLocaleString()}` => 3,162/3,500. Ledger matches. Good.

But bar coverage? Not in provided ledger. The page renders alphaCovTbl from `sa.bar_coverage`; absent in ledger. It would be empty. No defect? Maybe missing artifact? The ledger provided selection_alpha has no bar_coverage. Page says table for coverage. If absent, alphaCovRows empty; alphaCovNote empty. Fine? But page's code has comment about 2026-11-19 stale tables, not rendered. No issue.

Forward gate:
enforced true
n_rows 430
fingerprint 5771...
pods: 9 pods? Let's count: COMMODITY, CRYPTO-BOLLINGER, CRYPTO-BTC4H, CRYPTO-POSITION, CRYPTO-VWAP, EQUITY-BREAKOUT, ETF-DUAL, FABER, FOREX = 9. hypotheses only H-119 with n_forward 430. Page renderForward:
podRows from pods; hypRows from hypotheses. eligible = podRows.filter(p=>p.eligible).length = 0. fwdSub:
`430 forward rows in the ledger (fingerprint 5771...) · 9 pods · 0 eligible to promote · 0 read errors. Rows are counted only from each pod's registration date, so a pod cannot inherit pre-registration history.`
Ledger n_rows 430, fingerprint matches, pods 9, read_errors [], enforced true. Fine.

But potential contradiction: H-119 hypothesis has n_forward 430, min_n 100, eligible false due reasons. Pods all n_forward 0. Page fwdKpis includes "Pods tracked 9", "Eligible 0". Fine.

G8 gate text in gates:
fg.enforced ? `${(fg.n_rows||0).toLocaleString()} forward rows, fingerprint ${esc(fg.fingerprint||'—')}; a pod reaches PROVEN_T2 only on its own rows closed after registration (${Object.keys(fg.pods||{}).length} pods tracked).`
Matches 430 rows, fingerprint, 9 pods. Good.

Hypotheses section:
h.by_status from d.hypotheses. Not provided in ledger excerpt. Can't audit.

Evidence registry:
fetch audit3_evidence.json. Not provided. Can't audit.

Need find defects in provided data/page. Let's systematically inspect each rendered value.

Important: page uses `s.n_proven` in KPI "Proven T2" and class? n_proven 0. It says headline "0 of 67 tested cells survive every gate" — wording "0 of 67 ... survive" could imply none survive, while n_weak 59 keep observing. But "survive every gate" means PROVEN only. Fine.

Potential defect: "n_cells_tested": 67 but "n_cells_dsr_scored": 66. The page's G4 says "Deflated Sharpe ≥ threshold using n_trials = tested cells." The cells table marks DSR per cell; if one tested cell lacks DSR, does a cell marked tested without DSR? We don't have cells. The summary shows 67 tested, 66 DSR scored. The page does not surface that one tested cell lacks DSR. It displays DSR column with '—' if null. Could be a defect: a cell can be tested (verdict?) without DSR. But without cell data, can't cite exact cell. We can cite summary fields: n_cells_tested 67 vs n_cells_dsr_scored 66; page G4 claims DSR gate across tested cells. This is a discrepancy: one tested cell has no DSR, so the "every gate" claim cannot hold for all 67. But maybe one cell insufficient_n not tested? n_cells_tested 67, n_cells_dsr_scored 66. The page headline says 67 tested cells survive every gate (0). It doesn't say all have DSR. G4 says DSR using n_trials = tested cells. The provenance table includes "cells scored with DSR" from d.provenance.n_cells_scored_with_dsr. The ledger provenance not provided. Could flag as unreconciled: 67 tested vs 66 DSR-scored; page renders DSR per cell and a G4 gate, but no note that one tested cell has no DSR. Consequence moderate. Need exact text: audit3_ledger summary `"n_cells_tested": 67`, `"n_cells_dsr_scored": 66`; audit3.html G4: `Deflated Sharpe ≥ ${conv.dsr_threshold} using n_trials = tested cells.` and cell column `{key:'dsr', label:'DSR', render:r=>...}`. This is a real inconsistency? It could be that DSR not computable for one cell due insufficient data. But page should disclose. The prompt asks "cells marked tested without a DSR" — exactly. We can report: one of 67 tested cells lacks DSR; the page has no caveat and still counts it in the multiplicity denominator (n_trials = tested cells). File audit3_ledger summary. Good.

Another: Summary counts by verdict: n_proven 0 + n_candidate 0 + n_weak 59 + n_kill 8 + n_insufficient 295 = 362. That equals n_cells_total 362. Good. But n_cells_tested 67. Which verdicts count as tested? If tested = n ≥ floor? 362 total, 295 insufficient, so 67 non-insufficient = 0+0+59+8=67. Perfect. So tested cells are the 67 with verdict not INSUFFICIENT_N. One lacks DSR. Could be a KILL/WEAK cell. Can't name.

Class counts: n_kill_classes 2, n_proven_classes 0. Page classes table can show. No class data provided.

Symbol counts: n_symbol_cells 69, n_kill_symbols 11, n_weak_symbols 58, n_proven_symbols 0, n_candidate_symbols 0. Sum 11+58=69. Good. No insufficient symbols? n_symbol_cells 69 and only kill/weak/proven/candidate. Fine.

Potential defect: Page subline says `${s.n_kill} strategies and ${s.n_kill_symbols} symbol cells killed.` Summary n_kill 8, n_kill_symbols 11. But kill_tribunal kills length? Not provided. The tribunalSub uses kills.length, not s.n_kill. Could be mismatch if kill_tribunal includes scopes beyond strategy/symbol/segment/class. The ledger excerpt doesn't include kill_tribunal. Can't cite.

Potential defect: coverage statement says "The other 7,603 are not in this ledger: the publishing dashboard reports 7,508 integrity-excluded and 9,176 auto-expired rows". But 7508+9176=16684, greater than 7603. It explicitly says overlap. Fine. However "no surface scores any of them" — is that a claim with no data? It says dashboard reports. Maybe okay.

But there is a more concrete contradiction: `total_resolved`: 8769 and `valid_closed_picks`: 7942. Coverage statement says "8,769 of 16,372 closed picks". It calls total_closed_picks "closed picks". But total_resolved 8769. Fine.

`scored_share_of_total_pct`: 53.56. 8769/16372 = 53.56%. Good.

`scored_share_of_valid_note`: "not comparable: the scored rows come from the canonical view while valid_closed_picks comes from the payload summary, so the ratio exceeded 100% (110.41%)". The page never displays this note. It does display `sharePct` as 53.56 and labels "of the closed book". That's accurate. No defect.

But the page's `covKpis` "Judged here" uses `sharePct+'% of the closed book'`. It doesn't show that `valid_closed_picks` is 7,942; not necessary.

Potential defect: `coverage.window.first_closed_at` is `"2026-02-17 15:13:13 EST"` while last is ISO Z. Page `covNote` uses `stamp(cov.window.first_closed_at)`; JS Date parsing of "2026-02-17 15:13:13 EST" is implementation-dependent and may return Invalid Date. The `stamp` function:
```
const stamp = (iso) => { try{ return new Date(iso).toUTCString().replace('GMT','UTC'); }catch(e){ return iso; } };
```
`new Date("2026-02-17 15:13:13 EST")` in many browsers returns Invalid Date; `toUTCString()` returns "Invalid Date" (doesn't throw). So it would display "Scored window: Invalid Date → Fri, 20 Nov 2026 00:40:53 UTC." That's a concrete defect: mixed timestamp format not parseable reliably. File audit3_ledger coverage.window.first_closed_at exact text. Consequence low/moderate. But operator asked concrete defects. Could mention.

Also `generated_at` is ISO with +00:00, stamp works.

Potential defect: `selection_alpha.overall.alpha_ci` is [-0.5029, -0.0178], alpha_pct -0.2681. Page alphaCell displays alpha_pct and CI. Fine. But `alpha_annualized_pct`: -907.0513 is absurd; page does not display annualized. No issue.

Potential defect: selection alpha `covered`: 3162, `n_universe`: 3500. It says "3,162/3,500 picks priced". But `overall.n` is 3162. Fine.

Potential defect: `min_hold_participation`: 0.5161. Not shown. Fine.

Potential defect: `alpha_pct_min_hold`: -0.1157. Not shown. Fine.

Potential defect: `hold_net_pct`: 0.0444 positive, pick_net_pct -0.2237. Alpha = -0.2681. Correct arithmetic: -0.2237 - 0.0444 = -0.2681. Good.

Potential defect: Page says "Positive means the pick beat the hold; negative means it lost to doing nothing." But hold_net_pct is +0.0444, pick negative, alpha negative. Correct.

Potential defect: Page says "PF and gross/trade are demoted ... because they score how the exit was expressed, not whether the right instrument was picked." That's prose, not audit.

Potential defect: `n_cells_dsr_scored` 66 vs n_cells_tested 67. Also page provenance table includes `{k:'cells scored with DSR', v:(d.provenance||{}).n_cells_scored_with_dsr}`. The ledger excerpt has summary n_cells_dsr_scored but not provenance. If provenance absent, displays undefined? Actually esc(undefined) -> ''. The table would show blank. But not necessarily defect.

Potential defect: Forward gate "hypotheses" H-119 has n_forward 430, min_n 100, but eligible false. Page fwdHypTbl lists H-119 with pct = 430%? `pct: v.min_n ? Math.round(100*(v.n_forward||0)/v.min_n) : null` => 430%. It labels "Progress" and displays 430%. That's a metric shown as progress exceeding 100%, while eligible false. Is that a defect? It can exceed 100 because n_forward > min_n; progress percentage >100 is odd but not false. It might be okay to show 430% as progress? It is not capped. Could be "denominators that mix scopes": H-119 has 430 forward rows, min_n 100, so 430%. But eligibility also requires PF CI-LB >1 and IR ≥0.5 and benchmark coverage. The page shows progress 430% and Eligible no, with reasons. Not a contradiction. Could be misleading but has reason.

Potential defect: `fwdKpis` "Fingerprint" value is long hex, in KPI value styled 24px mono; not defect.

Potential defect: `fwdSub` says "Rows are counted only from each pod's registration date, so a pod cannot inherit pre-registration history." But H-119 is a hypothesis, not a pod, and has 430 rows; pods all 0. The statement is about pods. Fine.

Potential defect: G8 gate text says "a pod reaches PROVEN_T2 only on its own rows closed after registration (9 pods tracked)." But forward_gate.rule in ledger begins "a pod's cell reaches PROVEN_T2 only when its own forward rows (closed on/after registered_at) clear: n>=100, net PF CI-LB > 1.0" and is truncated in provided data. Page fwdRule uses fg.rule. Fine.

Potential defect: The page fetches `audit3_evidence.json` before ledger. If evidence fetch fails, it writes to evSub. Then ledger fetch. Not relevant.

Potential dead links? No external links except none. Fetch links are relative artifacts. audit3_evidence.json not provided; but page says weekly workflow writes it. Cannot verify. The prompt says stale or missing artifacts. We have only ledger partial. Could mention evidence registry artifact is fetched but not in provided data? But we can't know if published. The page has fallback. Not a defect.

Potential defect: `table` function when rows empty sets innerHTML to `<tbody>...` without thead. Fine.

Potential defect: `renderCells` filters by `c.n>=minN` default 20. But `n` could be string? likely number. Fine.

Potential defect: `renderSymbols` does not filter n≥20 despite section heading "Symbol × direction cells (n ≥ 20)". It filters class, verdict, search only. In contrast cells has min n input. The section title says n ≥ 20, but the code does not enforce n ≥ 20. If DATA.symbols includes cells with n<20, they'd be shown. The ledger summary says n_symbol_cells 69. It doesn't say all n≥20. This is a concrete defect in the page: heading claims n ≥ 20 but `renderSymbols()` lacks an n filter. Cite audit3.html: `<h3>Symbol × direction cells (n ≥ 20)</h3>` and function:
```
const rows = DATA.symbols.filter(c =>
    (!cls || c.asset_class===cls) && (!vd || c.verdict===vd) &&
    (!q || c.symbol.toLowerCase().includes(q)));
```
No `c.n>=20`. Consequence: can display cells below the stated sample floor, contradicting the heading. Good.

Potential defect: `renderCells` counts `rows.length` but table sorts; fine.

Potential defect: `table` sort numeric null handling. Not relevant.

Potential defect: The page's KPI "Proven harmful" uses `s.n_kill` = 8. Label "Proven harmful" could be misleading because n_kill is strategies? summary_scope says n_proven/n_candidate count strategy cells only; n_kill maybe not specified. But "Proven harmful" = KILL count 8, and "Symbol kills" 11. Fine.

Potential defect: "Kill rate" = kill_rate_pct 11.94 but denominator is tested cells (67), not total cells (362). The KPI is displayed next to "Tested cells" and "Proven T2"; no label of denominator. If an operator reads kill rate as share of all strategy cells, 8/362=2.21%. The ledger's kill_rate_pct is 11.94 = 8/67. The page does not state the denominator. This is a "denominators that changed" / metric cannot be interpreted. Is it a concrete defect? The page says in subline "0 of 67 tested cells survive" and KPI kill rate 11.94%. It might be inferable. But the KPI "Kill rate" with no denominator is ambiguous. However ledger kill_rate_pct itself is 11.94. The page just renders. Could flag as denominator mismatch: kill rate uses tested cells while coverage "judged" uses closed picks. But not contradiction.

Potential defect: Summary `n_cells_total` 362, `n_cells_tested` 67. Page headline uses tested=67 but subline says "362 strategy cells (67 with n ≥ wr_floor_n)". Good.

Potential defect: `n_rows` 8769 closed picks, but coverage `total_resolved` 8769. Good.

Potential defect: The hero subline says "every p-value is one-sided and BH-corrected across all 67 tests." But the method says BH runs within two separate families: confirmatory and discovery. Summary has n_confirmatory_cells 8, n_discovery_cells 354. If BH is run within two separate families, saying "across all 67 tests" contradicts the method text. This is a strong concrete contradiction within page/ledger. Let's examine.

Subline:
```
Win is defined net of per-class slippage; every p-value is one-sided and BH-corrected across all ${tested} tests.
```
Method details:
```
Benjamini–Hochberg runs within two separate families. Confirmatory cells ... discovery cells ...
```
Ledger summary has n_confirmatory_cells 8, n_discovery_cells 354. So BH is not across all 67 tests if it runs within two families. Even if only 67 tested, the families split. The page itself contradicts. Cite exact text. Consequence: multiplicity correction claim wrong; q-values cannot be interpreted as FDR across all tests. Good. Also G3 says "Benjamini–Hochberg q ≤ fdr_q across every tested cell" — contradicts method "within two separate families." That's another exact text. We can report as one defect: the page claims BH across all tested cells in hero subline and G3, while Method says BH runs within two separate families; ledger summary records 8 confirmatory and 354 discovery cells. This is a contradiction. Rank high because multiplicity is central.

Potential defect: `n_confirmatory_cells` 8 + `n_discovery_cells` 354 = 362 total, not 67 tested. The method says BH within two families; family sizes are total cells not tested? It says confirmatory cells match pod, discovery everything else. The counts are all cells. But BH across tested cells within each family. Still contradiction with "across all tested tests."

Potential defect: G4 says "using n_trials = tested cells" (67) but n_cells_dsr_scored 66. Already noted. Also if BH within two families, DSR n_trials maybe all tested. Fine.

Potential defect: `n_cells_tested` 67 but `n_cells_dsr_scored` 66. G4 requires DSR for every tested cell. One missing. High-ish.

Potential defect: `n_candidate` 0 but `n_candidate_symbols` 0. Page KPI Candidate 0. Fine.

Potential defect: `n_weak` 59 strategy cells, `n_weak_symbols` 58. Page subline says `${s.n_weak} keep observing` but doesn't mention weak symbols. Fine.

Potential defect: `n_kill` 8 strategies and `n_kill_symbols` 11 symbol cells killed. But `kill_rate_pct` 11.94 = 8/67. The KPI "Kill rate" uses strategy kills only, not symbol kills. The page displays "Symbol kills 11" separately. No contradiction.

Potential defect: The `hero` headline says `<span class="${s.n_proven? 'ok':'bad'}">${s.n_proven}</span> of ${tested} tested cells survive every gate`. With n_proven 0, class bad. Fine.

Potential defect: `n_proven` counts strategy cells only per summary_scope, but headline says "tested cells" generically. It says "0 of 67 tested cells survive every gate" — but n_proven counts strategy cells only. Since tested=67 strategy cells? n_cells_tested likely strategy cells. Fine.

Potential defect: `n_cells_total` 362 strategy cells, n_symbol_cells 69. Page in method "Proven cells with no registered hypothesis" uses h.untested_strategies. Fine.

Potential defect: Coverage statement says "audit3 scores 8,769 of 16,372 closed picks (53.6%)." But `total_closed_picks` 16372 and `valid_closed_picks` 7942. The phrase "closed picks" is okay. However `scored_rows` 8769 > `valid_closed_picks` 7942. The page's coverage KPI "Judged here 53.56% of the closed book" uses total. It doesn't show valid. The note in ledger says ratio exceeded 100% against valid. Could flag: the page never surfaces that scored rows exceed valid_closed_picks (110.41%), and the coverage block contradicts itself? It says `scored_share_of_valid_pct_status`: "not_comparable". The page does not render it. Is omission a defect? The prompt: "any claim the coverage block contradicts." The coverage statement says "8,769 of 16,372 closed picks" — no contradiction. The `valid_closed_picks` 7942 is lower than scored rows; but the ledger says not comparable. The page doesn't claim otherwise. Not a defect unless the operator needs it. Could mention as denominator mixing scopes? The coverage block itself includes both denominators; page only shows total. But not a contradiction.

Potential defect: `excluded_cohorts` integrity_excluded 7508 and auto_expired 9176; `unscored_rows` 7603. The page covRows table lists these cohorts. A skeptical operator might see "Not scored here 7,603" and table rows 7,508 + 9,176, which sum to 16,684. The page covNote includes "The excluded cohorts overlap each other, so their counts do not add up to the unscored gap." So it's addressed. Good.

Potential defect: `resolver_anomalies.expired_zero_pnl_rows` 3530. These are "rows affected" in covRows. But auto_expired cohort 9176. Overlap? The page adds resolver anomalies as covRows with reason "resolver anomaly reported by the publishing dashboard (rows affected)". It doesn't say these overlap with excluded cohorts. cov.cohorts_overlap true only for excluded cohorts, not resolver anomalies. Could double-count in the table. But table is not a partition; it's reasons. The covNote says excluded cohorts overlap; not anomalies. Minor.

Potential defect: `closed_rows_missing_closed_at` 3. The page's coverage window uses first/last closed_at. If 3 closed rows missing closed_at, window may be incomplete. Not a contradiction. Could mention data integrity but not page defect.

Potential defect: `stale_exit_beyond_planned_stop` 44. Not shown? covRows includes resolver anomalies all numeric >0: clamped_loss_rows 23, closed_rows_missing_closed_at 3, expired_zero_pnl_rows 3530, rows_scanned 25548, stale_exit_beyond_planned_stop 44. It includes `rows_scanned` as a cohort/anomaly row with n=25548 and reason "resolver anomaly reported..." That's a defect: `rows_scanned` is not an anomaly count; it's the denominator of rows scanned. The page loops over all resolver_anomalies entries and pushes every numeric >0 into covRows:
```
Object.entries(cov.resolver_anomalies||{}).forEach(([k,v])=>{
    if(typeof v==='number' && v>0) covRows.push({cohort:k, n:v,
      why:'resolver anomaly reported by the publishing dashboard (rows affected)'});
});
```
So it will render a row "rows_scanned 25,548" with why "rows affected", which is false: rows_scanned is the total scanned, not affected. This is a concrete defect. Cite audit3.html code and ledger `resolver_anomalies.rows_scanned: 25548`. Consequence: inflates the anomaly table with a non-anomaly and mislabels it as affected rows. Good. Also `expired_zero_pnl_rows` 3530 is an anomaly? It is rows affected. Fine. `rows_scanned` is denominator. This is exactly "denominators that mix scopes" maybe.

Potential defect: `coverage.denominator.canonical_excluded_by_reason` has invalid_row 7394, mirror_duplicate 95, non_performance_exit 43, resolver_breakeven_fallback 71. Sum = 7603? 7394+95=7489; +43=7532; +71=7603. Exactly unscored_rows. Interesting! The excluded cohorts (7508+9176) don't sum, but canonical excluded by reason sums to 7603. The page does not render `canonical_excluded_by_reason` at all. It renders excluded_cohorts and resolver anomalies. The coverage statement says "The other 7,603 are not in this ledger: the publishing dashboard reports 7,508 integrity-excluded and 9,176 auto-expired rows... Those cohorts overlap, so they do not sum to the gap." But the ledger actually has a partition of the gap: `canonical_excluded_by_reason` sums exactly to 7603. The page omits it. Is that a defect? The statement says "read them as reasons rows are missing, not as a partition" — but there is a partition in the denominator data. It doesn't claim no partition exists, just that those cohorts are not a partition. However the page's coverage table is less informative than the ledger. The prompt asks concrete defects: missing artifacts? Not exactly. Could flag: the coverage block's stated gap of 7,603 has an exact partition in `coverage.denominator.canonical_excluded_by_reason` (invalid_row 7394, mirror_duplicate 95, non_performance_exit 43, resolver_breakeven_fallback 71) that the page never renders, while it renders the overlapping dashboard cohorts instead. This is a real omission: operator sees overlapping reasons but not the canonical partition. But is it a "defect" or improvement? It is a missing data artifact / claim. The statement says "The other 7,603 are not in this ledger" — but their exclusion reasons are in the ledger. It says "the publishing dashboard reports..." — okay. The canonical partition is in ledger. Could report as "coverage display omits the only non-overlapping breakdown of the 7,603 gap." Consequence moderate. Need be careful not to overstate as contradiction. The prompt: "denominators that changed" and "claims with no data behind them". The claim "Those cohorts overlap, so they do not sum to the gap" is true, but there is data that does sum. Not a contradiction. But the operator asked review page against ledger. A concrete defect: page renders `excluded_cohorts` and `resolver_anomalies` but not `denominator.canonical_excluded_by_reason`; the coverage table therefore cannot reconcile 8,769 kept + 7,603 excluded = 16,372. Actually it can: 8769+7603=16372. But reasons not partition. Hmm.

Potential defect: `coverage.denominator.canonical_excluded_by_reason.invalid_row` 7394 vs `excluded_cohorts.integrity_excluded` 7508. Different scopes. The page says integrity-excluded 7508. The canonical invalid_row 7394. The difference 114. Could be mirror duplicates etc. Not shown. If operator tries to reconcile, confusing. But page notes overlap.

Potential defect: `coverage.total_resolved` 8769 but `valid_closed_picks` 7942. The page's "Scored rows" 8,769 and "Published closed picks" 16,372. It never shows valid 7,942. The ledger's `scored_share_of_valid_note` says the ratio exceeded 100% (110.41%). A skeptical operator would want to know that scored rows exceed "valid closed picks" by 827. The page omits this. Is it a defect? The coverage block has a field specifically warning not comparable. The page's coverage KPI "Judged here 53.56% of the closed book" is fine. But the page also in provenance table: `{k:'share of closed book judged', v: sharePct...}`. No valid. Could report as "the page suppresses the one denominator that is not comparable; an operator cannot see that 8,769 scored rows exceed 7,942 valid_closed_picks." Consequence: hides a scope mismatch. But the prompt asks concrete defects only, not omissions of every field. This is a denominator mixing scopes: scored rows come from canonical view, valid_closed_picks from payload summary. The page doesn't mix them. It avoids. So not a defect.

Potential defect: The method section says "BH runs within two separate families" but the subline says "across all 67 tests." Strong.

Potential defect: The method section says "Confirmatory cells match a pod declared in reports/audit3_confirmatory.json before its forward data existed; discovery cells are everything else and top out at CANDIDATE." But the forward gate has pods registered 2026-11-19 and ledger generated 2026-11-20. Confirmatory cells 8. Not verifiable.

Potential defect: The page's G0 says "n ≥ wr_floor_n for any verdict, n ≥ proven_min_n for PROVEN." But summary has n_insufficient 295 with n_cells_total 362. That means 295 cells below floor? Maybe. If any verdict requires n≥floor, INSUFFICIENT_N is a verdict? G0 says "for any verdict" but INSUFFICIENT_N is a verdict for below floor. Contradiction: INSUFFICIENT_N is a verdict, yet G0 says n ≥ floor for any verdict. But it's a non-verdict/placeholder. The legend says INSUFFICIENT_N. Could be semantic. Not strong.

Potential defect: The page's `verdictLegend` says "KILL now needs a net-expectancy CI entirely below zero and BH harm q ≤ conv.fdr_q." The tribunalSub says kills "with a net-expectancy CI entirely below zero that also survived BH harm correction." But summary n_kill 8 and n_harmful_segments 2. Fine.

Potential defect: `n_kill_classes` 2 but `n_proven_classes` 0. The classes table can show KILL class. No data.

Potential defect: `n_positive_segments` 0, but segSub says `${segs.length} reconstructed section cells, positive net expectancy first. ${(s.n_positive_segments||0)} have a net 95% CI entirely above zero.` If segs length 6 and n_positive_segments 0. Fine. But `segs` sorted by net_expectancy_pct descending; "positive net expectancy first" only if sortKey net_expectancy_pct dir -1. Yes. If no positive, still.

Potential defect: `n_harmful_segments` 2. The tribunalSub says kills include segments and class aggregates. But summary n_kill 8 strategy, n_kill_symbols 11, n_kill_classes 2, n_harmful_segments 2. Total kill entries could be 8+11+2+2=23. The page's `kills.length` is used for tribunalSub. Not provided. If kill_tribunal.kills length differs, cannot audit. But we can note the page's subline "8 strategies and 11 symbol cells killed" omits 2 class aggregates and 2 harmful segments that the summary counts. It says `${s.n_kill} strategies and ${s.n_kill_symbols} symbol cells killed.` It doesn't mention classes/segments. The tribunal tab says entries include strategies, symbols, segments and class aggregates. The hero subline only reports strategies and symbol cells. Is that a defect? It underreports kills. The summary has n_kill_classes 2 and n_harmful_segments 2. The page's headline/subline only mention 8 strategies and 11 symbol cells. An operator could think 19 kills total, while there are also 2 class aggregates and 2 segments. This is a concrete omission in the summary line. But not a contradiction; it's incomplete. Could report as "kill counts cannot be reconciled": n_kill 8 + n_kill_symbols 11 + n_kill_classes 2 + n_harmful_segments 2 = 23, but subline presents only 8+11. The tribunalSub uses kills.length. If kills.length includes all, then hero and tribunal can disagree. Since kill_tribunal not provided, we can say the hero subline omits the class and segment kills that summary records. Consequence moderate. Need exact text.

Potential defect: `n_kill` label "Proven harmful" in KPI. It uses n_kill 8. But `n_harmful_segments` 2 and n_kill_classes 2. The KPI "Proven harmful" is not scoped; ambiguous. Could mention.

Potential defect: `n_candidate` 0, `n_proven` 0, but `n_weak` 59. The headline "0 of 67 tested cells survive every gate" — 59 WEAK are tested but don't survive every gate; okay. But "survive every gate" could be read as they failed; legend says WEAK is "no claim yet — keep observing", not failed. The headline uses "bad" class for 0. It says "0 of 67 tested cells survive every gate" which is accurate for PROVEN. But it may contradict doctrine "innocent until proven guilty" by framing 0 survivors. Not a concrete data defect.

Potential defect: `kill_rate_pct` 11.94 computed from n_kill/n_cells_tested. But if n_cells_tested includes 67 and n_kill 8, okay. The page labels "Kill rate" red. If the denominator is tested cells, it's not stated. Could be minor.

Potential defect: `selection_alpha` available true, but the page's `alphaNote` says "3,162/3,500 picks priced" — `covered` is picks priced, `n_universe` picks universe. Good. But `overall.n` is 3162. Fine.

Potential defect: `selection_alpha.source` is "alpha_engine/audit3_selection_alpha.py (needs the price tables)" and page provenance says `selection alpha: joined from ${sa.source}`. It will display "joined from alpha_engine/audit3_selection_alpha.py (needs the price tables)" even though available true. That's awkward: "joined from ... (needs the price tables)" implies not computed. But not a factual contradiction? It is available. Could be a defect: provenance says "joined from" a source that "needs the price tables", while alphaNote says it was computed. Minor.

Potential defect: `generated_at` 2026-11-20T01:57:23 vs `source_generated_at` 2026-11-20T01:17:09. Page stamp shows ledger built and source data. Fine.

Potential defect: `forward_gate.fingerprint` 5771c6fac172ca46. Page escapes. Fine.

Potential defect: `forward_gate.rule` in ledger is truncated in prompt: `"rule": "a pod's cell reaches PROVEN_T2 only when its own forward rows (closed on/after registered_at) clear: n>=100, net PF CI-LB > 1.0` — no closing quote. Probably truncated for brevity. Cannot audit missing criteria (IR, benchmark coverage). The pod reasons include "net PF CI-LB 0.9213 <= 1.0 and IR 0.043 < 0.5" and "benchmark_leg_ret coverage 80% < 90%". The rule text shown in ledger only mentions n>=100 and net PF CI-LB >1.0, but eligibility also requires IR ≥0.5 and benchmark coverage ≥90%. The page's G8 gate text says "a pod reaches PROVEN_T2 only on its own rows closed after registration" but doesn't list criteria. The `fwdRule` displays fg.rule, which as given omits IR and benchmark coverage. This is a contradiction: H-119 is ineligible partly because IR 0.043 < 0.5 and benchmark coverage 80% < 90%, but the stated rule only says n>=100 and PF CI-LB >1.0. If the full rule actually includes those, the provided ledger rule is incomplete/truncated. We can cite exact: `forward_gate.rule` text vs `forward_gate.hypotheses["H-119"].reasons`. Is this a page defect? The page displays rule, and reasons. The operator sees a reason not in rule. That's a concrete contradiction between fields in the ledger as rendered. But the rule string may be truncated in the prompt (no closing quote). We should be cautious: the data snippet may be truncated by the user. But it's presented as ledger. We can say "as published, the rule string stops at PF CI-LB and does not state the IR or benchmark-coverage conditions that the H-119 reasons enforce." This is a real audit finding if not truncated. Consequence: promotion criteria not fully declared. However the prompt says "Report concrete defects only". We can include with caveat? Avoid speculative.

Potential defect: `H-119` has `n_forward` 430 and `min_n` 100, so n gate passes, PF CI-LB 0.9213 fails, IR 0.0429 fails, benchmark coverage 0.798 fails. The page fwdHypTbl shows `pct` 430% progress and Eligible no. It doesn't show PF CI-LB, IR, benchmark coverage columns, only reason string. The reason includes them. Fine.

Potential defect: `pods` all have n_forward 0, but `forward_gate.n_rows` 430. The page fwdSub says "430 forward rows in the ledger · 9 pods · 0 eligible". That's consistent but reveals all 430 rows belong to H-119, not any pod. The page's G8 says "a pod reaches PROVEN_T2 only on its own rows ... (9 pods tracked)." Since no pod has rows, no pod can promote. Fine.

Potential defect: In `renderForward`, `podRows` includes `hypothesis: v.hypothesis_id || (v.pod||'')`. For POD-EQUITY-BREAKOUT, status pre_registered, no promotion_blocked_by_status. Fine.

Potential defect: `fwdSub` says `${eligible} eligible to promote` where eligible counts podRows only, not hypothesis rows. H-119 is a hypothesis, not pod, and is ineligible. If a hypothesis were eligible, it wouldn't count. Minor.

Potential defect: `fwdKpis` "Pods tracked" 9, but hypotheses H-119 is not a pod. Fine.

Potential defect: The page's `table` function sets `th` click handlers; for `fwdPodTbl` and `fwdHypTbl` columns include `key:'pct'` etc. Fine.

Potential defect: `renderEvidence` uses `s.n_records` etc from `d.summary` of evidence JSON, not ledger. Can't audit.

Potential defect: The page fetches evidence first, then ledger. If evidence JSON missing, evSub fallback. Not dead link.

Potential defect: The HTML `<div class="note" id="disclaimer"></div>` gets `d.not_money_ready_disclaimer`. The ledger excerpt doesn't include it. If missing, blank. Not a defect in provided excerpt? Could be missing artifact. But we don't know full ledger.

Potential defect: `conventions` not in ledger excerpt. Many values rely on it. If missing, `conv.wr_floor_n` etc undefined; subline would say "n ≥ undefined". But the ledger likely has it. We only have summary/coverage/selection_alpha. Cannot audit. The user says "page against the ledger it reads" but provided only partial ledger. We should review what's given. Avoid claiming missing conventions.

Potential defect: `d.cells` etc not provided. Can't audit cells marked tested without DSR except summary counts.

Potential defect: `n_cells_tested` 67 but `n_cells_dsr_scored` 66. This is directly in provided summary. Good.

Potential defect: `n_confirmatory_cells` 8 and `n_discovery_cells` 354 sum 362, but `n_cells_tested` 67. The page method says BH within two families. If confirmatory family has 8 cells total, maybe only some tested. The page's G3 says "across every tested cell" — contradiction. Good.

Potential defect: The page says "every p-value is one-sided and BH-corrected across all 67 tests." But `n_cells_tested` 67 includes 8 KILL and 59 WEAK. BH q for KILL harm? The tribunalSub says "BH harm correction" — separate from edge BH? The page says "BH-corrected across all tests" but kills use "BH harm q". Is there one BH or two? The method says two families (confirmatory/discovery). The tribunal says BH harm. The summary has n_kill 8. Could be multiple testing corrections: edge q and harm q. The page's subline oversimplifies. We can mention the two-family contradiction, enough.

Potential defect: `n_cells_dsr_scored` 66 vs `n_cells_tested` 67, and `n_cells_total` 362. The page's G4 uses n_trials = tested cells (67) for DSR. But DSR was computed for 66. If n_trials is 67 but only 66 scored, the DSR threshold is applied to 66 values; one cell cannot have DSR. This is a metric cannot be computed as shown. Good.

Potential defect: `kill_rate_pct` 11.94. Let's compute if denominator n_cells_tested=67. 8/67=11.94. If denominator n_cells_total=362, 2.21. If denominator non-insufficient? same 67. Page displays "Kill rate 11.94%" but the KPI grid also displays "Tested cells 67" and "Proven harmful 8". It doesn't label denominator. Is 11.94 a "kill rate" of what? Of tested strategy cells. The page's subline says "8 strategies ... killed" and "0 of 67 tested cells survive". The operator can infer. Maybe not a defect. But the prompt specifically "denominators that mix scopes". The kill rate is strategy cells, while "Symbol kills" 11 and "Proven harmful" 8. The kill rate excludes symbol kills. The label "Kill rate" might be read as overall. But summary provides kill_rate_pct; page doesn't compute. Hmm.

Potential defect: `n_kill_symbols` 11, `n_symbol_cells` 69. If one computed symbol kill rate, 15.94%. The page shows "Symbol kills 11" but no rate. Fine.

Potential defect: `n_weak_symbols` 58 + n_kill_symbols 11 = 69. All symbol cells are either weak or kill. No proven/candidate. The page subline says "8 strategies and 11 symbol cells killed. 59 keep observing" — it says 59 keep observing, which is strategy weak count, but 58 symbol cells also keep observing. It omits them. Minor.

Potential defect: The headline "0 of 67 tested cells survive every gate" while `n_weak` 59 "keep observing (no claim either way)". The word "survive" could imply the 59 failed, but they are not killed. The page's own legend says WEAK is not failed. This is a semantic contradiction: headline says only 0 survive, but 59 are WEAK (innocent). However "survive every gate" specifically means pass all gates to PROVEN, not survive as not-killed. It's accurate but potentially misleading. Not concrete enough.

Potential defect: `n_insufficient` 295; `n_cells_total` 362; `n_cells_tested` 67; 295+67=362. Good. The page filter min n default 20. `wr_floor_n` maybe 20. If `wr_floor_n` is not 20, the default filter could show cells below floor or hide. The page's cells filter default min n 20, but G0 says n ≥ conv.wr_floor_n. We don't know wr_floor_n from ledger. Could be 20. If different, defect. Can't assert.

Potential defect: `renderSymbols` heading n≥20 but no filter. Strong.

Potential defect: `renderCells` has min n filter, but `renderSymbols` doesn't. Strong.

Potential defect: `covRows` includes `rows_scanned` as anomaly. Strong.

Potential defect: `covNote` timestamp parse. Strong-ish.

Potential defect: `covNote` includes `d.persistence` etc not in ledger. Can't audit.

Potential defect: `covNote` uses `stamp(cov.window.first_closed_at)` where first is EST. The `stamp` function is defined later with `const stamp = ...` after event listeners. But `render(d)` is called after the fetch resolves, and `stamp` is a `const` declared at top-level before fetch? Actually in script order: functions, then event listeners, then `const stamp = ...`, then `renderEvidence`, then fetch. The fetch callbacks execute asynchronously after the whole script has run, so `stamp` is initialized. No TDZ issue. Fine.

Potential defect: `stamp` uses `.replace('GMT','UTC')`. For invalid date, `toUTCString()` returns "Invalid Date", no throw. So "Invalid Date" displayed. Good.

Potential defect: `cov.window.first_closed_at` "2026-02-17 15:13:13 EST" — in Node, `new Date("2026-02-17 15:13:13 EST")` may parse? V8 often parses "2026-02-17 15:13:13 EST" as local? Let's think. JavaScript Date parsing is implementation-dependent. In Chrome, "2026-02-17 15:13:13 EST" might parse as local time? Actually V8 parses "YYYY-MM-DD HH:mm:ss" as local, and "EST" may be ignored or invalid. It could parse. But not guaranteed. The page is static; operator browser. A concrete defect: mixing a non-ISO local timestamp with ISO Z in the same window object, passed to `new Date`, yields browser-dependent output. That's valid.

Potential defect: `cov.window.last_closed_at` "2026-11-20T00:40:53Z" is ISO. Page `stamp` outputs UTC. Good.

Potential defect: `generated_at` source timezone. Fine.

Potential defect: `selection_alpha.overall.alpha_ci` [-0.5029, -0.0178] excludes zero (both negative). The page class table shows alpha CI. But summary n_proven_classes 0. If a class had alpha CI entirely below zero, it might be KILL. No class data.

Potential defect: `selection_alpha.overall.alpha_pct` -0.2681, CI [-0.5029, -0.0178]. The page's `alphaCell` displays `<b>-0.27%</b> [-0.50, -0.02] n=3162`. Fine.

Potential defect: `alpha_annualized_pct` -907.0513 is nonsensical; if displayed? The page does not display it. No.

Potential defect: `alpha_per_day_pct` -2.4851. Not displayed. No.

Potential defect: `hold_days_mean` 5.319, median 1.0256. Not displayed. No.

Potential defect: The page's selection alpha note says "Positive means the pick beat the hold; negative means it lost to doing nothing." Actually holding the same instrument is not "doing nothing" exactly; but okay.

Potential defect: `n_universe` 3500 but `covered` 3162. The page says "3,162/3,500 picks priced". It doesn't mention 338 unpriced. Fine.

Potential defect: `bar_coverage` absent. The page code renders an empty table and no note. If the ledger lacks bar_coverage but selection_alpha available, no issue.

Potential defect: `s.n_rows.toLocaleString()` 8,769. Coverage says 8,769. Good.

Potential defect: `total_closed_picks` 16,372. Page "Published closed picks" 16,372. Good.

Potential defect: `unscored_rows` 7,603. Page "Not scored here" 7,603. Good.

Potential defect: `scored_share_of_total_pct` 53.56. Page "53.56% of the closed book". Good.

Potential defect: `statement` says "audit3 scores 8,

## subq_cross — `subq-savant-1.4`

## Contradictions across the three surfaces

**1. Five different populations for "closed picks."** This is the root defect.
- `/audit`: *"Where Our Edge Actually Is (Closed-Pick Data, n=4,618)"* and, in the same page, *"What Makes a Winner — Decile Test Results / 1,927 closed picks"*.
- `audit3_ledger.json → coverage`: `total_closed_picks: 16372`, `scored_rows: 8769`, `valid_closed_picks: 7942`.

The ledger itself flags the last pair as broken: `scored_share_of_valid_pct_status: "not_comparable"` with *"the ratio exceeded 100% (110.41%)"*. Scored rows can exceed "valid" picks only if `valid_closed_picks` is not the population the scored rows came from — which means the field is mislabeled and any rate divided by it is wrong. Meanwhile `/audit` quotes 4,618 and 1,927 with no stated scope. Any win rate, PF or kill rate across these surfaces is quotable at four different denominators.

**2. The forward evidence cannot promote anything, but reads as populated.** `audit3_ledger.json → forward_gate` reports `n_rows: 430` for H-119 with `net_pf: 1.1147`, while all nine pods show `n_forward: 0`, `pf_ci_lb: null`, and statuses `observe` (8) / `pre_registered` (1), each with `"since": "2026-11-19"`. The 430 rows exist; none are attributable to a pod. The section is headed *"The only pipeline that can promote anything"* — and per its own rule (`n>=100`, `net PF CI-LB > 1.0`), nothing can. The headline number and the promotable reality disagree.

**3. audit2 is a stale copy of audit3 with no fetch behind it.** `audit2` outline fetches nothing (`FETCHES:` is empty), yet it renders *"Verdicts (from audit3_ledger.json)"* and *"Per-class verdicts (reconciled against the canonical rollup)"*. Its forward block is `generated_at: 2026-11-19T08:41:27Z` — over a day behind audit3's `2026-11-20T01:57:23Z` — and lists `H-119: { n: 430, pods: [] }` while audit3 lists nine pods under the same forward ledger. It claims reconciliation it cannot perform, and it is missing the pod registry.

**4. Two zero-PnL counts, no stated scope split.** `coverage.zero_pnl_count: 134` (canonical kept) vs `resolver_anomalies.expired_zero_pnl_rows: 3530` (of `rows_scanned: 25548`). Same concept, 26× apart, neither field says which universe it describes.

**5. Stale dated section on `/audit`.** *"SUPREME EDGE 2026-05-12 refresh"* sits on a page whose sibling ledger was generated 2026-11-20 and whose window runs to 2026-11-20T00:40Z. A six-month-old refresh presented as current edge.

**6. Kill rate denominator is chosen, not given.** `kill_rate_pct: 11.94` = 8/67 (`n_kill` / `n_cells_tested`). Against `n_cells_total: 362` it is 2.2%. The 11.94 figure is not wrong, but it is the least favorable-looking framing available and nothing on the surface states which denominator produced it. Related: `n_kill_symbols: 11 > n_kill: 8` — more symbols killed than kill cells, pre-empted only by the prose `summary_scope` string, not by the data.

**7. Window endpoints are in different timezones.** `window.first_closed_at: "2026-02-17 15:13:13 EST"` vs `last_closed_at: "2026-11-20T00:40:53Z"`. Comparing or diffing them requires a conversion the field doesn't declare.

**8. Write surface on a read page.** `/audit` fetches `api.github.com/.../actions/workflows/audit-dashboard.yml/dispatches` and `.../momentum-scanner.yml/dispatches` — the dashboard can trigger the pipeline that produces it.

## Most trustworthy: audit3

It is the only surface that declares its own denominator, publishes a hash of the view it scored (`canonical_rows_sha256: 63609da5…`, `canonical_schema: audit.canonical.v1`), states what it does not score (*"What this ledger does not score"*), refuses to present a non-comparable ratio rather than printing 110.41%, and treats overlapping exclusion cohorts honestly: *"Those cohorts overlap, so they do not sum to the gap — read them as reasons rows are missing, not as a partition."* `/audit` mixes dated sections and unstated samples; audit2 asserts reconciliation with no data and is a day stale. audit3 is the only one whose numbers you can re-derive — which is exactly why its defects (items 2, 4, 6, 7) are the ones worth fixing.

## Single highest-leverage fix

**Make the denominator a shared, versioned artifact and force every surface to print it alongside any rate.** Today `/audit` (4,618 / 1,927), audit2 (via audit3's ledger) and audit3 (8,769 / 7,942 / 16,372) each pick their own population, and the ledger already proves the mismatch by producing a 110.41% ratio it has to suppress. Emit one sidecar — `{canonical_sha256, n_canonical, n_total_closed, exclusion_reasons[]}` — and require every percentage on all three pages to render as `x% (n / denominator, sha256 prefix)`. That single change kills items 1, 4, 6 and most of 3 at once, and makes item 2 visible rather than plausible: a forward gate with `n_forward: 0` per pod cannot hide behind a `n_rows: 430` headline.
