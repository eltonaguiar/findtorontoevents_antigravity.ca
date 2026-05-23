# GitHub CLI (`gh`) and pull requests

## Where `gh` is

This repo’s Cursor/VS Code terminals prepend **`%USERPROFILE%\.local\bin`** via `.vscode/settings.json` so `gh` resolves if it was installed to the user-local path.

If `gh` is still not found in an external PowerShell or CMD:

```powershell
powershell -ExecutionPolicy Bypass -File tools/ensure_github_cli_on_path.ps1
```

Or install system-wide: `winget install --id GitHub.cli`

## Auth (required once)

```powershell
gh auth login
```

**Never** paste a PAT into email, tickets, or the repo. If a token was exposed, **revoke** it in GitHub immediately and create a new one.

Non-interactive / CI: set **`GH_TOKEN`** (classic PAT with `repo` scope) or **`GITHUB_TOKEN`** in the environment, then:

```powershell
gh auth status
```

## Create the MIMO feature PR (after auth)

Branch: **`feat/mimo-strategy-enhancements-20260412`** → **`main`**

```powershell
cd c:\findtorontoevents_antigravity.ca
git checkout feat/mimo-strategy-enhancements-20260412
git pull --rebase origin main
gh pr create --base main --head feat/mimo-strategy-enhancements-20260412 --title "MIMO: rehab strategies + unified copy-trade + coverage" --body-file PR_EXPAND_MIMO_2026-04-12.md
```

If `PR_EXPAND_MIMO_2026-04-12.md` is missing, use `--body "..."` or paste from `MIMO_2026-04-12T213000Z.MD`.

## Open compare in browser (no `gh` auth)

[Create PR: main ← feat/mimo-strategy-enhancements-20260412](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/compare/main...feat/mimo-strategy-enhancements-20260412?expand=1)

Use this if you cannot run `gh auth login` in this environment.

## Other pushed branch (earlier MIMO commit)

[Create PR: main ← feature/mimo-2026-04-12-strategies](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/compare/main...feature/mimo-2026-04-12-strategies?expand=1)

Merge **one** PR that contains the commits you want; avoid duplicate overlapping PRs.
