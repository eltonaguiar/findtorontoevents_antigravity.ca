---
name: large-repo-read
description: Safe read patterns for large files in this repo — dashboard JSON (18MB), coinglass DB (27MB), strategy JSONs, log files. Prevents OOM crashes and timeout kills from naive cat/read. Aliases - bigfile, safe-read, large-file-read, repo-read
---

# large-repo-read — Safe file reads for large repos

This repo has several files that will crash, hang, or OOM-kill an agent if read naively. This skill gives the safe access pattern for each.

---

## The dangerous files

| File | Size | Safe access |
|------|------|------------|
| `audit_dashboard/data/dashboard_data.json` | ~18MB | Python with targeted key path only |
| `coinglass_strategies/data/coinglass.db` | ~27MB | Never read — query with sqlite3 |
| `audit_dashboard/index.html` | ~4MB | Never read — edit `template.html` |
| `logs/cross_pc_protocol/events.jsonl` | Growing | `tail -20` only |
| `alpha_engine/data/pick_monitor_report.json` | ~1MB | Targeted key access |
| `regime_terminal/data/regime_state.json` | ~2MB | Targeted key access |

---

## dashboard_data.json — targeted key access

**Never** `cat`, `Read`, or `json.load` the whole file into context. Always access one key at a time:

```python
import json
from pathlib import Path

p = Path('audit_dashboard/data/dashboard_data.json')
# Stream parse — only loads what you access
d = json.loads(p.read_text(encoding='utf-8'))

# Freshness check
print('generated_at:', d.get('generated_at'))

# Per-class health (the only verdict-grade table)
for cls, stats in d.get('performance', {}).get('asset_class_health', {}).items():
    print(cls, stats.get('profit_factor'), stats.get('win_rate'), stats.get('total_picks'))

# Active picks only
picks = d.get('picks', [])
active = [p for p in picks if p.get('status') == 'active']
print('active picks:', len(active))

# Walk-forward table
wf = d.get('walkforward', {}).get('by_class', {})
for cls, row in wf.items():
    print(cls, row.get('oos_wr'), row.get('oos_sharpe'), row.get('consistency'))
```

**Never pass the full dict to an LLM or print it** — 18MB of JSON in context will truncate everything useful.

---

## coinglass.db — sqlite3 queries only

```bash
# List tables
python -c "
import sqlite3
con = sqlite3.connect('coinglass_strategies/data/coinglass.db')
print(con.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall())
"

# Sample from one table
python -c "
import sqlite3
con = sqlite3.connect('coinglass_strategies/data/coinglass.db')
rows = con.execute('SELECT * FROM signals ORDER BY ts DESC LIMIT 5').fetchall()
for r in rows: print(r)
"
```

Never `cat` or `Read` the `.db` file — it's binary.

---

## Large JSON strategy files — sample first

```bash
# Check structure without reading everything
python -c "
import json
from pathlib import Path
d = json.loads(Path('baby_strategies/results/some_result.json').read_text())
print('keys:', list(d.keys()))
print('n trades:', len(d.get('trades', [])))
print('metrics:', d.get('metrics'))
"

# For JSON arrays, count + sample
python -c "
import json
from pathlib import Path
items = json.loads(Path('signals_database.json').read_text())
print('count:', len(items))
print('sample[0]:', items[0] if items else 'empty')
"
```

---

## Log files — tail only

```bash
# Cross-PC event log
tail -20 logs/cross_pc_protocol/events.jsonl

# Parsed tail
python -c "
import json
from pathlib import Path
lines = Path('logs/cross_pc_protocol/events.jsonl').read_text().strip().splitlines()
for line in lines[-10:]:
    r = json.loads(line)
    e = r.get('envelope') or {}
    print(r.get('gateway_ts_utc'), r.get('direction'), e.get('from'), '->', e.get('to'), e.get('topic'))
"

# Trading/battle logs
tail -30 trading_bot.log
tail -30 battle_test.log
```

---

## Python files — read with line limits

When you need to inspect a large Python file (some strategy files are 500+ lines):

```bash
# Check line count first
git show --stat HEAD:alpha_engine/quality_gates.py | tail -1

# Read specific section (e.g., lines 100-150)
sed -n '100,150p' audit_trail/quality_gates.py

# Search for a symbol without reading the file
grep -n "BLOCKED_ASSET_STRATEGY_PAIRS" audit_trail/quality_gates.py
git grep -n "BLOCKED_ASSET_STRATEGY_PAIRS"
```

In Claude Code's Read tool, always specify `offset` and `limit` for files >500 lines. Never read a >1000-line file from offset 0 without limit.

---

## HTML files — template only

`audit_dashboard/index.html` is 4MB+ (auto-generated). Never read it.
Always work on `audit_dashboard/template.html` instead.

```bash
# Find a section in template.html
grep -n "tab-smart\|high_conviction\|asset-class" audit_dashboard/template.html | head -20

# Read a targeted range
sed -n '800,850p' audit_dashboard/template.html
```

---

## Repo-wide search — git grep, not grep -r

```bash
# Fast: uses git index, respects .gitignore, skips binary files
git grep -n "calculate_smart_score"
git grep -l "COMMODITY"              # list files only
git grep -n "def passes_" -- "*.py"  # scoped to Python

# Count matches
git grep -c "strat_fwd_wr"

# Context around match
git grep -n -C 2 "FUTURES floor"
```

Never `grep -r pattern .` — it will scan the 27MB binary DB and 18MB JSON on every invocation.

---

## When the Read tool times out

If the Read tool (or bash cat) hangs on a large file:
1. Switch to targeted Python key access (see dashboard_data.json section)
2. Use `git grep` instead of reading the file
3. Use `sed -n 'start,endp'` to read only the needed lines
4. Use `head -50` or `tail -50` for log files
5. For JSON: `python -c "import json; d=json.load(open(f)); print(list(d.keys()))"` to explore structure first

---

## Companion skills

- `/large-repo-git` — fast git operations (status, fetch, diff, push)
- `/money-maker-ready` — safe dashboard_data.json audit patterns
