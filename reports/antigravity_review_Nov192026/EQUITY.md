# EQUITY — Asset Class Deep-Dive Review

**Report date:** 2026-11-22
**Verdict: WEAK** (keep observing — no claim yet)
**Source surface:** findtorontoevents.ca/audit3 (2026-11-22 build) — cross-checked with local ledger and dashboard.

---

## 1. Current state

| Metric | Live audit3 (2026-11-22) | Local ledger (2026-11-20) |
|---|---|---|
| n | 956 | 942 |
| Win rate | 44.8% [41.6, 47.9] | 45.0% |
| Net expectancy / trade | −0.04% (n=731) | +0.16% |
| Selection alpha | +0.11% | −0.005% |
| Profit factor | 1.05 | 1.076 |
| DSR | 0.005 (live) / 0.011 (local) | |
| Verdict | **WEAK** | **WEAK** |

Dashboard `asset_class_health` (2026-10-19): status=`watch`, n=463, WR=55.3%, PF=0.88, sizing not allowed.

---

## 2. Statistical gate status

| Gate | Result | Notes |
|---|---|---|
| G0 | ✔ n=956 | |
| G1 | ⚠ borderline — net CI [−0.42, +0.33] straddles 0 | no clean edge |
| G2 | ⚠ CI not excluded from 0 | |
| G4 | DSR ~0.005–0.011 → fails (needs ≥0.95) | gross overfit risk |
| G5 | ⚠ split-half not both positive | |
| G6 | passes — no concentration breach | |
| G7 | ⚠ borderline after slippage | |
| G8 | n/a | |

**Key insight:** EQUITY is the **only class with positive selection alpha** (+0.11% live). That means picks at least keep pace with holding the same US equity — rare in this book. But net expectancy CI still includes 0, so no actionable edge yet.

---

## 3. Kill list (symbol)

| Symbol | n | WR | Net expectancy | PF |
|---|---|---|---|---|
| UBER | 28 | 28.6% | −1.10% | 0.52 |

---

## 4. Recency

| Panel | WR | PF |
|---|---|---|
| 14d | 28.3% | 0.63 |
| 48h | 39.0% | 1.07 |

⚠ **Recency is deteriorating**: 14d WR 28.3% (PF 0.63) is a sharp drop vs the 45% lifetime WR. The 48h recovery (39% / PF 1.07) is not enough to clear. Watch this class for a 14d flip to outright negative.

---

## 5. What has promise (audit2)

| Pod | Status | Evidence |
|---|---|---|
| POD-EQUITY-BREAKOUT | **pre_registered** | EQUITY OOS Sharpe +0.61 (33 folds), ETF +0.21 (53 folds); ~364 resolved trades net +0.46% |
| POD-FABER-TAA | observe | SPY n=11 Sharpe 1.74; QQQ n=7 Sharpe 1.65; **0 ETF closes in forward pilot** |
| POD-ETF-DUAL-MOMENTUM | observe | 12-1 sector-vs-SPY, lab WF PASS (OOS PF 2.75), but 0 forward closes (winner-stays bug) |

---

## 6. Recommendation

1. **Keep observing — do not kill.** EQUITY is the only class with positive selection alpha; kill verdicts here are symbol-specific, not class-wide.
2. **Do not size up yet** — net CI overlaps 0; rare 2× cost stress.
3. **Rescue:** EQUITY-BREAKOUT is the single `pre_registered` confirmatory pod in the whole book; it only needs its own closed forward rows (n≥100) to potentially promote. Fix the FABER-TAA / DUAL-MOMENTUM forward-pilot zero-close bugs so a 12-1 sector momentum sleeve can be judged.
4. **Recency flag:** if the 14d WR stays <30% for two consecutive builds, elevate to a WATCH/kill-review.

---
*Not investment advice. Data: audit3 ledger, dashboard panels, audit2 pods. Generated 2026-11-22.*
