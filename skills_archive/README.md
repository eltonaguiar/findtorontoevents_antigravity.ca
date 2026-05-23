# skills_archive/

Backup copies of Claude Code skills that live OUTSIDE this repo, so they are
versioned in git and recoverable if a machine is lost.

## global_user_skills/

Mirror of `~/.claude/skills/` (the user-profile / global skill set) as of
2026-05-17. These are personal cross-tool skills not tied to any one repo:

| Skill | Purpose |
|---|---|
| `consult-codex` | Second opinion via OpenAI Codex headless CLI |
| `consult-cursor-agent` | Second opinion via Cursor Agent (`agent`) CLI |
| `consult-gemini` | Second opinion via Google Gemini CLI |
| `consult-kilo` | Second opinion via kilo (opencode fork) CLI |
| `consult-opencode` | Second opinion via opencode CLI |
| `graphify` | Any input → knowledge graph |
| `handlealltodos` | Autonomously clear the session backlog |

These are an **archive copy** — they are NOT loaded as skills from here
(global skills load from `~/.claude/skills/`, project skills from
`.claude/skills/`). To restore: copy a directory back to `~/.claude/skills/`.

The project-scoped skills already live (and are versioned) in
`.claude/skills/` — they are not duplicated here.

Refresh procedure: re-copy `~/.claude/skills/*` into `global_user_skills/`
and commit. Scan for secrets before committing (`grep -rE 'sk-|ghp_|xai-'`).
