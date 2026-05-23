#!/usr/bin/env python3
"""Update Baby Strat dashboard with all strategies."""

import json
from pathlib import Path

# Load existing JSON to preserve metrics
with open('incubator/config/baby_strats_dashboard.json') as f:
    existing = json.load(f)

existing_by_name = {}
for s in existing.get('strategies', []):
    name = s.get('name') or s.get('strategy_name')
    if name:
        existing_by_name[name] = s

# Scan all strategies
agents_path = Path('incubator/agents')
strategies = []

for agent_dir in sorted(agents_path.iterdir()):
    if agent_dir.is_dir():
        agent_name = agent_dir.name
        for py_file in sorted(agent_dir.glob('*.py')):
            if '__pycache__' in str(py_file) or py_file.name.startswith('test'):
                continue
            strat_name = py_file.stem
            
            if strat_name in existing_by_name:
                # Use existing data with metrics
                strategies.append(existing_by_name[strat_name])
            else:
                # New strategy - placeholder
                strategies.append({
                    'name': strat_name,
                    'agent_id': agent_name,
                    'category': 'unknown',
                    'status': 'validating',
                    'stage': 0,
                    'backtest_metrics': {
                        'win_rate': None,
                        'sharpe': None,
                        'max_drawdown': None,
                        'total_trades': 0,
                        'period_days': 180
                    },
                    'unique_value': f'Strategy by {agent_name}'
                })

# Build dashboard
dashboard = {
    'updated_at': '2026-02-26T22:45:00Z',
    'total_strategies': len(strategies),
    'passed_backtest': sum(1 for s in strategies if s.get('status') == 'backtest_passed'),
    'failed_backtest': sum(1 for s in strategies if s.get('status') == 'backtest_failed'),
    'in_paper_trading': sum(1 for s in strategies if s.get('status') == 'paper_trading'),
    'graduated': sum(1 for s in strategies if s.get('status') == 'graduated'),
    'strategies': strategies,
    'summary': {
        'total': len(strategies),
        'by_agent': {}
    }
}

# Count by agent
for s in strategies:
    agent = s.get('agent_id', 'unknown')
    dashboard['summary']['by_agent'][agent] = dashboard['summary']['by_agent'].get(agent, 0) + 1

with open('incubator/config/baby_strats_dashboard.json', 'w') as f:
    json.dump(dashboard, f, indent=2)

print(f'Updated dashboard with {len(strategies)} strategies')
print(f'By agent: {dashboard["summary"]["by_agent"]}')
