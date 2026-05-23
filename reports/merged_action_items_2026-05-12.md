# Merged Action Items — 2026-05-12

**Sources:** this Opus session + parallel cloud-agent session (Grok COT analysis + hedge-fund rescue swarm + hidden-insights audit)
**Status legend:** ✅ SHIPPED · 🔨 IN WORKING TREE (uncommitted) · 🟢 NET-NEW · ❌ WRONG/STRIKE

---

## P0 — Ship within 7 days (money-ready blockers)

### ✅ P0-A · FOREX hard-cap sizing=0 until PF≥0.8
- Shipped in **PR #909** (`risk_policy_check.py:is_forex_sizing_allowed()`), merged 2026-05-12 05:00Z.
- **Remaining:** verify `block_reason` appears in `dashboard_data.json` post-deploy; re-run `tools/mutation_analysis.py` on fresh n at 30 days.

### 🟢 P0-B · BOND three-layer unblock *(replaces both the "allowlist" and "FRED timeout" theories — both falsified, see [reports/bond_root_cause_2026-05-12.md](reports/bond_root_cause_2026-05-12.md))*
Must ship as **one PR cluster** — fixing only one layer does nothing:
- **B1:** Lower `_elite_floor` 40→35 for BOND in `.github/workflows/bond-agent.yml`. Bond signals fail curation (7 raw → 0 quality at 2026-05-12T15:31Z run).
- **B2:** Add `FORWARD_GATE_OVERRIDES = {"bond": 10}` in `alpha_engine/forward_validator.py:389`. Every `bond_*` strategy has 0 forward trades; 50-trade global gate is unreachable.
- **B3:** Merge `non_crypto_agent/data/bond_picks.json` → `alpha_engine/data/active_picks.json` in bond-agent workflow. Today they never connect.
- **❌ STRIKE from §8 addendum:** "FRED API timeout / add `FRED_API_KEY` to secrets" — falsified; bond-agent.yml makes zero FRED calls.

### 🟢 P0-C · CRYPTO source-volume cut residuals
- ✅ Already shipped: **PR #906** (`quan_engine` 18%→12%), **PR #908** (`crypto_soc_*` quarantine), **PR #907** (`kimi_signal_tracking` blacklist).
- **Remaining:** 48h same-symbol cooldown for BTC/ETH only (Chinese report Risk #6); route `source_system='unknown'` through `mutation_analysis.py`.

### 🔨 P0-D · Confidence-inversion gate (cloud-agent finding)
- **In working tree, mid-edit by cloud agent** at [audit_trail/quality_gates.py](audit_trail/quality_gates.py) +56 lines.
- Backing data: CRYPTO 85-100% conf = 27.9% WR vs 0-25% conf = 52.8% WR (−24.9pp); EQUITY 85-100% conf = 22.2% WR (−41.0pp). FOREX/ETF exempt (confidence works correctly there).
- **Remaining:** cloud agent must commit + push so the rest of the queue can layer on top without conflict.

### 🟢 P0-E · Activate dormant high-WR strategies *(hidden-insights audit, hedge-fund swarm theme #1)*
- 41 strategies with WR ≥ 55% have **zero active picks**. Top three orphans:
  - `cftc_cot_commercial_signal` — 79.7% WR, n=59
  - `rs-breakout-scout` — 78.8% WR
  - `donchian-stock-breakout` — 78.6% WR
- **Action:** set `CFTC_COT_FETCHER_ENABLED=1` in cron workflow; wire `cftc_cot_commercial_signal` through `passes_smart_gate` per Wire-Up Rule. Audit the remaining 38 for production-path callers.

### 🟢 P0-F · COT commercial z-score gate *(Grok COT analysis + hedge-fund swarm theme #1)*
- Repo already has `cftc_cot_fetcher.py`, `multi_asset_cot`, USDA/COT fetchers — plumbing exists, **gate doesn't**.
- Measured edge on closed picks: COMMODITY with commercial z-score > +1.0 → +2.8pp WR / PF > 4.5. Tuesday + commercial-buying-acceleration → +18% WR lift on next-week CRYPTO picks.
- **Action:** add `cot_commercial_zscore` feature in `extract_features()`; add hard gate in `quality_gates.py` (long-only when z > +1.0, reject COMMODITY when z < −1.5). Nightly `feature_store` table in MySQL for pre-computed z-scores.
- **Caveat:** the +18% Tuesday/COT claim and +2.8pp WR lift are Grok-asserted numbers; bootstrap-validate before shipping the gate (don't trust them as priors).

---

## P1 — Ship within 2–4 weeks

### 🟢 P1-A · FOREX composite ranking (Chinese report formula)
- `Final_Score = 0.4·WR + 0.3·Trust + 0.2·Score + 0.1·Liquidity` + four-tier WR bands (A≥65 / B 55–64 / C 50–54 Major-only / reject).
- Ship behind feature flag `FOREX_RANKING_V2`; A/B against current scoring on closed Q2 2026 picks.

### 🟢 P1-B · EQUITY sample expansion (Chinese report P1-2)
- Smart Picks gate 85→78; dynamic Trust = `base × (1 + log(n)/10)`; early WR cut at n≥10 / threshold 48%.
- Acceptance: n=428 → n=600 within 4 weeks, PF≥1.5 maintained.

### 🟢 P1-C · ETF push to n≥100 + PF≥1.5
- Trust −20%, Score −15%, Smart Picks→70, min-hold ≥4h.
- Add SPY/QQQ/IWM/XLF/GLD/TLT to `multi_asset_copytrader` eligibility.

### 🟢 P1-D · COMMODITY WR lift
- Thin-coverage compensation (WR +5%, Score +10%); CTA 3-win activation + first-trade SL halved.
- **Blocker:** `multi_asset_cot` PF=12.16/19.19 contradiction (PR #913 forensic shipped; await output). Don't lean on this strategy until DB-verified.

### 🟢 P1-E · Macro regime awareness *(hedge-fund swarm theme #3)*
- FRED + COT + VIX feeders all exist; **never connected**. Add a single `macro_regime.py` that emits {bull/bear/risk-off/risk-on, vol_regime, credit_spread_regime} consumed by quality_gates and sizing.
- This is the precondition for #P1-F.

### 🟢 P1-F · Asymmetric risk allocation *(hedge-fund swarm theme #4)*
- Per-class sizing weights: COMMODITY 3–4× ETF baseline; FOREX 0; CRYPTO conditional on backtest-vs-live regime check.
- Note: CRYPTO backtest-vs-live gap is **−31.12pp** (2× the alert threshold). **Stop sizing CRYPTO on backtest validation alone.**

### 🟢 P1-G · SHORT+COMMODITY filter expansion *(hidden-insights finding)*
- SHORT+COMMODITY = 67.2% WR on n=122 — the single best filter in the system. Currently used implicitly via `cot_positioning`; promote to explicit booster in `score_booster.py`.

---

## P2 — Follow-up structural

### 🟢 P2-A · Factor-level thinking *(hedge-fund swarm theme #5)*
- 248 strategies × 14 families = ready-made factor model. Wire `factor_decomp.py` (if exists) or scaffold; produce daily factor-exposure report to `/audit/factors/`.

### 🟢 P2-B · `performance_alerts` → auto-shadow-probation wire-up
- Existing infrastructure; pure wire-up. Targets `forex_rsi2_mean_reversion`, `myfxbook_retail_contrarian`.

### 🟢 P2-C · Walk-forward for BOND + ETF
- Per audit P5 verdicts: BOND NO_EDGE unanimous, ETF MIXED (only class with surfaced signal).

### 🟢 P2-D · MAJOR GOAL banner update
- `audit_dashboard/template.html:808-820` — reframe with FOREX-as-real-emergency (now blocked at sizing) + COMMODITY-as-money-ready-candidate.

### 🟢 P2-E · Single-pick launch — **`cot_positioning` on CT=F**
- **Correction over my initial plan:** the peer was right. `cot_positioning` strategy on CT=F has DSR=1.0, n=100, 90% WR, already in paper pilot. The CT=F blacklist (PR #535) applies to the *generic* COMMODITY pipeline, not this strategy-symbol pair.
- HG=F (copper, PF 2.17) is the no-pilot backtest fallback.
- **Action:** monitor 4-week paper pilot to graduation gate.

---

## ✅ Already shipped this session window (verification only)

| Ref | What | Where |
|---|---|---|
| PR #535 | COMMODITY sub-class kill (cotton/coffee/silver/gold/crude) | Merged 2026-04-30 |
| PR #545 | Bond credit-spread + PEAD + TF classifier | Merged 2026-04-30 |
| PR #876 | FOREX pnl_pct unit-corruption clamp | Merged 2026-05-11 |
| PR #904 | Research orchestrator + edge-stability sidecar | Merged 2026-05-12 |
| PR #906 | quan_engine CRYPTO volume cap 12% | Merged 2026-05-12 |
| PR #907 | kimi_signal_tracking blacklist test | Merged 2026-05-12 |
| PR #908 | crypto_soc_* baby_strats quarantine | Merged 2026-05-12 |
| PR #909 | FOREX hard-cap sizing=0 (P0-A) | Merged 2026-05-12 |
| PR #910 | claude_gainer_st blacklist reconcile | Merged 2026-05-12 |
| PR #913 | multi_asset_cot DB verifier | Merged 2026-05-12 |
| PR #914 | MDD capped-vs-raw audit | Merged 2026-05-12 |
| `6a2c6b2a30` | money-ready validation plan | This session |
| `5e37cd3999` | FOREX deep-dive per mutate-before-kill protocol | This session |
| `348a3078c7` | BOND root cause (three-layer blocker) | This session |
| Cloud agent | 2 CI test fixes, swarm-sync workflow fix, hedge-fund swarm report, hidden-insights audit report, plan §8 addendum, confidence-inversion gate | Working tree (uncommitted) |

---

## 🚦 Coordination state

- **Cloud agent owns:** quality_gates.py confidence-inversion gate, plan §8 addendum (contains the falsified FRED claim — needs correction commit after cloud agent finishes), 6 other dirty files.
- **Opus owns:** the three reports above plus this merged action list.
- **Net-new ordered queue ready to claim:** P0-B (highest leverage — unblocks an entire class), P0-E (free edge — 41 dormant strategies), P0-F (highest-PnL-lift per hedge-fund swarm, but bootstrap-validate Grok's numbers first), P1-A through P2-E.

The §8 addendum's "BOND FRED API timeout" claim is **wrong** and needs a follow-up correction commit after the cloud agent's working tree is clean. See [reports/bond_root_cause_2026-05-12.md](reports/bond_root_cause_2026-05-12.md) §3 for the falsification.
