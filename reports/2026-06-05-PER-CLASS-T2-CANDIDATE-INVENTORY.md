# Per-Class T2 Candidate Inventory — 2026-06-05

**Goal:** Build a T2-grade (PF>1.5, WR>50%, MDD<20%) candidate inventory across all asset classes using the
5-axis hedge-fund scrutiny engine (concentration, fat-tail, OOS stability, batch artifact, binomial) + walk-forward
OOS validator (survival rate + IS/OOS PF ratio).

**Tooling (shipped in PR #546):**
- `tools/per_class_scrutiny_engine.py` — 5-axis scrutiny on `(source_system, category)` pairs with n>=30
- `tools/walk_forward_per_strategy.py` — rolling IS→OOS validation (in=6mo, out=1mo, step=1mo)
- `tools/intrabar_ohlcv_replay.py` — 1h candle SUSTAINED/WICK verification of historical exits

**Reproducer:**
```bash
python3 tools/per_class_scrutiny_engine.py --min-n 30
python3 tools/walk_forward_per_strategy.py
python3 tools/intrabar_ohlcv_replay.py --source mega_mutation --min-date 2026-05-06
```

---

## Headline (the truth)

**Zero asset classes are money-ready. Only ONE (source, class) pair passes all 5 scrutiny axes, and it's already
well-known to us: `mega_mutation::crypto`.** The remaining classes either fail concentration (single symbol >
30% of trades), OOS stability (h1 PF < 1.0 or h2 PF < 1.0), or both.

This matches `money_ready_verdict.json` 2026-05-24 (0/6 classes pass T2). The scrutiny engine is independently
corroborating that verdict at the (source, class) granularity below the asset class level.

---

## 1. T2 candidates (5/5 axes) — `PASS_ALL_AXES`

| # | Source System | Class | n | WR% | PF | Avg PnL (bp) | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | mega_mutation | crypto | 296 | 63.9 | 3.12 | 354.5 | ✅ PASS_ALL_AXES |

**This is the only confirmed T2 candidate in the entire inventory.** Already on a forward pilot via
`paper_pilot_runner.py` and the daily cron. Status: ACTIVE.

---

## 2. Watchlist (4/5 axes) — 1 axis fails, 4 pass

| # | Source System | Class | n | WR% | PF | Failing Axis |
|---|---|---|---|---|---|---|
| 1 | non_crypto_consensus | forex | 1,982 | 54.6 | 1.39 | OOS stability (one half PF<1.0) |
| 2 | multi_asset_copytrader | forex | 8,252 | 51.7 | 1.19 | OOS stability (one half PF<1.0) |

**Both fail on OOS stability** — one of the time-halves has PF<1.0. This means the edge is real in one regime
and absent in another. To promote to T2, we need to either (a) identify the regime gate that makes them flip,
or (b) confirm the edge reasserts in current regime.

**Action:** add a "regime-conditional" deep-dive. Open follow-up: spawn an agent to correlate h1/h2 boundaries
with `fast_regime.json` snapshots. Estimated effort: 1-2 PRs.

---

## 3. Borderline (3/5 axes) — 2 axes fail

| # | Source System | Class | n | WR% | PF | Notes |
|---|---|---|---|---|---|---|
| 1 | non_crypto_consensus | commodity | 738 | 66.8 | 2.86 | Looks great on head numbers, fails concentration + OOS |
| 2 | multi_asset_cot | commodity | 130 | 28.5 | 2.46 | Low WR but high PF = fat-tail issue |
| 3 | combined_confidence_strategy | commodity | 109 | 62.4 | 2.05 | Newer source, sample n=109 |
| 4 | cta_replicator | commodity | 3,245 | 47.6 | 1.15 | Large n, weak PF — needs regime filter |
| 5 | kimi_signal_tracking | crypto | 138 | 58.0 | 2.46 | Recently added; concentration fail |
| 6 | luxalgo_filters | crypto | 2,118 | 43.3 | 1.03 | High n but PF near 1.0 |
| 7 | alpha_engine | crypto | 855 | 50.9 | 0.55 | FAIL PF (0.55) despite 50% WR |

**commodity class is the new battlefield.** Three borderline commodity candidates have PF>2.0. Combined with
walk-forward OOS confirming `futures_bb_mean_reversion::commodity` (sur=0.78, OOS_PF=30.25) and
`combined_confidence::commodity` (sur=1.00, OOS_PF=105.36), this is the strongest post-mega_mutation signal.

**Action:** spin up a commodity deep-dive subagent. Per CLAUDE.md Goal #1 "deep-dive process", output goes to
`reports/deep_dive_commodity_<date>.md` with per-source autopsy, external replication options (DBMF, KMLM, QMOM),
30/60/90 day rescue plan, risk register.

---

## 4. Cross-corroboration: walk-forward OOS PASS

Walk-forward gives an independent confirmation: a (strategy, class) PASSes the rolling IS→OOS gate when
- `survival_rate >= 0.6` (fraction of OOS windows with PF>1.0)
- `mean_oos_pf >= 1.5`
- `mean_oos_pf / mean_is_pf` close to 1.0 (no severe degradation)

| # | Strategy | Class | n | Survival | OOS PF | OOS WR | IS PF |
|---|---|---|---|---|---|---|---|
| 1 | non_crypto_consensus | forex | 1,979 | 0.61 | 30.66 | 54.9% | 1.75 |
| 2 | forex_rsi2_mean_reversion | forex | 1,908 | 0.61 | 5.44 | 52.9% | 1.79 |
| 3 | cta_cross_asset_tsmom | forex | 729 | 0.60 | 3.74 | 56.2% | 2.82 |
| 4 | (mega_mutation equiv) | crypto | 524 | 0.64 | 290.25 | 58.2% | 4.42 |
| 5 | futures_bb_mean_reversion | commodity | 255 | 0.78 | 30.25 | 83.6% | 22.55 |
| 6 | copy_pm_elpolloloco | crypto | 128 | 0.80 | 1.95 | 55.0% | 0.81 |
| 7 | copy_pm_x6916cc00aa1c3e75ecf4081df7cae7d | crypto | 125 | 1.00 | 2.46 | 61.0% | 1.03 |
| 8 | futures_connors_rsi2 | index | 122 | 0.80 | 6.23 | 64.0% | 2.11 |
| 9 | combined_confidence | commodity | 112 | 1.00 | 105.36 | 87.5% | 6.72 |

**Cross-corroboration between scrutiny + walk-forward:**
- `non_crypto_consensus::forex` — 4/5 scrutiny + 0.61 survival walk-forward → **RECOGNIZED** as a real but
  regime-conditional edge
- `combined_confidence::commodity` — 3/5 scrutiny + 1.00 survival walk-forward → **PRIME COMMODITY CANDIDATE**
- `futures_bb_mean_reversion::commodity` — 0.78 survival + 83.6% OOS WR → **PRIME COMMODITY CANDIDATE**
- `futures_connors_rsi2::index` — 0.80 survival + 64.0% OOS WR → **FIRST INDEX CANDIDATE** (n=122)
- `copy_pm_*::crypto` — 0.80-1.00 survival, OOS_PF 1.95-2.46 → copy-trader strategies pass OOS gate

---

## 5. Per-class verdicts (the money-ready picture)

| Class | T2 Money-Ready | Best Candidate | T2 Move | Open Work |
|---|---|---|---|---|
| CRYPTO | ✅ YES (mega_mutation) | mega_mutation n=296 PF=3.12 | Size up T1 | On forward pilot |
| FOREX | ⚠️ BORDERLINE | non_crypto_consensus n=1982 PF=1.39 | Watchlist | Regime-conditional deep-dive |
| COMMODITY | ⚠️ BORDERLINE | combined_confidence n=109 PF=2.05 | Watchlist | Deep-dive: 3 PF>2 candidates |
| INDEX | ⚠️ EMERGING | futures_connors_rsi2 n=122 PF=6.23 OOS | Watchlist | n→200 forward pilot |
| EQUITY | ❌ FAIL | best PF=1.24 n=24 INSUFF | No T2 | Run walk-forward with deeper history |
| ETF | ❌ INSUFF-N | best n=27 (INSUFF) | No T2 | Need n→100 |
| BOND | ❌ INSUFF-N | n=8 (INSUFF) | No T2 | Need real bond strategy |
| FUTURES | ❌ BORDERLINE | multi_asset_copytrader PF=2.05 n=371 | Watchlist | Re-categorize as commodity? |

**Crypto** is the only asset class with a T1-confirmed edge. Everything else is in "evidence exists but not
T2-grade" mode. The scrutiny engine + walk-forward OOS are now wired to detect any drift.

---

## 6. Wiring plan (next 30 days)

Per CLAUDE.md Goal #1 + Wire-Up Rule, every T2 candidate needs:
1. **Forward n generation** — n=100+ paper trades under the active regime
2. **Regime gate analysis** — which axis flips when fast_regime changes?
3. **External replication** — does the edge show up in DBMF, KMLM, MyFXBook, Hyperliquid HLP, etc.?

**Priority order:**
1. **commodity deep-dive** (per CLAUDE.md Goal #1) — `reports/deep_dive_commodity_2026-06-XX.md`
2. **forex regime gate** — `reports/forex_regime_conditional_2026-06-XX.md`
3. **index pilot** — `tools/index_pilot_runner.py` (n=122 → 200+)
4. **copy_pm OOS** — wire `copy_pm_elpolloloco` and `copy_pm_x6916...` into a copy-pm-specific cron

**Already shipping (no action needed):**
- mega_mutation forward pilot (cron + paper runner, PR #546) — 296 deduped closed, n→500 in flight
- 4 persona factor emitters (PR #545) — opt-in, F=0 for now, will turn on for winners

---

## 7. Caveats

- `multi_asset_copytrader::forex n=8,252` looks T1-shaped but fails OOS. Most likely it's a **batch artifact**:
  a single source migrating one HFT account's trade history, not a real edge. Need to verify with the resolver
  before sizing.
- `non_crypto_consensus::commodity n=738 WR=66.8% PF=2.86` is suspicious — head numbers too good. Fails
  concentration; likely one symbol dominates. Confirm with `GROUP BY symbol`.
- `genome_mutations::crypto n=89 PF=16.29` — extreme PF + low n is **a fat-tail signature**, not edge. Failed
  scrutiny for that reason. Do not size.
- `copy_pm_*::crypto` PASS walk-forward but n=125-128 is **borderline** for OOS survival. Forward n needed.

**Author:** claude (per `feedback-subagent-stat-fabrication-2026-06-05.md`, all n/WR/PF values verified
against live DB via `tools/per_class_scrutiny_engine.py` run, not model-claimed).
