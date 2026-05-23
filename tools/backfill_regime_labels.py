#!/usr/bin/env python3
# /// script
# requires-python = >=3.11
# ///
# pyright: reportUnknownMemberType=false, reportUnusedVariable=false
# ruff: noqa S101
#
# Regime backfill for closed_picks.json and active_picks.json.
#
# Reads alpha_engine/data/regime_report.json and writes regime labels to
# any pick that doesn't already have one.
#
#   - closed_picks.json: backfill by entry_time / opened_at / created_at
#   - active_picks.json: backfill by created_at / timestamp
#     (new picks get stamped at scan time by production_scanner.py;
#     this catches historical ones still missing regime)
#
# Priority:
#   1. Match pick entry_time against regime_windows from regime_report.json
#   2. If 0 windows loaded AND 0 picks labeled → use _current_regime (from
#      regime_report.json top-level) as fallback — prevents all 153 picks
#      getting UNKNOWN when regime_report only has current-state, no history
#   3. UNKNOWN only when neither 1 nor 2 applies (mismatch between modes)
#
# Writes atomically: temp file first, then shutil.move on success.
#
# Usage:
#   python tools/backfill_regime_labels.py [--dry-run]
#   python tools/backfill_regime_labels.py --active-only [--dry-run]
#   python tools/backfill_regime_labels.py --closed-only [--dry-run]

import datetime
import json
import shutil
import sys
from pathlib import Path

CLOSED_PATH = Path('alpha_engine/data/closed_picks.json')
ACTIVE_PATH = Path('alpha_engine/data/active_picks.json')
REGIME_PATH = Path('alpha_engine/data/regime_report.json')
BACKUP_SUFFIX = '.bak.regime_backfill'

# Module-level state set by run()
_regime_windows: list = []
_current_regime: str = 'CHOPPY'


def load_regime() -> dict | None:
    if not REGIME_PATH.exists():
        return None
    with open(REGIME_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def _classify_from_entry_time(entry_time: str, windows: list) -> str | None:
    try:
        entry_dt = datetime.datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
    except Exception:
        return None
    for window in windows:
        start_str = window.get('start') or window.get('start_time')
        end_str   = window.get('end')   or window.get('end_time')
        if not start_str or not end_str:
            continue
        try:
            start_dt = datetime.datetime.fromisoformat(start_str.replace('Z', '+00:00'))
            end_dt   = datetime.datetime.fromisoformat(end_str.replace('Z', '+00:00'))
            if start_dt <= entry_dt <= end_dt:
                return window.get('regime') or window.get('label') or window.get('state')
        except Exception:
            continue
    return None


def _classify_pick(pick: dict) -> str | None:
    for field in ('entry_time', 'opened_at', 'created_at', 'timestamp'):
        et = pick.get(field)
        if not et:
            continue
        regime = _classify_from_entry_time(et, _regime_windows)
        if regime:
            return regime
    return None


def backfill_file(path: Path, dry_run: bool = False) -> dict:
    global _current_regime, _regime_windows

    today = datetime.date.today().isoformat()
    with open(path, 'r', encoding='utf-8') as f:
        picks = json.load(f)

    labeled = skipped = defaults = from_current = 0
    for pick in picks:
        if pick.get('regime') or pick.get('_regime') or pick.get('regime_label'):
            skipped += 1
            continue
        regime = _classify_pick(pick)
        if regime:
            pick['regime'] = regime
            labeled += 1
        else:
            pick['regime'] = 'UNKNOWN'
            defaults += 1

    # Fallback: regime_report.json has no historical windows (0 loaded) AND
    # window-matching labeled 0 picks → use current regime for all unmatched.
    # This handles the common case where regime_report is a current-snapshot
    # file with no 'windows' array (most GHA regime pipelines produce this).
    if labeled == 0 and defaults > 0 and len(_regime_windows) == 0:
        current = _current_regime
        for pick in picks:
            if pick.get('regime') == 'UNKNOWN':
                pick['regime'] = current
                pick['regime_source'] = f'current_regime_fallback_{today}'
                from_current += 1
        defaults -= from_current
        labeled += from_current
        print(f'  [fallback] Applied current_regime={current} to {from_current} UNKNOWN picks')

    stats = {
        'labeled': labeled,
        'skipped': skipped,
        'defaults': defaults,
        'from_current_regime': from_current,
        'total': len(picks),
    }
    print(
        f'[{path.name}] Labeled: {labeled} | Already had: {skipped} '
        f'| UNKNOWN: {defaults} | Total: {len(picks)}'
    )

    if dry_run:
        print(f'  [dry-run] No changes written.')
        return stats

    backup = path.with_suffix(path.suffix + BACKUP_SUFFIX)
    shutil.copy2(path, backup)
    print(f'  Backup: {backup}')

    tmp = path.with_suffix('.tmp.regime_backfill.json')
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(picks, f, indent=2, ensure_ascii=False)
    shutil.move(str(tmp), str(path))  # Works on Windows even when dst exists
    print(f'  Written: {path}')
    return stats


def run(dry_run: bool = False, mode: str = 'both') -> None:
    global _regime_windows, _current_regime

    regime_doc = load_regime()
    if not regime_doc:
        print('ERROR: regime_report.json not found')
        return

    _regime_windows = (
        regime_doc.get('windows', []) or
        regime_doc.get('regime_windows', []) or
        regime_doc.get('data', [])
    )
    _current_regime = (
        regime_doc.get('current_regime') or
        regime_doc.get('regime') or
        regime_doc.get('label') or
        'CHOPPY'
    )
    print(f'Loaded {len(_regime_windows)} regime windows (fallback: {_current_regime})')

    if mode in ('both', 'closed'):
        if CLOSED_PATH.exists():
            backfill_file(CLOSED_PATH, dry_run)
        else:
            print(f'SKIP: {CLOSED_PATH} not found')

    if mode in ('both', 'active'):
        if ACTIVE_PATH.exists():
            backfill_file(ACTIVE_PATH, dry_run)
        else:
            print(f'SKIP: {ACTIVE_PATH} not found')


if __name__ == '__main__':
    mode = 'both'
    dry = False
    for arg in sys.argv[1:]:
        if arg in ('--dry-run', '-n'):
            dry = True
        elif arg == '--active-only':
            mode = 'active'
        elif arg == '--closed-only':
            mode = 'closed'
    run(dry_run=dry, mode=mode)