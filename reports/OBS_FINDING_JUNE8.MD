# OBS_FINDING_JUNE8 — Obsidian Vault Edge Claims vs Clean DB (2026-06-09)

**Method:** Inventory every documented edge claim in `obsidian-notes/`, re-measure on the **clean cohort** (exclude backfill + NULL-resolved + banned sources + per-class sane-pnl guard; EXPIRED counts as non-win). Cross-checked against `money_ready_verdict.json` (2026-06-08) and live `at_pick_outcomes` queries.

**BLUF:** **No documented Obsidian edge claim HOLDS on clean data at money-ready bar.** Every vault "T1/T2/ready" claim either rests on backfill-inflated numbers, a tiny clean subset, lab-only backtests, or pre-fix picks-now display bugs. The system is **not a coin-flip winner today** — it is **worse than coin-flip on several classes** once artifacts are removed.

---

## 1. Cross-check: Copilot session audit (2026-06-09-transcript) vs verified data

| Copilot claim | Verified? | Clean-data truth |
|---|---|---|
| FOREX 14d WR **64.2%**, PF **2.43** | **REFUTED** | Clean FOREX 14d: **n=100, WR 5.0%** (5W). Pre-dedup 14d panel is concentration + duplication artifact. |
| GBPUSD n=114, WR **58.8%** | **REFUTED** | Post-fix `load_db_edge`: **6.9% WR**, 87% expired; backfill rows excluded. |
| stocks_rsi2_pullback n=894, WR **58.8%**, PF **2.68** | **REFUTED** | 14d equity WR **29.9%**; dup-inflated + period-biased (May correction). Do not re-emit. |
| RENDERUSDT inverse_ml WR **80%**, PF **7.7** | **REFUTED** | Strategy **PERMANENTLY_KILLED**; 0% on 3 clean live trades. |
| AI Tournament leaders = trading edge | **REFUTED** | Directional accuracy ≠ P&L after slippage; n=43–89 resolved; ~47% picks still OPEN. |
| 0/8 money-ready (verdict table) | **HOLDS** | Matches `money_ready_verdict.json` 2026-06-08: 0/9 pass Tier-2. |

**Source:** `updates/2026-06-09-session-transcript-strategy-audit.md` vs `reports/UPDATED_MONEY_READY_RECOMMENDATION_2026-06-09.md`, `pick_summary_stats_14d.json`, live DB 2026-06-09.

---

## 2. Per-class: vault claims vs clean DB (2026-06-09)

| Class | Vault claim (Obsidian) | Clean cohort (live DB) | Verdict |
|---|---|---|---|
| **CRYPTO** | mega_mutation T1: PF **2.86**, WR **63.9%**, n=204 (`CRYPTO.md`, `READY-TO-TRADE-NOW`) | Class clean: n=1773, WR **46.6%**, PF **1.25**. Intrabar replay: **42.9%** WR / PF **1.22** (coin flip). | **REFUTED** as money-ready until intrabar + multi-month hold. |
| **EQUITY** | 14d WR improving 37→67% (`EQUITY.md`) | Clean: n=358, WR **32.4%**, PF **1.30**. money_ready: n=71, WR 53.5%, MDD 33%. | **NO_EDGE** — single-snapshot May batch; not durable. |
| **FOREX** | fx_smart_carry PF **1.85**, T2 candidate (`fx_smart_carry_trade_momentum.md`) | Clean: n=117, WR **8.5%**, PF **0.63**. money_ready: WR **24%**, PF **0.077**, n=25. | **REFUTED** — catastrophic; KILL/MUTATE axis. |
| **COMMODITY** | z-score longs ZC=F/ZS=F score 81 (`READY-TO-TRADE-NOW`) | Clean: n=46, WR **50%**, PF **1.04** — below bar, n<50. | **INSUFFICIENT_DATA** |
| **ETF** | etf_verified_dual_momentum lab-T2, WF PASS (`etf_verified_dual_momentum.md`) | Clean live: n=**2**, WR **0%**. money_ready: n=20, WR 25%, PF 0.37. | **INSUFFICIENT_DATA** — lab ≠ live forward. |
| **BOND** | TLT/MUB/EMB picks (`READY-TO-TRADE-NOW`) | Clean: **n=0**. money_ready: n=1. | **INSUFFICIENT_DATA** |
| **FUTURES** | (zombie class) | Clean: **n=0**. PF 10.3 on raw data = 2-win artifact. | **INSUFFICIENT_DATA / tagging artifact** |

**Clean-cohort query recipe:** `reports/2026-06-06-money-ready-screen-clean-cohort.md` + filters in `/money-maker-readyv2` skill.

---

## 3. Claims that survived vs collapsed

### Collapsed (do NOT size up)
- `low_hanging_fruit_report.md` entire chain → **REFUTED** (`UPDATED_MONEY_READY_RECOMMENDATION_2026-06-09.md`)
- `READY-TO-TRADE-NOW.md` GBPUSD DB_WR=59% → **already marked SUPERSEDED** in vault
- luxalgo_confluence 63%/PF 5.35 (n=73 of 2040) → **borderline artifact**, not confirmed
- pick_summary 14d FOREX 64% → **pre-dedup contamination** (99% AlphaEngine concentration)

### Closest candidates (paper-pilot only, NOT money-ready)
| Strategy | Class | Clean numbers | Still missing |
|---|---|---|---|
| luxalgo_confluence | CRYPTO | n=73, WR 63%, PF 5.35, 3mo | Full-history 45.5%/1.20; intrabar; n<100 |
| MeanReversionBB | EQUITY | n=214, WR 44.9%, PF 1.88, 2mo | WR<52%; only 2 months |
| B_flip_PriceRocMeanReversion | CRYPTO | Intrabar: WR 80.4%, PF 6.3, n=51 | n<100; multi-month; forward-only post-fix |

---

## 4. How to save the system (coin-flip → statistical edge)

The failure is **measurement layer first**, not alpha supply. Academic sleeves (TSMOM, residual momentum, carry) exist in-repo but are **dormant** — do not wire until resolver is trustworthy.

### P0 — Fix measurement (unblocks all classes)
1. **Backfill quarantine** — DONE in `build_pf_registry.py` (77.8% rows excluded).
2. **Sane-pnl guard** — DONE (FX feed bugs, reverse-split defense).
3. **Intrabar OHLC replay resolver** — `tools/reresolve_intrabar.py` dry-run built; **--apply gated**. Deepen `crypto_ohlcv` history (currently ~30d 1h bars).
4. **TP/SL vs horizon** — production_scanner caps wired; legacy picks still 80%+ TIME_EXPIRED.

### P1 — Re-baseline & paper-pilot
5. Re-screen all strategies on clean+intrabar cohort (bar: n≥100, ≥3mo, PF>1.5, WR>52%).
6. Forward paper-pilot survivors only (`forward_test_only=1`); ≥4 weeks before sizing.

### P2 — Wire academic sleeves (after P0)
7. TSMOM vol-scaled (`tsmom_strategy.py` + `cta_bridge.py`) — trailing-stop exits fix expiry trap.
8. Residual momentum EQUITY (`residual_momentum.py`) — promote from sidecar.
9. Carry + roll-down BOND/COMMODITY/FX (`bond_strategy_harness.py`, `commodity_basis_carry.py`).

### P3 — Kill false surfaces
10. Ban sizing on tournament / pick_funnel / picks-now headline cells without clean-cohort corroboration.
11. FOREX: finish KILL/MUTATE (`multi_asset_scanner` banned; wire `apply_emitter_discipline`).

**Live roadmap page:** https://findtorontoevents.ca/audit/edge_validation_roadmap.html (zoocode, reviewed 2026-06-09; security leaks removed).

---

## 5. Reproducers

```bash
# money_ready verdict (official gates)
python3 -c "import json;d=json.load(open('audit_dashboard/data/money_ready_verdict.json'));print(d['generated_at']);[print(k,v['n_resolved'],round(v['wr']*100,1),v['pf'],v['verdict']) for k,v in d['classes'].items()]"

# intrabar dry-run (CRYPTO)
python3 tools/reresolve_intrabar.py --max 3000 --max-hold-bars 168 --min-strategy-n 30

# clean cohort screen
# See reports/2026-06-06-money-ready-screen-clean-cohort.md
```

**Related reports:** `2026-06-06-per-asset-class-edge-reality-and-academic-roadmap.md`, `2026-06-06-money-ready-screen-clean-cohort.md`, `UPDATED_MONEY_READY_RECOMMENDATION_2026-06-09.md`
