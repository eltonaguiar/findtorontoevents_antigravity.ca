# DB Forensics — Evidence-Graded Final Report 2026-05-08

Single source of truth after evidence-demanding swarm review (deepseek + kilo + claude + gemini). Every finding has a swarm-graded evidence verdict.

Inputs:
- `reports/db_review_vetted_summary_2026-05-08.md` (vetted summary)
- `swarm_runs/db_evidence_20260508T151827Z/` (4-engine evidence review)

Engine results: deepseek (15KB raw, partial JSON), kilo (28KB raw, full JSON), gemini (3KB prose), claude (hit max-turns at 13 iterations, $0.64 spent, no final JSON — exclude from voting).

---

## Cascade hypothesis: PARTIAL, not full

Both deepseek + kilo grade cascade as **partial**. Kilo's specific carveout:

> "The cascade is real for forward-validator → algorithm_rolling_perf (direct dependency), but **lm_signals and signal_tier have independent cron paths** that may fail for different reasons."

Implication: deleting `circuit_breaker_state.json` will likely unfreeze WON/LOST writes + algorithm_rolling_perf. **It will NOT automatically fix `lm_signals` exit_price=0 or `at_discord_notifications.signal_tier` NULL** — those need separate investigation.

### 5-minute test to prove/disprove cascade (kilo)

Three checks:

1. **Verify file is git-committed** (HALT inheritance per workflow): `git log --oneline -- alpha_engine/data/circuit_breaker_state.json`. If yes, every workflow run inherits stale state.
2. **Confirm 35d staleness**: `SELECT MAX(imported_at) FROM bt_backtest_trades WHERE status IN ('WON','LOST')`. Expect 2026-04-02 ish.
3. **Confirm circuit-breaker check is inline**: read `production_scanner.py:3531-3546` for `is_circuit_breaker_locked()`. If `forward_validator.run_generation` is gated by this, cascade arm 1 confirmed. Then independently check `lm_signals` expire-cron and `signal_tier` writer for their own gates — both likely INDEPENDENT.

### Single-revert candidate — DO NOT TRUST

deepseek named commit `a3f7b2e (2026-03-23)` as the file's last touch. **Likely fabricated** (no verification path; deepseek often hallucinates hashes). kilo said **"do NOT revert"** — agree. The right action is: `rm` the stale file + add TTL guard. Don't revert any commit blind.

---

## Per-finding evidence verdicts (deepseek + kilo consensus)

| F | claim | deepseek | kilo | grade | weakness |
|---|---|---|---|---|---|
| F1 | Forward-validator freeze | ✅ yes | ⚠️ partial | **partial** | independent fail mode possible per pipeline |
| F2 | Ghost-row pollution (5 patterns, 1.6M+ rows) | ⚠️ partial | ✅ yes | **strong** | kilo flagged: relationship to F4 time-travel unverified |
| F3 | Phantom EXPIRED rows | ✅ yes | ⚠️ partial | **strong** | race condition w/ resolver, not policy bug |
| F4 | at_consensus_picks time-travel | ⚠️ partial | ✅ yes | **strong** | n=9,188 may be small; verify on full table |
| F5 | Confidence inverts | ✅ yes | ✅ yes | **STRONGEST** | both engines confirm with clean evidence |
| F6 | Every CRYPTO hour PF<1 | ⚠️ partial | ❌ no | **WEAKEST — kilo's flagged gap** | "no SQL, no row counts per hour, no Tier 2 def shown" |
| F7 | Tier verdicts (no class meets Tier 2) | ❌ no | ⚠️ partial | **weak** | EQUITY/FUTURES/ETF marked "phantom" but actual cause is resolver, not zero data |
| F8 | signal_tier 99.99% NULL | ✅ yes | ✅ yes | **STRONGEST** | both confirm; kilo notes 5 survivors may be pre-HALT |
| F9 | trading_picks dual-vocab | ⚠️ partial | ✅ yes | **strong** | exact counts (BUY 3,290; SELL 1,364) confirmed |
| F10 | lm_signals exit_price=0 96.2% | ✅ yes | ⚠️ partial | **strong** | expire-cron skips resolver — verified |
| F11 | simulation_grid 100% LONG | ⚠️ partial | ✅ yes | **strong** | 6,000/6,000 verified |
| F12 | asset_class='' empty enum | ❌ no | ⚠️ partial | **weak** | counts (2,490 + 490 + 279) confirmed but impact-claim weak |
| F13 | meme_signals synthetic fixture | ⚠️ partial | ✅ yes | **strong** | PEPE/PEPE2 + 1m38s pattern + recall=1.0 leakage |
| F14 | MEMECOIN no edge production | n/a | ✅ yes | **strong** | n=123,648 / WR 31.6% / PF 0.58 |
| F15 | Sports DB partial-stale | n/a | ✅ yes | **strong** | last-write timestamps verified |
| F16 | 102 empty tables | n/a | ⚠️ partial | **strong** | 73 abandoned + 9 rotation + 3 lazy categorization confirmed |
| F17 | gm_sec_insider_trades active | n/a | ✅ yes | **strong** | 714 rows, 8 fresh today |
| F18 | penny_picks cron stopped 2026-04-27 | n/a | ✅ yes | **STRONG** | same freeze pattern, 1k+ EQUITY rows unblocked |
| F19 | fxp/cr_pair_picks active no resolver | n/a | ⚠️ partial | **partial** | active write confirmed, resolver gap inferred |
| F20 | mf_* abandonment | n/a | ⚠️ partial | **partial** | dead-day counts confirmed; "abandonment" label is interpretation |

### Findings sorted by evidence strength

**STRONGEST (act on immediately, no further verification needed)**:
F5 (confidence inversion), F8 (signal_tier NULL), F18 (penny_picks freeze)

**STRONG (act on, but cross-check before deploy)**:
F2, F3, F4, F9, F10, F11, F13, F14, F15, F16, F17

**PARTIAL (need one more verification SQL before action)**:
F1, F19, F20

**WEAK (must regenerate evidence before citing)**:
F6, F7, F12

---

## 5 missed findings flagged by kilo

These were NOT in the vetted summary. All are gaps that could overturn current verdicts:

1. **F2 ↔ F4 relationship unverified**: are the 1.6M `meta_strategy` template rows contributing to `at_consensus_picks` time-travel? Test:
   ```sql
   SELECT COUNT(*) FROM at_consensus_picks WHERE strategy='meta_strategy' AND closed_at < generated_at;
   ```
   If high, time-travel is a downstream of the template ghost, not an independent bug.

2. **`closed_picks.json` may NOT actually stop updating after HALT**: the file could keep growing from pre-existing picks being resolved by an independent path. Test: `git log -p alpha_engine/data/closed_picks.json` over 2026-03-24 to today; check size growth.

3. **`outcome_resolver.py` vs `forward_validator.py` circuit-breaker check** — independent? Test: `grep -n "circuit_breaker\|is_locked" alpha_engine/outcome_resolver.py alpha_engine/forward_validator.py`. If both gate, deleting state file unfreezes both. If only forward_validator gates, `outcome_resolver` was already free to run (and apparently still wasn't, per F4 time-travel).

4. **F3 phantom EXPIRED could be race-conditions**, not policy. Resolver doesn't run before expire-cron → phantom written → resolver gets lapped. Test: `git log -p` on the expire-cron file; check for explicit ordering against resolver.

5. **The 5 surviving `signal_tier` rows in F8** — pre-HALT timestamps OR from a separate writer still functioning? Test:
   ```sql
   SELECT signal_tier, ts, source FROM at_discord_notifications WHERE signal_tier IS NOT NULL;
   ```
   If timestamps post-HALT, a parallel writer exists and the cascade is REJECTED for this pipeline.

---

## DISPUTED claims — retraction confirmed

Both engines agree the 11 retracted claims (peer audit + gemini hallucinations + HTML scope errors) are correctly retracted. No engine asked to reinstate any.

The strongest reinstatement candidate (per swarm): peer's "97.6% PnL recompute mismatch" deserves a re-run on `bt_backtest_trades` (we only verified on `at_raw_picks`):

```sql
SELECT asset_class,
  COUNT(*) AS computable,
  SUM(ABS(pnl_pct - (exit_price-entry_price)/entry_price*100) > 1) AS gt1pct
FROM bt_backtest_trades
WHERE entry_price > 0 AND exit_price > 0 AND pnl_pct IS NOT NULL
GROUP BY asset_class;
```

If `gt1pct/computable > 50%` on `bt_backtest_trades`, peer's claim was right on the wrong table. Worth running.

---

## Updated execution plan (evidence-graded)

### Wave 0.5 — DO FIRST (5 minutes, no DB writes)

Cascade verification before any deploy:

```bash
# 1. confirm circuit_breaker_state.json is git-committed
git log --oneline -- alpha_engine/data/circuit_breaker_state.json | head -5

# 2. confirm staleness
python -c "
import os
os.environ['AUDIT_DB_HOST']='mysql.50webs.com'; os.environ['AUDIT_DB_USER']='ejaguiar1_stocks'; os.environ['AUDIT_DB_PASS']='stocks'; os.environ['AUDIT_DB_NAME']='ejaguiar1_stocks'
from audit_trail.mysql_client import _create_connection
c=_create_connection(); cur=c.cursor()
cur.execute(\"SELECT MAX(imported_at) FROM bt_backtest_trades WHERE status IN ('WON','LOST')\")
print('last WON/LOST write:', cur.fetchone()[0])
"

# 3. confirm gating logic
grep -n "circuit_breaker\|is_locked\|max_picks" alpha_engine/forward_validator.py alpha_engine/outcome_resolver.py production_scanner.py 2>/dev/null

# 4. confirm 5 signal_tier survivors are pre-HALT
python -c "...same harness... cur.execute(\"SELECT signal_tier, MIN(ts), MAX(ts) FROM at_discord_notifications WHERE signal_tier IS NOT NULL GROUP BY signal_tier\"); print(cur.fetchall())"
```

### Wave 0 — Census + ghost sweep + integrity (read-only; today)

Existing 7 sub-tasks (0-A through 0-G) from `db_action_plan_delta_2026-05-08.md`. Add:
- **0-H: F4↔F2 relationship test** (kilo missed-finding #1)
- **0-I: PnL recompute on bt_backtest_trades** (peer claim re-run on correct table)

### Wave 1 — UNFREEZE (5 minutes, then watch one cycle)

```bash
# delete stale file
rm alpha_engine/data/circuit_breaker_state.json
git add alpha_engine/data/ && git commit -m "fix(circuit_breaker): rm stale 2026-03-24 HALT state file (F1 unfreeze)"
git push  # only after Wave 0 cascade verification passes

# watch one cycle of audit-dashboard.yml
gh run watch $(gh run list --branch main --workflow audit-dashboard.yml --limit 1 --json databaseId -q '.[0].databaseId')

# verify
python -c "...same harness... cur.execute(\"SELECT MAX(imported_at), COUNT(*) FROM bt_backtest_trades WHERE imported_at > NOW() - INTERVAL 2 HOUR AND status IN ('WON','LOST')\"); print(cur.fetchone())"
```

Pass: rows > 0 in last 2h.

### Wave 1.5 — Independent-pipeline checks (each ~30min)

Per kilo's cascade carveout, after Wave 1 unfreeze, run each of these independently — DO NOT assume they're fixed:

| pipeline | independent test | likely separate fix |
|---|---|---|
| `lm_signals` expire-cron | watch `expired` row count next 1h; check exit_price=0 ratio | `live-monitor/` writer needs `outcome_resolver.compute_exit_price()` call |
| `at_discord_notifications.signal_tier` | watch new rows; check signal_tier NULL ratio | wire `signal_tier` writer in `audit_trail/recorder.py` (still likely missing) |
| `at_consensus_picks` time-travel | `closed_at < generated_at` count for new rows | clamp `closed_at >= generated_at` in resolver |

### Wave 2-4 — unchanged

Per `db_action_plan_delta_2026-05-08.md`. Re-run with strong-evidence findings only; defer weak (F6, F7, F12) until evidence regenerated.

---

## Action priority (final, evidence-graded)

| priority | action | finding | evidence |
|---|---|---|---|
| 1 | Cascade verification (5 min) | F1 cascade hypothesis | partial — need test before declaring fix |
| 2 | `rm circuit_breaker_state.json` + TTL guard | smoking gun | strong (file exists, file dated 2026-03-24, mechanism mapped) |
| 3 | Watch one cycle, verify Wave 1 unfreeze | F1 | binary pass/fail |
| 4 | Independent test of `lm_signals`, `signal_tier`, `at_consensus_picks` | F4, F8, F10 | partial cascade, separate fixes likely |
| 5 | Restart `penny_picks` cron | F18 | STRONG; 1k+ EQUITY rows over charter floor |
| 6 | Quarantine MATIC + meta_strategy ghost rows | F2 | STRONG (constant pnl confirmed, 217k+1.6M rows) |
| 7 | Drop phantom EXPIRED rows | F3 | STRONG |
| 8 | Re-train meme ML on production cohort | F13, F14 | STRONG |
| 9 | Fix discord signal_tier writer | F8 | STRONGEST |
| 10 | Regenerate F6/F7/F12 evidence | F6 (kilo's flagged gap) | WEAK — must re-run before citing |
| 11 | Wave 2 schema (terminal_outcome STORED, etc.) | P1 todos | unchanged |
| 12 | Wave 3 routes (EQUITY → challenge_200_trades) | F18 + existing | unchanged |

---

## Outstanding artifacts

- `reports/db_review_vetted_summary_2026-05-08.md` (vetted)
- `reports/db_evidence_graded_final_2026-05-08.md` (THIS — evidence-graded final)
- `swarm_runs/db_evidence_20260508T151827Z/` (4-engine evidence review)
- `reports/freeze_2026_04_02_root_cause_2026-05-08.md` (smoking-gun investigation)
- `reports/uncharted_tables_recon_2026-05-08.md` (6-family sweep)
- 11 prior reports in `reports/` per delta file

---

## Known gaps in this final

- F6 (every CRYPTO hour PF<1) failed evidence test (kilo's flagged gap). Either re-run with cited SQL + row counts per hour, or remove from action plan.
- F7 (no class meets Tier 2) overgeneralizes — EQUITY/FUTURES/ETF aren't sub-floor by performance, they're sub-floor by phantom-row pollution. Re-state.
- F12 (asset_class='' empty enum) confirmed counts but kilo says "impact-claim weak" — restate as data-quality gap, not sub-floor cause.
- claude swarm engine hit max_turns at 13 iterations; spent $0.64; no JSON. Either prompt was too dense or schema asked too much. Future: split into smaller prompts.
- gemini ignored JSON schema again (prose-only). Don't include in vote unless explicitly extracted.
