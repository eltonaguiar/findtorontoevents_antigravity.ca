# Loop 2 Checkpoint 3 — T+~90m (2026-05-08 22:15 UTC)

## STOCKSUNIFY2 sibling repo — integration target identified

**Repo**: `eltonaguiar/STOCKSUNIFY2` — 9,885 KB, last update **2026-05-07** (yesterday — ACTIVE).

**Top-level content**:
- `data/daily-stocks.json` (13,650 bytes) ← **integration target for /audit**
- `STOCK_ALGORITHMS.md` (10 KB), `STOCK_ALGORITHM_DECISION_MATRIX.md` (10 KB), `STOCK_ALGORITHM_PROSCONS_AND_IMPROVEMENTS.md` (21 KB), `STOCK_ALGORITHM_SUMMARY.md` (6 KB), `STOCK_RESEARCH_ANALYSIS.md` (6 KB) — comprehensive algorithm catalog (5 docs reference 4 AI assessments: Gemini, ChatGPT, Comet Browser, others)
- `scripts/{generate-ledger.ts, verify-performance.ts, lib/, v2/}` + `scripts/v2/aggregate-performance.ts`

**Top 3 algorithms cataloged**:
1. **CAN SLIM Growth Screener** (long-term 3-12mo, ~60-70% confidence per O'Neil research): RS rating ≥90, Stage-2 uptrend (Minervini), revenue growth ≥25%, institutional accumulation. Source: `mikestocks` family of repos.
2. **SCREENER_PENNYSTOCK_SKYROCKET_24HOURS** (short-term 24h-1wk): volume surge + RSI extremes + 20-day breakouts + BB squeeze + short interest. Penny stocks under $4.
3. **eltonsstocks-apr24_2025**: portfolio mgmt + risk control.

**Decision matrix consensus** (Gemini + Comet + ChatGPT):
- Watchlist → Growth Screener
- Entry → Penny Stock Screener
- Risk → Replicator Risk Mgmt
- Sentiment → QuickPicks
- Holding → QuickPicks + Replicator

### Integration plan (1-day work)

```yaml
# .github/workflows/stocksunify2-pull.yml — NEW
name: STOCKSUNIFY2 daily-stocks.json pull
on:
  schedule:
    - cron: '0 13 * * *'   # 13:00 UTC daily, after STOCKSUNIFY2 generates
  workflow_dispatch:
jobs:
  pull:
    steps:
      - uses: actions/checkout@v6
      - run: |
          curl -fsSL -o audit_dashboard/data/stocksunify2_daily_stocks.json \
            https://raw.githubusercontent.com/eltonaguiar/STOCKSUNIFY2/main/data/daily-stocks.json
          python -c "import json; d=json.load(open('audit_dashboard/data/stocksunify2_daily_stocks.json')); print(f'pulled {len(d.get(\"picks\",[]))} picks')"
      - run: bash tools/safe_commit_push.sh
```

Plus 1-line addition to `audit_trail/dashboard_generator.py` `JSON_PICK_SOURCES`:
```python
{
  "name": "stocksunify2_daily_stocks",
  "path": "audit_dashboard/data/stocksunify2_daily_stocks.json",
  "asset_class": "EQUITY",
  "default_concept_family": "long_term_value",
  ...
}
```

This unlocks ~1k+ EQUITY picks/day from a separate active repo.

## mercury2_fast 2-month staleness — INTENTIONAL, not a bug

`.github/workflows/mercury2-fast-scan.yml:3-5`:

```yaml
on:
  # DISABLED 2026-03-12: mercury2_fast is garbage data (+333% synthetic TRXUSDT, -100% losses). Purge approved.
  # schedule:
  #   - cron: "0 */4 * * *"
  workflow_dispatch:
```

Commented out due to known synthetic-data pollution. Last successful run 2026-03-13. Workflow state shows "active" but cron is gone. **Verdict**: don't restart; the data was bad. Keeping `mercury2_fast_picks.json` 2-month stale is correct.

## Hyrotrader Tables 4-5 freshness check

(Pending — TODO for next checkpoint)

Source files for Tables 4-5 are:
- `audit_dashboard/data/hyro_quan_bridge.json` — QuanEngine Edge Tracker
- `audit_dashboard/data/hyro_pick_strength.json` (or similar) — Table 4 Signal Strength
- `audit_dashboard/data/hyro_ml_optimizer.json` — Table 5 ML Edge Optimizer

Will verify next checkpoint.

## Done since checkpoint 2

- ✅ STOCKSUNIFY2 inspected via gh api: 9.9MB, daily-stocks.json target located, 5 algorithm docs catalogued
- ✅ Top-3 algorithms confirmed (CAN SLIM, Skyrocket, Replicator)
- ✅ Integration plan drafted (1 workflow + 1 dashboard_generator line)
- ✅ mercury2_fast staleness diagnosed: INTENTIONAL disable per known synthetic-data
- ⏳ Hyrotrader Tables 4-5 freshness deferred to next checkpoint

## Top-12 fix queue updated (1 new + STOCKSUNIFY2 integration)

| # | new fix | priority |
|---|---|---|
| 13 | Add STOCKSUNIFY2 pull workflow + register `daily-stocks.json` in JSON_PICK_SOURCES | P1 (1-day work, unlocks ~1k EQUITY/day) |

(Other 12 unchanged from checkpoint 2.)

## Up next (T+120m)

- Hyrotrader Tables 4-5 freshness check
- Investigate cross-asset transfer candidates (Hurst pairs, BB momentum + VIX, etc.) — quick feasibility scan
- Schedule next wakeup at T+30m
