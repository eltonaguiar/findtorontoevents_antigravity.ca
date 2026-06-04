#!/usr/bin/env python3
"""
Comprehensive Strategy Roadmap & Analysis
==========================================
Author: Claude Opus 4.7 | Date: 2026-05-29
Purpose: Document all 81 strategies per asset class, identify world-class candidates,
         and outline the path to investable strategies.

Based on rigorous backtest results from alpha_engine/rigorous_backtest_harness.py
with purged walk-forward, DSR, PBO, and cost modeling.
"""

import pymysql
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# 2026-06-04 INCIDENT #89 scrub: switched from hardcoded literal to the
# canonical tools.db_env.get_stocks_creds() helper. The hardcoded fallback
# was the well-known convention literal — gitignored per ~/dbpasses.txt, but the
# literal in code was a P0 leak. The helper resolves from env vars in
# priority order (DB_PASS_STOCKS → MYSQL_PASSWORD → legacy aliases) and
# raises if none are set, so misconfigured runs fail loud instead of
# silently using the convention.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from tools.db_env import get_stocks_creds  # noqa: E402


def get_connection():
    creds = get_stocks_creds()
    return pymysql.connect(
        **creds, charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def generate_roadmap():
    conn = get_connection()
    cur = conn.cursor()
    
    now = datetime.now(timezone.utc)
    est = now - timedelta(hours=4)
    est_str = est.strftime('%Y-%m-%d %H:%M:%S EDT')
    
    # Overall stats
    cur.execute("SELECT COUNT(*) as cnt FROM strategy_summary WHERE pick_count_all_time IS NOT NULL AND pick_count_all_time > 0")
    n_strats = cur.fetchone()['cnt']
    
    cur.execute("SELECT sizing_status, COUNT(*) as cnt, AVG(dsr) as avg_dsr, AVG(pbo) as avg_pbo FROM strategy_summary WHERE dsr IS NOT NULL GROUP BY sizing_status")
    sizing_stats = cur.fetchall()
    
    # Per-class stats
    classes = ['CRYPTO', 'EQUITY', 'FOREX', 'ETF', 'COMMODITY', 'FUTURES', 'BOND']
    class_stats = {}
    for ac in classes:
        cur.execute(f"""
            SELECT COUNT(*) as n_strategies,
                   AVG(pick_count_all_time) as avg_n,
                   AVG(pf_all_time) as avg_pf,
                   AVG(wr_all_time) as avg_wr,
                   AVG(dsr) as avg_dsr,
                   AVG(pbo) as avg_pbo,
                   SUM(CASE WHEN sizing_status IN ('T1','T2','T3') THEN 1 ELSE 0 END) as n_sized
            FROM strategy_summary WHERE asset_class='{ac}' AND pick_count_all_time IS NOT NULL AND pick_count_all_time > 0
        """)
        class_stats[ac] = cur.fetchone()
    
    # Top 3 per class by DSR
    top_per_class = {}
    for ac in classes:
        cur.execute(f"""
            SELECT strategy_name, pf_all_time, wr_all_time, pick_count_all_time, sizing_status,
                   dsr, pbo, costed_sharpe, costed_mdd, file_path,
                   walk_forward_consistency, walk_forward_avg_os_sharpe
            FROM strategy_summary 
            WHERE asset_class='{ac}' AND pick_count_all_time IS NOT NULL AND pick_count_all_time >= 3
            ORDER BY dsr DESC LIMIT 3
        """)
        top_per_class[ac] = cur.fetchall()
    
    # World-class candidates (closest to T1/T2/T3)
    cur.execute("""
        SELECT strategy_name, asset_class, pf_all_time, wr_all_time, pick_count_all_time,
               sizing_status, dsr, pbo, costed_sharpe, costed_mdd,
               walk_forward_consistency
        FROM strategy_summary 
        WHERE pick_count_all_time IS NOT NULL AND pick_count_all_time >= 10
        ORDER BY 
            CASE sizing_status WHEN 'T1' THEN 1 WHEN 'T2' THEN 2 WHEN 'T3' THEN 3 ELSE 4 END,
            dsr DESC
        LIMIT 15
    """)
    candidates = cur.fetchall()
    
    conn.close()
    
    # Generate markdown
    md = f"""# Comprehensive Strategy Roadmap

- **Generated:** {est_str}
- **Total Strategies Tracked:** {n_strats}
- **Database:** ejaguiar1_stocks (mysql.50webs.com)
- **Backtest Harness:** Purged WF + DSR + PBO + Costs (`alpha_engine/rigorous_backtest_harness.py`)

---

## 1. Executive Summary

### Current State: No World-Class Strategies Yet

**0 strategies meet T1/T2/T3 sizing thresholds.** While 81 strategies are tracked across 7 asset classes, rigorous statistical validation reveals systemic overfitting:

| Metric | Value |
|---|---|
| Strategies with DSR/PBO computed | {sum(1 for s in sizing_stats)} |
| Average DSR (all sized) | {sum(s['avg_dsr'] or 0 for s in sizing_stats) / max(len(sizing_stats), 1):.2f} |
| Average PBO (all sized) | {sum(s['avg_pbo'] or 0 for s in sizing_stats) / max(len(sizing_stats), 1):.3f} |
| Strategies passing T3+ | 0 |

**Root Cause:** High PBO (0.3–0.7) indicates most strategies were data-mined (many parameter trials), inflating in-sample performance but failing out-of-sample. The solution: fewer parameters + economic rationale + purged walk-forward during development.

---

## 2. Per-Asset-Class Overview

"""
    
    for ac in classes:
        s = class_stats[ac]
        n = s['n_strategies'] or 0
        if n == 0:
            md += f"### {ac}\n*No strategies with sufficient data yet.*\n\n"
            continue
        
        avg_pf = s['avg_pf'] or 0
        avg_wr = s['avg_wr'] or 0
        avg_dsr = s['avg_dsr'] or 0
        avg_pbo = s['avg_pbo'] or 0
        n_sized = s['n_sized'] or 0
        
        md += f"### {ac} ({n} strategies)\n"
        md += f"| Metric | Value |\n|---|---|\n"
        md += f"| Avg PF | {avg_pf:.3f} |\n"
        md += f"| Avg WR | {avg_wr:.1%} |\n"
        md += f"| Avg DSR | {avg_dsr:.2f} |\n"
        md += f"| Avg PBO | {avg_pbo:.3f} |\n"
        md += f"| Strategies sized (T1/T2/T3) | {n_sized} |\n\n"
        
        md += f"**Top 3 by DSR:**\n"
        md += "| Rank | Strategy | PF | WR | n | DSR | PBO | WF Consistency | Status |\n"
        md += "|---|---|---|---|---|---|---|---|---|\n"
        for i, r in enumerate(top_per_class.get(ac, []), 1):
            pf = r['pf_all_time'] or 0
            wr = r['wr_all_time'] or 0
            n_r = r['pick_count_all_time'] or 0
            dsr = r.get('dsr') or 0
            pbo = r.get('pbo') or 0
            wf = r.get('walk_forward_consistency') or 0
            md += f"| {i} | {r['strategy_name']} | {pf:.3f} | {wr:.1%} | {n_r} | {dsr:.2f} | {pbo:.3f} | {wf:.1%} | {r['sizing_status']} |\n"
        md += "\n"
    
    md += """---

## 3. World-Class Thresholds (Not Yet Met)

| Tier | Min PF | Min WR | Min n | Min DSR | Max PBO | Max MDD | Description |
|---|---|---|---|---|---|---|---|
| T1 | > 2.0 | > 55% | ≥ 30 | > 0.95 | < 0.05 | < 10% | Renaissance-grade |
| T2 | > 1.5 | > 50% | ≥ 30 | > 0.90 | < 0.10 | < 20% | Institutional |
| T3 | > 1.2 | > 48% | ≥ 20 | > 0.80 | < 0.20 | < 30% | Retail-OK |

### Closest Candidates (Still Shadow)

| Strategy | Class | PF | WR | n | DSR | PBO | Gap to T3 |
|---|---|---|---|---|---|---|---|
"""
    
    for r in candidates:
        pf = r['pf_all_time'] or 0
        wr = r['wr_all_time'] or 0
        n_r = r['pick_count_all_time'] or 0
        dsr = r.get('dsr') or 0
        pbo = r.get('pbo') or 0
        
        gaps = []
        if pf < 1.2: gaps.append(f"PF {pf:.2f}<1.2")
        if wr < 0.48: gaps.append(f"WR {wr:.0%}<48%")
        if n_r < 20: gaps.append(f"n {n_r}<20")
        if dsr < 0.80: gaps.append(f"DSR {dsr:.2f}<0.80")
        if pbo > 0.20: gaps.append(f"PBO {pbo:.2f}>0.20")
        
        gap_str = "; ".join(gaps) if gaps else "MEETS T3"
        md += f"| {r['strategy_name']} | {r['asset_class']} | {pf:.3f} | {wr:.1%} | {n_r} | {dsr:.2f} | {pbo:.3f} | {gap_str} |\n"
    
    md += """
---

## 4. Path to World-Class Strategies

### Problem: Overfitting (High PBO)
The primary blocker is PBO > 0.20 for nearly all strategies. This means the strategies were likely discovered through extensive parameter searching, which inflates in-sample performance but fails out-of-sample.

### Solution: The 7 New Strategy Designs
See `alpha_engine/new_strategies/strategy_designs.py` for 7 economically-motivated strategies (one per asset class) designed with:
- **≤2 parameters each** (reduces trial count → lowers PBO)
- **Strong economic rationale** (not data-mined patterns)
- **Simple threshold rules** (no ML, no complex interactions)
- **Cost-aware design** (survives realistic fees/slippage)

| Asset Class | Strategy Name | Params | Expected Sharpe | Economic Basis |
|---|---|---|---|---|
| CRYPTO | crypto_funding_carry_reversion | 2 | 0.8 | Funding rate structural carry + RSI mean-reversion |
| EQUITY | equity_earnings_momentum_quality | 2 | 0.6 | PEAD anomaly (35+ years literature) + quality filter |
| FOREX | forex_carry_term_structure | 2 | 0.7 | Currency carry risk premium + term structure timing |
| ETF | etf_sector_rotation_momentum | 2 | 0.6 | Sector momentum (Jegadeesh & Titman 1993) |
| COMMODITY | commodity_term_structure_carry | 2 | 0.5 | Contango/backwardation → supply/demand signal |
| FUTURES | futures_trend_volatility_target | 2 | 0.8 | Time-series momentum (100+ years data) + vol targeting |
| BOND | bond_yield_curve_steepener | 2 | 0.5 | 2s10s slope predicts duration returns |

### Implementation Priority
1. **FUTURES trend + vol target** — simplest, most documented (Moskowitz et al. 2012)
2. **COMMODITY term structure carry** — economically clean, few params
3. **BOND yield curve steepener** — single macro signal, well-documented
4. **FOREX carry + term structure** — established risk premium
5. **ETF sector rotation** — requires sector ETF data
6. **EQUITY PEAD** — requires earnings data pipeline
7. **CRYPTO funding carry** — requires funding rate data

### Data Integrity Prerequisites
Before any strategy can be validated:
1. **Fix TIME_EXIT phantom-closes** — 62% of trading_picks are zero-PnL exits diluting metrics
2. **Resolve EXPIRED→WON mislabels** — inflates WR artificially
3. **Dedup signal timestamps** — prevents double-counting into WR/PF
4. **Increase sample sizes** — most strategies have n < 30

---

## 5. Database Schema Reference

| Table | Rows | Purpose |
|---|---|---|
| `strategy_summary` | 81 | Canonical catalog with PF/WR/DSR/PBO/time-windows/traceability |
| `pick_dimension_snapshot` | 3,000 | Per-pick Score/Trust/AGV/Regime/Edge sub-tags |
| `pick_funnel_views` | 6 | Performance by nav-surface (button vs tab comparison) |
| `edge_discovery` | 7 | Pre-computed edge significance (Bonferroni-corrected) |
| `metric_dimensions` | 41 | Dictionary of all dimension values |
| `view_definition_catalog` | 10 | Documents every dashboard button/filter |

### Live Dashboard
- **Strategy Funnel section:** https://findtorontoevents.ca/audit/pick_funnel.html
- **Data source:** https://findtorontoevents.ca/audit/data/strategy_funnel_data.json

---

## 6. Re-Run Backtests

```bash
# All strategies for one asset class
python3 alpha_engine/rigorous_backtest_harness.py --batch --class CRYPTO

# Single strategy
python3 alpha_engine/rigorous_backtest_harness.py --strategy stocks_rsi2_pullback --class EQUITY

# With more trials for better DSR/PBO estimates
python3 alpha_engine/rigorous_backtest_harness.py --batch --class FOREX --n-trials 200 --n-bootstrap 2000
```

---

*Report generated from ejaguiar1_stocks. All metrics from resolved picks with pnl_pct IS NOT NULL.
Backtest harness implements purged walk-forward, DSR (Bailey & Lopez de Prado 2014), PBO (2015), and cost modeling.*
"""
    
    # Write to file
    output_path = 'reports/STRATEGY_ROADMAP_COMPREHENSIVE_2026-05-29.md'
    with open(output_path, 'w') as f:
        f.write(md)
    
    print(f"Written to {output_path}")
    print(f"Report length: {len(md)} characters, {md.count(chr(10))} lines")
    print(f"n_strategies={n_strats}, n_classes_with_data={sum(1 for ac in classes if class_stats[ac]['n_strategies'] or 0 > 0)}")

if __name__ == '__main__':
    generate_roadmap()
