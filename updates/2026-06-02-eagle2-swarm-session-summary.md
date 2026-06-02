# EAGLE session report — updates deploy (2026-06-02)

## What this PR ships

- **`updates/eagle2-swarm-session-summary-2026-06-02.html`** — findings, achievements, repo tasks, best-picks rationale (detailed), short/long-term plan; ELI5 under every section.
- **`updates/index.html`** — top card (before incidents block) linking to the HTML report.
- **PF clarification:** Dedicated section explaining the cited PF book was live and populated; the confusing part was old empty-state messaging (81 portfolios, 66 with opens, `deepseek_v4__aggressive` had 11 opens).

## Post-merge deploy (required for live site)

50webs has no shell — git merge does not update findtorontoevents.ca/updates until FTP:

```bash
python3 tools/deploy_audit_files.py --only updates
curl -sI -A "Mozilla/5.0" 'https://findtorontoevents.ca/updates/eagle2-swarm-session-summary-2026-06-02.html'
```

## Verify locally

```bash
python3 tools/serve_local.py
# http://localhost:5173/updates/eagle2-swarm-session-summary-2026-06-02.html
```

## Key message

0/9 money-ready on production `/audit`; paper edge on ai-tournament; first promotion candidate ETF dual momentum (shadow).

## Live URLs (after deploy)

- https://findtorontoevents.ca/updates/eagle2-swarm-session-summary-2026-06-02.html
- https://findtorontoevents.ca/updates/index.html
