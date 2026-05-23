# Audit dashboard: Strong / EDGE / RSI·VOL empties + thin asset-class actives

**Scope:** [audit_dashboard/template.html](e:/findtorontoevents_antigravity.ca/audit_dashboard/template.html) Active Picks table on `findtorontoevents.ca/audit`, payload enrichment in [audit_trail/dashboard_generator.py](e:/findtorontoevents_antigravity.ca/audit_trail/dashboard_generator.py), gates in [audit_trail/quality_gates.py](e:/findtorontoevents_antigravity.ca/audit_trail/quality_gates.py), scanners ([multi_asset/scanner.py](e:/findtorontoevents_antigravity.ca/multi_asset/scanner.py), [alpha_engine/smart_picks_engine.py](e:/findtorontoevents_antigravity.ca/alpha_engine/smart_picks_engine.py)).

**Status:** Strong-column UI bug fixed in template (2026-04-15): `_ic_strong` now honors `pick.strong` / `pick.strong_signal` like the Strategy column. Remaining items below are follow-ups.

---

## 1. Why **Strong** looked empty

**Code path:** `_picksTableInner` → `c.key === '_ic_strong'` (template ~6120).

**Root cause (fixed):**

- The **Strategy** column already had a fallback: `window._strongSignals[ssKey]` **or** `p.strong === true` / `p.strong_signal === true` (~6177–6188).
- The dedicated **Strong** column only checked `window._strongSignals[ssKey]` and returned em dash otherwise.
- `strong_signals.json` is a narrow feed (often stale or few keys); most picks never appear in the map.

**Fix applied:** Strong column now uses the **same OR** as the strategy badge (map **or** pick flags), with tooltip noting when neither applies.

**Follow-ups (optional):**

- Regenerate / widen [alpha_engine/data/strong_signals.json](e:/findtorontoevents_antigravity.ca/alpha_engine/data/strong_signals.json) (or `/audit/data/strong_signals.json` when deployed) so more rows match by `symbol|strategy`.
- Align `ssKey` with `_resolveStrategyAlias` everywhere strong signals are keyed (avoid alias mismatches).

---

## 2. Why **EDGE** (`verified_edge`) looked empty

**Code path:** `c.key === 'verified_edge'` → `getVerifiedTier(p)` (~6369–6381).

**Root cause (by design, not a bug):**

- `getVerifiedTier` uses `window._verifiedEdgeIndex` built from **closed** ledger stats (`buildVerifiedEdgeIndex`, ~1741+).
- **GOLDEN** requires a qualifying **(strategy, symbol)** combo **and** strategy overall not decayed.
- **VERIFIED** requires strategy-wide stats (e.g. n≥30, WR≥55%, PF≥1.5 with losses — see tooltip on column).
- **Active picks** often use **new** symbol/strategy pairs or thin forward history → **tier stays `null`** → cell shows **—**.

**Plan / UX improvements:**

| Priority | Action |
|----------|--------|
| P1 | Tooltip already explains; add short subtitle under Active Picks: “EDGE blank = no GOLDEN/VERIFIED closed-book tier for this row (normal for new names).” |
| P2 | Optionally show a **lighter badge** for “TRACK ONLY” when `_ic_track` has WR but `getVerifiedTier` is null — avoids users reading blank as broken. |
| P3 | Ensure `dashboard_generator` / resolver keeps enriching `strat_fwd_wr`, `strat_fwd_trades` so **Track** and HC columns are populated even when EDGE is blank. |

---

## 3. Why **RSI** / **VOL** were empty for some picks

**Code path:** `c.key === 'rsi_at_entry'` / `volume_ratio` (~6270–6351).

**Root cause:**

1. **Primary:** Values come from pick payload: `rsi_at_entry`, `rsi`, `rsi_14`, `ml_features_at_entry`, `sb_rsi_at_entry` (and analogs for volume).
2. **Lazy fill:** Only for symbols ending **`USDT` / `USDC`** via `fetchBinanceKlinesWithFailover` (Binance spot klines).
3. **Non-crypto** tickers (`EURUSD=X`, `AAPL`, `GC=F`, `SPY`, etc.) **do not** match that branch → cell shows **-** unless the **scanner / generator** wrote RSI/VOL into the pick.

**ColTips** already document this (~5780–5781).

**Plan:**

| Priority | Action |
|----------|--------|
| P1 | **Server-side:** In `dashboard_generator`, extend enrichment (or a small post-step) to compute RSI-14 + volume ratio from **existing** price series for non-crypto when yfinance/Binance data is already fetched for live PnL — avoid duplicating client logic. |
| P2 | **Scanner-side:** Ensure `multi_asset/scanner.py` (and other non-crypto emitters) set `rsi_at_entry` / `volume_ratio` at signal time from the same OHLCV used for the signal. |
| P3 | **Client (optional):** Lazy-fetch via a **Yahoo-style** endpoint for `=X`, `=F`, and equity symbols — only if same-origin or CORS-safe; otherwise rely on P1/P2. |

---

## 4. Why **Commodities / Futures / ETFs / Bonds** had no active picks

**Observations from codebase:**

1. **`non_crypto_performance` / Active column** counts **open picks in `picks.active`** after `passes_active_gate` ([dashboard_generator.py](e:/findtorontoevents_antigravity.ca/audit_trail/dashboard_generator.py) recomputes from final active list).
2. **Empty pipeline:** If `picks.active` and `picks.active_raw` both have **0** rows for a class, **no opens exist in merged JSON sources** — run `python tools/audit_nc_active_investigation.py` on fresh `dashboard_payload.json` to confirm.
3. **Gates / policy (addressed in recent commits):** ETF hard-ban removed in favor of narrow ETF allow; `BLOCKED_ASSET_CLASSES` cleared; smart-picks commodity/futures policy split; breadth pass; higher non-crypto cap; expanded multi_asset futures universe — see git history on `quality_gates.py`, `smart_picks_engine.py`, `multi_asset/scanner.py`.
4. **Operational:** `multi_asset/data/active_picks.json` must be produced by running `multi_asset/scanner.py`; dashboard reads that path.

**Plan:**

| Step | Action | Owner |
|------|--------|--------|
| 1 | CI or cron: run multi-asset scanner on schedule; fail health check if `active_picks.json` stale > N hours | Ops |
| 2 | After policy changes, regenerate payload and re-run `audit_nc_active_investigation.py` — expect ETF `raw >= active` when narrow gate filters some ETF rows | Dev |
| 3 | If classes still 0/0: expand signals in scanner (more symbols/strategies) rather than lowering gates further | Dev |
| 4 | Document expected **EDGE** / **RSI** blanks for thin classes so support does not file false “broken UI” tickets | Docs |

---

## 5. Verification checklist

- [ ] Local: open audit template build, Active Picks table — **Strong** shows star when `pick.strong` true even if JSON map missing.
- [ ] **EDGE** — confirms **—** for a known-new pair; **GOLDEN**/**VERIFIED** for a known combo from closed index.
- [ ] **RSI/VOL** — crypto USDT row fills after lazy fetch; forex row shows **-** until server/scanner enrichment (P1/P2).
- [ ] `python tools/audit_nc_active_investigation.py` — per-class `active` vs `active_raw` after full pipeline run.
- [ ] Deploy: edit **template** only per project rule; let dashboard workflow regenerate `index.html` if applicable.

---

## 6. References (in-repo)

- Strong feed fetch URLs: template ~14495 (`strong_signals.json` paths).
- `getVerifiedTier` / `buildVerifiedEdgeIndex`: template ~1741–1837.
- RSI/VOL lazy Binance branch: template ~6284–6313, ~6328–6350.
- Non-crypto active investigation tool: [tools/audit_nc_active_investigation.py](e:/findtorontoevents_antigravity.ca/tools/audit_nc_active_investigation.py).
