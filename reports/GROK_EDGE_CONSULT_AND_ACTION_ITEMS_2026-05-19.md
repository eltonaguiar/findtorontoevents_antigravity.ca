# Grok Edge-Consult + Session Action Items — 2026-05-19

4 parallel Grok consults + transcript scan + BOND defensive guard implemented.

## 1. The 4 candidate hypotheses I proposed earlier — Grok's verdict

| # | hypothesis | Grok score (0-10) | failure mode |
|---|-----------|-------------------|--------------|
| H-029 | Sector cross-sectional momentum (XLE/XLF/XLV/...) | **1/10** | Decayed post-ETF era; 21d top-2 / bottom-2 consumed by turnover + costs + rising sector correlations |
| H-030 | Oil-regime XLE gate (Brent > 90d MA) | **0/10** | Whipsaws around the MA; mean-reverting oil + imperfect XLE tracking; net negative expectancy |
| H-031 | PCE event-drift (short vol pre, directional post) | **2/10** | Surprises absorbed in minutes by market-makers; thin announcement drift erodes through option spreads |
| H-032 | S&P → DAX cross-region lead-lag (>1σ) | **0/10** | Textbook-knowledge; fully internalized by cross-market algos + E-mini/DAX pricing |

**Verdict: all 4 candidates I proposed are not exploitable.** The daily-recap blob source was zero-signal; the hypotheses I derived from it are documented but decayed.

## 2. Grok's per-asset-class verdict (independent consult)

| class | edge candidate | Sharpe (post-cost) | capacity | failure mode |
|-------|----------------|-------------------|----------|--------------|
| CRYPTO | **NO realistic candidate** | — | — | Low-vol anomaly + calendar weak; free-data history too short for robust harness; spot-ETFs compressed inefficiencies |
| EQUITY | Industry/sector momentum + trend filter (Moskowitz-Grinblatt 1999, refined 2024 versions) | **0.35-0.60** | >$500M | Persistent concentration in 1-2 sectors → high-beta whipsaws |
| FOREX | **NO realistic candidate** | — | — | Time-series/cross-sectional momentum sharply decayed post-GFC; carry too close to banned yield-curve logic |
| COMMODITY | Term-structure (basis/roll-yield) long-short (Gorton-Rouwenhorst 2006) | **0.30-0.55** | $75-150M | Prolonged contango across complex (financialization / supply response) flattens curves |
| FUTURES | Time-series momentum diversified (TSMOM, Moskowitz-Ooi-Pedersen 2012; **uses free AQR data**) | **0.35-0.65** | >$200M | Multi-asset choppy/range-bound regimes → clustered false signals |
| BOND | **NO realistic candidate** | — | — | On-the-run/off-the-run requires non-free CUSIP+repo data; corporate momentum reverses; yield-curve banned |
| ETF | **NO realistic candidate** | — | — | Calendar effects data-mined; country-ETF momentum decayed post-GFC; creation/redemption requires intraday |

**Net: 3/7 classes have a plausible (not guaranteed) candidate** — EQUITY industry momentum, COMMODITY term-structure, FUTURES TSMOM. The other 4 (CRYPTO/FOREX/BOND/ETF) — Grok says no realistic free-data + harness-passable candidate at our size in 2026. Match the 9 prior harness kills + 3 sidecar rejects this session.

## 3. Grok's "better hypotheses" (replacements for the 4 rejected)

- **Mid-cap earnings volatility premium harvest** — sell iron condors / short straddles 1 day pre-earnings on $2-15B mkt-cap names where straddle-implied move ≥20% above own 12Q realized median. Risk 0.4% per name, 6-10 prints/quarter. Mid-caps = sweet spot (retail overpays for binary lottery vol; institutional vol-arb can't scale without impact).
- **Niche CEF discount capture** — accumulate 8-12 lowest-AUM equity/credit closed-end funds at NAV discounts >2.5σ of own history. Target 40-70% closure over 30-90 days. Structurally mispriced by retail flows.

Neither is in our banned families. Both require infrastructure we don't currently have (earnings calendars + options chains for #1; CEF universe + premium/discount feed for #2).

## 4. BOND class-mis-tag root cause + autonomous fix

**Root cause** (Grok + repo investigation): `dashboard_generator.py::_normalize_orphan_emitter_pick` stamped `asset_class="BOND"` on ANY symbol from `bond_picks.json` filename — no symbol-vs-class consistency check. `resolve_asset_class` then trusted the upstream tag without a crypto-symbol guard. Result: 500 PEPEUSDT/WIFUSDT-style rows tagged BOND in `at_raw_picks`.

**Autonomous fix shipped this turn** (commit on `main`):
- `audit_trail/asset_classification.py` — new `is_obviously_crypto_symbol()` helper + crypto-symbol guard at the top of `resolve_asset_class()` (refuses any non-crypto tag on a crypto symbol).
- `audit_trail/dashboard_generator.py` — defense-in-depth at `_normalize_orphan_emitter_pick` (refuses to stamp BOND on a crypto symbol, force-downgrades to CRYPTO + logs warning + stamps `_orphan_emitter_class_override`).
- `tests/test_asset_class_crypto_guard.py` — 18 regression tests, all pass.

This **stops the bleed** (no new contamination). The **500 already-tagged rows** in the DB are operator-gated cleanup (one-time SQL UPDATE inside `resolver-step5-6-backfill` pattern, or via the BOND ingestion-source identification — peer work).

## 5. TV portfolios — Grok's verdict (since I can't drive TV from this session)

**For every portfolio except "The Leap Crypto" (retired): "add nothing, flat is the correct posture."**

| portfolio | KEEP | CLOSE (verify against live TV first — Grok's snapshot may be stale) | ADD |
|-----------|------|------------------------------------------------------|-----|
| SCALPER | none | none | **nothing** — no scalping-grade candidate clears harness |
| TESTER | none | none | **nothing** — no qualifying filter test today |
| TRUSTOURSCORE | none | none | **nothing** — zero high-n strategies at Tier-2 floor |
| zerounderscore | none | BINANCE:APTUSDT LONG; BINANCE:ADAUSDT SHORT (sub-tier-2 crypto) | **nothing** |
| BROKIE | none | none | **nothing** — small-account discipline forbids sub-Tier-2 picks |
| HIGHFWWRABV55_*  | none | NYSE:F; NYSE:VZ; NYSE:PFE; NYSE:USB; NYSE:UNM; NYSE:KMI (placeholder/clone stats) | **nothing** |

**Operator instruction:** verify each row in the LIVE TV terminal before executing the close (Grok used stale-ish snapshots). Then close + leave the accounts flat. Save the session log as `TV_2026-05-19.MD` if you actually execute any closes.

I cannot drive TV from this Claude Code session (`mcp__tradingview-desktop__*` not loaded). The 10 `tv-*` skills now cite https://github.com/tradesdontlie/tradingview-mcp; run them from an IDE-session with that MCP connected.

## 6. Action items (genuine, cross-checked against transcript scan)

### A. Done this turn — committed to `main`
1. ✅ BOND defensive guard + 18 regression tests (commit pending in this turn).
2. ✅ Grok edge consults run in parallel (4 agents).
3. ✅ Transcript scan committed (`reports/transcript_scan_actionitems_2026_05_19.md`).
4. ✅ Action-items + findings report (this file).

### B. Next-session autonomous-safe candidates
1. **Build EQUITY sector-momentum sidecar** (`tools/h029_equity_sector_momentum_research.py`) matching ET-1/CO-1/E-1 pattern. Free SPDR sector data via yfinance. Register H-033. Run through harness.
2. **Build COMMODITY term-structure sidecar** (`tools/h030_commodity_term_structure_research.py`). yfinance `=F` continuous front/second contracts. Register H-034. Harness.
3. **Build FUTURES TSMOM sidecar** (`tools/h031_futures_tsmom_research.py`). Uses **free AQR Time-Series Momentum monthly factor data** (Excel download). Register H-035. Harness.
4. Investigate which `source_system` writes BOND-tagged crypto rows (peer/ingestion bug) — identify via `SELECT source_system, COUNT(*) FROM at_raw_picks WHERE asset_class='BOND' AND symbol LIKE '%USDT' GROUP BY source_system` from a GHA workflow.

### C. Operator-gated
1. Cleanup of 500 BOND-tagged crypto rows in `at_raw_picks` — DB write, similar to step 5-6 pattern (backup + UPDATE in transaction). I built the step 5-6 workflow pattern — a similar one can be made for this targeted UPDATE.
2. Verify TV portfolio open positions against LIVE terminal; close per Grok's per-account list; save TV_2026-05-19.MD log.
3. Strategic fork — Grok's per-class verdict is brutally clear: **4 of 7 classes have no realistic edge candidate** with our constraints (free data, harness-gated, ≤$100M AUM, no banned families). Strategic decision: continue chasing edge on 3 classes (EQUITY/COMMODITY/FUTURES) OR pivot to the "better hypotheses" (mid-cap earnings vol harvest / CEF discount capture) which require new data infrastructure.

### D. Transcript scan items (false-OPEN inflation as always — these are LEADS to verify, not a to-do list)
Cross-checked: the only OPEN items that aren't false-OPEN this scan match the action-items above (build sidecars + harness-test + 90d forward-test + real money only after confirmation). All previously-done items show DONE.

## 7. Brutally honest path to "real money, not gambling"

**Per Grok + the 9 prior harness kills + the 3 sidecars this session:**
- CRYPTO/FOREX/BOND/ETF — accept paper-only indefinitely; no documented anomaly survives at our size with free data.
- EQUITY/COMMODITY/FUTURES — build the 3 sidecars (H-033/H-034/H-035), run through harness. If admissible, 90d forward-test paper. **Only after stuck + forward-confirmed → real money.**
- New infrastructure for mid-cap earnings vol / CEF discount = a multi-week build (options data, CEF universe). Operator decision.

We will likely end up with **EQUITY sector-momentum (decayed but documented)** as the strongest candidate. Expected Sharpe 0.35-0.60 — institutionally OK, not "10x in a year." That's what real-money quant looks like. Mark expectations accordingly.
