# CRYPTO — Asset Class Deep-Dive Review

**Report date:** 2026-11-22
**Verdict: KILL** (class aggregate)
**Source surface:** findtorontoevents.ca/audit3 (Quant Kill Tribunal ledger, 2026-11-22 build) — cross-checked against local `audit_dashboard/data/audit3_ledger.json` (2026-11-20 build) and `dashboard_data.json` (asset_class_health).

---

## 1. Current state

| Metric | Live audit3 (2026-11-22) | Local ledger (2026-11-20) |
|---|---|---|
| n (closed picks in ledger) | 6,926 | 6,874 |
| Win rate | 39.4% [38.2, 40.5] | 40.2% |
| Net expectancy / trade | −0.55% (n=1,674) | −0.316% |
| Selection alpha | −0.42% | −0.371% |
| Profit factor | 0.79 | 0.834 |
| DSR | 0.000 | 0.000 |
| Verdict | **KILL** | **KILL** |

Dashboard `asset_class_health` (2026-10-19 snapshot, stale): status=`stressed`, n=19,621, WR=45.7%, PF=0.289, sizing not allowed, intrabar-truth WR=35.5% / PF=0.881.

**Readiness gate (money_ready_verdict, 2026-11-20):** BLOCKED/MONITORING, below T2. Intrabar truth: WR=35.8%, PF=0.917 (n=3,726). Daily-vs-intrabar inflation is **0.29×** on PF (data is inflated by ~3.4× without intrabar-touch truth).

---

## 2. Statistical gate failure

| Gate | Requirement | CRYPTO result |
|---|---|---|
| G0 sample floor | n≥20 / ≥100 | ✔ (n=6,926) |
| G1 edge direction | Net-expectancy bootstrap CI must exclude 0 | ✘ CI [−0.58, −0.08], entirely below 0 |
| G2 net expectancy | 95% CI excludes 0 after slippage | ✘ |
| G3 multiplicity | BH q ≤ 0.1 | q=1.000 (fails) |
| G4 overfit | Deflated Sharpe ≥ 0.95 | DSR = 0.000 (fails) |
| G5 stability | Split-half both means > 0 | ✘ first −0.27%, second −0.36% |
| G6 concentration | No source >90%; symbol >60% | Top source 58.1%; top symbol 8.4% (passes) |
| G7 cost realism | Net PnL > 0 after slippage | ✘ |
| G8 forward | PROVEN_T2 only on own closed forward rows | n/a |

**Root cause (quantitative):** net expectancy CI entirely below zero at 2× slippage too; alpha is deeply negative; the strategy cohort has no real edge and is dominated by beta. `beta_dominant=true`.

---

## 3. Recency (14d / 48h)

| Panel | Source | WR | PF |
|---|---|---|
| 14d | pick_summary_stats_14d.json (2026-11-20) | 46.6% | 1.10 |
| 48h | pick_summary_stats_48h.json (2026-11-20) | 52.1% | 1.49 |
| Ledger recency | audit3 ledger window (25% of trades) | window net mean −0.72% (n=1,718) |

Note: 14d/48h panels show a *recent* improvement, but the ledger's recency window (which uses the honest resolver) is still **negative** (−0.72%/trade). The two panels disagree because they use different denominators (publishing dashboard raw vs canonical resolved view). Treat the ledger recency as the trustworthy figure.

---

## 4. Kill list (strategy + symbol level)

**Strategies killed (CRYPTO):**
| Strategy | n | WR | Net expectancy | PF |
|---|---|---|---|---|
| stochrsi_macd_combo (LONG) | 145 | 25.5% | −1.04% | 0.42 |
| MomentumEMA (LONG) | 73 | 6.9% | −1.81% | 0.07 |
| crypto_signal_engine (LONG) | 49 | 8.2% | −1.01% | 0.19 |
| strong consensus alpha_engine/kimi (LONG) | 24 | 25.0% | −2.41% | 0.18 |
| altseason-rotation-scout (LONG) | 20 | 30.0% | −3.50% | 0.40 |

**Symbols killed (CRYPTO):** BTC, XRP, ATOM, SAND, MANA, HBAR, CHZ, BCH (8 of the 11 class symbol kills are crypto).

**Emission gate:** blocked 205 CRYPTO pick attempts (top suppressed sources: prediction_market_consensus ×112).

---

## 5. What has some promise (from audit2 pods)

| Pod | Status | Evidence |
|---|---|---|
| POD-CRYPTO-VWAP-REVERSION | observe | Lab OOS Sharpe 3.10, DSR 21.4, PBO 0.18 — **CONTESTED**: 1-bar lag drops PF to 0.957 |
| POD-CRYPTO-BOLLINGER-MR | observe | OOS n=38, PF 1.67, Sharpe 1.38 — n<100 |
| POD-CRYPTO-POSITION | observe | Only pre-committable slice surviving BH: +2.0%/pick [0.97, 3.08] n=145 q=0.001 |
| POD-CRYPTO-BTC4H-RSIMACD | observe | Best discovery cell by DSR (0.118), +2.0%/trade n=35 — fails 2× cost stress |

---

## 6. Recommendation

1. **Do not size up.** Class is below T2, sizing disallowed, and the net-expectancy CI excludes zero on the wrong side.
2. **Mutate before kill** per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` — several killed emitters are fade signals (WR<40%): consider inverting or requiring a second source before re-emitting.
3. **Focus forward testing only on the 4 observe pods** (VWAP, Bollinger, POSITION, BTC4H), each gated on own closed forward rows (n≥100, 2× cost CI-LB>0).
4. **Fix measurement** — the 0.29× intrabar-vs-daily PF inflation means every legacy dashboard number for CRYPTO is unreliable; always read the intrabar-truth columns.
5. **Fix stale FX/price data blockers** that leave many pods at 0 forward rows.

---
*Not investment advice. Data: audit3 ledger (canonical resolved view), dashboard recency panels, money_ready_verdict, audit2 pods. Generated 2026-11-22.*
