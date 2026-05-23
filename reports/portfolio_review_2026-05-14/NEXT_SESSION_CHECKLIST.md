# Next-Session Checklist — Fri 2026-05-15 14:45Z (9:45 ET)

Equity/ETF markets reopen 13:30Z. Wait 15 min for liquidity, then run this from Claude Code on the desktop with TV running on CDP.

## Pre-flight
- Open TradingView Desktop with CDP: `"C:\Program Files\WindowsApps\TradingView.Desktop_3.1.0.7818_x64__n534cwy3pjxzj\TradingView.exe" --remote-debugging-port=9222 --remote-allow-origins=*`
- If you launched on 9223 (or anything other than 9222): `python tools/tv_cdp_proxy.py 9222 9223 &` (background)
- Verify: `mcp__tradingview-desktop__tv_health_check` → expect `cdp_connected: true`

## Equity/ETF action queue (parked from 2026-05-14)

### `HIGHFWWRABV55_SCOREABOVE50_V4` (7 positions)
- NASDAQ:SOFI Long +2.42% — already protected (TP 17.75 / SL 14.95). HOLD.
- AMEX:CORN Long −1.18% — protected. **Check week-7 ETF / commodity outlook**; HOLD unless source-system `multi_asset_copytrader` further degraded.
- AMEX:DBA Long −0.88% — protected. Same as CORN.
- NYSE:KMI Long +3.07% — protected. **Tighten SL to BE 32.29.**
- NYSE:VZ Long −1.71% — protected. **Consider close** (defensive name, ETF EQUITY week WR 22.9% COLD).
- NYSE:USB Long −1.81% — protected. **Consider close** (regional bank exposure correlated with BAC).
- NYSE:KO Long +2.98% — protected. **Tighten SL to BE 78.12.**

### `theswarm` (12 positions remaining)
- NYSE:BAC Long −1.42% — protected. HOLD (correlated with USB/zerounderscore BAC).
- NASDAQ:TLT Long −0.64% — protected. HOLD (bond proxy, rate-sensitive).
- NASDAQ:PLTR Short +1.92% — protected. **Tighten SL to BE 136.11.**
- NASDAQ:AMZN Long +0.52% — protected. HOLD.
- AMEX:GLD Long −0.71% — protected. HOLD.
- NASDAQ:CRWD Long +7.22% — **CRITICAL: Tighten SL to 555.00 (locks ~+$60 = +2.8%).** Highest UPnL%.
- COMEX_MINI:MHG1! Long −1.01% — futures, partial sessions. **Tighten SL or close** depending on Mon copper outlook.

### `zerounderscore`
- NYSE:BAC Long −2.62% — protected this session (TP 55.50 / SL 47.50). HOLD; let it work.
- NYSE:LLY Long +5.03% — already at BE+ (SL 970 > entry 958.45). **Tighten SL to 990** (locks ~+3.3%).

## Crypto / forex (open now, re-eval if not already done)

- `brokie` 4× crypto LONGs (APT/INJ/BNB/ETH) all +1-2% — gain too small to bother BE-tighten unless retail-strong move.
- `theswarm` BINANCE:BNBUSDT Long +2.69% — **tighten SL to 662.46 BE**.
- `theswarm` BINANCE:POLUSDT Short +3.55% — already attempted BE-tighten (failed; retry with `keydown:Enter` dispatch before Confirm per skill update).
- `zerounderscore` BINANCE:ADAUSDT Short +2.55% — SL already at 0.2786 (locked).

## Pattern note for SL-modify via order ticket

EURUSD-style works first-shot. POLUSDT/GBPUSD needed retry with `keydown:Enter` between input dispatch and Confirm click. Add this to `.claude/skills/tv-paper-trade/SKILL.md` step 4.

```javascript
sl.dispatchEvent(new Event('input', {bubbles:true}));
sl.dispatchEvent(new Event('change', {bubbles:true}));
sl.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));
sl.dispatchEvent(new KeyboardEvent('keyup',{key:'Enter',bubbles:true}));
sl.blur();
// then click Confirm
```

## Provenance daily reconciliation (recommended for follow-up PR)

Per `feedback_gate_at_execution_not_generation` memory: positions on `HIGHFWWRABV55_*` accounts stay open even when the source-system filter no longer passes. Build:

1. Cron daily 00:30 UTC: `python tools/reconcile_filter_accounts.py`
2. For each `HIGHFWWRABV55_*` open position: query current `audit_dashboard/data/dashboard_data.json::systems` for `source_system` of the pick. If fwd_WR < 55 OR PF < 1.5 OR n < 20: emit close-recommendation to Redis bus + notify.
3. Operator (or future autonomous closer) actions the close.

## Reference files

- `reports/portfolio_review_2026-05-14/FINAL_SYNTHESIS.md` — what happened this session
- `reports/portfolio_review_2026-05-14/weekly_asset_class_perf.md` — week's WR/PF by class
- `reports/portfolio_review_2026-05-14/swarm_model_deepdive.md` — "swarm" is single-model with personas
- `reports/portfolio_review_2026-05-14/non_swarm_provenance.md` — non-swarm position provenance
- `.claude/skills/tv-*` — the new skill set (delegate-ready for Hermes / subagents)
