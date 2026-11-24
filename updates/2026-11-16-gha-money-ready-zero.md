# Money-Ready Verdict: 0/9 Asset Classes Money-Ready — RCA

**File:** `updates/2026-11-16-gha-money-ready-zero.md`
**Generated:** 2026-11-16
**Repo:** eltonaguiar/findtorontoevents_antigravity.ca (worktree: ghactions-v4)
**Source artifacts:** `audit_dashboard/data/money_ready_verdict.json`, `audit_dashboard/data/audit_surface_truth.json`

## Summary

The Money-Ready verdict surface shows **0/9 asset classes money-ready** (`money_ready: []`, `watch: [COMMODITY]`). Every canonical asset class fails at least one hard gate. The root cause is not a single bug — it is that every class with enough data (n≥100) fails the profit-factor ≥1.5 gate, and most also fail the win-rate sanity floor, DSR, SPA, expectancy, and/or MDD/CVaR tail-risk gates. Classes with too few picks (n<100) short-circuit to `INSUFFICIENT_DATA`.

## Money-Ready Gates (alpha_engine/money_ready_verdict.py)

| Gate | Threshold | Notes |
|------|-----------|-------|
| n_ok | n ≥ 100 | `MIN_N_CLASS` (Tier-2 charter) |
| wr_ok | per-class floor | `CLASS_WR_FLOORS`: CRYPTO 50%, FOREX 40%, COMMODITY 40%, FUTURES 40%, ETF 45%, BOND 45%, EQUITY 52% |
| pf_ok | PF ≥ 1.5 | `MIN_PF` |
| dsr_ok | DSR ≥ 0.95 | `DSR_THRESHOLD` |
| pbo_ok | PBO ≤ 0.55 | `PBO_THRESHOLD` (≥5 strategies required for power) |
| spa_ok | SPA p ≤ 0.10 | `SPA_ALPHA` (≥1 strategy with n≥20 required) |
| expectancy_ok | E > 0 net of slippage | `SLIPPAGE_GATE_ENABLED=1` (ENFORCED, monotone downgrade only) |
| mdd_cvar_gate_ok | MDD ≤ cap + \|CVaR\| < 10% | `MDD_GATE_ENFORCE=1` (ENFORCED); COMMODITY MDD cap 55% |
| recency_ok | ≥1 pick closed in last 14d | Shadow — informational only |

Verdict logic (`_verdict`, line 1172): n<100 → `INSUFFICIENT_DATA`; not recent → `NOT_READY`; if wr_ok & pf_ok & (dsr_ok or spa_ok) & (pbo_ok or spa_ok) → concentration/slippage/MDD/FDR/single-source checks → `MONEY_READY`; if pf<1.0 → `NOT_READY`; if wr_ok or pf_ok → `WATCH`; else `NOT_READY`.

## Per-Class Failure Analysis

### CRYPTO — NOT_READY
- n=3716 (n_ok ✅), WR=35.76% (wr_ok ❌ <50%), PF=0.9163 (pf_ok ❌ <1.5)
- DSR=0.00 ❌, PBO=0.00 ✅ (83 eligible strategies), SPA p=0.00 ✅ (30 pass)
- Expectancy=-0.0581 ❌ (after 15bps slippage), MDD=1.0009 ❌ (100% drawdown!), CVaR=-95.6% ❌
- Top source UNKNOWN at 99.6% share (source concentration capped)
- ml_enhanced quarantine: 520 picks excluded (shadow only, ML_ENHANCED_CRYPTO_QUARANTINE=1 set in GHA)
- **Fails:** WR, PF, DSR, expectancy, MDD, CVaR
- **Action:** Fix null PnL backfill (`tools/backfill_resolved_pnl.py`); grow inverse_ml ADA/feature sleeves to forward n=100; kill/mutate emitters driving UNKNOWN-source concentration; the 100% MDD means the class has suffered total loss — do not size real money.

### FOREX — NOT_READY
- n=612 (n_ok ✅), WR=32.19% (wr_ok ❌ <40%), PF=0.6596 (pf_ok ❌ <1.5)
- DSR=0.0009 ❌, PBO=null (only 1 eligible strategy), SPA p=0.47 ❌
- Expectancy=-0.0022 ❌, MDD=0.9036 ❌ (90% drawdown), CVaR=-5.86% ✅
- Top source UNKNOWN at 89.5% share
- **Fails:** WR, PF, DSR, SPA, expectancy, MDD
- **Action:** `audit_surface_truth.json` bridge_action: **"FAIL — mutate or kill emitters; no real money"**. FOREX is a loss-making book (PF 0.66). Mutate or kill all FOREX emitters until a clean ledger demonstrates PF≥1.5 on n≥100.

### EQUITY — NOT_READY
- n=250 (n_ok ✅), WR=59.2% (wr_ok ✅ ≥52%), PF=0.9392 (pf_ok ❌ <1.5)
- DSR=0.0 ❌, PBO=null (1 eligible strategy), SPA p=0.468 ❌
- Expectancy=0.0071 ✅ (positive after 10bps slippage), MDD=0.9999 ❌ (~100% drawdown), CVaR=-6.56% ✅
- Only 1 eligible strategy for PBO/SPA/FDR
- **Fails:** PF, DSR, SPA, MDD
- **Action:** `audit_surface_truth.json` bridge_action: **"FAIL — mutate or kill emitters; no real money"**. EQUITY passes WR and expectancy but PF<1.5 means gross losses exceed gross wins. Fix the losing emitters; the MDD near 1.0 indicates a catastrophic drawdown in the equity curve.

### COMMODITY — WATCH (closest to ready)
- n=229 (n_ok ✅), WR=40.17% (wr_ok ✅ ≥40%), PF=1.0256 (pf_ok ❌ <1.5)
- DSR=0.0001 ❌, PBO=null (0 eligible strategies), SPA=null (no strategies n≥20)
- Expectancy=-0.0012 ❌ (marginally negative after 12bps slippage), MDD=0.1748 ✅ (under 55% CTA cap), CVaR=-3.66% ✅
- policy_clean_n=14 (only 14 picks survive policy cleaning vs 229 intrabar)
- **Fails:** PF, DSR, expectancy
- **Passes:** WR, MDD/CVaR
- **Action:** `audit_surface_truth.json` bridge_action: **"SUB_TIER2 — forward paper until n≥100 and PF≥1.5"**. COMMODITY is the only class with a WATCH verdict. The PF gap (1.03 vs 1.50 required) is small but real; expectancy is marginally negative. Forward paper trade until clean n≥100 and PF≥1.5.

### FUTURES — INSUFFICIENT_DATA
- n=52 ❌ (<100), WR=42.31% (wr_ok ✅ ≥40%), PF=1.0936 (pf_ok ❌ <1.5)
- Recency stale: last pick 247.3 days ago (2026-03-13)
- DSR=0.5792 ❌, MDD=0.1378 ✅, CVaR=-4.77% ✅
- **Fails:** n, PF, recency
- **Action:** Forward paper until n≥100 and PF≥1.5; the class is effectively dormant — investigate why FUTURES emission stopped.

### ETF — INSUFFICIENT_DATA
- n=45 ❌ (<100), WR=2.22% (wr_ok ❌ <45%), PF=0.0216 (pf_ok ❌ <1.5)
- Recency stale: last pick 2.58 days ago (borderline, within 14d but past 48h)
- Expectancy=-0.0256 ❌
- Top source `institutional_picks_engine` at 60% share
- **Fails:** n, WR, PF, expectancy
- **Action:** `audit_surface_truth.json` bridge_action: **"FAIL — mutate or kill emitters; no real money"**. ETF WR of 2.2% is catastrophic — almost every pick loses. Kill or rewrite ETF emitters.

### MEME — INSUFFICIENT_DATA
- n=10 ❌ (<100), WR=10%, PF=0.0234
- No date field found in picks (recency unknown)
- MDD=0.4936 ❌, CVaR=-13.85% ❌
- **Fails:** n, WR, PF, MDD, CVaR, recency (no dates)
- **Action:** "no class-level sizing; paper-pilot only" — MEME is a gambling book, not investable.

### PENNY_STOCK — INSUFFICIENT_DATA
- n=4 ❌ (<100), WR=50%, PF=0.1779
- No date field found in picks
- **Fails:** n, PF
- **Action:** "no class-level sizing; paper-pilot only"

### BOND — INSUFFICIENT_DATA
- n=1 ❌ (<100), WR=0%, PF=0.0
- Recency stale: last pick 5.56 days ago (2026-11-10)
- policy_clean_n=1, top_symbol TLT at 100% share
- **Fails:** n, WR, PF, recency
- **Action:** "no class-level sizing; paper-pilot only" — BOND is emitting one pick via `bond_duration_rotation`; not enough data for any statistical test.

## Score Booster Calibration — Is It Applied in Production?

**Yes.** `_calibrate_confidence(conf, asset_class)` at `alpha_engine/score_booster.py:672` is wired into `run_score_booster()` at line 1472:

```python
cal = _calibrate_confidence(raw_conf, asset_class)
if abs(cal) > 0.01:
    pick["_conf_calibration"] = round(cal, 3)
    new_score = max(0, min(100, int(old_score + cal)))
```

It applies per-pick score adjustments to **active picks** based on confidence inversion bands:
- CRYPTO: conf>0.85 → -12, conf 0.50-0.60 → +3
- EQUITY: conf 0.85-0.90 → -15, conf>0.90 → +5
- FOREX: conf≥0.85 → -10, conf 0.55-0.65 → +3 to +5
- COMMODITY: conf≥0.85 → -8, conf 0.55-0.70 → +3

**However, this calibration does NOT fix the money_ready problem.** It only adjusts the display `score` on active (unresolved) picks. The money_ready verdict reads from closed/resolved picks (`closed_picks.json` via the `build_pf_registry` pipeline) and gates on WR, PF, DSR, SPA, PBO, expectancy, and MDD — none of which are altered by score_booster calibration. The calibration is a display/ranking fix, not a statistics fix.

## Actionable Fixes Per Class (Which Emitters to Fix/Mutate/Kill)

| Class | Verdict | Primary fix | Emitters to target |
|-------|---------|-------------|-------------------|
| CRYPTO | NOT_READY | Fix null PnL backfill; grow inverse_ml ADA/feature sleeves; kill UNKNOWN-source concentration | `ml_enhanced_*` family (520 picks quarantined), claude_gainer_st concentration |
| FOREX | NOT_READY | **Mutate or kill all emitters** — loss-making book | All FOREX emitters (PF 0.66, WR 32%) |
| EQUITY | NOT_READY | **Mutate or kill losing emitters** — PF<1.5 despite good WR | Equity emitters producing gross losses |
| COMMODITY | WATCH | Forward paper to n≥100, PF≥1.5 | CT=F concentration guard already applied (-8 score) |
| FUTURES | INSUFFICIENT_DATA | Restart emission; forward paper to n≥100 | FUTURES emitter pipeline (dormant since March 2026) |
| ETF | INSUFFICIENT_DATA | **Mutate or kill emitters** — WR 2.2% | `institutional_picks_engine` (60% share) |
| MEME | INSUFFICIENT_DATA | Paper-pilot only — no class-level sizing | MEME emitters (gambling book) |
| PENNY_STOCK | INSUFFICIENT_DATA | Paper-pilot only — no class-level sizing | Penny stock emitters |
| BOND | INSUFFICIENT_DATA | Paper-pilot only — no class-level sizing | `bond_duration_rotation` (1 pick) |

## Cross-Cutting Issues

1. **Null PnL backlog:** `audit_surface_truth.json` reports 278 null-pnl resolved picks; run `tools/backfill_resolved_pnl.py` after the `ejaguiar1_backups` archive.
2. **Source concentration:** CRYPTO (UNKNOWN 99.6%), FOREX (UNKNOWN 89.5%), EQUITY (UNKNOWN 97.1%) — most resolved picks come from an unidentified source, making DSR/SPA results reflect a single source's idiosyncrasies, not class-level edge.
3. **MDD/CVaR:** CRYPTO (100% MDD, -95% CVaR), FOREX (90% MDD), EQUITY (~100% MDD) — catastrophic drawdowns that the MDD gate (ENFORCED via `MDD_GATE_ENFORCE=1` in GHA) correctly blocks.
4. **PBO/SPA underpowered:** Most classes have <2 eligible strategies with n≥20, so PBO/SPA return null — statistical overfit testing cannot run.

## Documentation Location

`/home/eaguiar2015/findtorontoevents_antigravity.ca/.kilo/worktrees/ghactions-v4/updates/2026-11-16-gha-money-ready-zero.md`
