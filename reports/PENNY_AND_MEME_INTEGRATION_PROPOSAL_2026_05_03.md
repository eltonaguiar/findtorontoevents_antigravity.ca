# Penny Stocks + Meme Coins — Integration Proposal

**Date:** 2026-05-03
**Author:** Claude (Opus 4.7)
**Status:** PROPOSAL — no code changes in this PR. Approve before implementation.
**Default state:** OFF (opt-in via feature flag, per user instruction)

---

## TL;DR

Both classes are **mostly already wired in code but gated off**. The work is configuration + thresholds + dashboard surfaces, not new pipelines. Treat as two separate v1 PRs after this proposal lands:

| Class | Existing scaffolding | Net new work |
|---|---|---|
| **PENNY (penny stocks)** | `alpha_engine/asset_class.py:62`, `audit_trail/backfill.py:53-91` returns `PENNY_STOCK`; live scraper `scripts/penny_stock_picks.py` ($1-$5, NYSE/NASDAQ only) | hc_filter.js PENNY branch, hc_gate_params.json penny block, feature flag, dashboard dropdown unblocklist, **resolver threshold fix for sub-$1 stocks** |
| **MEME (meme coins)** | `alpha_engine/asset_classification.py:18-21` defines `AssetClass.MEME`; `:215-217` patterns (PEPE, WIF, DOGE, SHIB, BONK, FLOKI, MAGIC, AI16Z, FARTCOIN, etc.); `data/meme_scanner_active.json` exists; `dashboard_generator.py:3666` wires meme_scanner; `:3203` flag `ASSET_CLASS_MAP_MEME_TO_CRYPTO=1` (default ON, currently remaps MEME→CRYPTO on payload) | hc_filter.js MEME branch, hc_gate_params.json meme block (different shape — see below), feature flag, optional `meme_risk_filter.py` |

---

## 1. PENNY STOCKS

### 1.1 Surface area (files that need a PENNY case)

- `config/hc_gate_params.json` — add `forwardWRMinPctPenny`, `scoreFloorPenny` block.
- `audit_dashboard/hc_filter.js:30-46` (defaults) + `:337-362` (`passesHcFilter` switch) — add `else if (assetClass === 'PENNY')` branch.
- `audit_dashboard/template.html` — asset-class filter dropdown currently blocklists non-canonical classes; add PENNY toggle gated on feature flag.
- `config/feature_flags.json` — add `enable_penny_stocks: false`.
- `alpha_engine/production_scanner.py` — conditional loader for `/findstocks/portfolio2/data/penny_picks_latest.json` when flag is on.
- **Resolver fix:** `alpha_engine/outcome_resolver.py:115-126` — current per-class threshold `EQUITY=5bp` is wrong for sub-$1 stocks. On a $0.50 stock, 5bp = $0.000025. Need `max(5bp, 0.5% × entry_price)` for PENNY, OR a flat $0.01 floor. Decision: dynamic `max(5bp, 0.5% × entry)` avoids hardcoding cents.

### 1.2 Data source (already shipped)

- `scripts/penny_stock_picks.py` — yfinance-based, $1-$5 filter, 200K min volume, $50M+ market cap. Hard-rejects OTC/pink sheets. Output: 15-20 picks/day at `/findstocks/portfolio2/data/penny_picks_latest.json`. Scoring: Altman Z, Piotroski F, Clenow momentum, RSI, PEAD. TP +30% / SL -15%.
- **No new external feed needed for v1.** OTC integration explicitly deferred — Reg SHO + short-borrow friction + sparse quotes make backtests unreliable.

### 1.3 Proposed gating thresholds

| Param | Value | Rationale |
|---|---|---|
| `forwardWRMinPctPenny` | 50 | Relaxed 5pp from EQUITY due to micro-cap vol (±8-12% daily vs ±2-3% EQUITY). |
| `scoreFloorPenny` | 40 | Match COMMODITY/FUTURES floor; penny is noisier. |
| `forwardTradesMinPenny` | 20 | Demand 4× the EQUITY n=5 floor — small-cap idiosyncratic events dominate small samples. |
| `confidenceMaxPenny` | 0.85 | Insider moves + short squeezes = surprise tail risk. |
| Per-symbol entry price | $1.00 - $5.00 | Already enforced upstream. |
| Per-symbol market cap | $50M - $2B | Stays inside short-borrow easy-borrow zone. |

### 1.4 Wire-up plan (Wire-Up Rule compliant)

**PR-A (config + UI gate, no behavior change):**
- Add penny block to `config/hc_gate_params.json`
- Add PENNY branch to `hc_filter.js`
- Add `enable_penny_stocks: false` to `config/feature_flags.json`
- Add PENNY to dashboard asset-class dropdown (gated to render only when flag is true)
- **No production caller wired yet** — labeled opt-in sidecar with `## Wiring Plan` section in PR body naming PR-B target.

**PR-B (production wire-up, behind flag):**
- `alpha_engine/production_scanner.py` reads `penny_picks_latest.json` when `enable_penny_stocks=true`
- `alpha_engine/outcome_resolver.py` PENNY threshold `max(5bp, 0.5% × entry)`
- Tests: `tests/test_penny_integration.py` covers flag-OFF=zero PENNY rows, flag-ON=picks flow.

**PR-C (default-on lift, only after baseline):**
- Lift `enable_penny_stocks → true` only after n≥100 noise-filtered closed PENNY trades show WR ≥55% + PF ≥1.5 documented in `reports/penny_stock_baseline_*.md`.

### 1.5 Risks

- **Reg SHO threshold securities:** sub-$5 names face short-borrow friction; mitigated by `enable_penny_stocks` shorting opt-out (long-only v1).
- **Pump-and-dump cohort:** social-media coordination on micro-caps. Filter: reject if symbol appears on >2 retail-cohort sources within 1h window.
- **Resolver threshold mismatch:** the bug noted in 1.1 — must ship in PR-B alongside the wire-up.
- **Liquidity cliff:** $100K market order on a $5 stock eats 2-3% slippage. Mitigation: position sizer caps PENNY at 0.5% × ADV.

---

## 2. MEME COINS

### 2.1 Current state (already wired but remapped away)

- `AssetClass.MEME` enum exists at `alpha_engine/asset_classification.py:18-21`.
- `_MEME_PATTERNS` regex at `:215-217`: PEPE, WIF, DOGE, SHIB, BONK, FLOKI, PEOPLE, WOO, MAGIC, GMEE, BIGTIME, GOAT, ACT, AI16Z, FARTCOIN.
- Pipeline: `data/meme_scanner_active.json` (currently `[]`), refreshed hourly via `scripts/meme_scanner_monitor.py`.
- `audit_trail/dashboard_generator.py:3666` wires `("meme_scanner", "data/meme_scanner_active.json", None)` into pick collection.
- **Critical:** `audit_trail/dashboard_generator.py:3203` flag `ASSET_CLASS_MAP_MEME_TO_CRYPTO=1` defaults ON — meme picks are silently relabeled CRYPTO on the dashboard payload. Today there is no MEME bucket in `asset_class_health`.

### 2.2 Sub-classification: top-level vs sub-field

| Option | Pro | Con | Verdict |
|---|---|---|---|
| **A — keep top-level `MEME_COIN` (current code)** | Clean separation, easy gating, minimal schema churn | Breaks "all crypto" aggregations (need dual-path) | **Recommended for v1.** Just flip the remap flag off behind feature flag. |
| **B — `CRYPTO + crypto_subclass=MEME`** | Preserves CRYPTO totals | New field across 50+ pick sources | Defer to v2. |

### 2.3 Proposed gating thresholds (different shape from majors)

Meme coins pay via R:R, not WR. Gating on the standard 70% WR floor rejects them all.

| Param | Standard (CRYPTO) | MEME proposal | Rationale |
|---|---|---|---|
| `forwardWRMinPctMeme` | 70 | **40** | Empirical meme base WR 25-35%; 40% = filtered cohort. |
| `scoreFloorMeme` | 55 | **45** | Meme momentum scoring is structurally lower. |
| `forwardTradesMinMeme` | 5 | **10** | Higher noise → demand more closures. |
| `confidenceMaxMeme` | 0.90 | **0.85** | Wash-trade + flash-crash tail. |
| `riskRewardFloorMeme` | (none) | **2.5x** | NEW gate — reject if entry-to-TP < 2.5× entry-to-SL. This is the load-bearing meme filter. |

### 2.4 Wire-up plan

**PR-A (config + flag, no behavior change):**
- Add `MEME_*` block to `config/hc_gate_params.json`
- Add MEME branch to `hc_filter.js:337-362`
- Add `enable_meme_coins: false` to `config/feature_flags.json`
- When `enable_meme_coins=true`, automatically set `ASSET_CLASS_MAP_MEME_TO_CRYPTO=0` in `dashboard_generator.py:3203` so MEME bucket appears on payload.

**PR-B (risk filter module, opt-in):**
- New `alpha_engine/meme_risk_filter.py` exposing `is_safe_meme(pick) -> (bool, reason)` checking:
  - DexScreener `is_honeypot=false`, `liquidity_locked >= 6 months`
  - 24h volume vs 7d avg vol-spike ratio < 8× (wash-trade screen)
  - Liquidity USD >= $500K
  - Contract age >= 14 days
  - Cohort signal count <= 2 within 1h window
- Wired into `production_scanner.py` ONLY when `enable_meme_coins=true`.

**PR-C (default-on lift):**
- Lift `enable_meme_coins → true` only after n≥100 noise-filtered closed MEME trades show WR ≥40%, PF ≥1.2, median R:R ≥2.0× across top 20 symbols, plus a deep-dive report `reports/deep_dive_meme_coins_*.md` (per CLAUDE.md deep-dive process).

### 2.5 Data sources

| Source | Free | Rate limit | Use |
|---|---|---|---|
| DexScreener | yes | 300/min | Primary liquidity / honeypot / verified-contract |
| Birdeye | yes (limited) | 60/min | Holder concentration, on-chain depth |
| GeckoTerminal | yes | 30/min | Backup price + pair history |
| Pump.fun | yes | 100/min | Solana meme launches |
| Etherscan | yes (key) | 5/sec | Contract age, audit status (async batch) |

---

## 3. Cross-cutting decisions

### 3.1 Feature-flag pattern (one canonical shape)

`config/feature_flags.json`:
```json
{
  "enable_penny_stocks": false,
  "enable_meme_coins": false,
  "policy_version": "v5-2026-05-03"
}
```

Each flag gates: (a) loader in `production_scanner.py`, (b) HC gate branch in `hc_filter.js`, (c) dashboard dropdown rendering, (d) any sub-class remap (e.g., MEME→CRYPTO flip).

### 3.2 Acceptance criteria (both classes, charter-aligned)

Per existing rule "Do not promote a class to 'proven' without n≥100 clean (post-noise-filter) trades":

1. n≥100 closed trades on opt-in cohort
2. Tier 2 minimum: PF >1.5, WR >50%, MDD <20% — OR documented rationale for relaxed thresholds (e.g., MEME R:R-driven model)
3. 24h/7d walk-forward shows no >5pp WR degradation vs backtest
4. Deep-dive report at `reports/deep_dive_<class>_*.md` per CLAUDE.md Goal #1 process
5. Risk register signed off (regulatory for PENNY, rugpull/wash-trade for MEME)

Until those criteria are met, both flags stay `false` regardless of model output.

### 3.3 Wire-Up Rule compliance

PR-A in each track is explicitly opt-in sidecar (no production caller change). Wiring Plan section names PR-B target file + function + expected wire-up date. PR-B is the wire-up. PR-C is the default-on flip with evidence.

### 3.4 What this proposal does NOT do

- No new pipelines, no new external feeds for v1 (penny scraper + meme_scanner already exist).
- No removal of existing CRYPTO-aggregation code paths.
- No size or position-management changes — kelly_position_sizer.py untouched.
- No MDD calculation methodology change.
- No commitment to ship v1 without baseline data — flags default off until n≥100 trades.

---

## 4. Decision points for user

Before any code lands, please confirm:

1. **PENNY:** OK to keep v1 universe = NYSE/NASDAQ $1-$5 only (defer OTC indefinitely)? **Y / N**
2. **MEME:** OK with relaxed-WR + R:R-floor gate model? **Y / N**
3. **Resolver penny fix:** OK to ship `max(5bp, 0.5% × entry)` for PENNY in PR-B (touches `outcome_resolver.py:115-126`)? **Y / N**
4. **Default state:** confirm both flags ship `false` and stay `false` until n≥100 baseline + deep-dive report. **Y / N**
5. **Sequencing:** PENNY first, MEME second? Or parallel tracks? **PENNY-first / parallel**

---

## 5. Cited code locations

- [alpha_engine/asset_class.py:62](alpha_engine/asset_class.py#L62) — `_CAT_MAP` penny entry
- [audit_trail/backfill.py:53-91](audit_trail/backfill.py#L53-L91) — `derive_asset_class_ext` returns PENNY_STOCK
- [scripts/penny_stock_picks.py](scripts/penny_stock_picks.py) — live scraper
- [alpha_engine/asset_classification.py:18-21](alpha_engine/asset_classification.py#L18-L21) — `AssetClass.MEME` enum
- [alpha_engine/asset_classification.py:215-217](alpha_engine/asset_classification.py#L215-L217) — `_MEME_PATTERNS`
- [audit_trail/dashboard_generator.py:3203](audit_trail/dashboard_generator.py#L3203) — `ASSET_CLASS_MAP_MEME_TO_CRYPTO` remap flag
- [audit_trail/dashboard_generator.py:3666](audit_trail/dashboard_generator.py#L3666) — meme_scanner pick wiring
- [audit_dashboard/hc_filter.js:30-46](audit_dashboard/hc_filter.js#L30-L46) — per-asset thresholds
- [audit_dashboard/hc_filter.js:337-362](audit_dashboard/hc_filter.js#L337-L362) — passesHcFilter switch
- [alpha_engine/outcome_resolver.py:115-126](alpha_engine/outcome_resolver.py#L115-L126) — `PNL_WIN_THRESHOLD_BY_CLASS`
- [config/feature_flags.json](config/feature_flags.json) — feature flag registry
