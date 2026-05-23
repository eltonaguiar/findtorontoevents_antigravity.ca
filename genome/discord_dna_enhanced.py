#!/usr/bin/env python3
"""
Discord Enhanced DNA Signals
============================

Sends enhanced DNA-based signals to Discord with:
- Multi-symbol universal patterns
- Reverse-engineered winning setups  
- Expanded gene pool indicators
- Confidence scores from multiple validations

Usage:
    python discord_dna_enhanced.py --preview    # Preview in terminal
    python discord_dna_enhanced.py --send       # Send to Discord
"""

import json
import os
import requests
from datetime import datetime, timezone, timedelta
from typing import List, Dict
from pathlib import Path

# Discord webhooks
DISCORD_FRESHPICKS = os.environ.get("DISCORD_FRESHPICKS", os.environ.get("DISCORD_WEBHOOK_URL", ""))
DISCORD_MASTER_PICKS = os.environ.get("DISCORD_MASTER_PICKS", "")

def load_dna_signals() -> List[Dict]:
    """Load signals from all DNA sources."""
    signals = []
    
    # Load from master output
    master_path = Path('genome/results/dna_master_output.json')
    if master_path.exists():
        with open(master_path) as f:
            data = json.load(f)
            signals.extend(data.get('live_signals', []))
    
    # Load from universal signals
    universal_path = Path('genome/results/live_signals_universal.json')
    if universal_path.exists():
        with open(universal_path) as f:
            data = json.load(f)
            signals.extend(data.get('signals', []))
    
    # Remove duplicates by symbol+direction
    seen = set()
    unique = []
    for sig in signals:
        key = f"{sig.get('symbol')}_{sig.get('direction')}"
        if key not in seen:
            seen.add(key)
            unique.append(sig)
    
    # Sort by confidence
    unique.sort(key=lambda x: x.get('confidence', 0), reverse=True)
    
    return unique


def format_signal(signal: Dict) -> str:
    """Format a signal for Discord."""
    symbol = signal.get('symbol', 'UNKNOWN')
    direction = signal.get('direction', 'LONG')
    entry = signal.get('entry', 0)
    tp = signal.get('tp', 0)
    sl = signal.get('sl', 0)
    confidence = signal.get('confidence', 0)
    reason = signal.get('reason', 'DNA Pattern Match')
    
    # Calculate metrics
    tp_pct = abs(tp - entry) / entry * 100
    sl_pct = abs(entry - sl) / entry * 100
    r_r = tp_pct / sl_pct if sl_pct > 0 else 0
    
    # Emoji based on confidence
    if confidence >= 0.8:
        emoji = "🟢"
        tier = "MASTER"
    elif confidence >= 0.6:
        emoji = "🟡"
        tier = "FRESH"
    else:
        emoji = "⚪"
        tier = "PAPER"
    
    # Direction emoji
    dir_emoji = "🚀" if direction == "LONG" else "🔻"
    
    lines = [
        f"{emoji} **{symbol} {direction}** | {tier} PICK",
        f"{dir_emoji} Entry: `${entry:,.4f}`",
        f"🎯 TP: `${tp:,.4f}` (+{tp_pct:.1f}%)",
        f"🛡️ SL: `${sl:,.4f}` (-{sl_pct:.1f}%)",
        f"⚖️ R:R = {r_r:.1f}",
        f"📊 Confidence: {confidence:.0%}",
        f"💡 {reason}",
        ""
    ]
    
    return "\n".join(lines)


def send_to_discord(content: str, webhook_url: str):
    """Send message to Discord webhook."""
    if not webhook_url:
        print("No webhook URL configured")
        return False
    
    payload = {
        "content": content,
        "username": "DNA Enhanced Bot"
    }
    
    try:
        response = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        return response.status_code == 204
    except Exception as e:
        print(f"Failed to send: {e}")
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--preview', action='store_true', help='Preview only')
    parser.add_argument('--send', action='store_true', help='Send to Discord')
    args = parser.parse_args()
    
    # Load signals
    signals = load_dna_signals()
    
    if not signals:
        print("No DNA signals found. Run the DNA analysis first:")
        print("  python genome/run_all_dna_variations.py")
        return
    
    print(f"Loaded {len(signals)} DNA signals")
    
    # Separate by confidence
    master_picks = [s for s in signals if s.get('confidence', 0) >= 0.8][:5]
    fresh_picks = [s for s in signals if 0.6 <= s.get('confidence', 0) < 0.8][:10]
    
    # Format messages
    est = timezone(timedelta(hours=-5))
    timestamp = datetime.now(est).strftime("%b %d, %Y %I:%M %p EST")
    
    if master_picks:
        master_content = [
            "🧬 **ENHANCED DNA MASTER PICKS** 🧬",
            f"*Multi-symbol universal patterns | {timestamp}*",
            "",
            "🏆 **High Confidence Signals (≥80%)**",
            ""
        ]
        
        for sig in master_picks:
            master_content.append(format_signal(sig))
        
        master_content.extend([
            "",
            "📊 *These patterns showed consistency across 20+ symbols*",
            "⚠️ *Not financial advice - DYOR*"
        ])
        
        master_message = "\n".join(master_content)
        
        if args.preview:
            print("\n" + "="*60)
            print("MASTER PICKS (would go to #master-picks)")
            print("="*60)
            print(master_message)
        
        if args.send and DISCORD_MASTER_PICKS:
            if send_to_discord(master_message, DISCORD_MASTER_PICKS):
                print("✅ Master picks sent to Discord")
    
    if fresh_picks:
        fresh_content = [
            "🧬 **ENHANCED DNA FRESH PICKS** 🧬",
            f"*Reverse-engineered winning setups | {timestamp}*",
            "",
            "🌱 **Medium Confidence Signals (60-79%)**",
            ""
        ]
        
        for sig in fresh_picks:
            fresh_content.append(format_signal(sig))
        
        fresh_content.extend([
            "",
            "📊 *Patterns that would have won today*",
            "⚠️ *Paper trade first - validate forward*"
        ])
        
        fresh_message = "\n".join(fresh_content)
        
        if args.preview:
            print("\n" + "="*60)
            print("FRESH PICKS (would go to #freshpicks)")
            print("="*60)
            print(fresh_message)
        
        if args.send and DISCORD_FRESHPICKS:
            if send_to_discord(fresh_message, DISCORD_FRESHPICKS):
                print("✅ Fresh picks sent to Discord")
    
    if not args.preview and not args.send:
        print("\nUse --preview to see signals or --send to post to Discord")
        print(f"\nFound {len(master_picks)} master picks and {len(fresh_picks)} fresh picks")


if __name__ == "__main__":
    main()
