# Hyro stack — agent guide (backtest, save findings, live dashboard)

This doc is for **another agent** (or future you) wiring research into the HyroTrader audit page:

- Live page: [https://findtorontoevents.ca/audit/hyrotrader/index.html](https://findtorontoevents.ca/audit/hyrotrader/index.html)
- Static JSON the page reads: `audit_dashboard/data/hyrotrader_picks.json`, `hyrotrader_journal.json`, `hyro_live_strategies.json`
- Live 1h signals in the browser use the same math as `tools/hyro_backtest.py`, loaded from `audit_dashboard/hyrotrader/hyro_live_signals.js`

---

## 1. What is already wired

| Piece | Role |
|--------|------|
| `tools/hyro_filter_from_dashboard.py` | Pulls `dashboard_data.json`, filters Hyro-safe picks → writes `hyrotrader_picks.json` |
| `tools/hyro_backtest.py` | Historical Binance 1h, prop-style rules, strategies: `bollinger`, `rsi2`, `volume`, `sr` |
| `tools/hyro_backtest_extended.py` | Same simulator + **extra** strategies (Connors RSI2, EMA cross, Keltner, MACD, VWAP proxy, Donchian, stochastic, supertrend, etc.) — **research only** unless mirrored in `hyro_live_signals.js` |
| `tools/hyro_risk_sweep.py` | Grid of `risk_pct` values on a fixed list of symbol × strategy combos; writes `audit_dashboard/data/hyro_risk_optimization.json` |
| `audit_dashboard/data/hyro_live_strategies.json` | **Which symbols × which strategies** the dashboard checks live (browser → Binance public API) |
| `hyro_live_signals.js` | Signal logic for `bollinger` / `rsi2` / `volume` / `sr` ( `hyro_backtest.py` ) and `donchian` / `heikin_ashi` ( `hyro_backtest_extended.py` ) |

---

## 2. How to backtest and save results (agent checklist)

1. **Run from repo root (Windows):**

   ```powershell
   python tools/hyro_backtest.py --symbol ETHUSDT --strategy volume --months 6 --long-only --risk 0.75 --save --output audit_dashboard/data/hyro_backtest_results.json
   ```

   Use `--all` and `--symbols BTCUSDT ETHUSDT SOLUSDT BNBUSDT` for a grid. Tweak RSI thresholds: `--rsi2-long 12 --rsi2-short 88`.

2. **Commit the JSON** (or attach as a CI artifact). `hyro_backtest_results.json` is **research output**, not loaded by the Hyro HTML page today — it is for humans and for deciding which strategies belong in `hyro_live_strategies.json`.

   **Extended grid (many strategies):**

   ```powershell
   python tools/hyro_backtest_extended.py --months 6 --symbols BTCUSDT ETHUSDT SOLUSDT --save
   ```

   Default save path: `audit_dashboard/data/hyro_backtest_extended_results.json`. Use `--strategy <key>` for one strategy; keys match `EXTENDED_STRATEGIES` in the script.

   **Risk sweep on shortlisted combos:**

   ```powershell
   python tools/hyro_risk_sweep.py --months 6 --output audit_dashboard/data/hyro_risk_optimization.json
   ```

3. **Promote “winning” configs to live dashboard:** edit `audit_dashboard/data/hyro_live_strategies.json`:

   - Add or remove entries under `strategies` (each needs `strategy` = `bollinger` \| `rsi2` \| `volume` \| `sr`, optional `long_only`, and `params` matching `hyro_backtest.py` / `hyro_live_signals.js`).
   - Adjust `symbols` (USDT spot pairs on Binance; Hyro uses perps — symbols are **hints**; user confirms on Hyro).

4. **If you change signal math in Python**, update `audit_dashboard/hyrotrader/hyro_live_signals.js` the same way so the dashboard stays honest.

5. **Deploy audit bundle** (FTP credentials in env):

   ```powershell
   python tools/deploy_to_ftp.py --audit-only
   ```

   Uploads include `hyrotrader/index.html`, `hyrotrader/*.js`, and `data/hyro_live_strategies.json` when present.

6. **Optional CI:** `.github/workflows/hyro-daily.yml` runs filter + backtest and uploads artifacts; it does not auto-commit.

---

## 3. How live “valid entry” works (for the user at view time)

- After `hyrotrader_picks.json` loads, the page fetches `hyro_live_strategies.json`, then **1h klines** per symbol from Binance (mirror failover in the browser).
- The **last fully closed** 1h bar is evaluated (in-progress bar is dropped).
- A row shows **Valid LONG/SHORT** only if that bar satisfies the same rules as the backtester for that strategy.
- This is **not** a fill guarantee, not Hyro-specific fees/slippage, and **perps ≠ spot** — it is a **real-time sanity check** aligned with your research stack.

---

## 4. Files another agent should not break

- Do not invent numeric `entry_price` / `stop_loss` / `take_profit` in JSON for “planned” picks (tracker and tests enforce honest empty state).
- Keep `hyro_filter_from_dashboard.py` merge behavior for `challenge` / `playbook` / `account_snapshot` so the tracker does not lose required keys.

---

## 5. Quick verification

- Local: `python tools/serve_local.py` → open `http://127.0.0.1:5173/audit/hyrotrader/index.html`
- Tests: `npx playwright test tests/hyrotrader_tracker.spec.ts`
- Static HTML: `node tools/check_syntax.js audit_dashboard/hyrotrader/index.html`
- JS module: `node --check audit_dashboard/hyrotrader/hyro_live_signals.js`

---

## 6. Strategy catalog (context)

Hundreds of named strategies live under `docs/ALL_STRATEGIES.md` and `baby_strategies/`. The live panel implements **`bollinger`**, **`rsi2`**, **`volume`**, **`sr`** (aligned with `hyro_backtest.py`) plus **`donchian`** and **`heikin_ashi`** (aligned with `hyro_backtest_extended.py`) in `hyro_live_signals.js`. Any *other* extended keys still need a JS mirror before they can appear in `hyro_live_strategies.json`.
