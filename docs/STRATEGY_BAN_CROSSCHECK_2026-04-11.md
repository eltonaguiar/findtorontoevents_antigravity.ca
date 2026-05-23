# Strategy Ban Cross-Check — 2026-04-11

> **Context:** Antigravity bot (c1319eb042) flagged that several BLOCKED/DEMOTED strategies are outperforming on crypto. This report cross-checks every banned strategy against `recent_closed` picks from `dashboard_data.json` to identify wrongful bans before anything destructive ships.

**Reference time:** 2026-04-10T23:54:34 UTC  
**Dataset:** 2,129 crypto closed picks, 82 active picks  
**Methodology:** Match all picks by `source_system` and `strategy` against `BLOCKED_SYSTEMS`, `_TRUST_PROBATION`, and `_TRUST_DEMOTED` in `template.html`. Analyze across 24h / 3d / 7d / all-time windows.

---

## 🚨 Wrongly Blocked — Immediate Action Required

These strategies are **HARD-BLOCKED** (hidden from all views) but are actively winning on crypto.

### 1. `kimi_signal_tracking` — BLOCKED, should be UNBLOCKED

| Window | W/L | WR | Avg PnL | Top Symbols |
|--------|-----|-----|---------|-------------|
| Last 24h | 1W/1L | 50.0% | +1.95% | TIA-USD |
| Last 3d | 7W/2L | 77.8% | +4.30% | TIA-USD, BTC-USD, ENJ-USD, BNB-USD, SOL-USD |
| Last 7d | 9W/2L | **81.8%** | **+4.15%** | TIA-USD, BTC-USD, ENJ, BNB, SOL, DOT, ONDO, INJ, ATOM |

**Ban reason (stale):** "22 trades, 18.2% WR, -126% PnL, PF 0.20"  
**Current reality:** 81.8% WR, +4.15% avg PnL across 11 diversified crypto trades. BTC 100% WR, SOL +7.93%, ATOM +7.39%.  
**Recommendation:** Unblock immediately. The old stats predate whatever fix/improvement was applied. This is the single most damaging ban in the system right now.

### 2. `signal_validation` — BLOCKED, should be UNBLOCKED

| Window | W/L | WR | Avg PnL | Top Symbols |
|--------|-----|-----|---------|-------------|
| Last 24h | 5W/1L | 83.3% | +2.19% | DOT, ADA, LINK, DOGE, ETH |
| Last 3d | 7W/1L | **87.5%** | +2.39% | AVAX(2), DOT, ADA, LINK, DOGE |
| Last 7d | 11W/6L | **64.7%** | **+1.29%** | BTC(4), AVAX(3), DOT(2), DOGE(2), ETH(2) |

**Ban reason (stale):** "10 trades, 0% WR, -18.4% PnL"  
**Current reality:** 64.7% WR on 17 trades, last 3 days 87.5% WR. AVAX-USD 3/3 = 100% WR.  
**Recommendation:** Unblock. The 0% WR was from an initial batch that no longer represents the strategy's output.

---

## ⚠️ Wrongly Suppressed — Probation Review Needed

### 3. `crypto_ml_edge` — PROBATION, should be SANDBOX or PROVEN

| Window | W/L | WR | Avg PnL | Symbols |
|--------|-----|-----|---------|---------|
| Last 24h | 1W/0L | 100% | +2.21% | DOGEUSDT |
| Last 7d | 4W/1L | **80.0%** | **+1.52%** | DOGEUSDT, ADAUSDT, BNBUSDT, LINKUSDT, AVAX-USD |

**Probation reason (stale):** "Zero closed picks in data files - unvalidated"  
**Current reality:** 5 closed picks, 80% WR, +1.52% avg. The probation reason is factually wrong — it now has validated closed picks.  
**Recommendation:** Remove from probation. Promote to SANDBOX minimum, consider PROVEN if next 10 trades sustain >60% WR.

---

## 📊 Borderline — Keep on Probation, Do NOT Block

These strategies are net-positive but not convincingly strong. Probation is appropriate; blocking would be destructive.

### 4. `alpha_engine` — PROBATION (correct tier, do not escalate)

| Window | W/L | WR | Avg PnL | Volume |
|--------|-----|-----|---------|--------|
| Last 24h | 106W/107L | 49.8% | +0.24% | 213 trades |
| Last 3d | 231W/292L | 44.2% | +0.24% | 523 trades |
| Last 7d | 383W/419L | 47.8% | +0.25% | 802 trades |

**Notable outperformers within alpha_engine:**

| Symbol | W/L | WR | Avg PnL |
|--------|-----|-----|---------|
| JTOUSDT | 9W/1L | **90%** | +3.10% |
| INJUSDT | 4W/1L | **80%** | +3.05% |
| WLDUSDT | 4W/1L | **80%** | +2.51% |
| SUIUSDT | 5W/1L | **83%** | +1.62% |
| STRKUSDT | 10W/3L | **77%** | +1.47% |

**Losers dragging it down:** XLMUSDT (0% WR), ONDOUSDT (0% WR), ESPUSDT (0% WR), DYDXUSDT (25% WR).  
**Recommendation:** Keep on probation. The system is net-positive because winners outsize losers, but the sub-50% WR means it relies on favorable RR. Consider per-symbol filtering to kill the 0% WR symbols.

### 5. `baby_strats_forward` — PROBATION (correct)

- 7d: 174 trades, 43.7% WR, +0.01% avg — breakeven, high volume
- BTC dominates (149/174 trades), marginal edge

### 6. `rapid_fire` — PROBATION (correct)

- 7d: 115 trades, 41.7% WR, +0.21% avg — slightly positive
- Pockets of strength: ZECUSDT +5.38% avg, XPLUSDT +5.21% avg, TAOUSDT +3.26% avg
- Pockets of weakness: LINKUSDT 0% WR, SOLUSDT 29% WR

---

## ✅ Correctly Blocked — No Action Needed

| Strategy | 7d Trades | 7d WR | Avg PnL | Status |
|----------|----------|-------|---------|--------|
| `crypto_winners` | 4 | 25.0% | -0.92% | Correctly blocked |
| `mercury2_fast` | 0 | — | — | No recent activity, correctly blocked |
| `ml_bg_system_a` | 0 | — | — | No recent activity, correctly blocked |
| `ml_bg_system_b` | 0 | — | — | No recent activity, correctly blocked |
| `ml_bg_system_c` | 0 | — | — | No recent activity, correctly blocked |
| `ml_bg_ensemble` | 0 | — | — | No recent activity, correctly blocked |
| `ml_bg_system_f` | 0 | — | — | No recent activity, correctly blocked |
| `ml_crypto_pred_v12` | 0 | — | — | No recent activity, correctly blocked |
| `quan_engine_scalp` | 0 | — | — | Zombie, correctly blocked |
| `quan_engine_swing` | 0 | — | — | Zombie, correctly blocked |
| `futures_ema_stack_momentum` | 0 | — | — | Zombie, correctly blocked |

---

## Action Items

1. **UNBLOCK `kimi_signal_tracking`** — Remove from `BLOCKED_SYSTEMS` set. 81.8% WR on crypto is too strong to suppress.
2. **UNBLOCK `signal_validation`** — Remove from `BLOCKED_SYSTEMS` set. 64.7% WR, accelerating (87.5% last 3d).
3. **Remove `crypto_ml_edge` from `_TRUST_PROBATION`** — Probation reason is factually stale. Has validated closed picks now.
4. **Do NOT escalate `alpha_engine` to BLOCKED** — It's net-positive. Consider per-symbol kill list (XLMUSDT, ONDOUSDT, ESPUSDT) instead of system-wide ban.
5. **Add time-decay to ban decisions** — Bans based on all-time stats should auto-expire or require revalidation when recent windows show >50% WR on 10+ trades.

---

*Generated 2026-04-11 by cross-checking `audit_dashboard/data/dashboard_data.json` against `BLOCKED_SYSTEMS`, `_TRUST_PROBATION`, and `_TRUST_DEMOTED` in `audit_dashboard/template.html`.*
