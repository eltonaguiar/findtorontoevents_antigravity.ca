# Quant Strategy Root-Cause Review

**Date:** 2026-06-02  
**Reviewer lens:** Institutional PM / quant research  
**Canonical live evidence:** `audit_dashboard/data/money_ready_verdict.json`, `audit_dashboard/data/pf_registry.json` (generated 2026-06-02T06:21Z)  
**Lab evidence:** `verified_strategies/`, `reports/multi_class_strategy_lab_2026-06-02.md`, `reports/backtesting_methodology_audit_2026-06-02.md`

---

## Executive answer (TL;DR)

| Question | Answer |
|----------|--------|
| **Do we just need more time?** | **Partly for forward pilots only** — ETF/crypto verified sleeves need n≥100 *forward* closes. **No** for production picks: CRYPTO/EQUITY/FOREX already have n=32–377 resolved and **still lose money** after policy-clean filters. Time alone will not fix negative expectancy. |
| **Do our strategies suck?** | **Production pipeline: mostly yes** (PF<1, WR<40% on main classes). **Lab OHLCV sleeves: mixed** — a few real edges exist (ETF dual momentum, VWAP crypto WF) but fail live translation or risk gates. |
| **What are we doing wrong?** | (1) Validating on different engines than we trade, (2) promoting from inflated pre-policy metrics, (3) breadth over depth (88 strategies, 78 silent), (4) broken/incorrect live mechanics (resolver, leakage, TIME_EXIT zombies), (5) no single admissibility gate before capital. |
| **DNA mutate / invert?** | **Mutate before kill** on *specific* sleeves with lab edge + live failure (Faber TAA, carry, sector mom) — not blanket mutation. **Invert** only where signed edge is stable (rare; e.g. some mean-reversion failures are sizing not direction). **Do not invert** dead strategies (Connors crypto) — they're loss-skew, not wrong sign. |
| **Dead due to data feeds?** | **Secondary, not primary.** FRED timeouts (gx10) affect carry *backtests*; fixed via curl cache. Live CRYPTO pain is **pick quality + dedup/policy**, not Binance outage. Portfolio page emptiness was **URL corruption**, not missing data (see §7). |

**Bottom line:** You don't have a "wait 90 days" problem on the main book. You have a **research–production gap**: backtests show plausible edges; live closed picks after flicker-dedup and policy-clean are **sub break-even on every major asset class**.

---

## 1. Live performance truth (policy-clean net)

Source: `pf_registry.by_asset_class_policy_clean_net` + `money_ready_verdict.json`

| Asset class | n (resolved) | WR | PF | MDD | Verdict |
|-------------|--------------|-----|-----|-----|---------|
| **CRYPTO** | 377 | 35.5% | **0.89** | 100% | NOT_READY — negative expectancy |
| **EQUITY** | 52 | 26.9% | **0.33** | 62% | NOT_READY |
| **FOREX** | 32 | 28.1% | **0.48** | 82% | INSUFFICIENT_DATA (but already bad) |
| **FUTURES** | 13 | 15.4% | **0.52** | 17% | INSUFFICIENT_DATA |
| **COMMODITY** | 4 | 50.0% | 1.68 | 2.5% | INSUFFICIENT_DATA (n=4) |
| **ETF** | 3 | 66.7% | 1.46 | 2.0% | INSUFFICIENT_DATA (n=3) |
| **BOND** | 0 | — | — | — | No policy-clean rows |

**Tier-2 institutional bar:** PF>1.5, WR>50%, n≥100, MDD<20%, DSR/PBO where applicable.  
**Money-ready classes:** **0/9**.

### The "two books" problem

| View | CRYPTO PF | Why it misleads |
|------|-----------|-----------------|
| Raw registry | 1.46 (n=1580) | Duplicate emissions, pre-policy, mercury2 leakage |
| Policy-clean net | **0.89** (n=377) | What you should size on |

**Never size from raw `by_asset_class_raw`.** The dashboard 78.9% CRYPTO Smart-Picks dispute (duplicate groups, mislabels) is the same failure mode.

---

## 2. Lab vs live — why backtests look better

### Lab Tier-2 pass (real OHLCV, June 2026 run)

Only **1/6** classes pass lab gates: **ETF Dual Momentum** — PF 1.60, WR 53.8%, n=104.

Walk-forward **PASS** (costed) on crypto lab sleeves:

| Sleeve | OOS PF | OOS Sharpe | Live production? |
|--------|--------|------------|------------------|
| VWAPReversion | 1.32 | 3.10 | Opt-in only; not in main scanner |
| BollingerMR | 1.67 | 1.38 | Opt-in only |
| DualMomentum crypto | 1.13 | 0.54 | Opt-in only |

**Confirmed dead in lab:** ConnorsRSI2 crypto (PF 0.90, equity → 20% despite 61% WR).

### Root cause: engine bifurcation

From `reports/backtesting_methodology_audit_2026-06-02.md`:

| Engine | Asset classes | Walk-forward | DSR/PBO | Costs |
|--------|---------------|--------------|---------|-------|
| `walk_forward_backtester.py` | CRYPTO | Partial | Yes | Partial |
| `real_data_backtest.py` | EQUITY, FOREX, COMMODITY, ETF, BOND | **No** | **No** | **No** |
| `rigorous_backtest_harness.py` | Ad hoc | Purged WF | Yes | Yes |
| `verified_strategies/*` | Per-sleeve | 70/30 OOS | MC only | 10bps crypto |

**80% of academic strategies use the weakest engine.** Promotion decisions and "Tier B" labels on lab sleeves do not automatically apply to the 200+ production `source_system` strategies feeding `at_raw_picks`.

---

## 3. Proper backtesting methodology (target standard)

Single **admissibility pipeline** — no strategy reaches paper capital without passing all stages:

### Stage 0 — Pre-registration (M-107)

- Register hypothesis in `reports/hypothesis_registry.json` **before** any OHLCV run.
- Kill examples: H-001 COT (leakage), H-003 ETF momentum (sign instability at n=30k).

### Stage 1 — Signal generation (real data only)

- OHLCV: documented chain (yfinance / Binance mirrors / FRED+curl cache).
- **Forbidden:** synthetic random walk, config-only carry rates without cache flag, closed-pick replay as "backtest."

### Stage 2 — Purged walk-forward (minimum)

- Chronological k-fold with **purge + embargo** (López de Prado) — already in `rigorous_backtest_harness.py`; must be **the only** promotion engine.
- Report: IS/OOS Sharpe, PF, WR, n, max DD **after costs**.
- Asset-class costs: CRYPTO 10bps+5bps slippage RT; EQUITY/ETF 4bps; FOREX 2–5bps.

### Stage 3 — Multiple-testing correction

- **DSR** > 0.95 (conservative N = all variants ever tried, not just winner).
- **PBO** < 0.05 on actual strategy matrix, not sign-flip synthetics.
- **SPA/Reality Check** when ≥2 strategies compete per class.

### Stage 4 — Robustness (block bootstrap)

- Replace i.i.d. trade shuffle with **stationary block bootstrap** (autocorrelation in crypto regimes).
- Regime splits: trend × vol (min 30 trades per cell or fail).

### Stage 5 — Forward paper (mandatory)

- Virtual book with TP/SL/max-hold (`pilot_virtual_book.py` pattern).
- Promotion only if: forward n≥100 **and** forward PF≥1.5 **and** WR≥50% **and** forward PF ≥ 0.85 × lab OOS PF.

### Stage 6 — Live shadow → sized capital

- Opt-in scanner flag → 30d shadow → 0.1% sizing → scale on MDD cap.

**Current gap:** Stages 2–4 are **optional and fragmented**. Stage 5 just started (ETF DM, crypto WF, Faber pilots). Production scanner still emits from hundreds of un gated sources.

---

## 4. Root causes by bucket (ranked)

### A. Structural — research ≠ production (P0)

- Lab winners (`verified_strategies`, `baby_strategies`) are **opt-in sidecars**; bulk of picks come from `production_scanner.py` + tournament + copy-trader + mercury2.
- **88 strategies in funnel; 78 silent** — breadth without forward validation.
- Orphan integrations (~20/21 hedge-fund libs had no production caller historically).

### B. Statistical — negative expectancy after clean data (P0)

- CRYPTO WR 35.5% with loss-skew (Connors pattern class-wide).
- EQUITY dominated by `regime_terminal` (40% concentration) — PF 0.33.
- FOREX `multi_asset_scanner` — PF 0.48.

**Not fixable by waiting** on these streams without changing *what* emits picks.

### C. Methodology — overfitting & leakage (P1)

- No purge/embargo in main WF backtester → OOS inflated 15–30%.
- i.i.d. Monte Carlo on correlated trades → false significance.
- COT/commercial timing leakage (98% confirmed) poisoned COMMODITY history.
- `futures_connors_rsi2`: 372/373 TIME_EXIT @ pnl=0 — resolver zombie, not strategy alpha.

### D. Operational — resolver & labels (P1)

- Tournament resolver backlog (1289 overdue picks) blocked n≥100 for models.
- EXPIRED→WON mislabels, duplicate signal-ts groups (1864 in CRYPTO 90d dispute).
- Pre-fix vs post-fix resolver splits — always use `asset_class_health` not raw DB.

### E. Data feeds — real but second-order (P2)

- FRED urllib timeout on gx10 → carry backtest fallback; **fixed** via `tools/fetch_fred_carry_cache.py` + curl fallback in `data_fetcher.py`.
- Crypto OHLCV: Binance pagination works (2500 bars); not the binding constraint.
- **Price feed for PF portfolios:** export marks open positions; if `get_close` fails, UI shows entry-only (not empty book).

---

## 5. Strategy quality by class — honest assessment

| Class | Production book | Lab best sleeve | Diagnosis |
|-------|-----------------|-----------------|-----------|
| **CRYPTO** | **Fail** PF 0.89 | VWAP WF OOS Sharpe 3.1 | Production = noise + mean-reversion on wrong regime; lab edge exists but **not wired** as primary. Connors-style loss-skew kills book. |
| **EQUITY** | **Fail** PF 0.33 | 12-1 mom PF 2.31 (MDD fail) | `regime_terminal` and friends emit without class-level edge. Faber TAA lab OK; forward pilot just started. |
| **FOREX** | **Fail** PF 0.48 | Carry PF 2.27 (n=13 lab) | Too few live resolves; carry needs multi-pair + FRED — pilot exists, not in main funnel. |
| **ETF** | **Insufficient** n=3 live | Dual momentum **Tier-2 pass** n=104 | **Best candidate** — wire after forward n≥100, not before. |
| **COMMODITY** | **Insufficient** n=4 | TSMOM PF 1.08 | Cross-mom tuned to Sharpe 0.88; COT strategies looked great pre-leakage, dead post-fix. |
| **BOND** | **No clean data** | Credit Faber PF 3.4 (n=11) | Sample too small; HYG/LQD momentum promising (Sharpe 1.84) — forward n needed. |

**Do strategies "suck"?**  
- **Bulk production emitters:** yes for capital allocation purposes.  
- **Small verified sleeve:** no — but they're **≤5% of pick volume** and gated OFF by default.

---

## 6. DNA mutate / invert / kill — decision rules

| Action | When | Example |
|--------|------|---------|
| **Kill** | Post-fix PF<0.8, n≥100, no lab rescue | ConnorsRSI2 crypto, seasonal_factor_rotation CRYPTO |
| **Mutate (3-axis)** | Lab PF>1.5 but live PF<1; n≥30 | Faber: SPY→QQQ, add 10bps; commodity: drop ZC=F, vol-scale |
| **Invert** | Only if OOS PF(inverted) > 1.3 and original PF<0.7 with symmetric costs | Rare; test per-strategy, never class-wide |
| **Wire lab→prod** | WF PASS + forward promotion_ready | VWAP/Bollinger crypto, ETF dual momentum |
| **Do nothing (wait)** | Forward pilot n<100, lab PASS | Current ETF DM, crypto WF, Faber pilots |

Reference: `docs/MUTATION_THREE_AXIS_PROTOCOL.md`, `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`.

---

## 7. Portfolio empty? — full audit of all 81 books (2026-06-02)

**The books are not empty on the server.** Live roster: `pf_portfolios.json` → **81 portfolios** (27 models × 3 appetites), generated 2026-06-02T06:27Z.

| Bucket | Count | Meaning |
|--------|-------|---------|
| **Has open positions** | **66** | Daily PF engine ingested tournament picks; normal state |
| **Zero positions ever** | **15** | Model seeded but no eligible picks ingested yet |
| **Missing JSON (404)** | **0** | All keys have `pf_portfolio_<key>.json` on live |

### Top open books (examples)

| portfolio_key | Open | Model |
|---------------|------|-------|
| groq_llama_3_70b__aggressive | 21 | groq_llama_3_70b |
| cerebras_llama4__aggressive | 20 | cerebras_llama4 |
| grok3__aggressive | 16 | grok3 |
| **deepseek_v4__aggressive** | **11** | deepseek_v4 |
| deepseek_v4__balanced | 12 | deepseek_v4 |

**deepseek_v4__aggressive** live symbols (2026-06-02): GC=F, ES=F, MVST, SI=F, JPM, HD, VZ, MA, ADAUSDT, LINKUSDT, ETHUSDT.

### The 15 genuinely empty portfolios

These exist in the roster but have **zero rows** in `PF_POSITION` — not a UI bug:

- `aimlapi_gpt4o__*` (3), `gh_models_gpt4o__*` (3)
- `command_a__*` (3), `groq_kimi_k2__*` (3)
- `nous_hermes_4__aggressive`, `nous_hermes_4__balanced`
- `deepseek_r1__conservative`

**Why:** `run_daily.py` seeds portfolios for leaderboard models with `pf_ci_lo > 1.0`, but ingestion only adds picks **that model actually emitted** in tournament. Models with high CI on small n (e.g. fireworks_qwen n=9) or no recent tournament emissions stay at $100k with zero positions.

### Why pf.html *looked* empty (UI bug)

1. **Invisible Unicode in pasted URL** — trailing char (e.g. U+E006) → `safeKey()` → `deepseek_v4__aggressive_` → wrong JSON → 404 → *"Pending first daily run"*.
2. **Fix applied locally:** `audit_dashboard/pf.html` strips invisible Unicode from `?key=` before fetch.

**Clean URL:** https://findtorontoevents.ca/audit/pf.html?key=deepseek_v4__aggressive

### portfolio_mix__* (separate from model books)

Shadow mix portfolios (`portfolio_mix__aggressive_top5`, etc.) aggregate tournament history — **866 closed rows, 0 open** on live. They are **not** the same as per-model PF books. Link from tournament "mix" variants if you want historical shadow NAV, not live open exposure.

---

## 8. Where is the edge? — three audit surfaces compared

**Trust hierarchy (canonical):**

```
policy_clean money_ready_verdict  ← size capital here ONLY
        ↑
verified_strategies lab + WF      ← promotion candidates (forward n≥100)
        ↑
paper_pilot virtual forward       ← accumulating now
        ↑
ai-tournament / pf.html           ← separate universe — NOT money-ready
        ↑
pick_funnel cells / nav matrix    ← discovery — many DISPUTED
```

### Surface A — `/audit/` (main dashboard + money_ready_verdict)

| Class | Policy-clean n | PF | Money-ready? |
|-------|----------------|-----|--------------|
| CRYPTO | 377 | **0.89** | NO |
| EQUITY | 52 | **0.33** | NO |
| FOREX | 32 | **0.48** | NO |
| ETF | 3 | 1.46 | INSUFF-N |
| COMMODITY | 4 | 1.68 | INSUFF-N |

**Verdict:** **No deployable edge** on the main book. This is the only surface that should drive real-money sizing.

### Surface B — `/audit/ai-tournament.html` + `pf.html`

Tournament leaderboard (2026-06-01): models ranked by **Wilson LB on PF** (CI-adjusted), separate pick universe from Smart Picks.

| Model | pf_ci_lo | PF | n resolved | Notes |
|-------|----------|-----|------------|-------|
| fireworks_qwen | 5.59 | 24.3 | **9** | tiny n — do not trust |
| gpt4o_mini | 2.82 | 10.5 | **10** | tiny n |
| **deepseek_v4** | **2.52** | **3.46** | **208** | **Best credible tournament edge** |
| gpt4o | 2.13 | 3.14 | 134 | solid n |
| grok3 | 1.74 | 2.29 | 303 | solid n |
| cursor_agent | 1.20 | 1.88 | 101 | at threshold |

**Verdict:** **Edge lives here for paper/tournament** — deepseek_v4, gpt4o, grok3 with n≥100 and pf_ci_lo>1.5. This is **NOT** the same cohort as production CRYPTO (PF 0.89). Tournament picks ≠ Smart Picks pipeline. PF portfolios paper-trade tournament emissions; 66/81 books have open positions.

### Surface C — `/audit/pick_funnel.html` (cell discovery)

**Nav surface matrix (`nav_surface_edge_matrix.json`):** **8/8 surfaces = `no-edge`** at surface level (Verified Alpha, Smart Picks, Money Ready, HC, ELITE, etc.).

Notable **cell-level** signals (still fail generalization gates):

| Surface | Class | n | PF | holdout PF | Why not edge |
|---------|-------|---|-----|------------|--------------|
| Smart Picks | CRYPTO | 126 | 2.90 | 7.70 | **67% mega_mutation concentration** |
| Smart Picks | ETF | 22 | 4.30 | 1.80 | **100% kimi_riseoftheclaw**, small n |
| Smart Picks | EQUITY | 15 | 2.66 | 1.35 | **93% kimi_riseoftheclaw**, small n |

**One PROVEN cell** in `top_edges_per_class.json` (90d, Bonferroni + holdout):

- **CRYPTO** `trust=UNK & rr=RR1.0-1.5 & dir=LONG` — n=327, PF=3.89, holdout PF=3.07 ✅

**But** class-level policy-clean rollup is still PF 0.89 — the proven cell is a **subset**; the rest of the book destroys expectancy. Classic "edge in a filter cell, loss in aggregate."

**14d recency (`pick_summary_stats_2w.json`)** — raw DB, not policy-clean:

| Class | 14d WR | 14d PF | Caveat |
|-------|--------|--------|--------|
| CRYPTO | 38.4% | **0.67** | incubator_gainer 66% concentration |
| FOREX | 83.5% WR | **0.10 PF** | EXPIRED mislabel 76% — **high WR, catastrophic PF** |
| EQUITY | 65.5% | 5.32 | smart_money 60% concentration — verify resolver |

**Verdict:** pick_funnel is for **discovery and dispute flagging**, not capital allocation. The DISPUTED CRYPTO Smart Picks banner (78.9% WR cohort) remains valid — do not size from nav matrix green cells without policy-clean confirmation.

### Surface D — verified_strategies lab (not on dashboard yet)

| Sleeve | Lab | Forward n | Promotion |
|--------|-----|-----------|-----------|
| ETF Dual Momentum | **Tier-2 PASS** | 0 | Wait n≥100 |
| Crypto VWAP WF | OOS Sharpe 3.1 | 0 | Wait n≥100 |
| Crypto Bollinger WF | OOS PF 1.67 | 0 | Wait n≥100 |
| Faber TAA QQQ | Tier B | pilot open | Wait n≥100 |

**Verdict:** **Best future edge** — not yet on `/audit` main funnel; gated off in scanner.

---

## 9. Root causes by asset class (quant sign-off)

### Immediate (this week)

1. **Single admissibility gate** — merge `rigorous_backtest_harness.py` + `walkforward_suite.py` into one CLI; no new scanner wiring without WF PASS artifact path.
2. **Depromote negative-expectancy sources** — block or cap `regime_terminal`, unverified mercury2 paths, Connors crypto from active until forward proof.
3. **Deploy pf.html key sanitization** — FTP `audit_dashboard/pf.html`.
4. **Run daily** `tools/run_verified_pilots_daily.py` — accumulate forward n on ETF DM + crypto WF + Faber.

### 30-day

5. **Unify backtest engine** — port `real_data_backtest.py` strategies to purged WF + costs (methodology audit Flaw 4).
6. **ETF dual momentum** — if forward n≥100 and PF≥1.5, set `ETF_VERIFIED_DUAL_MOMENTUM_ENABLED=1`.
7. **Crypto VWAP/Bollinger** — same gate for `CRYPTO_VERIFIED_VWAP_ENABLED`.

### 90-day

8. **Strategy census** — kill or quarantine silent 78; max 3 promoted sleeves per asset class.
9. **Block bootstrap** replace i.i.d. MC in `strategy_verification_engine.py`.
10. **Class-level capital** — zero default sizing on CRYPTO/EQUITY/FOREX until money_ready_verdict flips.

| **BOND** | No clean data | Credit Faber PF 3.4 (n=11) | Sample too small; forward pilot needed |

---

## 10. Prioritized action plan (quant sign-off)

```bash
# Live verdict (authoritative)
python3 alpha_engine/money_ready_verdict.py --json
python3 tools/build_pf_registry.py

# Lab walk-forward
VERIFY_SKIP_FRED=1 python3 verified_strategies/walkforward_suite.py --only hyro

# Forward pilots + dashboard
python3 tools/run_verified_pilots_daily.py
python3 tools/pilot_forward_dashboard.py

# Portfolio JSON (live)
# All portfolios open-position audit
curl -sA 'Mozilla/5.0' 'https://findtorontoevents.ca/audit/data/pf_portfolios.json' | python3 -c "
import json,sys,urllib.request,re,subprocess
roster=json.load(sys.stdin)
items=roster.get('portfolios',[])
base='https://findtorontoevents.ca/audit/data/pf_portfolio_'
def safe(k): return re.sub(r'[^A-Za-z0-9_.-]','_',k)
for p in items:
    k=p['portfolio_key']
    d=json.loads(subprocess.check_output(['curl','-sA','Mozilla/5.0',base+safe(k)+'.json']))
    op=sum(1 for x in d.get('positions',[]) if str(x.get('status','')).lower()=='open')
    print(k, 'open=', op)
"
```

---

**Verdict:** Waiting alone is insufficient. **Edge location is split across three universes** — tournament (deepseek_v4 paper), pick_funnel cells (CRYPTO RR filter), lab sleeves (ETF DM) — none of which yet clears **policy-clean money-ready** on `/audit/`. Capital should flow only through the admissibility pipeline — starting with ETF dual momentum and crypto VWAP/Bollinger once forward books hit n≥100.

10. **Wire tournament→production bridge** — only after policy-clean forward proof; tournament edge (deepseek_v4) must not be confused with Smart Picks edge.

---

## 11. Reproducer commands
