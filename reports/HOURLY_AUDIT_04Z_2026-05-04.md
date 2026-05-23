# Hourly Audit — 2026-05-04T04Z

**Generated:** 2026-05-04T04:24Z  
**Dashboard snapshot:** 2026-05-04T03:43:55Z (`meta.generated_at`)  
**Analyst:** Claude Sonnet 4.6 (automated hourly check)  
**Prior audit:** PR #771 (03Z — merged this hour)

---

## 1. Dashboard Refresh Status

Dashboard data pulled from `audit_dashboard/data/dashboard_data.json` via `git pull --rebase origin main`. Snapshot lag ~40 min from analysis time. Pool size: **n=3500** recent_closed picks.

---

## 2. Per-Asset Windowed Metrics

Analysis run at 2026-05-04T04:24Z. All windows computed from `picks.recent_closed[*].closed_at`.

| CLASS     | 24h PF | 24h WR  | 24h n | 7d PF | 7d WR  |  7d n | 30d PF | 30d WR  | 30d n |
|-----------|-------:|--------:|------:|------:|-------:|------:|-------:|--------:|------:|
| CRYPTO    |   1.21 |  47.8%  |    67 |  1.29 |  46.0% |   670 |   1.40 |  47.4%  |  1206 |
| EQUITY    |   0.00 |   0.0%  |     0 |  1.09 |  50.0% |    32 |   3.36 |  67.3%  |   107 |
| FOREX     |   1.56 |  50.0%  |     8 |  0.45 |  22.5% |    71 |   0.64 |  29.4%  |    85 |
| COMMODITY |   0.00 |   0.0%  |     0 |  1.19 |  40.0% |    30 |   0.95 |  35.3%  |    34 |
| ETF       |   0.00 |   0.0%  |     0 |  1.57 |  62.5% |     8 |   4.06 |  77.8%  |    36 |
| BOND      |   0.00 |   0.0%  |     0 |  0.00 |   0.0% |     0 |   0.00 |   0.0%  |     0 |

### Long-run (asset_class_health, post-resolver-v2)

| CLASS     | PF   | WR    |
|-----------|------|-------|
| EQUITY    | 1.42 | 53.0% |
| COMMODITY | 1.78 | 46.9% |
| CRYPTO    | 1.25 | 44.5% |
| ETF       | 1.24 | 55.2% |
| FOREX     | 0.27 | 46.3% |

---

## 3. Delta vs Baselines

Baselines from task prompt (CLAUDE.md / issue #686 / issue #693). Prior-hour values from PR #771 (03Z).

| CLASS     | Window | Baseline | 03Z    | 04Z    | Delta (03Z→04Z) | Signal |
|-----------|--------|----------|--------|--------|-----------------|--------|
| CRYPTO    | 24h    | 3.54     | 0.90   | 1.21   | +0.31           | ↑ recovering; below baseline (regime noise) |
| CRYPTO    | 7d     | 1.33     | —      | 1.29   | ≈ stable        | ✅ on floor |
| CRYPTO    | 30d    | 1.33     | —      | 1.40   | +0.07           | ✅ improving |
| EQUITY    | 7d     | 0.87     | 1.09   | 1.09   | =               | ✅ goldmine_6x kill holding |
| EQUITY    | 30d    | 2.18     | 3.31   | 3.36   | +0.05           | ✅ Tier-1 intact |
| FOREX     | 7d     | 0.14     | 0.45   | 0.45   | =               | 🟡 improving but sub-floor |
| FOREX     | 30d    | 0.97     | —      | 0.64   | ↓ deteriorating | 🔴 30d window catching recent kills |
| COMMODITY | 30d    | 1.78 LR  | 0.81   | 0.95   | +0.14           | 🟡 edge decay — monitor |
| ETF       | 7d     | —        | —      | 1.57   | —               | ✅ T2-candidate (n=8, small) |

### CRYPTO 24h Note
24h dip to 0.90 in 03Z now partially recovered to 1.21 — consistent with intraday noise pattern. 7d/30d stable. PR #694 (quan_engine HYPEUSDT block) expected to improve both 7d and 30d over next 72h as HYPEUSDT trades roll off.

### EQUITY Note (issue #693 monitor)
7d PF held at 1.09 (confirmed from 03Z). 30d Tier-1 (PF 3.36 / WR 67.3%). Issue #693 criterion: "If EQUITY 14d returns to PF >= 1.5 within 7 days post-#692 → kill was sufficient." Monitor 14d window — not yet in this dataset (n only 32 in 7d, 107 in 30d). Next check: 72h.

### FOREX Note
30d continuing to deteriorate (0.97 → 0.64) as the pre-#687 JPY-cross disaster trades scroll into the 30d window. Expected: 30d will continue to fall for ~7 more days before pre-kill trades age out. Monitor; do not act on this mechanical deterioration.

---

## 4. Strategy Attribution

### FOREX 7d (n=71)

| Strategy                          | n  | WR    | PF   |
|-----------------------------------|----|-------|------|
| forex_rsi2_mean_reversion         | 45 | 11.1% | 0.13 |
| unknown                           | 10 | 50.0% | 1.49 |
| fx_smart_carry_trade_momentum     |  8 | 12.5% | 0.24 |
| combined_confidence               |  4 | 75.0% | 3.79 |
| fx_smart_forex_rsi2_mean_reversion|  2 |100.0% | inf  |
| forex-rsi-ema-scout               |  2 |  0.0% | 0.00 |

`forex_rsi2_mean_reversion` (n=45, WR 11.1%) — confirmed dominant killer, sole P1 kill candidate per 03Z findings. `forex_carry_momentum` absent from 7d (PR #692 kill effective). `fx_smart_carry_trade_momentum` (n=8, WR 12.5%) — sub-floor; watch for n≥20.

### EQUITY 7d (n=32)

| Strategy               | n  | WR    | PF    |
|------------------------|----|-------|-------|
| stocks_rsi2_pullback   | 14 | 35.7% | 0.89  |
| mtf-align-scout        |  4 | 75.0% | 2.17  |
| macd-hidden-div-scout  |  4 | 50.0% | 0.61  |
| goldmine_5x_consensus  |  4 | 75.0% |12.54  |
| adx-trend-scout        |  2 | 50.0% | 1.30  |
| rs-breakout-scout      |  2 | 50.0% | 1.60  |
| quality-momentum-scout |  1 |100.0% | inf   |
| price-accel-scout      |  1 |  0.0% | 0.00  |

`goldmine_6x_consensus` absent (PR #692 kill confirmed). `stocks_rsi2_pullback` (n=14, WR 35.7%) — still dragging; n below 20 threshold so no kill action yet. Watch.

### CRYPTO 7d — top 10 strategies (n=670 total)

| Strategy                                  | n   | WR    | PF   |
|-------------------------------------------|-----|-------|------|
| luxalgo_confluence                        | 150 | 52.7% | 1.71 |
| st_fear_greed_contrarian                  |  81 | 66.7% | 2.57 |
| unknown                                   |  78 | 12.8% | 0.34 |
| ensemble                                  |  28 | 25.0% | 0.61 |
| crypto_mtf_ema_slope_alignment_v1         |  26 | 53.8% | 1.39 |
| MeanReversionBB                           |  24 | 75.0% | 6.36 |
| claude_ml_moderate_mut                    |  23 | 60.9% | 2.44 |
| crypto_kalman_trend_residual_reversion_v1 |  21 | 76.2% | 2.60 |
| signal_engine_momentum_mut                |  10 | 30.0% | 0.83 |
| vwap_deviation_reversion_sol_v1           |  10 | 70.0% | 3.38 |

`unknown` (n=78, WR 12.8%, PF 0.34) — 7% volume drag at PF 0.34 (consistent with issue #686 baseline). `ensemble` (n=28, WR 25.0%, PF 0.61) — P2 watch; n≥20 but WR not yet ≤35% sustained across multiple audits.

---

## 5. Mutation Analysis — New Findings

Run: `python tools/mutation_analysis.py --json` at 04:24Z.

### Already posted to issue #686 (03Z audit)
- `quan_engine×ONDOUSDT`: n=31, WR 16.1% (in WORST list confirmed)
- `rapid_fire×UUSDT`: n=34, WR 0% (confirmed)

### NEW this hour — directional strategy kills

| Strategy                      | Direction | n   | WR    | Action |
|-------------------------------|-----------|-----|-------|--------|
| myfxbook_retail_contrarian    | LONG      |  72 | 12.5% | **P1** — n≥20, WR<35%, sustained. Post to #686. Mutation/inverse tests before kill. |
| ig_contrarian_sentiment       | LONG      |  90 | 25.6% | **P2** — n≥20, WR<35%. Post to #686. |
| quan_engine_swing             | LONG      | 104 | 26.0% | **P2** — n≥20, WR<35%. Note: SHORT WR 60% (n=5 — too small). |
| forex_rsi2_mean_reversion     | LONG      |  46 |  4.3% | **P1** — catastrophic. Already in kill pipeline (full strategy, not direction-only). |

### Symbol-level variance (new signals)
- `rapid_fire×TAOUSDT`: n=18, WR 5.6% — below n=20 floor; monitor
- `multi_asset_copytrader` WORST: SI=F (0%), AMD (0%), ZW=F (0%) — symbol-allowlist mutation candidate (sandbox first)

**Constraint check:** None of the new P1/P2 candidates match existing `BLOCKED_ASSET_STRATEGY_PAIRS` patterns. All require 3+ AI consensus before kill per CLAUDE.md. No auto-kill action taken.

---

## 6. PR Triage

### Open PRs (total: 4)

| PR  | Title                              | CI               | Mergeable | Reviews                  | Action |
|-----|------------------------------------|------------------|-----------|--------------------------|--------|
| #771 | audit: hourly 03Z               | scan=✅           | clean     | Codex COMMENTED only     | **MERGED** this hour |
| #772 | feat(b9): adversarial shadow    | test(3.11)=❌    | —         | Body: DO NOT ADMIN-MERGE | **HOLD** |
| #769 | feat(personas): batch B         | scan+drift=✅    | **dirty** | Codex COMMENTED only     | **HOLD** (merge conflict) |
| #764 | feat(b5): concept scorer        | test(3.12)=❌    | —         | Codex COMMENTED only     | **HOLD** (CI failure) |

### HOLD set (permanent — never merge)
#660, #658, #681, #661 — Plan v2.1 fabricated stats family. Not appearing in open PRs (previously closed or never opened under these numbers in current state).

### Author-rebase check
PRs #669, #676 — **already merged** (confirmed via API: #669 merged 2026-05-02, #676 merged 2026-05-03). Remaining named PRs (#608, #665, #644, #597, #615, #655) not in open PR list → all closed/merged. No pending author-rebase actions.

---

## 7. Issue Status

| Issue | Status | Action |
|-------|--------|--------|
| #685 | Open — resolver-rescope DONE | No action. Auto-close any PR claiming "widen re-resolve scope." |
| #686 | Open — quality regression tracker | Posting new P1: `myfxbook_retail_contrarian` LONG (n=72, WR 12.5%) + P2: `ig_contrarian_sentiment` LONG (n=90, WR 25.6%) |
| #693 | Open — EQUITY 7d/14d/30d monitor | 7d PF held at 1.09 (stable from 03Z). 30d PF 3.36 — Tier-1 intact. goldmine_6x kill sufficient so far. Monitor 14d at next 72h checkpoint. |

---

## 8. Summary

**Merged:** #771 (audit 03Z)  
**New findings:** 2 new P1/P2 directional kill candidates for issue #686  
**Held:** #769 (conflict), #764 (CI fail), #772 (explicit hold)  
**Goal #1 trajectory:** EQUITY Tier-1 holding; FOREX recovering slowly post-kills; CRYPTO 24h noise, 7d/30d stable.
