import json

with open(
    "E:/findtorontoevents_antigravity.ca/data/goldmine/closed_trades.json", "r"
) as f:
    data = json.load(f)

trades = data["trades"]
wins = [t for t in trades if t["outcome"] == "WIN"]
losses = [t for t in trades if t["outcome"] == "LOSS"]

print("=== TRADE SUMMARY ===")
print(f"Total closed trades: {len(trades)}")
print(f"Winning trades: {len(wins)}")
print(f"Losing trades: {len(losses)}")
print(f"Win rate: {len(wins) / len(trades) * 100:.1f}%")

print("\n=== TOP 10 WINNING PICKS ===")
for t in sorted(wins, key=lambda x: -x["final_return_pct"])[:10]:
    print(
        f"{t['ticker']:6} | Entry: {t['entry_price']:8.2f} | Exit: {t['exit_price']:8.2f} | PnL: {t['final_return_pct']:6.2f}% | {t['entry_date'][:10]} → {t['exit_date'][:10]}"
    )

print("\n=== TOP 10 WORST PICKS (FILTER THESE OUT) ===")
for t in sorted(losses, key=lambda x: x["final_return_pct"])[:10]:
    score = t["algorithms"][0]["score"] if t["algorithms"] else "N/A"
    print(
        f"{t['ticker']:6} | Entry: {t['entry_price']:8.2f} | Exit: {t['exit_price']:8.2f} | PnL: {t['final_return_pct']:6.2f}% | Algos: {t['algo_count']} | Score: {score}"
    )

print("\n=== SCORE PERFORMANCE BREAKDOWN ===")
score_bands = [(0, 39, 0), (40, 54, 0), (55, 69, 0), (70, 84, 0), (85, 100, 0)]

for low, high, wins in score_bands:
    band_trades = []
    for t in trades:
        if not t["algorithms"]:
            continue
        score = t["algorithms"][0]["score"]
        if low <= score <= high:
            band_trades.append(t)
    if band_trades:
        win_count = sum(1 for t in band_trades if t["outcome"] == "WIN")
        avg_pnl = sum(t["final_return_pct"] for t in band_trades) / len(band_trades)
        print(
            f"Score {low}-{high}: {len(band_trades)} trades | Win rate: {win_count / len(band_trades) * 100:.1f}% | Avg PnL: {avg_pnl:+.2f}%"
        )
