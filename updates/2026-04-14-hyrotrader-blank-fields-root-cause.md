# HyroTrader audit page — blank / empty fields (root cause)

**Page:** [https://findtorontoevents.ca/audit/hyrotrader/](https://findtorontoevents.ca/audit/hyrotrader/)  
**Date:** 2026-04-14  
**Scope:** What users perceive as “blank” cells, empty sections, or “—” placeholders on `/audit/hyrotrader/`.

---

## Executive summary

| Area | What it looks like | Root cause |
|------|-------------------|------------|
| **QuanEngine Regime Analysis** table (Signal, Consensus, Confidence, Mode, Entry, TP, SL, R:R, Strategies) | Empty-looking row or one wide muted row | **`hyro_quan_bridge.json` has `ensemble: null` (and thus `trade_setup` / `risk_gate` unset)** when the QuanEngine ensemble does not clear voting thresholds. The UI collapses nine columns into one cell: *“No consensus (X/Y votes)”*. |
| **Pick list — SL / TP / numeric prices** | No dollar prices | **By design.** JSON omits `entry_price` / `stop_loss` / `take_profit` until a human adds real levels; the page states this explicitly. |
| **Account snapshot / progress** | “—” for some numbers | **Missing or null fields** in `hyrotrader_picks.json` → `account_snapshot` (e.g. `largest_single_day_profit_usdt: null`) render as em dash via `fmtNum()`. |
| **Live playbook signals** | Empty table, errors in Levels column, or only errors | **No strategy fired on the last closed 1h bar** (“No setup”), **Binance klines fetch failed** from the browser (mirror failover still failing), or **“Hide No setup”** hides most rows. |
| **Trade journal** | Empty table | **`hyrotrader_journal.json`** has no trades (or file missing / empty array). |
| **Whole page** | Red error banner | **`hyrotrader_picks.json` failed to load** (404, wrong path, or opened as `file://`). |

---

## 1. QuanEngine table — the main “blank fields” case

### Live data shape

`GET https://findtorontoevents.ca/audit/data/hyro_quan_bridge.json` (sample 2026-04-14) includes:

- Per symbol: `regime`, `hurst`, `active_votes`, `total_votes`
- **`ensemble`: `null`**
- **`trade_setup`: `null`**
- **`risk_gate`: `null`**

Example counts: BTC `3/18`, ETH `4/18`, SOL `5/18`, BNB `3/18` active votes.

### Pipeline behavior (`tools/hyro_quan_bridge.py`)

For each symbol, `run_symbol()` initializes:

```python
"ensemble": None,
"trade_setup": None,
"risk_gate": None,
```

A populated ensemble only appears after `ensemble.vote(votes)` returns a non-null `EnsembleSignal`. If `signal is None`, the function **returns early** with those fields still `null` (see `tools/hyro_quan_bridge.py` around the `if signal is None: return out` branch).

### Ensemble rules (`quan_engine/ensemble_layer.py`)

`QuanEnsemble.vote()` returns **`None`** unless:

1. **Consensus path:** At least **2** active (non-`ABSTAIN`) voters; **≥ 60%** of active voters agree on `BUY` vs `SELL`; **average confidence of the majority ≥ 0.55** (`CONSENSUS_THRESHOLD` / `MIN_AVG_CONFIDENCE` from `quan_engine/config.py`).
2. **Solo fallback:** At least one active voter with **confidence ≥ 0.80** (then emitted as a discounted solo signal).

If strategies mostly **abstain**, or active votes **split** across directions, or **consensus / confidence** checks fail, **`signal` stays `None`** → JSON keeps `ensemble: null`.

### UI behavior (`audit_dashboard/hyrotrader/index.html`)

The second script block loads `hyro_quan_bridge.json` and, when `!ens`, renders:

```javascript
'<td colspan="9" style="color:var(--dim);font-style:italic">No consensus (' + (s.active_votes||0) + '/' + (s.total_votes||0) + ' votes)</td></tr>'
```

So the **detailed columns are intentionally not filled** — they are replaced by a **single spanned cell**. Users often describe that as “blank” columns.

**Conclusion:** The “blank” QuanEngine fields are not a failed fetch of the JSON; they reflect **valid pipeline output**: regime/Hurst are computed, but **no tradable ensemble signal** passed the consensus gates.

---

## 2. Pick list — numeric Entry / SL / TP

The renderer uses `formatLevelsCell()`:

- If `entry_price`, `stop_loss`, `take_profit` are all absent, it shows copy explaining that **numeric prices are not invented** and stay empty until added to JSON.

This matches product intent: **methodology text** (`stop_plan`, `take_profit_plan`) can be present while numbers stay unset.

---

## 3. Account snapshot and progress bars — “—”

`fmtNum()` maps `null` / `undefined` / `""` to **"—"**.

Examples:

- `largest_single_day_profit_usdt: null` → consistency line falls back to instructional text.
- Any optional challenge field omitted → corresponding row shows “—”.

---

## 4. Live playbook signals (1h)

Rows depend on:

1. **`hyro_live_strategies.json`** (config; defaults exist if missing).
2. **Browser `fetch()` to Binance (and mirrors)** for klines. Failures produce a **“Klines error”** row with the error message in the last column.
3. **Strategy rules** on the last **closed** 1h bar — often **“No setup”** (not a bug).
4. **Checkbox “Hide ‘No setup’”** (default **on**) — hides rows without a valid signal, which can make the table **look empty** if every pair is “No setup”.

---

## 5. Stale or missing data (secondary)

If `hyro_quan_bridge.json` or `hyrotrader_picks.json` were **not deployed**, **out of date**, or the page opened as **`file://`**, sections would fail or stay empty. That class of issue is documented in:

- `updates/2026-04-14-hyrotrader-stale-data-fix.md`
- `HYROTRADER_PIPELINE_FIXES.md`

The **blank QuanEngine detail columns** with **fresh JSON** are still explained by **`ensemble: null`** (Section 1), not only by staleness.

---

## 6. Optional follow-ups (not required to explain “blanks”)

- **Lower ensemble thresholds** or **adjust strategy participation** if the product goal is to show ensemble rows more often (trade-off: more noise).
- **Clarify UI copy** so “No consensus (X/Y)” is clearly distinct from a loading or broken state.
- **Ensure CI + FTP** keep `audit_dashboard/data/*.json` current for non–browser-dependent panels.

---

## References (repo)

- `audit_dashboard/hyrotrader/index.html` — `fmtNum`, `formatLevelsCell`, `dataBaseUrl`, QuanEngine loader, `runLiveSignalsScan`
- `tools/hyro_quan_bridge.py` — `run_symbol`, ensemble / early return when `signal is None`
- `quan_engine/ensemble_layer.py` — `QuanEnsemble.vote`
- `quan_engine/config.py` — `CONSENSUS_THRESHOLD`, `MIN_AVG_CONFIDENCE`
- `audit_dashboard/data/hyro_quan_bridge.json` — example live payload with `ensemble: null`
