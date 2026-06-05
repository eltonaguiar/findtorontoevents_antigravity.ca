# Real-Money Edge Hunt — Per Asset Class (2026-06-05)

**Goal #1** — statistical edge without waiting months on empty forward books.  
**Ground truth:** `money_ready_verdict.json` generated `2026-06-05T14:09Z` — **0/9 classes money-ready**.

| Class | n | WR | PF | Verdict | Size today? |
|-------|--:|---:|---:|---------|-------------|
| CRYPTO | 220 | 47.3% | 0.99 | NOT_READY | Pilot only (one sleeve) |
| EQUITY | 45 | 24.4% | 0.26 | INSUFFICIENT_DATA | **No** (wire PEAD probation) |
| COMMODITY | 7 | 42.9% | 1.74 | INSUFFICIENT_DATA | **No** (frozen) |
| ETF | 11 | 63.6% | 0.80 | INSUFFICIENT_DATA | **No** (pilot XLK only) |
| FOREX | 22 | 22.7% | 11.22* | INSUFFICIENT_DATA | **No** (*PF artifact) |
| BOND | 0 | — | — | INSUFFICIENT_DATA | **No** |
| FUTURES | 15 | 6.7% | 0.07 | INSUFFICIENT_DATA | **No** |

Tier tracker: `reports/strategy_tier_tracker_20260605T141115Z.md`

---

## Fast substitutes (don't wait on forward picks)

| Source | Use for | Caveat |
|--------|---------|--------|
| `pf_registry.json` policy_clean_net | Canonical closed-book PF/WR | Class aggregates can hide sleeve edge |
| Walk-forward / verified_strategies | ETF dual-mom, PEAD equity | Lab ≠ live book until merged |
| `bootstrap_forward_stats.json` | inverse_ml ADA forward PF 2.38 n=38 | `recommend_enable: false` |
| AI tournament (`ai_tournament_picks_latest.json`) | Model triangulation | **Not** production merge — research |
| `tools/research/forex_carry.py` | Carry backtest PF 2.11 n=13 | LOCKED until n≥30 |
| `etf_managed_futures_proxy` (DBMF/KMLM) | Commodity beta via ETF | Run under ETF paper |
| Earnings cache `data/earnings/*/latest.json` | PEAD inputs | Not wired to `pead_equity` loader yet |

---

## Per-class: promote / block / this week

### CRYPTO — closest to T2

**Promote (pilot, reduced size):**
- `crypto_liquidity_wick_reversal_v1` — n=30, WR=60%, PF=1.55 (only T2 sleeve)
- `battleground_luxalgo` — PF≈3.98, n=26 (probe until n≥30)
- **LONG-only** class filter (14d WR 53.6% vs SHORT 31%)

**Block:** `copy_trader_intel`, `ml_enhanced_*`, ensemble stacks, tournament→production merge

**Wire:** Attach `onchain_cache.json` funding/FGI to all crypto picks so `fundamental_macro_gates` scores non-valuation strategies.

### EQUITY — earnings / analyst / financials

**Best edge (evidence):** `pead_equity` WF OOS **62.2%** WR — **shadow only** (`PEAD_EQUITY_ENABLED=0`).

**Best closed sleeve (tiny):** `stocks_rsi2_pullback` n=5, WR=100%.

**Block:** `regime_terminal`, `multi_asset_copytrader`, `regime_accumulation`, `Earnings Drift`, EQUITY SHORT, conf [0.60,0.65).

**This week:**
1. `PEAD_EQUITY_ENABLED=1` → collect `pead_shadow_picks.json` (no active sizing)
2. Wire `data/earnings/*/latest.json` into PEAD loader (not `incubator_picks.json` only)
3. Probation cap: max 2 `pead_equity` picks after ~30 shadow signals
4. `post-earnings-rev-scout` (58.3% WR n=12) — feature boost, not standalone emitter
5. `value_screener` — universe n=1 today; not ready

**Modules:** `equity_pead_strategy.py`, `equity_post_earnings_drift.py`, `equity_earnings_surprise.py`, `fundamental_macro_gates.py` (equity scoring is reason-keyword heuristic until earnings wired).

### COMMODITY — frozen

**NO_TRADE** futures class. PF 1.74 on n=7 is mirage.

**Fast substitute:** `alpha_engine/etf_managed_futures_proxy.py` — DBMF/KMLM under **ETF** paper (10% cap).

**Rebuild:** `commodity_term_cot` paper-only; M-096 CT=F cap; exclude 2026-06-04 backfill from analytics.

### ETF — lab PASS, live FAIL

**Best sleeve:** `etf_verified_dual_momentum` — lab OOS PF **2.746**, forward **0** closes.

**Live book:** `cta_golden_cross` etc. → class PF **0.80** (wrong population).

**This week:** Keep XLK paper rotation; do **not** enable scanner; optional governed lab→paper_log backfill for n≥30 shadow gate.

### FOREX — frozen, PF lie

**Trustworthy PF:** **0.31** (excl. one +0.61% outlier). Reported 11.22 is ratio artifact.

**Path:** Extend `forex_carry` backtest 2010–2025; paper `cta_cross_asset_tsmom` **SHORT** only after n≥30.

**Keep:** `FOREX_HARD_DISABLE=1`

### BOND / FUTURES

**BOND:** NO_TRADE. Paper `bond_hyg_lqd_winner` only.

**FUTURES:** NO_TRADE. Move TSMOM research to **COMMODITY** class; fix TIME_EXIT zombies.

---

## AI tournament (immediate signal, not sizing)

T1 models (n≥30, PF_CI_lo>1): deepseek_v4, cursor_agent, llama4_scout, grok3 — use for **directional research** and cross-check, not production merge until n≥100 + OOS stability.

---

## Priority wiring queue (7 days)

| P | Action | File / env |
|---|--------|------------|
| P0 | PEAD shadow on + earnings JSON feed | `production_scanner.py`, `data/earnings/` |
| P0 | Block EQUITY regime_terminal on all emit paths | `quality_gates.py` |
| P1 | Crypto network metrics → fundamental gates | `crypto_risk_gates.py`, `fundamental_macro_gates.py` |
| P1 | ETF pilot cron + first rotation close | `verified_strategies/.../etf_dual_momentum_pilot.py` |
| P2 | DBMF/KMLM paper under ETF | `etf_managed_futures_proxy.py` |
| P2 | forex_carry backtest extend | `tools/research/forex_carry.py` |

---

## Reproduce

```bash
python3 tools/strategy_tier_tracker.py
python3 -c "import json;from pathlib import Path;d=json.load(open('audit_dashboard/data/money_ready_verdict.json'));print(d.get('generated_at'));[print(k,v['n_resolved'],v['wr'],v['pf'],v['verdict']) for k,v in d['classes'].items()]"
```

Subagent detail: `reports/edge_hunt_FOREX_2026-06-05.md` (FOREX agent), tier tracker, `plans/money_ready_enhancements_spec.md`.