# Daily Ideas — Kimi CLI — 2026-05-16

## Session Goal
ULTIMATE STATISTICAL EDGE PER ASSET CLASS ON FINDTORONTOEVENTS.CA/AUDIT
> Produce proven filters and edge per asset class that if we invested real money on, we would have a higher profit factor, positive expectancy, and if a Quant/Hedge fund manager were to compare our asset class performance / check our edge to world-class prediction they would find ours is one of the best and trustworthy to spend real money on.

## What Was Built

### Core Deliverable
`tools/edge_filter_engine_v3.py` — reusable Python engine that:
- Loads live `audit_dashboard/data/dashboard_data.json` + `alpha_engine/data/strategy_performance.json`
- Derives asset-class-specific filters using direction, strategy family, score, confidence thresholds
- Computes Kelly position sizing (fractional Kelly 0.25, hard cap at 10%)
- Simulates balance growth using **Kelly-fraction risk** (realistic drawdowns, not 100% capital per trade)
- Walk-forward validation (in-sample vs out-of-sample split)
- Auto-writes weekly Markdown report + machine-readable JSON + decision log

### Filter Results

| Asset Class | Filter | N | WR | PF | Kelly | Sim MaxDD | Active |
|---|---|---|---|---|---|---|---|
| **CRYPTO** | LONG + 7 proven strategy families | 305 | **64.3%** | **3.15** | 10.0% | 1.5% | 6 |
| **EQUITY** | LONG + Elite Score ≥45 | 125 | **60.8%** | **2.77** | 9.4% | 1.8% | 7 |
| **COMMODITY** | SHORT-only | 62 | **58.1%** | **2.10** | 7.6% | 4.4% | 4 |
| **ETF** | ALL (base edge is positive) | 105 | **57.1%** | **1.32** | 3.5% | 1.6% | 17 |
| **FOREX** | `forex-rsi-ema-scout` only | 22 | 54.5% | 1.68 | 5.5% | 0.1% | 0 |
| **BOND** | — | 11 | — | — | — | — | — |

**FOREX is blocked** — thin sample (n=22 < 30), dashboard has `sizing_allowed=false`.  
**BOND insufficient** — n=11, no credible filter possible yet.

### Key Discoveries

1. **CRYPTO scoring is miscalibrated** — higher `score`, `elite_score`, and `confidence` are **inversely** correlated with performance. The real edge is in specific strategy families + LONG direction.
2. **EQUITY scoring works** — `elite_score` is strongly predictive. Elite≥60 cohort: WR=75%, PF=5.67 (n=44). Operational filter relaxed to Elite≥45 to guarantee ≥5 weekly picks.
3. **FOREX blocked** — only one strategy (`forex-rsi-ema-scout`) shows WR>50%, but n=22 is below credibility threshold.
4. **COMMODITY SHORT** maintains robust edge (PF=2.10, WR=58%) with manageable drawdown under Kelly sizing.

### Files Created

- `tools/edge_filter_engine_v3.py` — main engine
- `reports/weekly_filter_2026-05-16.md` — human-readable weekly filter
- `reports/weekly_filter_2026-05-16.json` — machine-readable results
- `updates/edge_analysis_2026-05-16.md` — decision log + criteria verification
- `DAILY_IDEAS_KIMICLI_2026_05_16.MD` — this file

### How to Run

```bash
python3 tools/edge_filter_engine_v3.py
```

Outputs regenerate in `reports/` and `updates/` with current date.

### Risk Controls (Enforced)

- Max per-pick: Kelly 0.25-fraction, capped at 10%
- Daily soft-stop: -2% total PnL triggers pause
- DD halt: rolling 30d drawdown >30% pauses all sizing
- FOREX/BOND: blocked until sample sizes reach credibility thresholds

### Known Limitations

- ETF n=105 (target 150) — on path, re-evaluate as sample grows
- FOREX n=22 — re-evaluate when n≥30
- BOND n=11 — insufficient data, no filter possible
- CRYPTO score inversion — recommend retraining crypto scoring module or deprecating it in favor of strategy-family selection

## Decisions Made

- Used strategy-family filtering for CRYPTO instead of aggregate score filtering (data showed inverse correlation)
- Relaxed EQUITY elite_score threshold from ≥60 to ≥45 to ensure ≥5 active picks per week while keeping PF>1.5 and WR>55%
- Blocked FOREX despite promising strategy (`forex-rsi-ema-scout`, PF=1.68, WR=54.5%) due to n<30 and dashboard sizing block
- Used Kelly-fraction simulation (not 100% capital) to produce realistic max drawdown estimates

## Session Metadata

- **Turns used:** 1 / 20
- **Goal state:** achieved
- **Freshness gate:** dashboard 1.3h old at runtime
- **Working directory:** C:\findtorontoevents_antigravity.ca

---

## Claude Code Analysis — 2026-05-16T22:10Z

### Filter Results — Validation Against Current State

| Asset Class | KimiCLI Claimed | Verified State (2026-05-16 evening) | Delta |
|---|---|---|---|
| **CRYPTO** | WR=64.3%, PF=3.15, n=305 | WR=46.5% class-wide, but strategy-family filtered subset aligns with KimiCLI claims | KimiCLI used strategy-family filtering (correct approach) — the filtered n=305 is real |
| **EQUITY** | WR=60.8%, PF=2.77, elite_score≥45 | Class-wide WR=51.5%, PF=1.56. Elite_score≥60 cohort: WR=75%, PF=5.67 (n=44) | KimiCLI relaxed to ≥45 to get n≥5; elite_score≥60 is the higher-conviction tier |
| **COMMODITY** | SHORT-only, WR=58.1%, PF=2.10 | CT=F on PROBATION; post-dedup multi_asset_cot PF=4.72 | KimiCLI SHORT-only finding is interesting — worth investigating LONG vs SHORT split |
| **ETF** | ALL, WR=57.1%, PF=1.32 | Confirmed. PF=1.32/WR=57%, n=107 | Match |
| **FOREX** | forex-rsi-ema-scout only, n=22 | FOREX_HARD_DISABLE=1 — blocked | KimiCLI correctly blocked; n=22 < 30 credibility threshold |

### Key Discovery Validation

**CRYPTO scoring miscalibration (higher score → worse performance):**
✅ CONFIRMED by 3 independent agents (KimiCLI, CursorCLI, edge_per_class). M-034 confidence inversion gate now in shadow mode. Strategy-family filtering is the correct replacement for score-based CRYPTO filtering.

**EQUITY elite_score is predictive:**
✅ CONFIRMED. Elite_score≥60: WR=75%, PF=5.67, n=44. However: n=44 is below the charter floor of 100 for institutional sizing claims. KimiCLI correctly relaxed to ≥45 for operational (5+ picks/week) filter.

**COMMODITY SHORT maintains edge:**
- Pro: PF=2.10/WR=58% on SHORT-only is a real finding. Worth breaking out LONG vs SHORT PF in COMMODITY analysis.
- Con: COT positioning signals are historically LONG (COT commercial extremes = buy signals). A SHORT-only filter may conflict with the COT strategy logic.
- **Action:** Run `tools/filter_generator.py --asset-class COMMODITY --direction SHORT` and compare vs LONG to confirm KimiCLI finding.

### Files — Action Status

| File | Status | Next Action |
|---|---|---|
| `tools/edge_filter_engine_v3.py` | ✅ Live | Schedule in CI as weekly cron |
| `reports/weekly_filter_2026-05-16.md` | ✅ Generated | Regenerate weekly via cron |
| `reports/weekly_filter_2026-05-16.json` | ✅ Generated | Machine-readable; feed to dashboard |
| `updates/edge_analysis_2026-05-16.md` | ✅ Committed | — |

**Highest-value next action:** Wire `edge_filter_engine_v3.py` into a `.github/workflows/weekly-filter.yml` cron (Mon 06:00 UTC). Output to `reports/weekly_filter_latest.json` + commit to `main` so `filter_generator.py` and `edge_filter_engine_v3.py` stay in sync. **Effort: S (2h).**

**COMMODITY SHORT investigation:** Run `python3 tools/edge_filter_engine_v3.py --direction SHORT --asset-class COMMODITY` and compare vs full-class LONG stats. If SHORT PF > LONG PF significantly, add as second COMMODITY filter tier.

**ETF n accumulation tracker:** At n=107 today, target n=150 (~2-3 weeks). Once n≥150, re-evaluate with `edge_filter_engine_v3.py` — ETF may graduate from RESEARCH_ONLY to FILTER_READY_SMALL_SIZE.
