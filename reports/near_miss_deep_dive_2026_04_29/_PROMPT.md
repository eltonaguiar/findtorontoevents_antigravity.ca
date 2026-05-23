# Near-Miss Deep Dive — 3 strategies just below tier-promotion thresholds

You are reviewing 3 strategies that are JUST below promotion thresholds. The repo
uses Tier-2 = "PF>=1.5 / WR>=50 / MDD<20", Tier-1 = "PF>=2 / WR>=55 / MDD<10".
Candidate floor: n>=30. Proven floor: n>=200.

## Strategy A: luxalgo_confluence (CRYPTO)
- n=205 closed picks (10-day window 2026-04-19 → 2026-04-29)
- WR 52.2%, PF 1.66, sum_pnl +93.7%
- LONG: n=103, WR 52.4%, +51.4%; SHORT: n=102, WR 52.0%, +42.3% — symmetric
- TP_HIT/SL_HIT split exactly 73/73 (50/50). FORCE_CLOSED=57 trades, +0.51% avg
- Top symbols: STXUSDT 60% WR/+17%, ARBUSDT 71%/+21%, ADAUSDT 71%/+14%, WIFUSDT 70%/+14%
- Worst: SOLUSDT 31%/-3.7%, JUPUSDT 36%/-3.7%, BTCUSDT 38%/-2.8%
- Currently ACTIVE: 0
- BLOCKERS:
  - In `_PAPER_ONLY_STRATEGIES` (alpha_engine/strategy_blocklist.py:174) since 2026-04-19,
    rationale: "appears in every toxic consensus combo" (consensus, not standalone)
  - In core_whitelist.json kill_list (BOTH "luxalgo_confluence" and "luxalgo_filters::luxalgo_confluence")
  - Trust tier=RELIABLE, wf_verdict=VIABLE, score 36-53 (avg 45)
- Latest emit: 3h ago — pipeline IS running upstream, just blocked at dashboard active gate

## Strategy B: rs-breakout-scout (EQUITY/ETF)
- n=23 closed picks (Feb 19 → Apr 24)
- WR 78.3%, PF 7.49, sum_pnl +59.8%
- LONG-only, asset_class EQUITY=18, ETF=4, BOND=1
- TP_HIT 14, TIME_EXIT 6, SL_HIT 3 (61% TP-hit rate)
- Top: SOXX 80%/+15.4%, XLK 100%/+11.1%, CVX 100%/+9.2%, NFLX 100%/+7%
- Source: kimi_riseoftheclaw (UNTRUSTED tier in the schema)
- BLOCKERS:
  - NOT in kill_list, NOT in paper-only
  - NOT in equity allowlist explicit but IS in `smart_picks_engine.py:253`
    PROVEN_STRATEGIES with boost=8 wr=69.2
  - Last emit 5 days ago. Trickle ~1-2/day. Setup is rare.
- Currently ACTIVE: 0
- Question: rare-setup or upstream issue?

## Strategy C: atr_percentile_gate (CRYPTO/BTCUSDT-only)
- n=22 closed picks (Apr 25 → Apr 27)
- WR 95.5%, PF 13.51, sum_pnl +9.27%
- 100% BTCUSDT LONG. TP_HIT 16, TIME_EXIT 5, SL_HIT 1
- Avg win 0.48%, avg loss -0.74% (SMALL TP — 2.5x ATR target with 1.5x ATR stop)
- Burst pattern: 2 picks Apr 25, 20 picks Apr 26, then NOTHING for 3 days
- BLOCKERS:
  - PR #519 (b218cb7ba2 merged Apr 29) removed `baby_strats_forward::atr_percentile_gate`
    from kill_list. Auto-expiry of stale kill_list (>21d) also fires.
  - 100% of closed picks have score < 50 (avg 44.7); HIGHFWWRABV55_SCOREABOVE50 gate
    blocks ALL of them. 27% have conf < 0.50.
  - trust_tier=WATCH (not RELIABLE/PROVEN)
- Currently ACTIVE: 0
- Question: even with kill_list removal, score gate blocks emission to active. Real?

## Your task
Answer concisely (no preamble):
1. Which of A/B/C should we prioritize for promotion-step intervention this week?
2. What is the highest-leverage 1-line fix for each?
3. Fragility concerns? (small-n + regime change + concentrated symbol)
4. Should the 0.55 confidence floor / 50 score floor be relaxed for proven-WR
   strategies, or kept rigid?
5. Does symmetric LONG/SHORT performance + perfectly equal TP/SL count argue
   FOR or AGAINST trusting luxalgo_confluence's edge as real (not a noise artifact)?
