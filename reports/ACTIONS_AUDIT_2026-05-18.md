# GitHub Actions Audit — 2026-05-18

`/swarm-actions-audit` — 3-specialist swarm (Mercury DevOps, Grok cost, Claude security).
Repo: 339 active workflows, storm-commit model (~30 workflows push to `main`).

## Overview

| metric | value |
|--------|-------|
| Active workflows | 339 |
| Failures (last 50 runs) | CI Tests 35, Gate Config Emit 13, Secret Scan 2 |
| Est. Actions run rate | ~131,000 runs/month |

CI Tests' 35-failure count is one burst (03:29–03:37 UTC) — a stale test fixture
colliding with the expanded `crypto_quarantine.json` (peer-fixed `ac60b7d9e6c`,
green since 03:45). Not a structural issue.

## P0 — fixed this session

### Gate Config Emit push race → **PR #1225**

5 of last 7 runs failed: bare `git push` rejected `! [rejected] main -> main
(fetch first)`. Fix: `concurrency` group + `fetch-depth 20` + 5-attempt
`pull --rebase --autostash` retry loop. Single-file, lowest-risk item.

## P1 — structural (Mercury) — flagged, not done

**11 other workflows share the race-vulnerable `git push` pattern.** Apply the
same 5-attempt rebase loop:

- Bare `git push`, no rebase: `actions-failure-guardian.yml:42`,
  `auto-retire-daily.yml:45`, `swarm-janitor.yml:41`,
  `growth-stock-screener-daily.yml:83-88` *(highest priority — daily, no retry)*.
- Rebase but no retry loop: `fred-macro-refresh.yml`,
  `monthly-calibrator-refit.yml`, `sidecar-status-update.yml`,
  `swarm-pick-review.yml`, `ml-gatekeeper-train-ab.yml`, `swarm-sync-v2.yml`,
  `stocksunify2-pull.yml`.

Reference correct implementations: `ab_analysis.yml`, `etf-bond-scanner.yml`,
`dynamic-alpha-engine.yml`, `research-orchestrator.yml`.

**Cron storm:** `meme-scanner-v2.yml:171` has a redundant `*/10` cron (also has
`0 */3`) — 144 runs/day, delete it. ~27 workflows fire at `:00` — stagger to
distinct minute offsets.

## P1 — cost (Grok)

~131k runs/month. Ranked savings (est. minutes/month):

1. **Push-trigger fan-out** (45k–65k) — 4–5 lightweight push gates
   (`conflict-marker-check`, `ci`, `no-stale-db-passwords`, `secret-scan`) fire
   per push with no `cancel-in-progress`. Add
   `concurrency: {group: ${{github.workflow}}-${{github.ref}}, cancel-in-progress: true}`;
   consider collapsing the 4 into one `pr-gates.yml`.
2. **`Unified Audit Dashboard` churn** (9k–15k) — 9/15 recent runs cancelled
   mid-flight (0.7–16.8 min billed, zero output). Drop the `push:` trigger or
   ensure `cancel-in-progress: false`.
3. **Uncached `pip install`** (7k–12k) — ~180 of 237 pip-installing workflows
   lack `cache: 'pip'`. `audit-dashboard.yml` runs `pip install pymysql` 7× in
   one run.
4. **Sub-15-min crons** (3k–5k) — downgrade `*/10` + non-market-hours `*/15`.
5. **Cron mega-cluster stagger** (2k–4k).

Fixing #1 alone likely cuts total Actions minutes 40–60%.

## P0/P1 — security (Claude)

- **P0-1 — 17 FTP deploys run `ssl:verify-certificate no`** while forcing SSL —
  credentials sent over encrypted-but-unauthenticated channel, MITM-harvestable.
  Files: `deploy-fc-api-env-godaddy.yml`, `db-sync-bidirectional.yml`,
  `db-sync-to-mirror.yml`, `db-backup-email.yml`, `deploy-battleground-ftp.yml`,
  others. **Needs host-cert verification before fixing — risk of breaking prod
  deploys; do not blind-edit.**
- **P0-2 — `deploy-fc-api-env-godaddy.yml`** writes `MYSQL_PASSWORD` +
  `GOOGLE_CLIENT_SECRET` to `/tmp/godaddy_fc_env`, FTP-uploads it, never shreds
  the temp file. Add `rm -f` cleanup with `if: always()`.
- **P0-3 — no approval gate** on any credentialed FTP/SFTP deploy. Add
  `environment: production` + required reviewers.
- **P1 — 0/343 actions SHA-pinned**; no CodeQL; no `dependabot.yml`; ~95
  workflows have no `permissions:` block (inherit broad write).
- **P1 — `no-stale-db-passwords.yml`** only matches 2 literal patterns; misses
  `analytics` DB, `.php`/`.env`/`.js` files, generic password forms.

Positives: no hardcoded tokens in workflows; alpha-engine push paths mask the
token via `sed`; `gitleaks` (M-043) runs on every PR + daily.

## Consensus (2+ specialists agreed)

- Storm-commit fan-out is the dominant problem — Mercury (race failures) +
  Grok (#1 cost leak). The fix axis is the same: `concurrency` groups.
- `pip` caching gap — Mercury + Grok.

## Action list

1. ✅ **PR #1225** — Gate Config Emit race fix.
2. Apply rebase-retry loop to the 11 race-vulnerable workflows.
3. Add `cancel-in-progress` concurrency to the 4 push gates (biggest cost win).
4. Security P0-1/P0-2/P0-3 — owner-coordinated; verify host certs first.
5. Add `.github/dependabot.yml` + `codeql.yml`; SHA-pin third-party actions.
