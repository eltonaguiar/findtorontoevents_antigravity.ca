#!/usr/bin/env python3
'''
backtest_runner.py — Retro-run the production value-bet algorithm against
historical odds + grade against historical results.

This is a pure-Python code generator. It does NOT connect to MySQL itself;
instead it emits two artifacts an operator runs on the DB host:

  1. <run_id>.sql  — INSERTs for historical odds into lm_sports_odds_historical,
                     plus the lm_sports_backtest_runs row.
  2. <run_id>.sh   — Shell script that invokes
                     `php sports_value_analyze_cli.php --as-of ... --run-id ...`
                     once per historical event, then runs a final grading SQL
                     block to set actual_outcome / actual_pnl on the synthetic
                     bets by joining against historical game results.

Why a code generator instead of direct DB access:
  - Keeps Python free of MySQL deps (matches existing scrapers in this dir).
  - Uses the existing PHP credentials path (db_config.php on the prod host).
  - Easy to inspect the generated SQL/shell before running anything.
  - Same operator workflow as the existing OddsHarvester / sportsdataverse
    scripts: --save-json now, decide later when to inject.

Inputs (one of each, can be repeated):
  --odds-json <path>     OddsHarvester JSON (or directory of JSONs) with
                         historical bookmaker quotes per event.
  --results-json <path>  sportsdataverse_backfill.py JSON (or directory)
                         with home_score / away_score per game.

Outputs:
  --out-dir <dir>        Default: live-monitor/backfill/backtests/
                         Writes <run_id>.sql, <run_id>.sh, <run_id>.manifest.json

Run-id is auto-generated: bt_<UTC date>_<6-hex>. Override with --run-id.

Usage:
  # Generate artifacts
  python3 live-monitor/sportsbetting_lib/backtest_runner.py \\
      --odds-json    live-monitor/backfill/clv/ \\
      --results-json live-monitor/backfill/ \\
      --sports nba,nhl --start-date 2024-10-01 --end-date 2025-04-15

  # Then on the DB host:
  mysql -u <user> -p <db> < live-monitor/backfill/backtests/bt_20260425_a1b2.sql
  bash live-monitor/backfill/backtests/bt_20260425_a1b2.sh
'''

from __future__ import annotations

import argparse
import datetime
import glob
import hashlib
import json
import os
import sys
from typing import Any, Dict, Iterable, List, Optional, Tuple


# ---- Loading inputs ----------------------------------------------------------

def _iter_json_files(path: str) -> Iterable[str]:
    if os.path.isdir(path):
        for fp in sorted(glob.glob(os.path.join(path, '*.json'))):
            yield fp
    elif os.path.isfile(path):
        yield path


def _load_jsons(paths: List[str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for p in paths:
        for fp in _iter_json_files(p):
            try:
                with open(fp, 'r', encoding='utf-8') as fh:
                    payload = json.load(fh)
            except (OSError, ValueError) as e:
                print(f'[warn] could not read {fp}: {e}', file=sys.stderr)
                continue
            out.append({'_path': fp, 'payload': payload})
    return out


def _norm_sport(s: str) -> str:
    s = (s or '').lower().strip()
    aliases = {
        'nba': 'basketball_nba',
        'nhl': 'icehockey_nhl',
        'nfl': 'americanfootball_nfl',
        'mlb': 'baseball_mlb',
        'cfl': 'americanfootball_cfl',
        'mls': 'soccer_usa_mls',
    }
    return aliases.get(s, s)


# ---- Odds extraction ---------------------------------------------------------
# OddsHarvester output isn't formally specced here; we accept several shapes:
#   {'rows': [...]} or {'events': [...]} or a bare list. Each row may be:
#   - flat: event_id, bookmaker_key, market, outcome_name, outcome_price, ...
#   - nested: event {bookmakers: [{markets: [{outcomes: [...]}]}]}

def _flatten_event(ev: Dict[str, Any], default_sport: str = '') -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    eid = ev.get('event_id') or ev.get('id') or ev.get('eid') or ''
    sport = _norm_sport(ev.get('sport') or default_sport or '')
    home = ev.get('home_team') or ev.get('home') or ''
    away = ev.get('away_team') or ev.get('away') or ''
    commence = ev.get('commence_time') or ev.get('start_time') or ev.get('gameday') or ''
    bookmakers = ev.get('bookmakers') or []
    if isinstance(bookmakers, list) and bookmakers:
        for b in bookmakers:
            bk_key = b.get('key') or b.get('bookmaker_key') or b.get('book') or ''
            bk_name = b.get('name') or b.get('bookmaker') or bk_key
            for m in b.get('markets', []):
                mkt = m.get('key') or m.get('market') or 'h2h'
                for o in m.get('outcomes', []):
                    rows.append({
                        'event_id': str(eid),
                        'sport': sport,
                        'home_team': home,
                        'away_team': away,
                        'commence_time': commence,
                        'bookmaker': bk_name,
                        'bookmaker_key': bk_key,
                        'market': mkt,
                        'outcome_name': o.get('name') or o.get('outcome_name') or '',
                        'outcome_price': float(o.get('price') or o.get('outcome_price') or 0),
                        'outcome_point': o.get('point'),
                        'snapshot_kind': ev.get('snapshot_kind', 'close'),
                        'snapshot_at': ev.get('snapshot_at'),
                        'source': ev.get('source', 'oddsharvester'),
                    })
    elif 'outcome_price' in ev:
        rows.append({
            'event_id': str(eid),
            'sport': sport,
            'home_team': home,
            'away_team': away,
            'commence_time': commence,
            'bookmaker': ev.get('bookmaker', ''),
            'bookmaker_key': ev.get('bookmaker_key', ''),
            'market': ev.get('market', 'h2h'),
            'outcome_name': ev.get('outcome_name', ''),
            'outcome_price': float(ev.get('outcome_price', 0)),
            'outcome_point': ev.get('outcome_point'),
            'snapshot_kind': ev.get('snapshot_kind', 'close'),
            'snapshot_at': ev.get('snapshot_at'),
            'source': ev.get('source', 'oddsharvester'),
        })
    return rows


def collect_odds_rows(payloads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for entry in payloads:
        payload = entry['payload']
        default_sport = payload.get('sport', '') if isinstance(payload, dict) else ''
        events: List[Dict[str, Any]] = []
        if isinstance(payload, list):
            events = payload
        elif isinstance(payload, dict):
            events = payload.get('events') or payload.get('rows') or []
        for ev in events:
            if isinstance(ev, dict):
                rows.extend(_flatten_event(ev, default_sport))
    return rows


# ---- Results extraction ------------------------------------------------------
# sportsdataverse_backfill.py emits: {sport, event_id, home_team, away_team,
# commence_time, home_score, away_score, winner, spread_line, total_line, ...}

def collect_result_rows(payloads: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    by_eid: Dict[str, Dict[str, Any]] = {}
    for entry in payloads:
        payload = entry['payload']
        rows = []
        if isinstance(payload, dict):
            rows = payload.get('rows') or []
        elif isinstance(payload, list):
            rows = payload
        for r in rows:
            if not isinstance(r, dict):
                continue
            eid = str(r.get('event_id') or '')
            if not eid:
                continue
            by_eid[eid] = r
    return by_eid


# ---- Filtering ---------------------------------------------------------------

def _parse_iso_date(s: str) -> Optional[datetime.date]:
    if not s:
        return None
    s = s[:10]
    try:
        return datetime.datetime.strptime(s, '%Y-%m-%d').date()
    except ValueError:
        return None


def _row_within_window(commence_time: str, start: Optional[datetime.date],
                       end: Optional[datetime.date]) -> bool:
    d = _parse_iso_date(commence_time)
    if d is None:
        return False
    if start and d < start:
        return False
    if end and d > end:
        return False
    return True


# ---- SQL emission ------------------------------------------------------------

def _sql_str(v: Any) -> str:
    if v is None:
        return 'NULL'
    s = str(v)
    return "'" + s.replace('\\', '\\\\').replace("'", "''") + "'"


def _sql_num(v: Any) -> str:
    if v is None or v == '':
        return 'NULL'
    try:
        return str(float(v))
    except (TypeError, ValueError):
        return 'NULL'


def _normalize_commence(s: str) -> str:
    '''sportsdataverse uses YYYY-MM-DD; OddsHarvester uses ISO 8601 with TZ.
    MySQL DATETIME wants YYYY-MM-DD HH:MM:SS in UTC.'''
    if not s:
        return '1970-01-01 00:00:00'
    s = s.strip().replace('T', ' ').replace('Z', '')
    s = s.split('+')[0].split('.')[0]
    if len(s) == 10:
        s += ' 00:00:00'
    elif len(s) == 16:
        s += ':00'
    return s[:19]


def emit_odds_inserts(rows: List[Dict[str, Any]], out_fh, batch_size: int = 200) -> int:
    cols = ('sport', 'event_id', 'home_team', 'away_team', 'commence_time',
            'bookmaker', 'bookmaker_key', 'market', 'outcome_name',
            'outcome_price', 'outcome_point', 'snapshot_kind', 'snapshot_at',
            'source')
    header = ('INSERT IGNORE INTO `lm_sports_odds_historical`\n  ('
              + ', '.join('`' + c + '`' for c in cols) + ')\nVALUES\n  ')
    written = 0
    batch: List[str] = []
    for r in rows:
        # Skip obviously bad data.
        if not r.get('event_id') or not r.get('bookmaker_key'):
            continue
        try:
            price = float(r.get('outcome_price', 0))
        except (TypeError, ValueError):
            continue
        if price < 1.01 or price > 80.0:
            continue
        vals = (
            _sql_str(r.get('sport', '')),
            _sql_str(r['event_id']),
            _sql_str(r.get('home_team', '')),
            _sql_str(r.get('away_team', '')),
            _sql_str(_normalize_commence(r.get('commence_time', ''))),
            _sql_str(r.get('bookmaker', '')),
            _sql_str(r['bookmaker_key']),
            _sql_str(r.get('market', 'h2h')),
            _sql_str(r.get('outcome_name', '')),
            _sql_num(price),
            _sql_num(r.get('outcome_point')),
            _sql_str(r.get('snapshot_kind', 'close')),
            # Load-bearing: _normalize_commence("") returns the 1970 epoch literal,
            # so we MUST pass None when snapshot_at is missing — do not "simplify"
            # this branch into _normalize_commence(r.get('snapshot_at', '')).
            _sql_str(_normalize_commence(r.get('snapshot_at', '')) if r.get('snapshot_at') else None),
            _sql_str(r.get('source', 'oddsharvester')),
        )
        batch.append('(' + ', '.join(vals) + ')')
        if len(batch) >= batch_size:
            out_fh.write(header + ',\n  '.join(batch) + ';\n')
            written += len(batch)
            batch = []
    if batch:
        out_fh.write(header + ',\n  '.join(batch) + ';\n')
        written += len(batch)
    return written


def emit_grading_sql(run_id: str, results: Dict[str, Dict[str, Any]], out_fh) -> int:
    '''After the PHP CLI runs, mark each synthetic bet win/loss/push by joining
    against historical results. Returns number of update statements emitted.
    Limited to h2h moneyline grading in this first cut; spreads/totals require
    parsing bet_type strings, deferred to follow-up.'''
    out_fh.write('\n-- Grading: h2h moneyline only in v1; non-h2h rows stay pending.\n')
    n = 0
    for eid, res in results.items():
        winner = res.get('winner')
        if winner not in ('home', 'away', 'push'):
            continue
        home = res.get('home_team', '')
        away = res.get('away_team', '')
        if not home or not away:
            continue
        winner_team = home if winner == 'home' else (away if winner == 'away' else '')
        eid_sql = _sql_str(str(eid))
        run_sql = _sql_str(run_id)
        if winner == 'push':
            out_fh.write(
                f"UPDATE `lm_sports_synthetic_bets` SET actual_outcome='push', actual_pnl=0, "
                f"graded_at=NOW() WHERE backtest_run_id={run_sql} AND event_id={eid_sql} "
                f"AND market='h2h' AND actual_outcome='pending';\n"
            )
            n += 1
            continue
        winner_sql = _sql_str(winner_team)
        loser_sql = _sql_str(away if winner == 'home' else home)
        # Win: pnl = kelly_bet * (best_odds - 1)
        out_fh.write(
            f"UPDATE `lm_sports_synthetic_bets` SET actual_outcome='win', "
            f"actual_pnl=ROUND(kelly_bet * (best_odds - 1), 2), graded_at=NOW() "
            f"WHERE backtest_run_id={run_sql} AND event_id={eid_sql} AND market='h2h' "
            f"AND outcome_name={winner_sql} AND actual_outcome='pending';\n"
        )
        # Loss: pnl = -kelly_bet
        out_fh.write(
            f"UPDATE `lm_sports_synthetic_bets` SET actual_outcome='loss', "
            f"actual_pnl=-kelly_bet, graded_at=NOW() WHERE backtest_run_id={run_sql} "
            f"AND event_id={eid_sql} AND market='h2h' AND outcome_name={loser_sql} "
            f"AND actual_outcome='pending';\n"
        )
        n += 2
    return n


# ---- Manifest + shell emission -----------------------------------------------

def build_event_manifest(odds_rows: List[Dict[str, Any]],
                         results_by_eid: Dict[str, Dict[str, Any]],
                         require_results: bool,
                         as_of_offset_hours: float = 1.0) -> List[Dict[str, Any]]:
    '''Pick one (event_id, as_of) pair per event: as-of = commence_time minus
    as_of_offset_hours so the analyzer sees the event as upcoming.'''
    by_eid: Dict[str, Dict[str, Any]] = {}
    for r in odds_rows:
        eid = r['event_id']
        if eid in by_eid:
            continue
        if require_results and eid not in results_by_eid:
            continue
        commence_str = _normalize_commence(r.get('commence_time', ''))
        try:
            commence_dt = datetime.datetime.strptime(commence_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            continue
        as_of = commence_dt - datetime.timedelta(hours=as_of_offset_hours)
        by_eid[eid] = {
            'event_id': eid,
            'sport': r.get('sport', ''),
            'commence_time': commence_str,
            'as_of': as_of.strftime('%Y-%m-%d %H:%M:%S'),
        }
    return list(by_eid.values())


def emit_shell_script(run_id: str, manifest: List[Dict[str, Any]],
                      php_bin: str, cli_path: str, sql_for_grading: str,
                      bankroll: float, min_ev: float, out_fh) -> None:
    out_fh.write('#!/usr/bin/env bash\n')
    out_fh.write(f'# backtest run: {run_id}\n')
    out_fh.write(f'# events: {len(manifest)}\n')
    out_fh.write('# Run AFTER applying the corresponding .sql file to the DB.\n')
    out_fh.write('#\n')
    out_fh.write('# IDEMPOTENCY: lm_sports_synthetic_bets has UNIQUE KEY\n')
    out_fh.write('#   (backtest_run_id, event_id, market, outcome_name, best_book_key)\n')
    out_fh.write('# so re-running this script with the same RUN_ID will not duplicate rows;\n')
    out_fh.write('# the analyzer will INSERT and the DB will skip dup-key collisions silently.\n')
    out_fh.write('# To start fresh, first:\n')
    out_fh.write(f'#   DELETE FROM lm_sports_synthetic_bets WHERE backtest_run_id=\'{run_id}\';\n')
    out_fh.write('set -u  # do not -e: a single CLI failure should not abort the run\n')
    out_fh.write('PHP_BIN="${PHP_BIN:-' + php_bin + '}"\n')
    out_fh.write('CLI="${CLI:-' + cli_path + '}"\n')
    out_fh.write(f'RUN_ID="{run_id}"\n')
    out_fh.write(f'BANKROLL={bankroll}\n')
    out_fh.write(f'MIN_EV={min_ev}\n')
    out_fh.write(f'LOG="${{LOG:-{run_id}.cli.log}}"\n')
    out_fh.write('OK=0\nERR=0\n')
    out_fh.write(': > "$LOG"  # truncate prior log\n')
    out_fh.write('echo "[backtest] starting run $RUN_ID with ' + str(len(manifest)) + ' events; per-CLI output -> $LOG"\n')
    for i, m in enumerate(manifest, 1):
        sport = m.get('sport', '')
        sport_arg = f' --sport "{sport}"' if sport else ''
        out_fh.write(
            f'echo "--- event {i}/{len(manifest)} as_of={m["as_of"]} sport={sport} ---" >>"$LOG"; '
            f'"$PHP_BIN" "$CLI" --as-of "{m["as_of"]}" --run-id "$RUN_ID"'
            f'{sport_arg} --bankroll $BANKROLL --min-ev $MIN_EV >>"$LOG" 2>&1'
            f' && OK=$((OK+1)) || ERR=$((ERR+1))\n'
        )
        if i % 100 == 0:
            out_fh.write(f'echo "[backtest] processed {i}/{len(manifest)} (ok=$OK err=$ERR)"\n')
    out_fh.write('echo "[backtest] CLI loop done: ok=$OK err=$ERR (full output in $LOG)"\n')
    out_fh.write('echo "[backtest] now run grading SQL: '
                 + os.path.basename(sql_for_grading) + '"\n')


# ---- Main --------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description='Generate backtest artifacts for the value-bet algorithm.')
    parser.add_argument('--odds-json', action='append', default=[],
                        help='Path to OddsHarvester JSON file or directory. Repeatable.')
    parser.add_argument('--results-json', action='append', default=[],
                        help='Path to sportsdataverse JSON file or directory. Repeatable.')
    parser.add_argument('--sports', default='',
                        help='Comma-separated sport filter (nba,nhl,nfl,mlb). Empty = all.')
    parser.add_argument('--start-date', default='', help='YYYY-MM-DD lower bound on commence_time.')
    parser.add_argument('--end-date', default='', help='YYYY-MM-DD upper bound on commence_time.')
    parser.add_argument('--out-dir', default='live-monitor/backfill/backtests',
                        help='Where to write <run_id>.sql, .sh, .manifest.json.')
    parser.add_argument('--run-id', default='', help='Override the auto-generated run id.')
    parser.add_argument('--bankroll', type=float, default=1000.0)
    parser.add_argument('--min-ev', type=float, default=1.5)
    parser.add_argument('--php-bin', default='php')
    parser.add_argument('--cli-path', default='live-monitor/api/sports_value_analyze_cli.php')
    parser.add_argument('--require-results',
                        action=argparse.BooleanOptionalAction,
                        default=True,
                        help='Skip events without a matching result row. Pass --no-require-results to keep them.')
    parser.add_argument('--as-of-offset-hours', type=float, default=1.0,
                        help='Hours before commence_time used as the analyzer "as_of" instant. '
                             'Defaults to 1.0; raise for sports where lines lock earlier (NFL: 3-6h).')
    args = parser.parse_args()

    if not args.odds_json:
        print('ERROR: at least one --odds-json is required', file=sys.stderr)
        return 2

    odds_payloads = _load_jsons(args.odds_json)
    results_payloads = _load_jsons(args.results_json) if args.results_json else []
    print(f'[load] odds files: {len(odds_payloads)}, result files: {len(results_payloads)}')

    odds_rows = collect_odds_rows(odds_payloads)
    print(f'[load] odds rows (raw): {len(odds_rows)}')

    sport_filter = set()
    if args.sports.strip():
        sport_filter = {_norm_sport(s) for s in args.sports.split(',') if s.strip()}
    start = _parse_iso_date(args.start_date)
    end = _parse_iso_date(args.end_date)

    if sport_filter or start or end:
        before = len(odds_rows)
        odds_rows = [
            r for r in odds_rows
            if (not sport_filter or _norm_sport(r.get('sport', '')) in sport_filter)
            and _row_within_window(r.get('commence_time', ''), start, end)
        ]
        print(f'[filter] odds rows after filters: {len(odds_rows)} (was {before})')

    if not odds_rows:
        print('ERROR: no odds rows after filtering', file=sys.stderr)
        return 2

    results = collect_result_rows(results_payloads)
    print(f'[load] result rows: {len(results)}')

    manifest = build_event_manifest(odds_rows, results, args.require_results,
                                    as_of_offset_hours=args.as_of_offset_hours)
    print(f'[plan] events to backtest: {len(manifest)} (as_of offset={args.as_of_offset_hours}h)')

    if not manifest:
        print('ERROR: no events with both odds and results in window', file=sys.stderr)
        return 2

    run_id = args.run_id.strip()
    if not run_id:
        h = hashlib.sha1()
        h.update(str(len(odds_rows)).encode())
        h.update(str(len(manifest)).encode())
        h.update(datetime.datetime.utcnow().isoformat().encode())
        run_id = 'bt_' + datetime.datetime.utcnow().strftime('%Y%m%d') + '_' + h.hexdigest()[:6]

    os.makedirs(args.out_dir, exist_ok=True)
    sql_path = os.path.join(args.out_dir, run_id + '.sql')
    sh_path  = os.path.join(args.out_dir, run_id + '.sh')
    grading_path = os.path.join(args.out_dir, run_id + '.grading.sql')
    manifest_path = os.path.join(args.out_dir, run_id + '.manifest.json')

    with open(sql_path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(f'-- Backtest run {run_id}\n')
        fh.write(f'-- Generated: {datetime.datetime.utcnow().isoformat()}Z\n')
        fh.write(f'-- Odds rows: {len(odds_rows)}, events: {len(manifest)}\n\n')
        # Normalize sports list to the canonical odds-table keys (basketball_nba etc.)
        # so a DBA joining lm_sports_backtest_runs.sports against
        # lm_sports_synthetic_bets.sport sees consistent values.
        if args.sports.strip():
            sports_canonical = ','.join(_norm_sport(s) for s in args.sports.split(',') if s.strip())
        else:
            sports_canonical = 'all'
        fh.write(
            'INSERT IGNORE INTO `lm_sports_backtest_runs` (run_id, sports, start_date, end_date, notes) '
            f"VALUES ({_sql_str(run_id)}, {_sql_str(sports_canonical)}, "
            f"{_sql_str(args.start_date or '1970-01-01')}, "
            f"{_sql_str(args.end_date or '2099-12-31')}, "
            f"'auto');\n\n"
        )
        n_inserted = emit_odds_inserts(odds_rows, fh)
    print(f'[write] {sql_path} ({n_inserted} odds rows)')

    with open(grading_path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(f'-- Grading SQL for run {run_id}\n')
        fh.write('-- Run AFTER the .sh script completes.\n\n')
        n_grade = emit_grading_sql(run_id, results, fh)
        fh.write(
            "\nUPDATE `lm_sports_backtest_runs` SET finished_at=NOW(), "
            "synthetic_bets_emitted=(SELECT COUNT(*) FROM lm_sports_synthetic_bets WHERE backtest_run_id="
            + _sql_str(run_id) + "), synthetic_bets_graded=(SELECT COUNT(*) FROM lm_sports_synthetic_bets WHERE backtest_run_id="
            + _sql_str(run_id) + " AND actual_outcome != 'pending'), "
            "events_processed=" + str(len(manifest)) + " WHERE run_id=" + _sql_str(run_id) + ";\n"
        )
    print(f'[write] {grading_path} ({n_grade} grading statements)')

    with open(sh_path, 'w', encoding='utf-8', newline='\n') as fh:
        emit_shell_script(run_id, manifest, args.php_bin, args.cli_path,
                          grading_path, args.bankroll, args.min_ev, fh)
    try:
        os.chmod(sh_path, 0o755)
    except OSError:
        pass
    print(f'[write] {sh_path}')

    with open(manifest_path, 'w', encoding='utf-8') as fh:
        json.dump({
            'run_id': run_id,
            'generated_at': datetime.datetime.utcnow().isoformat() + 'Z',
            'events': manifest,
            'sports': args.sports,
            'start_date': args.start_date,
            'end_date': args.end_date,
            'bankroll': args.bankroll,
            'min_ev': args.min_ev,
        }, fh, indent=2)
    print(f'[write] {manifest_path}')

    print('\n[done] To execute on the DB host:')
    print(f'  mysql -u <user> -p <db> < {sql_path}')
    print(f'  bash {sh_path}')
    print(f'  mysql -u <user> -p <db> < {grading_path}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
