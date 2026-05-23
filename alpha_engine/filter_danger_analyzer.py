#!/usr/bin/env python3
"""
Filter Danger Analyzer — identifies dangerous filter values from closed pick data.

Analyzes all closed picks and flags filter options that are proven losers,
so the audit dashboard can show warning emojis next to them.

Standalone runnable: python alpha_engine/filter_danger_analyzer.py
"""
import sys, os, json
from datetime import datetime, timezone
from pathlib import Path

# Windows UTF-8 fix
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Resolve paths
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
PAYLOAD_PATH = REPO_ROOT / 'audit_trail' / 'data' / 'dashboard_payload.json'
OUTPUT_PATH = SCRIPT_DIR / 'data' / 'filter_danger_report.json'


def load_closed_picks():
    """Load closed picks from dashboard_payload.json."""
    if not PAYLOAD_PATH.exists():
        print(f"[FilterDanger] Payload not found at {PAYLOAD_PATH}")
        return []

    with open(PAYLOAD_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    picks = data.get('picks', {}).get('recent_closed', [])
    print(f"[FilterDanger] Loaded {len(picks)} closed picks")
    return picks


def compute_stats(picks):
    """Compute WR, avg PnL, total PnL for a list of picks."""
    if not picks:
        return {'trades': 0, 'wr': 0.0, 'avg_pnl': 0.0, 'total_pnl': 0.0}

    wins = sum(1 for p in picks if p.get('status') == 'WON')
    losses = sum(1 for p in picks if p.get('status') == 'LOST')
    total_decided = wins + losses
    wr = (wins / total_decided * 100) if total_decided > 0 else 0.0

    pnls = [p.get('pnl_pct', 0) or 0 for p in picks]
    avg_pnl = sum(pnls) / len(pnls) if pnls else 0.0
    total_pnl = sum(pnls)

    return {
        'trades': len(picks),
        'wr': round(wr, 1),
        'avg_pnl': round(avg_pnl, 2),
        'total_pnl': round(total_pnl, 2)
    }


def classify_danger(stats):
    """Classify as DANGER, CAUTION, or None."""
    if stats['trades'] < 10:
        return None
    if stats['wr'] < 35 and stats['avg_pnl'] < -0.5:
        return 'DANGER'
    if stats['wr'] < 45 and stats['avg_pnl'] < 0:
        return 'CAUTION'
    return None


def analyze_confidence(picks):
    """Analyze confidence tiers."""
    tiers = {
        '<0.50': lambda p: (p.get('confidence') or 0) < 0.50,
        '0.50-0.65': lambda p: 0.50 <= (p.get('confidence') or 0) < 0.65,
        '0.65-0.75': lambda p: 0.65 <= (p.get('confidence') or 0) < 0.75,
        '0.75-0.85': lambda p: 0.75 <= (p.get('confidence') or 0) < 0.85,
        '>=0.85': lambda p: (p.get('confidence') or 0) >= 0.85,
    }

    reasons = {
        '<0.50': 'Very low confidence picks are right to be uncertain \u2014 they lose {wr_loss}% of the time.',
        '0.50-0.65': 'Below-average confidence. Consider waiting for higher-conviction setups.',
        '0.65-0.75': 'Moderate confidence picks with below-average returns.',
        '0.75-0.85': 'The sweet spot \u2014 best risk-adjusted returns historically.',
        '>=0.85': 'Overconfident picks lose {wr_loss}% of the time. The 0.75-0.85 range is the only profitable confidence tier.',
    }

    results = {}
    for tier_name, filter_fn in tiers.items():
        tier_picks = [p for p in picks if filter_fn(p)]
        stats = compute_stats(tier_picks)
        level = classify_danger(stats)
        if level:
            wr_loss = round(100 - stats['wr'], 0)
            reason = reasons.get(tier_name, '').format(wr_loss=wr_loss)
            results[tier_name] = {**stats, 'level': level, 'reason': reason}

    return results


def analyze_asset_class(picks):
    """Analyze asset class performance."""
    classes = set(p.get('asset_class', '') for p in picks if p.get('asset_class'))

    reasons = {
        'EQUITY': 'Stock picks have {wr}% WR and {avg_pnl}% avg PnL. Our system works much better on crypto.',
        'FOREX': 'Forex picks have {wr}% WR and {avg_pnl}% avg PnL in the current regime.',
        'CRYPTO': 'Crypto picks showing {wr}% WR and {avg_pnl}% avg PnL.',
    }

    results = {}
    for cls in classes:
        cls_picks = [p for p in picks if p.get('asset_class') == cls]
        stats = compute_stats(cls_picks)
        level = classify_danger(stats)
        if level:
            reason = reasons.get(cls, '{cls} has {wr}% WR and {avg_pnl}% avg PnL.').format(
                cls=cls, wr=stats['wr'], avg_pnl=stats['avg_pnl'])
            results[cls] = {**stats, 'level': level, 'reason': reason}

    return results


def analyze_timeframe(picks):
    """Analyze trade timeframe performance."""
    timeframes = set(p.get('trade_timeframe', '') for p in picks if p.get('trade_timeframe'))

    reasons = {
        'INTRADAY': 'Intraday trades are our biggest losing category by volume. SWING and SCALP perform better.',
        'SWING': 'Swing trades showing {wr}% WR and {avg_pnl}% avg PnL.',
        'SCALP': 'Scalp trades have {wr}% WR and {avg_pnl}% avg PnL.',
        'POSITION': 'Position trades have {wr}% WR and {avg_pnl}% avg PnL.',
    }

    results = {}
    for tf in timeframes:
        tf_picks = [p for p in picks if p.get('trade_timeframe') == tf]
        stats = compute_stats(tf_picks)
        level = classify_danger(stats)
        if level:
            reason = reasons.get(tf, '{tf} has {wr}% WR and {avg_pnl}% avg PnL.').format(
                tf=tf, wr=stats['wr'], avg_pnl=stats['avg_pnl'])
            results[tf] = {**stats, 'level': level, 'reason': reason}

    return results


def analyze_direction(picks):
    """Analyze direction performance."""
    directions = set(p.get('direction', '') for p in picks if p.get('direction'))

    reasons = {
        'SHORT': 'Shorts have decent WR but larger losses when wrong. Prefer LONG in current market.',
        'LONG': 'Long picks showing {wr}% WR and {avg_pnl}% avg PnL.',
    }

    results = {}
    for d in directions:
        d_picks = [p for p in picks if p.get('direction') == d]
        stats = compute_stats(d_picks)
        level = classify_danger(stats)
        if level:
            reason = reasons.get(d, '{d} has {wr}% WR and {avg_pnl}% avg PnL.').format(
                d=d, wr=stats['wr'], avg_pnl=stats['avg_pnl'])
            results[d] = {**stats, 'level': level, 'reason': reason}

    return results


def analyze_score_tier(picks):
    """Analyze score tier performance."""
    tiers = {
        '<30': lambda p: (p.get('score') or 0) < 30,
        '30-49': lambda p: 30 <= (p.get('score') or 0) < 50,
        '50-69': lambda p: 50 <= (p.get('score') or 0) < 70,
        '70+': lambda p: (p.get('score') or 0) >= 70,
    }

    reasons = {
        '<30': 'Ultra-low score picks win only {wr}% of the time. Score >= 50 is the minimum for any edge.',
        '30-49': 'Below-threshold picks at {wr}% WR and {avg_pnl}% avg. Paper trade zone only.',
        '50-69': 'Mid-tier scores with {wr}% WR \u2014 tradeable but watch sizing.',
        '70+': 'High conviction at {wr}% WR and {avg_pnl}% avg PnL.',
    }

    results = {}
    for tier_name, filter_fn in tiers.items():
        tier_picks = [p for p in picks if filter_fn(p)]
        stats = compute_stats(tier_picks)
        level = classify_danger(stats)
        if level:
            reason = reasons.get(tier_name, '').format(wr=stats['wr'], avg_pnl=stats['avg_pnl'])
            results[tier_name] = {**stats, 'level': level, 'reason': reason}

    return results


def analyze_source_system(picks):
    """Analyze source system performance."""
    systems = set(p.get('source_system', '') for p in picks if p.get('source_system'))

    results = {}
    for sys_name in systems:
        sys_picks = [p for p in picks if p.get('source_system') == sys_name]
        stats = compute_stats(sys_picks)
        level = classify_danger(stats)
        if level:
            reason = f'{sys_name} system has {stats["wr"]}% WR and {stats["avg_pnl"]}% avg PnL across {stats["trades"]} trades.'
            results[sys_name] = {**stats, 'level': level, 'reason': reason}

    return results


def main():
    picks = load_closed_picks()
    if not picks:
        print("[FilterDanger] No closed picks found, skipping analysis")
        return

    report = {
        'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'total_analyzed': len(picks),
        'dangers': {}
    }

    # Run all analyses
    analyses = {
        'confidence': analyze_confidence,
        'asset_class': analyze_asset_class,
        'timeframe': analyze_timeframe,
        'direction': analyze_direction,
        'score_tier': analyze_score_tier,
        'source_system': analyze_source_system,
    }

    danger_count = 0
    caution_count = 0

    for category, analyzer in analyses.items():
        result = analyzer(picks)
        if result:
            report['dangers'][category] = result
            for v in result.values():
                if v.get('level') == 'DANGER':
                    danger_count += 1
                elif v.get('level') == 'CAUTION':
                    caution_count += 1

    report['summary'] = {
        'danger_count': danger_count,
        'caution_count': caution_count,
        'total_flags': danger_count + caution_count
    }

    # Save report
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"[FilterDanger] Report saved to {OUTPUT_PATH}")
    print(f"[FilterDanger] Found {danger_count} DANGER + {caution_count} CAUTION flags")

    # Print summary
    for cat, items in report['dangers'].items():
        for key, info in items.items():
            emoji = '\U0001f5d1\ufe0f' if info['level'] == 'DANGER' else '\u26a0\ufe0f'
            print(f"  {emoji} {cat}/{key}: {info['wr']}% WR, {info['avg_pnl']}% avg ({info['trades']} trades)")


if __name__ == '__main__':
    main()
