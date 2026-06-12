# Session Complete — Audit Edge Hunt & PM Actions

**Agent:** Cursor (Composer)  
**Dates:** 2026-06-11 → 2026-06-12 (EST)  
**User request:** Hostile review of money-ready master loop; find hidden edges on `/audit`; debug 0/8 profitable asset classes; root-cause `picks-now.html` 21.1% forward WR; verify tournament/leaderboard claims; document PM todos and investigation skill.

**Canonical wrap:** this file. Related artifacts listed in §8.

---

## 1. Tasks completed ✅

### Investigation & documentation

| # | Task | Status | Evidence |
|---|------|--------|----------|
| 1 | Hostile quant review of `MONEY_READY_MASTER_LOOP_2026-06.md` | ✅ Done | `CURSOR_JUNE112026.MD` (Parts I–IX) |
| 2 | Per-class proven-winner hunt on intrabar deduped ledger | ✅ Done | `reports/per_class_winners_2026-06-11.md`, `.json` |
| 3 | Strategy pass-hunter (T2 + R1/R2/R3) | ✅ Done | `tools/strategy_pass_hunter.py`, `reports/strategy_pass_hunter_2026-06-11.json` |
| 4 | June 2026 research pipeline (30 hypotheses, OHLC proxy BT) | ✅ Done | `tools/june2026_strategy_research_pipeline.py`, `alpha_engine/june2026_research_candidates.py` |
| 5 | P0/P1 plan markdowns from master loop gaps | ✅ Done | `docs/plans/2026-06-12-P0*.md`, `P1*.md` |
| 6 | Full `/audit` surface audit (user prompt) | ✅ Done | `PLAN_INSIGHTS_CURSOR_June122026_638PM.MD` |
| 7 | PM action todo backlog | ✅ Done | `docs/todos/PM_ACTIONS_JUNE12_2026.md` |
| 8 | Investigation skill + slash command | ✅ Done | `.claude/skills/thingstocheck-june2026/SKILL.md`, `.claude/commands/thingstocheck-june2026.md` |
| 9 | DB-verify tournament WR claims | ✅ Done | See §4 — gpt4_1, kimi_direct |
| 10 | Root-cause picks-now 21.1% WR | ✅ Done | See §4 — stale track record |
| 11 | Validate pick_funnel / intrabar_truth alignment | ✅ Done | 0/6 money-ready, DISPUTED banner accurate |
| 12 | Explain ai_leaderboard “only one model” perception | ✅ Done | min_n_ranked=20 → 2 classified engines |
| 13 | Portfolio history staleness assessment | ✅ Done | Generator stale; freeze recommendation |
| 14 | Session documentation (this file) | ✅ Done | `reports/SESSION_COMPLETE_CURSOR_June122026_AUDIT_EDGE_HUNT.MD` |

### Code / tooling shipped in session arc

| Artifact | Purpose |
|----------|---------|
| `tools/strategy_pass_hunter.py` | Scan sleeves for T2 + discipline gates |
| `tools/per_class_winner_hunt.py` | PROVEN / PROBATION / WATCH ladder per class |
| `tools/stamp_entry_conditions.py` | Entry-side stamps (`crypto_us_monday`, `equity_mom_with`, etc.) |
| `alpha_engine/june2026_research_candidates.py` | 20 v2 + forward observation emitters |
| `tools/june2026_strategy_research_pipeline.py` | Registered hypothesis backtest run |

---

## 2. Tasks remaining ⏳

### P0 — Stop bleeding (this week) — **NOT IMPLEMENTED**

| ID | Action | Owner | Verify |
|----|--------|-------|--------|
| P0-1 | Fix **luxalgo SHORT emission** (scanner returns 0; probation n stuck at 38) | `june2026_research_candidates.py`, `priority_picks_emitter.py` | `_generate_luxalgo_short_v2()` len > 0 |
| P0-2 | **Block CRYPTO LONG** at emitter (M-036 extension) | `config.py`, `emitter_discipline.py` | Intrabar LONG WR ~34%, PF ~1.02 |
| P0-3 | Ship **hourly intrabar reresolve** in GHA | `docs/plans/2026-06-12-P0A-intrabar-hourly-reresolve-plan.md` | New resolutions after 2026-06-10 |
| P0-4 | Kill **fear-greed CRYPTO LONG** from daily batch | `st_fear_greed_contrarian_winner` | Emitter dry-run: 0 CRYPTO LONG |
| P0-5 | **Refresh picks-now** track record + resolver | `picks_now_professional.py`, `resolve_picks_now.py` | WR panel updates daily; n grows |

### P1 — Measurement honesty (2 weeks) — **NOT IMPLEMENTED**

| ID | Action |
|----|--------|
| P1-1 | Star tab: **symbol×direction FWD WR** (not strategy-level WR) |
| P1-2 | Tournament UI: show **MISPRICED_ENTRY** counts beside headline WR |
| P1-3 | pick_funnel: hourly Smart Picks DB ground truth refresh |
| P1-4 | Intrabar replay **COMMODITY gold_overnight_gap_fade** (BT proxy only today) |
| P1-5 | FOREX live block **F1=CONTRARIAN** (76% loss capture in experiments) |
| P1-6 | Portfolio history: regen from intrabar truth or **deprecate with banner** |

### P2 — Institutional playbook (4 weeks) — **NOT IMPLEMENTED**

| ID | Action |
|----|--------|
| P2-1 | **2 focus classes only** — CRYPTO luxalgo SHORT + COMMODITY gap-fade confirm |
| P2-2 | Kill **12/16 june2026 v2 emitters** without intrabar support |
| P2-3 | **Monkey test + stress matrix** before PROBATION→PROVEN |
| P2-4 | **Growth-stock screener** integration for picks-now ([starboi-63/growth-stock-screener](https://github.com/starboi-63/growth-stock-screener)) |
| P2-5 | **research_index → hypothesis registry** wire-up |

### Forward lane / master loop gaps (from `CURSOR_JUNE112026.MD`)

| Gap | Status |
|-----|--------|
| Forward lane stalled — zero new intrabar resolutions since ~2026-06-10 noon | ⏳ P0-3 |
| H2 unscoreable while walk-forward stale (#132) | ⏳ P1 |
| Discovery guardrails prose-only (monkey test, FDR batch) | ⏳ P2-3 |
| Portfolio books untrusted until `performance.py` ships | ⏳ P1-6 |

---

## 3. Achievements 🎯

1. **Honest baseline established** — 0/8 asset classes PROVEN on intrabar deduped ledger; no fabricated “hidden edge” in any filter combination audited.
2. **One disciplined probation sleeve identified** — `luxalgo_confluence × CRYPTO × SHORT` (n=38, WR 71.1%, PF 2.21, full R1/R2/R3 pass).
3. **Tournament claims verified in MySQL** — gpt4_1 55.6% WR is arithmetic on WIN/LOSS only; 75/117 rows correctly quarantined as MISPRICED_ENTRY.
4. **kimi_direct bias debunked** — exclusion logic working; do not nuke tournament data; reresolve + geometry backfill instead.
5. **picks-now failure explained** — 21.1% WR = 4W/15L on 19 stale resolved rows (Jun 9 freeze), EQUITY STRONG_BUY SL geometry, not a sizing surface.
6. **pick_funnel validated** — DISPUTED CRYPTO banner + 0/6 money-ready matches `intrabar_truth_by_class.json`.
7. **Investigation skill + command** — repeatable `/thingstocheck-june2026` workflow with `PLAN_INSIGHTS_*` output convention.
8. **PM backlog prioritized** — P0 stop-bleed before P2 breadth (50 tournament models, 0 proven classes).

---

## 4. Findings (evidence-backed)

### 4.1 Hidden edge on `/audit`?

**No.** No filter combination (high-conviction, smart picks, proven only, best score, star active picks) surfaces a class that passes institutional Tier-2 on honest intrabar truth.

| Class | n (intrabar) | WR | PF | Verdict |
|-------|--------------|-----|-----|---------|
| CRYPTO | 1154 | 32.4% | 0.73 | FAIL |
| EQUITY | 107 | 34.6% | 0.47 | FAIL |
| COMMODITY | 90 | 41.1% | 1.39 | INSUFFICIENT_N |
| FOREX | 88 | 42.0% | 1.13 | INSUFFICIENT_N |
| ETF | 16 | 0.0% | 0.0 | INSUFFICIENT_N |
| BOND | 6 | 33.3% | 2.24 | INSUFFICIENT_N |
| FUTURES | 7 | 28.6% | 0.22 | FAIL |
| MEMECOIN | 77 | 26.0% | 0.58 | INSUFFICIENT_N |

**Source:** `audit_dashboard/data/intrabar_truth_by_class.json`, `money_ready_verdict.json` (2026-06-12).

### 4.2 Best probation unit

| Field | Value |
|-------|-------|
| Strategy | `luxalgo_confluence` |
| Class | CRYPTO |
| Direction | SHORT |
| n | 38 |
| WR | 71.1% |
| PF | 2.21 |
| Wilson LB | 55.2% |
| Discipline | R1/R2/R3 pass, MC 99.8th pctile vs coin flip |
| **Blocker** | Emitter ships **0** luxalgo SHORT v2 picks → forward n not growing toward 100 |

### 4.3 picks-now.html forward-tested 21.1% WR

| Metric | Value |
|--------|-------|
| Last generated | 2026-06-09T19:19:11Z |
| Resolved | 19 / 100 symbol-days tracked |
| Won / Lost | 4 / 15 |
| WR | 21.1% |
| Cum PnL | −44.3% |
| Dominant pattern | EQUITY STRONG_BUY → SL_HIT within 0–1 days (AAPL, AMD, etc.) |

**Root causes:** tiny sample, stale pipeline, wrong hypothesis (valuation longs vs intrabar EQUITY FAIL), missing growth/momentum filters.

### 4.4 Tournament / model claims

**gpt4_1** (`tournament_picks`, resolved):

```text
WIN: 20 | LOSS: 16 | MISPRICED_ENTRY: 75 | OPEN: 6
Decisive WR = 55.56% — matches ai_tournament_leaderboard.json
Not money-ready: 64% of resolved rows quarantined; wide PF CI
```

**kimi_direct:**

```text
WIN: 29 | LOSS: 18 | MISPRICED_ENTRY: 47
Decisive WR ≈ 61.7%; leaderboard 60.9% on n=46 after exclusions
Do not nuke — quarantine is correct behavior
```

**ai-tournament.html:** 45 models with n_resolved>0; page labels tournament **research-only** vs policy-clean sizing — **NOT MONEY-READY everywhere is correct**.

### 4.5 Dashboard pages audited

| URL | Finding |
|-----|---------|
| `/audit/` | 0/9 intrabar pass; high-conviction/smart picks historical inflation |
| `/audit/picks-now.html` | 21.1% WR — stale, not edge |
| `/audit/pick_funnel.html` | Accurate; keep DISPUTED banner |
| `/audit/ai-tournament.html` | Live; kimi_direct rank 1 on subset |
| `/audit/ai_leaderboard.html` | Index stale 2026-06-09; only 2 engines “classified” at min_n=20 |
| `/audit/portfolio_history.html` | Stale generator; heavy EW losses — freeze or deprecate |
| `/audit/research_index.html` | 30+ hypotheses registered; 0 intrabar PROVEN wired to emitter |

### 4.6 OHLC proxy only (not intrabar-confirmed)

| Sleeve | Class | n | PF | Status |
|--------|-------|---|-----|--------|
| gold_overnight_gap_fade | COMMODITY | 108 | 1.92 | PROXY — needs intrabar replay |
| volume_spike_fade | PENNY | — | T2 proxy | PROXY — needs intrabar replay |

---

## 5. Areas needing deep-dive 🔬

Priority-ordered. Each should spawn `reports/deep_dive_<topic>_*.md` per CLAUDE.md Goal #1.

### 5.1 P0 — Measurement & emission (immediate)

| Topic | Why | Suggested owner / repro |
|-------|-----|-------------------------|
| **luxalgo SHORT emission failure** | Only probation sleeve; 0 forward picks | Trace `priority_picks_emitter` → scanner → DB symbols; compare to intrabar winners |
| **CRYPTO LONG bleed** | Class baseline WR 32.4%; LONG ~34% WR | `emitter_discipline.py`, M-036 extension, fear-greed source kill |
| **Forward lane stall** | No new intrabar resolutions since Jun 10 | P0-A GHA hourly `reresolve_intrabar_signal_outcomes.py` |
| **picks-now resolver geometry** | 4% SL hits on STRONG_BUY in 1 day | `tools/resolve_picks_now.py`, split-aware prices, entry filters |

### 5.2 P1 — Data quality & UI honesty

| Topic | Why |
|-------|-----|
| **Star tab FWD WR vs strategy WR** | Users see strategy registry WR, not symbol×direction forward truth |
| **MISPRICED_ENTRY transparency** | gpt4_1 headline 55.6% hides 75 quarantined rows |
| **Reverse split / sign-flip contamination** | User called out; run fabrication-red-team on WR>55% cells |
| **Active-pick-limit bias** | Cap may exclude losers from denominator |
| **Smart Picks DB vs nav matrix** | Historical 78.9% CRYPTO cohort untracked |

### 5.3 P2 — Strategy & external replication

| Topic | Why |
|-------|-----|
| **COMMODITY gap-fade intrabar replay** | Only OHLC proxy T2 today; compare vs DBMF/KMLM |
| **FOREX trend-aligned filter** | PF 4.74 at n=14 — worth n→30 watch, block CONTRARIAN |
| **EQUITY mom-WITH filter** | PF 2.17 at n=24 — R1/R2 fail; entry selection not geometry |
| **12/16 v2 emitter kill list** | Batch emits 44 picks, none luxalgo SHORT; velocity over breadth |
| **Growth-stock screener for picks-now** | Replace valuation-only STRONG_BUY hypothesis |
| **Portfolio history resurrection** | Only if wired to intrabar_truth + kill list |
| **ai_leaderboard throughput** | 43 engines, 31 resolved index-wide — resolver or min_n policy |

### 5.4 Known master-loop gaps (from hostile review)

| ID | Gap |
|----|-----|
| H2 | Walk-forward stale — promotion unscoreable |
| Addendum B | Monkey test + stress matrix not enforced |
| Portfolio math | Pre-fix NAV sign rows remain trust hazard |
| Concentration gate | Not enforced before DSR/SPA → false Tier-1 PASS history |

---

## 6. Recommended execution order

```
P0-1 luxalgo SHORT emit  →  P0-2 block CRYPTO LONG  →  P0-3 hourly reresolve
        ↓
P0-5 refresh picks-now   →  P1-1 symbol FWD WR on Star tab
        ↓
P1-4 COMMODITY intrabar replay  →  P2-1 two-class focus  →  P2-2 kill bad emitters
```

Do **not** size up on tournament or picks-now headline WR until intrabar forward lane accrues n≥100 on a disciplined sleeve.

---

## 7. Reproducer commands

```bash
# This session doc
cat reports/SESSION_COMPLETE_CURSOR_June122026_AUDIT_EDGE_HUNT.MD

# PM todos
cat docs/todos/PM_ACTIONS_JUNE12_2026.md

# Plan insights (June 12 audit)
cat PLAN_INSIGHTS_CURSOR_June122026_638PM.MD

# Hostile review (June 11)
cat CURSOR_JUNE112026.MD

# Per-class winners
cat reports/per_class_winners_2026-06-11.md

# Intrabar class truth
python3 -c "import json; d=json.load(open('audit_dashboard/data/intrabar_truth_by_class.json')); print(json.dumps(d['by_class'], indent=2))"

# Money-ready verdict
python3 alpha_engine/money_ready_verdict.py --json | python3 -m json.tool | head -80

# Picks-now track record
python3 -c "import json; t=json.load(open('audit_dashboard/data/picks_now_track_record.json')); print(t['totals'])"

# Investigation skill
cat .claude/skills/thingstocheck-june2026/SKILL.md
```

---

## 8. Related artifacts (index)

| File | Role |
|------|------|
| `reports/SESSION_COMPLETE_CURSOR_June122026_AUDIT_EDGE_HUNT.MD` | **This file** — tasks, findings, deep-dives |
| `PLAN_INSIGHTS_CURSOR_June122026_638PM.MD` | Audit findings + P0/P1/P2 summary |
| `CURSOR_JUNE112026.MD` | Hostile master-loop review Parts I–IX |
| `docs/todos/PM_ACTIONS_JUNE12_2026.md` | Actionable PM backlog |
| `docs/plans/2026-06-12-P0A-intrabar-hourly-reresolve-plan.md` | P0-A implementation plan |
| `docs/plans/2026-06-12-P0B-*.md`, `P0C-*.md`, `P1A-*.md`, `P1B-*.md` | Prioritized fix plans |
| `reports/per_class_winners_2026-06-11.md` | Per-class PROVEN/PROBATION ladder |
| `reports/strategy_pass_hunter_2026-06-11.json` | Pass-hunter scan output |
| `.claude/skills/thingstocheck-june2026/SKILL.md` | Repeatable audit investigation |
| `.claude/commands/thingstocheck-june2026.md` | Slash command entry point |

---

## 9. Live pages (spot-check)

- https://findtorontoevents.ca/audit/
- https://findtorontoevents.ca/audit/picks-now.html
- https://findtorontoevents.ca/audit/pick_funnel.html
- https://findtorontoevents.ca/audit/ai-tournament.html
- https://findtorontoevents.ca/audit/ai_leaderboard.html
- https://findtorontoevents.ca/audit/portfolio_history.html
- https://findtorontoevents.ca/audit/research_index.html

---

## 10. Session status

| Category | Count |
|----------|-------|
| Investigation tasks completed | 14 |
| Code/tools shipped (session arc) | 5+ modules |
| P0 actions remaining | 5 |
| P1 actions remaining | 6 |
| P2 actions remaining | 5 |
| PROVEN classes (n≥100) | **0 / 8** |
| PROBATION sleeves | **1** (CRYPTO luxalgo SHORT) |

**Next step for implementer:** Execute P0-1 (luxalgo SHORT emission) and P0-2 (CRYPTO LONG block) before any dashboard copy or sizing changes.
