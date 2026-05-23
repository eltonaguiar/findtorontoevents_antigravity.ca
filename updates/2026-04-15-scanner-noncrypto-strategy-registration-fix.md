# Scanner: non-crypto strategy registration fix (2026-04-15)

*All **timestamps** in this note (pick baseline table, “last refreshed”, and `tools/_last_pick_per_asset_class.py` output) are shown in **US Eastern Time** (`America/New_York`: **EST** or **EDT** by season). Calendar-only labels (e.g. the doc title date) are local filing dates, not timezone-specific.*

## Executive summary

**Completed fix:** `alpha_engine/scanner.py` — commodity, futures, ETF, and bond strategy packs were never merged into the active strategy map on full scans because four `if` conditions used **unquoted identifiers** (`all`, `commodity`, …), causing an immediate **`NameError`** and skipping those entire strategy families.

**Finding:** The **symbol universe expansion** in `config.py` (futures, ETFs, bonds) was already present; the pipeline could fetch data for those symbols, but **`run_strategies(..., "all")` did not register the corresponding strategy modules**, so those books stayed artificially thin compared with crypto / equity / forex.

**Enhancement:** None beyond this correctness fix; behavior now matches the intended design (all asset-class strategy dicts participate when `strategy_filter` is `"all"` or the specific class).

---

## What was broken

| Location | Issue |
|----------|--------|
| `run_strategies()` ~L1979–1988 | `strategy_filter in (all, commodity)` etc. — `all` was the built-in function; `commodity` / `futures` / `etf` / `bond` were undefined names. |

**Call path affected:** `forward_validator.run_generation()` → `run_strategies(data, context)` (default `"all"`), used by `production_scanner.run_full_cycle()`.

---

## What changed

Replaced with string literals:

- `("all", "commodity")`, `("all", "futures")`, `("all", "etf")`, `("all", "bond")`

so `COMMODITY_STRATEGIES`, `FUTURES_STRATEGIES`, `ETF_STRATEGIES`, and `BOND_STRATEGIES` are actually loaded.

---

## Verification

- `python -m py_compile alpha_engine/scanner.py` — exit 0.
- Before fix: `run_strategies(..., "all")` failed at the commodity line with `NameError: name 'commodity' is not defined`. After fix: execution proceeds past strategy registration.

---

## Expected benefits and results

| Area | Expected effect |
|------|------------------|
| **Signal volume** | More **raw signals** from futures, ETF, bond, and commodity strategies on each full scan, since those modules now register. |
| **Active / closed picks** | **Gradual** increase in opens and over time in closes for those asset classes, subject to `rank_and_filter_signals`, `MAX_OPEN_PICKS`, kill lists, risk controls, and HC gates — not necessarily a large jump in a single hourly cycle. |
| **Dashboard** | Non-crypto cards (futures, ETFs, bonds, commodities) should **better reflect** the expanded `config.py` universe once the fixed code runs in CI/production. |
| **Win rate** | **Not guaranteed to improve** globally. Thin futures history with very low WR was partly driven by **strategy quality** (e.g. EMA-stack / `futures_ema_stack_momentum` already flagged elsewhere). This fix addresses **missing coverage**, not bad edges. Follow-up: strategy gates, demotion, or mutation analysis per project protocol. |

---

## Deployment note

Dashboard and pick JSON update only after the environment that runs `production_scanner` / `run_full_cycle` uses a build that includes this `scanner.py` commit (e.g. `main` on GitHub Actions). Until then, behavior is unchanged.

---

## Pick baselines — last opened vs last closed (per asset class)

Times below are **US Eastern** (see header). Use this table to see whether **new** activity is landing after the scanner fix. **Refresh** after CI or a local scan updates `alpha_engine/data/active_picks.json` and `closed_picks.json`:

```bash
python tools/_last_pick_per_asset_class.py --markdown
```

Paste the output here, or compare timestamps manually.

**Rules used**

| Column | Meaning |
|--------|--------|
| **Last opened** | Latest *open* time per class: `opened_at` → `entry_time` → `created_at` → `timestamp` → else `entry_date` (noon UTC internally). **Displayed in US Eastern.** |
| **Last closed** | Latest *close* time among picks that look **closed** (`status` CLOSED/CLOSE, or `closed_at` / `exit_time`, or `exit_reason` set), using `closed_at` then `exit_time`. **Displayed in US Eastern.** |
| **Strategy** | `strategy`, else `source_system`, else `source` (some scalps omit `strategy`). |

**Canonical class** comes from `alpha_engine.asset_class.normalize_asset_class` (symbol-first). Tickers such as **IEF** may appear under **etf** in this table even when `category` is `bond`, because known ETF symbols are classified before category.

### Snapshot (repo `alpha_engine/data`)

**Last refreshed (US Eastern):** 2026-04-15 11:50 PM EDT — re-run the command above after `active_picks.json` / `closed_picks.json` change.

| Asset class | Last opened (US Eastern) | Symbol | Strategy | Last closed (US Eastern) | Symbol | Strategy |
|-------------|---------------------------|--------|----------|---------------------------|--------|----------|
| crypto | 2026-04-15 11:29:29 PM EDT | RENDERUSDT | inverse_ml_enhanced_RENDERUSDT_1h_D | 2026-04-15 03:37:22 PM EDT | HYPEUSDT | quan_engine |
| equity | 2026-04-15 11:15:34 PM EDT | MSTR | stocks_ema_golden_cross | - | - | - |
| forex | 2026-04-15 11:16:05 PM EDT | USDCAD=X | cta_cross_asset_tsmom | 2026-04-15 03:02:19 PM EDT | GBPJPY=X | forex_rsi2_mean_reversion |
| futures | 2026-04-15 11:16:05 PM EDT | CL=F | cta_cross_asset_tsmom | - | - | - |
| etf | 2026-04-15 11:16:05 PM EDT | IEF | cta_cross_asset_tsmom | - | - | - |
| bond | - | - | - | - | - | - |
| unknown | - | - | - | - | - | - |

**How to read `-`:** no qualifying pick in the merged active+closed JSON for that column (e.g. no closed equity rows in `closed_picks.json`, or no pick normalizes to **bond** because bond-tagged symbols map to **etf** first).
