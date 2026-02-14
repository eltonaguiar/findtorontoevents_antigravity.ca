import json, sys

with open('temp_db_audit.json', 'r') as f:
    d = json.load(f)

for db in d.get('databases', []):
    name = db.get('database', '?')
    if db.get('error'):
        print("\n=== %s === ERROR: %s" % (name, db['error']))
        continue
    print("\n" + "=" * 65)
    print("  DATABASE: %s" % name)
    print("  Tables: %d total | %d with data | %d empty" % (
        db['total_tables'], db['populated_tables'], db['empty_tables']))
    print("  Total rows: %s" % "{:,}".format(db['total_rows']))
    print("=" * 65)

    # Show populated tables
    print("\n  --- POPULATED TABLES (%d) ---" % db['populated_tables'])
    for t in db['tables']:
        if t['rows'] > 0:
            ld = t.get('last_date', '')
            dc = t.get('date_column', '')
            date_str = "  Last: %s (%s)" % (ld, dc) if ld else ''
            print("    %-40s %8s rows%s" % (t['name'], "{:,}".format(t['rows']), date_str))

    # Show empty tables
    empty = [t for t in db['tables'] if t['rows'] == 0]
    if empty:
        print("\n  --- EMPTY TABLES (%d) ---" % len(empty))
        for t in empty:
            print("    %s" % t['name'])
