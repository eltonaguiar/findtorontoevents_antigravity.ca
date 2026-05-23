# Dormant winners → audit + MySQL (ejaguiar1_stocks)

## What we changed (2026-03-29)

1. **`JSON_PICK_SOURCES`** (`audit_trail/dashboard_generator.py`) now includes revival + DNA feeds that existed on disk but were missing from the unified audit merge:
   - `revival_breakout_spike`, `revival_crypto_gainer_ml`, `revival_ml_system_b_regime`, `revival_ml_system_c_deeplearn`
   - `trusted_genome` → `genome/data/trusted_genome_picks_live.json`
   - `dna_rapid_fire_mutations`, `dna_confluence_mutations` → genome daily pipeline outputs
2. **`SYSTEM_SOURCES`** (`audit_trail/universal_pick_resolver.py`) — same paths so picks get TP/SL resolution and closed rows merged.
3. **DARWIN workflow** (`.github/workflows/darwin-evolution.yml`) — revival step: `--stale-days 1 --mutations-per 15` (was 2 / 10) to surface more DNA variation for stale systems.

## Find dormant strategies locally

```bash
python tools/report_dormant_winners.py --min-trades 20 --min-wr 55 --max-active 0
```

## Audit site (`findtorontoevents.ca/audit`)

- Hourly **Unified Audit Dashboard** workflow regenerates `dashboard_payload.json` and deploys FTP.
- After merge to `main`, new systems appear in payload on the next successful run.

## MySQL (`mysql.50webs.com` / `ejaguiar1_stocks`)

Typical env: `AUDIT_DB_HOST`, `AUDIT_DB_USER`, `AUDIT_DB_PASS`, `AUDIT_DB_NAME` (or `MYSQL_*` / `DB_*` per script).

| Path | Role |
|------|------|
| `sync_all_picks_to_mysql.py` | Bulk `at_raw_picks` from `genome/data` and other dirs |
| `audit_trail/mysql_client.py` | `record_raw_pick` / consensus tables |
| `alpha_engine/mysql_trading_sync.py` | `trading_picks` from alpha JSON |
| `alpha_engine/audit_sync.py` | `trade_log` / portfolios / ML metrics (mostly **closed** + Darwin) |

**DNA / genome JSON under `genome/data/`** is already under the `("genome/data", "mega_mutation")` scan in `sync_all_picks_to_mysql.py` plus `("genome", "genome")` — new revival/mutation files in that directory are picked up on the next sync if naming matches `active_picks.json` / `closed_picks.json` conventions expected by the syncer (see `PickSyncer` logic in that file).

Run (with credentials set):

```bash
python sync_all_picks_to_mysql.py
```

## Operational checklist

- [ ] Merge PR → wait for audit-dashboard + darwin-evolution Actions
- [ ] Confirm new keys in live `dashboard_data.json` (`systems[].name`)
- [ ] Run `sync_all_picks_to_mysql.py` on a schedule or post-deploy if `at_raw_picks` must mirror JSON
- [ ] For **baby-strat** names with paper-only forward metrics, promotion is a separate battleground/incubator workflow — wiring above targets **genome revival + DNA mutations** first
