Search the Obsidian vault at `obsidian-notes/` for notes matching the user's query.

## How to search

Run a ripgrep across the vault directory, returning file names + matching lines:

```bash
grep -rn --include="*.md" -i "$QUERY" obsidian-notes/
```

If $QUERY is empty, list all notes:
```bash
find obsidian-notes -name "*.md" | sort
```

## Output format

For each match show:
- **File path** (as a clickable markdown link)
- **Matching line(s)** with context (1 line before/after)
- **Tags** from the file's frontmatter (if any)

If more than 20 results, group by folder and summarize.

## Special query modifiers

- `tag:X` — filter by frontmatter tag (e.g. `tag:strategy`)
- `tier:T1` — filter strategy notes by tier field
- `status:open` — filter incidents/sessions by status field
- `class:CRYPTO` — filter by asset class tag

## Examples

```
/obsidian-search mega_mutation
/obsidian-search tag:incident status:open
/obsidian-search resolver
/obsidian-search tier:T1
```
