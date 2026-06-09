---
name: obsidian-memory
description: Bridge between Claude's file-based memory system and the Obsidian vault. Reads, writes, and searches project knowledge stored in obsidian-notes/ as the long-form counterpart to the terse entries in ~/.claude/projects/.../memory/. Use when the user asks to "save to Obsidian", "look up in vault", "update the vault", or when a decision/finding deserves richer context than a memory entry allows. Aliases: obsidian-memory, vault-memory, save-to-vault.
allowed-tools: Read Write Bash Grep
---

# obsidian-memory — Vault-Backed Memory Bridge

The project has two memory layers:

| Layer | Location | Best for |
|-------|----------|----------|
| **Terse memory** | `~/.claude/projects/.../memory/*.md` | User prefs, feedback, quick facts |
| **Vault notes** | `obsidian-notes/` | Deep analysis, strategy stats, incident timelines |

This skill bridges them. When something is too rich for a one-liner memory entry, write it to the vault instead (or both).

## Vault structure

```
obsidian-notes/
├── Home.md                 ← index / nav
├── asset-classes/          ← CRYPTO.md, EQUITY.md, FOREX.md, …
├── strategies/             ← one note per strategy
├── incidents/              ← bugs, outages, data issues
├── sessions/               ← per-session summaries
├── reference/              ← stable facts (tiers, banned sources, checklists)
└── templates/              ← strategy.md, session.md, incident.md
```

## How to write a vault note

1. Pick the right folder (see table above)
2. Copy the matching template from `obsidian-notes/templates/`
3. Fill in YAML frontmatter: `tags`, `created`, `status`
4. Add `[[wikilinks]]` to related notes
5. Write, then confirm path to user

## How to read / search

```bash
# Full-text search
grep -rn --include="*.md" -i "QUERY" obsidian-notes/

# By tag
grep -rl "tags:.*strategy" obsidian-notes/strategies/

# By tier
grep -r "^tier:" obsidian-notes/strategies/

# By status
grep -rl "status: open" obsidian-notes/incidents/
```

## How to update without overwriting

**Never replace existing content.** Append a dated update block:

```markdown
## Update 2026-06-07

- New finding: …
- Stats changed: PF 1.85 → 2.10
```

## Triggers

Use this skill when:
- A strategy tier changes (update `strategies/` note)
- An incident is opened or resolved (create/update `incidents/` note)
- A session ends (create `sessions/YYYY-MM-DD-topic.md`)
- A class-level verdict changes (update `asset-classes/` note)
- User asks "remember this in the vault" or "save to Obsidian"

## Example: saving a new strategy finding

```
User: mega_mutation last10_WR jumped back to 60% — save this to Obsidian

→ Read obsidian-notes/strategies/mega_mutation.md
→ Append "## Update 2026-06-07\n- last10_WR recovered to 60%"
→ Confirm: "Updated obsidian-notes/strategies/mega_mutation.md"
```
