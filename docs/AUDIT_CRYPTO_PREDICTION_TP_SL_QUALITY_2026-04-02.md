# Crypto prediction pick quality & TP/SL — enhancement roadmap for `/audit`

**Date:** 2026-04-02 UTC  
**Scope:** `findtorontoevents.ca/audit` active book, prediction-market / pro-trader lanes, and mechanical TP/SL behavior.  
**Audience:** dashboard ETL, `quality_gates`, resolver, and strategy emitters.

---

## 1. How the audit book is built (relevant paths)

| Layer | Role | Key files |
|-------|------|-----------|
| **Ingest + normalize** | Maps many feeds into one pick shape; can **synthesize** missing TP/SL for crypto | `audit_trail/dashboard_generator.py` — `_normalize_pick`, `_vol_aware_tp_sl`, `_get_vol_tier` |
| **Gates + scoring** | Active vs Smart, penalties, R:R checks, liquidity, trust | `audit_trail/quality_gates.py` — `passes_active_gate`, `passes_smart_gate`, `_trade_rr`, `_apply_score_penalties`, Kimi liquidity hooks |
| **Resolution** | Marks TP/SL hits for persistence / closed history | `audit_trail/universal_pick_resolver.py` — price vs `take_profit` / `stop_loss` |
| **Liquidity enrichment** | `quote_volume_24h` for USDT pairs (Binance 24h) | `audit_trail/kimi_crypto_liquidity.py` + scoring in `quality_gates.py` |

Operational UI preset (CRYPTO + VA + quartile + volume) lives in `audit_dashboard/template.html` (“Wins: Crypto+VA”); it does not change backend TP/SL.

---

## 2. Current TP/SL behavior (crypto)

### 2.1 Dashboard normalization (`dashboard_generator.py`)

- **`_vol_aware_tp_sl`** (used when both TP and SL are missing on a crypto row):
  - Volatility **tier** from `_SYMBOL_VOL_TIER` (LOW / MID / HIGH / DEFAULT).
  - **SL ~2.1%** from entry (percentage path); **TP** scales by tier (e.g. ~2.0% LOW → ~3.5% HIGH).
  - If **ATR** is present (`atr_at_entry` / `atr`), distances use tier multipliers; **minimum R:R 1.2** enforced by widening TP if needed.
- Partial TP/SL: if only one side exists, code fills the other using tier-aware R:R (see branches around “Has SL but no TP”).

### 2.2 Universal resolver (`universal_pick_resolver.py`)

- Uses each pick’s `take_profit` / `stop_loss` when present.
- When **both missing**, applies **different** fallbacks (e.g. ~2.5% / 1.5% style defaults in some branches) — **not identical** to `_vol_aware_tp_sl` tier table.

**Enhancement (P0):** Single source of truth — import or share one module (e.g. `audit_trail/tp_sl_crypto.py`) used by **both** `dashboard_generator._normalize_pick` and `universal_pick_resolver` so live resolution matches what the dashboard displays and what Smart R:R gates assume.

---

## 3. Pick *quality* (prediction + crypto alpha)

### 3.1 What already helps

- **Score vs realized PnL** on closed book: run `tools/analyze_audit_scores_vs_pnl.py`; top score quartile vs bottom remains a strong global signal (see `tools/data/score_pnl_analysis.json`).
- **Smart gate funnel:** `tools/audit_smart_gate_funnel.py` + `evaluate_smart_gate_funnel` in `quality_gates.py` — surfaces first-failure reasons (e.g. `anti_overfit`, `score_floor`, `crypto_trust`).
- **Narrow anti-overfit exception:** CRYPTO + `research_cohort == verified_alpha` can pass Smart anti-overfit block; all other Smart clauses still apply (documented in `TRACE_LOG.MD`).
- **Liquidity:** `quote_volume_24h` and Kimi-style tier penalties reduce illiquid USDT names when Binance data exists.

### 3.2 Gaps & enhancements

1. **PM / prediction picks**  
   Sources such as Polymarket / Kalshi / whale aggregates often **bypass strict geometry** in `_has_valid_trade_geometry` when TP/SL are absent.  
   **Enhancement:** For CRYPTO PM rows, either require explicit TP/SL from the emitter or apply `_vol_aware_tp_sl` *before* scoring so `_trade_rr` and Smart `SMART_PICKS_MIN_RR` reflect real trade geometry.

2. **Align Smart R:R with emitted levels**  
   `passes_smart_gate` enforces min/max R:R vs pick fields. If upstream strategies emit inconsistent TP/SL, picks fail Smart for the wrong reason.  
   **Enhancement:** After normalization, recompute `rr` / `risk_reward` fields from final entry/TP/SL; optionally **clamp** TP to satisfy min R:R without breaking direction.

3. **Closed-loop TP/SL calibration**  
   Bucket `recent_closed` by (tier, strategy family, mode) and measure **TP hit rate vs SL hit rate** and time-to-exit.  
   **Enhancement:** If SL hits dominate for a bucket, widen SL or tighten TP for *that tier only*; ship changes via `_VOL_TIER_DEFAULTS` or per-strategy overrides — not a global loosening.

4. **Resolver vs dashboard drift**  
   Unify defaults (section 2.2) so backtested “hit TP” rates on `/audit` match what the resolver would have done with the same JSON.

5. **Fees + slippage (honesty layer)**  
   For *display* and *research*, optional net-of-fee PnL or minimum TP distance vs assumed round-trip cost prevents overfitting to gross touch levels.

---

## 4. Suggested implementation order

| Priority | Task | Outcome |
|----------|------|---------|
| P0 | Shared TP/SL helper: dashboard + resolver | Consistent levels end-to-end |
| P1 | Recompute R:R after normalize; PM crypto gets vol-aware TP/SL | Fewer bogus Smart rejects; cleaner geometry |
| P2 | Closed-book TP/SL outcome study → tier tweaks | Data-driven vol tier table |
| P3 | Fee/slippage overlay on closed stats | Realistic expectancy |

---

## 5. Commands / artifacts

```bash
python tools/analyze_audit_scores_vs_pnl.py --dashboard audit_dashboard/data/dashboard_data.json
python tools/audit_smart_gate_funnel.py audit_dashboard/data/dashboard_data.json
python tools/fetch_audit_dashboard_snapshot.py   # optional: latest live JSON
```

Related docs: `docs/AUDIT_PICKS_EDGE_ANALYSIS_2026-04-06.md`, `TRACE_LOG.MD`, `docs/REDIS_BUS_CHANGELOG.md`.

---

## 6. Non-goals

- Widening Smart or active gates globally to “get more picks” without funnel evidence.
- Using **open** unrealized PnL as the primary KPI for score quality (closed book + gates only).
