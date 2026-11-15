# Peer cross-check review — PLAN_FINAL.md & QA_PLAN.md (deepAI/inspect-wt)

**Reviewer:** review sub-agent (skeptical quant) · **Date:** 2026-11-14 · **Method:** every peer claim re-fetched from GitHub `main` (raw), local repo state re-checked, PR metadata via GitHub API. No draft file was modified.

---

## VERDICTS

- **`final_v4/inspect-wt/01_plan/PLAN_FINAL.md` — FAIL.** Sound structure, and most shipped-code citations are correct, but it presents itself as a "post-24h-review" while repeating three numbers its own cited sources (#773, `final_v3/06_followups`) explicitly corrected: the 98.8% fill attribution, `PF≈1.00`, and "B4 open". It also keeps EQUITY as slot-1 candidate after the pre-registered peer decision **closed it as beta** (`NO_ALPHA_BETA`, t=1.05). 7 [MUST] edits required (Items 1–7 below).
- **`final_v4/inspect-wt/02_qa/QA_PLAN.md` — PASS (conditional).** Core design is sound, its peer-facing claims mostly verify, and it correctly reuses `tools/stop_fill_replay.py`. Conditional on 3 [MUST] edits (Items 14–16): one peer citation I could not find anywhere (`flaxen-hair 13/24`), no acknowledgment that flaxen-hair already proposed the same validator as a concrete file (`alpha_engine/risk_qa_validator.py`), and no explicit boundary vs `tools/per_class_cost_gate.py` (which it must NOT change — that gate is deliberately fail-open for emission).

`RAW` prefix below = `https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/`

---

## A. Claim-by-claim cross-check of PEER-work claims

### A1. PLAN_FINAL §0 header

| # | Claim | Verdict | Source |
|---|---|---|---|
| 1 | `final_v3` = decision round: BUGS.md B1–B14, focus decision, shipped code | **CORRECT** | `RAW`final_v3/README.md; `RAW`final_v3/00_common_themes/BUGS.md (B1–B14 present) |
| 2 | `final_v4` = "review round: 5 peer bundles + synthesis" | **NOT FOUND as stated** | `main` tree: 6 bundle folders (`childlike-airport-20261114-215046Z`, `finpredict_2026-11-14T215013Z`, `flaxen-hair_…T2150/T2200/T2304` ×3, `scratch-hippodraco-2026-11-14T2150Z`) from 4 peers, plus finpredict-v4's own `01_…05_` sections. "5 bundles" is not reproducible from the tree |
| 3 | PRs #773–#777 reviewed | **CORRECT** | GitHub API: #773 "fix(kimi): … settle B4; EQUITY fails its SPY gate" merged 22:00:55Z; #774 (remove CROSS_PEER_REVIEW_REPORT) 22:01:32Z; #775 (pandas pin, correct B13, peer-work review) 22:06:43Z; #776 (docs: scratch-hippodraco bundles) 22:10:45Z; #777 (ME alias, cost fallback) 22:13:27Z — all merged |
| 4 | "100 remote commits (18 meaningful, 82 `[skip ci]` churn)" | **PARTIAL / split NOT REPRODUCED** | API `commits?since=2026-11-13T18:00Z&per_page=100` → exactly 100 (page cap), **96 with `[skip ci]`** in my window. Total plausible; the 18/82 split could not be reproduced (window-dependent) |
| 5 | "26 modified / ~358 untracked files — all May–June leftovers, mtime-verified" | **NOT REPRODUCED** | Local `git status --porcelain` = **25 M**, 49 `??` collapsed lines; `-uall` = **576,505 untracked** (dominated by `.venv-swarm`). The "26/358" figures are unreproducible as stated (some filter was applied but not documented) |

### A2. PLAN_FINAL §0.1 — shipped-code claims (quant-audit branch → main)

| # | Claim | Verdict | Source |
|---|---|---|---|
| 6 | `audit_trail/stop_fill.py` (20 tests) | **CORRECT as peer claim / WRONG vs code** | `RAW`final_v3/README.md says "20 unit tests" — but `RAW`tests/test_stop_fill.py on `main` contains **18** test functions (AST-counted). Flag the discrepancy |
| 7 | gap-aware fill flag `RESOLVER_GAP_AWARE_FILL` in `universal_pick_resolver.py` | **CORRECT** | `RAW`audit_trail/universal_pick_resolver.py:623–624 (`_GAP_AWARE_FILL = os.environ.get("RESOLVER_GAP_AWARE_FILL","1")…`, env `=0` restores legacy) |
| 8 | `tools/per_class_cost_gate.py` (18 tests, 3× round-trip gate, default ON) | **CORRECT as peer claim / WRONG vs code count** | README: "18 unit tests … default ON"; code: `REQUIRED_COST_MULTIPLE = 3.0`, `DEFAULT_OUT=config/per_class_cost_gate.json`, fail-open docstring — but `RAW`tests/test_per_class_cost_gate.py has **15** tests on main |
| 9 | `after_cost_net_per_trade` in `dashboard_generator.py` | **CORRECT** | `RAW`audit_trail/dashboard_generator.py — 8 occurrences (fields list :304, stamp fn :7755, fallback :8543) |
| 10 | `tools/stop_fill_replay.py` (30 crypto + 25 equity + 25 ETF real replays) | **CORRECT** | `RAW`final_v3/README.md: "30 crypto + 25 equity + 25 ETF real replays"; also `--limit 30`/`--limit 25` reproduce commands in same file |
| 11 | COT test failed 4/4, honestly reported | **CORRECT** | `RAW`final_v3/README.md: "`tools/cot_contrarian_backtest.py` — **gate failed 4/4** — reported as failure"; `RAW`final_v3/03_focus/DECISION.md: "failed all four pre-registered checks today" |
| 12 | "52 tests" (implied) | **CORRECT (pre-#773), superseded** | README + `RAW`final_v4/05_final_summary/FINAL_SUMMARY.md: 52. Reproduces on main: 18 (stop_fill) + 15 (cost gate) + 19 (cot) = **52**. After #773: `66 passed` per `RAW`final_v3/06_followups/2026-11-14_next_steps.md (adds `tests/test_kimi_exit_fill.py`, 14 tests) |
| 13 | "Crypto stop-fill = 98.8% of class loss is now modeled (B3 fixed)" | **CORRECT as of final_v3, WRONG as current fact** | ✓ `RAW`final_v3/README.md + BUGS.md B3 ("98.8% of the class loss"). **But** `RAW`final_v3/07_peer_review/PEER_WORK_REVIEW_2026-11-14.md §2.2 table lists "98.8% of class loss → **artifact of the same field**" after #773, and PR #773 body: kimi correction is **+67.5pp, not +727.3pp** ("the larger figure measured a drifted `stop_loss` field, measuring the field mismatch rather than the fill") |

### A3. PLAN_FINAL §0.2 — focus-decision numbers

| # | Claim | Verdict | Source |
|---|---|---|---|
| 14 | EQUITY 3.23× cost, mean +0.323%, n=738, t=1.52 p=0.12; only class clearing 3× cost | **CORRECT** | `RAW`final_v3/03_focus/DECISION.md screen table ("✅ 3.23× … 738", "t=1.52, p=0.12") |
| 15 | "#773 shows EQUITY fails its SPY gate" | **CORRECT** | PR #773 body: 738 pairs, excess +0.2092%, median −0.5726%, **t=1.05, G3 FAIL → `NO_ALPHA_BETA`**; `RAW`final_v3/06_followups/…next_steps.md §3 |
| 16 | EQUITY = "slot 1" candidate (plan §1 Phase 2 table) | **WRONG vs latest peer decision** | Same DECISION.md **REVISION**: "EQUITY is no longer 'slot 1 — candidate'. It is **slot 1 — closed as a source of edge**, retained only as a measurement baseline"; PR #773: "`DECISION.md` revised: slot 1 closed as a source of edge; CRYPTO promoted to the only remaining candidate." PLAN acknowledges the failed gate yet still ranks EQUITY #1 |
| 17 | CRYPTO = slot 2 conditional, 0.58× cost | **CORRECT** | DECISION.md table ("❌ 0.58× … YES — slot 2, conditional") |
| 18 | ETF 267% cost ratio; FOREX −16.2pp; BOND n=35; COMMODITY blocked | **CORRECT** | `RAW`final_v3/README.md: "ETF at 267% cost/PnL, COMMODITY at 422%, FOREX a −16.2pp breakeven gap, BOND n=35"; DECISION.md table agrees (BOND n=35, COMMODITY n=7) |
| 19 | MF = allocation, not prediction (0 rows) | **CORRECT** | `RAW`final_v3/03_focus/MUTUAL_FUNDS_SUBSET.md: "0 mutual fund rows across 3,500 closed picks — verified" |
| 20 | Phase 2 slot 2 evidence: "ITERATION-005 + fixed fill (PF 0.768→≈1.00)" | **PARTIAL — `≈1.00` WRONG now** | ITERATION-005 is named in `RAW`final_v4/05_final_summary/FINAL_SUMMARY.md:15 and SYNTHESIS.md:45. But PR #773 + next_steps.md: crypto correction **+67.5pp, PF 0.768 → ~0.80, "not ~1.00"**; PEER_WORK_REVIEW §2.2: "CRYPTO PF ~1.00 breakeven → **~0.80**" |
| 21 | Phase 2 slot 2 gate "forward PF ≥ 1.15 after fill fix, n≥100" | **CONFLICT with peers' gate** | DECISION.md slot 2 step 3: "Forward-test POSITION horizon only … **gate PF ≥ 1.3 and WR ≥ 55%**"; SYNTHESIS §3 candidate table repeats PF≥1.3/WR≥55%. PLAN's 1.15 is looser than the peer-agreed gate |
| 22 | Phase 2 slot 2 ignores benchmark-relative objection to TSMOM | **MISSED peer finding** | `RAW`final_v3/07_peer_review/PEER_WORK_REVIEW §3: childlike-airport ranks **Crypto Vol-Targeted TSMOM #1 (Sharpe 2.13)** while quant-audit downgraded ITERATION-005 because "tested vs zero, not vs B&H; B&H Sharpe ≈ 2.2" — "2.13 < 2.2 … occupies the slot EQUITY just vacated" |

### A4. PLAN_FINAL §0.3 — final_v4 consensus / bug catalog

| # | Claim | Verdict | Source |
|---|---|---|---|
| 23 | "not profitable but now testable"; two candidates | **CORRECT as final_v4 text; stale vs #773** | `RAW`final_v4/05_final_summary/FINAL_SUMMARY.md (21:50Z). PEER_WORK_REVIEW §2.2: "final_v4 is stale within ten minutes of its own timestamp … 'two deployable candidates' rests on both legs, and both are now false" (SPY test ran and failed 22:00Z) |
| 24 | B4 = "40–56% of non-crypto SL_HIT never touched the stop", **open** | **CORRECT for the 40–56% figure; WRONG on "open" status** | "40–56%" verbatim in `RAW`final_v3/README.md B4 row (initial replay: EQUITY 14/25=56%, ETF 10/25=40%). But BUGS.md now carries "**B4 — RESOLVED**" (label, not price), PR #773 title says "**settle B4**", and next_steps.md table: "Settle B4 → **Settled**". Latest truncated numbers: EQUITY 14/25, ETF 13/25 never touched (52–56%) |
| 25 | "B7 = all 166 cells single-source" | **WRONG attribution (bug-ID collision)** | Matches `RAW`final_v4/05_final_summary/FINAL_SUMMARY.md:80 and `RAW`final_v4/04_synthesis/SYNTHESIS.md §4 — **but contradicts the canonical catalog** `RAW`final_v3/00_common_themes/BUGS.md, where **B7 = "FOREX is not 100% forex, allowlist never enforced"** (fix → G7). "0/166 cells pass all gates" is a *different* quant-audit claim (`RAW`final_v3/quant-audit-2026-11-14/09_evidence/EVIDENCE_INDEX.md). PEER_WORK_REVIEW §4 documents exactly this: "bug IDs collide across packages — B14 means five different things; B1 means three" |
| 26 | B8 = 170 ledgers, 4 pass vs 8.5 by chance | **CORRECT** | `RAW`final_v3/00_common_themes/BUGS.md B8 (verbatim) |
| 27 | B1 = "EXPIRED→WON mislabeling + refuted-VALIDATED advertising" | **PARTIAL — merges two canonical bugs** | BUGS.md **B1** = refuted-VWAP-still-`VALIDATED`; **B10** = "EXPIRED→WON relabeling is still pending". FINAL_SUMMARY:80-style table calls B1 "EXPIRED→WON mislabeling". PLAN's Phase 0 wording is a merge of both; needs explicit citation of both IDs |

### A5. QA_PLAN peer-work claims

| # | Claim | Verdict | Source |
|---|---|---|---|
| 28 | Spec'd file:line against `f54efb3b4a` in `2026-11-14/…/fixspecs/` | **CORRECT, caveat omitted** | 8 fixspec files exist on main at `2026-11-14/deepAI_proposed_fixes_20261114_1612/fixspecs/` and reference `f54efb3b4a`. **Caveat:** `f54efb3b4a` = "Copy trader portfolio: 2026-06-06" — the fixspec docs themselves say "anchors verified at f54efb3b4a … ~5 months behind origin/main — re-grep before merge" (`…/per_asset_class/crypto/proposed_fix.md:3`) |
| 29 | Gate 3.1: "peers measured 40–56% non-crypto" | **CORRECT (initial measurement), superseded** | final_v3 README + BUGS.md B4 initial replay; settled truncated values are 52–56% (see #24) |
| 30 | Gate 3.2: "flaxen-hair found 13/24" TP never reached | **NOT FOUND** | Searched and found zero occurrences of `13/24` / `13 of 24` in: `final_v4/flaxen-hair_2026-11-14T2150/{00_common_themes/BUGS.md, 00_common_themes/DEEP_INVESTIGATION.md, 04_per_class_profitability, 06_execution_roadmap, 05_proof_assessment, 07_summary}`, `…T2200/{01_common_themes_bugs, 06_per_class_profitability, 10_peer_work_review}`, `…T2304/{01_proposed_edits/PROPOSED_EDITS.md, 02_qa_plan/QA_PLAN.md, 05_peer_review_results}`, plus final_v3 BUGS.md/README/DECISION/SYNTHESIS/FINAL_SUMMARY, and local `final_v2/`, `final_2026_11_14/`, `final_v4/` (grep) — only hit is the draft itself |
| 31 | Gate 3.3: "crypto budget now measured: 1.932%→2.970%" | **CORRECT — but it is inspect-wt's OWN number, not peers'** | `final_v2/inspect-wt/01_peer_review/peer_adjudication_final.md:17` (local): "mean planned risk **1.932%** vs mean realized **2.970%** (theirs: … 1.919 vs 2.990)". Peers' published numbers differ: BUGS.md B3 / `audit_trail/stop_fill.py` docstring = **1.919% → 2.956%**. Cite your own source |
| 32 | Gate 4: "existing disagreement banner spec" | **CORRECT** | `fixspec_surface_disagreement_banner.md` is 1 of the 8 fixspecs (see #28) |
| 33 | Gate 3.4: `exit_reason` already populated; `resolution_method` unset | **CORRECT** | BUGS.md B5: `resolution_method` NULL on all 3,500; `exit_reason` = `SL_HIT 1,468 · TP_HIT 873 · FORCE_CLOSED 615 · TIME_EXIT 517 · UNKNOWN 22 · EXPIRED 5` |
| 34 | "81% fake zeros" | **CORRECT (own prior work)** | `final_2026_11_14/inspect-wt/02_active_picks/02_active_picks_repricing.md` (local): 703 open-ish → 624 priced → **504/624 (81%)** at 0/None |
| 35 | "EURGBP/JPY-class garbage" | **PARTIAL** | EURGBP verified: `…/02_active_picks_repricing.md:24` "`EURGBP=X` entry 688.17 vs market 0.835". JPY `0.000001` placeholders: **NOT FOUND** in local inspect-wt docs |
| 36 | Verification plan: finpredict-v3 `pi_data_hygiene.py` + quant-audit `per_class_stats.py` | **CORRECT (both exist)** | `RAW`final_2026_11_14/finpredict-v3/02_tools_guardian/tools/pi_data_hygiene.py; `RAW`final_v2/quant-audit-2026-11-14/04_verification/per_class_stats.py |
| 37 | "703 open picks" (PLAN §0.4) | **CORRECT (own prior work)** | `…/02_active_picks_repricing.md:5,16` |

---

## B. Conflict / duplication analysis (drafts vs shipped + proposed peer work)

### B1. QA_PLAN Gate 1 vs `tools/per_class_cost_gate.py` — **COMPLEMENTARY, no duplication, one boundary to state**
The shipped gate is **class-level** (`class mean pnl_pct ≥ 3.0 × round-trip cost`, index in `config/per_class_cost_gate.json`, pick-level `gate_pick()`, **deliberately fail-open** on missing/stale/unknown/thin evidence — module docstring: "it must never silence a class merely because bookkeeping is absent"; wired into `tools/hc_gates_python.py`, default ON). QA Gate 1 is **row-level** (reprice stored PnL vs market). Different granularity, different output (`qa_status` vs `decision`).
**Risk:** QA_PLAN's "any MISMATCH >2% blocks money-ready scoring (fail-closed)" is right for **promotion/readiness**, but if read as applying to *emission*, it contradicts the shipped design. PEER_WORK_REVIEW §1.3 records the adopted resolution: "emission stays fail-open, promotion must fail closed with `INSUFFICIENT`" (their G5; also flaxen-hair PROPOSED_EDITS Edit 2). QA_PLAN must state this boundary explicitly (Item 15).

### B2. QA_PLAN Gate 1/3 vs `tools/stop_fill_replay.py` — **REUSED (good), with two gaps**
Gate 3.1 says "Reuse `tools/stop_fill_replay.py`" ✓. Gaps: (a) Gate 3.1 should name the settled flag `--truncate-at-exit` — untruncated replay "manufactures touches" (PEER_WORK_REVIEW §2.1); (b) Gate 1 builds its own candle pipeline (Binance/Yahoo/Stooq) while the shipped tool already has `fetch_bars()` (Binance) and `fetch_bars_yfinance()` — two candle pipelines is the B2-style divergence defect the catalog warns about. No contradiction with the tool otherwise.

### B3. PLAN Phase 0 vs final_v3's fixes — **partially duplicative, partially missing**
- Phase 0 says "Adopt peers' shipped fixes" — correct: G1 (stop-fill provenance), G2 (gap-aware fill), G9 (cost gate), G10 (`after_cost_net_per_trade`) are **DONE TODAY** per `RAW`final_v3/01_plan/GENERAL_FIXES.md. No re-work.
- **Duplicates without citation:** PLAN B1 ≈ G3 ("verdict artifact invalidation: `evidence_hash` + `generated_at`, CI greps `VALIDATED`") — PLAN mentions only banner+relabel; PLAN B5 ≈ G5 ("field contract + population assertion ≥95%") — PLAN proposes re-recording without the CI assertion; PLAN B9 misses the G9/B9-fix instruction to **extend the existing `tools/db_freshness_check.py` + hourly guardian** (BUGS.md B9 fix line), proposing only `universal_price_enricher` (file exists: `alpha_engine/universal_price_enricher.py` ✓).
- **Contradiction:** PLAN calls **B4 "deepest open bug"** and proposes touch-vs-fill instrumentation as new work — but B4's diagnosis is **settled** (label-not-price; `--truncate-at-exit` replays; PR #773). The peer-documented remaining work item is **reclassifying `exit_reason`**, plus "do **not** extend the gap-aware fill to non-crypto exits" (BUGS.md B4 RESOLVED; next_steps §2). PLAN says neither.
- **Attribution:** PLAN's **B7 = "single-source"** collides with canonical B7 = FOREX hygiene (fix G7, unaddressed in PLAN). PEER_WORK_REVIEW §4 explicitly demands namespacing ("Namespace them (`QA-B3`, `CA-B3`) or keep one registry").
- **Missing shipped fact:** #773's kimi scanner fix (`exit_fill_for_stop()`, `exitPrice/polledPrice/stopUsed/targetUsed/exitPriceBasis`, TAKE_PROFIT fills-at-target) is a peer fix PLAN's "adopt shipped fixes" should name — it directly affects QA Gate 3.2/3.3 interpretation (post-fix rows clean, pre-fix rows not).

### B4. Peer-proposed changes the plan misses entirely
| Source | Proposal | In PLAN/QA? |
|---|---|---|
| `final_v3/06_followups/2026-11-14_next_steps.md` | B4 settled → binding constraint is **exit taxonomy + B14 cross-symbol stop contamination** (implied-risk ≤25% sanity bound; ADA-USD row) | **No** |
| same | Crypto correction **+67.5pp**, PF ~0.80 (not ~1.00) | **No** (PLAN still ≈1.00) |
| `final_v3/07_peer_review/PEER_WORK_REVIEW_2026-11-14.md` §1.2 | `MONEY_READY_FDR_GATE` + `MONEY_READY_SINGLE_SOURCE_GATE` **default `"0"` (OFF)** at `alpha_engine/money_ready_verdict.py:180/:195` — verified on main | **No** (PLAN Phase 4 references `is_single_source_artifact=False` but never turns on the existing gates) |
| same §2.3 + PR #775 | CI was red for everyone (pandas `freq="ME"`); "no package's 'tests pass' claim today was CI-verified" | **No** |
| same §3 | ITERATION-005/TSMOM fails vs buy-and-hold (2.13 < 2.2) — benchmark-relative objection to the crypto candidate | **No** |
| same §4 | Bug-ID collisions (B1×3, B14×5) → namespace or single registry | **No** |
| `final_v3/hilarious-seer/02-improvement-plan/todo_master_list.md` (47 tasks) | A1 PnL unit contract, A2 price freshness pipeline, **A3 zombie drain + dedup**, A4 store reconciliation, **C1 route `kimi_riseoftheclaw` through intrabar resolver**, **C2 kill CRYPTO SWING emission (n=243, PF 0.457, −328.6pp)**, M1/M2 keep MF `NOT_BUILT` label | PLAN mentions zombie purge only via QA `STALE_OPEN`; **C1/C2 (both P0, both in DECISION week-1) absent** |
| `final_v4/flaxen-hair_2026-11-14T2304/01_proposed_edits/PROPOSED_EDITS.md` | **Edit 5: `alpha_engine/risk_qa_validator.py`** with `validate_pnl_zero/validate_blank_fields/validate_open_items/validate_recently_closed` + **Edit 6** wire into `production_scanner.py` — i.e. the *same QA* QA_PLAN specifies | **Duplicate risk — no acknowledgment** (QA_PLAN proposes nightly script + `dashboard_generator` wiring instead: two parallel implementations = B2 defect) |
| same, Edit 1/2/3/4 | Enable FDR/single-source gates; fail-closed for promotion; un-suppress after-cost stamping errors; weekly/monthly loss limits | **No** |
| `final_v3/finpredict/FOCUS_DECISION.md` | MF/ETF **`BENCHMARK_SLEEVE` control arm** (`benchmark_snapshot.py` vs SPY), demote `tactical_fund_rotation` to reference | **Partial** — PLAN slot 3 is a rotation sleeve; the *control-arm* framing and its attribution are missing |
| `final_v4/scratch-hippodraco-2026-11-14T2150Z/04-synthesis/RISK_AND_VETO_LIST.md` | No mass DELETE of ghost rows (flag/quarantine instead); regenerate `benchmark_ledger_proof.json` if Nov-14 logic changed; keep MF `NOT_BUILT` until NAV/EOD/walk-forward exist | **Partial** — QA quarantine aligns ✓; PLAN's "zombie purge" and B8 evidence currency not qualified by these vetoes |

---

## C. Proposed edits (numbered; exact replacement text where possible)

### PLAN_FINAL.md

1. **[MUST] §0.1 last line — 98.8% is superseded.**
 Replace: `→ **Crypto stop-fill = 98.8% of class loss is now modeled (B3 fixed).**`
 With: `→ **B3 (final_v3): fill gap measured at 98.8% of class loss. SUPERSEDED by #773 — the 98.8%/+727.3pp figures differenced against a drifted \`stop_loss\` field; the verified kimi fill correction is **+67.5pp** (crypto −837.8 → −770.3pp, PF 0.768 → ~0.80), per \`final_v3/06_followups/2026-11-14_next_steps.md\` and PR #773.**`
 *Rationale:* PLAN cites #773 but keeps the number #773 retracted.

2. **[MUST] §0.1 test counts — reconcile with code.**
 Replace: `audit_trail/stop_fill.py (20 tests), … tools/per_class_cost_gate.py (18 tests, 3× round-trip gate, default ON)`
 With: `audit_trail/stop_fill.py (18 tests on main; final_v3/README.md says 20 — reconcile), … tools/per_class_cost_gate.py (15 tests on main; README says 18), COT test 19 — 52 total at final_v3, **66 after #773** (\`tests/test_kimi_exit_fill.py\`)`
 *Rationale:* per-file counts in the README don't match the shipped test files (AST-counted); totals do.

3. **[MUST] §0.2 + Phase 2 slot 1 — reconcile EQUITY with the peer decision it cites.**
 Replace the slot-1 row's framing `**EQUITY** (variant C selector + RSI(2) H10) vs **SPY benchmark**` … `**35–45%**` with:
 `| 1 | **EQUITY — CLOSED as a source of edge (measurement baseline only)** per DECISION.md REVISION + #773 (NO_ALPHA_BETA: t=1.05, median pick −0.57% vs SPY, 54% underperform). Reopening requires a *new pre-registered* test with a documented trial ID (B8), not a re-run with different thresholds | benchmark-relative gate (record only) | n/a (0% as candidate) |`
 *Rationale:* DECISION.md revision explicitly: "slot 1 — closed as a source of edge"; keeping it #1 with a 35–45% success guess contradicts the cited source and trips the multiple-testing discipline the plan itself mandates.

4. **[MUST] Phase 2 slot 2 — corrected fill math + peer-agreed gate + benchmark objection.**
 Replace: `ITERATION-005 + fixed fill (PF 0.768→≈1.00)` / `forward PF ≥ 1.15 after fill fix, n≥100, dual-source` / `**25–35%**`
 With: `ITERATION-005 + fixed fill (PF 0.768→~0.80 per #773 — not ≈1.00); kimi routed through intrabar resolver; CRYPTO SWING emission killed (n=243, PF 0.457, −328.6pp)` / `forward **PF ≥ 1.3, WR ≥ 55%**, n≥100, dual-source (peers' pre-registered gate), **and** a risk-matched benchmark (TSMOM Sharpe 2.13 vs B&H ≈2.2 must be beaten)` / `**20–30%** (revised down: fill fix buys ~+67.5pp, not breakeven)`
 *Rationale:* three peer corrections (PR #773, DECISION slot-2 step 3, PEER_WORK_REVIEW §3) in one row.

5. **[MUST] Phase 0 B4 — settled diagnosis; pivot to the documented work item.**
 Replace the B4 bullet with: `- **B4 — diagnosis SETTLED (#773, \`--truncate-at-exit\`): the *label*, not the price (11/14 EQUITY and 12/13 ETF never-touched rows exited at a different level). Remaining work = reclassify \`exit_reason\` (trailing/target/max-hold), quarantine the 4 rows that never traded at their recorded exit price, and instrument the resolver for touch-vs-fill logging. **Do not extend the gap-aware fill to non-crypto exits** (gap-aware makes EQUITY worse: −83.62 vs −63.41pp).`
 *Rationale:* "deepest open bug" is stale; peers settled it hours before this plan's own review window closed.

6. **[MUST] §0.3 — fix the B7 attribution and adopt bug-ID namespacing.**
 Replace: `B7 all 166 cells single-source`
 With: `B7 — **ID collision**: final_v4's table says "all 166 cells single-source" (FINAL_SUMMARY/SYNTHESIS), while canonical \`final_v3/00_common_themes/BUGS.md\` B7 = FOREX composition/allowlist (fix G7); "0/166 cells pass all gates" is a separate quant-audit claim. All bug IDs below are quoted with their source package (see PEER_WORK_REVIEW §4: B1×3, B14×5 meanings)`
 *Rationale:* the plan currently reproduces the exact defect its own cited peer review flags.

7. **[MUST] §1 Phase 2 note — add the missing peer week-1 P0s.**
 Add after the Phase 2 intro: `Peer week-1 P0s adopted verbatim (DECISION.md 90-day sequence; hilarious-seer todo C1/C2): route \`kimi_riseoftheclaw\` through the intrabar resolver; kill CRYPTO SWING emission.`
 *Rationale:* both are unanimous peer P0s absent from the plan.

8. **[SHOULD] Phase 0 B1 — adopt G3 in full.**
 Append: `… (my \`fixspec_surface_disagreement_banner\` already specifies this) **+ G3: every verdict carries \`evidence_hash\` + \`generated_at\`; CI greps \`VALIDATED\`/`PROVEN` and fails without a registry entry** (\`final_v3/01_plan/GENERAL_FIXES.md\` G3).`
 *Rationale:* banner-only fix misses the peer-designed invalidation mechanism.

9. **[SHOULD] Phase 0 B5 — cite G5 instead of reinventing.**
 Append: `… we still need *how* it filled** — implement as G5's field contract + CI assertion (≥95% of closed rows populate \`resolution_method\` ∧ payload \`exit_reason\`, else build fails).`
 *Rationale:* G5 already specifies the mechanism.

10. **[SHOULD] Phase 0 B9 — use the existing freshness guardian.**
 Replace: `wire \`universal_price_enricher\` + staleness guard`
 With: `extend the existing \`tools/db_freshness_check.py\` + hourly guardian to these three feeds (BUGS.md B9 fix), plus wire \`alpha_engine/universal_price_enricher.py\`; hard TTL fails the build`
 *Rationale:* peers explicitly said the guardian "already exists — extend coverage".

11. **[SHOULD] Phase 0 — add two items peers named as binding.**
 Add bullets: `- **B14 (06_followups) — cross-symbol stop contamination:** implied-risk sanity bound ≤25% at write time (ADA-USD row: +45,772pp of fake correction from one row).` and `- **Turn on the existing promotion gates:** \`MONEY_READY_FDR_GATE\` / \`MONEY_READY_SINGLE_SOURCE_GATE\` default \`"0"\` at \`alpha_engine/money_ready_verdict.py:180/:195\` → \`"1"\` for promotion (emission stays fail-open, per G5).`
 *Rationale:* both verified on main, both absent from the plan.

12. **[SHOULD] §2 non-goals — add the TSMOM benchmark objection.**
 Append: `No ITERATION-005 deployment on "tested vs zero" evidence — it must beat a risk-matched buy-and-hold (Sharpe 2.13 vs ≈2.2 currently fails).`
 *Rationale:* the plan's #2 candidate currently inherits an unresolved peer conflict.

13. **[SHOULD] Phase 4 — add CI-verification requirement.**
 Insert: `All certification runs must be **CI-green** (pandas \`freq="ME"\` incident: no tests-pass claim from 2026-11-14 was CI-verified before #775; PR #775).`
 *Rationale:* prevents certifying on local-only test runs.

14. **[SHOULD] §0 header — soften/repair the two unreproducible counts.**
 Replace: `(26 modified / ~358 untracked files — all May–June leftovers, mtime-verified; zero new local peer work outside my folders)`
 With: `(working-tree dirty-state counts filter-dependent: 25 modified at review time; untracked count excludes \`/ .venv*\`; zero new local peer work outside my folders)`
 and replace `100 remote commits (18 meaningful, 82 \`[skip ci]\` churn)` with `~100 remote commits (reproduced count; the meaningful/`[skip ci]` split is window-dependent — 96/100 by my API window)`.
 *Rationale:* both numbers failed independent reproduction (see A1 #4–5).

15. **[NICE] Phase 2 MF sleeve attribution.**
 Replace `expense-ratio ≤0.20% screen per finpredict-v3's subset` with `expense-ratio ≤0.20% screen per \`final_v3/03_focus/MUTUAL_FUNDS_SUBSET.md\`; \`final_v3/finpredict/FOCUS_DECISION.md\` separately proposes the \`BENCHMARK_SLEEVE\` control arm (vs SPY) — adopt as the sleeve's control`.
 *Rationale:* the ≤0.20% screen is not in finpredict's subset (that one is VTI/3-fund); correct attribution + captures a missed peer proposal.

16. **[NICE] §0 header "5 peer bundles"** → `6 bundles from 4 peers + finpredict-v4 synthesis`. *Rationale:* matches the actual `main` tree.

### QA_PLAN.md

17. **[MUST] Gate 3.2 — remove/repair the unfound citation.**
 Replace: `(flaxen-hair found 13/24; must be re-measured with the new fill model)`
 With: `(no source found for the "13/24" attribution in flaxen-hair's bundles — **re-measure from scratch**; peer-measured anchor available: B4 replay, n=25/class, found 4 rows that never traded at their recorded exit price — \`final_v3/00_common_themes/BUGS.md\` B4 RESOLVED)`
 *Rationale:* A5 #30 — the citation is NOT FOUND anywhere; keep the gate, drop the claim.

18. **[MUST] Add an integration/boundary section (after the intro).**
 Insert: `**Relationship to shipped gates.** Gate 1/2 are *row-level measurement* and are complementary to \`tools/per_class_cost_gate.py\` (class-level emission gate, deliberately fail-open on missing evidence — do not modify it; QA fail-closed applies to **money-ready/promotion only**, per \`final_v3/07_peer_review\` G5). Gate 3.1 reuses \`tools/stop_fill_replay.py\`; Gate 1 should import its \`fetch_bars()\`/\`fetch_bars_yfinance()\` rather than build a second candle pipeline. **One implementation, not two:** reconcile this plan with flaxen-hair's proposed \`alpha_engine/risk_qa_validator.py\` (PROPOSED_EDITS Edit 5/6) — single module, this plan's thresholds.`
 *Rationale:* answers B1/B2/B4 — prevents the B2-class duplication defect inside the fix for B2.

19. **[MUST] Gate 3.1 — name the settled replay method and current numbers.**
 Replace: `Reuse \`tools/stop_fill_replay.py\` — extend to all classes.`
 With: `Reuse \`tools/stop_fill_replay.py --truncate-at-exit\` (untruncated replay manufactures touches — \`final_v3/07_peer_review\` §2.1) — extend to all classes. Note peers' *settled* never-touched rates are 52–56% (EQUITY 14/25, ETF 13/25), not 40–56% (that was the untruncated first pass).`
 *Rationale:* without the flag the gate would reproduce the exact error peers corrected.

20. **[SHOULD] Gate 3.2 — account for the shipped TAKE_PROFIT fix.**
 Append: `Note: #773 fixed \`TAKE_PROFIT\` booking in \`KIMI_RISEOFTHECLAW/live_scanner.py\` (fills at the target, not the polled price) — split the measurement pre-/post-#773 before judging.`
 *Rationale:* rows after the fix should be clean; mixing windows muddies the re-measurement.

21. **[SHOULD] Gate 3.3 — cite your own source for 1.932→2.970.**
 Replace: `(crypto budget now measured: 1.932%→2.970%)`
 With: `(inspect-wt independent re-run: 1.932%→2.970%, \`final_v2/inspect-wt/01_peer_review/peer_adjudication_final.md\`; peers publish 1.919%→2.956% — \`final_v3/00_common_themes/BUGS.md\` B3 / \`audit_trail/stop_fill.py\` docstring; state which budget the gate uses)`
 *Rationale:* two different budgets are in circulation; the gate must pin one.

22. **[SHOULD] Intro — add the anchor-staleness caveat.**
 Replace: `spec'd file:line against \`f54efb3b4a\` in \`2026-11-14/.../fixspecs/\``
 With: `spec'd file:line against \`f54efb3b4a\` (a **2026-06-06** commit — the fixspecs themselves warn the anchors are ~5 months behind \`origin/main\`; re-grep before merge) in \`2026-11-14/deepAI_proposed_fixes_20261114_1612/fixspecs/\``
 *Rationale:* QA of specs must not inherit stale anchors silently (verified: `proposed_fix.md:3`).

23. **[SHOULD] Gate 2 — merge flaxen-hair's required-field list.**
 Add to the field list: `symbol, entry_time, status, exit_date` (flaxen-hair `PROPOSED_EDITS` Edit 5 `required_open`/`required_closed`); note both plans currently specify overlapping-but-different lists (resolved in Item 18).
 *Rationale:* one canonical blank-field contract, not two (B2 lesson).

24. **[SHOULD] Gate 4 — cite the fixspec file explicitly.**
 Replace `the existing disagreement banner spec` with `the existing disagreement banner fixspec (\`2026-11-14/deepAI_proposed_fixes_20261114_1612/fixspecs/fixspec_surface_disagreement_banner.md\`)`.
 *Rationale:* verifiable pointer instead of a description.

25. **[NICE] Gate 1 sampling budget — reuse enricher.**
 Append: `Reuse \`alpha_engine/universal_price_enricher.py\` for symbol→feed mapping before any new fetch layer.`
 *Rationale:* file already exists (B9 wiring planned in PLAN Phase 0).

---

## D. Claims I could NOT verify (flagged, not guessed)

1. **"flaxen-hair's 13/24 finding" (PLAN §1.3, QA Gate 3.2)** — NOT FOUND in any flaxen-hair bundle or peer doc searched (full file list in A5 #30). Treat as unverified until a path is produced.
2. **"variant C walk-forward (reproduced twice by peers, clone-dedup robust, sub-T2)"** (PLAN §0.4) — "variant C" appears only in inspect-wt's own `final_v2/inspect-wt/*` docs; I found no peer reproduction. Unverified.
3. **"8 fixspecs + patches"** — **verified**: exactly 8 fixspec files + `per_asset_class/{crypto,…}/*.patch` on main. (Not unverified.)
4. **"mega_mutation disputed 2-v-1"** (PLAN §0.4) — a mega_mutation adjudication exists (`final_v3/hilarious-seer/01-common_themes/peer_adjudication_summary.md`, Adjudication 4: VETOED, "high-risk secondary sleeve only"), but the **2-v-1 vote count is NOT FOUND**. Unverified detail.
5. **"VWAP falsified twice"** — VWAP refutation is documented twice over (BUGS.md B1 conflict table; hilarious-seer adjudication "VWAP rejected"), but I did not independently establish a count of exactly two falsifications. Partially verified.
6. **"100 remote commits (18 meaningful / 82 `[skip ci]`)"** — total 100 reproduced (API page cap), split **not** reproduced (96/100 `[skip ci]` in my window). Unverified split.
7. **"26 modified / ~358 untracked"** — not reproducible (25 M; `-uall` 576,505 ??). Filter undocumented.
8. **"JPY 0.000001-class placeholders"** (QA Gate 2 "EURGBP/JPY-class garbage") — EURGBP verified locally; JPY placeholder rows NOT FOUND in local inspect-wt evidence.
9. **"5 peer bundles"** (PLAN §0) — tree shows 6 bundle folders / 4 peers; count ambiguous.
10. **QA Gate 1 thresholds (`max(0.25%, 3σ)`, "typical crypto σ ≈1–2%")** — inspect-wt's own calibration; no peer source claimed or found. Not a peer claim; out of this cross-check's scope (methodology reviewer owns it).
11. **PLAN Phase 2 slot 1 "variant C fwd n=237 PF 1.26 (equity/ETF 232)"** and **"full Kelly ≈10%/trade"** — own-work numbers; not found in peer docs. Unverified here.
12. **Local mtime verification of "all May–June leftovers"** — not re-run by me (would require stat-ing ~576k paths); unverified.

---

### Sources fetched for this review (all on GitHub `main`)
`final_v3/README.md` · `final_v3/00_common_themes/BUGS.md` · `final_v3/03_focus/DECISION.md` · `final_v3/03_focus/MUTUAL_FUNDS_SUBSET.md` · `final_v3/01_plan/GENERAL_FIXES.md` · `final_v3/05_evidence/INDEX.md` · `final_v3/06_followups/2026-11-14_next_steps.md` · `final_v3/07_peer_review/PEER_WORK_REVIEW_2026-11-14.md` · `final_v3/quant-audit-2026-11-14/{04_asset_class_fixes,08_focus_decision,09_evidence,07_general_fixes}` · `final_v3/finpredict/{README,FOCUS_DECISION}.md` · `final_v3/hilarious-seer/{README,peer_adjudication_summary,todo_master_list,mutual_funds_and_etfs}.md` · `final_v4/05_final_summary/FINAL_SUMMARY.md` · `final_v4/04_synthesis/SYNTHESIS.md` · `final_v4/flaxen-hair_{2150,2200,2304}/**` (12 files) · `final_v4/scratch-hippodraco-2026-11-14T2150Z/{README,04-synthesis/*}` · `final_v4/childlike-airport-20261114-215046Z/07_final_focus_profitability/FOCUS_AND_PROFITABILITY.md` · code: `audit_trail/{stop_fill,universal_pick_resolver,dashboard_generator}.py`, `tools/{per_class_cost_gate,stop_fill_replay,equity_vs_spy}.py`, `tests/{test_stop_fill,test_per_class_cost_gate,test_kimi_exit_fill,test_cot_contrarian_backtest}.py` · GitHub API: PRs #773–#777, commits window, full git tree · local: `final_v2/inspect-wt/*`, `final_2026_11_14/inspect-wt/*`, `2026-11-14/deepAI_proposed_fixes_20261114_1612/`, `git status`, commit `f54efb3b4a`.
