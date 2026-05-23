# Hyrotrader Prop-Firm Challenge Audit

**Date:** 2026-05-12
**Author:** mb2v7tau (Claude Opus 4.7) + cavecrew-investigator subagent
**Goal:** Map `/audit/hyrotrader` code + strategies + symbols; propose prop-firm-challenge-passing improvements.

## Code structure

| File | Role |
|---|---|
| `audit_dashboard/hyrotrader/index.html` | UI dashboard (progress bars, rules, sizing, playbook links) |
| `audit_dashboard/hyrotrader/hyro_live_signals.js` | Fetch picks JSON + render live signals panel |
| `audit_dashboard/data/hyrotrader_picks.json` | Canonical state: challenge rules, account snapshot, 7 active picks |
| `alpha_engine/hyrotrader_enhanced_scoring.py` | Technical indicators (RSI/MACD/BB/ATR) + backtest validator |
| `alpha_engine/hyrotrader_short_term_scanner.py` | 1h crypto radar (consolidation, volume) |
| `tools/hyrotrader_risk_sizer.py` | Position sizing (Kelly fraction + class caps + 3% Hyro ceiling) |
| `tools/hyrotrader_log_trade.py` | CLI to log fills → `hyrotrader_journal.json` |
| `docs/HYROTRADER_CHALLENGE_STRATEGY.md` | Execution playbook + trailing DD rules + day-by-day pace |

**Data flow:** Static JSON (challenge rules + 7 picks) → JS load → UI renders. No live Binance hook; picks are reference setups.

## 7 active strategies + symbols (all CRYPTO, all 1H, both LONG+SHORT)

| Rank | Symbol | Strategy | BT PF | WR | Max DD | n | Grade |
|---|---|---|---|---|---|---|---|
| 1 | BTCUSDT | CCI Divergence | **2.15** | 52% | $263 | 54 | A+ |
| 2 | ETHUSDT | ADX Vol Breakout | 1.76 | 41% | $207 | 46 | A |
| 3 | AVAXUSDT | CMF Cross | 1.53 | 44% | $230 | 85 | A |
| 4 | XRPUSDT | BB Squeeze | 1.41 | 40% | $279 | 101 | A |
| 5 | SOLUSDT | Multi-EMA + ADX | 1.89 | 49% | $172 | 35 | A |
| 6 | SOLUSDT | CCI Divergence | 1.49 | 43% | $208 | 61 | A- |
| 7 | BTCUSDT | ADX Vol Breakout | 1.46 | 37% | $327 | 57 | B+ |

**System PF:** 1.67 (weighted, n≈339 over 6mo). **System WR:** 44.2%. **Max portfolio DD:** $388 (78% of Hyro $500 limit).

**Account snapshot (Apr 8):** Equity $4,929 (-$70.66 / -1.4%), DD used $141/$500, 0 live trades logged (pre-execution).

## 5 critical improvements to pass

### 1. Daily-loss-limit prevention (–5%/–$250 rule)
Current 0.5% per-trade ($25) gives only 10 consecutive losses before daily hard stop.
- **Fix:** Session-state machine in `tools/hyrotrader_log_trade.py`:
  - Real-time daily realized PnL tracking (not EOD snapshots)
  - Auto-gate new picks at –2.5% cumulative (soft stop)
  - Drop to 0.35% ($17.50) after first loss in day → 14-trade buffer

### 2. Trailing-drawdown ratchet exploitation
Hyro's trailing DD ratchets to new highs. Current playbook books at fixed 2× risk TP but doesn't lock the ratchet floor.
- **Fix:** `TP = max(2.0×risk, session_high - 0.5%)` — locks every new peak. Adjusts on-the-fly in TV Protect Position dialog.

### 3. Consistency constraint (40% rule: ~$200/day P1, ~$100/day P2)
Hyro caps single-day profit toward target at ~40%. Current TP plan assumes uncapped daily.
- **Fix:** Track `largest_single_day_profit_usdt` in JSON. At $200 (P1) / $100 (P2), stop opening; manage to close. Prevents consistency-breach disqualification.

### 4. Edge-decay monitor + tiered strategy rotation
All 7 strategies running in parallel — worst case all hit DD simultaneously ($388).
- **Fix:** Rolling 20-trade WR per strategy (refresh every 5 trades). If live WR < (BT_WR – 15pp), demote to tier-2 (size 50%). If WR recovers within 5pp, restore.
- Tier-1 (full 0.5%): BTC CCI, SOL Multi-EMA
- Tier-2 (0.25%): CMF, BB Squeeze
- Tier-3 (0.15%): ADX variants
- Expected DD cap: <$250 vs $388 worst case.

### 5. Pre-trade symbol-correlation guard
All 7 are crypto; corr(BTC, SOL, ETH, AVAX, XRP) ≈ 0.60–0.80. BTC break-down → all follow → $500 limit breached fast.
- **Fix:** Check 1h corr of proposed symbol vs 3 largest open positions. Block if corr > 0.70. Whitelist (BTC,XRP) ~0.40, (ETH,XRP) ~0.45. Introduce LINK / ARB as tier-2 alternates (lower-corr, proven 1.2–1.5 PF on same strategies).

## Implementation order

1. **Now:** Add daily-cap + edge-decay to `tools/hyrotrader_log_trade.py` (purely local script changes, no execution layer changes)
2. **Next 24h:** Wire correlation check into pre-trade sizing
3. **Day 3:** Add trailing-DD ratchet logic to TP calculator
4. **Day 5:** UI updates to `audit_dashboard/hyrotrader/index.html` showing tier state per strategy + daily cap remaining

## Swarm consultation queued

Next session: feed this report + the 5 fixes to Grok-4 + Cerebras qwen-3-235b + ernie-coder for adversarial review. Targets:
- Are the size adjustments survival-positive (not over-cautious)?
- Does correlation gating break edge for the highest-PF strategies?
- Trailing-DD lock-in: does it leak too much profit by exiting too early?

Backtest each proposed change against the 6-month historical dataset before going live with the prop-firm account.
