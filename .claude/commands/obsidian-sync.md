Sync key project state into the Obsidian vault at `obsidian-notes/` so it stays current.

## What to sync

1. **Performance tiers** — pull latest from `money_ready_verdict.json` and update `reference/performance-tiers.md`
2. **Active incidents** — query `reports/` for unresolved items; update or create files in `incidents/`
3. **Strategy list** — read `pf_registry.json` top entries per class; update strategy notes
4. **Session close** — create a new `sessions/YYYY-MM-DD-<topic>.md` from today's work

## Steps

```bash
# 1. Check latest verdict
cat audit_dashboard/data/money_ready_verdict.json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); [print(k,v) for k,v in d.items()]"

# 2. List open incident reports
ls reports/ | grep -i incident | sort -r | head -10

# 3. Check pf_registry for T2+ candidates
python3 tools/strategy_tier_tracker.py 2>/dev/null | head -40
```

Then write/update the relevant Obsidian notes. Confirm each file updated.

## When to use

- End of a work session (`/obsidian-sync`)
- Before a `/money-maker-readyv2` run
- When a strategy tier changes

Alias: `obsidian-sync`, `vault-sync`, `update-vault`
