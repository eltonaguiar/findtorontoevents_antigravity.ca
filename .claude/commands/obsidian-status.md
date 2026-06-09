Print a quick status summary of the Obsidian vault at `obsidian-notes/`.

## Output

Show:
1. **Note counts** by folder
2. **Open incidents** (status: open in frontmatter)
3. **Strategy tiers** — list all strategy notes with their tier field
4. **Recent sessions** — last 5 by filename date

## How

```bash
# Count notes by folder
find obsidian-notes -name "*.md" ! -path "*/.obsidian/*" | awk -F/ '{print $2}' | sort | uniq -c | sort -rn

# Open incidents
grep -rl "status: open" obsidian-notes/incidents/ 2>/dev/null

# Strategy tiers
grep -r "^tier:" obsidian-notes/strategies/ 2>/dev/null

# Recent sessions
ls obsidian-notes/sessions/ | sort -r | head -5
```

Format output as a compact markdown table. Keep response under 30 lines.
