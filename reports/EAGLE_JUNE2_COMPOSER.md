# EAGLE June 2 Quant Review — Composer

**Author:** Composer (Cursor Agent)  
**Date:** 2026-06-02  
**Goal #1:** Phenomenal `/audit` performance — institutional-grade edge per asset class  
**Live evidence:** `curl` → findtorontoevents.ca/audit/data/* (2026-06-02T06:56Z)  
**Machine report:** `audit_dashboard/data/strategy_admissibility.json`  
**Methodology:** `docs/BACKTEST_ADMISSIBILITY_STANDARD.md`  
**NFA — research memo, not a sizing recommendation.**

---

## Executive summary

| Question | Answer |
|----------|--------|
| **More time?** | **Yes only for forward pilots** (ETF dual momentum, crypto VWAP/Bollinger, Faber — forward n=0, gate n≥100). **No** for bulk production: CRYPTO n=374 PF **0.89**, EQUITY n=52 PF **0.33**, FOREX n=32 PF **0.48** — already negative expectancy. |
| **Strategies suck?** | **Bulk production emitters: yes** for capital allocation. **Lab/tournament sleeves: mixed** — real edges exist but are opt-in or separate universe. |
| **Doing wrong?** | Engine bifurcation (25/31 academic on weak `real_data_backtest.py`), sizing on raw vs policy-clean, breadth over depth, tournament ≠ Smart Picks conflation. |
| **DNA mutate?** | **Surgical** per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` — Faber (QQQ/costs), commodity (drop ZC=F, vol-scale). Not blanket. |
| **Invert?** | **Per-strategy only** when inverted OOS PF>1.3; **never** Connors crypto (loss-skew, not wrong sign). |
| **Data feeds dead?** | **Secondary.** FRED carry backtests fixed via `tools/fetch_fred_carry_cache.py`. Live pain = pick quality + methodology, not Binance outage. |
| **Portfolio empty?** | **No on server.** 81 portfolios audited: **66 with open positions**, 15 seeded-empty, 0 missing JSON. UI empty = invisible Unicode in `?key=` or viewing a zero-pick model. |
| **Where is edge?** | **Not** on money-ready `/audit/`. **Paper:** ai-tournament (deepseek_v4 n=208). **Discovery:** pick_funnel CRYPTO RR cell (subset). **Future:** verified lab ETF DM + crypto WF (forward n<100). |

**Money-ready classes: 0/9.** Policy-clean Tier-2 live: **0/6 major classes.**

---

## 1. Live ground truth (only surface for real-money sizing)

Sources: `money_ready_verdict.json`, `pf_registry.json` → `by_asset_class_policy_clean_net` (2026-06-02T06:21Z).

| Asset class | n | WR | PF | Verdict | Root cause (one line) |
|-------------|---|-----|-----|---------|------------------------|
| **CRYPTO** | 374 | 35.6% | **0.89** | NOT_READY | Bulk scanner loss-skew; lab VWAP/Bollinger WF PASS but opt-in only |
| **EQUITY** | 52 | 26.9% | **0.33** | NOT_READY | `regime_terminal` 40% concentration |
| **FOREX** | 32 | 28.1% | **0.48** | INSUFFICIENT | Carry lab thin; 14d EXPIRED mislabel inflates WR |
| **FUTURES** | 13 | 15.4% | **0.52** | INSUFFICIENT | TIME_EXIT zombies, not alpha |
| **ETF** | 3 | 66.7% | 1.46 | INSUFFICIENT | Best lab candidate — need forward n≥100 |
| **COMMODITY** | 4 | 50.0% | 1.68 | INSUFFICIENT | COT dead post-leakage; n=4 |
| **BOND** | 0 | — | — | INSUFFICIENT | No policy-clean rows |

**Tier-2 institutional bar:** PF>1.5, WR>50%, n≥100, MDD<20%, DSR/PBO where applicable.

### Two books problem (never size on raw)

| View | CRYPTO PF | Trust? |
|------|-----------|--------|
| Raw registry | ~1.46 (n≈1580) | **No** — duplicates, pre-policy |
| Policy-clean net | **0.89** (n≈377) | **Yes** |
| Smart Picks nav cell | WR 62–79%, PF 2.9–9.7 | **DISPUTED** — concentration, dup groups |
| pick_funnel PROVEN cell | RR1.0–1.5 LONG PF 3.89 n=327 | **Subset only** — aggregate still loses |

---

## 2. Root cause by asset class

| Class | Production verdict | Lab best | Diagnosis |
|-------|-------------------|----------|-----------|
| **CRYPTO** | FAIL PF 0.89 | VWAP WF OOS Sharpe 3.1 | Production = noise; lab edge not wired as primary |
| **EQUITY** | FAIL PF 0.33 | 12-1 mom PF 2.31 (MDD fail) | `regime_terminal` dominates; Faber pilot starting |
| **FOREX** | FAIL PF 0.48 | Carry PF 2.27 (n=13 lab) | Too few resolves; mislabel artifact on 14d panel |
| **ETF** | INSUFF n=3 | **Dual momentum Tier-2** n=104 | **Best promotion candidate** after forward gate |
| **COMMODITY** | INSUFF n=4 | TSMOM PF 1.08 | Post-leakage COT dead; vol-scaled cross-mom ~Sharpe 0.88 |
| **BOND** | No data | HYG/LQD mom Sharpe 1.84 | Sample too small |

**Structural root causes (ranked):**

1. **Research ≠ production** — lab winners are opt-in sidecars; bulk picks from un gated scanner/tournament/copy-trader.
2. **Negative expectancy after clean data** — not fixable by waiting on current emitters.
3. **Methodology** — no purge/embargo on main WF; i.i.d. MC; `real_data_backtest.py` lacks DSR/PBO/costs for 25/31 academic strategies.
4. **Operational** — resolver backlog, EXPIRED→WON, duplicate signal-ts groups.
5. **Data feeds** — secondary (FRED fixed; not binding constraint).

---

## 3. Proper backtesting methodology (M-108 admissibility standard)

**Doc:** `docs/BACKTEST_ADMISSIBILITY_STANDARD.md`  
**Tool:** `python3 tools/strategy_admissibility_report.py --write --fetch-live-portfolios`

| Stage | Requirement | Engine |
|-------|-------------|--------|
| 0 | Pre-register (M-107) | `hypothesis_registry.json` |
| 1 | Real OHLCV only | Documented fetch chains |
| 2 | Purged WF + costs | `rigorous_backtest_harness.py` / `walkforward_suite.py` |
| 3 | DSR / PBO / SPA | `rigorous_backtest_harness.py` |
| 4 | Block bootstrap + regime split | Required before Tier-1 |
| 5 | Forward virtual n≥100, PF≥1.5, WR≥50% | `pilot_virtual_book.py` |
| 6 | Shadow → `money_ready_verdict` | Opt-in scanner flags |

**Engine gap (2026-06-02):**

| Engine | WF | DSR/PBO | Costs | Classes |
|--------|-----|---------|-------|---------|
| `rigorous_backtest_harness.py` | Purged | Yes | Yes | All (PnL series) |
| `walkforward_suite.py` | 70/30 OOS | No | Yes | Verified sleeves |
| `real_data_backtest.py` | **No** | **No** | **No** | 25/31 academic |

**Action:** No new scanner wiring without Stage 2–5 artifacts on disk.

---

## 4. Portfolio audit — all 81 books (not empty)

Live roster `pf_portfolios.json` (2026-06-02T06:27Z):

| Bucket | Count |
|--------|-------|
| Has open positions | **66** |
| Zero positions (seeded, no tournament picks) | **15** |
| Missing JSON | **0** |

**Example — deepseek_v4__aggressive:** 11 open  
(GC=F, ES=F, MVST, SI=F, JPM, HD, VZ, MA, ADAUSDT, LINKUSDT, ETHUSDT)

**Top open books:** groq_llama_3_70b__aggressive (21), cerebras_llama4__aggressive (20), grok3__aggressive (16).

**15 genuinely empty:** `command_a__*`, `groq_kimi_k2__*`, `aimlapi_gpt4o__*`, `gh_models_gpt4o__*`, parts of `nous_hermes_4__*`, `deepseek_r1__conservative`.

**Why pf.html looked empty:**

1. Invisible Unicode in pasted `?key=deepseek_v4__aggressive` → wrong filename → 404 → “Pending first daily run”.
2. Viewing a seeded-empty model book.
3. `portfolio_mix__*` shadow books — 866 closed, **0 open** by design.

**Clean URL:** https://findtorontoevents.ca/audit/pf.html?key=deepseek_v4__aggressive  
**Fix:** `audit_dashboard/pf.html` strips invisible Unicode from `?key=` (2026-06-02).

**Reproducer:**

```bash
python3 tools/strategy_admissibility_report.py --write --fetch-live-portfolios
curl -sA 'Mozilla/5.0' 'https://findtorontoevents.ca/audit/data/pf_portfolio_deepseek_v4__aggressive.json' \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('open', sum(1 for p in d['positions'] if p.get('status')=='open'))"
```

---

## 5. Where is the edge? — three surfaces

### Trust hierarchy

```
1. policy_clean money_ready_verdict     ← ONLY real-money sizing
2. verified_strategies lab + WF         ← promotion candidates
3. paper_pilot forward (n≥100)          ← gate before scanner merge
4. ai-tournament / pf.html              ← separate universe; paper only
5. pick_funnel / nav matrix             ← discovery; DISPUTED cells
```

### A) https://findtorontoevents.ca/audit/

**Verdict: NO deployable edge.** 0/9 money-ready. Size only on policy-clean rollup.

### B) https://findtorontoevents.ca/audit/ai-tournament.html

**Verdict: Best credible PAPER edge** (separate from Smart Picks production).

| Model | pf_ci_lo | n resolved |
|-------|----------|------------|
| **deepseek_v4** | **2.52** | **208** |
| gpt4o | 2.13 | 134 |
| grok3 | 1.74 | 303 |
| cursor_agent | 1.20 | 101 |

Ignore fireworks_qwen (pf_ci_lo 5.59, **n=9**). Tournament PF portfolios: 66/81 have open positions.

### C) https://findtorontoevents.ca/audit/pick_funnel.html

**Verdict: Discovery only — do not size without policy-clean confirmation.**

- Nav surface matrix: **8/8 surfaces = `no-edge`**
- Smart Picks CRYPTO: PF 2.9 holdout pass but **67% mega_mutation concentration** → surface verdict no-edge
- One PROVEN cell: CRYPTO `trust=UNK & rr=RR1.0-1.5 & dir=LONG` (n=327, PF=3.89, holdout 3.07) — **subset**; class aggregate PF 0.89
- 14d recency: CRYPTO PF **0.67**; FOREX **83% WR / PF 0.10** (EXPIRED mislabel)

### D) Verified lab (not on main banner yet)

| Sleeve | Lab | Forward n | Status |
|--------|-----|-------------|--------|
| ETF dual momentum | Tier-2 PASS | 0 | Wait n≥100 |
| Crypto VWAP | WF PASS OOS Sharpe 3.1 | 0 | Opt-in |
| Crypto Bollinger | WF PASS PF 1.67 | 0 | Opt-in |
| Connors crypto | PF 0.90 | — | **REJECT** |
| Donchian combined | WF FAIL | — | Blocked |

---

## 6. DNA mutate / invert / kill

| Action | When | Example |
|--------|------|---------|
| **Kill** | Post-fix PF<0.8, n≥100 | ConnorsRSI2 crypto, seasonal rotation |
| **Mutate** | Lab PF>1.5, live PF<1 | Faber QQQ + costs; commodity vol-scale |
| **Invert** | OOS inverted PF>1.3 only | Rare; never class-wide |
| **Wire lab→prod** | WF PASS + forward promotion_ready | ETF DM, crypto VWAP |
| **Wait** | Forward n<100, lab PASS | Current pilots |

---

## 7. Shipped this session (Composer)

| Artifact | Purpose |
|----------|---------|
| `docs/BACKTEST_ADMISSIBILITY_STANDARD.md` | Canonical 7-stage gate |
| `tools/strategy_admissibility_report.py` | Unified quant JSON + portfolio audit |
| `audit_dashboard/data/strategy_admissibility.json` | Live dashboard payload |
| `audit_dashboard/data/verified_edge_status.json` | Edge trust strip |
| `audit_dashboard/pf.html` | Unicode key sanitization |
| `.github/workflows/verified-pilot-daily.yml` | Daily admissibility refresh |
| `reports/quant_strategy_root_cause_review_2026-06-02.md` | Long-form root-cause |

**Live JSON:** https://findtorontoevents.ca/audit/data/strategy_admissibility.json

---

## 8. Prioritized next actions

1. **Do not size up** on tournament or pick_funnel until `money_ready_verdict` flips.
2. **Run daily** `tools/run_verified_pilots_daily.py` — accumulate forward n on ETF DM + crypto WF + Faber.
3. **Route academic adapters** off `real_data_backtest.py` onto `rigorous_backtest_harness.py`.
4. **Depromote** negative-expectancy bulk sources (`regime_terminal`, unverified mercury2, Connors crypto).
5. **Promote ETF dual momentum** only when `pilot_forward_dashboard.json` → `promotion_ready: true`.

---

## 9. Cross-reference

- Peer memo: `reports/EAGLE_JUNE2_GROK.md`
- Methodology audit: `reports/backtesting_methodology_audit_2026-06-02.md`
- Updates card: `updates/2026-06-02-quant-admissibility-pipeline.md`

**Final verdict:** Waiting alone is insufficient. Edge is **split across three universes** (tournament paper, pick_funnel filter cells, lab sleeves). None clears policy-clean money-ready on `/audit/` today. Capital flows only through the M-108 admissibility pipeline.
