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

1. **Stored the replacement #paper-trade webhook as GitHub secrets** (never in the repo):
   * `DISCORD_WEBHOOK_PAPERTRADE`
   * `DISCORD_WEBHOOK_PAPER_TRADE` (alias used by `paper_trading/discord_reporter.py` and
     `strategy_health/hoffman_tracker.py`)
2. **Removed the hardcoded dead URL** and made both code paths env-only:
   * `coinglass_strategies/discord_notify.py` → `os.environ.get("DISCORD_WEBHOOK_PAPERTRADE", "")`
   * `shared/failover_notifications.py` → `os.getenv("DISCORD_WEBHOOK_URL") or os.getenv("DISCORD_WEBHOOK_PAPERTRADE", "")`
3. **Scrubbed the dead URL from the two plan docs** (replaced with a placeholder).

## Verification

* `curl -s -o /dev/null -w '%{http_code}' <new webhook>` → **200** (webhook name `Paper Trade hoook`, channel `1478614904733827103`).
* `python3 -m py_compile coinglass_strategies/discord_notify.py shared/failover_notifications.py` → OK.
* `git grep -E "(discord|discordapp)\.com/api/webhooks/[0-9]{10,}"` (excluding worktrees) → **no hardcoded webhook URLs remain**.

## Follow-ups (not yet done)

* Broken-channel redirect: the user offered to point other broken channels at the #paper-trade
  hook. Not done unilaterally — that would funnel every alert into one channel. Decide per channel.
* Fix secret-name aliasing so the existing secrets are found
  (`DISCORD_FRESHPICKS`→`DISCORD_WEBHOOK_FRESHPICKS`, `DISCORD_SANDBOX`→`DISCORD_WEBHOOK_SANDBOX`,
  `DISCORD_HEALTH_ALERTS`→`DISCORD_HEALTH_WEBHOOK`, `DISCORD_FRESH_PICKS`→`DISCORD_WEBHOOK_FRESHPICKS`).
* Add response-code validation so a 404 fails loudly instead of being swallowed.
* The dead URL still exists in local `.worktrees/` and `.claude/worktrees/` copies (untracked).
* Consider a `git secret` / pre-commit hook to block future webhook literals.
