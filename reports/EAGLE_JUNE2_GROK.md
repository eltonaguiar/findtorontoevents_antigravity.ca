# EAGLE June 2 Quant Review — Grok

**Author:** Grok (Cursor session)  
**Date:** 2026-06-02  
**Goal #1:** Phenomenal `/audit` performance — institutional-grade edge per asset class  
**Live fetch:** 2026-06-02T06:56Z (`curl` → findtorontoevents.ca/audit/data/*)  
**NFA — research memo, not a sizing recommendation.**

---

## Executive summary

| Question | Answer |
|----------|--------|
| **More time?** | **Yes only for forward pilots** (ETF DM, crypto VWAP/Bollinger: virtual n=0, target n≥100). **No** for CRYPTO/EQUITY production — n=374/52 resolved, PF 0.89/0.33, negative expectancy. |
| **Strategies suck?** | **Bulk production emitters: yes** for capital. **Lab verified sleeves: no** — ETF dual momentum Tier-2; crypto VWAP/Bollinger WF OOS PASS. |
| **Doing wrong?** | Six backtest engines, lab ≠ production, 88 funnel / 78 silent strategies, disputed Smart/VA metrics, opt-in lab winners &lt;5% of pick volume. |
| **DNA mutate?** | **Surgical** (Faber, carry, sector mom) per `MUTATION_THREE_AXIS_PROTOCOL.md` — not blanket. |
| **Invert?** | **Per-strategy only** when OOS inverted PF&gt;1.3; never class-wide; Connors loss-skew ≠ wrong sign. |
| **Data feeds dead?** | **Secondary.** FRED/carry backtest gaps fixable; live CRYPTO pain = dedup, resolver, source mix (`battleground` 23%). |
| **Portfolio empty?** | **No** — `deepseek_v4__aggressive` has **11 open** on server; UI empty = bad URL Unicode, cache, or 0 closed rows. |
| **Where is edge?** | **Not** on money-ready production. **Maybe** on tournament model selection + **lab/pilot** sleeves — not yet wired as primary book. |

**Money-ready classes: 0/9.** Policy-clean Tier-2 live: **0/6 major classes.**

---

## 1. Live ground truth (size on this)

Sources: `audit_dashboard/data/money_ready_verdict.json`, `pf_registry.json` → `by_asset_class_policy_clean_net` (generated 2026-06-02T06:21Z).

| Asset class | n | WR | PF | Verdict | Top source (share) |
|-------------|---|-----|-----|---------|-------------------|
| CRYPTO | 377 | 35.5% | **0.89** | NOT_READY | battleground (23%) |
| EQUITY | 52 | 26.9% | **0.33** | NOT_READY | regime_terminal (40%) |
| FOREX | 32 | 28.1% | **0.48** | INSUFFICIENT | multi_asset_scanner |
| FUTURES | 13 | 15.4% | **0.52** | INSUFFICIENT | multi_asset_scanner (85%, artifact) |
| ETF | 3 | 66.7% | 1.46 | INSUFFICIENT | — |
| COMMODITY | 4 | 50.0% | 1.68 | INSUFFICIENT | — |
| BOND | 0 | — | — | INSUFFICIENT | — |

**Tier-2 bar:** PF&gt;1.5, WR&gt;50%, n≥100, MDD&lt;20%, DSR/PBO where applicable.

### Two books problem

| View | CRYPTO PF | Use? |
|------|-----------|------|
| Raw registry | ~1.46 (n≈1580) | **No** — duplicates, pre-policy |
| Policy-clean net | **0.89** (n=377) | **Yes** |
| Smart Picks headline | 78–88% WR, PF 9–18 | **DISPUTED** — `claude_gainer_st`, EXPIRED→WON, dup groups |

---

## 2. Lab vs live — root cause of “no top-notch by class”

**Full lab:** `verified_strategies/MULTI_CLASS_LAB_REPORT.json` (2026-06-02T05:52Z, real OHLCV).

| Class | Best lab sleeve | Lab PF / WR / n | Tier-2? | Live policy-clean PF |
|-------|-----------------|-----------------|--------|----------------------|
| **ETF** | Dual Momentum Sectors | 1.60 / 53.8% / 104 | **PASS** | n=3 |
| CRYPTO | Donchian | 7.04 / 50% / 370 | SUB_T2 (MDD −45%) | 0.89 |
| CRYPTO | Connors H-103 | 1.36 / 66% / 5740 | SUB_T2 | 0.89 |
| EQUITY | 12-1 momentum | 2.31 / 43% / 228 | FAIL WR/MDD | 0.33 |
| FOREX | Carry | 2.27 / 15% / 13 | FAIL n/WR | 0.48 |
| COMMODITY | TSMOM | 1.08 / 54% / 5650 | FAIL PF | n=4 |

**Walk-forward (costed pilot, 2026-06-02):**

| Sleeve | Verdict | OOS PF | OOS n |
|--------|---------|--------|-------|
| `etf_dual_momentum` | **PASS** | 1.21 | 32 |
| `crypto_donchian` | **FAIL** | — | 67 |
| `vwap_reversion` | **PASS** | 1.32 | 516 |
| `bollinger_mr` | **PASS** | 1.67 | 38 |
| `equity_momentum_12_1` | **FAIL** | — | — |

**Forward pilots today** (`reports/etf_forward_stats_latest.json`, `crypto_wf_forward_stats_latest.json`):

- Virtual **n_closed = 0** on all sleeves → `promotion_ready: false` (gate: n&lt;100).
- ETF pilot has **open XLE** rotation signal; not yet a closed forward track.

**Structural root cause:** Production scanner still emits from **hundreds** of `source_system` rows; lab winners are **opt-in sidecars** (`production_scanner` block **3b-VFD**, env flags default OFF, ETF merge gated on `recommend_scanner_enable`). Until one clean sleeve dominates per class, live rollups stay diluted.

**Engine bifurcation** (`reports/backtesting_methodology_audit_2026-06-02.md`): ~80% of academic strategies use `real_data_backtest.py` (no purge/embargo/DSR). Promotion labels on lab files do not apply to tournament + mercury2 + battleground volume.

---

## 3. Proper backtesting methodology (institutional standard)

Single admissibility pipeline — **no capital without every stage:**

### Stage 0 — Pre-registration (M-107)

- Entry in `reports/hypothesis_registry.json` **before** OHLCV.
- Kill: H-001 COT leakage, unstable sign at scale.

### Stage 1 — Real data only

- OHLCV: yfinance / Binance mirror chain / FRED+curl cache (`VERIFY_SKIP_FRED=1` only for dev).
- **Forbidden:** synthetic bars, config-only carry without cache, closed-pick replay as “backtest.”

### Stage 2 — Purged walk-forward (mandatory promotion engine)

- López de Prado purge + embargo — `alpha_engine/rigorous_backtest_harness.py` + `verified_strategies/walkforward_suite.py`.
- Report IS/OOS Sharpe, PF, WR, n, MDD **after costs** (CRYPTO 30bps RT; EQUITY/ETF 5–10bps).

### Stage 3 — Multiple-testing correction

- DSR &gt; 0.95, PBO &lt; 0.05, SPA when ≥2 competitors per class.
- Conservative N = all variants ever tried.

### Stage 4 — Robustness

- Stationary block bootstrap (not i.i.d. trade shuffle on crypto).
- Regime cells: trend × vol, min 30 trades/cell or fail.

### Stage 5 — Forward paper (virtual book)

- `verified_strategies/paper_pilot/*` + `pilot_virtual_book.py` pattern.
- **Promote iff:** forward n≥100 **and** PF≥1.5 **and** WR≥50% **and** forward PF ≥ 0.85 × lab OOS PF.

### Stage 6 — Live shadow → sized capital

- Opt-in env flag → 30d shadow log → 0.1% sizing → scale under MDD cap.

**Current gap:** Stages 2–4 optional/fragmented; Stage 5 started; Stage 6 not reached for any class.

Canonical doc: `docs/BACKTESTING_GUIDE.md`.

---

## 4. Mutate / invert / kill — decision matrix

| Action | When | Examples |
|--------|------|----------|
| **Kill** | Post-fix PF&lt;0.8, n≥100, no lab rescue | ConnorsRSI2 crypto (lab PF 0.90 equity bleed) |
| **Mutate (3-axis)** | Lab PF&gt;1.5, live PF&lt;1, n≥30 | Faber: universe/params/costs |
| **Invert** | OOS inverted PF&gt;1.3, symmetric costs | Rare; never class-wide |
| **Wire lab→prod** | WF PASS + `promotion_ready` | ETF DM, crypto VWAP/Bollinger |
| **Wait** | Forward n&lt;100, lab PASS | **Current** ETF/crypto/Faber pilots |

**Connors H-102:** harness **UNTESTED** (0 windows, admissible=False) — `CONNORS_RSI2_CRYPTO_ENABLED` must stay shadow-only.

**Donchian:** WF **FAIL** — hard-blocked in `crypto_verified_donchian.py`.

---

## 5. Data feeds — honest assessment

| Issue | Severity | Status |
|-------|----------|--------|
| FRED urllib timeout (gx10) | P2 backtest | `tools/fetch_fred_carry_cache.py` + curl fallback |
| Binance OHLCV pagination | OK | 2500 bars majors |
| Resolver EXPIRED→WON, dup signal-ts | **P0 live** | Policy-clean fixes applied; disputed surfaces remain |
| Tournament resolver backlog | P1 | Blocked model n≥100 historically |
| PF mark-to-market | P3 UI | Entry marks if `get_close` fails — not empty book |

**Binding constraint is governance + emitter selection, not missing candles.**

---

## 6. Portfolio audit (all 81 keys)

**Roster:** `https://findtorontoevents.ca/audit/data/pf_portfolios.json` (n=81, generated 2026-06-02T06:27Z).

| Metric | Count |
|--------|-------|
| Portfolios with **≥1 open** position | **66** |
| Truly empty (0 open, 0 closed) | **15** |
| HTTP 404 | **0** |

### Example: `deepseek_v4__aggressive`

- **Not empty:** 11 open, 0 closed, 2 NAV points, roster `latest_nav` ≈ $100,403.
- JSON: `https://findtorontoevents.ca/audit/data/pf_portfolio_deepseek_v4__aggressive.json`
- Clean UI: `https://findtorontoevents.ca/audit/pf.html?key=deepseek_v4__aggressive`

**Why UI looked empty:**

1. Invisible Unicode in pasted `?key=` → wrong filename → 404 → “Pending first daily run.” Fix: `audit_dashboard/pf.html` `getKeyParam()` strips U+200B–F8FF.
2. Browser cache — hard refresh.
3. **Closed tab empty** — book is ~2 days old; open tab should show 11 rows when JSON loads.

**Caveat:** Tournament PF (deepseek_v4 PF≈3.5, n≈208 on **tournament picks**) ≠ production CRYPTO money-ready (PF≈0.89). PF page = **paper book** from tournament seed, separate universe.

---

## 7. Where is the edge? (surface map)

### Trust hierarchy

1. `money_ready_verdict.json` + `pf_registry` `by_asset_class_policy_clean_net`
2. `dashboard_data.json` → `asset_class_health`
3. `pick_summary_stats_2w.json` / `48h.json` (raw; read caveats)
4. Nav Smart / VA / HC / ELITE — **DISPUTED** on CRYPTO
5. `MULTI_CLASS_LAB_REPORT.json` / `WALKFORWARD_REPORT.json` — promotion candidates only
6. `ai_tournament_leaderboard.json` — model selection, not money-ready

### `/audit/` (main dashboard)

- **No class money-ready.** CRYPTO/EQUITY FAIL DSR + expectancy.
- DISPUTED banner required for Smart/VA/HC CRYPTO tiles.
- Verified-edge strip: `audit_dashboard/data/verified_edge_status.json` (pilot gates).

### `pick_funnel.html`

- `nav_surface_edge_matrix.json`: **no surface** has sustainable class-level `verdict: edge`.
- Smart Picks CRYPTO can show PF≈2.9 + holdout PASS but `why_no_edge`: **67% mega_mutation concentration** — not generalizable.
- Strategy funnel **100% WR** rows often contradict `pf_registry` canonical PF.

### `ai-tournament.html`

- **Strongest headline PF** on tournament-resolved picks (live top by `pf_ci_lo`):

| Model | pf_ci_lo | WR | n |
|-------|----------|-----|---|
| fireworks_qwen | 5.59 | 89% | **9** |
| gpt4o_mini | 2.82 | 80% | **10** |
| **deepseek_v4** | **2.52** | 58% | **208** |
| grok3 | 1.74 | 56% | 303 |

- Use for **model tournament research**, not production class sizing. Small-n leaders (n&lt;15) are overfit noise.

### Lab + forward pilots (best path to real edge)

| Sleeve | Lab | WF | Forward n | Scanner |
|--------|-----|-----|-----------|---------|
| ETF dual momentum | Tier-2 PASS | PASS | 0 | `ETF_VERIFIED_*` shadow until `promotion_ready` |
| Crypto VWAP | — | PASS | 0 | `CRYPTO_VERIFIED_VWAP_ENABLED` |
| Crypto Bollinger MR | — | PASS | 0 | `CRYPTO_VERIFIED_BOLLINGER_MR_ENABLED` |
| Donchian | High IS PF | **FAIL** | — | **Blocked** |
| Connors RSI-2 | High WR | — | — | H-102 **UNTESTED** |

---

## 8. Prioritized 90-day plan

### Week 1–2 (P0)

1. Zero default sizing on CRYPTO/EQUITY/FOREX until `money_ready_verdict` flips.
2. Enforce concentration + dup_groups before funnel PF display.
3. FTP-deploy `pf.html` + `verified_edge_status.json` after changes.
4. Daily `python3 tools/run_verified_pilots_daily.py`.

### Week 2–6 (P1)

5. ETF DM: enable `ETF_VERIFIED_DUAL_MOMENTUM_ENABLED=1` only when `recommend_scanner_enable` true.
6. Crypto VWAP/Bollinger: same forward n≥100 gate.
7. Depromote `regime_terminal`, unverified battleground paths from active sizing.

### Week 4–12 (P2)

8. Unify `real_data_backtest.py` strategies onto purged WF + costs.
9. Strategy census: kill/quarantine 78 silent funnel entries; max 3 promoted sleeves/class.
10. Block bootstrap in `strategy_verification_engine.py` (replace i.i.d. MC).

---

## 9. Reproducer commands

```bash
# Live verdict
python3 alpha_engine/money_ready_verdict.py --json
python3 tools/build_pf_registry.py

# Lab + walk-forward
VERIFY_SKIP_FRED=1 python3 tools/multi_class_strategy_lab.py
python3 verified_strategies/walkforward_suite.py --only pilot
python3 verified_strategies/walkforward_suite.py --only hyro

# Forward pilots
python3 tools/run_verified_pilots_daily.py
python3 tools/pilot_forward_dashboard.py
python3 tools/write_verified_edge_status.py

# Live portfolio check
curl -s 'https://findtorontoevents.ca/audit/data/pf_portfolio_deepseek_v4__aggressive.json' | python3 -m json.tool | head -40
```

---

## 10. Related artifacts (this repo)

| File | Role |
|------|------|
| `reports/quant_strategy_root_cause_review_2026-06-02.md` | Prior session quant memo |
| `reports/audit_cross_surface_edge_2026-06-02.md` | Cross-page edge comparison |
| `reports/backtesting_methodology_audit_2026-06-02.md` | Engine fragmentation audit |
| `updates/2026-06-02-verified-strategies-production-wire-up.md` | 3b-VFD scanner wiring |
| `docs/BACKTESTING_GUIDE.md` | Harness methodology reference |

---

**Sign-off:** The institution does not have a “wait 90 days on production picks” problem. It has a **research–production gap** and **measurement honesty** problem. Capital should flow only through the admissibility pipeline in §3, starting with ETF dual momentum and crypto VWAP/Bollinger once forward virtual books hit n≥100 — not from tournament leaderboard PF, Smart Picks tiles, or raw registry rollups.