#!/usr/bin/env python3
"""
Early Warning System - Monitor all prediction systems for degradation
"""

import argparse
import json
import sys
import requests
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unified_prediction_ledger import UnifiedPredictionLedger, EarlyWarningSystem
from mysql_core import MySQLDatabase


def send_discord_alert(webhook_url: str, alerts: list):
    """Send warning to Discord"""
    if not webhook_url or not alerts:
        return
    
    embeds = []
    for alert in alerts:
        color = 15158332 if alert['severity'] == 'HIGH' else 16776960  # Red or Yellow
        embeds.append({
            'title': f"⚠️ {alert['severity']} Alert: {alert['system']}",
            'color': color,
            'fields': [
                {'name': 'Issues', 'value': '\n'.join(alert['warnings']), 'inline': False},
                {'name': 'Win Rate', 'value': f"{alert['metrics']['win_rate']:.1f}%", 'inline': True},
                {'name': 'Avg P&L', 'value': f"{alert['metrics']['avg_pnl']:.2f}%", 'inline': True},
                {'name': 'Sample Size', 'value': str(alert['metrics']['total_predictions']), 'inline': True}
            ],
            'timestamp': datetime.now().isoformat()
        })
    
    payload = {
        'content': 'Prediction System Alert',
        'embeds': embeds
    }
    
    try:
        requests.post(webhook_url, json=payload, timeout=10)
    except Exception as e:
        print(f"Failed to send Discord alert: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--db-host', required=True)
    parser.add_argument('--db-user', required=True)
    parser.add_argument('--db-pass', required=True)
    parser.add_argument('--db-name', default='ejaguiar1_memecoin')
    parser.add_argument('--webhook', help='Discord webhook URL')
    
    args = parser.parse_args()
    
    # Connect to database
    db = MySQLDatabase()
    db.config['host'] = args.db_host
    db.config['user'] = args.db_user
    db.config['password'] = args.db_pass
    db.config['database'] = args.db_name
    
    # Create warning system
    ledger = UnifiedPredictionLedger(db)
    warning_system = EarlyWarningSystem(ledger)
    
    # Check all systems
    print("Checking all systems for warnings...")
    alerts = warning_system.check_all_systems()
    
    if alerts:
        print(f"\n⚠️  {len(alerts)} system(s) with warnings:")
        for alert in alerts:
            print(f"\n  {alert['system']} ({alert['severity']}):")
            for warning in alert['warnings']:
                print(f"    - {warning}")
        
        # Send Discord alert if webhook provided
        if args.webhook:
            send_discord_alert(args.webhook, alerts)
        
        sys.exit(1)  # Exit with error to trigger notification
    else:
        print("✓ All systems healthy")
        sys.exit(0)


if __name__ == '__main__':
    main()
