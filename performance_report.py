import sqlite3
conn = sqlite3.connect('incubator/forward_test.db')
cursor = conn.cursor()

print('🎯 CURRENT BABY STRATEGY PERFORMANCE REPORT')
print('=' * 60)

# Get all positions with current status
cursor.execute('''
SELECT strategy_name, symbol, direction, entry_price, take_profit, stop_loss,
       confidence, status, pnl_pct, exit_reason
FROM forward_signals
ORDER BY
    CASE WHEN status = 'OPEN' THEN 0 ELSE 1 END,
    strategy_name
''')

positions = cursor.fetchall()

open_positions = [p for p in positions if p[7] == 'OPEN']
closed_positions = [p for p in positions if p[7] == 'CLOSED']

print(f'\n📊 OVERVIEW:')
print(f'  Total Positions: {len(positions)}')
print(f'  Open Positions: {len(open_positions)}')
print(f'  Closed Positions: {len(closed_positions)}')

if closed_positions:
    wins = sum(1 for p in closed_positions if p[8] and p[8] > 0)
    losses = len(closed_positions) - wins
    total_pnl = sum(p[8] for p in closed_positions if p[8])
    avg_pnl = total_pnl / len(closed_positions) if closed_positions else 0
    print(f'  Wins: {wins} | Losses: {losses} | Win Rate: {wins/len(closed_positions)*100:.1f}%')
    print(f'  Total P&L: {total_pnl:+.2f}% | Average P&L: {avg_pnl:+.2f}%')

print(f'\n📈 OPEN POSITIONS ({len(open_positions)}):')
for pos in open_positions[:5]:  # Show first 5
    strategy, symbol, direction, entry, tp, sl, conf, status, pnl, exit_reason = pos
    print(f'  {strategy[:30]:<30} | {symbol} {direction} | Entry: ${entry or 0:.2f} | Conf: {conf or 0:.1f}%')

if len(open_positions) > 5:
    print(f'  ... and {len(open_positions)-5} more open positions')

print(f'\n✅ CLOSED POSITIONS ({len(closed_positions)}):')
for pos in closed_positions:
    strategy, symbol, direction, entry, tp, sl, conf, status, pnl, exit_reason = pos
    result = 'WIN' if (pnl and pnl > 0) else 'LOSS'
    exit_reason_str = exit_reason or "UNKNOWN"
    print(f'  {strategy[:30]:<30} | {symbol} {direction} | P&L: {pnl or 0:+.2f}% | {result} ({exit_reason_str})')

# Strategy performance breakdown
print(f'\n📊 STRATEGY PERFORMANCE BREAKDOWN:')
cursor.execute('''
SELECT strategy_name,
       COUNT(*) as total,
       SUM(CASE WHEN status = 'CLOSED' AND pnl_pct > 0 THEN 1 ELSE 0 END) as wins,
       SUM(CASE WHEN status = 'CLOSED' AND pnl_pct <= 0 THEN 1 ELSE 0 END) as losses,
       AVG(CASE WHEN status = 'CLOSED' THEN pnl_pct ELSE NULL END) as avg_pnl,
       COUNT(CASE WHEN status = 'OPEN' THEN 1 ELSE NULL END) as open_count
FROM forward_signals
GROUP BY strategy_name
ORDER BY total DESC
''')

strategy_stats = cursor.fetchall()
for strategy, total, wins, losses, avg_pnl, open_count in strategy_stats:
    win_rate = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0
    avg_pnl_str = f"{avg_pnl or 0:+.2f}%" if avg_pnl else "N/A"
    print(f'  {strategy[:25]:<25} | Total: {total} | Open: {open_count} | Closed: {wins+losses} | Wins: {wins} | Losses: {losses} | Win%: {win_rate:.1f}% | Avg P&L: {avg_pnl_str}')

conn.close()