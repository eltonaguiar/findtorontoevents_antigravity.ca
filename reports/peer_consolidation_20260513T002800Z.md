# Cross-Peer Consolidation — 2026-05-13T00:28Z

Three independent agents reviewed the same session window:

| Peer | Top finding | Top action |
|---|---|---|
| **Me** (this assistant) | COMMODITY 75% CT=F single-symbol; A6 corr-finding sample-thin (n_obs=123 < 252 floor) | Stage `active_picks_sync --apply` CRYPTO class first |
| **Claude#2 mb2v7tau** (Grok-4 + Mercury-2 + Kimi-K2 swarm) | Productivity high but reliability+completeness low — switches staged but never enabled | Flip `AUTO_RETIRE_APPLY=1` + `ML_GATE_AB_ENABLED=1` via `gh variable set` (~5min) |
| **Agent#3** (3-engine consensus) | 10 personas all backed by Opus-4.7 = fake diversity; close LINK-L (-$100) + ETH-L (-$94) | Rotate DB pass (DONE), build `tv_pick_capture.py`, resolve 60% backfilled |

## Convergent verdict (3-of-3 alignment)

**Session pattern was breadth-over-depth. Right cadence going forward: place → resolve → analyze, NOT place×5 + build×infra.**

All 3 reviewers independently flagged: shipping pace exceeded validation pace. Each named different specific symptom but same disease.

## DB rotation gotcha (operational P0)

User just confirmed DB passwords rotated. New env names:
- `DB_PASS_STOCKS` / `DB_NAME_STOCKS`
- `DB_PASS_BACKTESTS` / `DB_NAME_BACKTESTS`

**Repo state:** 128 file references use OLD names (`DB_STOCKS_PASSWORD`, `MYSQL_PASSWORD`, `AUDIT_DB_PASS`, `DB_BACKTESTS_PASSWORD`). 0 references use new names.

**Mitigations:**

1. **Local dev:** All 128 files will fail auth locally until env-var fallback chain exists.
2. **CI:** GH secret `MYSQL_PASSWORD` is the source for workflows. If user updated that secret to the new password, all workflows still work. If not, every DB-touching cron will fail.
3. **Fix shipped this commit:** `tools/db_env.py` — unified resolution helper. Tries new names first, falls back through all legacy aliases. Callers can migrate at their own pace via:
   ```python
   from tools.db_env import get_stocks_creds, get_backtests_creds
   conn = pymysql.connect(**get_stocks_creds())
   ```

## Unified TOP-3 cross-peer next steps

Cross-walking my 6 NS items, Claude#2's flip recommendations, and Agent#3's
build-capture-then-resolve loop, the highest-leverage actions in order:

### CP-1 — Verify `MYSQL_PASSWORD` GH secret matches new DB password

User-action: confirm `gh secret list -R eltonaguiar/...` shows the `MYSQL_PASSWORD`
entry updated AFTER the rotation timestamp. If not, every DB-touching
workflow auth-fails on next run. Estimated 5 min (one `gh secret set` call).

```bash
# Confirm via:
gh secret list -R eltonaguiar/findtorontoevents_antigravity.ca | grep MYSQL_PASSWORD
# Update if needed:
gh secret set MYSQL_PASSWORD -R eltonaguiar/findtorontoevents_antigravity.ca
# (paste new pass at stdin prompt)
```

### CP-2 — Flip `AUTO_RETIRE_APPLY=1` via gh variable

User-action per Claude#2 + Mercury-2 #1 consensus. Auto-retires 7
known bleeders (kimi_signal_tracking already class-wide blocked but
auto-retire-daily.yml hasn't been allowed to consume the quarantine
manifest writes yet). 5 min.

```bash
gh variable set AUTO_RETIRE_APPLY --body "1" -R eltonaguiar/findtorontoevents_antigravity.ca
```

**Pre-flight safety check (just shipped this session):**
- `8a82f133ca7` C1 fixed the drawdown sign-convention dead-code
- `8a82f133ca7` C2 added FOREX mutate-before-kill guard
- Result: auto-retire now actually fires on real DDs + skips FOREX
- Therefore safe to flip without additional code change.

### CP-3 — Flip `ML_GATE_AB_ENABLED=1` via gh variable

User-action per Claude#2. With `gatekeeper_old.joblib` + `gatekeeper_new.joblib`
both on main (`4c6ecc4bb47`), the env-flag gate at `ml_gatekeeper/gatekeeper.py:618`
now produces real 50/50 OLD vs NEW split. ~30d soak then z-test.

```bash
gh variable set ML_GATE_AB_ENABLED --body "1" -R eltonaguiar/findtorontoevents_antigravity.ca
```

Worst-case rollback: `gh variable set ML_GATE_AB_ENABLED --body "0"`. No real-money impact (paper picks only until full LIVE_ELIGIBLE path clears).

## Items I disagree with from peer reviews

| Peer claim | My pushback |
|---|---|
| Claude#2: "switches staged not enabled" implies my session work was incomplete | Most of my work was DIAGNOSTIC (audits, payload fields, swarm consensus). The flip is operator-side; agent code cannot self-flip `gh variable set` without explicit user consent per CLAUDE.md "shared-state actions" rule |
| Agent#3: "close LINK-L (-$100) + ETH-L (-$94)" | Those are individual paper picks in theswarm; closing requires user action via TV MCP. Not autonomous-shippable |
| Agent#3: "9/10 personas all backed by Opus-4.7" | Did not investigate theswarm persona setup in my session. Defer to agent#3 |
| Claude#2: real-money 2026-07-15 timeline | My swarm consensus already pushed this to 2026-08-15 floor (REV-4 in `session_review_consensus_20260513T001430Z.md`) |
| Peer agent#3: "DB rotation pending" | User confirms DONE; `tools/db_env.py` shipped this commit to handle the env-name fallback locally |

## Open user-action checklist

| Item | User-action | Risk | Reversibility |
|---|---|---|---|
| 1 | `gh secret set MYSQL_PASSWORD` to new value | Low (auth failure only) | Full — re-set old value |
| 2 | `gh variable set AUTO_RETIRE_APPLY 1` | Med (writes quarantine manifest) | Full — re-set to 0 |
| 3 | `gh variable set ML_GATE_AB_ENABLED 1` | Low (paper-only A/B split) | Full — re-set to 0 |
| 4 | Close LINK-L + ETH-L on theswarm paper portfolio via TV MCP | Low (paper only) | n/a (losses already booked) |
| 5 | Confirm `gatekeeper_old/new.joblib` are committed to main | DONE per `4c6ecc4bb47` | n/a |

Items 1-3 are 5min total. Items 4 is ~2min via TV-MCP UI. Item 5 already done.

## Autonomous-shippable next steps (will continue without flips)

| Item | Status |
|---|---|
| `tools/db_env.py` unified DB env resolution | **shipped this commit** |
| `tools/correlation_regime_sidecar.py` default 150→500d (n_obs floor) | shipped `cd9ad7de442` |
| `alpha_engine/requirements.txt` pymysql dep | shipped `cd9ad7de442` |
| Migrate first few connect() helpers to `tools/db_env.py` | next |
| A1 cron output review (multi_asset_cot DB-verify) | awaits `gh workflow run ab_analysis.yml` (user OR cron) |

## Strongest convergent recommendation

**Both Claude#2 and Agent#3 say: stop building, start measuring.**

The session shipped 24+ commits across audits, payload fields, gates,
sidecars, and 2 swarm-consensus rounds. None of those produce profit
on their own. The 3 ops switches (CP-1/CP-2/CP-3 above) are what flip
the pipeline from "we built it" to "it's running."

I cannot flip them autonomously. User decision.
