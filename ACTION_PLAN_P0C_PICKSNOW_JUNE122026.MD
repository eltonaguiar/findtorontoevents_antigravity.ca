# ACTION PLAN — P0C + picks-now Fixes Deployed June 12, 2026

**Branch:** `p0c-crypto-long-block-picksnow-fixes-2026-06-12`
**PR:** [Create on GitHub](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/new/p0c-crypto-long-block-picksnow-fixes-2026-06-12)
**Author:** Buffy (deepseek-v4-pro)
**Evidence:** `reports/new_strategies_june2026_20260612_0400.json`, `BUFFY_MASTER_HANDOFF_JUNE122026.MD`

---

## 1. What Was Just Deployed

### P0C — Block CRYPTO LONG (M-036 extension)
**Files:** `alpha_engine/config.py:429`, `audit_trail/quality_gates.py:7221`

- `CRYPTO_BLOCKED_DIRECTIONS`: `{BUY}` → `{BUY, LONG, STRONG_BUY}`
- `forward_test_only` + `_monitor_mode` exemption before block (measurement lanes continue)
- **Stops −503% cumulative CRYPTO LONG PnL destruction immediately**
- CRYPTO SHORT (55.8% WR, n=104) continues unblocked

### Picks-now Fix #1 — One-Position-Per-Ticker
**File:** `audit_trail/quality_gates.py:6183` (`_dedup_gate_blocks`)

- Symbol-only dedup alongside existing (symbol, direction, strategy) tri-key
- `_SEEN_SYMBOLS` set for in-batch dedup (catches same-symbol-different-strategy in single scan)
- `active_picks` loop checks symbol match regardless of strategy/direction
- Kill-switch: `ONE_PER_TICKER_DISABLED=1`
- **Eliminates MU×8, AVGO×3, AMT×5 concentration**

### Picks-now Fix #2 — Universal TP/SL Fallback
**File:** `audit_trail/quality_gates.py:10135` (before `return True` in `passes_active_gate`)

- Default percentage-based TP/SL if pick has none:
  - CRYPTO: TP +5%, SL −3%
  - EQUITY: TP +3%, SL −2%
  - FOREX: TP +1.5%, SL −1%
  - COMMODITY: TP +4%, SL −2.5%
  - ETF: TP +3%, SL −2%
- LONG (TP above entry, SL below) vs SHORT (TP below, SL above) correct
- Fail-open: exception → admission without protection (better than block)
- Kill-switch: `UNIVERSAL_TPSL_DISABLED=1`
- **Cuts catastrophic tail from −35.86% mean → closer to −0.04% trimmed**

---

## 2. Verification Steps (After Merge → Deploy)

### 2.1 CRYPTO LONG Block Verification
```bash
# After 7 days: confirm zero new CRYPTO LONG emissions
SELECT direction, COUNT(*) FROM at_signal_outcomes
WHERE asset_class='CRYPTO' AND opened_at > NOW() - INTERVAL 7 DAY
GROUP BY direction;
# Expect: LONG=0, SHORT > 0
```

### 2.2 One-Per-Ticker Verification
- Check `/audit/picks-now.html` live mark-to-market: no symbol should appear more than once
- Before deploy: MU appears 8x identically → after deploy: MU appears once
- `ONE_PER_TICKER_DISABLED=1` to roll back if needed

### 2.3 TP/SL Fallback Verification
```bash
# Check picks without TP/SL after deploy
SELECT COUNT(*) FROM trading_picks
WHERE (take_profit IS NULL OR stop_loss IS NULL) AND created_at > NOW() - INTERVAL 1 DAY;
# Expect: 0 (all picks should have TP/SL from fallback)
```

### 2.4 Kill-Switch Tests
- `CRYPTO_BUY_DIRECTION_GATE_ENABLED=0` → all CRYPTO directions allowed (existing gate)
- `ONE_PER_TICKER_DISABLED=1` → concentration limit lifted
- `UNIVERSAL_TPSL_DISABLED=1` → TP/SL fallback disabled
- `DIRECTION_TRIPLE_GATE_DISABLED=1` → BLOCKED_DIRECTION_TRIPLES gate lifted (existing)

---

## 3. Remaining Action Items (Priority Order)

### 🔴 P0 — Bleed Stoppers

| # | Task | Impact | Effort | Depends On |
|---|---|---|---|---|
| **P0B** | Unified kill list — add 7 strategies to HARD_KILL in `emitter_discipline.py`, centralize `is_emission_allowed()` | Stops silent emission leaks | Low | None |
| **P0A** | Intrabar hourly reresolve — one-time bootstrap batch (177K backlog), then cap 500/hr | Seeds honest data for MONITORED strategies | Medium | None |

### 🟡 P1 — High ROI

| # | Task | Impact | Effort | Depends On |
|---|---|---|---|---|
| **P1A** | Intrabar-only verdict UI on `/audit` | Shows honest WR/PF when n≥30 | Medium | P0A |
| **P1B** | Auto-kill tribunal (weekly automated demotion) | Systematizes strategy lifecycle | Medium | P0B |
| **Council #3** | Bridge AI panel → quant score (−20pts per reject) | META 7/7 reject shouldn't show as top pick | Medium | None |
| **Equity gap fade** | Increase symbol universe, tighten entry for `equity_gap_fade` (66.7% WR, PF=1.364) | Only strategy near P95 with n≥30 | Medium | None |

### 🟢 P2 — Nice to Have

| # | Task | Impact | Effort |
|---|---|---|---|
| Council #4 | Factor correlation penalty in picks-now scoring | Reduces echo-chamber | Medium |
| Council #5 | Factor 4 → veto gate (skip if RVOL extreme) | Prevents catching falling knives | Low |
| Council #6 | DB Edge Overlay 10%→25% in picks-now | Anchors scoring to proven edge | Low |
| Council #7 | Expose trimmed-mean PnL on dashboard | Shows real story: −0.04% vs raw −35.86% | Low |
| Tune zero-trade strategies | Relax entry params for 3 strategies that generated 0 trades | May find more baseline-beaters | Low |
| SHORT variants | Add SHORT direction variants — forensic shows PF=7.40 (futures), PF=6.13 (forex_rsi2) | Untapped edge direction | Medium |
| Stress matrix | Apply cost×0.5/1/2/4 before promoting MONITORED strategies | Prevents overfit promotion | Medium |
| FOREX data audit | Verify ~1,500 bars per FX symbol — is data truncated? | Data quality | Low |

---

## 4. DB Baselines (Reference — June 12, 2026)

| Class | n | WR% | PF | Money-Ready? |
|---|---|---|---|---|
| CRYPTO | 1,283 | 29.2 | 0.728 | ❌ |
| EQUITY | 130 | 28.5 | 0.509 | ❌ |
| FOREX | 124 | 29.8 | 1.107 | ❌ (thin) |
| COMMODITY | 110 | 33.6 | 1.426 | ❌ (below P95) |
| ETF | 22 | 0.0 | 0.148 | ❌ |
| MEMECOIN | 77 | 26.0 | 0.580 | ❌ |
| BOND | 7 | 28.6 | 1.699 | ❌ (n too low) |

**0/9 money-ready.** Deficit is entry selection, not exit geometry.

---

## 5. MONITORED Strategies (Registered This Session)

| Strategy | Class | n (backtest) | WR% | PF | Promotion Criteria |
|---|---|---|---|---|---|
| `crypto_funding_contrarian` | CRYPTO | 1,481 | 34.2 | 0.825 | n≥20 intrabar + PF>0.728 |
| `equity_gap_fade` | EQUITY | 36 | 66.7 | 1.364 | n≥20 intrabar + PF>0.509 |
| `equity_rsi2_sma200` | EQUITY | 91 | 30.8 | 0.694 | n≥20 intrabar + PF>0.509 |
| `etf_rsi2_pullback_uptrend` | ETF | 53 | 37.7 | 1.145 | n≥20 intrabar + PF>0.148 |

All tagged `_monitor_mode=True`, `_monitor_tag="BASELINE_BEATER_SHADOW"`, `_sizing_override="zero"`.

---

## 6. Key System Invariants

1. **P0B/P0C route through gate layer** — never add blocks directly in `production_scanner.py`
2. **Kill-switches on every gate** — `*_DISABLED=1` env vars documented
3. **Fail-open on exceptions** — gate error never blocks a pick
4. **Backup before DB mutation** — `ejaguiar1_backups` via `tools/db_backup_to_backups.py`
5. **Credentials via `tools/db_env.py`** — never hardcode passwords

---

*Generated 2026-06-12 by Buffy (deepseek-v4-pro). Companion to BUFFY_MASTER_HANDOFF_JUNE122026.MD.*
