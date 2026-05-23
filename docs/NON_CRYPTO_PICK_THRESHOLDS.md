# Non-crypto pick thresholds and pipeline notes

Internal reference for commodities, forex, futures, and equity pick volume. Keep in sync with code when changing gates.

## Dashboard UI categories

The audit dashboard **Commodities** vs **Futures** tabs use the same rules as `matchCategory` in [`audit_dashboard/template.html`](../audit_dashboard/template.html) (search `matchCategory`). Roughly:

- **Futures:** `asset_class` / `category` = `FUTURES` (e.g. ES=F, NQ=F).
- **Commodities:** `COMMODITY` class/category, or symbols starting with `XAU` / `XAG` (metal USDT). A row can match **both** if it has e.g. `asset_class: FUTURES` and `category: commodity`.

Backend normalization: [`audit_trail/dashboard_generator.py`](../audit_trail/dashboard_generator.py) `_derive_asset_class` (commodity roots `CL`, `GC`, `ZW`, … with `=F`).

## Scraper / signal gates

| Layer | Location | Notes |
|--------|-----------|--------|
| Volume confirmation | [`copy_trader_intel/multi_asset_copytrader_scraper.py`](../copy_trader_intel/multi_asset_copytrader_scraper.py) | Futures momentum path: **current volume > 1.5× 20-day average** (see comments ~983–985). Commodity sections use **ATR-based TP/SL**. |
| Institutional caps | [`multi_asset/institutional_picks_engine.py`](../multi_asset/institutional_picks_engine.py) `RISK_PARAMS` | **FUTURES max_picks 6**, **FOREX max_picks 6**, **EQUITY max_picks 8**, plus correlation groups. |
| Smart Picks (non-crypto) | [`alpha_engine/smart_picks_engine.py`](../alpha_engine/smart_picks_engine.py) `NON_CRYPTO_POLICY` | Forex: allowlist **`cta_tsmom_blend`**, **`forex_rsi2_mean_reversion`**; **min_trades 50**; **allowed_trust: PROVEN** only. Futures bucket (includes `commodity` category mapped to `futures`): allowlist does **not** include **`cftc_cot_commercial_signal`**. |
| Dashboard TP/SL fallback | [`audit_trail/dashboard_generator.py`](../audit_trail/dashboard_generator.py) `_ac_defaults` | **COMMODITY / FUTURES:** ~**3% TP, 2% SL** when ATR-based levels missing (~4484–4489). |
| Pick quality distances | [`copy_trader_intel/pick_quality_monitor.py`](../copy_trader_intel/pick_quality_monitor.py) `DISTANCE_LIMITS` | **commodity:** TP max **15%**, SL max **10%** of entry; **futures:** 20% / 15%. |

There is **no single global min-volatility config**; gates are distributed across these modules.

## GitHub Actions: what shows up in logs (examples)

### Multi-Asset Copytrader Scanner (`multi-asset-scanner.yml`)

- **`continue-on-error: true`** on all Python steps — workflow can be **green** even if a step failed; always open each step log.
- Example lines from a successful run (2026-04-02):
  - `CFTC COT: API unavailable, falling back to RSI + seasonal proxy`
  - `HTTP Error 404` / `No data found` for **`FDAX=F`** (bad/delisted Yahoo symbol — non-fatal for other symbols).
  - `Binance Futures ping failed — BINANCE_FUTURES_DISABLED=True` (session flag).
  - Commodity emits e.g. **`[SHORT] COMMODITY CL=F`** after the CFTC proxy path.

Inspect logs: **Actions → "Multi-Asset Copytrader Scanner v2" → latest run →** search **`Traceback`**, **`Error`**, **`yfinance`**, **`CL=F`**, **`CFTC`**.

### Unified Audit Dashboard (`audit-dashboard.yml`)

- Example: **`HTTP 451`** on Binance (geo-block in runner region) — resolver falls back to other price sources where implemented.
- Non-crypto consensus may log **`Commodity(0)`** if upstream JSON had no commodity rows at that instant (ordering vs multi-asset commit).

Inspect logs: search **`451`**, **`Traceback`**, **`commodity`**, **`WARNING`**.

## Pick-level “errors” without opening Actions

Open [`multi_asset/data/active_picks.json`](../multi_asset/data/active_picks.json) (or `copy_trader_intel/data/multi_asset_picks.json`) and search the **`reason`** field for:

- **`CFTC COT proxy (API unavailable)`** — degraded COT data, not necessarily a crashed job.

## Automated audit: class counts + mirror diff

After each dashboard generation locally or in CI:

```bash
python tools/non_crypto_pick_audit.py audit_trail/data/dashboard_payload.json
```

Writes [`audit_trail/data/non_crypto_pick_audit.json`](../audit_trail/data/non_crypto_pick_audit.json) with:

- Active counts per **EQUITY / FOREX / COMMODITY / FUTURES / ETF** (blocked systems excluded; same names as `BLOCKED_SYSTEMS` in `template.html`).
- Diff of **commodity-class symbols** between payload actives and `multi_asset/data/active_picks.json` when the mirror file exists.

**Strict CI (optional):** set `STRICT_PICK_CLASS_COUNTS=1` and any of `PICK_COUNT_MIN_COMMODITY`, `PICK_COUNT_MIN_FOREX`, etc. The job fails if counts are below those minimums.

## Forex: profit factor vs win rate

**Profit factor** = gross winning PnL / gross losing PnL. **Win rate** is the fraction of trades with positive PnL. A **high profit factor** with **~50% win rate** is normal when average wins are larger than average losses (or a few large winners).
