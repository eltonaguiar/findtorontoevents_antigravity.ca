# V4 edge-based picks + theswarm long-drag cleanup — 2026-05-12 21:12 EST

## V4 picks added (edge-tier per `edge_stability_index.json` @ 21:53Z)

Edge ranking driving selection (top 3):
1. **COMMODITY** — STABLE_EDGE, PF 4.31, WR 58.4%, Sharpe 0.35 (best class)
2. **EQUITY** — STABLE_EDGE, PF 1.92, WR 54.5%, Sharpe 0.24
3. **ETF** — MIXED, PF 1.35, WR 55.7%, Sharpe 0.12

V4 = $1,022 paper acct, $865 nominal available (~$200 effective free after 6 pending value LIMITs). Picks sized cheap so we get 3 positions, not 1.

| Sym | Class | Side | Qty | Limit | TP | SL | Margin | Edge basis |
|---|---|---|---|---|---|---|---|---|
| AMEX:CORN | COMMODITY | Long | 5 | 18.85 | 20.50 | 17.80 | ~$94 | Teucrium Corn — direct commodity ETF, top-edge class |
| AMEX:DBA | COMMODITY | Long | 3 | 28.50 | 30.85 | 27.45 | ~$86 | Invesco DB Agriculture basket — commodity diversification within top class |
| NASDAQ:SOFI | EQUITY | Long | 6 | 15.85 | 17.75 | 14.95 | ~$95 | Fintech value/growth — EQUITY class STABLE_EDGE |

Total added: ~$275 margin, all LIMIT (markets closed Tuesday 9pm EST). V4 utilization now 95% ($971 of $1,022).

**SLV (silver) rejected** — TV order panel slipped back to Market mode + reinterpreted limit_price (78.45) as qty, would-be $6,156 notional, V4 rejected for margin. **No damage, no fill.** Lesson: explicit `Limit` tab click required before EVERY new symbol, even if previously in Limit mode — chart symbol switch resets tab.

## theswarm cleanup — closed 2 long-bias drags

Strategy agent (transcript review 2026-05-12 19:14 EST) flagged:
> "Close LINK-L and ETH-L today, or at minimum demote to LIMIT-only re-entries below current price. These violate the long-bias-on-red-BTC rule in memory `feedback_long_source_bias.md`. LINK-L 5/5 unanimous is exactly the false-consensus the memory warns about."

| Sym | Side | Qty | Entry | Last | PnL @ close | Status |
|---|---|---|---|---|---|---|
| BINANCE:LINKUSDT | Long | 475 | 10.52 | 10.39 | -$61.74 (-1.24%) | CLOSED |
| BINANCE:ETHUSDT | Long | 2.26 | 2,325.50 | 2,290.30 | -$79.54 (-1.51%) | CLOSED |

Combined realized loss: -$141.28 (~0.14% of $100k acct). Acceptable cut vs alternative of holding while shorts (TSLA/ADA) carry the book.

## Why these moves matter

**V4 edge alignment:** prior V4 picks (F/VZ/PFE/USB/UNM/KMI) were Buffett-style value-cyclicals — one factor bet. Adding CORN/DBA (top-edge COMMODITY class) + SOFI (EQUITY edge) diversifies V4 across the two highest-Sharpe classes on the dashboard. The COMMODITY edge is concentrated in CT=F per peer's just-shipped `asset_class_concentration` payload (75% one symbol = WARN), so CORN+DBA ETF surrogates capture broad commodity exposure without single-instrument capacity limits.

**theswarm long-drag cleanup:** strategy reviewer's diagnosis was clean — long-bias picks were the loss leaders while shorts (TSLA-S +$121, ADA-S +$71) carried the book. Cutting LINK-L + ETH-L lets the working shorts breathe without longs dragging margin. Future swarm rounds need ≥4 non-Opus personas to avoid the persona-correlation echo chamber that produced the 5/5 LINK-L unanimous in the first place.

## Cross-account state (post-this-round)

| Acct | Balance | Active | Pending | Margin used | Realized | Unrealized |
|---|---|---|---|---|---|---|
| zerounderscore | $91k | 4 | — | ~$1.4k | — | — |
| The Leap Crypto | $100k | 3 | — | ~$905 | — | — |
| V4 | $1,022 | KO | 9 LIMITs (F/VZ/PFE/USB/UNM/KMI/CORN/DBA/SOFI) | $160 active + $811 reserved | +$22 | +$4 |
| theswarm | ~$100k | 17 (was 19, -2) | ~50 working | ~$25k | +$248 - $141 = ~+$107 net | flat-positive |

Total ~30 paper positions live. theswarm net realized now slightly positive after LINK+ETH cleanup.

## Next steps (per peer message — coordinating to avoid overlap)

Peer (0f7ecsyk) shipped concentration + capped_vs_raw + active_picks_sync live writer + tv_pick_capture (218 lines already done). Sent peer message offering to take A4 (CT=F capacity model) or A6 (correlation-regime GOLD↔EQUITY +0.76 follow-up) if they don't want to. Awaiting reply.

Standing recommendations:
- Don't add more picks to theswarm until ≥60% of the 38 tracked swarm_picks resolve
- Force ≥4 non-Opus personas in next fanout (Kimi-k2.5, DeepSeek R1, Qwen3-coder-480b, GPT-OSS-120b all available locally)
- CT=F sizing capacity model (peer's A4) needs correlation gate, not just ADV — GOLD↔EQUITY just crossed +0.76 = diversifier moving with equities
