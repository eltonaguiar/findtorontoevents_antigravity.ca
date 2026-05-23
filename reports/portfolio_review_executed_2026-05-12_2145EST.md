# Portfolio Review Execution — 2026-05-12 21:45 EST

Second-opinion swarm agent (general-purpose) reviewed 4-account state. Verdict: 5 CLOSE NOW + 4 TIGHTEN SL + 2 PARTIAL 50% + 3 ADD candidates. Honest verdict on methodology: "swarm produces *candidates*, not *portfolios* — needs portfolio-construction layer enforcing no-shorting-the-regime + no-offsetting-trades-across-accounts."

## Executed (theswarm)

### Closes (2 of 5 succeeded — crypto only; stocks/futures blocked by after-hours TV)

| Pick | Action | Reason from swarm |
|---|---|---|
| BINANCE:DOGEUSDT Short | **CLOSED** | Netted against Leap DOGE LONG +0.74% across accounts — kill the loser |
| BINANCE:DOTUSDT Short | **CLOSED** | Worst loser (-$64 / -3.22%), thesis broken (DOT outperforming peers) |

### Close attempts on stocks/futures — FAILED

NVDA Short, GLD Long, MES1! Short close clicks went through TV's `close-settings-cell-button` but TV refused to fill (markets closed Tues 9pm EST). **Side effect: the failed close-clicks cancelled the TP/SL working orders on all 3 positions** (toast confirmed "Stop Loss order cancelled on NASDAQ:NVDA" + same for GLD/MES). Positions left NAKED.

### Re-protect (3 positions saved from naked exposure)

Re-opened Protect Position dialog on each + restored original TP/SL per `reference_tv_protect_position_tp_toggle.md` (enable toggles BEFORE setting prices).

| Sym | Restored TP | Restored SL |
|---|---|---|
| NASDAQ:NVDA Short 18 | 201.90 | 228.20 |
| AMEX:GLD Long 12 | 460.80 | 421.60 |
| CME_MINI:MES1! Short 1 | 7,271.00 | 7,494.00 |

All 3 verified TP/SL inline on position row post-confirm.

### Partial closes

| Pick | Action | Outcome |
|---|---|---|
| BINANCE:RUNEUSDT Long 2500→1250 | **50% PARTIAL CLOSE** (Market Sell 1250) | Banked +$36 on closed half; 1250 trailing at last $0.617 (vs entry $0.588) |

### Skipped from swarm rec (will revisit Wed when stocks open)

| Pick | Skip reason |
|---|---|
| NVDA close | After-hours — retry Wed open |
| GLD close | After-hours — retry Wed open |
| MES close | After-hours — retry Wed open (Globex tech: open but TV paper refused) |

### Tighten SL — deferred

Swarm recommended 4 SL tightens (ADA-S→0.2775 breakeven, TSLA-S→440, LLY→970, BTC-S Leap→81,500). **Deferred** — TV Protect Position dialog already saturated with retries this session, risk of mis-clicks. Will run as a clean batch next session if positions still warrant.

### ADD candidates — deferred

Swarm top-3:
1. CT=F Long after closing GLD — but GLD didn't close (after-hours); skip until GLD exits. Also CT=F single contract = $36k notional = 36% of theswarm = too concentrated.
2. SPY/QQQ Long — markets closed. Could LIMIT order, but defer pending fresh edge_stability re-read.
3. DBA Long — already pending on V4 (filled at Wed open).

## Cross-account state post-execution

| Acct | Active before | Active after | Net change |
|---|---|---|---|
| theswarm | 15 | 13 | -2 (DOGE-S, DOT-S closed) |
| RUNE qty 2500 | | RUNE qty 1250 | -50% |
| zerounderscore | 4 | 4 | no change |
| Leap Crypto | 3 | 3 | no change |
| V4 | 1+9 pending | 1+9 pending | no change |

theswarm realized PnL change this session: +$36 (RUNE half) - (DOT/DOGE realized losses on close).

## Critical safety note

The TV after-hours close-button silently cancels TP/SL without closing positions. **This is a footgun.** Any peer / future-session agent that uses the standard close-position flow on a stock/ETF/futures during after-hours risks naked exposure if they don't immediately re-protect. Consider:
- A `feedback_tv_close_button_after_hours_strips_tpsl` memory entry
- Wrapper in tv-paper-trade skill that detects market-closed + warns / blocks

## Swarm methodology honest verdict (verbatim)

> "Of 22 positions, 7 are pure noise (<±1%), 5 are working (TSLA, RUNE, BNB, LLY, ADA-shorts), 4 should never have been opened against a confirmed BULLISH regime (MES short, NVDA short, GLD as 'hedge' with corr +0.77 to SPY, duplicate DOGE long+short across accounts). Total unrealized +$200 across $300k of paper capital is a 0.07% session result. The swarm picks individually pass gates but the portfolio-level construction is incoherent: no position-correlation check, no regime-direction gate, no cross-account netting. The methodology generates candidates, not portfolios. Until a portfolio-construction layer enforces 'no shorting the regime' and 'no offsetting trades across accounts,' realized edge will keep getting eaten by self-cancellation and regime-fight. The Tier-1 target (PF>2) is unreachable from this construction style regardless of pick quality. **Fix the portfolio layer, not the picker.**"

This is the highest-leverage finding of the session.
