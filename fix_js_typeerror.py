#!/usr/bin/env python3
"""Fix JS TypeError: Cannot read properties of undefined (reading 'picks') in audit dashboard."""
import sys

FILE = "audit_dashboard/template.html"

with open(FILE, "r", encoding="utf-8") as f:
    content = f.read()

fixes_applied = 0

# Fix 1: kimi null guard in renderKimiComparison()
old1 = "function renderKimiComparison() {\n  const kimi = window._kimiPicks;"
new1 = "function renderKimiComparison() {\n  const kimi = window._kimiPicks;\n  if (!kimi) return; // non-blocking fetch may not have completed yet"
if old1 in content:
    content = content.replace(old1, new1, 1)
    fixes_applied += 1
    print("Fix 1 applied: kimi null guard")
else:
    print("Fix 1 NOT found - pattern mismatch")

# Fix 2: D.picks safety guard in init()
old2 = "async function init() {\n  let freshLoaded = await loadExternalDashboardDataIfFresher();"
new2 = (
    "async function init() {\n"
    "  let freshLoaded = await loadExternalDashboardDataIfFresher();\n"
    "  // Safety: ensure D.picks exists even if data payload was malformed/missing\n"
    "  if (!D.picks) D.picks = { active: [], recent_closed: [], active_raw: [] };"
)
if old2 in content:
    content = content.replace(old2, new2, 1)
    fixes_applied += 1
    print("Fix 2 applied: D.picks safety guard")
else:
    print("Fix 2 NOT found - pattern mismatch")

# Fix 3: snap/latest/laterSnap.picks null guards
count = 0
for pat, rep in [
    ("latest.picks.forEach", "(latest.picks||[]).forEach"),
    ("snap.picks.forEach", "(snap.picks||[]).forEach"),
    ("laterSnap.picks.find", "(laterSnap.picks||[]).find"),
    ("snap.picks.length", "(snap.picks||[]).length"),
    ("snap.picks.reduce", "(snap.picks||[]).reduce"),
]:
    n = content.count(pat)
    if n > 0:
        content = content.replace(pat, rep)
        count += n
if count > 0:
    fixes_applied += 1
    print(f"Fix 3 applied: {count} snap/latest/laterSnap.picks null guards")
else:
    print("Fix 3 NOT found - no unguarded .picks accesses")

with open(FILE, "w", encoding="utf-8") as f:
    f.write(content)

print(f"\nTotal fix groups applied: {fixes_applied}/3")
if fixes_applied == 0:
    print("ERROR: No fixes applied - patterns may have changed")
    sys.exit(1)
