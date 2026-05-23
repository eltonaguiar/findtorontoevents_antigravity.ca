# TV Multi-Account Paper-Trade Session — Round 2 — 2026-05-12 15:53 EST

Round 2 of multi-account paper-trade session. Round 1 = `TV_SWARM_SESSION_2026-05-11_2330EST.MD`.

## Summary

16 new picks placed across 2 accounts (theswarm refresh + V4 value-stock batch). 1 design doc shipped for swarm-pick tracking infra. 3 background research swarms ran earlier; both pick swarms (theswarm refresh + V4 value) executed in parallel.

## theswarm refresh — 10 picks placed

10-persona swarm voted on a fresh 20-symbol universe (DIFFERENT from round-1 universe). Account balance ~$100,248 (+$248 realized from round-1 fills). All entries quote-verified live; swarm's reference prices were ~15-85% stale on most symbols — TP/SL recomputed from live legend read.

### Crypto (5 market orders)
| Symbol | Side | Qty | Entry | TP | SL | Tier (refresh) | TF |
|---|---|---|---|---|---|---|---|
| BINANCE:DOTUSDT | Short | 1,500 | 1.337 | 1.230 | 1.404 | 3 personas SHORT | 4h |
| BINANCE:INJUSDT | Long | 530 | 4.724 | 5.102 | 4.535 | 3 personas LONG (RWA narrative) | 4h |
| BINANCE:TIAUSDT | Short | 3,300 | 0.4587 | 0.4130 | 0.4820 | 2 personas SHORT | 1D |
| BINANCE:POLUSDT | Short | 15,000 | 0.0987 | 0.0888 | 0.1036 | 2 personas SHORT (MATIC rebrand, ghost-WR memory) | 1D |
| BINANCE:RUNEUSDT | Long | 2,500 | 0.588 | 0.634 | 0.558 | 1 persona LONG (Thorchain volume) | 4h |

### Stocks (3 LIMIT orders — US market closed)
| Symbol | Side | Qty | Limit | TP | SL | Tier | TF |
|---|---|---|---|---|---|---|---|
| NASDAQ:CRWD | Long | 4 | 546.50 | 601.00 | 519.00 | 2 personas LONG (cyber tailwind) | 1W |
| NYSE:BAC | Long | 30 | 50.85 | 55.88 | 48.26 | 2 personas LONG (value bank, curve steepener) | 1W |
| NASDAQ:PLTR | Short | 11 | 136.10 | 122.40 | 142.80 | 2 personas SHORT (parabolic, retail-driven) | 1D |

### Forex (2 market orders)
| Symbol | Side | Qty | Entry | TP | SL | Tier | TF |
|---|---|---|---|---|---|---|---|
| FX:AUDJPY | Long | 10,000 | 114.117 | 115.83 | 112.97 | Carry trade (RBA-BoJ rate diff) | 1D |
| FX:USDCAD | Long | 5,000 | 1.37000 | 1.3905 | 1.3604 | CAD soft on oil + BoC dovish | 1D |

### Futures (1 market order — Globex open)
| Symbol | Side | Qty | Entry | TP | SL | Tier | TF |
|---|---|---|---|---|---|---|---|
| CME_MINI:MES1! | Short | 1 | 7,419.75 | 7,271 | 7,494 | Equity hedge — VIX 16 cheap insurance | 4h |

### Asset-class consensus per refresh swarm
Highest conviction: **CRYPTO** (5 picks, mix L/S, alt-L1 dispersion thesis).

## V4 value-stock batch — 6 LIMIT orders placed

V4 = $1,022 balance, $865 available margin. Existing KO Long 2sh ($157 margin). Spawned dedicated Buffett/Piotroski/Graham value-screener swarm. All 6 picks LIMIT for Monday open. Total deployed: ~$668 margin (within budget).

| Symbol | Side | Qty | Limit | TP | SL | Margin | Sector | TF | F-Score | Thesis |
|---|---|---|---|---|---|---|---|---|---|---|
| NYSE:F | Long | 10 | 12.05 | 13.85 | 11.10 | ~$121 | Consumer Cyclical | 3M | 6 | P/E 9.94, 4.87% div, Q1 EPS $0.66 vs $0.18 est (260% beat), EY 10% |
| NYSE:VZ | Long | 2 | 48.20 | 54.50 | 44.80 | ~$97 | Communications | 6M | 7 | P/E 9.84, 6.15% div, $19B FCF, 0.45 beta, defensive |
| NYSE:PFE | Long | 5 | 25.80 | 29.50 | 23.80 | ~$129 | Healthcare | 6M | 6 | 6.7% div yield, Q1 rev beat, oncology pipeline (Seagen), 17yr div payer |
| NYSE:USB | Long | 2 | 55.60 | 63.00 | 51.20 | ~$112 | Financials | 6M | 7 | P/E 11.64, P/B 1.31, 3.71% div, super-regional bank Q1 beat |
| NYSE:UNM | Long | 1 | 79.50 | 91.00 | 74.00 | ~$80 | Insurance/Fin | 6M | 7 | P/E 9.77 (EY 10.2%), P/B 1.18, record Q1 EPS $2.14 |
| NYSE:KMI | Long | 4 | 32.30 | 36.50 | 29.90 | ~$129 | Energy/Midstream | 6M | 6 | 3.7% div, $1.65B FCF TTM, LNG export tailwind, toll-road model |

V4 deep-value lens: all picks pass Buffett/Piotroski filter — earnings yield >5% (most >9%), positive FCF, dividend-paying, P/E <14, P/B <1.5 for financials. Sector diversification: 6 sectors. Avg position $111. If BULLISH regime breaks, every name has defensive cash flow / book-value floor / high div yield acting as price magnet — basket avg div yield ~4.5%.

## Caveats noted during placement

1. **Swarm reference prices were broadly stale** — recompute live before TP/SL math. Examples:
   - DOT swarm est $4.85 → live $1.337 (72% off)
   - INJ swarm est $28.40 → live $4.724 (83% off)
   - TIA swarm est $3.95 → live $0.4587 (88% off)
   - PLTR swarm est $24.50 → live $136.01 (82% off)
   - MES swarm est $5,640 → live $7,419.75 (32% off)
2. **MATIC delisted on Binance.** Pivoted to POL (Polygon rebrand, $0.0987).
3. **TV order panel mode is sticky** — switching account doesn't reset Market vs Limit tab. First RUNE placement attempted on residual LIMIT panel with qty=1 / limit_price=2500. Detected after place + retried as MARKET qty 2500. Audit post-placement showed clean position + working TP/SL orders only, no dangling far-OTM order.

## Swarm-pick tracking design doc

Background subagent produced `docs/SWARM_PICK_TRACKING_DESIGN.md` (~520 lines). Key findings:
- No swarm-pick panel exists on `/audit` currently
- AI Challenge curator panel (7 curators) is the closest analog — wired at `audit_trail/dashboard_generator.py:3796-3829`
- Proposes new `audit_dashboard/data/swarm_picks.json` with per-pick consensus tier + per-model votes + outcome resolution
- Weekly review process: `tools/swarm/weekly_review.py` → `reports/swarm_review/YYYY_WW.md` → `swarm_leaderboard.json`
- Pattern miner: `(tier × class × regime)` cells with WR>60% and n>=10 highlighted
- **Open question for user (#3 in design doc):** should `models_consulted[]` include `underlying_model` field (e.g. "opus-4.7", "qwen3-coder-480b") so leaderboard can roll up by underlying model AND persona? This is the central question the DAILY_IDEAS.MD multi-model bake-off wants to answer. Recommend **YES** — without it the bake-off can't distinguish "MOMENTUM_TECH persona is good" from "Opus-4.7 backing that persona is good." Cost: 1 extra string field per vote.

## Cross-account state (post-round-2)

| Account | Balance | Active positions | Pending orders | Margin used |
|---|---|---|---|---|
| zerounderscore | ~$91,658 | 4 (ONDO-L / APT-L / ARB-L / ADA-S round 1) | 0 | ~$1,439 |
| Leap Crypto | ~$100,070 | 3 (BTC-S / ETH-S / DOGE-L USDC.P round 1) | 0 | ~$905 |
| V4 | $1,022 | KO-L + 6 round-2 pending LIMITs (F/VZ/PFE/USB/UNM/KMI) | 6 | $160 active + ~$668 reserved |
| theswarm | ~$100,248 | 11+ active (round-1 fills + 5 round-2 crypto + AUDJPY + USDCAD + MES) | 27+ (incl 6 round-1 LIMITs + 3 round-2 stock LIMITs + RUNE TP/SL working orders) | ~$25,687 active + $7,017 orders |

## Future suggestions

1. Implement design doc tasks 1-3 (schema + backfill round-1 + outcome resolver) to start the pattern-detection clock — currently winning vs losing picks die in markdown files without aggregation.
2. Wire live STOCKSUNIFY2 picks (https://raw.githubusercontent.com/eltonaguiar/STOCKSUNIFY2/main/data/v2/current.json) into the swarm voting as a 11th persona (data-source: external open-source momentum/regime engine).
3. Add Ish2K/stock-picking library as a 12th persona for explicit Piotroski-F + EPS-yield value lens — already pip-installable.
4. Wire `weekly_review.py` to run as a `routine` (one-time RemoteTrigger via `/schedule` skill) every Sunday 23:00 EST so consensus-tier WR/PF tracks automatically.
5. Resolve TV `quote_get` MCP tool bug (returns chart-symbol price regardless of `symbol` arg) — file issue against tradingview-desktop MCP.
6. Cross-pollinate: feed V4 value-screener picks back into theswarm for next refresh — value-lens persona missing from current 10-persona list.

## Files written this round

- `TV_SWARM_SESSION_2026-05-12_1553EST.MD` (this file)
- `docs/SWARM_PICK_TRACKING_DESIGN.md` (swarm-pick infra proposal — subagent output)

## Remaining open items

- PR #904 swarm review (pre-existing, still pending)
- Wire-up of design doc tasks 1-10 (need user to answer open Q3 before task 1)
- Cancel/verify any stale orders Monday morning before market open
