# 2026-10-03 — Discord webhook deleted (exposed in public repo) → most notifications silently stopped

## Symptom

`findtorontoevents.ca/` pipelines stopped delivering **most** Discord notifications, while the
GitHub Actions workflows themselves stayed green (no failed runs).

## Root cause (two compounding problems)

### 1. The shared webhook was exposed and Discord deleted it

An automated scanner (`FriendlyScanner`) found a hardcoded Discord webhook in the **public**
GitHub repo `eltonaguiar/findtorontoevents_antigravity.ca-archive-2026-05-23`, at
`coinglass_strategies/discord_notify.py`, and posted an "Exposed Webhook!!!" notice on
**2026-09-19**. Discord then **permanently deleted** that webhook.

* Webhook ID: `1478588243459965008` (token redacted here)
* Verified live: `GET https://discord.com/api/webhooks/1478588243459965008/<token>` → **HTTP 404 `{"message":"Unknown Webhook","code":10015}`**

The deleted URL was still hardcoded as a **fallback default** in the current repo:

| File | Role |
|------|------|
| `coinglass_strategies/discord_notify.py` | default for `DISCORD_WEBHOOK_PAPERTRADE` (#paper-trade) |
| `shared/failover_notifications.py` | default for the central failover notifier's primary channel |
| `docs/plans/2026-03-03-coinglass-dna-bundle-plan.md` | documented secret value |
| `docs/plans/2026-03-04-paper-trading-portfolio-plan.md` | documented secret value |

Because every `POST` to the dead URL returned 404 and the code only logged a warning, **nothing
visible failed** — the notifications were simply dropped.

### 2. Most channel secrets are not configured (silent skips)

The workflows reference **19 distinct** `DISCORD_*` secret names but only **4** exist
(`DISCORD_WEBHOOK_URL`, `DISCORD_WEBHOOK_FRESHPICKS`, `DISCORD_WEBHOOK_SANDBOX`,
`DISCORD_HEALTH_WEBHOOK`). Missing names (with reference counts):

`DISCORD_ML_CHANNEL` (14), `DISCORD_MASTER_PICKS` (8), `DISCORD_BOT_TOKEN` (5),
`DISCORD_WEBHOOK_DNA_MASTER` (4), `DISCORD_FRESHPICKS` (4 — note: the real secret is
`DISCORD_WEBHOOK_FRESHPICKS`), `DISCORD_WEBHOOK_PROPICKS` (2),
`DISCORD_WEBHOOK_PAPERTRADE`/`DISCORD_WEBHOOK_PAPER_TRADE` (2+2), `DISCORD_WEBHOOK_CONVICTION` (2),
plus one-off aliases (`DISCORD_SANDBOX`, `DISCORD_FRESH_PICKS`, `DISCORD_HEALTH_ALERTS`,
`DISCORD_SIGNAL_ALERTS`, `DISCORD_QUALITY_ALERTS`, `DISCORD_REPORTS`, `DISCORD_ML_ALERTS`,
`DISCORD_NOTIFICATIONS`, `DISCORD_GENERAL`, `DISCORD_WEBHOOK`).

When the env var is empty the code prints `No DISCORD_* set, skipping…` and exits 0 → green
workflow, no Discord message.

## Fix applied

1. **Removed the hardcoded dead URL** and made both code paths env-only:
   * `coinglass_strategies/discord_notify.py` → `os.environ.get("DISCORD_WEBHOOK_PAPERTRADE", "")`
   * `shared/failover_notifications.py` → `os.getenv("DISCORD_WEBHOOK_URL") or os.getenv("DISCORD_WEBHOOK_PAPERTRADE", "")`
2. **Scrubbed the dead URL from the two plan docs** (replaced with a placeholder).
3. **Wired every channel secret to its real webhook** (stored as GitHub Secrets — never committed;
   this repo is public). All 10 hooks were verified live via a non-destructive `GET`:

| Secret(s) | Channel | Webhook name |
|---|---|---|
| `DISCORD_WEBHOOK_PAPERTRADE`, `DISCORD_WEBHOOK_PAPER_TRADE` | #paper-trade | Paper Trade hoook |
| `DISCORD_ML_CHANNEL`, `DISCORD_ML_ALERTS` | #ml-picks | MACHINE LEARNING PICKS |
| `DISCORD_MASTER_PICKS`, `DISCORD_WEBHOOK`, `DISCORD_WEBHOOK_PROPICKS`, `DISCORD_WEBHOOK_DNA_MASTER` | #master-picks | MASTER PICKS |
| `DISCORD_WEBHOOK_CONVICTION` | #conviction-picks | Conviction Picks |
| `DISCORD_WEBHOOK_FRESHPICKS`, `DISCORD_FRESHPICKS`, `DISCORD_FRESH_PICKS` | #freshpicks | Fresh Picks |
| `DISCORD_WEBHOOK_SANDBOX`, `DISCORD_SANDBOX` | #sandbox | SANDBOXER |
| `DISCORD_NOTIFICATIONS`, `DISCORD_QUALITY_ALERTS`, `DISCORD_REPORTS`, `DISCORD_HEALTH_ALERTS` | #notifications | Captain Hook |
| `DISCORD_GENERAL` | #general | Spidey Bot |
| `DISCORD_SIGNAL_ALERTS` | #crypto-automation | Crypto Automation |

The alias mismatches (`DISCORD_FRESHPICKS`, `DISCORD_FRESH_PICKS`, `DISCORD_SANDBOX`,
`DISCORD_HEALTH_ALERTS`) are resolved by populating the alias secrets, so no workflow edits were
needed. `DISCORD_WEBHOOK_URL` and `DISCORD_HEALTH_WEBHOOK` were already live and left untouched.

**Also corrected:** `DISCORD_ML_CHANNEL_ID` was hardcoded to `1469431505439948920` — which is the
**#notifications** channel id — in `.github/workflows/claude-gainer-tracker.yml`,
`.github/workflows/crypto-ml-tracker.yml`, `.github/workflows/discord-bot.yml`, and
`crypto_gainer_ml/live_predictor.py`. All four now use the real **#ml-picks** id
`1478588195120873472` (confirmed by a `GET` on the #ml-picks webhook).

## Verification

* `curl -s -o /dev/null -w '%{http_code}' <new webhook>` → **200** (webhook name `Paper Trade hoook`, channel `1478614904733827103`).
* `python3 -m py_compile coinglass_strategies/discord_notify.py shared/failover_notifications.py` → OK.
* `git grep -E "(discord|discordapp)\.com/api/webhooks/[0-9]{10,}"` (excluding worktrees) → **no hardcoded webhook URLs remain**.

## Follow-ups (not yet done)

* `DISCORD_BOT_TOKEN` is still unset — Discord *bot commands* (slash commands, `clear-channel`,
  accountability reminders) cannot work without it. A webhook cannot substitute for a bot token.
* The dead URL still exists in local `.worktrees/` and `.claude/worktrees/` copies (untracked).
* Consider a pre-commit hook to block future Discord webhook literals in tracked files.

## Follow-up completed — 2026-10-04: loud failure on a dead webhook

**Done:** response-code validation so a future dead webhook fails loudly instead of being
swallowed.

* `coinglass_strategies/discord_notify.py` — new `DiscordWebhookError`. `_post()` now treats a
  4xx response (other than 429) as permanent: it logs the status + body at ERROR level and
  **raises**, so an unknown/deleted webhook (HTTP 404 `{"message":"Unknown Webhook"}`) fails the
  workflow instead of silently dropping notifications. Retries are skipped for permanent 4xx
  (previously it retried three times then gave up at warning level).
* `shared/failover_notifications.py` — `DiscordWebhookChannel.send()` now logs the failure at
  ERROR level (including the HTTP status) before recording it, so a dead primary webhook is
  visible rather than only being recorded internally and masked by the file fallback.
* `tests/test_coinglass_discord_webhook_failure.py` (new) — asserts 404/401 raise
  `DiscordWebhookError` (and are not retried), a 204 does not raise, and an unset webhook makes
  no HTTP call. Run: `python3 -m pytest tests/test_coinglass_discord_webhook_failure.py -q` →
  4 passed. Existing `tests/test_discord_job_failure.py` + `tests/test_discord_quality_badge.py`
  still pass (11 passed total).
* Verified no hardcoded webhook literals remain in tracked files:
  `git grep -nE '(discord|discordapp)\.com/api/webhooks/[0-9]{10,}'` → no matches.
