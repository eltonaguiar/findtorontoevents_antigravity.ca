# Validate /audit/hyrotrader/ stats — 2026-05-31

(EST 2026-05-31 17:06) Audit time UTC=2026-05-31T21:06Z.
Live page: https://findtorontoevents.ca/audit/hyrotrader/ (HTTP 200, 92,985 bytes, last-modified 2026-05-31T20:59Z).

## Source JSON inventory + freshness

| JSON | `generated_at` | Age vs now (UTC 21:06) | Verdict |
|---|---|---|---|
| `hyrotrader_picks.json` | (none — manual snapshot, `last_session_date=2026-04-08`) | n/a | manual-curated, account_snapshot 2026-04-08 still labelled "Apr 2026" |
| `hyro_quan_bridge.json` | `2026-05-31T20:51:13.752272+00:00` | 15 min | FRESH |
| `hyro_pick_performance.json` | `2026-05-29T15:51:36.200136+00:00` | **53h 14m** | **STALE >24h** |
| `hyro_ml_pick_rankings.json` | `2026-05-31T20:51:32.941501+00:00` | 15 min | FRESH |
| `hyrotrader_journal.json` | (none — `trades: []`) | n/a | empty (acceptable; no closed trades logged) |

PRE-EXPECTATION: all five JSONs <24h. RAW RESULT: 3 fresh / 1 stale / 1 manual-snapshot / 1 empty-by-design. Verdict: **partial** — `hyro_pick_performance.json` is 53h stale (no cron run since 2026-05-29T15:51Z).

## 5 tables — sources, displayed stats, integrity

### Table 1 — QuanEngine Edge Tracker (h2 line 180 in live HTML)
- Source: `hyro_quan_bridge.json` → `symbols[]` (15 symbols), `hyro_challenge_params`.
- Status: FRESH. `symbols_len=15`, `errors={}`. Matches displayed.

### Table 2 — Live playbook signals (1h) (h2 line 199)
- Source: `hyrotrader_picks.json` → `playbook[]` (length=11).
- Status: manual-curated, no `generated_at`.

### Table 3 — Pick List "★ THE MAIN EVENT ★" (h2 line 250)
- Source: `hyrotrader_picks.json` → `picks[]`.
- PRE-EXPECTATION: page literal "Expected 10 rows from …" (HTML line 1457).
- Query: `jq '.picks|length' hyrotrader_picks.json` → **7**.
- Verdict: **MISMATCH** — UI advertises 10 expected, JSON ships 7. Below threshold the "No picks array" amber warning would not trigger (length>0), but the documented expectation is violated.

### Table 4 — Signal Strength & Pick Performance (h2 line 276) + Strategy scorecard (h3 line 309)
- Source: `hyro_pick_performance.json` (53h stale).
- Summary displayed: `total_signals=129` (validated=`wins 36 + losses 66 + expired 12 + pending 15 = 129`), overall_wr=`35.3%`.
- Raw JSON verbatim: `"wins":36, "losses":66, "expired":12, "no_data":0, "pending":15, "overall_win_rate":0.353, "best_strategy":"", "best_strategy_score":90.0, "worst_strategy":"residual_momentum_midcap"`.
- **PHANTOM EMPTY-STRATEGY A+ BUG — STILL PRESENT** (see §Phantom below). `best_strategy=""`.

### Table 5 — ML Edge Optimizer (h2 line 370)
- Source: `hyro_ml_pick_rankings.json`.
- Verbatim summary: `total_combos=240, a_grade_combos=1, f_grade_combos=239, avg_score=3.5, best_combo="rsi2×BNBUSDT", best_score=99.5`.
- Status: FRESH. Top1=`{rank:1, strategy:"rsi2", symbol:"BNBUSDT", score:99.5, grade:"A+", method:"ml"}`. Matches displayed.

## Phantom-empty-strategy A+ — STILL PRESENT (not resolved)

PRE-EXPECTATION: previous PR fixed the empty-string strategy key surfacing as A+ row.

Query: `jq '.strategy_scores | has("")' hyro_pick_performance.json`
RAW RESULT: `true`.

Query: `jq '.strategy_scores[""]' hyro_pick_performance.json`
RAW RESULT:
```json
{"strength_score": 90.0, "grade": "A+", "win_rate": 0.818,
 "wins": 9, "losses": 2, "expired": 0, "total_signals": 11,
 "profit_factor": 8.9, "avg_mfe_pct": 0.039, "avg_mae_pct": 0.003,
 "total_pnl_pct": 0.316, "edge_ratio": 13.34}
```

Producer source (file:line, verbatim):
- `tools/hyro_pick_performance_validator.py:461` — `key = v["strategy"]`. No filter for empty/blank.
- `tools/hyro_pick_performance_validator.py:691` — `ranked = sorted(strategy_scores.items(), key=lambda x: x[1]["strength_score"], reverse=True)`. Empty key with score 90 sorts to rank 1 → `best[0] = ""`.
- Output line 706-707: `"best_strategy": "", "best_strategy_score": 90.0`.

Consumer (live HTML, `audit/hyrotrader/index.html`):
- Line 1708 — `if (sum.best_strategy && sum.best_strategy !== 'none') { … }` — truthy-check coincidentally hides the "best strategy" CARD when key is "", BUT:
- Line 1714-1731 — `stratKeys = Object.keys(strats).sort(...)` then `stratKeys.map(function(name) { … '<td style="font-weight:600">' + name.replace(/_/g,' ') + '</td>' …`. NO filter for empty `name`. Empty-string strategy renders as a blank-labelled row at the TOP of the scorecard (sorted by score desc, 90.0).

Git history check today (`git log --since=2026-05-30 -- tools/hyro_pick_performance_validator.py`):
RAW RESULT — last 3 commits are all `[skip ci]` data refreshes (MOMENTUM TRACKER 08:31Z, copy-trader 06:07Z, Gainer scan 02:32Z). **No phantom-strategy fix commit found.**

Verdict: **phantom_strategy_resolved = false**. The "earlier today" fix either landed elsewhere (didn't reach producer/consumer of this JSON) or was reverted/never merged. Empty-strategy A+ row is still served to users on the live page.

## Other findings

- `account_snapshot.last_session_date = "2026-04-08"` while the JSON note says "Snapshot from Hyro UI (Apr 2026)". The challenge tracker has not been updated for 53+ days; `trading_days_logged=0`, `cumulative_pnl_usdt=-70.66`.
- `hyrotrader_journal.json.trades = []` — empty (acceptable, but Progress card shows the "journal empty but snap PnL is non-zero" hint per HTML line 1194).

## Suggested fixes (do not apply pre-21:30Z per peer-collision rule)

1. **Producer** `tools/hyro_pick_performance_validator.py:461` — guard: `key = v["strategy"] or "unknown"`; and in `compute_strategy_scores` drop blank keys before returning. At line 691 filter `ranked = sorted([(k,v) for k,v in strategy_scores.items() if k and k != ""], ...)`.
2. **Consumer** live HTML `stratKeys` filter: `Object.keys(strats).filter(function(n){ return n && n.trim() !== '' && n !== 'unknown'; })` before sort.
3. **Cron** rerun `hyro_pick_performance_validator.py` — it has been stale 53h. Find/repair the missing GH Actions schedule.
4. **Picks** investigate why `picks_len=7` vs documented "Expected 10".

## Result line

HYRO:tables=5:fresh=3:stale=1:mismatches=2:phantom_strategy_resolved=false

(mismatches = phantom-empty-strategy A+ row in Table 4 + picks 7 vs expected 10 in Table 3; manual `hyrotrader_picks.json` and empty journal excluded from fresh/stale counts.)
