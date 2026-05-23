# Loop 2 Checkpoint 4 — T+~120m (2026-05-08 22:45 UTC)

## Hyrotrader page freshness audit — most data is STALE

| file | last update | age | source workflow | status |
|---|---|---|---|---|
| `hyro_ml_pick_rankings.json` | 2026-05-08 14:32 | 1h ✅ | `hyro-daily.yml` | passing |
| `hyro_quan_bridge.json` | 2026-04-19 01:49 | **20 days** ⚠️ | `hyro-bridge-regen.yml` | failing 3+ days |
| `hyro_pick_performance.json` | 2026-04-20 00:04 | 19 days | unknown | unknown |
| `hyro_backtest_new_strategies.json` | 2026-04-15 12:24 | 24 days | unknown | unknown |
| `hyro_live_strategies.json` | 2026-04-15 11:53 | 24 days | unknown | unknown |
| `hyro_playbook_combined.json` | 2026-04-14 07:48 | 25 days | unknown | unknown |
| `hyro_batch2_results.json` | 2026-04-07 18:02 | 32 days | unknown | unknown |
| `hyro_backtest_extended_results.json` | 2026-04-07 17:57 | 32 days | unknown | unknown |
| `hyro_backtest_12m_new_strategies.json` | 2026-04-08 01:54 | 31 days | unknown | unknown |
| `hyro_backtest_results.json` | 2026-04-07 17:57 | 32 days | unknown | unknown |

**Verdict**: HyroTrader dashboard is ~80% stale. Only ML pick rankings is fresh.

## Hyro Quan Bridge — root cause found

```
Run hyro-bridge-regen.yml: failure
  Step: "Regenerate bridge (atomic write via tools/hyro_quan_bridge.py)" — exit 1
  Error: ModuleNotFoundError: No module named 'numpy'
  Location: tools/hyro_quan_bridge.py:32
```

Workflow step:
```yaml
- name: Install minimal deps
  run: |
    python -m pip install --quiet pyyaml   # ← MISSING numpy + pandas
```

### Fix

```yaml
- name: Install minimal deps
  run: |
    python -m pip install --quiet pyyaml numpy pandas requests
```

(Add deps that match `tools/hyro_quan_bridge.py` imports — exact list needs reading the file's imports section.)

## Top-14 fix queue (consolidated, this checkpoint adds 2)

| # | fix | impact |
|---|---|---|
| 1-13 | per checkpoint 2+3 (12 + STOCKSUNIFY2 integration) | unchanged |
| 14 | **Add numpy + pandas to `hyro-bridge-regen.yml` Install step** | restores 20-day-stale `hyro_quan_bridge.json`, unblocks QuanEngine Edge Tracker on /audit/hyrotrader |
| 15 | Investigate other hyro-* JSON writers (~30 days stale) | many tables on /audit/hyrotrader rendering on Apr 7 data |

## What's working on hyrotrader vs what's stale

✅ **Working**:
- Table 5 — ML Edge Optimizer (`hyro_ml_pick_rankings.json` 1h fresh, 40KB)
- Account snapshot, drawdown check (computed live from JSON)

❌ **Stale**:
- QuanEngine Edge Tracker (Table 1): 20 days
- Table 4 — Signal Strength (likely from `hyro_pick_performance.json` 19 days)
- Table 2 — Live playbook signals (`hyro_playbook_combined.json` 25 days)
- All backtest comparisons (Apr 7-15)

The "MAIN EVENT" Table 3 — Pick List source needs identification (didn't show up in `hyro_*.json` ls). Likely served from the main `dashboard_data.json::picks.active` filtered to hyro-eligible symbols.

## STOCKSUNIFY2 integration plan reaffirmed

Per checkpoint 3, STOCKSUNIFY2 sibling repo has:
- `data/daily-stocks.json` (13.6 KB, last update 2026-05-07 — ACTIVE)
- 5 algorithm catalog docs (CAN SLIM Growth Screener, Skyrocket, Replicator)
- Cross-AI consensus (Gemini + Comet + ChatGPT) on stack ordering

Integration = 1 new workflow `.github/workflows/stocksunify2-pull.yml` + 1 `JSON_PICK_SOURCES` line in `dashboard_generator.py`. Unlocks ~1k EQUITY picks/day from a different repo.

## Cross-asset transfer candidates (Hermes daily)

Strategies flagged as transferable from CRYPTO → EQUITY/FOREX:
- Hurst exponent pairs / autocorrelation reversion
- Adaptive Bollinger Momentum + VIX term structure
- Turn-of-month, put/call ratio contrarian
- Liquidity imbalance
- chatgpt_combined (high historical WR)

Each would take ~1-2 days to port + backtest on EQUITY/FOREX universe via STOCKSUNIFY2 pipeline. Not actioned this loop; queued for future.

## Done since checkpoint 3

- ✅ Inventoried all 10 `hyro_*.json` files w/ mtimes
- ✅ Identified `hyro-bridge-regen.yml` failing 3+ days
- ✅ Pulled failure log: `ModuleNotFoundError: No module named 'numpy'` at `tools/hyro_quan_bridge.py:32`
- ✅ Drafted fix: add numpy + pandas to "Install minimal deps" step

## Up next (T+150m)

- Identify writers + status for the 6 still-unknown hyro_*.json files
- Check `dashboard_data.json` size + freshness (claimed 17.5MB in freebuff)
- Verify the `_compute_hf_decay_watchlist` is firing (HF P0 Item #2 from CLAUDE.md memory)
- Schedule next wakeup at T+30m
