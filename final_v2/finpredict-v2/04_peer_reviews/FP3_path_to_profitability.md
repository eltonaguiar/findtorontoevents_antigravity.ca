# FP3 — Independent Review: `PLAN_PATH_TO_PROFITABILITY.md` + the quant remediation plan

**Verdict: FAIL** for `PLAN_PATH_TO_PROFITABILITY.md` — every one of its four promoted "verified edges" is either a mis-dated April artifact, a 25-row subset, or unreachable in every current dataset. **CONDITIONAL** for `updates/2026-11-14-quant-remediation-plan.md` — its premise (the system is not profitable) is correct and independently reproduced here, but it misses two defects that are larger than the ones it lists.

- Reviewer: FP3 (independent, read-only on repo source; the only file written is this review)
- Clock: 2026-11-14T20:20Z
- Under review: `PLAN_PATH_TO_PROFITABILITY.md` (129 lines, 2026-11-14), `updates/2026-11-14-quant-remediation-plan.md`, cross-checked against `updates/2026-11-14-quant-audit-multitest.md` and `updates/2026-11-14-edge-search-results.md`
- Data actually opened (read-only): live `https://findtorontoevents.ca/audit/data/dashboard_data.json` (25,247,161 B, `generated_at 2026-11-14T19:27:23Z`, fetched 20:17Z), `tools/data/snapshots/dashboard_data_2026-04-06T225846Z.json` (the snapshot the claims come from), `audit_trail/data/universal_resolved_picks.json`, `audit_dashboard/data/{pf_registry,pilot_verified_edges_shadow,bootstrap_verified_edges,walk_forward_per_strategy_latest}.json`, `quan_engine/data/quan_engine.db`, `data/live_picks.db`
- Code read: `audit_trail/quality_gates.py`, `strategies/source_quality_filter_v1.py`, `alpha_engine/{pilot_verified_edges,bootstrap_verified_edges}.py`
- Peer context: `2026-11-14/finpredict-v2_20261114-1602/MASTER_AUDIT.md`, `research/profitability/{SCORECARD.md,validation/VWAP_VERDICT.md}`, FP1/FP2/FP4 reviews in this folder

---

## 0. One-paragraph summary

The plan's numbers are not invented — they are **real, but from 2026-04-06, not November 2026**, and they are computed on a resolver whose loss tail is truncated. The string `95.8% WR, +669% PnL` maps to `dashboard_data_2026-04-06T225846Z.json → systems.quan_engine`: **292 closed, 280 W / 12 L, WR 95.9%, total +689.4%, PF 79.61, avg win +2.49%, avg loss −0.73%**. That is a seven-month-old snapshot of a strategy that today has **zero** resolved picks in the live payload and **40.7% WR / PF 1.17** in its own SQLite database. The 72.0%/20.3% direction split comes from a 25-row and a 64-row cell inside a 3,488-row ledger whose full-population direction split is the **opposite** (SHORT 31.6%, LONG 47.2%). Only the score-40-59 claim survives contact with today's data, and even it is not statistically significant (p = 0.124). The remediation plan is right that the system is not profitable; it is wrong to think the five defects it lists are the whole story — the two canonical ledgers disagree in **sign**, and one of them is built from fixed-ladder PnL.

---

## 1. Claim-by-claim verification

| # | Claim (as written in `PLAN_PATH_TO_PROFITABILITY.md`) | Where it actually comes from | Independent verification | Status |
|---|---|---|---|---|
| C1 | `quan_engine`: **95.8% WR, +669% PnL, 284 trades** — "Nov 2026 Reality" | `dashboard_data_2026-04-06T225846Z.json` → `systems.quan_engine` = 292 closed, 280W/12L, **95.9%**, **+689.4%**, PF **79.61** | Reproduced exactly in the **April 6** snapshot. Not in the November payload: `systems.quan_engine` = 0 closed / 0 resolved / 0 wins / WR 0.0. Its own DB (`quan_engine.db`, 255 signals, 2026-05-23→05-25 only): 216 closed, **WR 40.7%, PF 1.166, avg +0.127%, total +27.4%**. n is 292, not 284. | **ARTIFACT** (stale + truncated-loss resolver; label false) |
| C2 | `st_rsi_momentum_confluence`: **65.1% WR, PF 2.53, 258 trades** | "walk-forward validated edge" in `EDGE_FINDINGS_2026-04-06.md:183` | **Zero rows** in every ledger I can open: live `recent_closed` (3,500), `universal_resolved_picks.json` (4,498), `quan_engine.db`, `live_picks.db`. `walk_forward_validation.json` (the cited source) **does not exist**; `walk_forward_per_strategy_latest.json` has 7 cells, none of them this strategy. 258 is almost certainly walk-forward *windows*, not trades. | **UNVERIFIED** (unreproducible; source file absent) |
| C3 | **SHORT 72.0% WR vs LONG 20.3%** | `EDGE_FINDINGS_2026-04-06.md:88-93` — n=25 SHORT, n=64 LONG | These cells are **2.5% of the 3,488-row April ledger**. That same snapshot's full population: **SHORT 31.6% (n=307)**, **LONG 47.2% (n=3,181)** — reversed. Live Nov payload: SHORT **53.6%** (n=647), LONG **38.7%** (n=2,842). Second ledger (`universal_resolved_picks`): SHORT **46.9%** vs LONG **54.3%** — reversed again. Binomial p for the current SHORT cell = **0.070**. | **ARTIFACT** (subset + regime/beta) |
| C4 | **Score 40-59: 60.8% WR, +0.056% avg PnL** | `EDGE_FINDINGS_2026-04-06.md:27` — n=79 | April full snapshot: 40-59 bucket = **57.0%, n=823, +0.511%** (n=79 was a sub-subset). Live Nov payload: **54.4%, n=331, avg +0.644%, PF 1.737**, n_effective 263, positive in **8 of 10 months**, beats the rest-of-book in 8 of 10 months. But two-sided binomial **p = 0.124**; and `elite_score`↔PnL Pearson is **+0.013** across all 3,489 today (the +0.203 in the April doc is not reproducible). | **QUALITATIVELY REAL / QUANTITATIVELY WRONG** (directionally reproducible, not significant) |
| C5 | "Kill lists were built from **May 2026** data … `quan_engine` = '0% WR, blocked'" | `audit_trail/quality_gates.py:1446` | The block reason is **not** performance: `"quan_engine", # 2026-05-06 P0-B: 0 closed + 0 active — proactively blocked`. It was blocked for having **no data**, not for being 0% WR. `st_rsi_momentum_confluence` was blocked on genuine evidence (10W/95L, WR 10%, −296.5%, n=105) — text matches. Provenance is April–May, so "stale" is fair; the claimed May label is **falsified**. | **PARTLY TRUE / mis-stated** |
| C6 | TradingView winners, from **59K–107K contestant leaderboards** | No citation at all | No URL, dataset, date, author, or artifact anywhere in the repo; a scoped search for `59K`/`107K`/`contestant leaderboard` returns nothing. Directly contradicted by our own `research/profitability/SCORECARD.md` §"On TradingView contest winners": winners are "survivorship + multiple testing, not proof of a repeatable method." | **UNVERIFIED** (unsourced, and contradicted internally) |
| C7 | "Score-PnL correlation current **+0.008**" | `EDGE_FINDINGS...:15` | `+0.008` is **confidence**↔PnL. Actual `elite_score`↔PnL = +0.203 (April) → **+0.013** (today). Metric substitution. | **MISLABELLED** |

### 1.1 The 95.9% is a resolver artifact, not an edge

From the April snapshot, `systems.quan_engine` reports `avg_win 2.49`, `avg_loss −0.73`, PF `79.61`. A PF of 79.6 requires the *entire* loss distribution to be truncated at about −0.73% while wins pay +2.49%. Real crypto strategies do not have a 0.73% hard tail with a 95.9% hit rate; a first-touch resolver with TP checked before SL does. This is the same defect our peers already found independently ("`TP_HIT` 92.4% vs `SL_HIT` 4.5% — mathematically impossible … resolver checks TP before SL in close-price fallback", `audits/2026-11-14/finpredict-v4_.../INDEX.md`). Corroborating: all 4 `quan_engine` rows inside that snapshot's `recent_closed` have **`pnl_pct = 2.5`, `exit_reason = TP_HIT`, status `WON`** — a fixed ladder, not a price path.

The plan then proposes to **amplify this source 1.5×**, which is exactly backwards: it would up-weight the strategy whose reported number is the most obviously synthetic.

---

## 2. Selection / multiple-testing analysis

### 2.1 Denominators are the largest single defect (bigger than the audit's 3,378)

Live `summary` at 19:27Z:

| Field | Value |
|---|---:|
| `total_closed_picks` | 16,183 |
| `valid_closed_picks` / `headline_closed_unique` | **7,959** |
| `total_resolved` | 8,511 |
| `auto_expired_excluded` | **8,899 (55.0% of closed)** |
| `integrity_excluded` | 7,574 |
| `overall_win_rate` | 41.3% |
| `profit_factor` | 0.92 |
| `total_pnl_pct` (compounded) | −82.59% |
| `expectancy` | −0.14% |

Every headline WR in the plan is computed on the surviving 8,511 rows. The 8,899 expired-at-zero rows are precisely the slow-bleed outcomes that a high-WR strategy would produce most of. A 55% censoring rate can move a WR cell by tens of points; the plan's 95.9% cell cannot be evaluated at all until C1 lands.

### 2.2 The two canonical ledgers disagree in **sign**

| Ledger | Window | n | WR | PF | avg PnL |
|---|---|---:|---:|---:|---:|
| `picks.recent_closed` (live, Nov 14) | 2026-02-21 → 2026-11-14 | 3,489 | **41.4%** | **0.869** | **−0.177%** (Σ −617.5%) |
| `audit_trail/data/universal_resolved_picks.json` | 2026-05-31 → 2026-11-14 | 4,498 (3,420 priced) | **52.3%** | **1.793** | **+0.638%** (Σ +2,182%) |

ID overlap between them is **62 rows**. These are not two views of one book; they are two almost-disjoint books reaching opposite conclusions about whether the system makes money. This is a defect the remediation plan does not name, and it invalidates any single-ledger claim in either direction.

### 2.3 One of those ledgers is fabricated by construction

`universal_resolved_picks.json` contains **34 `(strategy, pnl)` cohorts with ≥10 identical values**, including:

- `unknown` → **−2.0 × 377**, **+3.5 × 228**
- `MeanReversionBB` → **3.0 × 110**, **3.5 × 92**
- `hs_lb_None` → 3.5 × 92; `luxalgo_confluence` → 3.5 × 62

Fixed +3.5/−2.0 ladders mechanically produce WR ≈ 52% and PF ≈ 1.79 regardless of market behaviour. That is the ledger the plan's own bootstrap was run against. By contrast, `recent_closed` is internally honest on this axis: **3,489/3,489 rows have PnL equal to price-derived PnL within 0.05pp**, and its TP/SL sides are correct for 3,489/3,489 and 3,451/3,489 respectively.

### 2.4 Pseudo-replication

- 416 `(symbol, direction, strategy, day)` duplicate groups covering **1,003 / 3,489 rows (28.7%)**, max 9 per group.
- Distinct 4-tuples: **2,902** → 16.8% raw-n inflation before any clustering by date.
- Top emitter: **48.9%** of all rows (`kimi_riseoftheclaw`, 1,706). Second: `luxalgo_filters` 1,265. Two emitters = 85% of the book.
- Score-40-59 bucket: 331 rows → **263 distinct 4-tuples** → the true n is ≈ 26% smaller than quoted.

### 2.5 Multiple testing is computed and then ignored

- `kill_switch`: **177 strategies**, only **56 evaluated**, 42 killed (75% of evaluated), 14 survivors. Criteria are crude: n≥30, WR≥45%, PF>1.0 — no DSR, no PBO, no FDR.
- `money_ready_verdicts`: `_fdr_gate_enforce = False` for **all 9 classes**; CRYPTO `NOT_READY`, `pbo = 0.0`.
- The four promoted cells were selected from ≥ 5 score buckets × 2 directions × 113 distinct strategies in the visible ledger (177 in the kill switch). Corrected thresholds:

| Claimed cell | n | observed WR | binomial p (H0=50%) | ×10 search correction |
|---|---:|---:|---:|---:|
| SHORT | 647 | 53.6% | 0.070 | **0.70** |
| Score 40-59 | 331 | 54.4% | 0.124 | **1.00** |
| LONG (the claimed loser) | 2,842 | 38.7% | <1e-30 | — (significant, but says the book loses) |

Neither promoted positive cell clears α = 0.05 even **uncorrected**. There is no cell in the plan that survives any multiple-testing correction.

### 2.6 Regime is not measurable, so the "regime change" story is unfalsifiable

- `regime_validation.data_coverage`: **21 / 16,183 rows carry a regime (0.1%)**; `closed_without_regime` = 8,588; `alignment_coverage_pct` = 0.0.
- `regime_validation.active_regime_composition.with_regime_data` = **0**.

The plan's root cause ("crypto entered a new volatility regime; the system never re-evaluated") cannot be tested with 0.1% coverage. What *can* be shown is that the direction edge flips by month — LONG WR 72.0% in April (n=168) vs 26.0% in November (n=605) — which is beta, not regime alpha.

### 2.7 PnL unit normalization

Not the driver here: neither current ledger shows dollar-scale values (max |PnL| 24.6% in `recent_closed`, 4.0% in `universal_resolved`). But the defect is real and documented in `pf_registry.json` (`futures_connors_rsi2`: `gross_profit = 19,081,667`, `PF = 613,777` from point-value PnL). Any aggregate that still includes the legacy registry can be dominated by it, and `pf_registry` is one of the bootstrap's JSON fallbacks. Unit normalization remains a live hazard for any PF quoted from registry-derived files.

---

## 3. Contradictions between the plan and its own evidence

1. **Date.** Plan says "Nov 2026 Reality." The numbers are byte-for-byte the **2026-04-06T20:11:17Z** snapshot. The plan asserts a seven-month regime change using data from before it.
2. **Existence.** Plan says `quan_engine` is a live profitable edge being "HARD BLOCKED." The live payload shows `quan_engine` with **0 active, 0 closed, 0 resolved, 0 wins**. You cannot block what is not emitting.
3. **Its own bootstrap.** `bootstrap_verified_edges.json` (19:10Z, 10,000 resamples) marks `quan_engine` **`INSUFFICIENT_N`, n=28** and `st_rsi_momentum_confluence` **`INSUFFICIENT_N`, n=0**. The plan's own P1 action #7 refutes its own P0 premise, and the "95.8%/284" edge is 28 rows (WR 32.1%, PF 1.22) when you look.
4. **Its own pilot.** Plan action #1: "Emits ONLY `quan_engine`, `st_rsi_momentum_confluence`, and SHORT-bias signals." The artifact (`pilot_verified_edges_shadow.json`) has **207 picks: 0 st_rsi, 2 quan_engine, and 205 other strategies** (`hs_lb_None` 58, `inverse_ml_enhanced_*` 127, `luxalgo_confluence` 15). It has **0 exit prices**, and its entry dates are **June–August 2026** (85 undated). It is not the pipeline the plan describes; it is a stale grab-bag relabelled as a pilot.
5. **Direction.** Plan proposes boosting SHORT +20%. The same April snapshot's full population had SHORT at 31.6% and LONG at 47.2%; a second ledger has SHORT at 46.9% and LONG at 54.3%. The "edge" changes sign with the ledger chosen.
6. **Implementation before review.** `da85a2d302a` (19:07:39Z) already moved `quan_engine` from `penalized_sources` (0.8×) to `amplified_sources` (**1.5×**) in `strategies/source_quality_filter_v1.py`, with the comment "regime change — quan_engine now 95.8% WR". `bf6a8e310ac` (19:16:20Z) then blocked `quan_engine_scalp`. Both were merged before this review, on evidence that does not survive inspection.
7. **Success metric.** Plan targets "score-PnL correlation **+0.008 → +0.3**." `+0.008` is the confidence metric; the score metric is +0.013 today. The baseline is misquoted, and the target is 23× the best value ever observed (+0.203).
8. **TradingView.** Plan recommends "specialize in ONE pattern per asset class" while its own risk table says "still run 100+ strategies in background." Both cannot be the strategy, and neither is supported by a sourced study.
9. **Remediation plan vs plan.** The remediation plan's premise — "3,489 resolved picks, WR 41.8%, binomial p = 1.00; 0/8 emitters significant" — matches my independent recompute (**41.4%, PF 0.869, Σ −617.5%**). The two documents cannot both be right; the remediation plan is the one that is.

---

## 4. TradingView "research" verification

| Requirement | Finding |
|---|---|
| Named source (URL, author, dataset, date) | **None.** No citation of any kind in the section. |
| Reproducible artifact in repo | **None.** No file contains `59K`, `107K`, or a contestant leaderboard extract. |
| Consistency with our own research | **Contradicted.** `research/profitability/SCORECARD.md` explicitly concludes contest winners are a survivorship + multiple-testing artifact and that such a method is not proof of a repeatable edge. |
| Internal consistency | Rules 1 and "run 100+ strategies in background" conflict; rules 2–5 (sizing, stops, loss caps) are generic risk management, not evidence of profitability. |

**Verdict: UNVERIFIED, and internally contradicted.** The section should not be used to justify any action.

---

## 5. Ranked actions

Ranking = impact × certainty ÷ effort, and it starts with undoing what was already merged.

| Rank | Action | Why this rank | Effort | Certainty |
|---:|---|---|---|---|
| **1** | **Revert `da85a2d302a`'s source-filter unblock; retract claims C1/C2/C3; keep the pilot shadow-only and drop the `verified` tag.** | The 1.5× amplification is live now, on a number that is an April resolver artifact. Nothing else matters until this stops. | ~0 | 1.00 |
| **2** | **C1 — make every pick terminate (`TP/SL/TIME/EXPIRED` + price + `closed_at`), count EXPIRED as a non-win.** | 8,899 uncounted rows (55% of closed) dominate every WR. This is the only fix that changes the answer rather than the display. | M | 1.00 |
| **3** | **NEW C0 — reconcile the two disjoint ledgers and purge fixed-ladder PnL cohorts.** | `recent_closed` (−617%) and `universal_resolved` (+2,182%) disagree in sign with 62 shared IDs. One ledger must be declared authoritative; 34 flat-PnL cohorts must be quarantined before any gate reads them. Not in the remediation plan. | M | 0.95 |
| **4** | **C3 — dedupe at write time, publish `n_raw` + `n_effective`.** | 28.7% of rows sit in duplicate groups; 48.9% of the book is one emitter. Necessary before any p-value is quotable. | L | 0.95 |
| **5** | **C2 — enforce `admit_strategy()`; delete `_fdr_gate_enforce=false`.** | Currently computed then ignored in all 9 classes. Highest value once the data under it is honest (ranks below C0/C1 for that reason). | M | 0.90 |
| **6** | **C4 — one ledger marked to market hourly.** | `current_price` null vs 0.0 is why the page is unauditable per pick. | H | 0.75 |
| **7** | **C5 — consolidate workflows; fix the scanner `KeyError: 'LONG'`.** | Diagnosability; does not change any number. | M | 0.85 |
| **8** | **Score 40-59 — re-test as a *pre-registered* shadow hypothesis only.** | The only claim with directional reproducibility (54.4%, PF 1.74, n=331, 8/10 months positive), but p=0.124 and n_effective 263. Needs ≥200 independent, BH-corrected, cost-inclusive. | L | 0.60 |
| **9** | **SHORT bias — do NOT ship as a +20% score boost.** If used at all, model it as an explicit market-beta/exposure decision benchmarked against a short-crypto index, because the "edge" flips sign by ledger and by month (LONG was 72% in April). | Fitting the last two months into a score constant is the exact error the audit describes. | L | 0.90 |
| **10** | **Regime routing (plan action #5) — defer until after C1.** | 0.1% regime coverage (21/16,183) means it cannot be validated today. | M | 0.80 |
| **11** | **TradingView methodology adoption — drop until sourced.** | Unsourced and contradicted by our own scorecard. | ~0 | 0.95 |

The remediation plan's four-week sequencing is otherwise sound, with one change: C0 (ledger reconciliation + flat-PnL quarantine) must run in **week 1**, in parallel with C5, because C1's "count every pick" is meaningless while one ledger counts 8,899 expiries and the other never sees them.

---

## 6. `UNVERIFIED` register

| Item | Why it cannot be verified |
|---|---|
| `st_rsi_momentum_confluence` 65.1% / PF 2.53 / n=258 | 0 rows in all 5 datasets; `walk_forward_validation.json` absent; current walk-forward artifact has no such cell. |
| TradingView 59K–107K leaderboards, and the six behavioural rules | No source, URL, dataset, or artifact. |
| `+669%` as a tradable return | It is a sum of `pnl_pct`, not a compounded equity curve; `quan_engine` rows are a fixed ±ladder. |
| The "May 2026 kill list" as the cause | Kill entry is dated 2026-05-06 and cites **0 closed + 0 active**, i.e. no performance data was behind it. |
| Whether expired picks would improve or worsen the 40-59 bucket | No `exit_price`/`closed_at` on the 8,899 excluded rows — same limitation the audit flags. |
| Magnitude of the `quan_engine` 95.9% after intrabar resolution | Daily/intrabar bars for that window are not in the payload; only the truncated ladder is visible. |

---

## 7. Top findings (for the reviewer who reads only this)

1. **The 95.8% is real — in April.** `dashboard_data_2026-04-06T225846Z.json` → `systems.quan_engine` = 292 closed, 280W/12L, 95.9%, +689.4%, **PF 79.61**, avg loss **−0.73%**. That PF is a truncated-loss resolver artifact, not an edge. Today the same system has **0 resolved picks**; its own DB says **40.7% WR / PF 1.166** on 216 closed.
2. **The SHORT claim is a 25-row cell.** In the very snapshot it came from, the full population was **SHORT 31.6% (307) vs LONG 47.2% (3,181)** — the opposite conclusion. Today it is 53.6% vs 38.7% (p = 0.070), and a second ledger has it 46.9% vs 54.3%.
3. **`st_rsi_momentum_confluence` cannot be found anywhere.** Zero rows in five datasets; the cited source file does not exist. It is the plan's second pillar and it is `UNVERIFIED`.
4. **Score 40-59 is the only survivor — and it is not significant.** 54.4% WR, PF 1.74, n=331 (n_eff 263), positive in 8/10 months, p = 0.124. Worth a pre-registered shadow test; not worth a live gate on `>59`/`<40` today.
5. **The plan's own tooling refuted it before it shipped.** `bootstrap_verified_edges.json`: quan_engine `INSUFFICIENT_N n=28`, st_rsi `n=0`. And the merged pilot emits **207 picks with 0 st_rsi, 2 quan, 0 exit prices, entry dates from June–August** — not the three edges it claims.
6. **The remediation plan is right about the disease and incomplete about its size.** Independent recompute: **3,489 rows, 41.4% WR, PF 0.869, Σ −617.5%** — the premise holds. But it misses (a) two almost-disjoint ledgers with **62 shared IDs and opposite signs** (`−617%` vs `+2,182%`), and (b) **34 fixed-ladder PnL cohorts** (e.g. `unknown` at −2.0×377 and +3.5×228) sitting inside the ledger its own bootstrap trusts. Add **C0** to week 1, and the plan becomes executable.

---

## Appendix — reproduction

```bash
cd /home/eaguiar2015/findtorontoevents_antigravity.ca
curl -sS -o /tmp/dd.json https://findtorontoevents.ca/audit/data/dashboard_data.json   # 25,247,161 B
# C1 origin (April snapshot)
python3 -c "import json;d=json.load(open('tools/data/snapshots/dashboard_data_2026-04-06T225846Z.json'));print({s['name']:{k:s.get(k) for k in ['closed_picks','wins','losses','win_rate','total_pnl_pct','profit_factor','avg_win','avg_loss']} for s in d['systems'] if s['name']=='quan_engine'})"
# C1 today (live payload, systems.quan_engine) -> 0 closed / 0 resolved / WR 0.0
# C1 authoritative DB
python3 -c "import sqlite3;c=sqlite3.connect('file:quan_engine/data/quan_engine.db?mode=ro',uri=True);print(c.execute('select count(*),avg(pnl_pct) from signals where pnl_pct is not null').fetchone())"
# C3 full-population direction split (April snapshot)
#   SHORT 31.6% n=307 ; LONG 47.2% n=3181
# C3/C4 today (live recent_closed): SHORT 53.6% n=647 ; LONG 38.7% n=2842
#   score 40-59: 54.4% n=331 PF 1.737 avg +0.644% ; binomial p=0.124
# C0 ledger divergence: recent_closed 41.4%/PF 0.869/Σ-617.5 vs universal_resolved 52.3%/PF 1.793/Σ+2182 ; id overlap 62
# C0 flat cohorts: universal_resolved -> unknown -2.0 x377, +3.5 x228
# C2: walk_forward_validation.json absent; walk_forward_per_strategy_latest.json = 7 cells, no st_rsi
# C5: audit_trail/quality_gates.py:1446 "0 closed + 0 active — proactively blocked"
# C6: no 59K/107K anywhere; research/profitability/SCORECARD.md rejects the inference
```

*No repo source, data file, or branch was modified by this review. Only this file was written.*
