Create or update a note in the Obsidian vault at `obsidian-notes/`.

## Usage

```
/obsidian-note <folder>/<title> [content or --update]
```

## Folders

| Folder | Use for |
|--------|---------|
| `sessions/` | Work session summaries |
| `strategies/` | Strategy analysis notes |
| `incidents/` | Bugs, outages, data issues |
| `asset-classes/` | Per-class status notes |
| `reference/` | Stable reference docs |

## Behavior

1. **New note**: create the file using the appropriate template from `obsidian-notes/templates/`
2. **Update existing**: append a dated `## Update YYYY-MM-DD` section, never overwrite existing content
3. **Always** include YAML frontmatter with `tags`, `created`, `status`
4. **Always** add wikilinks `[[note-name]]` for related notes
5. After writing, confirm the file path and a one-line summary

## Examples

```
/obsidian-note strategies/rsi2_pullback
/obsidian-note incidents/open-picks-resolver-fail
/obsidian-note sessions/2026-06-07-equity-deep-dive
```
