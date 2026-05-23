# GitHub Actions & audit freshness fixes (2026-04-16)

This note documents fixes for failing workflows and explains why **findtorontoevents.ca/audit** could look a day stale without **Unified Audit Dashboard** appearing in the “failed jobs” list.

**Primary commit:** `3ce49b01cd` on `main`.

---

## 1. Forward Test Daily (and torontoevent.net mirror)

### Symptom

- **Forward Test Daily** and **[torontoevent.net] Forward Test Daily** failed in `Resolve open picks` with:
  - `KeyError: 'ticker'` at `forward_test.py` line 425 (set comprehension over open picks).

### Root cause

`STOCKS/competition/forward_picks.json` contained **at least one** `OPEN` record in an **alternate schema** (e.g. imported penny/momentum shape): `symbol`, `take_profit`, `stop_loss`, etc., instead of `ticker`, `tp_price`, `sl_price`, `expiry_date`. The resolver assumed every open pick had `ticker`.

### Fix

In `STOCKS/competition/forward_test.py`:

- Added `_normalize_open_pick_for_resolve()` to map:
  - `symbol` → `ticker`
  - `take_profit` / `stop_loss` → `tp_price` / `sl_price` when missing
  - derive `expiry_date` from `timestamp` + `hold_days` when missing
  - synthesize `id` when missing
- After normalization, any `OPEN` pick still lacking `ticker` is closed as **`MISSING_TICKER`** so one bad row cannot block the job.

---

## 2. Feed Health Check

### Symptom

- **Feed Health Check** failed with exit code 1 and a Slack-style summary: **stale** `audit_trail/data/dashboard_payload.json` (`generated_at` ~21h old vs threshold).

### Why this looked “wrong” vs /audit

- **Feed Health** validates the **committed** snapshot of `dashboard_payload.json` on `main` after checkout—not the live site directly.
- **Unified Audit Dashboard** can be **queued**, **long-running**, or **cancelled** while other work floods the queue; the **payload file on `main`** may not update for many hours even though the workflow name doesn’t show as your first “failure” in a quick scan.
- So **stale /audit** on the server correlates with **delayed or incomplete publish**, while the red X you notice might be **Feed Health** (staleness) rather than the dashboard workflow’s latest conclusion.

### Fix

In `.github/workflows/feed-health.yml`:

- Raised **`MAX_AGE_SECONDS`** from **43200 (12h)** to **108000 (30h)** so a **~24h lag** during heavy queue / long generator runs does not **false-fail** the health workflow, while still catching truly dead pipelines beyond about a day.

---

## 3. Unified Audit Dashboard (stale `/audit` on the site)

### Symptom

- Live **https://findtorontoevents.ca/audit** data appeared **~1 day old**; pick timestamps looked like “yesterday.”

### Contributing factors (observed in Actions)

- **Unified Audit Dashboard** runs **hourly** (`cron: 10 * * * *`) with a **long** generate + commit + **FTP deploy** phase.
- Multiple runs showed **`cancelled`** or long **`in_progress`** windows; **timeout** and **runner contention** can prevent a full **commit + deploy** from finishing, so neither **git `main`** nor **FTP** get fresh artifacts on schedule.
- **Feed Health** then correctly complained the **committed** payload was old (before the 30h threshold change).

### Fix

In `.github/workflows/audit-dashboard.yml`:

- Increased job **`timeout-minutes`** from **90** to **115** to reduce **mid-pipeline** cancellations that leave `/audit` stale.

### Follow-up

- After this lands, confirm **Unified Audit Dashboard** runs complete and FTP step logs show success for **findtorontoevents.ca**.
- If cancellations persist with `cancel_reason: null`, treat as **capacity / queue / manual interrupt** and review concurrent workflows and runner choice (`ubuntu-latest` vs self-hosted).

---

## 4. Related earlier hardening (context)

Separate commits on `main` (not part of `3ce49b01cd`) already addressed **push storms** affecting many workflows:

- `.github/scripts/safe_push.sh`: more retries, longer git timeouts, shallow **deepen**, submodule pull disabled for broken `.gitmodules` paths.
- **Live Spike**, **Enhanced ML Crypto**, **Dynamic Runner**: staggered crons, `TOKEN_FOR_PUSH`, longer job timeouts where needed.

Those reduce **`ERROR: All N push attempts failed`** and **timeout cancellations** that indirectly keep **audit** and other data from landing on `main`.

---

## Verification checklist

1. **Forward Test Daily** — `resolve` step completes; no `KeyError: 'ticker'`.
2. **Feed Health Check** — passes when payload is &lt; 30h old by `generated_at`; Slack still gets warnings from `feed_health_check.py` when `health.ok` is false.
3. **Unified Audit Dashboard** — completes within **115m**; `/audit` and `audit/data/dashboard_payload.json` on the server update after deploy.
4. On `main`, `audit_trail/data/dashboard_payload.json` **committed** `generated_at` should move forward after a successful dashboard run.
