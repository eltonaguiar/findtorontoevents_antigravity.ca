# FP4 — Peer Folder Sweep & Recent-Artifact Inventory

**Reviewer:** FP4
**Review clock:** 2026-11-14T20:20Z
**Root:** `/home/eaguiar2015/findtorontoevents_antigravity.ca` (user `E:\`)
**Working tree:** `.kilo/worktrees/finpredict-v2` (current branch `fix/p0-safe-fixes-2026-11-14-main`, HEAD `bf6a8e310ac`)
**Mode:** read-only. No repo source, data, or peer artifact was modified. The only file written is this report.

---

## Coverage verdict

**FAIL (partial coverage).** The named worktrees and both named remote branches exist and were inventoried, and the two previously-unread peer groups (`inspect-wt`/`deepAI` and `scratch-hippodraco`) were read from their pushed commits. But the deliverable tree `final_2026_11_14/` contains **no peer folders at all** — only `finpredict-v2/` — and `05_final/` is empty. Peer coverage currently lives only as review *documents* under `03_peer_reviews/`, not as archived peer evidence.

| Coverage item | Verdict |
|---|---|
| 7 named worktrees inventoried | **PASS** |
| `audit/live-audit-2026-11-14` reviewed | **PASS** (now on origin at `cc0226b`) |
| `docs/scratch-hippodraco-audit-2026-11-14` reviewed | **PASS** |
| Other new audit branches identified | **PASS** (15 local-only audit branches enumerated) |
| New profitability claims extracted | **PASS** (6 distinct claims; 1 already falsified) |
| Peer folders present in `final_2026_11_14/` | **FAIL — none present** |
| Final synthesis present | **FAIL — `05_final/` empty** |
| Post-18:59 peer research reviewed | **PASS** (v4 scoring framework, edge-search, VWAP falsification) |

**Methodological caveat (important):** worktree file mtimes are unreliable provenance. Checkout/copy operations stamp many files uniformly at `18:23`, `18:55`, `18:58`, and `19:08`. Where a file has a commit, this report uses the **commit timestamp** as the true modification time and notes the mtime only as observed. No mtime is presented as a commit time.

---

## 1. Recent-file inventory (audit/peer artifacts, ≥18:30Z where a commit exists)

Generated trading data, `archive/`, `node_modules/`, `__pycache__/`, `.next/`, and `audit_dashboard/data/*.json` payloads are excluded.

### 1.1 Root profitability / research claims (now on `origin/main`)

| Path | Commit (true time) | Size | One-line description |
|---|---|---:|---|
| `TRUE_PROFITABILITY_VALIDATED.md` | `3e41fe5026d` 18:58:02Z | 5,462 B | flaxen-hair: `mega_mutation` CRYPTO is the only statistically valid edge; claims production enable |
| `PROFITABLE_APPROACH_PROVEN.md` | `3e41fe5026d` 18:58:02Z | 4,969 B | Companion summary: forward n=50, 84% WR, PF 8.32; 8 tournament combos |
| `PLAN_PATH_TO_PROFITABILITY.md` | `da85a2d302a` 19:08:39Z | 5,541 B | finpredict-v4: `quan_engine` 95.8% WR / `st_rsi` 65.1% / SHORT bias; P0 pilot plan |
| `updates/2026-11-14-edge-search-results.md` | `09a7975f113` 18:26:00Z | 8,122 B | 0 of 40 pre-committed trials pass; two closest candidates fail the null |
| `updates/2026-11-14-quant-remediation-plan.md` | `09a7975f113` 18:26:00Z | 12,150 B | D1–D5 defect chain; C1–C5 remediation (resolver, gate, dedup, ledger, ops) |
| `updates/2026-11-14-PROFITABLE-APPROACH-VWAP-MEAN-REVERSION.md` | `45168e2528a` 19:03:59Z | 12,488 B | childlike-airport: regime-filtered VWAP claim (later falsified, see §3) |
| `updates/2026-11-14-quant-audit-multitest.md` | `f790fbbcdff` 18:12:31Z | 75,664 B | Quantitative multi-test audit of `/audit` (input to the remediation plan) |
| `updates/2026-11-14-flaxen-hair.md` | worktree/archive | 9,806 B | flaxen-hair audit summary (mega mutation + quick wins) |
| `updates/2026-11-14-hilarious-seer-audit-summary.md` | `6929af0bdc8` 18:14:54Z | 3,703 B | hilarious-seer summary (regime/zombie priorities) |
| `updates/2026-11-14-ML-AUDIT-childlike-airport.md` | (main repo) | 11,760 B | SQLite forensics: 129 picks 172.9 d stale, sign contradictions, empty audit tables |

### 1.2 Independent falsification / scorecard (new, not covered by FP1–FP3)

| Path | Commit (true time) | Size / lines | One-line description |
|---|---|---:|---|
| `research/profitability/SCORECARD.md` | `97001b6f23e` 19:15:58Z | 4 lines added | 23 candidates over v1–v4: **NOT PROVED**; profitability-proof score 0/10 |
| `research/profitability/validation/VWAP_VERDICT.md` | `97001b6f23e` 19:15:58Z | 52 lines | Peer VWAP claim **FAIL — NOT PROVED**; intrabar PF 0.81, Sharpe ~1.18, t=0.91 |
| `research/profitability/validation/VWAP_STATS_REVIEW.md` | `97001b6f23e` 19:15:58Z | 480 lines | Adversarial stats: annualization error, non-CSCV PBO, non-DSR, 7.18-month OOS |
| `research/profitability/validation/VWAP_REPLICATION.md` | `97001b6f23e` 19:15:58Z | 301 lines | Independent replication with intrabar stops and concurrent-capital model |
| `research/profitability/HYPOTHESES.md`, `README.md` | `97001b6f23e` | 6 / 8 lines added | Hypothesis registry + protocol index update |

### 1.3 Worktree artifacts ≥18:30 (commit times)

| Worktree | Artifact | Time | Size | Description |
|---|---|---|---:|---|
| `finpredict` | `2026-11-14/finpredict/…/research/ITERATION-005.md` | 19:10Z (in doc) | 3,541 B | **"PROVEN"**: diversified vol-targeted trend, Sharpe 2.13, CI [1.25,3.25], t=5.56 |
| `finpredict` | `…/research/ITERATION-004.md` | 19:00Z (in doc) | 3,884 B | Trend method Sharpe 0.50; bootstrap CI still crosses zero |
| `finpredict` | `TRUE_PROFITABILITY_VALIDATED.md`, `PROFITABLE_APPROACH_PROVEN.md` | 18:58 | 5,462 / 4,969 B | Copies of the root flaxen claims |
| `finpredict` | `quick_wins/shared/{gated_scanner,daily_forward_tracker,normalize_pnl_units}.py` | 18:58 | 15,626 / 2,941 / 3,480 B | Scanner, tracker, unit normalizer |
| `finpredict-v4` | `research/PROFITABLE_SCORING_FRAMEWORK.md` | 18:59 | 16,448 B | 6-gate statistical scoring framework |
| `finpredict-v4` | `alpha_engine/statistical_scoring_framework.py` | 19:02 | 28,957 B | Implementation of the framework |
| `finpredict-v4` | `research/tradingview_contest_winner_research_2026-11-14.md` | 19:02 | 9,990 B | Contest-winner methodology research |
| `finpredict-v4` | `fix(resolver): exit_price fallback…` | HEAD `8689bac2245` | — | TIME_EXIT exit-price fallback + backfill |
| `flaxen-hair` | HEAD `3e41fe5026d` | 18:58:02Z | — | Mega-mutation validation + production enable |
| `finpredict-v3` | HEAD `eacd332779d` | — | — | Live-site JS/console/network spec + findings |
| `childlike-airport` | HEAD `1d9354ab9e2` | 2026-11-13 | — | Stale: branch predates today's VWAP claim; VWAP doc landed on `main`, not this HEAD |

### 1.4 Remote branches

| Ref | Tip | Commit time | Contents |
|---|---|---|---|
| `origin/audit/live-audit-2026-11-14` | `cc0226bdaf0` | 18:40:43Z (13:40 −0500) | deepAI FINAL audit (5 commits) + `inspect-wt` archive + `deepAI_proposed_fixes` |
| `origin/docs/scratch-hippodraco-audit-2026-11-14` | `1e5146bfe50` | 18:25:52Z | `scratch-hippodraco.MD` (258 lines) + 11-file quick-wins bundle |
| `origin/fix/audit-p0-truth` | `d1c1db68280` | — | P0 truth fixes (peer-implemented) |
| `origin/fix/audit-js-syntax-and-deploy-guard` | `ba1378cbfa9` | — | Pre-FTP `node --check` JS deploy guard |

**Local-only audit branches (not on `origin`):** `audit/finpredict-v2-{1602,1602b,1602c,1602d,nextdata,profitability,rereview1837,v34,vwap}`, `audit/hilarious-seer-quickwins-2026-11-14`, `audit/quant-multitest-2026-11-14`, `audit/quant-multitest-delivery`, `audit/quant-remediation-plan`, `audit-prediction-system-20261114-154529`, `kilo/audit-findings-2026-11-14`, `publish/ml-audit-2026-11-14`, `audit-asset-class-algorithms-and-data`. Their content is reachable only from this host; a synthesis run elsewhere cannot see them.

### 1.5 Root archive `2026-11-14/`

| Path | Files | Status |
|---|---|---|
| `2026-11-14/finpredict/2026-11-14T160004Z/` | README, `quick-wins/`, `master-plan/inputs/01..07`, `research/ITERATION-004/005` | Present |
| `2026-11-14/finpredict-v3/` | 5 timestamped sets: `155500Z`, `161500Z`, `161700Z`, `174500Z`, `175100Z`, `175500Z` | Present |
| `2026-11-14/finpredict-v2_20261114-1602/` | `MASTER_AUDIT.md` 35,323 B @19:08, `PEER_CROSSREF.md`, `INDEX.md`, `sub/`, `recommendations/`, `rereview/`, `raw/`, `actions_deepdive/` | Present (copy of our archive) |
| `2026-11-14/inspect-wt_*` | — | **ABSENT from root archive**; exists only on the audit branch |
| `2026-11-14/deepAI_*` | — | **ABSENT from root archive**; exists only on the audit branch |
| `2026-11-14/scratch-hippodraco-quick-wins/` | — | **ABSENT from root archive**; exists only on the scratch branch |

---

## 2. New profitability / "final" claims not covered by FP1–FP3

Six distinct claims now exist. FP1–FP3/Track A covered (a) flaxen mega mutation, (b) deepAI variant C, and (c) the path-to-profitability plan. The remaining three — ITERATION-005 trend, VWAP, and the quantified edge-search negative — were **not** reviewed before this pass.

| # | Claim | Author / artifact | Headline numbers | Status after this review |
|---:|---|---|---|---|
| C1 | `mega_mutation` CRYPTO is the only real edge | flaxen-hair · `TRUE_PROFITABILITY_VALIDATED.md`, `PROFITABLE_APPROACH_PROVEN.md` | forward n=50, WR 84%, PF 8.32; backtest PF 3.12–5.82 | Partially corroborated; **n/PF conflicts** (see §4.3) |
| C2 | Walk-forward selection variant C beats random | deepAI · `PROFITABLE_APPROACH_v1.md` | n=237, WR 47.3%, PF 1.26, +98.7pp, p<0.0013 | **Pilot-grade, not T2.** Explicitly self-limited |
| C3 | Diversified vol-targeted trend is "PROVEN" | finpredict-v1 · `ITERATION-005.md` | Sharpe 2.13, CI [1.25,3.25], t=5.56, OOS 2.33, 10/10 assets | **Methodologically plausible but not an alpha claim** (see §3.1) |
| C4 | `quan_engine` + `st_rsi` are blocked winners | finpredict-v4 · `PLAN_PATH_TO_PROFITABILITY.md`, `alpha_engine/pilot_verified_edges.py` | quan_engine 95.8% WR / +669%; st_rsi 65.1% WF / PF 2.53; SHORT 72.0% vs LONG 20.3% | **UNVERIFIED and pre-validation**: the plan itself schedules bootstrap for "next 24h"; HEAD blocks a toxic name variant |
| C5 | Regime-filtered VWAP is validated | childlike-airport · `updates/…VWAP-MEAN-REVERSION.md` | PF 1.21, Sharpe 3.76, DSR 1.0, MDD 10%, 129 trades, "~22 months OOS" | **FALSIFIED** by `97001b6f23e`: intrabar PF 0.81, Sharpe ~1.18, t=0.91 p=0.18, CSCV PBO 0.84–0.97 |
| C6 | No simple rule survives honest testing | research/profitability · `edge-search-results.md`, `SCORECARD.md` | 0/40 trials pass; 23 candidates NOT PROVED | **Strongest-supported negative**; survives its own pre-registered gates |

### 2.1 C1 — flaxen mega mutation (key sections read)

The two root docs state:
- Backtest PF 3.12–5.816, WR 64–76%, n=100–593; forward n=50, WR 84%, PF 8.32 since 2026-06-06.
- Task-10 benchmark on **n=8/n=9** per-strategy ledgers: PF 11.71 and 7.40; paired bootstrap passes 95% on 2 of 4; random-entry MC percentile 0.949 on one cell.
- `production_enable = true`, `promotion_ready = true` in `mega_mutation_state.json`.

Caveat stated by the author: "n=50 forward … continue paper trading before live capital." The claim of statistical validation rests on **n=8 and n=9** bootstrap ledgers for the two named mutations, not on n=50. This is a small-n statistical claim presented alongside a large-n forward claim; the synthesis must keep those separate.

### 2.2 C3 — ITERATION-005 trend (key sections read)

The document is unusually honest and therefore easy to mis-cite:
- Net CAGR 23.0%, vol 9.7%, Sharpe 2.13, MDD −17.4%, PF 1.40, WR 51.7%, t=5.56, bootstrap CI [1.25, 3.25].
- It states buy-and-hold of the same 10 assets had **Sharpe ≈ 2.2** in the same bull window. The trend method's advantage is **drawdown and volatility**, not raw risk-adjusted return vs B&H.
- It states survivorship (no LUNA/FTT), single asset class (crypto), and a bull-market window.
- The bootstrap is on **daily portfolio returns over 2,490 bars**, not on the project's T2 trade ledger; n (assets) = 10.

Therefore: "statistically positive absolute Sharpe" is a defensible statement; "provable alpha over buy-and-hold" is not. PF 1.40 and WR 51.7% also fail the project's own T2 charter (PF ≥ 1.5). The separate independent `SCORECARD.md` reaches **NOT PROVED** and scores actual profitability proof **0/10**.

### 2.3 C4 — `quan_engine` / `st_rsi` pilot (key sections read)

- The plan's own sequence is: build pilot now, "Next 24h: Bootstrap validation on verified edges", "Next 48h: If validation passes, promote." So the headline numbers were **not** bootstrap/OOS/DSR-validated when the claim was written.
- `alpha_engine/pilot_verified_edges.py` hard-codes `VERIFIED_SOURCES = {"quan_engine", "st_rsi_momentum_confluence"}` and `BLOCKED_VARIANTS = {"quan_engine_scalp", …}`.
- The current HEAD commit `bf6a8e310ac` ("fix(pilot): block toxic quan_engine_scalp…") records: `quan_engine_scalp` variants have **PF 0.39, −427% PnL**, and the pilot now emits **207 SHORT-bias picks, all SHORT**.
- This is a name-bucket claim with a same-family toxic variant and a 100% one-direction emission. It is not evidence of a validated edge; it is a hypothesis awaiting the tests the plan itself defers.

### 2.4 C5 — VWAP (key sections read)

The claim's own gates (PF 1.21 > 1.2, Sharpe 3.76, PBO 0.489, DSR 1.0, MDD 10%) all reproduce arithmetically. The independent review shows the statistics are mislabeled:
- The "DSR" is a hand-rolled one-sided z using an **annualized** Sharpe in a per-period SE formula. Proper DSR: 0.8285 (N=1), 0.0109 (N=960), 0.0022 (N=7,680).
- The "PBO" is a bootstrap tail p that is ~0.5 by construction; CSCV PBO is 0.840–0.970.
- OOS is **7.18 months**, not ~22; the 129-trade aggregate is the 8-symbol universe (5-symbol = 72).
- With intrabar stops: PF 0.81, return −17.4%, MDD 24.6%. At 40% per symbol, 5 concurrent = 280% gross exposure.

Verdict: claim withdrawn as a proof; the correct disposition is `NOT_PROVED`.

---

## 3. `inspect-wt` / `deepAI` final audit — review vs `MASTER_AUDIT.md`

### 3.1 Access status changed since the earlier integration note

`03_peer_reviews/inspect-wt_integration.md` (16:40Z) says the archive is **NOT PRESENT** on this host or `origin`. That is now **stale**. `origin/audit/live-audit-2026-11-14` exists at `cc0226bdaf0` and contains:
- `2026-11-14/deepAI_final_audit_20261114_1809/` — `AUDIT_FINAL.md`, `PROFITABLE_APPROACH_v1.md`, `TODO_profitable_approach.md`, `notes/01..05`, `notes/playwright_live_js_report.md`, `notes/evidence/*` (repricing 163,858 B, closed_stats, px samples, wf_last_seen).
- `2026-11-14/deepAI_proposed_fixes_20261114_1612/` — README, `cross_check_and_merge.md`, 8 fixspecs, 1 patch, 3 per-class quick-win files.
- `2026-11-14/inspect-wt_20261114_1058/reports_live_audit_2026-11-14/summary.MD` + `actions_api/*` (raw GitHub Actions JSON, ~1.7 MB per page file).

**Integration hazard:** `git merge-base origin/main origin/audit/live-audit-2026-11-14` returns **empty** in this clone (`fatal: … no merge base`). The previously-instructed cherry-pick range `fcac1d9017..0cd7a1204e` therefore cannot be applied as a normal range here. Files must be copied or the branch re-based deliberately; this is not a routine merge. Whether the histories are truly unrelated or the clone is grafted/shallow is `UNVERIFIED`.

### 3.2 Agreements with `MASTER_AUDIT.md`

| Finding | deepAI | MASTER | Verdict |
|---|---|---|---|
| Overall verdict | NOT profitable; multiple-testing artifact | FAIL | **AGREE** |
| 0/9 classes money-ready | cites `audit_surface_truth.json` | same | **AGREE** |
| Multiple testing | 361 + 285 = 646; ~32 expected FP; 69/80 OVERFIT_LIKELY; Reality Check never ran | 658 scored; 32.9 expected FP; 21 Bonferroni survivors all single-source | **AGREE in direction and arithmetic** |
| Survivorship | 2,262 inverse re-emissions; 129 dedup collisions; 3,872 spot-flicker dropped | 63% never resolve; 22,947 ghost rows; 49% survive gates | **AGREE** |
| Frozen / dead data | hyro 157 h stale; regime 21/8,538; 404 files | same, plus 10+ sidecars 79–245 d | **AGREE** |
| Units / zero PnL | 81% of priced open picks show 0; real mean −1.80% | 19/20 curated frozen at entry; raw 43–100% frozen by class | **AGREE** |
| Mutual funds | not built | NOT BUILT | **AGREE** |
| mega_mutation | PF 3.16–3.20, WR 64–72%, n≈18–295; pilot only | n=295, WR 64.1%, PF 3.16; sole PASS_ALL_AXES; pilot only | **AGREE** |
| Kalshi | real live API, 4 picks, 0 resolved | same | **AGREE** |

### 3.3 Differences (surface/population, not verdict) — and genuine contradictions

| Item | deepAI | MASTER | Classification |
|---|---|---|---|
| Open-pick population | 703 open-ish, 624 priced (89%) | 691 OPEN; 177 quoted; 123 non-zero PnL | **Population/clock** — deepAI uses `picks.active_raw` 16:15Z; MASTER mixes 14:30/16:15 payloads |
| Zero-PnL open share | 504/624 = 81%; mean −1.80%; real −1,116pp vs claimed −106pp | "19/20 curated frozen"; raw freeze 43–100% by class | **Same defect, different denominators** |
| EXPIRED inside `active_raw` | 3,272 / 4,164 (78.6%) | 3,377 / 4,148 | **Snapshot drift** (~1 h) |
| NEARUSDT | entry 3.324 → market 3.142 = +5.47% | entry 3.324 → 3.197–3.222 = +3.1–3.8% | **Quote clock** (~16:20 vs ~16:03). Not a contradiction |
| CRYPTO policy-clean PF | 0.232 registry (caveated) / 0.805 14-day | 0.2595 policy-clean net | **Near agreement**; deepAI flags possible 2026-06-04 backfill contamination |
| mega_mutation sample | n=18 in 3,500-row window; last 30d n=7 PF 1.58 | n=295 peer inventory / n=18 live check | **AGREE** |
| Negative/decayed forward edge | "last 30d n=7" | "even it is n≈18–295, not certified" | **AGREE** |

Genuine contradictions requiring synthesis resolution:

1. **mega_mutation magnitude.** flaxen (C1) claims forward **n=50, WR 84%, PF 8.32**. deepAI's live `recent_closed` check sees **n=18, WR 72.2%, PF 3.20** (last 30 d: n=7, PF 1.58). These are different populations (paper-pilot ledger vs system `recent_closed`), but the headline PF 8.32 and the system-visible PF 3.20 must not both be quoted as "the" forward result.
2. **Open-pick denominators.** 703 vs 691 and 624 priced vs 177 quoted cannot both be the "live open" count for the same clock. The synthesis must name the array and the timestamp for every count.
3. **CRYPTO PF surface.** MASTER 0.2595 (policy-clean net), scratch-hippodraco 0.92–0.93 (intrabar / `performance`), deepAI 0.81–0.805 (14-day `recent_closed`). These are four different surfaces; the number is not interchangeable.

### 3.4 Unique deepAI findings not in `MASTER_AUDIT.md`

- **`EURGBP=X` entry recorded as 688.17 vs market 0.835** (824× off), hiding a −99.9% loss as −0.63%.
- **Root cause of zero-PnL, precise:** peer report `reports/zero_pnl_data_pipeline_audit_2026-06-05.md` — 100% of 28,218 zero rows are `status=EXPIRED`, `resolution_method=TIME_EXPIRED`, from the `backfill_widened/updated` resolvers (81.2%/96.6% zero share); the time-expiry resolver writes `pnl_pct=0` instead of close-vs-entry. Per-class zero share: FUTURES 98.4% … CRYPTO 56.5%.
- **June ban not enforced on live emission:** `luxalgo_filter` = 16 rows, `prediction_market*` = 3 rows still in `active_raw`, despite the June ban list.
- **2026-06-04 closed_at backfill contaminated ~35,494 rows**; deepAI labels its own registry-derived PF numbers as possibly contaminated and says the 14-day recompute is clean. Any master synthesis using `pf_registry` must filter `DATE(closed_at) != '2026-06-04'`.
- **Sports leak:** `'MONTREAL CANADIENS VS BUFFALO SABRES'` appears as a trading `symbol`.
- **`asset_class` split:** `STOCKS` vs `EQUITY` are separate classes for the same asset.
- **`last_checked` batch stamp:** identical across hundreds of rows; not a per-pick check.

### 3.5 deepAI self-corrections that matter for the synthesis

`cross_check_and_merge.md` retracts two of its own earlier claims:
- "61% spot-flicker dropped" → not reproducible; registry rate **7.7% (2,188/28,460)**.
- "surfaces disagree = arbitrary filters" → actually **NOMINAL_TP_LEGACY vs intrabar truth**; intrabar is the trustworthy surface.
It also credits `mega_mutation` as the one genuine edge it initially missed.

---

## 4. `scratch-hippodraco` audit / quick-wins — review vs `MASTER_AUDIT.md`

Source: `origin/docs/scratch-hippodraco-audit-2026-11-14` @ `1e5146bfe50`; `scratch-hippodraco.MD` (258 lines) + `2026-11-14/scratch-hippodraco-quick-wins/` (README, 8 class files, `overall/OVERALL.md`, `peer-review/PEER_REVIEW.md`). Read-only audit; no code applied.

### 4.1 Agreements (strong; independent corroboration)

| Finding | scratch-hippodraco | MASTER | Verdict |
|---|---|---|---|
| Headline PnL untrustworthy | mixed units, stalled resolver, zombies | same FAIL | **AGREE** |
| Zombie backlog | 90,588 OPEN (86,064 >7 d); ~5–7 resolved/day | 90,523 / 143,156 never resolve | **AGREE**, same order |
| Active-count conflict | 20 / 158 / 4,148 | 20 / 158 / 263 / 4,148 | **AGREE** |
| Resolver frozen while dashboard claims fresh | 08:21–08:50Z; `stale_warning:false` | dashboard generated 14:30Z, payload fresh | **AGREE** |
| 0/9 money-ready on intrabar | CRYPTO 0.92, EQUITY 0.94, FOREX 0.66, ETF 0.02, BOND 0.39 | 0/9 T2; policy-clean PF 0.26 | **AGREE on verdict** |
| Mutual funds phantom | frozen Feb–Mar 2026; no class | NOT BUILT | **AGREE** |
| Regime coverage | 21 / 16,126 (0.1%) | 21 with regime / 8,538 without | **AGREE** |
| BOND is ETF proxies; FUTURES is % of price | TLT/HYG; no contract multiplier | BOND proxied; FUTURES n=13 | **AGREE** |
| Two classifiers | `asset_class.py` vs `config.py` | MASTER notes FOREX/COMMODITY misclassification | **AGREE** |
| 20 curated picks internally clean | 0 PnL-sign errors, median age 2.2 h | 19/20 frozen at entry | **Compatible**: clean ≠ priced |

### 4.2 New finding that `MASTER_AUDIT.md` does not have in its P0 set

**PnL unit mix in MySQL `at_signal_outcomes.pnl_pct`:** 17,632 rows stored as percent and **6,306 rows as a fraction** (same column); 5,400 of ~25k checkable rows mismatch recomputation by >0.5 pp; `trading_picks` has 3,543 mismatches. The generator "heals" it with `if abs(pnl) < 0.10: pnl *= 100` (`audit_trail/dashboard_generator.py:8065-8072`), which also turns a genuine +0.08% into +8%.

`FOLDER_REVIEW_SYNTHESIS.md` already recorded this as correction #13 ("PnL-unit bug is missing from our P0 list — Add to `QUICK_WINS.md`"). As of this sweep the correction is **still not applied to `MASTER_AUDIT.md`** and the unit bug is still absent from the P0 list. The final synthesis must adopt scratch-hippodraco's `QW-ALL-2` (percent-only at write, `pnl_source`, recompute-or-NULL, never magnitude-guess).

### 4.3 Additional scratch findings with no MASTER equivalent

- **Daily-bar vs intrabar inflation is quantified per class:** ETF daily PF 1.84 / WR 73% vs intrabar PF **0.02** / WR 2.2% (~85×); EQUITY 1.30 vs 0.94; COMMODITY 0.17 vs 1.03 (sign disagreement). This explains why "ETF looks good" and "ETF is broken" can both be true on different surfaces.
- **Three incompatible headline totals published side by side:** −62.65 (rolling-100 compound), −923.53 (raw sum), −99.0 (EW compound).
- **Kill switch coverage hole:** 177 strategies, only 56 evaluated, 42 killed, 121 never evaluated.
- **Slippage:** 76/198 strategies flagged, 38 CRITICAL; `forex_rsi2_mean_reversion` slippage = 48.5% of PnL.
- **Backtest-with-zero-forward:** `connors_rsi2` backtest WR 68.8% with `fwd_trades = 0`.
- **`ml_score` 98.1% zero/null in `recent_closed`**; `entry_time` missing 48.3%.
- **`summary.total_pnl_pct` naming:** it is a rolling-100 compound, not a sum.

### 4.4 Contradictions / surface mismatches vs MASTER (do not silently merge)

| Item | scratch | MASTER | Resolution needed |
|---|---|---|---|
| CRYPTO PF | 0.93 `performance`, 0.92 intrabar | 0.2595 policy-clean net | Name the surface; they are not the same statistic |
| ETF PF | 1.04 window, 0.02 intrabar | 1.8358 policy-clean (n=15) | All are small-n; none is a class edge |
| Headline total | −923.53 raw / −62.65 rolling-100 | −469.5% on 3,500-row window | Different populations (16,126 headline vs 3,500 window) |
| Walkforward age | 212 d (`walkforward.by_class`) | 161.6 d (`pilot_forward_dashboard`) | Different artifacts; both dead |
| `picks.active` health | "CLEAN, 0 sign errors" | "19/20 PnL = 0 identity" | Compatible; state both |
| BOND threshold | `thresholdPass:true` vacuously (`minTrades=0`) | BOND n=1 / 0% | **AGREE**, scratch adds the vacuity mechanism |

### 4.5 Scratch's own peer review (relevant to coverage)

`peer-review/PEER_REVIEW.md` independently rates:
- childlike-airport: **SOLID-WITH-CORRECTIONS** (SQLite evidence is peer-worktree-only; `live_picks.db` exists in main, 472K, Jun 3).
- flaxen-hair: **SOLID, most complete**, but its `normalize_pnl_units.py` is **partially unsafe**: it picks ratio as canonical and trusts `existing/100` when `|existing|>1`, so a genuine +150% becomes 1.5%; the `abs(v)<=1.0 → v*100` helper would turn 0.08% into 8%. This directly undercuts the `normalize_pnl_units.py` that C1's validation relied on.
- hilarious-seer: **WEAK/stubs**; model-roster/402 material is off-scope ops drift, not asset-class evidence.
- Rejects as stated: flaxen ETF dedupe snippet, any direct `UPDATE` without dry-run.

**Implication:** the mega-mutation C1 validation was produced in the same worktree whose normalizer a peer review calls partially unsafe. C1's numbers should be treated as `UNVERIFIED` until recomputed with the percent-at-write contract (QW-ALL-2). This is not evidence C1 is wrong; it is evidence it has not been independently re-derived.

---

## 5. `final_2026_11_14/` peer-folder check

**Result: no peer folders exist.** `final_2026_11_14/` contains exactly one subtree, `finpredict-v2/`.

| Subtree | Contents | Notes |
|---|---|---|
| `01_audit/` | `INDEX.md`, `MASTER_AUDIT.md`, `PEER_CROSSREF.md`, `sub/A..G`, `recommendations/{overall,per_asset_class,patch_plan,peer_review}` | `recommendations/peer_review/` **duplicates** `03_peer_reviews/` — two copies of PF1–PF5 + syntheses, risk of divergence |
| `02_research/profitability/` | protocols, `strategies.py`, `run_v1..v4.py`, `runs/v1..v4`, `validation/VWAP_*`, `SCORECARD.md`, forward ledger scaffold | Present |
| `03_peer_reviews/` | PF1–PF5, per-asset reviews (crypto/commodity, equity/ETF/bond/MF, forex/futures/CI), `overall_review.md`, `FOLDER_REVIEW_SYNTHESIS.md`, `REVIEW_SYNTHESIS.md`, `inspect-wt_integration.md`, `rereview_1837/RR1..RR3` | Documents only; no peer evidence copies |
| `04_actions/actions_deepdive/` | ACTIONS_DEEP_DIVE.md, GA1–GA4, 365-row matrix, raw logs | Present |
| `05_final/` | **empty** | Final synthesis not written |
| `06_evidence/` | `RAW_MANIFEST.md` only | No peer evidence archived |

Missing peer subtrees that the scope named: `finpredict/`, `finpredict-v3/`, `finpredict-v4/`, `flaxen-hair/`, `scratch-hippodraco/`, `hilarious-seer/`, `childlike-airport/`, `inspect-wt/`, `deepAI/`.

---

## 6. Coverage map

| Peer group | Evidence location | Reviewed by | Status |
|---|---|---|---|
| finpredict v1 | `2026-11-14/finpredict/…160004Z` | PF1; this sweep adds `research/ITERATION-004/005` | **Reviewed** |
| finpredict-v3 | `2026-11-14/finpredict-v3/…` (5 sets) | PF2 | **Reviewed** |
| finpredict-v4 (archive) | `audits/2026-11-14/finpredict-v4_2026-11-14-1555/` | PF3 | **Reviewed** |
| finpredict-v4 (post-18:59 research) | worktree `research/PROFITABLE_SCORING_FRAMEWORK.md`, `tradingview_contest…`, `statistical_scoring_framework.py` | **This sweep (inventory only)** | **NOT REVIEWED in depth** |
| flaxen-hair | root claims + worktree + `updates/2026-11-14-flaxen-hair.md` | scratch PEER_REVIEW; required by FP1/Track A | **Reviewed (claimed by FP1–FP3)** |
| childlike-airport ML audit | `updates/2026-11-14-ML-AUDIT-childlike-airport.md` | PF4 | **Reviewed** |
| childlike-airport VWAP claim | `updates/…VWAP-MEAN-REVERSION.md` + `research/…VWAP_*` | **This sweep** | **Reviewed; FALSIFIED** |
| hilarious-seer | `audit_quickwins`, summary | PF4 | **Reviewed** |
| scratch-hippodraco | `origin/docs/scratch-hippodraco-…` | **This sweep** | **Reviewed** |
| inspect-wt / deepAI | `origin/audit/live-audit-…` | **This sweep** (first access) | **Reviewed** |
| GA1–GA4 Actions | `04_actions/actions_deepdive` | GA1–GA4 | **Reviewed** |
| Quant audit / edge search / remediation | `updates/2026-11-14-quant-*`, `edge-search-results` | **This sweep** | **Reviewed (headline + gates)** |
| `audit/quant-multitest-2026-11-14` | local branch `f790fbb` | content = `updates/…quant-audit-multitest.md` | **Reviewed at root** |
| `audit/hilarious-seer-quickwins` | local branch `6929af0` | summary read | **Reviewed** |
| `audit/finpredict-v2-*` (our branches) | local only | self | **n/a** |

### What the final synthesis must include

1. **One verdict, three surfaces.** State "system as published is not profitable" (MASTER/deepAI/scratch agree) separately from "no strategy in the 683-zoo is T2-certified" (deepAI/edge-search) and "three pilot candidates exist but none is proven" (mega_mutation, variant C, trend).
2. **Adopt the PnL unit contract as P0.** Percent-at-write, `pnl_source`, recompute-or-NULL. Do not use flaxen's ratio-convention normalizer. This is the only way C1's numbers become citable.
3. **Reconcile the six claims in §2 explicitly.** Mark C3 as a positive absolute Sharpe but not alpha over B&H; mark C4 as pre-validation; mark C5 as falsified; keep C1 as pilot with n/PF conflict; keep C2 pilot-grade; adopt C6 as the honest negative.
4. **Name the array and clock for every count** (691 vs 703 open; 3,377 vs 3,272 EXPIRED; 0.26 vs 0.92 vs 0.81 CRYPTO PF).
5. **Correct `MASTER_AUDIT.md`** with the outstanding FOLDER_REVIEW_SYNTHESIS corrections: PnL unit bug in P0; fresh CRYPTO PF 0.9196/0.2628 provenance; `d8c8dd25581` gatekeeper flip; "8 empty + 2 non-empty" audit_trail tables; z=−22.69; FDR disabled not failing.
6. **Close the archive gaps:** materialize peer evidence under `final_2026_11_14/<peer>/`, write `05_final/`, and de-duplicate `01_audit/recommendations/peer_review/` vs `03_peer_reviews/`.
7. **State the deepAI branch integration hazard:** no merge base, copy-don't-merge, and do not apply destructive SQL/fixspecs.
8. **Include the 2026-06-04 backfill caveat** on every `pf_registry`-derived number.

---

## 7. UNVERIFIED

- **True worktree modification times.** Uniform `18:23/18:55/18:58/19:08` mtimes are checkout artifacts; only commit times are reliable.
- **Whether `origin/audit/live-audit-2026-11-14` is truly an unrelated history** or this clone is shallow/grafted. `merge-base` is empty; the cause is not established.
- **mega_mutation forward PF.** flaxen n=50/PF 8.32 vs deepAI n=18/PF 3.20 vs inventory n=295/PF 3.16. Not reconciled to one ledger with one unit contract.
- **C1's n=8/n=9 bootstrap ledgers** are too small to certify; the per-strategy PF 11.71/7.40 are not independently re-derived here.
- **C3 trend claim:** bootstrap on 2,490 daily bars, not trades; survivorship and B&H-Sharpe ≈ 2.2 acknowledged by the author; independent replication not performed.
- **C4 `quan_engine` 95.8% WR / +669%:** no bootstrap, OOS, or DSR artifact was found in the plan or pilot; the plan defers validation to "next 24h".
- **C4 pilot output "207 SHORT-bias picks"** was not executed or inspected as a ledger; only the commit message states it.
- **`pf_registry` contamination by 2026-06-04 backfill** (~35,494 rows) is asserted by deepAI from a peer report; not re-queried here.
- **`at_signal_outcomes` true `MAX(resolved_at)`** — `db_freshness.json` is itself 175 days old.
- **Exact `live_picks.db` counts** — peer-worktree-only; main-repo file exists (472K, Jun 3) but was not opened.
- **Whether the 15 local-only audit branches are recoverable from any other host** — not on `origin`.
- **Root `2026-11-14/` archive completeness** — `inspect-wt`, `deepAI`, and `scratch` folders are absent there; only `finpredict`, `finpredict-v3`, `finpredict-v2` are present.
- **The `fix/p0-safe-fixes-2026-11-14-main` HEAD state** — `bf6a8e` blocks `quan_engine_scalp`; whether the rest of the C4 plan was reverted is not established.

---

## 8. Top 6 findings

1. **Coverage FAIL at the archive layer:** `final_2026_11_14/` has no peer folders and `05_final/` is empty, even though all seven worktrees and both named remote branches were inventoried and read. `01_audit/recommendations/peer_review/` duplicates `03_peer_reviews/`.
2. **The previously "missing" deepAI/inspect-wt archive is now on origin** (`audit/live-audit-2026-11-14` @ `cc0226b`). `inspect-wt_integration.md` is stale. The branch has **no merge base** with `origin/main`, so it must be copied, not merged.
3. **Six profitability claims coexist; only one is already falsified and none is T2-certified.** C1 mega_mutation (PF 8.32 n=50 vs system PF 3.20 n=18), C2 variant C (PF 1.26, pilot), C3 trend (Sharpe 2.13 but not alpha over B&H), C4 quan_engine (pre-validation), C5 VWAP (**falsified**: PF 0.81, t=0.91), C6 edge search (**0/40, NOT PROVED**).
4. **The PnL unit-mix bug is still missing from `MASTER_AUDIT.md`'s P0 list.** scratch-hippodraco quantifies it (17,632 percent vs 6,306 fraction; 5,400 mismatches >0.5 pp) and the generator's `|pnl|<0.10 → ×100` heuristic. This is the single highest-correctness impact item and it also invalidates citing C1 until fixed.
5. **deepAI and scratch both independently confirm the MASTER verdict** (0/9 money-ready, ~90k zombie OPEN, frozen resolver, mutual funds phantom, multiple-testing artifact). The contradictions are **surface/population** (691 vs 703 open; 3,377 vs 3,272 EXPIRED; CRYPTO PF 0.26 vs 0.92 vs 0.81), not verdict-level — every count must name its array and clock.
6. **The strongest evidence-based negative is the new independent research:** `edge-search-results` (0/40), `SCORECARD` (23 candidates, NOT PROVED, 0/10 on actual proof), and `VWAP_VERDICT` (falsified). The final synthesis should lead with this negative and treat the three pilots as `PILOT / NOT CERTIFIED`, not as proven profitability.

---

*FP4 sweep complete, 2026-11-14T20:20Z. Read-only; no repo source modified. Peer claims are attributed to their authors and artifacts; items that could not be checked directly are marked `UNVERIFIED`.*
