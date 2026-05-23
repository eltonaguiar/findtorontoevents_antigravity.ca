# GITHUB ACTIONS HEALTH MONITOR — CURSOR

**Monitoring started:** 2026-05-23 09:58:13 UTC  
**Check interval:** 15 minutes  
**Script:** `tools/gha_health_monitor_cursor.py`  
**Context:** Post-major GitHub restore — tracking traction

## Executive summary (Cursor session 2026-05-23)

| Area | Status | Notes |
|------|--------|-------|
| **FavCreators `/fc/#/guest`** | ✅ Fixed | `.env` deployed; `status.php` → `db: connected` |
| **MySQL Trading Picks Sync** | ⚠️ Partial | Auth **fixed** (`printf` secrets). Run 26329747150: 4000/4006 upserted; 6 dedup-key collisions → exit 1. **Fix staged locally** in `mysql_trading_sync.py` (treat errno 1062 as skip). Needs commit+push. |
| **Strategy Health Monitor/Report** | ⏳ Pending | Should pass after `MYSQL_PASSWORD` fix propagates |
| **GitHub Pages deploys** | ❌ Blocked | Pages not enabled — [settings/pages](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/settings/pages) |
| **FTP deploy workflows** | ⚠️ Partial | `FTP_HOST` was bad earlier; verify `ftps2.50webs.com` in secrets |
| **DB Sync mirror (torontoevent.net)** | ❌ Blocked | GoDaddy FTP creds / lftp path issue |

**Monitor daemon:** `python3 tools/gha_health_monitor_cursor.py` (background PID logged in `.cursor/gha_health_state.json`)

**Manual one-shot check:** `python3 tools/gha_health_monitor_cursor.py --once`

---

## CHECK 2026-05-23 09:58:18 UTC
- **Stale failures** (latest run failed, no success since): **6**
- **In progress:** 4
- **Recent failures** (last 15 runs): 1

### ❌ Claude's Test - Portfolio Manager
- Run: [26329415484](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26329415484)
- Failed at: 2026-05-23T09:36:37Z
- **Classification:** FLAKY — git push/rebase race during auto-commit
- **Log tail:**
```
manage-portfolios	Commit updated state and dashboard	2026-05-23T09:52:27.2354995Z   (use "git add <file>..." to update what will be committed)
manage-portfolios	Commit updated state and dashboard	2026-05-23T09:52:27.2355391Z   (use "git restore <file>..." to discard changes in working directory)
manage-portfolios	Commit updated state and dashboard	2026-05-23T09:52:27.2355778Z 	modified:   audit_dashboard/claudes_test.html
manage-portfolios	Commit updated state and dashboard	2026-05-23T09:52:27.2356126Z 	modified:   audit_dashboard/data/claudes_test_dashboard.json
manage-portfolios	Commit updated state and dashboard	2026-05-23T09:52:27.2356504Z 	modified:   audit_dashboard/data/claudes_test_state.json
manage-portfolios	Commit updated state and dashboard	2026-05-23T09:52:27.2356876Z 	modified:   audit_dashboard/data/claudes_test_state.json.bak
manage-portfolios	Commit updated state and dashboard	2026-05-23T09:52:27.2357106Z 
manage-portfolios	Commit updated state and dashboard	2026-05-23T09:52:27.2357289Z no changes added to commit (use "git add" and/or "git commit -a")
manage-portfolios	Commit updated state and dashboard	2026-05-23T09:52:27.2357861Z Dropped refs/stash@{0} (603db1047e6e2fb789321c6559794ad45a62e8f4)
manage-portfolios	Commit updated state and dashboard	2026-05-23T09:52:27.3893203Z [main 531bc36d] chore(claudes-test): update portfolio state [skip ci]
manage-portfolios	Commit updated state and dashboard	2026-05-23T09:52:27.3893934Z  3 files changed, 4606 insertions(+), 5026 deletions(-)
manage-portfolios	Commit updated state and dashboard	2026-05-23T09:52:27.4364397Z ##[error]Process completed with exit code 128.
```

### ❌ Deploy Rise of the Claw Dashboard
- Run: [26328930891](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26328930891)
- Failed at: 2026-05-23T09:10:41Z
- **Classification:** ENV — GitHub Pages not enabled on repo
- **Log tail:**
```
deploy	Deploy to GitHub Pages	2026-05-23T09:15:44.0515464Z 	"artifact_id": 7175886383,
deploy	Deploy to GitHub Pages	2026-05-23T09:15:44.0515980Z 	"pages_build_version": "dcd726709928edce780d37c400095f5fa710da43",
deploy	Deploy to GitHub Pages	2026-05-23T09:15:44.0585018Z 	"oidc_token": "***"
deploy	Deploy to GitHub Pages	2026-05-23T09:15:44.0585392Z }
deploy	Deploy to GitHub Pages	2026-05-23T09:15:44.2982996Z ##[error]Creating Pages deployment failed
deploy	Deploy to GitHub Pages	2026-05-23T09:15:44.2993795Z ##[error]HttpError: Not Found
deploy	Deploy to GitHub Pages	    at /home/runner/work/_actions/actions/deploy-pages/v4/node_modules/@octokit/request/dist-node/index.js:124:1
deploy	Deploy to GitHub Pages	    at processTicksAndRejections (node:internal/process/task_queues:95:5)
deploy	Deploy to GitHub Pages	    at createPagesDeployment (/home/runner/work/_actions/actions/deploy-pages/v4/src/internal/api-client.js:125:1)
deploy	Deploy to GitHub Pages	    at Deployment.create (/home/runner/work/_actions/actions/deploy-pages/v4/src/internal/deployment.js:74:1)
deploy	Deploy to GitHub Pages	    at main (/home/runner/work/_actions/actions/deploy-pages/v4/src/index.js:30:1)
deploy	Deploy to GitHub Pages	2026-05-23T09:15:44.2998293Z ##[error]Error: Failed to create deployment (status: 404) with build version dcd726709928edce780d37c400095f5fa710da43. Request ID A81A:3230E1:9B8F632:2545DBD9:6A117040 Ensure GitHub Pages has been enabled: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/settings/pages
```

### ❌ Run Backtests & Deploy Dashboards
- Run: [26328521712](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26328521712)
- Failed at: 2026-05-23T08:49:48Z
- **Classification:** ENV — FTP_HOST / DNS misconfigured in secrets
- **Log tail:**
```
backtest	Deploy dashboard to FTP	2026-05-23T09:54:21.2595540Z     self.connect(host)
backtest	Deploy dashboard to FTP	2026-05-23T09:54:21.2596112Z   File "/usr/lib/python3.12/ftplib.py", line 158, in connect
backtest	Deploy dashboard to FTP	2026-05-23T09:54:21.2596984Z     self.sock = socket.create_connection((self.host, self.port), self.timeout,
backtest	Deploy dashboard to FTP	2026-05-23T09:54:21.2597649Z                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
backtest	Deploy dashboard to FTP	2026-05-23T09:54:21.2598082Z   File "/usr/lib/python3.12/socket.py", line 828, in create_connection
backtest	Deploy dashboard to FTP	2026-05-23T09:54:21.2605156Z     for res in getaddrinfo(host, port, 0, SOCK_STREAM):
backtest	Deploy dashboard to FTP	2026-05-23T09:54:21.2605708Z                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
backtest	Deploy dashboard to FTP	2026-05-23T09:54:21.2606332Z   File "/usr/lib/python3.12/socket.py", line 963, in getaddrinfo
backtest	Deploy dashboard to FTP	2026-05-23T09:54:21.2607455Z     for res in _socket.getaddrinfo(host, port, family, type, proto, flags):
backtest	Deploy dashboard to FTP	2026-05-23T09:54:21.2608118Z                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
backtest	Deploy dashboard to FTP	2026-05-23T09:54:21.2608721Z socket.gaierror: [Errno ***2] Name or service not known
backtest	Deploy dashboard to FTP	2026-05-23T09:54:21.2764014Z ##[error]Process completed with exit code 1.
```

### ❌ DB Sync: Bi-directional User Data
- Run: [26328521362](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26328521362)
- Failed at: 2026-05-23T08:49:47Z
- **Classification:** ENV — FTP session dropped (mirror host creds or TLS)
- **Log tail:**
```
Bi-directional user data sync	Deploy sync scripts to torontoevent.net	2026-05-23T09:51:30.9307048Z open: ***: string start/ends with forbidden hyphen
Bi-directional user data sync	Deploy sync scripts to torontoevent.net	2026-05-23T09:51:30.9308410Z mkdir: Not connected
Bi-directional user data sync	Deploy sync scripts to torontoevent.net	2026-05-23T09:51:30.9310001Z mput: db_sync_apply.php: Not connected
Bi-directional user data sync	Deploy sync scripts to torontoevent.net	2026-05-23T09:51:30.9310860Z mput: db_sync_export.php: Not connected
Bi-directional user data sync	Deploy sync scripts to torontoevent.net	2026-05-23T09:51:30.9314599Z mput: db_sync_initial_reconcile.php: Not connected
Bi-directional user data sync	Deploy sync scripts to torontoevent.net	2026-05-23T09:51:30.9315160Z mput: db_sync_mark.php: Not connected
Bi-directional user data sync	Deploy sync scripts to torontoevent.net	2026-05-23T09:51:30.9315588Z mput: db_sync_prune.php: Not connected
Bi-directional user data sync	Deploy sync scripts to torontoevent.net	2026-05-23T09:51:30.9315894Z mput: ensure_sync_tables.php: Not connected
Bi-directional user data sync	Deploy sync scripts to torontoevent.net	2026-05-23T09:51:30.9316199Z mput: sync_config.php: Not connected
Bi-directional user data sync	Deploy sync scripts to torontoevent.net	2026-05-23T09:51:30.9316467Z mput: sync_helpers.php: Not connected
Bi-directional user data sync	Deploy sync scripts to torontoevent.net	2026-05-23T09:51:30.9316724Z mput: sync_status.php: Not connected
Bi-directional user data sync	Deploy sync scripts to torontoevent.net	2026-05-23T09:51:30.9331100Z ##[error]Process completed with exit code 1.
```

### ❌ Strategy Health Monitor
- Run: [26328384733](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26328384733)
- Failed at: 2026-05-23T08:42:29Z
- **Classification:** ENV — MySQL password/secret (check trailing newline in gh secret set)
- **Log tail:**
```
refresh	Run health monitor	2026-05-23T09:51:18.3119722Z                   ^^^^^^^^^^^^^^^^^^^
refresh	Run health monitor	2026-05-23T09:51:18.3120216Z   File "/home/runner/.local/lib/python3.12/site-packages/pymysql/connections.py", line 803, in _read_packet
refresh	Run health monitor	2026-05-23T09:51:18.3120690Z     packet.raise_for_error()
refresh	Run health monitor	2026-05-23T09:51:18.3121142Z   File "/home/runner/.local/lib/python3.12/site-packages/pymysql/protocol.py", line 219, in raise_for_error
refresh	Run health monitor	2026-05-23T09:51:18.3121611Z     err.raise_mysql_exception(self._data)
refresh	Run health monitor	2026-05-23T09:51:18.3122089Z   File "/home/runner/.local/lib/python3.12/site-packages/pymysql/err.py", line 154, in raise_mysql_exception
refresh	Run health monitor	2026-05-23T09:51:18.3122610Z     raise errorclass(errno, errval, sqlstate=sqlstate)
refresh	Run health monitor	2026-05-23T09:51:18.3123488Z pymysql.err.OperationalError: (1045, "Access denied for user 'ejaguiar1_stocks'@'20.55.46.161' (using password: YES)")
refresh	Run health monitor	2026-05-23T09:51:18.3124320Z Strategy Health Monitor — 2026-05-23T09:51:18.160038Z
refresh	Run health monitor	2026-05-23T09:51:18.3124628Z Fee rate: 0.15% per trade
refresh	Run health monitor	2026-05-23T09:51:18.3124768Z 
refresh	Run health monitor	2026-05-23T09:51:18.3354443Z ##[error]Process completed with exit code 1.
```

### ❌ Strategy Health Report
- Run: [26328352266](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26328352266)
- Failed at: 2026-05-23T08:40:46Z
- **Classification:** ENV — MySQL password/secret (check trailing newline in gh secret set)
- **Log tail:**
```
report	Post health report	2026-05-23T09:51:15.6709182Z   File "/home/runner/.local/lib/python3.12/site***packages/pymysql/connections.py", line 1000, in _request_authentication
report	Post health report	2026-05-23T09:51:15.6709676Z     auth_packet = self._read_packet()
report	Post health report	2026-05-23T09:51:15.6709923Z                   ^^^^^^^^^^^^^^^^^^^
report	Post health report	2026-05-23T09:51:15.6710378Z   File "/home/runner/.local/lib/python3.12/site***packages/pymysql/connections.py", line 803, in _read_packet
report	Post health report	2026-05-23T09:51:15.6710917Z     packet.raise_for_error()
report	Post health report	2026-05-23T09:51:15.6711362Z   File "/home/runner/.local/lib/python3.12/site***packages/pymysql/protocol.py", line 219, in raise_for_error
report	Post health report	2026-05-23T09:51:15.6711838Z     err.raise_mysql_exception(self._data)
report	Post health report	2026-05-23T09:51:15.6712319Z   File "/home/runner/.local/lib/python3.12/site***packages/pymysql/err.py", line 154, in raise_mysql_exception
report	Post health report	2026-05-23T09:51:15.6712827Z     raise errorclass(errno, errval, sqlstate=sqlstate)
report	Post health report	2026-05-23T09:51:15.6713380Z pymysql.err.OperationalError: (1045, "Access denied for user 'ejaguiar1_stocks'@'20.118.213.17' (using password: YES)")
report	Post health report	2026-05-23T09:51:15.6713937Z Strategy Health Report *** 2026***05***23T09:51:15.309529Z
report	Post health report	2026-05-23T09:51:15.6959238Z ##[error]Process completed with exit code 1.
```

**New deep-dives this check:** Claude's Test - Portfolio Manager, Deploy Rise of the Claw Dashboard, Run Backtests & Deploy Dashboards, DB Sync: Bi-directional User Data, Strategy Health Monitor, Strategy Health Report

⏭️ **Skipping next check** — complicated failure(s); cooldown 15 min until 10:13 UTC.

---
**Daemon loop started** 2026-05-23 09:58:25 UTC (every 15 min)

## CHECK 2026-05-23 09:58:25 UTC — SKIPPED (deep-dive cooldown)
_Resume after 10:13 UTC_

## CHECK 2026-05-23 10:04:11 UTC — SKIPPED (deep-dive cooldown)
_Resume after 10:13 UTC_

## CHECK 2026-05-23 10:05 UTC — CURSOR DEEP-DIVE (manual, post-repro)

### ✅ MySQL auth restored
- Run [26329747150](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26329747150): **Connected** on all 3 attempts after `printf` secret fix.
- **4000 rows upserted**, 46,075 total picks in DB.

### ⚠️ False-negative workflow failure
- **6 upserts** hit `1062 Duplicate entry` on `uq_trading_picks_dedup` (clone_hl_copy_lb picks — same symbol/strategy/entry already stored under different id).
- `mysql_trading_sync.py` returns exit **1** if any errors → shell wrapper retries 3× then fails.
- **Local fix applied:** errno 1062 treated as dedup skip (non-fatal). **Not yet on main** — commit+push required for CI.

### Stale count: 7 workflows
Unchanged blockers: GitHub Pages (404), FTP mirror sync, git push race (Claude's Test), Strategy Health (await next hourly run with fixed secret).

### Monitor daemon
- PID 707915 still running; cooldown cleared — next auto-check ~10:13 UTC.

---

## CHECK 2026-05-23 10:13:30 UTC
- **Stale failures** (latest run failed, no success since): **3**
- **In progress:** 5
- **Recent failures** (last 15 runs): 1

### ❌ Claude's Test - Portfolio Manager
- Run: [26329985743](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26329985743)
- Failed at: 2026-05-23T10:08:02Z
- **Classification:** FLAKY — git push/rebase race during auto-commit
- **Log tail:**
```
manage-portfolios	Commit updated state and dashboard	2026-05-23T10:09:35.7088238Z   (use "git add <file>..." to update what will be committed)
manage-portfolios	Commit updated state and dashboard	2026-05-23T10:09:35.7089110Z   (use "git restore <file>..." to discard changes in working directory)
manage-portfolios	Commit updated state and dashboard	2026-05-23T10:09:35.7089732Z 	modified:   audit_dashboard/claudes_test.html
manage-portfolios	Commit updated state and dashboard	2026-05-23T10:09:35.7090335Z 	modified:   audit_dashboard/data/claudes_test_dashboard.json
manage-portfolios	Commit updated state and dashboard	2026-05-23T10:09:35.7090966Z 	modified:   audit_dashboard/data/claudes_test_state.json
manage-portfolios	Commit updated state and dashboard	2026-05-23T10:09:35.7091565Z 	modified:   audit_dashboard/data/claudes_test_state.json.bak
manage-portfolios	Commit updated state and dashboard	2026-05-23T10:09:35.7091936Z 
manage-portfolios	Commit updated state and dashboard	2026-05-23T10:09:35.7092200Z no changes added to commit (use "git add" and/or "git commit -a")
manage-portfolios	Commit updated state and dashboard	2026-05-23T10:09:35.7098186Z Dropped refs/stash@{0} (e031fc70a8e017d3911a193b6ba836c187d96a85)
manage-portfolios	Commit updated state and dashboard	2026-05-23T10:09:35.9827493Z [main be22a4da] chore(claudes-test): update portfolio state [skip ci]
manage-portfolios	Commit updated state and dashboard	2026-05-23T10:09:35.9828597Z  3 files changed, 4625 insertions(+), 5109 deletions(-)
manage-portfolios	Commit updated state and dashboard	2026-05-23T10:09:36.0908684Z ##[error]Process completed with exit code 128.
```

### ❌ Deploy Rise of the Claw Dashboard
- Run: [26329961213](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26329961213)
- Failed at: 2026-05-23T10:06:41Z
- **Classification:** ENV — GitHub Pages not enabled on repo
- **Log tail:**
```
deploy	Deploy to GitHub Pages	2026-05-23T10:11:55.6279166Z 	"artifact_id": 7176179697,
deploy	Deploy to GitHub Pages	2026-05-23T10:11:55.6279738Z 	"pages_build_version": "ba31bca10d5015a9687ba0513047d04d89403052",
deploy	Deploy to GitHub Pages	2026-05-23T10:11:55.6357999Z 	"oidc_token": "***"
deploy	Deploy to GitHub Pages	2026-05-23T10:11:55.6358434Z }
deploy	Deploy to GitHub Pages	2026-05-23T10:11:55.8980298Z ##[error]Creating Pages deployment failed
deploy	Deploy to GitHub Pages	2026-05-23T10:11:55.8991348Z ##[error]HttpError: Not Found
deploy	Deploy to GitHub Pages	    at /home/runner/work/_actions/actions/deploy-pages/v4/node_modules/@octokit/request/dist-node/index.js:124:1
deploy	Deploy to GitHub Pages	    at processTicksAndRejections (node:internal/process/task_queues:95:5)
deploy	Deploy to GitHub Pages	    at createPagesDeployment (/home/runner/work/_actions/actions/deploy-pages/v4/src/internal/api-client.js:125:1)
deploy	Deploy to GitHub Pages	    at Deployment.create (/home/runner/work/_actions/actions/deploy-pages/v4/src/internal/deployment.js:74:1)
deploy	Deploy to GitHub Pages	    at main (/home/runner/work/_actions/actions/deploy-pages/v4/src/index.js:30:1)
deploy	Deploy to GitHub Pages	2026-05-23T10:11:55.8995644Z ##[error]Error: Failed to create deployment (status: 404) with build version ba31bca10d5015a9687ba0513047d04d89403052. Request ID 2412:278746:181B31F:5D3006E:6A117D6B Ensure GitHub Pages has been enabled: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/settings/pages
```

### ❌ DNA Genome Daily Pipeline
- Run: [26329331253](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26329331253)
- Failed at: 2026-05-23T09:32:09Z
- **Classification:** UNKNOWN — needs manual log review
- **Log tail:**
```
deploy-to-ftp	Deploy to findtorontoevents.ca	﻿2026-05-23T10:08:12.4949142Z ##[group]Run SamKirkland/FTP-Deploy-Action@4.3.0
deploy-to-ftp	Deploy to findtorontoevents.ca	2026-05-23T10:08:12.4949524Z with:
deploy-to-ftp	Deploy to findtorontoevents.ca	2026-05-23T10:08:12.4949732Z   local-dir: ./genome/
deploy-to-ftp	Deploy to findtorontoevents.ca	2026-05-23T10:08:12.4949994Z   server-dir: /findtorontoevents.ca/genome/
deploy-to-ftp	Deploy to findtorontoevents.ca	2026-05-23T10:08:12.4950301Z   protocol: ftps
deploy-to-ftp	Deploy to findtorontoevents.ca	2026-05-23T10:08:12.4950515Z ##[endgroup]
deploy-to-ftp	Deploy to findtorontoevents.ca	2026-05-23T10:08:12.5395941Z ##[error]Error: Input required and not supplied: server
```

**New deep-dives this check:** Claude's Test - Portfolio Manager, Deploy Rise of the Claw Dashboard, DNA Genome Daily Pipeline

⏭️ **Skipping next check** — complicated failure(s); cooldown 15 min until 10:28 UTC.
