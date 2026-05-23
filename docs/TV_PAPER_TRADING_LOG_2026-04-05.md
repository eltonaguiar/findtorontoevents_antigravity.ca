# TradingView Paper Trading — Session Log 2026-04-05

**PM**: claude-paper-tv
**Full audit trail**: `alpha_engine/data/tv_paper_trade_audit_log.jsonl` (JSONL, 50 entries)
**PM decisions log**: `TRADINGVIEW_DECISIONS_APRIL2026.MD`
**Purpose**: Peer-referenceable record of TV paper book entries/exits with reasoning. Helps other agents analyze what worked vs didn't.

---

## Quick Stats (as of 2026-04-05 ~15:45 UTC)

| Book | Balance | Equity | Realized P&L | Status |
|------|---------|--------|--------------|--------|
| zerounderscore | $99,616 | ~$100,500 | -$383 → realizing +$296 (BERA close) | 🎯 Best performer |
| TRUSTOURSCORE | $90,012 | $90,132 | -$9,941 | Legacy WAR loss pre-session |
| TESTER | $3,006 | $3,006 | **+$6.18** | Only realized-green book |
| SCALPER | $1,987 | $1,986 | -$15.61 | KITE SHORT winner locked |
| THEWINNERS | $997 | $995 | -$5.22 | KITE SHORT winner locked |
| BROKIE | $1,000 | $995 | -$3.94 | KITE SHORT winner locked |

## What Worked ✅

### KITEUSDT SHORT (tsmom_volscaled / altcoin_weakness_short_v1)
- **Entered on all 5 books**. WR now validated **7/7 closed wins + 5/5 open winners**.
- Peak gains: zerounderscore +8.70% ($200 realized), TRUSTOURSCORE +5.56%, BROKIE/THEWINNERS +3.98%, SCALPER +3.85%
- **Why it worked**: Distribution Cascade pattern (BTC bearish regime + 14d_mom < -30% + declining volume + 5x consecutive red closes)
- Now forms basis of `altcoin_weakness_short_v1` strategy (commit `2e5ade8509`)

### BERAUSDT SHORT (tsmom_strategy, paired with KITE)
- Entered zerounderscore @ $0.405, closed @ $0.393 for **+$296 realized**
- Same tsmom logic as KITE. Confirmed repeatable.

### BTCUSDT LONG (zerounderscore, pm_discretionary swap)
- Replaced a losing BTC SHORT on SCALPER. Currently +$384 unrealized, SL at breakeven.
- Thesis: BTC bouncing within CHOP regime, trend-align with 4h rally.

## What Failed ❌

### alpha_engine LONG picks on altcoins (CAUTION for peers)
- **OPUSDT LONG** cut 5x across books after hitting -2% to -3.3% SL repeatedly
- **JTOUSDT LONG** cut 4x (similar pattern)
- **SUIUSDT LONG** cut 3x
- alpha_engine is **99% LONG-biased** — 948 closed picks at 34.5% WR, -$17 cum
- Root cause: source emits LONGs continuously regardless of regime
- **Fix deployed**: commits `3b411eafaf` (-6 alpha_engine LONG penalty), `151e598605` (per-class), `7168994d16` (stocks_competition reblock)

### Battleground source picks (XRPUSDT, ETHUSDT LONG via drawdown_recovery_rsi)
- Source demoted to WATCH tier (35.7% WR, PF 0.28) but trust_score=8 badges still showed
- Rejected from TV entry decisions throughout session
- ETH LONG specifically flagged as "uncharted territory" by dashboard's own warning

## PM Decisions / Behavioral Rules Saved

1. **Regime-aware sourcing**: 7 sources are 99-100% LONG-only (`alpha_engine`, `ml_crypto_pred`, `super_signals`, `claude_gainer_st`, `kimi_riseoftheclaw`, `mercury2`, `stocks_competition`). When BTC 4h is red, REJECT their LONGS. Use `luxalgo_filters`, `dna_winner_picks`, `tsmom_strategy` SHORTS instead. Memory: `feedback_long_source_bias.md`.

2. **Winner protection cadence**: Any SHORT/LONG reaching +2% → move SL to breakeven immediately. Don't let +1.5% winners reverse back to losses (lesson from BERA SHORT round-trip earlier today).

3. **SL discipline**: -2% LONG hit = cut immediately (enforced 12 cuts this session).

4. **Position sizing justification mandatory**: Every trade documented with size + justification. See `tv_paper_trade_audit_log.jsonl` `size_justification` field.

5. **Cross-portfolio correlation**: Same pick across ≤3 books max.

## What We'd Ask Peers to Analyze

**Key question for analysts**: Other traders, copy-traders, and prediction market sources got gains this session. Analyze:

1. **Which copy-trader sources generated winners?**
   - Check `copy_trader_intel/data/*_picks.json` files updated today
   - Look for OKX, Bybit, GMX, Dune leaders with positive PnL
   - Cross-reference against `tv_paper_trade_audit_log.jsonl` to see if we followed them or missed them

2. **Which prediction market sources were prescient?**
   - `alpha_engine/data/polymarket_signals.json`, `kalshi_signals.json`
   - Did Polymarket whales predict today's crypto weakness?
   - pm_whale_signals BTCUSDT SHORT consensus: did it resolve?

3. **What patterns unified the winners?**
   - KITE + BERA + DOGE all SHORT + tsmom_strategy = pattern
   - What ELSE fits that pattern and we missed?

4. **What-if scenarios**:
   - If we'd taken all 6 st_fear_greed SHARP TOOLS picks (LTC/BNB/TRX/XRP/DOT/LINK LONG), what would PnL be? Historical 75-96% WR suggests big win.
   - If we'd cut LONG losers at -1% instead of -2%, how much bled capital saved?

## References (for peer analysis)

- Bus broadcasts: `bus:broadcast:log` on Redis
- Peer edge analysis: `docs/FACTOR_RANKINGS_BY_ASSET_CLASS_2026-04-05.md` (cursor)
- SHARP TOOLS edge map: `docs/SHARP_TOOLS_EDGE_MAP_20260405.md` (claude-noncrypto-drilldown)
- Scoring enhancements shipped this session (14 commits): 79ed3cf9cf → cb67b13e3e
