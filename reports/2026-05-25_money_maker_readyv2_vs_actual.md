# /money-maker-readyv2 — Skill vs Actual Performance Audit — 2026-05-25

**Author:** claude-opus-4-7 (review-only; skill not re-run)
**Scope:** compare the v2 skill's stated success bar against the most recent verdict-grade numbers on disk.
**Crypto-deep-dive caveat:** another agent is investigating CRYPTO's "78% claim" — this report records CRYPTO numbers but does not duplicate the DB work.

---

## 1. Skill summary (what v2 claims it delivers)

Source: `.claude/skills/money-maker-readyv2/SKILL.md` (skill version unstamped, post-v1.1 extension).

**Goal:** produce per-asset-class filters that a hedge-fund manager would size with real capital. "Real-money-grade" is operationally defined as **PF≥1.5 / WR≥50% / MDD≤20% / sample-tier from `asset_class_health`**, with a computed Kelly position size per pick.

**Success criteria (ALL must be true to call done):**

| # | Class    | Bar |
|---|----------|-----|
| 1 | EQUITY   | weekly filter shows ≥5 picks with elite_score≥60, WR≥55% on historical analogs (n≥30/bucket), PF≥1.5 on resolved |
| 2 | CRYPTO   | sub-class filters identified, WR≥50%, PF≥1.5 on resolved_n≥100 |
| 3 | COMMODITY| post-COT-dedup n≥50, top strategy PF≥1.5 |
| 4 | ETF      | n≥150 toward OOS_READY, PF≥1.3 |
| 5 | FOREX    | mutation protocol in progress; directional filter WR≥50% if any |
| 6 | BOND     | n≥20, top strategy identified |
| 7 | Kelly    | every weekly-filter pick has computed % via `compute_position_size()` + DD-halt |

**Weekly filter output:** `reports/weekly_filter_<UTC>.md` per Step 5 of the skill — must list per-class filter (criteria + expected WR/PF + Kelly sizing + how-to-apply UI steps + risk controls).

**Autonomous execution rules (NON-NEGOTIABLE):** PLAN FIRST, work autonomously, self-verify every step, debug yourself, no placeholders, progress log, check success before stopping. Freshness gate fails fast if `dashboard_data.json` >2h old. Hard rules inherited from v1.1 (no class-wide BLOCKED edits without approval, no `(asset_class | n | timeframe)` claim w/o triple, etc.).

---

## 2. Actual current per-class state

**Primary verdict source:** `audit_dashboard/data/money_ready_verdict.json` (generated 2026-05-24T07:24Z by `alpha_engine/money_ready_verdict.py --json`). This is the **post-PR-#1183, post-concentration-gate, DSR/PBO/SPA-aware** verdict file — newer + stricter than `asset_class_health`.

**Secondary source (also checked):** `audit/data/dashboard_data.json` — file mtime 2026-05-23 but `generated_at` is 2026-04-11 (stale by ~1062h; freshness preflight would HARD-FAIL). The auto-refresh pipeline is broken or hasn't run for this artifact. `audit_dashboard/data/dashboard_data.json` does not exist at the path the SKILL specifies.

| Class      | v2 PF target | Actual PF | v2 WR target | Actual WR | n   | Top sym (concentration) | Verdict       |
|------------|--------------|-----------|--------------|-----------|-----|-------------------------|---------------|
| EQUITY     | ≥1.5         | **0.897** | ≥55%         | **33.3%** | 33  | AMD (39.4%)             | **FAIL** + INSUFFICIENT-N |
| CRYPTO     | ≥1.5         | **1.145** | ≥50%         | **43.4%** | 728 | BTCUSDT (18.3%)         | **FAIL** (n OK; PF/WR miss); MDD=1.0 (catastrophic) |
| COMMODITY  | ≥1.5         | **0.309** | (n≥50)       | **10.7%** | 28  | CT=F (57.1%)            | **FAIL** + INSUFFICIENT-N + concentration breach |
| ETF        | ≥1.3         | 11.99     | —            | 50%       | 2   | ARKK (100%)             | **INSUFFICIENT-N** (n=2 vs target 150) |
| FOREX      | (dir filter) | **0.547** | ≥50%         | **39.6%** | 53  | USDJPY=X (54.7%)        | **FAIL** + concentration breach |
| BOND       | (n≥20)       | 0.0       | —            | 0%        | 8   | TLT (37.5%)             | **INSUFFICIENT-N** (n=8 vs target 20) |
| FUTURES    | (not in v2)  | 0.956     | —            | 16.7%     | 12  | CL=F (33.3%)            | n/a |
| PENNY_STOCK| (not in v2)  | 0.0       | —            | 0%        | 1   | SOFI                    | n/a |

**Drift between 2026-05-21 → 2026-05-24 (3 days, from `money_ready_verdict.json::drift.per_class`):**

- **FOREX**: WATCH → NOT_READY (wr_delta −0.150, pf_delta −0.862, n_delta −99, gate flips: dsr_ok T→F, spa_ok T→F).
- **COMMODITY**: WATCH → INSUFFICIENT_DATA (wr_delta −0.410, pf_delta −0.930, n_delta −30). The headline `cot_positioning` PF 4.64 from the 2026-05-17 v2 report appears to have collapsed.
- **EQUITY**: NOT_READY → INSUFFICIENT_DATA (n_delta −22). Resolved-pick set is shrinking.
- **CRYPTO**: NOT_READY → NOT_READY (wr_delta +0.051, pf_delta +0.015, n_delta +156).

**Net: ZERO classes pass the v2 bar today. Three classes that were "WATCH/NOT_READY" with at least directional edge 3 days ago have DEGRADED.**

---

## 3. Has the v2 skill actually run? What deliverables exist?

**Weekly-filter outputs (the skill's Step-5 deliverable):**
- `reports/weekly_filter_2026-05-16.md` / `.json` (the canonical "filter day")
- `reports/weekly_filter_20260516T*Z.md` × 5 (intra-day re-runs)
- `reports/weekly_filter_2026-05-17.md` + `.json` + 3 intra-day variants
- `reports/weekly_filter_2026-05-18T04-33Z.md` + `weekly_filter_20260518T0851Z.md`

Latest = **2026-05-18** — **NO weekly_filter has been produced in the last 7 days**, despite `.github/workflows/weekly-filter.yml` existing. That workflow may be broken or skipping (was not investigated in this review; flag for follow-up).

**v2-specific deliverables:**
- `reports/money_maker_readyv2_2026-05-17.md` — last full v2 run, contains the corrigendum that retracted both Tier-1 claims after the concentration-gate check.
- `reports/MONEY_MAKER_READYV2_ADDENDUM_TODOS_2026-05-19T0010Z.md`
- `reports/MONEY_MAKER_READYV2_FREEBUFF_INTEGRATION_2026-05-19T0030Z.md`
- `reports/MONEY_MAKER_READYV2_NORTH_STAR_2026-05-19T2350Z.md` — last v2 artifact.

**Last v2 activity: 2026-05-19. 6-day gap to today.**

**Daily verdict snapshots (running):** `audit_dashboard/data/money_ready_archive/money_ready_<DATE>.json` 2026-05-17 → 2026-05-24 (8 consecutive days). The `money-ready-snapshot.yml` workflow IS working. So the *data pipeline* is alive; only the *human-readable v2 deliverable + weekly filter* have stalled.

---

## 4. Gap diagnosis — why the skill ran but didn't move the metrics

### Gap A — The two "real edges" from v2's last run were data artifacts, not edges

The 2026-05-17 v2 report self-corrects (corrigendum):
- `cot_positioning` PF 4.64: 85.1% of picks were CT=F (cotton) — same COT-row-duplication artifact that retired `cftc_cot_commercial_signal`. Excluding CT=F: n=20, WR 30%, PF 0.51.
- `cta_cross_asset_tsmom` SHORT WR 65.8% PF 2.89: 93.2% USDJPY=X (109/117) — single-pair USDJPY-short, not a class edge. Excluding USDJPY: n=8.

DSR/SPA "passed" both because they only test the return series, not symbol concentration or upstream data integrity. **The skill's gate stack is missing concentration as a hard early filter — and confirms it on the next page, but doesn't enforce it before "PASS".**

### Gap B — Sample sizes have COLLAPSED post-stricter resolver/filtering

`money_ready_verdict.json` 2026-05-24 numbers vs v2's 2026-05-17 baseline:
- COMMODITY: 326 → 28 (post-COT-dedup + post-concentration-cap)
- FOREX: 152 → 53 (LONG block + USDJPY-cap)
- EQUITY: 55 → 33 (resolver tightening)
- BOND: 17 → 8
- ETF: 87 → 2

This is partly *correct* (noise removed) and partly *fatal* — n is now too small to clear v2's own n-floors. The skill's bar (n≥100 for CRYPTO PF, n≥150 for ETF, n≥50 for COMMODITY, n≥20 for BOND) is FURTHER from being met than it was a week ago.

CLAUDE.md cites the old `asset_class_health` numbers (CRYPTO n=8067, COMMODITY n=750, FOREX n=1169, EQUITY n=421, ETF n=87, BOND n=18 as of 2026-05-03). The `money_ready_verdict.json` numbers are 10-100× smaller. The two systems are not citing the same `n` — confirming the v1.1 "`n`-citation discipline" warning is being violated by the dashboard's own JSONs.

### Gap C — Weekly-filter automation has stalled

7 days since last weekly_filter output. Cron may have stopped. The skill specifies `git commit` + `git add` at Step 7; if the workflow's `gh push` is gated by CI green and CI has been red, the artifact never lands.

### Gap D — Drift is real and unmonitored

3 of 6 classes flipped verdicts (FOREX, COMMODITY, EQUITY) in 72h. The skill's drift detection lives in `drift.per_class` — it's *computed* but no recipient acts on it. There is no "drift → auto-pause" wiring beyond writing the JSON.

### Gap E — The skill points to a path that doesn't exist

SKILL.md repeatedly cites `audit_dashboard/data/dashboard_data.json` — that file is not on disk. The live equivalent is `audit/data/dashboard_data.json` (and it is 1062h stale). The freshness preflight as written would `assert age_h < 2` and abort immediately if anyone actually ran it.

---

## 5. What would actually move the needle (ranked)

1. **P0 — Wire concentration as a HARD pre-filter inside `money_ready_verdict.py`.** Reject any verdict where top_symbol_share > 30% before computing DSR/PBO/SPA — currently `top_symbol_share` is recorded (`COMMODITY.CT=F 0.57`, `FOREX.USDJPY=X 0.55`) but `concentration_capped: false` shows the gate is not enforced. This single fix would have blocked both 2026-05-17 false-Tier-1 claims at the source.

2. **P0 — Fix the dashboard_data.json path drift.** Decide: is `audit_dashboard/data/dashboard_data.json` or `audit/data/dashboard_data.json` canonical? Update the skill + repair the refresh cron for whichever one wins. Right now both are wrong/stale and the skill can't run cleanly.

3. **P0 — Fix the `weekly-filter.yml` workflow.** Diagnose why no weekly_filter_*.md has been produced since 2026-05-18 (`gh run list --workflow=weekly-filter.yml --limit 10`). Without this, v2's Step-5 deliverable doesn't exist for end users.

4. **P1 — Reconcile the two `n`-counters.** `asset_class_health.n` (~hundreds-to-thousands) vs `money_ready_verdict.classes.n_resolved` (~tens). One filters more aggressively. Document which one is the "real-money n" and update CLAUDE.md + SKILL.md to cite that one consistently.

5. **P1 — Lower v2's class-level bar OR move v2's bar to strategy-level explicitly.** Today's reality (CRYPTO n=728 PF 1.14, no other class with n>53) means **no class will pass a class-aggregate PF≥1.5 / WR≥50% / n≥100 gate in 2026 absent a fundamental edge breakthrough**. The 2026-05-17 v2 report already moved to per-strategy verdicts and got fooled by concentration. The path forward is strategy×symbol×direction triples with n≥30 each + the concentration gate from action 1.

6. **P1 — Add drift-auto-pause.** When `drift.per_class.<CLASS>.verdict_changed == true && wr_delta < -0.05`, surface to operator and auto-tag the class "PAUSE" in the dashboard. Today the drift block is written but ignored.

7. **P2 — Build a real n-budget per class.** Today the only class with v2-relevant n is CRYPTO. Per-class n is constrained by upstream emitter throughput + the resolver's strictness. Without growing emitters (CRYPTO is fine, EQUITY/ETF/BOND are emitter-starved), no v2 bar will ever be crossed for those classes. This is a strategy decision the skill cannot solve — flag for human.

---

## 6. TL;DR

- **Skill bar:** PF≥1.5 / WR≥50% / MDD≤20% per class, n-floors per class, weekly filter doc + Kelly sizing.
- **Actual:** 0/6 classes meet the bar on `money_ready_verdict.json` 2026-05-24. CRYPTO has n but no PF/WR; everyone else lacks n. COMMODITY/FOREX/EQUITY drifted *worse* in the last 72h.
- **Skill outputs:** last weekly_filter 2026-05-18, last v2 artifact 2026-05-19. 6-7 day gap.
- **Root causes (top 3):** (a) concentration gate not enforced before DSR/SPA; (b) dashboard JSON path mismatch + 1062h stale; (c) weekly-filter cron stalled.
- **Top 3 actions:** (1) concentration as hard pre-filter; (2) fix dashboard path + freshness pipeline; (3) repair weekly-filter.yml.

**Files referenced:**
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/.claude/skills/money-maker-readyv2/SKILL.md`
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/.claude/skills/money-maker-ready/SKILL.md`
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/audit_dashboard/data/money_ready_verdict.json`
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/audit_dashboard/data/money_ready_archive/money_ready_2026-05-{17..24}.json`
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/audit/data/dashboard_data.json` (stale)
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/reports/money_maker_readyv2_2026-05-17.md`
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/reports/MONEY_MAKER_READYV2_NORTH_STAR_2026-05-19T2350Z.md`
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/reports/weekly_filter_2026-05-18T04-33Z.md` (most recent)
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/reports/hedge_fund_performance_review_summary_2026_04_27.md`
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/.github/workflows/weekly-filter.yml`
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/.github/workflows/money-ready-snapshot.yml`
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/money_ready_verdict.py`
