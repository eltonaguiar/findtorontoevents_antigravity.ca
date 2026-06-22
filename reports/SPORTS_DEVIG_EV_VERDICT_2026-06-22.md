# Goal #2 Sports — devig +EV edge-hunt verdict (2026-06-22)
**Author:** claude-opus · 5h cycle, fresh-domain pivot · ESPN-outcome-resolved · honest

## What was tested
Shin-devig +EV on real production odds (ejaguiar1_sportsbet, 44,071 rows, 342 h2h events). Anchor on Pinnacle (sharp) -> devig -> fair probs; +EV = soft-book price where fair*price-1 >= 2%; resolved vs ACTUAL game outcomes fetched from ESPN's public scoreboard API (130 Pinnacle-h2h events, 96 ESPN-resolved).

## Result — NO proven edge
- n=1,039 +EV bets across **46 events**; hit 48.9%; **ROI +8.68% point but CI-LB -9.1%** (90% CI [-9.1%, +26.7%], event-clustered). n_events=46 < the 100 bar.
- **Concentration-driven**: NHL (752 bets, the bulk) ROI **+0.3%** (flat, no edge); MLB (+40.6%) and NBA (+13.6%) on few events carry the headline -> a few-event fluke the cluster-bootstrap CI-LB correctly discounts to -9.1%.
- **Stale-snapshot caveat (decisive)**: these odds are a single last_updated snapshot, NOT verified closing lines. +EV vs a stale Pinnacle price is exactly the artifact that looks +EV but isn't (the soft book's "generous" price may reflect newer info than the stale sharp snapshot). The gold standard (CLV vs closing) is not measurable here.

## Verdict
Same dissolution pattern as every trading signal: an apparent positive (ROI +8.68%) collapses under proper event-clustering (CI-LB -9.1%) + concentration (MLB fluke) + the stale-line caveat. **No confirmable sports +EV edge on this data.**

## Outcome-starvation parallel
Sports is also outcome-limited: the dump's schedule tables are empty and the LIVE DB has only ~25 settled bets (344 arena bets still pending). The +EV backtest was only possible by fetching outcomes externally from ESPN — and even then, n_events=46 and the snapshot-line problem block a verdict.

## Honest bottom line across BOTH goals
Goal #1 (trading): no promotable alpha (every signal dissolves under power/clustering). Goal #2 (sports): no confirmable +EV edge (dissolves under clustering + stale-line). The constraint is consistent: **the available data lacks the resolution quality (closing lines / settled outcomes / point-in-time / price-path) needed to confirm an edge** — not a shortage of analysis. Remaining sports angles (totals/spreads, true CLV) need closing-line capture, which the snapshot lacks.
