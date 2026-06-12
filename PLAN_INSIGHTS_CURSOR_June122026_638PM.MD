# PLAN_INSIGHTS — Cursor Agent — June 12 2026 ~6:38 PM EST

> **Full session wrap (tasks complete/remaining, achievements, findings, deep-dives):**  
> [`reports/SESSION_COMPLETE_CURSOR_June122026_AUDIT_EDGE_HUNT.MD`](reports/SESSION_COMPLETE_CURSOR_June122026_AUDIT_EDGE_HUNT.MD)

## Session scope

Full `/audit` edge hunt per user request + PM-action todos from prior hostile review. Skill saved: `.claude/skills/thingstocheck-june2026/SKILL.md`. Slash command: `.claude/commands/thingstocheck-june2026.md`. PM todo list: `docs/todos/PM_ACTIONS_JUNE12_2026.md`.

---

## Accomplishments (this session)

- **Created PM action backlog** (`docs/todos/PM_ACTIONS_JUNE12_2026.md`) — P0 stop-bleed through P2 institutional playbook.
- **DB-verified tournament claims** — `gpt4_1` 55.6% WR is **real on decisive rows only** (20 WIN / 16 LOSS); **75/117 rows quarantined as MISPRICED_ENTRY** and correctly excluded from leaderboard denominator.
- **Confirmed kimi_direct bias pattern** — 47/94 MISPRICED_ENTRY; decisive WR 61.7% (29/47) vs leaderboard 60.9% on n=46 after untrustworthy exclusion — single-snapshot / bad-geometry quarantine is working, not hiding a fake 100% sleeve.
- **Root-caused picks-now 21.1% WR** — `picks_now_track_record.json` frozen **2026-06-09**, only **19 resolved** symbol-days (4W/15L), mostly **EQUITY STRONG_BUY** hitting **SL** within 0–1 days; cum PnL **−44.3%**.
- **Validated pick_funnel honesty** — DISPUTED banner + **0/6 money-ready** aligns with `intrabar_truth_by_class.json` (CRYPTO WR 32.4% / PF 0.73 at n=1154).
- **ai_leaderboard staleness explained** — index `as_of` **2026-06-09**; only **2 engines** meet `min_n_ranked=20` as “classified”; user perception “only claude-opus-4.7” is mostly **insufficient-n across 43 engines**, not a dead pipeline.
- **ai-tournament leaderboard is live** — 45 models with `n_resolved>0`; top rank kimi_direct T2 on policy-clean subset; page labels tournament as **research-only**, not sizing (`money_ready_verdict.json`).

---

## Findings — is there a hidden edge?

### Verdict: **No class passes institutional Tier-2 on honest intrabar ledger**

| Surface | What it claims | Ground truth | Gap / bug |
|---------|----------------|--------------|-----------|
| `/audit/` high-conviction / smart picks | Historical “elite” cohorts | `money_ready_verdict.json` **0/9** intrabar pass; CRYPTO class WR **32.4%** PF **0.73** | Soft resolution + LONG bias + concentration (pick_funnel DISPUTED row obsolete but historical 78.9% cohort untracked) |
| Star tab active picks FWD WR | Symbol×direction forward WR | Often shows **strategy-level** WR from registry | **P1 fix**: wire `at_signal_outcomes` per pick_id |
| `picks-now.html` forward-tested | **21.1% WR** | 19 resolved, stale since Jun 9; STRONG_BUY longs stop out | Valuation screen ≠ edge; no intrabar discipline; needs refresh + growth-screener factors |
| `pick_funnel.html` | Nav matrix vs DB | **Accurate** on 0/6 sizing + CRYPTO dispute | Keep; refresh Smart Picks DB ground truth hourly |
| `ai-tournament.html` | NOT MONEY-READY everywhere | **Correct** — tournament picks ≠ policy-clean intrabar | gpt4_1 **55.6%** on n=36 decisive **after** excluding 75 mispriced |
| `ai_leaderboard.html` | Best model | Only **31 resolved** picks index-wide; 2 classified | Raise resolver throughput or lower `min_n_ranked` for discovery |
| `portfolio_history.html` | Model portfolios | File mtime **May 31** locally; live **Jun 12** deploy but **stale generator** — books show heavy EW losses | **P1**: resurrect only if wired to intrabar truth + kill list |
| `research_index.html` | Research leverage | 30+ June hypotheses registered; **0 intrabar PROVEN** | Wire registry → emitter (luxalgo SHORT ships **0** picks) |

### One probation sleeve (not yet PROVEN)

**`luxalgo_confluence × CRYPTO × SHORT`** — n=38, WR **71.1%**, PF **2.21**, Wilson LB **55.2%**, passes R1/R2/R3 discipline on deduped intrabar ledger. **Blocker:** `priority_picks_emitter` emits **0** luxalgo SHORT v2 picks (scanner empty) → forward lane not accruing n toward 100.

### OHLC proxy backtests (not intrabar-confirmed)

Only **COMMODITY `gold_overnight_gap_fade`** (n=108, PF 1.92) and **PENNY `volume_spike_fade`** pass Tier-2 proxy in June research pipeline — **zero** confirmed on `at_signal_outcomes` harness.

---

## Why picks-now forward WR is horrible (21.1%)

1. **Tiny sample** — 19 resolved of 100 symbol-days tracked (rest OPEN or not yet resolved).
2. **Stale pipeline** — last run **2026-06-09T19:19:11Z**; forward lane stalled (no closes in 48h per money_ready recency gate).
3. **Wrong hypothesis** — page optimizes **valuation / STRONG_BUY** equity longs; intrabar truth shows **EQUITY FAIL** (WR 34.6%, PF 0.47, n=107).
4. **Resolver geometry** — first-touch TP/SL with 4% SL hits on AAPL/AMD within 1 day (`exit_reason: SL_HIT`).
5. **Missing integration** — growth-stock-screener style quality/momentum filters not wired (`starboi-63/growth-stock-screener` pattern).

**Fix path (P0-5):** refresh track record daily; block EQUITY STRONG_BUY until F2=mom-WITH or similar passes; add picks from probation CRYPTO SHORT sleeve; rerun `tools/resolve_picks_now.py` on intrabar OHLC.

---

## gpt4_1 55.6% — double-checked

```text
tournament_picks WHERE model_id='gpt4_1' AND resolved_at IS NOT NULL:
  WIN: 20 | LOSS: 16 | MISPRICED_ENTRY: 75 | OPEN: 6
  Decisive WR = 20/36 = 55.56%  ← matches ai_tournament_leaderboard.json
  n_excluded_untrustworthy: 75  ← leaderboard excludes these from ranking
```

**Conclusion:** Number is **arithmetically correct** on WIN/LOSS only. **Not money-ready** — 64% of resolved rows are mispriced-entry quarantine; PF CI spans 0.66–3.66 (wide); class-level intrabar still fails.

---

## kimi_direct — nuke or backfill?

**Do not nuke.** Exclusion logic is doing its job (47 mispriced). **Do:** hourly intrabar reresolve (P0-A) so forward picks reclassify with honest geometry; backfill tournament rows where `entry_price` disagrees with signal bar OHLC by > threshold.

---

## Portfolio history — stale? worth it?

- Local artifact **May 31**; CDN **Jun 12** (FTP deploy without regen).
- Aggregate model books compound **large negative EW** in last audit — consistent with 0/6 money-ready.
- **Recommendation:** **Freeze** public page until portfolios pull from `intrabar_truth` + emitter kill list; otherwise it misleads. Low priority vs picks-now + luxalgo SHORT.

---

## P0 / P1 / P2 next steps

### P0 (this week)

| ID | Action |
|----|--------|
| P0-1 | Fix **luxalgo SHORT emission** (0 picks) |
| P0-2 | **Block CRYPTO LONG** at emitter |
| P0-3 | Ship **hourly intrabar reresolve** GHA job |
| P0-4 | Kill **fear-greed CRYPTO LONG** from batch |
| P0-5 | **Refresh picks-now** track record + resolver |

### P1 (2 weeks)

| ID | Action |
|----|--------|
| P1-1 | Symbol×direction FWD WR on Star tab |
| P1-2 | Tournament UI: show **MISPRICED_ENTRY** counts beside WR |
| P1-3 | pick_funnel hourly Smart Picks DB refresh |
| P1-4 | Intrabar replay **gold_overnight_gap_fade** |
| P1-5 | FOREX live block F1=CONTRARIAN |
| P1-6 | Portfolio history — regen or deprecate banner |

### P2 (4 weeks)

| ID | Action |
|----|--------|
| P2-1 | Focus **2 classes** — CRYPTO SHORT + COMMODITY gap-fade |
| P2-2 | Kill **12/16** june2026 v2 emitters without intrabar support |
| P2-3 | Monkey test + stress matrix before PROVEN promotion |
| P2-4 | Growth-stock screener → picks-now |
| P2-5 | research_index → hypothesis registry wire-up |

---

## Areas for further improvement

1. **Velocity over breadth** — 50 tournament models but 0 proven classes; cut emitters faster (M-107 pre-register already exists — enforce kill on fail).
2. **Single forward lane** — `entry_conditions_forward.json` stamps must match what emitter actually ships (today: 44 picks, none luxalgo SHORT).
3. **Peer-review swarm on resolver** — sign-flip, reverse-split, active-pick-cap bugs called out in skill; run `fabrication-red-team` on any cell claiming WR>55%.
4. **External replication** — COMMODITY gap-fade vs DBMF/KMLM; CRYPTO SHORT vs funding/OI filters before size.
5. **User-facing honesty** — every surface showing WR should cite **intrabar_truth** n/WR/PF and **INSUFFICIENT_N** when n<100.

---

## Reproducer commands

```bash
# Intrabar class truth
python3 -c "import json; d=json.load(open('audit_dashboard/data/intrabar_truth_by_class.json')); print(d['by_class'])"

# Money-ready verdict
python3 alpha_engine/money_ready_verdict.py --json | python3 -m json.tool | head -80

# Picks-now track record
python3 -c "import json; t=json.load(open('audit_dashboard/data/picks_now_track_record.json'))['totals']; print(t)"

# Tournament gpt4_1 decisive WR (needs DB creds)
python3 - <<'PY'
import pymysql
from tools.db_env import get_stocks_creds
c={k:v for k,v in get_stocks_creds().items() if k in ('host','user','password','database','port','connect_timeout')}
conn=pymysql.connect(**c,cursorclass=pymysql.cursors.DictCursor)
cur=conn.cursor()
cur.execute("SELECT SUM(status='WIN') w,SUM(status='LOSS') l FROM tournament_picks WHERE model_id='gpt4_1' AND resolved_at IS NOT NULL")
r=cur.fetchone(); print('gpt4_1 WR', r['w']/(r['w']+r['l']))
PY

# PM todos
cat docs/todos/PM_ACTIONS_JUNE12_2026.md
```

---

## Live pages to spot-check

- https://findtorontoevents.ca/audit/
- https://findtorontoevents.ca/audit/picks-now.html
- https://findtorontoevents.ca/audit/pick_funnel.html
- https://findtorontoevents.ca/audit/ai-tournament.html
- https://findtorontoevents.ca/audit/ai_leaderboard.html
- https://findtorontoevents.ca/audit/portfolio_history.html
