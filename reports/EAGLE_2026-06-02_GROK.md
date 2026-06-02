# EAGLE — Root Cause, Enhancement Plan & Implementation Guide

**Filename:** `EAGLE_2026-06-02_GROK.md`  
**Author:** Grok (Cursor)  
**Date:** 2026-06-02  
**Surfaces:** [`/audit/`](https://findtorontoevents.ca/audit/), [`ai_leaderboard.html`](https://findtorontoevents.ca/audit/ai_leaderboard.html)  
**Companion:** `reports/EAGLE2_2026-06-02_GROK.md` (workstream backlog)  
**NFA.**

---

## Part A — Why there is no profitable strategy per asset class

### A.1 One-sentence root cause

**`/audit` and `ai_leaderboard.html` measure different books with different filters than “capital-ready production edge.”** The main audit book is a **diluted, policy-clean aggregate of hundreds of weak emitters**; the leaderboard page is **stale swarm attribution + backtested MA trends**, neither of which is wired as the sole production emitter with forward proof.

This is **not** “wait longer” for CRYPTO/EQUITY/FOREX. It **is** wait for **ETF** (and lab sleeves) on **forward n≥100**.

---

### A.2 `/audit` — five structural root causes

| # | Root cause | Mechanism | Evidence |
|---|------------|-----------|----------|
| R1 | **Research ≠ production** | Lab Tier-2 sleeves (`etf_dual_momentum`, crypto VWAP/Bollinger) are opt-in sidecars; bulk picks come from `production_scanner`, battleground, regime_terminal, mercury2, tournament overflow | `money_ready_verdict`: CRYPTO PF **0.89** n=374; lab ETF PF **1.60** n=104 not dominant live |
| R2 | **Wrong evidence layer promoted** | Operators see green **Smart/VA/HC** tiles (PF 9–18) while policy-clean CRYPTO is **0.89** | `nav_surface_edge_matrix`: Smart CRYPTO holdout PASS but `why_no_edge` = 67% `mega_mutation` concentration |
| R3 | **Emitter over-breadth** | 88 strategies in funnel, 78 silent; winners “buried” in per-strategy leaderboard, not in class aggregate | Incidents + `dashboard_data.json` leaderboard duplicates (`source=""` inflation) |
| R4 | **Aggregation kills sub-cohort edge** | Tournament models (deepseek_v4) and funnel cells can win; **aggregate** book loses | CRYPTO: battleground 23% of policy-clean volume at PF&lt;1 |
| R5 | **Measurement contamination** | EXPIRED→WON, duplicate signal-ts, TIME_EXIT @ 0 PnL (futures_connors_rsi2) | FOREX: high WR + PF 0.48; disputed CRYPTO cohort |

**Authoritative sizing layer:** `audit_dashboard/data/money_ready_verdict.json` + `pf_registry.json` → `by_asset_class_policy_clean_net`.  
**Today:** **0/9** classes `READY`. CRYPTO + EQUITY `NOT_READY`.

| Class | Policy-clean n | WR | PF | Verdict |
|-------|----------------|-----|-----|---------|
| CRYPTO | 377 | 35.5% | **0.89** | NOT_READY |
| EQUITY | 52 | 26.9% | **0.33** | NOT_READY |
| FOREX | 32 | 28.1% | **0.48** | INSUFFICIENT |
| ETF | 3 | 66.7% | 1.46 | INSUFFICIENT (n) |
| COMMODITY | 4 | 50% | 1.68 | INSUFFICIENT (n) |
| FUTURES | 13 | 15.4% | 0.52 | artifact concentration |
| BOND | 0 | — | — | no sample |

---

### A.3 `ai_leaderboard.html` — separate root causes

The page is **not** the same as main `/audit` production picks. It loads:

1. **`data/ai_leaderboard/ai_leaderboard_index.json`** — built by `tools/ai_attribution/build_ai_leaderboard.py` from **`swarm_picks.json`**, not `at_raw_picks` / Smart Picks.
2. **`data/ma_strategy_leaderboard.json`** — MA trend forward-tracker (yfinance 6y), with on-page disclaimer that high PF is **trend-following shape, not alpha**.

**Live state (2026-06-02 curl):**

| Feed | `generated_at` / `as_of` | Status |
|------|------------------------|--------|
| `ai_leaderboard_index.json` | **2026-05-16** | **1 engine, 5 resolved picks** — stale; not representative |
| `ma_strategy_leaderboard.json` | 2026-05-29 | 8 MA variants, **`n_golden: 0`** — no strategy passes golden gate (pf_oos≥2.5, n≥50, holdout≥1.5) |
| `money_ready_verdict.json` | 2026-06-02 | All classes NOT_READY / INSUFFICIENT |

**Why the page cannot show “profitable per asset class” for production:**

| Issue | Detail |
|-------|--------|
| **Wrong universe** | Swarm book ≠ production scanner book |
| **Stale cron** | Leaderboard index ~17 days old on live FTP |
| **MA section is backtest** | OOS PF looks good (e.g. Classic200 EQUITY oos PF 2.1) but holdout fails (PF 0.71); MC verdict: underperforms B&H Sharpe |
| **n-floor** | `MIN_N_RANKED = 20` — most engines greyed; no Tier-2 (n≥100) |
| **No policy-clean filter** | Does not apply flicker-dedup, resolver fix cohort, or `money_ready` gates |

**Incidents already logged:** P1 “leaderboard shows T1 PF while money_ready NOT_READY”; P2 “ma_strategy_leaderboard empty/stale”.

---

### A.4 Diagram — three books

```
                    ┌─────────────────────┐
                    │  Lab / verified     │  ETF DM Tier-2, crypto WF PASS
                    │  (OHLCV backtest)   │  → NOT dominant in live volume
                    └──────────┬──────────┘
                               │ promotion gate (n>=100 forward)
                               v
┌──────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│ ai_tournament│    │ production_scanner   │    │ swarm_picks.json    │
│ tournament_  │    │ at_raw_picks         │    │ ai_leaderboard.html │
│ picks        │    │ → policy_clean       │    │ (stale, n=5)        │
└──────┬───────┘    │ → money_ready FAIL   │    └─────────────────────┘
       │            └─────────────────────┘
       v                      ↑
  pf.html paper          SIZE HERE ONLY
  (66/81 have opens)     (today: nowhere)
```

---

## Part B — How to handle it (operator rules)

1. **Size only** when `money_ready_verdict.classes[CLASS].verdict == "READY"` (today: never).
2. **Treat `ai_leaderboard.html` as R&D attribution**, not production proof — refresh cron before trusting it.
3. **Treat MA strategy block as defensive overlay research**, not alpha (per page MC banner).
4. **Use pick_funnel for hypothesis discovery**; require concentration + holdout pass before H-register.
5. **Use ai-tournament + pf.html for paper tracking** until tournament feed passes same admissibility pipeline as production.
6. **First expected production win:** ETF dual momentum after `etf_forward_stats.promotion_ready`.

---

## Part C — Enhancement plan (summary)

Full workstreams: **`reports/EAGLE2_2026-06-02_GROK.md`**.

| Phase | Weeks | Deliverable |
|-------|-------|-------------|
| P0 | 1–2 | Capital lock; nav matrix honesty; refresh `ai_leaderboard` + `strategy_admissibility.json` daily |
| P1 | 2–4 | Unified `tools/strategy_admit.py`; block bootstrap; emitter census |
| P2 | 3–8 | ≤3 sleeves/class; ETF + crypto VWAP forward n≥100 |
| P3 | 4–10 | Tournament → virtual book → optional production bridge |

**90-day target:** ≥1 money-ready class (ETF first); CRYPTO aggregate frozen unsized until PF≥1.0 or structural fix.

---

## Part D — Standardized validation pipeline (steps + code)

### D.1 Pipeline steps (mandatory order)

| Step | Action | Artifact |
|------|--------|----------|
| 1 | Pre-register hypothesis | `reports/hypothesis_registry.json` |
| 2 | Load real OHLCV + provenance | `verified_strategies/data_fetcher.py` |
| 3 | Purged + embargo walk-forward | `alpha_engine/rigorous_backtest_harness.py` |
| 4 | Apply asset-class costs | `DEFAULT_COSTS` in harness |
| 5 | DSR / PBO | harness `DSR_PARAMS` |
| 6 | Block bootstrap (optional module) | see D.4 |
| 7 | Regime split | trend × vol cells, min 30 trades |
| 8 | Forward virtual book | `verified_strategies/paper_pilot/*` |
| 9 | Promotion gate | `alpha_engine/verified_promotion_gate.py` |
| 10 | Scanner merge | `alpha_engine/verified_scanner_merge.py` |

### D.2 Example — run rigorous harness (existing)

```bash
# From repo root — single strategy / class
python3 alpha_engine/rigorous_backtest_harness.py \
  --strategy etf_dual_momentum \
  --class ETF

# Batch candidates
python3 alpha_engine/rigorous_backtest_harness.py --batch
```

Core config already in repo:

```python
# alpha_engine/rigorous_backtest_harness.py (excerpt)
DEFAULT_COSTS = {
    "CRYPTO": 0.001,
    "EQUITY": 0.0005,
    "FOREX": 0.0003,
    "ETF": 0.0005,
}
WF_PARAMS = {
    "n_splits": 8,
    "purge_pct": 0.05,
    "embargo_pct": 0.02,
    "min_train": 30,
    "min_test": 10,
}
```

### D.3 Example — walk-forward pilot gate (existing)

```bash
VERIFY_SKIP_FRED=1 python3 verified_strategies/walkforward_suite.py --only pilot
python3 verified_strategies/walkforward_suite.py --only hyro   # crypto VWAP / Bollinger
python3 tools/etf_forward_stats.py
```

### D.4 Example — proposed unified CLI wrapper (`tools/strategy_admit.py`)

```python
#!/usr/bin/env python3
"""Single admissibility gate — EAGLE2 B1."""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "verified_strategies" / "admit_artifacts"


def run(cmd: list[str]) -> int:
    print("+", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", required=True)
    ap.add_argument("--asset-class", required=True)
    ap.add_argument("--hypothesis-id", help="M-107 registry id")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    verdict = {"strategy": args.strategy, "asset_class": args.asset_class, "steps": {}}

    # Step 1 — pre-registration check (manual gate if id missing)
    if not args.hypothesis_id:
        print("WARN: no --hypothesis-id; register in hypothesis_registry.json first")
    verdict["steps"]["preregister"] = bool(args.hypothesis_id)

    # Step 3–5 — rigorous harness
    rc = run([
        sys.executable,
        str(ROOT / "alpha_engine/rigorous_backtest_harness.py"),
        "--strategy", args.strategy,
        "--class", args.asset_class,
    ])
    verdict["steps"]["rigorous_harness"] = rc == 0

    # Walk-forward sleeve key mapping (strategy-specific)
    rc2 = run([
        sys.executable,
        str(ROOT / "verified_strategies/walkforward_suite.py"),
        "--only", "pilot",
    ])
    verdict["steps"]["walkforward"] = rc2 == 0

    verdict["admit"] = all(verdict["steps"].values())
    path = OUT / f"{args.strategy}_{args.asset_class}_admit.json"
    path.write_text(json.dumps(verdict, indent=2), encoding="utf-8")
    print(json.dumps(verdict, indent=2))
    return 0 if verdict["admit"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

Wire production merge only when `admit.json` has `"admit": true` **and** forward stats `promotion_ready`.

### D.5 Example — block bootstrap for trade series (add to harness)

```python
import numpy as np

def block_bootstrap_pf(returns: np.ndarray, block_len: int = 10, n_boot: int = 1000, seed: int = 42) -> dict:
    """Stationary block bootstrap on per-trade returns (not i.i.d. shuffle)."""
    rng = np.random.default_rng(seed)
    n = len(returns)
    if n < block_len + 5:
        return {"pf_lo": None, "pf_hi": None, "note": "insufficient_n"}
    pfs = []
    for _ in range(n_boot):
        idx = []
        while len(idx) < n:
            start = rng.integers(0, max(1, n - block_len))
            idx.extend(range(start, min(start + block_len, n)))
        idx = idx[:n]
        sample = returns[idx]
        wins = sample[sample > 0].sum()
        losses = abs(sample[sample < 0].sum())
        pfs.append(wins / losses if losses > 0 else 10.0)
    pfs = np.array(pfs)
    return {"pf_lo": float(np.percentile(pfs, 5)), "pf_hi": float(np.percentile(pfs, 95))}
```

---

## Part E — Real-time monitoring: concentration & resolver disputes

### E.1 Concentration metrics (per class / surface)

Use fields already in `money_ready_verdict.json` and `pf_registry.json`:

| Metric | Formula / field | **Alert** | **Block sizing** |
|--------|-----------------|-----------|------------------|
| Top symbol share | `top_symbol_share` | **> 0.40** | **> 0.50** |
| Top source share | `top_source_share` | **> 0.50** | **> 0.60** |
| HHI (sources) | \(\sum s_i^2\) on source mix | **> 0.25** | **> 0.35** |
| Single-source artifact flag | `is_single_source_artifact` | `true` | `true` |
| `source_concentration_capped` | verdict field | `false` + share>0.5 | always cap |

**Pick-funnel / nav matrix:** reject `is_edge: true` when `why_no_edge` mentions `concentration=` (already in `nav_surface_edge_matrix.json`).

**Implementation hook:**

```python
# In quality_gates or money_ready_verdict builder
CONCENTRATION_ALERT = {"top_symbol_share": 0.40, "top_source_share": 0.50, "hhi": 0.25}
CONCENTRATION_BLOCK = {"top_symbol_share": 0.50, "top_source_share": 0.60, "hhi": 0.35}

def concentration_gate(class_metrics: dict) -> str:
    if class_metrics.get("is_single_source_artifact"):
        return "BLOCK"
    if class_metrics.get("top_source_share", 0) >= CONCENTRATION_BLOCK["top_source_share"]:
        return "BLOCK"
    if class_metrics.get("top_symbol_share", 0) >= CONCENTRATION_BLOCK["top_symbol_share"]:
        return "BLOCK"
    if class_metrics.get("top_source_share", 0) >= CONCENTRATION_ALERT["top_source_share"]:
        return "ALERT"
    return "OK"
```

### E.2 Resolver dispute metrics

| Metric | How to measure | **Alert** | **Block** |
|--------|----------------|-----------|-----------|
| EXPIRED positive PnL share | % resolved EXPIRED with pnl&gt;0 (14d panel) | **> 30%** of EXPIRED | **> 50%** |
| Duplicate signal-ts rate | duplicate groups / total signals (90d CRYPTO) | **> 5%** | **> 10%** |
| STATUS mismatch | ghost / non-canonical status rows | **> 0** | any |
| TIME_EXIT zero-PnL rate | futures_connors_rsi2-style | **> 20%** of class resolves | **> 40%** |
| Disputed cohort flag | manual + `pick_funnel` DISPUTED banner | active on CRYPTO | active |

**Weekly SQL sketch (ejaguiar1_stocks.at_raw_picks):**

```sql
-- EXPIRED mislabel proxy (FOREX/CRYPTO)
SELECT asset_class,
       COUNT(*) AS n_expired,
       SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) AS expired_positive,
       ROUND(100.0 * SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct
FROM at_raw_picks
WHERE UPPER(status) = 'EXPIRED'
  AND resolved_at >= NOW() - INTERVAL 14 DAY
GROUP BY asset_class;
```

**CI gate:** extend `tools/db_freshness_check.py` with dispute rate thresholds; fail if FOREX `pct` > 50%.

### E.3 Dashboard refresh cadence

| JSON | Generator | Max age |
|------|-----------|---------|
| `money_ready_verdict.json` | `money_ready_verdict.py` | 24h |
| `ai_leaderboard/ai_leaderboard_index.json` | `build_ai_leaderboard.py` | **24h** (today: **stale 17d**) |
| `ma_strategy_leaderboard.json` | `ma_strategy_forward_tracker.py` | 7d |
| `strategy_admissibility.json` | `strategy_admissibility_report.py --write` | 24h |
| `nav_surface_edge_matrix.json` | `build_nav_surface_matrix.py` | 7d |

```bash
# Daily operator bundle
python3 alpha_engine/money_ready_verdict.py --json
python3 -m tools.ai_attribution.build_ai_leaderboard
python3 tools/ma_strategy_forward_tracker.py
python3 tools/strategy_admissibility_report.py --write --fetch-live-portfolios
```

---

## Part F — Mutation testing framework (failed-but-plausible sleeves)

### F.1 When to mutate (not invert)

| Condition | Action |
|-----------|--------|
| Lab PF ≥ 1.5, live PF &lt; 1, n ≥ 30 | **3-axis mutation** |
| Lab PF &lt; 0.8, n ≥ 100 | **Kill** (after export autopsy) |
| OOS inverted PF ≥ 1.3 and orig PF ≤ 0.7 | **Invert trial** (single strategy ticket) |

### F.2 Tools (already in repo)

```bash
# Step 0 — export closed picks / use JSON
python3 tools/mutation_analysis.py --json \
  --min-trades 5 \
  --dir-spread 20 \
  --tf-spread 15 \
  --sym-spread 30 \
  -o reports/mutation_analysis_$(date -u +%Y%m%d).txt \
  --matrix-csv mutation_artifacts/compat_matrix.csv

# Build symbol gates for quality_gates.py
python3 tools/matrix_rules_from_csv.py \
  -i mutation_artifacts/compat_matrix.csv \
  -o alpha_engine/data/matrix_symbol_gates.json
```

**Axes:** symbol allowlist, direction (`long_only`/`short_only`), timeframe bucket — see `docs/MUTATION_THREE_AXIS_PROTOCOL.md`.

### F.3 Lab sleeve mutation workflow (Faber / carry / sector mom)

```bash
# 1. Register variant as new hypothesis (M-107)
# 2. Re-run lab with one axis changed
VERIFY_SKIP_FRED=1 python3 verified_strategies/run_phase2.py  # or targeted runner

# 3. Walk-forward
python3 verified_strategies/walkforward_suite.py --only pilot

# 4. Shadow in scanner (no merge)
FABER_TAA_ENABLED=shadow python3 -c "
from alpha_engine.verified_scanner_merge import merge_verified_sidecars_into_active
merge_verified_sidecars_into_active([])
"

# 5. Compare forward pilot JSON vs baseline
python3 tools/pilot_forward_dashboard.py
```

### F.4 Automated mutation candidate script (proposed)

```python
#!/usr/bin/env python3
"""Flag sleeves for 3-axis mutation from lab vs live divergence."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
lab = json.loads((ROOT / "verified_strategies/MULTI_CLASS_LAB_REPORT.json").read_text())
live = json.loads((ROOT / "audit_dashboard/data/money_ready_verdict.json").read_text())

candidates = []
for item in lab.get("tier2_pass", []) + list(lab.get("best_per_class", {}).values()):
    if not isinstance(item, dict):
        continue
    ac = item.get("asset_class")
    lab_pf = (item.get("stats") or {}).get("pf", 0)
    live_row = live.get("classes", {}).get(ac, {})
    live_pf = live_row.get("pf", 0)
    if lab_pf >= 1.5 and live_pf < 1.0:
        candidates.append({
            "asset_class": ac,
            "strategy": item.get("strategy"),
            "lab_pf": lab_pf,
            "live_pf": live_pf,
            "action": "MUTATE_3_AXIS",
        })
print(json.dumps(candidates, indent=2))
```

Save as `tools/mutation_candidates_from_lab_live.py` in a follow-up PR.

### F.5 Recommended tool stack

| Tool | Role |
|------|------|
| `tools/mutation_analysis.py` | Production closed-pick autopsy |
| `tools/matrix_rules_from_csv.py` | Symbol gates → `quality_gates.py` |
| `verified_strategies/walkforward_suite.py` | OOS gate after mutation |
| `tools/h102_connors_rsi2_crypto.py` | Harness template for crypto sleeves |
| `alpha_engine/rigorous_backtest_harness.py` | DSR/PBO/purged WF |

**Do not use** blanket `strategy_mutator.py` invert until `mutation_analysis.py` shows direction spread &gt; 20pp.

---

## Part G — `ai_leaderboard.html` specific fixes

| ID | Fix | Command / file |
|----|-----|----------------|
| L1 | Cron daily `build_ai_leaderboard.py` | Add to `.github/workflows/audit-dashboard.yml` or `verified-pilot-daily.yml` |
| L2 | Banner: “Swarm attribution — not money-ready production” | `audit_dashboard/ai_leaderboard.html` |
| L3 | Cross-link `money_ready_verdict` per class | Fetch JSON in page script; grey out engines when class NOT_READY |
| L4 | Refresh `ma_strategy_forward_tracker.py` weekly | `n_golden` must be &gt; 0 to show “golden” section |
| L5 | Do not conflate MA OOS PF with live PF | Keep MC disclaimer prominent |

---

## Part H — Immediate commands

```bash
python3 tools/strategy_admissibility_report.py --write --fetch-live-portfolios
python3 tools/run_verified_pilots_daily.py
python3 -m tools.ai_attribution.build_ai_leaderboard
python3 alpha_engine/money_ready_verdict.py --json

# Portfolio sanity
curl -s 'https://findtorontoevents.ca/audit/data/pf_portfolio_deepseek_v4__aggressive.json' \
  | python3 -c "import sys,json;d=json.load(sys.stdin);print(len(d.get('positions',[])),'open positions')"
```

---

## References

- `reports/EAGLE_JUNE2_GROK.md` — diagnosis
- `reports/EAGLE2_2026-06-02_GROK.md` — workstreams
- `reports/EAGLE_JUNE2_COMPOSER.md` — peer review variant
- `tools/ai_attribution/build_ai_leaderboard.py` — leaderboard data source
- `docs/BACKTESTING_GUIDE.md`, `docs/MUTATION_THREE_AXIS_PROTOCOL.md`

---

**Final answer:** Lack of profitable per-class strategies on `/audit` is a **deployment and measurement problem**, not a missing alpha problem. `ai_leaderboard.html` adds **stale swarm data + non-alpha MA backtests** on top — fix refresh cadence and unify evidence layers before expecting the UI to show capital-ready winners.