
We need answer max 300 words, concrete. User asks senior quant infra reviewer. Need address three questions. Need understand component: capacity/cost stress matrix adopted before probation: rerun candidate replay under cost multipliers x0.5/1/2/4, entry-latency slips 1/5/15min, volume caps 1%/5% of entry-bar volume; PF CI-LB >1.15 must survive >=3 adverse cases. Constraint only 1h OHLCV bars no tick/spread. Need answer: (1) implement latency slips correctly with 1h bars (enter at next bar open? interpolate?) without fooling ourselves; (2) bar-volume liquidity proxy for crypto alts or haircut; (3) minimal defensible version vs gold-plating.

Need maybe discuss using 1h bars: cannot know intrabar path. Conservative: if signal at close of bar t, execute at open of t+slip bars (next bar open for 1-min slip? Actually slips 1/5/15min align with 1h bars. 1min within same bar? Need implement). If only hourly bars, if signal known at bar close, no intrabar execution. For 1min slip, entering within same bar impossible to validate; must either ignore 1min or treat as same bar close? Need avoid lookahead. For 1h bars, safe execution prices: next bar open for any slip less than 1h if signal at close; next bar close if signal intrabar? Let's reason.

OHLCV bars: bar t has open/high/low/close/volume. If strategy uses bar t close to generate signal, cannot enter during bar t because close known after bar. Earliest execution is open of t+1. For a latency slip of 1/5/15 minutes after signal at t close, actual execution would be in t+1 bar, but exact price unknown. Conservative with no intrabar data: use worst of open/high? For long, entry price = max(open_{t+1},? Actually if entering within first 15 minutes of bar t+1 after signal, could get any price in first 15 min, not known. OHLCV high/low entire hour. To be conservative for long, use bar t+1 high (worst fill) or open plus slippage? But that may be too conservative. Alternative: execute at next bar open for all slips <1h, but that ignores 5/15 min. It is optimistic? If signal at close, next bar open is earliest, so for latency slip 5/15 min, next bar open is too early; but costs may be higher? Need "without fooling ourselves". Could say do not interpolate intrabar from OHLCV; impossible and dangerous. Use execution grid based on bar boundaries: signal at close, base case next bar open; latency slip should be modeled as one-hour increments or as "bar delay" with conservative fill. If requirement says 1/5/15min, with 1h bars we cannot distinguish them; collapse to same case or use conservative haircut to open? Let's formulate.

Maybe answer: For 1h bars, implement latency slips as delayed execution at the first observable price after the slip:
- If signal generated at close of bar k:
  - Slip <1h: earliest possible next bar open. But since 1/5/15 are not identifiable, don't claim precision. Use next bar open as best-case, next bar close as conservative/delayed? Or use bar k+1 high for longs / low for shorts for "within first hour worst-case"; or open plus slippage. 
  - Slip 1h: bar k+1 open? Wait if signal at close k and latency slip 60 min, execution at open k+1? Actually bar k close at time t=60m. Add 60m = time 120m, which is open of bar k+2? Let's define. If bars indexed by start/end. Signal at close of bar k at time end k. Next bar open = end k (same time if no latency). 1h slip = open k+1. 5min slip = also within bar k+1, not observable; conservative fill maybe high of bar k+1 (for long) or low for short, because worst price during that first hour. 15min same. But if using high/low entire hour for 5/15 min, too conservative because worst could occur after 15min. But without intrabar data, cannot know. Could use a conservative haircut to next bar open, not high. Hmm.

Need answer "enter at next bar open? interpolate?" The correct answer: don't interpolate; use only executable prices. For backtest with hourly bars, signal at bar close -> next bar open is the first executable price. For latency slip 1/5/15min, they all map to the same next bar open if you're using close-to-open assumption; if you want to stress them, you must model them as additional conservative slippage or use bar-level delay (e.g., 1h slip -> next bar open, 2h -> after). But maybe the adopted matrix says entry-latency slips 1/5/15min. Since only 1h bars, we can implement by shifting signal by 1 bar? But then 1/5/15 all same. Need maybe "if signal computed before bar close using data available up to previous bar, then enter at bar open; slip 1h = next bar open; 5/15 impossible." Let's parse component: "before PROBATION, re-run candidate replay under cost multipliers x0.5/1/2/4, entry-latency slips 1/5/15min, volume caps 1%/5% of entry-bar volume". Maybe candidate replay uses 1h OHLCV. Entry latency slips 1/5/15min. They ask how implement with 1h bars correctly (enter at next bar open? interpolate?) without fooling ourselves.

Could propose:
- Use bar-close signal, no intrabar interpolation.
- Base: enter at next bar open for any latency <1h. Mark as optimistic. For 1/5/15, because granularity coarser than slip, do not claim separate effects. Either collapse to "latency <1h" or add deterministic slippage equal to (high-low) * fraction? But interpolation from OHLCV not defensible. 
- If requiring separate 1/5/15, use conservative worst-of-hour fills: for long, entry = high of bar containing delayed execution; for short = low. But this is not latency-specific and overly punitive; acceptable as adverse case if stated.
- Better: shift entry by full bars: 0min = next open, 60min = open next bar, 120min etc. But 1/5/15 cannot be resolved.
- To avoid fooling ourselves, report "hourly-bar optimistic fill" and "latency stress is proxy, not measured"; don't pass based solely on 1/5/15 if no intrabar data; require survival under bar-open delay and cost/volume haircuts.

Need answer liquidity proxy:
- Bar-volume usable as coarse capacity proxy, but crypto alts need heavy haircut due to OHLCV reporting noise, wash trading, fragmented venues, time-varying liquidity, hidden depth, MEV/atomic, gaps. Use median over lookback not current bar? Use capped ADV? For entry-bar volume maybe use conservative: min(entry bar volume, median 20/50 bar volume) * participation cap * reliability haircut. Participation caps 1%/5% of entry-bar volume maybe high? For alt, 5% of hourly bar volume may be too high. Need haircut maybe 50-90%, e.g., use 10-25% of reported hourly volume as realistic notional participation. But if volume caps are 1%/5% of entry-bar volume, maybe "bar-volume is only usable after haircut; do not trust reported volume; use conservative haircut 0.25-0.5 for majors? 0.1-0.25 for alts; exclude low liquidity". Need concrete.

Could say:
- Use volume = median(last N hourly volumes) * venue/coin quality haircut * (1 - volatility penalty?) and cap order to min(1%,5%) of that. For alts, haircut reported OHLCV by 50-80%, or use only 10-30% of hourly volume as executable. If no reliable venue data, use 20% haircut default and fail/flag coins below threshold.
- Avoid using current entry-bar volume because it's look-ahead at signal time? Wait if signal at close of bar, volume known. But if entry in next bar, current entry-bar volume not known at execution. For capacity test, using entry-bar volume may be optimistic/lookahead if it caps order by volume that only becomes known after the bar. But for stress, maybe conservative? Let's think. If volume cap is % of entry-bar volume (the bar in which you enter), at backtest time if you enter at next bar open, you don't know that bar's volume. You cannot decide whether to enter or size based on that volume without lookahead. To avoid fooling ourselves, cap using volume known before entry: previous bar volume or rolling median volume. But the adopted says volume caps 1%/5% of entry-bar volume. Hmm. We need answer concrete maybe "do not use the entry bar's final volume to decide fill; it's look-ahead. For stress, use it only as ex-post capacity filter or use conservative pre-entry volume proxy." This is important. The component says "volume caps 1%/5% of entry-bar volume"; if signal generated at close of bar, entry bar is next bar; its volume unknown. If signal generated within bar? With 1h OHLCV, can't. So minimal defensible: cap by pre-entry known volume (last completed bar or rolling median), not final entry-bar volume; or if using entry-bar volume, treat as "post-trade capacity audit" and require no skipped trades due to insufficient volume? Need mention.

Need maybe define replay:
- For each candidate trade at bar k close:
  1. Compute signal from info ≤ close k.
  2. Entry time = open k+1 for base (or open k+1+floor(latency/60) if latency ≥1h). For 1/5/15 min, all same; no interpolation.
  3. Entry price = open k+1. For adverse case, use open plus slippage/cost multiplier; optionally use high/low for worst-case as a separate "OHLCV envelope" not latency.
  4. Exit similarly at next executable bar after exit signal, with slippage.
  5. Position size = min(model size, cap_pct * known_liquidity_proxy), where liquidity proxy = haircut * median volume over past N bars; not entry bar final volume.
  6. If cap reduces size, record capacity hit; don't skip unless zero.
  7. Costs: apply per-side cost multiplier to spread/slippage estimate; no tick spread so use fixed bps or high-low/volume proxy.

Need "PF CI-LB>1.15 must survive >=3 adverse cases." Need maybe say "define adverse cases as combinations: cost x2/x4, latency next-open, volume cap 1% with 50-80% haircut; not count x0.5 or same-hour slip variants as independent." Because 1/5/15 min all same, don't count them as three adverse cases. Need answer minimal defensible vs gold-plating:
- Minimal:
  - Close-to-open execution only.
  - No intrabar interpolation.
  - Use cost multipliers.
  - Use conservative volume proxy with haircut and pre-entry known volume.
  - Run grid: costs x0.5, x1, x2, x4; latency 0 and 1h? But adopted says 1/5/15; implement as "latency <1h = next open; no separate pass credit"; maybe one adverse latency case.
  - Capacity cap 1% and 5% of haircut-adjusted median volume.
  - Require at least 3 distinct adverse cells: cost x2 + 1% cap; cost x4 + 1% cap; cost x4 + 5% cap? Or cost x2/x4 with latency next-open? Need maybe "adverse cases" count only independent stress dimensions: high cost, low capacity, delayed entry. If latency cannot be resolved, don't count 1/5/15 as separate.
  - Report sensitivity not overfit.

Gold-plating:
  - Simulated tick reconstruction, Brownian bridge interpolation, using OHLCV to infer VWAP/intrabar fill; not defensible.
  - Per-minute latency precision from hourly data.
  - Complex market impact model without data.

Need answer "without fooling ourselves": emphasize no interpolation, no using entry-bar volume lookahead, don't count unresolvable latency variants, label assumptions, use conservative known data, maybe "if strategy depends on 1-15 min edge, hourly bars cannot validate; require probation only with caveat or fail".

Let's craft final under 300 words. Need concrete. Maybe use bullets.

Need ensure max 300 words. Count approximate. Let's draft ~270 words.

Potential final:

"1) Latency: With 1h OHLCV, do not interpolate. If signal uses bar k close, first executable price is open k+1. Thus 1/5/15 min slips are not identifiable; treat them as same '<1h latency' case and execute at next bar open. If you want an adverse fill for those slips, use a conservative envelope: long fill = max(open k+1, some fraction of bar high?) Hmm maybe not. Need be precise.

Maybe: "For the mandated 1/5/15min cases, either collapse them to one next-open case, or run them as identical next-open entries with an added deterministic slippage; do not claim they are measured." But user asks "enter at next bar open? interpolate?" Answer: next bar open is correct first executable. Interpolation not defensible. For 1/5/15, all map to next bar open if signal at close. If signal is assumed at bar open based on previous close, then latency 1h = next bar open. Need not overcomplicate.

But maybe "entry at next bar open" for 1min slip is too optimistic? If signal at close, next bar open is exactly after 0 latency. 1/5/15 min should be later in next bar, but we don't know. To not fool ourselves, next bar open is the optimistic lower bound; maybe add a small fixed bps slippage or use next bar close for "adverse <1h". But if cost multipliers already include slippage, maybe okay. Need maybe "do not pass based on the 1/5/15 distinction; require survival under next-open and cost/cap stresses."

Could say:
- "For long, optional conservative alternative: fill at next bar high; for short, next bar low. This is a worst-hour fill, not a 5/15-min fill. Use only as an extra adverse case." This addresses.

Volume:
- "Bar volume is a coarse proxy only. For alts, haircut 50-90%; use 10-30% of reported hourly volume as executable. Use median/rolling known volume, not final entry-bar volume, because entry-bar volume is lookahead. Exclude assets with median hourly volume below threshold."

Minimal:
- "Close-to-open replay, cost grid, one unresolved latency bucket, volume caps using known haircuted median volume, no tick reconstruction. Count only independent adverse cells; don't count x0.5 or three sub-hour slips as separate. Gold plating is intrabar interpolation/VWAP reconstruction/market impact without data."

Need include PF CI-LB >1.15 survive >=3 adverse cases: