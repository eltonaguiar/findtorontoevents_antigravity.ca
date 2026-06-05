# Intrabar Resolver Expansion Scope — Non-CRYPTO

**Date:** 2026-06-05  **Mode:** read-only investigation, no code changes
**Source files cited verbatim from grep on this checkout.**

## TL;DR — Premise needs revision

The mission brief assumes "non-CRYPTO is still on the old single-snapshot resolver." **This is not what the code shows.** Both production resolvers already do intrabar OHLC replay for non-CRYPTO via yfinance. The 2026-06-04 work added the *missing* CRYPTO path (Binance/CoinGecko/KuCoin). Banner text on `audit_dashboard/ai-tournament.html:189` is consistent: "Non-CRYPTO 100% replay coverage; CRYPTO ~89% and rising."

The real non-CRYPTO problem is **yfinance reliability / coverage gaps** and **single-vendor risk**, not absence of intrabar replay.

## Code path inventory

- **Main resolver:** `alpha_engine/outcome_resolver.py`
  - `_fetch_yfinance_ohlc_window()` at L440 (15s timeout, L226 `YFINANCE_TIMEOUT_SECS=15`)
  - `_scan_ohlc_for_touch()` at L559 — SL-first conservative ordering
  - Non-crypto branch consumes ohlc_window: L913 `elif is_non_crypto and ohlc_window is not None and len(ohlc_window) > 0:` → L921 calls `_scan_ohlc_for_touch`
  - Empty-ohlc guard: L966-967 "v2.1 (2026-05-02): empty/missing ohlc_window for non-crypto. Refuse" — already lands intrabar by 2026-04-28 (v2) per L839
- **Tournament resolver:** `tools/ai_tournament/resolve_db_picks.py:135-176` — pre-fetches OHLC per symbol, calls `resolve_pick(..., ohlc_bars=...)`
- **OHLC fetch abstraction:** `tools/ai_tournament/price_tracker.py:412-468` `fetch_ohlc_window(pick)` — routes by asset_class:
  - L432-436 CRYPTO → `_fetch_ohlc_crypto_binance` (Binance mirrors → CoinGecko OHLC → KuCoin, defined L289-410)
  - L438-468 ALL OTHERS → yfinance `Ticker.history(interval="1d")` (one vendor, no fallback)

## The actual gap (single-vendor risk, not missing replay)

`price_tracker.fetch_ohlc_window` non-CRYPTO branch (L438) has **no failover** — one yfinance call, on failure returns `[]`, caller drops to spot snapshot. This is the asymmetry vs CRYPTO's Tier-3 chain. Per-class candidate Tier-2/3 sources:

- **EQUITY / ETF:** Tier-2 Alpha Vantage `TIME_SERIES_DAILY` (key already wired L138 of price_tracker.py for spot); Tier-3 Stooq CSV (no key) or Polygon.io free tier (5 calls/min)
- **COMMODITY (`*=F`):** Tier-2 Stooq (`gc.f`, `cl.f`); Tier-3 Nasdaq Data Link free CME continuous
- **BOND (`^TNX`, `^TYX`):** Tier-2 FRED (`DGS10`, `DGS30` — daily yield CSV, no key); Tier-3 Alpha Vantage
- **FOREX (`*=X`):** Tier-2 Alpha Vantage `FX_DAILY`; Tier-3 exchangerate.host historical OHLC
- **FUTURES:** same as COMMODITY

## Effort estimate (smallest expansion = add ONE Tier-2 fallback per class)

- **Files touched:** 1 — `tools/ai_tournament/price_tracker.py` (add `_fetch_ohlc_<class>_tier2` helpers; chain them inside the L438 branch keyed off `asset_class`). Mirror change optional in `alpha_engine/outcome_resolver.py:440` (currently identical single-vendor pattern).
- **Hours:** ~4-6 for first class wired end-to-end with cached unit tests; ~2h per additional class.
- **Risk:** low — fallback only triggers on yfinance miss; existing path is unchanged when yfinance returns bars.

## Highest-ROI first class

**EQUITY**. Justification (from CLAUDE.md MAJOR GOALS block, today's status line): EQUITY is FAIL+INSUFF-N (PF 0.90 / WR 33% / n=33) and Goal #1's most volume-rich non-CRYPTO class once n>100. Alpha Vantage `TIME_SERIES_DAILY` is the cheapest add (free key, daily resolution matches yfinance, no symbol-rewrite needed beyond suffix-strip already present at price_tracker.py:127). Also unblocks ETF (same code path) for free.

## 1 minimum change to unblock EQUITY

Patch sketch — `tools/ai_tournament/price_tracker.py` at line 438 (the `else` arm of the CRYPTO check inside `fetch_ohlc_window`):

```
# AFTER yfinance returns [] / raises, fall through to:
if not bars:
    av_key = os.environ.get("ALPHA_VANTAGE_KEY", "")
    if av_key and (pick.get("asset_class") or "").upper() in {"EQUITY","ETF"}:
        bars = _fetch_ohlc_equity_alphavantage(yf_sym, submitted_at, av_key)
return bars
```

New helper `_fetch_ohlc_equity_alphavantage` parallels `_fetch_ohlc_crypto_binance` (L289-336 template), parses `Time Series (Daily)` JSON into the same `{date,open,high,low,close}` dict shape `_scan_ohlc_for_touch` already expects. No changes needed in `outcome_resolver.py` or `resolve_db_picks.py` — they just consume the bars list.

**Mirror in main resolver (optional, same shape):** `alpha_engine/outcome_resolver.py:440-511` `_fetch_yfinance_ohlc_window` — wrap its `hist = future.result(...)` (L494) failure path with the same AV fallback before returning empty.
