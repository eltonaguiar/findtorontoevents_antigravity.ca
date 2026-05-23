# GITHUB ACTIONS HEALTH MONITOR — CURSOR

**Monitoring started:** 2026-05-23 09:58:13 UTC  
**Check interval:** 15 minutes  
**Script:** `tools/gha_health_monitor_cursor.py`  
**Context:** Post-major GitHub restore — tracking traction

## Executive summary (Cursor session 2026-05-23)

| Area | Status | Notes |
|------|--------|-------|
| **FavCreators `/fc/#/guest`** | ✅ Fixed | `.env` deployed; `status.php` → `db: connected` |
| **MySQL Trading Picks Sync** | 🔄 Verifying | Dedup fix pushed (`a331aea2`); run [26330281519](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26330281519) in progress on runner |
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

## CHECK 2026-05-23 10:24 UTC — CURSOR POST-PUSH

### ✅ Committed & pushed (`a331aea2`)
- `mysql_trading_sync.py` — errno 1062 dedup skip
- `db_test.php` — PHP 5.2 fix
- `tools/gha_health_monitor_cursor.py` + `___HELL_HEALTH_CURSOR.MD`

### 🔄 MySQL sync verification run [26330281519](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26330281519)
- Status: **pending** (queued on runner as of 10:28 UTC)

### 📉 Stale failures: **7 → 2-3** (traction improving)
**Cleared since session start:** MySQL Trading Picks Sync (auth), Strategy Health Monitor/Report, DB Sync, Run Backtests, Claude's Test (intermittent).

**Still stale (10:28 UTC):**
- Deploy Rise of the Claw Dashboard — GitHub Pages 404
- CI Tests — new failure (investigating)
- Audit Drift Telemetry — new failure (investigating)

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

## CHECK 2026-05-23 10:29:02 UTC
- **Stale failures** (latest run failed, no success since): **3**
- **In progress:** 5
- **Recent failures** (last 15 runs): 1

### ❌ CI Tests
- Run: [26330280855](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26330280855)
- Failed at: 2026-05-23T10:24:16Z
- **Classification:** UNKNOWN — needs manual log review
- **Log tail:**
```
test (3.12)	Run all tests	2026-05-23T10:26:51.5014918Z SKIPPED [1] tests/test_hf_pick_contracts.py:13: could not import 'pydantic': No module named 'pydantic'
test (3.12)	Run all tests	2026-05-23T10:26:51.5015832Z SKIPPED [1] tests/test_pick_schema.py:5: could not import 'pydantic': No module named 'pydantic'
test (3.12)	Run all tests	2026-05-23T10:26:51.5016479Z SKIPPED [1] tests/test_quan_engine_inverse_adapter.py:12: quan_engine_inverse feature removed from antigravity_strategies
test (3.12)	Run all tests	2026-05-23T10:26:51.5017150Z SKIPPED [1] tests/test_regime_gate_keltner.py:12: regime gate helpers removed from keltner strategy module
test (3.12)	Run all tests	2026-05-23T10:26:51.5017752Z SKIPPED [1] tests/test_regime_gate_squeeze.py:13: regime gate helpers removed from challenge_v3
test (3.12)	Run all tests	2026-05-23T10:26:51.5018400Z SKIPPED [1] tests/test_signal_spec.py:13: could not import 'pydantic': No module named 'pydantic'
test (3.12)	Run all tests	2026-05-23T10:26:51.5018977Z SKIPPED [1] tests/test_system_c_attention_sequence.py:8: could not import 'torch': No module named 'torch'
test (3.12)	Run all tests	2026-05-23T10:26:51.5019617Z ERROR tests/test_audit_metric_invariants.py
test (3.12)	Run all tests	2026-05-23T10:26:51.5019903Z ERROR tests/test_dashboard_payload_contract.py
test (3.12)	Run all tests	2026-05-23T10:26:51.5020251Z !!!!!!!!!!!!!!!!!!! Interrupted: 2 errors during collection !!!!!!!!!!!!!!!!!!!!
test (3.12)	Run all tests	2026-05-23T10:26:51.5020681Z =========== 7 skipped, 10 deselected, 1 warning, 2 errors in 25.39s ============
test (3.12)	Run all tests	2026-05-23T10:26:52.1060358Z ##[error]Process completed with exit code 2.
```

### ❌ Audit Drift Telemetry
- Run: [26330204496](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26330204496)
- Failed at: 2026-05-23T10:20:09Z
- **Classification:** UNKNOWN — needs manual log review
- **Log tail:**
```
drift	Build canonical backtest-forward drift report	2026-05-23T10:21:28.6628890Z               ^^^^^^^^^^^^^^^^^^^^^^
drift	Build canonical backtest-forward drift report	2026-05-23T10:21:28.6629979Z   File "/home/runner/work/findtorontoevents_antigravity.ca/findtorontoevents_antigravity.ca/tools/drift/build_backtest_forward_drift.py", line 40, in _read_json
drift	Build canonical backtest-forward drift report	2026-05-23T10:21:28.6630924Z     return json.loads(path.read_text(encoding="utf-8"))
drift	Build canonical backtest-forward drift report	2026-05-23T10:21:28.6631326Z                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
drift	Build canonical backtest-forward drift report	2026-05-23T10:21:28.6631978Z   File "/opt/hostedtoolcache/Python/3.11.15/x64/lib/python3.11/pathlib.py", line 1058, in read_text
drift	Build canonical backtest-forward drift report	2026-05-23T10:21:28.6871727Z     with self.open(mode='r', encoding=encoding, errors=errors) as f:
drift	Build canonical backtest-forward drift report	2026-05-23T10:21:28.6872628Z          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
drift	Build canonical backtest-forward drift report	2026-05-23T10:21:28.6873797Z   File "/opt/hostedtoolcache/Python/3.11.15/x64/lib/python3.11/pathlib.py", line 1044, in open
drift	Build canonical backtest-forward drift report	2026-05-23T10:21:28.6875101Z     return io.open(self, mode, buffering, encoding, errors, newline)
drift	Build canonical backtest-forward drift report	2026-05-23T10:21:28.6875990Z            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
drift	Build canonical backtest-forward drift report	2026-05-23T10:21:28.6877327Z FileNotFoundError: [Errno 2] No such file or directory: 'audit_dashboard/data/dashboard_data.json'
drift	Build canonical backtest-forward drift report	2026-05-23T10:21:28.6944832Z ##[error]Process completed with exit code 1.
```

### (cached) Deploy Rise of the Claw Dashboard — run `26329961213`

**New deep-dives this check:** CI Tests, Audit Drift Telemetry

⏭️ **Skipping next check** — complicated failure(s); cooldown 15 min until 10:43 UTC.

## CHECK 2026-05-23 10:36:14 UTC
- **Stale failures** (latest run failed, no success since): **0**
- **In progress:** 13
- **Recent failures** (last 15 runs): 0

✅ **All clear** — no stale failures detected.

## CHECK 2026-05-23 10:37 UTC — Audit Drift Telemetry verified

- **Run [26330501344](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26330501344): ✅ SUCCESS**
- Root cause of [26330204496](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26330204496): missing `dashboard_data.json` + committed stale `tmp/backtest_forward_drift_analysis.json` (30 rows) fooled validate step.
- **Fix (`b0f6b37e`):** `rm -f` stale tmp before build; gate validate/compute/export on `has_drift=1`; monitor skips workflows with later success.
- **Monitor rule:** if latest workflow run is success → skip deep-dive until next failure cycle.

---

## CHECK 2026-05-23 10:44:08 UTC
- **Stale failures** (latest run failed, no success since): **1**
- **In progress:** 6
- **Recent failures** (last 15 runs): 0

### (cached) Deploy Rise of the Claw Dashboard — run `26329961213`

## CHECK 2026-05-23 10:59:13 UTC
- **Stale failures** (latest run failed, no success since): **0**
- **In progress:** 12
- **Recent failures** (last 15 runs): 0

✅ **All clear** — no stale failures detected.

## CHECK 2026-05-23 11:14:18 UTC
- **Stale failures** (latest run failed, no success since): **0**
- **In progress:** 3
- **Recent failures** (last 15 runs): 0

✅ **All clear** — no stale failures detected.

## CHECK 2026-05-23 11:29:23 UTC
- **Stale failures** (latest run failed, no success since): **1**
- **In progress:** 6
- **Recent failures** (last 15 runs): 0

### ❌ CI Tests
- Run: [26331287284](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26331287284)
- Failed at: 2026-05-23T11:18:41Z
- **Classification:** UNKNOWN — needs manual log review
- **Log tail:**
```
test (3.11)	Run all tests	2026-05-23T11:24:05.8995945Z SKIPPED [1] tests/test_tier2_hero_cards.py:310: dashboard_data.json not present in checkout
test (3.11)	Run all tests	2026-05-23T11:24:05.8996607Z SKIPPED [1] tests/test_tradingagents_smoke.py:102: Set TRADINGAGENTS_LIVE_SMOKE=1 to run live TradingAgents smoke tests
test (3.11)	Run all tests	2026-05-23T11:24:05.8997365Z SKIPPED [1] tests/test_tradingagents_smoke.py:117: Set TRADINGAGENTS_LIVE_SMOKE=1 to run live TradingAgents smoke tests
test (3.11)	Run all tests	2026-05-23T11:24:05.8998099Z SKIPPED [1] tests/test_tradingagents_smoke.py:132: Set TRADINGAGENTS_LIVE_SMOKE=1 to run live TradingAgents smoke tests
test (3.11)	Run all tests	2026-05-23T11:24:05.8998836Z SKIPPED [1] tests/test_tradingagents_smoke.py:170: Set TRADINGAGENTS_LIVE_SMOKE=1 to run live TradingAgents smoke tests
test (3.11)	Run all tests	2026-05-23T11:24:05.8999564Z SKIPPED [1] tests/test_tradingagents_smoke.py:183: Set TRADINGAGENTS_LIVE_SMOKE=1 to run live TradingAgents smoke tests
test (3.11)	Run all tests	2026-05-23T11:24:05.9000286Z SKIPPED [1] tests/test_tv_place_pick_fillrelative.py:66: could not import 'websocket': No module named 'websocket'
test (3.11)	Run all tests	2026-05-23T11:24:05.9000924Z SKIPPED [1] tests/test_vt_csv_edge_luxalgo_alts.py:545: No signals generated with this data
test (3.11)	Run all tests	2026-05-23T11:24:05.9002161Z XFAIL tests/test_phantom_halt_mixed_units_regression.py::test_phantom_halt_with_mixed_pnl_units_under_triggers - P0-DATA scope: pnl_pct unit normalization at ingest required first. Round 3 panel 5/5 consensus, reports/round3_bugs_qa_synthesis_2026_04_29.md (P0 items #3 and #5).
test (3.11)	Run all tests	2026-05-23T11:24:05.9003389Z FAILED tests/test_hf_conviction_tier.py::test_tier_b_major - AssertionError: assert None == 'B'
test (3.11)	Run all tests	2026-05-23T11:24:05.9004132Z = 1 failed, 5839 passed, 56 skipped, 10 deselected, 1 xfailed, 6 warnings in 162.03s (0:02:42) =
test (3.11)	Run all tests	2026-05-23T11:24:06.7992782Z ##[error]Process completed with exit code 1.
```

**New deep-dives this check:** CI Tests

⏭️ **Skipping next check** — complicated failure(s); cooldown 15 min until 11:44 UTC.

## CHECK 2026-05-23 11:44:30 UTC
- **Stale failures** (latest run failed, no success since): **1**
- **In progress:** 10
- **Recent failures** (last 15 runs): 0

### (cached) CI Tests — run `26331287284`

## CHECK 2026-05-23 11:59:35 UTC
- **Stale failures** (latest run failed, no success since): **1**
- **In progress:** 1
- **Recent failures** (last 15 runs): 0

### (cached) CI Tests — run `26331287284`

## CHECK 2026-05-23 12:14:40 UTC
- **Stale failures** (latest run failed, no success since): **0**
- **In progress:** 15
- **Recent failures** (last 15 runs): 0

✅ **All clear** — no stale failures detected.

## CHECK 2026-05-23 12:29:44 UTC
- **Stale failures** (latest run failed, no success since): **3**
- **In progress:** 4
- **Recent failures** (last 15 runs): 0

### ❌ Daily Feed Summary
- Run: [26332573320](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26332573320)
- Failed at: 2026-05-23T12:24:02Z
- **Classification:** FLAKY — git push/rebase race during auto-commit
- **Log tail:**
```
generate-summary	Run actions/checkout@v6	2026-05-23T12:24:07.9644981Z [command]/usr/bin/git checkout --progress --force -B main refs/remotes/origin/main
generate-summary	Run actions/checkout@v6	2026-05-23T12:24:08.1943396Z ##[error]fatal: could not read Username for 'https://github.com': terminal prompts disabled
generate-summary	Run actions/checkout@v6	2026-05-23T12:24:08.2188915Z ##[error]fatal: could not fetch e69de29bb2d1d6434b8b29ae775ad8c2e48c5391 from promisor remote
generate-summary	Run actions/checkout@v6	2026-05-23T12:24:08.2225900Z ##[error]The process '/usr/bin/git' failed with exit code 128
generate-summary	Notify sandbox on failure	﻿2026-05-23T12:24:08.2540939Z ##[group]Run bash .github/notify-failure.sh "Daily Feed Summary" "$DISCORD_WEBHOOK_SANDBOX" "eltonaguiar/findtorontoevents_antigravity.ca" "26332573320"
generate-summary	Notify sandbox on failure	2026-05-23T12:24:08.2545118Z [36;1mbash .github/notify-failure.sh "Daily Feed Summary" "$DISCORD_WEBHOOK_SANDBOX" "eltonaguiar/findtorontoevents_antigravity.ca" "26332573320"[0m
generate-summary	Notify sandbox on failure	2026-05-23T12:24:08.2585222Z shell: /usr/bin/bash -e {0}
generate-summary	Notify sandbox on failure	2026-05-23T12:24:08.2586333Z env:
generate-summary	Notify sandbox on failure	2026-05-23T12:24:08.2588915Z   DISCORD_WEBHOOK_SANDBOX: ***
generate-summary	Notify sandbox on failure	2026-05-23T12:24:08.2589963Z ##[endgroup]
generate-summary	Notify sandbox on failure	2026-05-23T12:24:08.2688486Z bash: .github/notify-failure.sh: No such file or directory
generate-summary	Notify sandbox on failure	2026-05-23T12:24:08.2698865Z ##[error]Process completed with exit code 127.
```

### ❌ AI Tournament Pipeline — Daily Picks + DB Ingest
- Run: [26332442616](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26332442616)
- Failed at: 2026-05-23T12:17:59Z
- **Classification:** UNKNOWN — needs manual log review
- **Log tail:**
```
pipeline	Verify output was produced	2026-05-23T12:19:23.0026363Z [36;1mecho "✅ All output files present"[0m
pipeline	Verify output was produced	2026-05-23T12:19:23.0061864Z shell: /usr/bin/bash -e {0}
pipeline	Verify output was produced	2026-05-23T12:19:23.0062120Z env:
pipeline	Verify output was produced	2026-05-23T12:19:23.0062433Z   pythonLocation: /opt/hostedtoolcache/Python/3.11.15/x64
pipeline	Verify output was produced	2026-05-23T12:19:23.0062875Z   PKG_CONFIG_PATH: /opt/hostedtoolcache/Python/3.11.15/x64/lib/pkgconfig
pipeline	Verify output was produced	2026-05-23T12:19:23.0063302Z   Python_ROOT_DIR: /opt/hostedtoolcache/Python/3.11.15/x64
pipeline	Verify output was produced	2026-05-23T12:19:23.0063668Z   Python2_ROOT_DIR: /opt/hostedtoolcache/Python/3.11.15/x64
pipeline	Verify output was produced	2026-05-23T12:19:23.0064295Z   Python3_ROOT_DIR: /opt/hostedtoolcache/Python/3.11.15/x64
pipeline	Verify output was produced	2026-05-23T12:19:23.0064662Z   LD_LIBRARY_PATH: /opt/hostedtoolcache/Python/3.11.15/x64/lib
pipeline	Verify output was produced	2026-05-23T12:19:23.0064978Z ##[endgroup]
pipeline	Verify output was produced	2026-05-23T12:19:23.0137172Z ##[error]No picks file was generated for today
pipeline	Verify output was produced	2026-05-23T12:19:23.0139542Z ##[error]Process completed with exit code 1.
```

### ❌ CI Tests
- Run: [26332369798](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26332369798)
- Failed at: 2026-05-23T12:14:12Z
- **Classification:** UNKNOWN — needs manual log review
- **Log tail:**
```
test (3.11)	Run all tests	2026-05-23T12:21:11.7106797Z SKIPPED [1] tests/test_tier2_hero_cards.py:310: dashboard_data.json not present in checkout
test (3.11)	Run all tests	2026-05-23T12:21:11.7108681Z SKIPPED [1] tests/test_tradingagents_smoke.py:102: Set TRADINGAGENTS_LIVE_SMOKE=1 to run live TradingAgents smoke tests
test (3.11)	Run all tests	2026-05-23T12:21:11.7110874Z SKIPPED [1] tests/test_tradingagents_smoke.py:117: Set TRADINGAGENTS_LIVE_SMOKE=1 to run live TradingAgents smoke tests
test (3.11)	Run all tests	2026-05-23T12:21:11.7113051Z SKIPPED [1] tests/test_tradingagents_smoke.py:132: Set TRADINGAGENTS_LIVE_SMOKE=1 to run live TradingAgents smoke tests
test (3.11)	Run all tests	2026-05-23T12:21:11.7115244Z SKIPPED [1] tests/test_tradingagents_smoke.py:170: Set TRADINGAGENTS_LIVE_SMOKE=1 to run live TradingAgents smoke tests
test (3.11)	Run all tests	2026-05-23T12:21:11.7117645Z SKIPPED [1] tests/test_tradingagents_smoke.py:183: Set TRADINGAGENTS_LIVE_SMOKE=1 to run live TradingAgents smoke tests
test (3.11)	Run all tests	2026-05-23T12:21:11.7119785Z SKIPPED [1] tests/test_tv_place_pick_fillrelative.py:66: could not import 'websocket': No module named 'websocket'
test (3.11)	Run all tests	2026-05-23T12:21:11.7121593Z SKIPPED [1] tests/test_vt_csv_edge_luxalgo_alts.py:545: No signals generated with this data
test (3.11)	Run all tests	2026-05-23T12:21:11.7125101Z XFAIL tests/test_phantom_halt_mixed_units_regression.py::test_phantom_halt_with_mixed_pnl_units_under_triggers - P0-DATA scope: pnl_pct unit normalization at ingest required first. Round 3 panel 5/5 consensus, reports/round3_bugs_qa_synthesis_2026_04_29.md (P0 items #3 and #5).
test (3.11)	Run all tests	2026-05-23T12:21:11.7128813Z FAILED tests/test_hf_conviction_tier.py::test_tier_b_major - AssertionError: assert None == 'B'
test (3.11)	Run all tests	2026-05-23T12:21:11.7130475Z = 1 failed, 5839 passed, 56 skipped, 10 deselected, 1 xfailed, 6 warnings in 155.00s (0:02:35) =
test (3.11)	Run all tests	2026-05-23T12:21:12.7103361Z ##[error]Process completed with exit code 1.
```

**New deep-dives this check:** Daily Feed Summary, AI Tournament Pipeline — Daily Picks + DB Ingest, CI Tests

⏭️ **Skipping next check** — complicated failure(s); cooldown 15 min until 12:44 UTC.

## CHECK 2026-05-23 12:44:53 UTC
- **Stale failures** (latest run failed, no success since): **5**
- **In progress:** 6
- **Recent failures** (last 15 runs): 0

### ❌ ALPHA ENGINE - Adaptive Trust Tuner
- Run: [26332869663](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26332869663)
- Failed at: 2026-05-23T12:37:10Z
- **Classification:** UNKNOWN — needs manual log review
- **Log tail:**
```
trust-tuner	Run adaptive trust tuner	2026-05-23T12:38:31.8258664Z               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
trust-tuner	Run adaptive trust tuner	2026-05-23T12:38:31.8259396Z   File "/home/runner/work/findtorontoevents_antigravity.ca/findtorontoevents_antigravity.ca/alpha_engine/adaptive_trust_tuner.py", line 104, in _compute_rolling_metrics
trust-tuner	Run adaptive trust tuner	2026-05-23T12:38:31.8260113Z     "profit_factor_last20": _profit_factor(last20),
trust-tuner	Run adaptive trust tuner	2026-05-23T12:38:31.8260421Z                             ^^^^^^^^^^^^^^^^^^^^^^
trust-tuner	Run adaptive trust tuner	2026-05-23T12:38:31.8261127Z   File "/home/runner/work/findtorontoevents_antigravity.ca/findtorontoevents_antigravity.ca/alpha_engine/adaptive_trust_tuner.py", line 84, in _profit_factor
trust-tuner	Run adaptive trust tuner	2026-05-23T12:38:31.8261925Z     gross_wins = sum(abs(t.get("pnl_pct", 0)) for t in subset if t.get("status") == "WON")
trust-tuner	Run adaptive trust tuner	2026-05-23T12:38:31.8262357Z                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
trust-tuner	Run adaptive trust tuner	2026-05-23T12:38:31.8263220Z   File "/home/runner/work/findtorontoevents_antigravity.ca/findtorontoevents_antigravity.ca/alpha_engine/adaptive_trust_tuner.py", line 84, in <genexpr>
trust-tuner	Run adaptive trust tuner	2026-05-23T12:38:31.8263974Z     gross_wins = sum(abs(t.get("pnl_pct", 0)) for t in subset if t.get("status") == "WON")
trust-tuner	Run adaptive trust tuner	2026-05-23T12:38:31.8264344Z                      ^^^^^^^^^^^^^^^^^^^^^^^^
trust-tuner	Run adaptive trust tuner	2026-05-23T12:38:31.8264638Z TypeError: bad operand type for abs(): 'NoneType'
trust-tuner	Run adaptive trust tuner	2026-05-23T12:38:31.8445998Z ##[error]Process completed with exit code 1.
```

### ❌ DB Freshness Guardian
- Run: [26332723372](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26332723372)
- Failed at: 2026-05-23T12:30:35Z
- **Classification:** UNKNOWN — needs manual log review
- **Log tail:**
```
Check DB table freshness	Run DB freshness check	2026-05-23T12:32:05.9567682Z   DB_STOCKS_NAME: ejaguiar1_stocks
Check DB table freshness	Run DB freshness check	2026-05-23T12:32:05.9567904Z   DB_BACKTESTS_PASSWORD: ***
Check DB table freshness	Run DB freshness check	2026-05-23T12:32:05.9568104Z   DB_BACKTESTS_HOST: mysql.50webs.com
Check DB table freshness	Run DB freshness check	2026-05-23T12:32:05.9568318Z   DB_BACKTESTS_USER: ejaguiar1_backtests
Check DB table freshness	Run DB freshness check	2026-05-23T12:32:05.9568531Z   DB_BACKTESTS_NAME: ejaguiar1_backtests
Check DB table freshness	Run DB freshness check	2026-05-23T12:32:05.9568782Z   DB_FRESHNESS_OUTPUT: audit_dashboard/data/db_freshness.json
Check DB table freshness	Run DB freshness check	2026-05-23T12:32:05.9569028Z ##[endgroup]
Check DB table freshness	Run DB freshness check	2026-05-23T12:32:05.9641314Z === DB Freshness Guardian ===
Check DB table freshness	Run DB freshness check	2026-05-23T12:32:07.1178739Z WARNING backtests freshness: no created_at or imported_at in backtest_trades
Check DB table freshness	Run DB freshness check	2026-05-23T12:32:07.1182408Z INFO Freshness report written: /home/runner/work/findtorontoevents_antigravity.ca/findtorontoevents_antigravity.ca/audit_dashboard/data/db_freshness.json (overall=RED)
Check DB table freshness	Run DB freshness check	2026-05-23T12:32:07.1200500Z INFO Overall DB freshness: RED
Check DB table freshness	Run DB freshness check	2026-05-23T12:32:07.1291014Z ##[error]Process completed with exit code 2.
```

### (cached) Daily Feed Summary — run `26332573320`

### (cached) AI Tournament Pipeline — Daily Picks + DB Ingest — run `26332442616`

### (cached) CI Tests — run `26332369798`

**New deep-dives this check:** ALPHA ENGINE - Adaptive Trust Tuner, DB Freshness Guardian

⏭️ **Skipping next check** — complicated failure(s); cooldown 15 min until 12:59 UTC.

## CHECK 2026-05-23 13:00:00 UTC
- **Stale failures** (latest run failed, no success since): **6**
- **In progress:** 3
- **Recent failures** (last 15 runs): 0

### (cached) ALPHA ENGINE - Adaptive Trust Tuner — run `26332869663`

### (cached) DB Freshness Guardian — run `26332723372`

### (cached) Daily Feed Summary — run `26332573320`

### (cached) AI Tournament Pipeline — Daily Picks + DB Ingest — run `26332442616`

### ❌ DNA Genome Daily Pipeline
- Run: [26332383420](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26332383420)
- Failed at: 2026-05-23T12:14:55Z
- **Classification:** UNKNOWN — needs manual log review
- **Log tail:**
```
deploy-to-ftp	Deploy to findtorontoevents.ca	2026-05-23T12:46:55.3377344Z ----------------------------------------------------------------
deploy-to-ftp	Deploy to findtorontoevents.ca	2026-05-23T12:46:55.3377902Z ----------------------  full error below  ----------------------
deploy-to-ftp	Deploy to findtorontoevents.ca	2026-05-23T12:46:55.3378457Z ----------------------------------------------------------------
deploy-to-ftp	Deploy to findtorontoevents.ca	2026-05-23T12:46:55.3378820Z 
deploy-to-ftp	Deploy to findtorontoevents.ca	2026-05-23T12:46:55.3392688Z Error: Timeout (control socket)
deploy-to-ftp	Deploy to findtorontoevents.ca	2026-05-23T12:46:55.3393588Z     at Socket.<anonymous> (/home/runner/work/_actions/SamKirkland/FTP-Deploy-Action/4.3.0/dist/index.js:4808:58)
deploy-to-ftp	Deploy to findtorontoevents.ca	2026-05-23T12:46:55.3394760Z     at Object.onceWrapper (node:events:638:28)
deploy-to-ftp	Deploy to findtorontoevents.ca	2026-05-23T12:46:55.3395255Z     at Socket.emit (node:events:524:28)
deploy-to-ftp	Deploy to findtorontoevents.ca	2026-05-23T12:46:55.3395720Z     at Socket._onTimeout (node:net:595:8)
deploy-to-ftp	Deploy to findtorontoevents.ca	2026-05-23T12:46:55.3396206Z     at listOnTimeout (node:internal/timers:581:17)
deploy-to-ftp	Deploy to findtorontoevents.ca	2026-05-23T12:46:55.3396761Z     at process.processTimers (node:internal/timers:519:7)
deploy-to-ftp	Deploy to findtorontoevents.ca	2026-05-23T12:46:55.3421352Z ##[error]Error: Timeout (control socket)
```

### (cached) CI Tests — run `26332369798`

**New deep-dives this check:** DNA Genome Daily Pipeline

⏭️ **Skipping next check** — complicated failure(s); cooldown 15 min until 13:14 UTC.

## CHECK 2026-05-23 13:15:11 UTC
- **Stale failures** (latest run failed, no success since): **6**
- **In progress:** 3
- **Recent failures** (last 15 runs): 0

### (cached) ALPHA ENGINE - Adaptive Trust Tuner — run `26332869663`

### (cached) DB Freshness Guardian — run `26332723372`

### (cached) Daily Feed Summary — run `26332573320`

### (cached) AI Tournament Pipeline — Daily Picks + DB Ingest — run `26332442616`

### (cached) DNA Genome Daily Pipeline — run `26332383420`

### (cached) CI Tests — run `26332369798`

## CHECK 2026-05-23 13:30:16 UTC
- **Stale failures** (latest run failed, no success since): **4**
- **In progress:** 5
- **Recent failures** (last 15 runs): 0

### ❌ CI Tests
- Run: [26333779269](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26333779269)
- Failed at: 2026-05-23T13:19:55Z
- **Classification:** UNKNOWN — needs manual log review
- **Log tail:**
```
test (3.11)	Run all tests	2026-05-23T13:24:43.5705761Z SKIPPED [1] tests/test_vt_csv_edge_luxalgo_alts.py:545: No signals generated with this data
test (3.11)	Run all tests	2026-05-23T13:24:43.5707154Z XFAIL tests/test_phantom_halt_mixed_units_regression.py::test_phantom_halt_with_mixed_pnl_units_under_triggers - P0-DATA scope: pnl_pct unit normalization at ingest required first. Round 3 panel 5/5 consensus, reports/round3_bugs_qa_synthesis_2026_04_29.md (P0 items #3 and #5).
test (3.11)	Run all tests	2026-05-23T13:24:43.5708398Z FAILED tests/test_hf_conviction_tier.py::test_tier_b_major - AssertionError: assert None == 'B'
test (3.11)	Run all tests	2026-05-23T13:24:43.5709450Z FAILED tests/test_regime_gate.py::TestRegimeGate::test_exempt_contrarian_passes_volatile_regime - AssertionError: 0 != 1
test (3.11)	Run all tests	2026-05-23T13:24:43.5710245Z FAILED tests/test_regime_gate.py::TestRegimeGate::test_pick_without_macro_regime_passes_short - AssertionError: 0 != 1
test (3.11)	Run all tests	2026-05-23T13:24:43.5711043Z FAILED tests/test_regime_gate.py::TestRegimeGate::test_proven_exempt_contrarian_passes_volatile_regime - AssertionError: 0 != 1
test (3.11)	Run all tests	2026-05-23T13:24:43.5711839Z FAILED tests/test_regime_gate.py::TestRegimeGate::test_short_aligned_bearish_regime_passes - AssertionError: 0 != 1
test (3.11)	Run all tests	2026-05-23T13:24:43.5712642Z FAILED tests/test_regime_gate.py::TestRegimeGate::test_short_aligned_bullish_high_short_conf_passes - AssertionError: 0 != 1
test (3.11)	Run all tests	2026-05-23T13:24:43.5713411Z FAILED tests/test_regime_gate.py::TestRegimeGate::test_short_choppy_neutral_regime_passes - AssertionError: 0 != 1
test (3.11)	Run all tests	2026-05-23T13:24:43.5714160Z FAILED tests/test_regime_gate.py::TestRegimeGate::test_short_exempt_in_bullish_regime_passes - AssertionError: 0 != 1
test (3.11)	Run all tests	2026-05-23T13:24:43.5714818Z = 8 failed, 5832 passed, 56 skipped, 10 deselected, 1 xfailed, 6 warnings in 156.97s (0:02:36) =
test (3.11)	Run all tests	2026-05-23T13:24:44.6219585Z ##[error]Process completed with exit code 1.
```

### (cached) ALPHA ENGINE - Adaptive Trust Tuner — run `26332869663`

### (cached) Daily Feed Summary — run `26332573320`

### (cached) AI Tournament Pipeline — Daily Picks + DB Ingest — run `26332442616`

**New deep-dives this check:** CI Tests

⏭️ **Skipping next check** — complicated failure(s); cooldown 15 min until 13:45 UTC.

## CHECK 2026-05-23 13:45:22 UTC
- **Stale failures** (latest run failed, no success since): **3**
- **In progress:** 2
- **Recent failures** (last 15 runs): 0

### (cached) CI Tests — run `26333779269`

### (cached) ALPHA ENGINE - Adaptive Trust Tuner — run `26332869663`

### (cached) Daily Feed Summary — run `26332573320`

## CHECK 2026-05-23 14:00:27 UTC
- **Stale failures** (latest run failed, no success since): **2**
- **In progress:** 7
- **Recent failures** (last 15 runs): 0

### (cached) CI Tests — run `26333779269`

### (cached) ALPHA ENGINE - Adaptive Trust Tuner — run `26332869663`

## CHECK 2026-05-23 14:15:32 UTC
- **Stale failures** (latest run failed, no success since): **3**
- **In progress:** 2
- **Recent failures** (last 15 runs): 1

### ❌ Asset Class Freshness Watchdog
- Run: [26334794903](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26334794903)
- Failed at: 2026-05-23T14:06:45Z
- **Classification:** UNKNOWN — needs manual log review
- **Log tail:**
```
freshness	Generate freshness report (warn-only)	2026-05-23T14:07:58.9622281Z              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
freshness	Generate freshness report (warn-only)	2026-05-23T14:07:58.9623067Z   File "/home/runner/work/findtorontoevents_antigravity.ca/findtorontoevents_antigravity.ca/tools/generate_asset_class_freshness_report.py", line 126, in build_report
freshness	Generate freshness report (warn-only)	2026-05-23T14:07:58.9624108Z     payload = json.loads(input_path.read_text(encoding="utf-8"))
freshness	Generate freshness report (warn-only)	2026-05-23T14:07:58.9624471Z                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
freshness	Generate freshness report (warn-only)	2026-05-23T14:07:58.9624970Z   File "/opt/hostedtoolcache/Python/3.11.15/x64/lib/python3.11/pathlib.py", line 1058, in read_text
freshness	Generate freshness report (warn-only)	2026-05-23T14:07:58.9779888Z     with self.open(mode='r', encoding=encoding, errors=errors) as f:
freshness	Generate freshness report (warn-only)	2026-05-23T14:07:58.9780622Z          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
freshness	Generate freshness report (warn-only)	2026-05-23T14:07:58.9781538Z   File "/opt/hostedtoolcache/Python/3.11.15/x64/lib/python3.11/pathlib.py", line 1044, in open
freshness	Generate freshness report (warn-only)	2026-05-23T14:07:58.9782528Z     return io.open(self, mode, buffering, encoding, errors, newline)
freshness	Generate freshness report (warn-only)	2026-05-23T14:07:58.9783158Z            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
freshness	Generate freshness report (warn-only)	2026-05-23T14:07:58.9783931Z FileNotFoundError: [Errno 2] No such file or directory: 'audit_dashboard/data/dashboard_data.json'
freshness	Generate freshness report (warn-only)	2026-05-23T14:07:58.9850592Z ##[error]Process completed with exit code 1.
```

### (cached) CI Tests — run `26333779269`

### (cached) ALPHA ENGINE - Adaptive Trust Tuner — run `26332869663`

**New deep-dives this check:** Asset Class Freshness Watchdog

⏭️ **Skipping next check** — complicated failure(s); cooldown 15 min until 14:30 UTC.

## CHECK 2026-05-23 14:30:38 UTC
- **Stale failures** (latest run failed, no success since): **2**
- **In progress:** 11
- **Recent failures** (last 15 runs): 1

### ❌ Send Morning Goal Follow-Ups
- Run: [26335249487](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26335249487)
- Failed at: 2026-05-23T14:28:39Z
- **Classification:** UNKNOWN — needs manual log review
- **Log tail:**
```
send-followups	Send Morning Goal Follow-Up DMs	2026-05-23T14:28:43.1685216Z [36;1m        print(f\"Error: {e}\")[0m
send-followups	Send Morning Goal Follow-Up DMs	2026-05-23T14:28:43.1685724Z [36;1m"[0m
send-followups	Send Morning Goal Follow-Up DMs	2026-05-23T14:28:43.1719643Z shell: /usr/bin/bash -e {0}
send-followups	Send Morning Goal Follow-Up DMs	2026-05-23T14:28:43.1720138Z env:
send-followups	Send Morning Goal Follow-Up DMs	2026-05-23T14:28:43.1720529Z   EVENT_NOTIFY_API_KEY: 
send-followups	Send Morning Goal Follow-Up DMs	2026-05-23T14:28:43.1720981Z ##[endgroup]
send-followups	Send Morning Goal Follow-Up DMs	2026-05-23T14:28:43.1779201Z Sending morning goal follow-ups...
send-followups	Send Morning Goal Follow-Up DMs	2026-05-23T14:28:43.5893727Z POST blocked by ModSecurity (HTTP 403), retrying as GET...
send-followups	Send Morning Goal Follow-Up DMs	2026-05-23T14:28:43.7729117Z HTTP Status: 403
send-followups	Send Morning Goal Follow-Up DMs	2026-05-23T14:28:43.7730604Z Response: {"success":false,"error":"Unauthorized"}
send-followups	Send Morning Goal Follow-Up DMs	2026-05-23T14:28:43.7762339Z ##[error]Failed to send follow-ups (HTTP 403)
send-followups	Send Morning Goal Follow-Up DMs	2026-05-23T14:28:43.7772352Z ##[error]Process completed with exit code 1.
```

### (cached) Asset Class Freshness Watchdog — run `26334794903`

**New deep-dives this check:** Send Morning Goal Follow-Ups

⏭️ **Skipping next check** — complicated failure(s); cooldown 15 min until 14:45 UTC.

## CHECK 2026-05-23 14:45:44 UTC
- **Stale failures** (latest run failed, no success since): **4**
- **In progress:** 14
- **Recent failures** (last 15 runs): 0

### ❌ Sports Prediction Market Sync
- Run: [26335453145](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26335453145)
- Failed at: 2026-05-23T14:37:45Z
- **Classification:** UNKNOWN — needs manual log review
- **Log tail:**
```
sync	Commit updated signals	2026-05-23T14:39:09.3913658Z Error: Invalid status code: 128
sync	Commit updated signals	2026-05-23T14:39:09.3914481Z     at ChildProcess.<anonymous> (/home/runner/work/_actions/stefanzweifel/git-auto-commit-action/v5/index.js:17:19)
sync	Commit updated signals	2026-05-23T14:39:09.3915340Z     at ChildProcess.emit (node:events:524:28)
sync	Commit updated signals	2026-05-23T14:39:09.3915834Z     at maybeClose (node:internal/child_process:1104:16)
sync	Commit updated signals	2026-05-23T14:39:09.3916446Z     at ChildProcess._handle.onexit (node:internal/child_process:304:5) {
sync	Commit updated signals	2026-05-23T14:39:09.3917427Z   code: 128
sync	Commit updated signals	2026-05-23T14:39:09.3917613Z }
sync	Commit updated signals	2026-05-23T14:39:09.3917784Z Error: Invalid status code: 128
sync	Commit updated signals	2026-05-23T14:39:09.3918585Z     at ChildProcess.<anonymous> (/home/runner/work/_actions/stefanzweifel/git-auto-commit-action/v5/index.js:17:19)
sync	Commit updated signals	2026-05-23T14:39:09.3919335Z     at ChildProcess.emit (node:events:524:28)
sync	Commit updated signals	2026-05-23T14:39:09.3919760Z     at maybeClose (node:internal/child_process:1104:16)
sync	Commit updated signals	2026-05-23T14:39:09.3920299Z     at ChildProcess._handle.onexit (node:internal/child_process:304:5)
```

### ❌ CI Tests
- Run: [26335272654](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26335272654)
- Failed at: 2026-05-23T14:29:46Z
- **Classification:** UNKNOWN — needs manual log review
- **Log tail:**
```
test (3.11)	Run all tests	2026-05-23T14:34:21.8191219Z SKIPPED [1] tests/test_vt_csv_edge_luxalgo_alts.py:545: No signals generated with this data
test (3.11)	Run all tests	2026-05-23T14:34:21.8192413Z XFAIL tests/test_phantom_halt_mixed_units_regression.py::test_phantom_halt_with_mixed_pnl_units_under_triggers - P0-DATA scope: pnl_pct unit normalization at ingest required first. Round 3 panel 5/5 consensus, reports/round3_bugs_qa_synthesis_2026_04_29.md (P0 items #3 and #5).
test (3.11)	Run all tests	2026-05-23T14:34:21.8193577Z FAILED tests/test_hf_conviction_tier.py::test_tier_b_major - AssertionError: assert None == 'B'
test (3.11)	Run all tests	2026-05-23T14:34:21.8194270Z FAILED tests/test_regime_gate.py::TestRegimeGate::test_exempt_contrarian_passes_volatile_regime - AssertionError: 0 != 1
test (3.11)	Run all tests	2026-05-23T14:34:21.8195020Z FAILED tests/test_regime_gate.py::TestRegimeGate::test_pick_without_macro_regime_passes_short - AssertionError: 0 != 1
test (3.11)	Run all tests	2026-05-23T14:34:21.8195785Z FAILED tests/test_regime_gate.py::TestRegimeGate::test_proven_exempt_contrarian_passes_volatile_regime - AssertionError: 0 != 1
test (3.11)	Run all tests	2026-05-23T14:34:21.8196752Z FAILED tests/test_regime_gate.py::TestRegimeGate::test_short_aligned_bearish_regime_passes - AssertionError: 0 != 1
test (3.11)	Run all tests	2026-05-23T14:34:21.8197505Z FAILED tests/test_regime_gate.py::TestRegimeGate::test_short_aligned_bullish_high_short_conf_passes - AssertionError: 0 != 1
test (3.11)	Run all tests	2026-05-23T14:34:21.8198264Z FAILED tests/test_regime_gate.py::TestRegimeGate::test_short_choppy_neutral_regime_passes - AssertionError: 0 != 1
test (3.11)	Run all tests	2026-05-23T14:34:21.8198978Z FAILED tests/test_regime_gate.py::TestRegimeGate::test_short_exempt_in_bullish_regime_passes - AssertionError: 0 != 1
test (3.11)	Run all tests	2026-05-23T14:34:21.8199622Z = 8 failed, 5832 passed, 56 skipped, 10 deselected, 1 xfailed, 6 warnings in 151.30s (0:02:31) =
test (3.11)	Run all tests	2026-05-23T14:34:23.1415165Z ##[error]Process completed with exit code 1.
```

### (cached) Send Morning Goal Follow-Ups — run `26335249487`

### (cached) Asset Class Freshness Watchdog — run `26334794903`

**New deep-dives this check:** Sports Prediction Market Sync, CI Tests

⏭️ **Skipping next check** — complicated failure(s); cooldown 15 min until 15:00 UTC.

## CHECK 2026-05-23 15:00:51 UTC
- **Stale failures** (latest run failed, no success since): **4**
- **In progress:** 3
- **Recent failures** (last 15 runs): 0

### (cached) Sports Prediction Market Sync — run `26335453145`

### (cached) CI Tests — run `26335272654`

### (cached) Send Morning Goal Follow-Ups — run `26335249487`

### (cached) Asset Class Freshness Watchdog — run `26334794903`

## CHECK 2026-05-23 15:15:55 UTC
- **Stale failures** (latest run failed, no success since): **4**
- **In progress:** 3
- **Recent failures** (last 15 runs): 0

### (cached) Sports Prediction Market Sync — run `26335453145`

### (cached) CI Tests — run `26335272654`

### (cached) Send Morning Goal Follow-Ups — run `26335249487`

### (cached) Asset Class Freshness Watchdog — run `26334794903`

## CHECK 2026-05-23 15:31:00 UTC
- **Stale failures** (latest run failed, no success since): **3**
- **In progress:** 6
- **Recent failures** (last 15 runs): 0

### (cached) Sports Prediction Market Sync — run `26335453145`

### (cached) Send Morning Goal Follow-Ups — run `26335249487`

### (cached) Asset Class Freshness Watchdog — run `26334794903`

## CHECK 2026-05-23 15:46:06 UTC
- **Stale failures** (latest run failed, no success since): **1**
- **In progress:** 7
- **Recent failures** (last 15 runs): 0

### (cached) Sports Prediction Market Sync — run `26335453145`

## CHECK 2026-05-23 16:01:11 UTC
- **Stale failures** (latest run failed, no success since): **2**
- **In progress:** 1
- **Recent failures** (last 15 runs): 0

### ❌ Deploy Competition to Live Site
- Run: [26336951127](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26336951127)
- Failed at: 2026-05-23T15:46:34Z
- **Classification:** UNKNOWN — needs manual log review
- **Log tail:**
```
deploy	Deploy competition files to live site via FTP	2026-05-23T15:47:48.0659003Z [36;1melse[0m
deploy	Deploy competition files to live site via FTP	2026-05-23T15:47:48.0659338Z [36;1m  echo "::warning::FTP upload to findtorontoevents.ca failed"[0m
deploy	Deploy competition files to live site via FTP	2026-05-23T15:47:48.0659858Z [36;1mfi[0m
deploy	Deploy competition files to live site via FTP	2026-05-23T15:47:48.0700256Z shell: /usr/bin/bash -e {0}
deploy	Deploy competition files to live site via FTP	2026-05-23T15:47:48.0700556Z env:
deploy	Deploy competition files to live site via FTP	2026-05-23T15:47:48.0701078Z   FTP_SERVER: ***
deploy	Deploy competition files to live site via FTP	2026-05-23T15:47:48.0701347Z   FTP_USER: ***
deploy	Deploy competition files to live site via FTP	2026-05-23T15:47:48.0701609Z   FTP_PASS: ***
deploy	Deploy competition files to live site via FTP	2026-05-23T15:47:48.0701839Z ##[endgroup]
deploy	Deploy competition files to live site via FTP	2026-05-23T15:47:48.0779724Z === Deploying Algorithm Competition Arena to findtorontoevents.ca ===
deploy	Deploy competition files to live site via FTP	2026-05-23T15:57:42.1809244Z cd: Fatal error: max-retries exceeded (Connection timed out)
deploy	Deploy competition files to live site via FTP	2026-05-23T15:57:42.1838947Z ##[error]Process completed with exit code 1.
```

### (cached) Sports Prediction Market Sync — run `26335453145`

**New deep-dives this check:** Deploy Competition to Live Site

⏭️ **Skipping next check** — complicated failure(s); cooldown 15 min until 16:16 UTC.

## CHECK 2026-05-23 16:16:17 UTC
- **Stale failures** (latest run failed, no success since): **0**
- **In progress:** 4
- **Recent failures** (last 15 runs): 0

✅ **All clear** — no stale failures detected.

## CHECK 2026-05-23 16:31:21 UTC
- **Stale failures** (latest run failed, no success since): **0**
- **In progress:** 9
- **Recent failures** (last 15 runs): 0

✅ **All clear** — no stale failures detected.

## CHECK 2026-05-23 16:46:26 UTC
- **Stale failures** (latest run failed, no success since): **1**
- **In progress:** 7
- **Recent failures** (last 15 runs): 0

### ❌ Low-Score Winner Tracker
- Run: [26337831666](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26337831666)
- Failed at: 2026-05-23T16:29:21Z
- **Classification:** UNKNOWN — needs manual log review
- **Log tail:**
```
track	Run low-score tracker	2026-05-23T16:33:03.4380893Z shell: /usr/bin/bash -e {0}
track	Run low-score tracker	2026-05-23T16:33:03.4381143Z env:
track	Run low-score tracker	2026-05-23T16:33:03.4381415Z   pythonLocation: /opt/hostedtoolcache/Python/3.11.15/x64
track	Run low-score tracker	2026-05-23T16:33:03.4381868Z   PKG_CONFIG_PATH: /opt/hostedtoolcache/Python/3.11.15/x64/lib/pkgconfig
track	Run low-score tracker	2026-05-23T16:33:03.4382303Z   Python_ROOT_DIR: /opt/hostedtoolcache/Python/3.11.15/x64
track	Run low-score tracker	2026-05-23T16:33:03.4382688Z   Python2_ROOT_DIR: /opt/hostedtoolcache/Python/3.11.15/x64
track	Run low-score tracker	2026-05-23T16:33:03.4383090Z   Python3_ROOT_DIR: /opt/hostedtoolcache/Python/3.11.15/x64
track	Run low-score tracker	2026-05-23T16:33:03.4383484Z   LD_LIBRARY_PATH: /opt/hostedtoolcache/Python/3.11.15/x64/lib
track	Run low-score tracker	2026-05-23T16:33:03.4383808Z ##[endgroup]
track	Run low-score tracker	2026-05-23T16:33:03.4884934Z 2026-05-23T16:33:03 [ERROR] Dashboard payload not found: /home/runner/work/findtorontoevents_antigravity.ca/findtorontoevents_antigravity.ca/audit_trail/data/dashboard_payload.json
track	Run low-score tracker	2026-05-23T16:33:03.4886358Z ERROR: payload_not_found
track	Run low-score tracker	2026-05-23T16:33:03.4959966Z ##[error]Process completed with exit code 1.
```

**New deep-dives this check:** Low-Score Winner Tracker

⏭️ **Skipping next check** — complicated failure(s); cooldown 15 min until 17:01 UTC.

## CHECK 2026-05-23 17:01:33 UTC
- **Stale failures** (latest run failed, no success since): **1**
- **In progress:** 3
- **Recent failures** (last 15 runs): 0

### (cached) Low-Score Winner Tracker — run `26337831666`

## CHECK 2026-05-23 17:16:37 UTC
- **Stale failures** (latest run failed, no success since): **1**
- **In progress:** 6
- **Recent failures** (last 15 runs): 0

### (cached) Low-Score Winner Tracker — run `26337831666`

## CHECK 2026-05-23 17:31:42 UTC
- **Stale failures** (latest run failed, no success since): **1**
- **In progress:** 7
- **Recent failures** (last 15 runs): 0

### ❌ CI Tests
- Run: [26338728437](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26338728437)
- Failed at: 2026-05-23T17:13:05Z
- **Classification:** UNKNOWN — needs manual log review
- **Log tail:**
```
test (3.11)	Run all tests	2026-05-23T17:17:52.5346135Z SKIPPED [1] tests/test_tv_place_pick_fillrelative.py:66: could not import 'websocket': No module named 'websocket'
test (3.11)	Run all tests	2026-05-23T17:17:52.5347018Z SKIPPED [1] tests/test_vt_csv_edge_luxalgo_alts.py:545: No signals generated with this data
test (3.11)	Run all tests	2026-05-23T17:17:52.5348228Z XFAIL tests/test_phantom_halt_mixed_units_regression.py::test_phantom_halt_with_mixed_pnl_units_under_triggers - P0-DATA scope: pnl_pct unit normalization at ingest required first. Round 3 panel 5/5 consensus, reports/round3_bugs_qa_synthesis_2026_04_29.md (P0 items #3 and #5).
test (3.11)	Run all tests	2026-05-23T17:17:52.5349505Z FAILED tests/test_regime_gate.py::TestRegimeGate::test_exempt_contrarian_passes_volatile_regime - AssertionError: 0 != 1
test (3.11)	Run all tests	2026-05-23T17:17:52.5350257Z FAILED tests/test_regime_gate.py::TestRegimeGate::test_pick_without_macro_regime_passes_short - AssertionError: 0 != 1
test (3.11)	Run all tests	2026-05-23T17:17:52.5351087Z FAILED tests/test_regime_gate.py::TestRegimeGate::test_proven_exempt_contrarian_passes_volatile_regime - AssertionError: 0 != 1
test (3.11)	Run all tests	2026-05-23T17:17:52.5351870Z FAILED tests/test_regime_gate.py::TestRegimeGate::test_short_aligned_bearish_regime_passes - AssertionError: 0 != 1
test (3.11)	Run all tests	2026-05-23T17:17:52.5352790Z FAILED tests/test_regime_gate.py::TestRegimeGate::test_short_aligned_bullish_high_short_conf_passes - AssertionError: 0 != 1
test (3.11)	Run all tests	2026-05-23T17:17:52.5353545Z FAILED tests/test_regime_gate.py::TestRegimeGate::test_short_choppy_neutral_regime_passes - AssertionError: 0 != 1
test (3.11)	Run all tests	2026-05-23T17:17:52.5354272Z FAILED tests/test_regime_gate.py::TestRegimeGate::test_short_exempt_in_bullish_regime_passes - AssertionError: 0 != 1
test (3.11)	Run all tests	2026-05-23T17:17:52.5354922Z = 7 failed, 5833 passed, 56 skipped, 10 deselected, 1 xfailed, 6 warnings in 159.84s (0:02:39) =
test (3.11)	Run all tests	2026-05-23T17:17:53.6666788Z ##[error]Process completed with exit code 1.
```

**New deep-dives this check:** CI Tests

⏭️ **Skipping next check** — complicated failure(s); cooldown 15 min until 17:46 UTC.

## CHECK 2026-05-23 17:46:48 UTC
- **Stale failures** (latest run failed, no success since): **1**
- **In progress:** 5
- **Recent failures** (last 15 runs): 0

### (cached) CI Tests — run `26338728437`

## CHECK 2026-05-23 18:01:52 UTC
- **Stale failures** (latest run failed, no success since): **1**
- **In progress:** 3
- **Recent failures** (last 15 runs): 0

### (cached) CI Tests — run `26338728437`

## CHECK 2026-05-23 18:16:57 UTC
- **Stale failures** (latest run failed, no success since): **1**
- **In progress:** 14
- **Recent failures** (last 15 runs): 1

### ❌ CI Tests
- Run: [26340018574](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26340018574)
- Failed at: 2026-05-23T18:15:44Z
- **Classification:** FLAKY — git push/rebase race during auto-commit
- **Log tail:**
```
test (3.12)	Checkout	2026-05-23T18:15:48.9988635Z ##[group]Fetching the repository
test (3.12)	Checkout	2026-05-23T18:15:48.9995249Z [command]/usr/bin/git -c protocol.version=2 fetch --no-tags --prune --no-recurse-submodules --depth=1 origin +8a4dd1015b1347e18d7daa563c75dd0d2e7bcdc2:refs/remotes/origin/main
test (3.12)	Checkout	2026-05-23T18:15:49.1731968Z ##[error]fatal: could not read Username for 'https://github.com': terminal prompts disabled
test (3.12)	Checkout	2026-05-23T18:15:49.1740010Z The process '/usr/bin/git' failed with exit code 128
test (3.12)	Checkout	2026-05-23T18:15:49.1740964Z Waiting 10 seconds before trying again
test (3.12)	Checkout	2026-05-23T18:15:59.1731536Z [command]/usr/bin/git -c protocol.version=2 fetch --no-tags --prune --no-recurse-submodules --depth=1 origin +8a4dd1015b1347e18d7daa563c75dd0d2e7bcdc2:refs/remotes/origin/main
test (3.12)	Checkout	2026-05-23T18:15:59.3580335Z ##[error]fatal: could not read Username for 'https://github.com': terminal prompts disabled
test (3.12)	Checkout	2026-05-23T18:15:59.3596614Z The process '/usr/bin/git' failed with exit code 128
test (3.12)	Checkout	2026-05-23T18:15:59.3597200Z Waiting 13 seconds before trying again
test (3.12)	Checkout	2026-05-23T18:16:12.3598180Z [command]/usr/bin/git -c protocol.version=2 fetch --no-tags --prune --no-recurse-submodules --depth=1 origin +8a4dd1015b1347e18d7daa563c75dd0d2e7bcdc2:refs/remotes/origin/main
test (3.12)	Checkout	2026-05-23T18:16:12.5344477Z ##[error]fatal: could not read Username for 'https://github.com': terminal prompts disabled
test (3.12)	Checkout	2026-05-23T18:16:12.5382907Z ##[error]The process '/usr/bin/git' failed with exit code 128
```

**New deep-dives this check:** CI Tests

⏭️ **Skipping next check** — complicated failure(s); cooldown 15 min until 18:31 UTC.

## CHECK 2026-05-23 18:32:04 UTC
- **Stale failures** (latest run failed, no success since): **3**
- **In progress:** 13
- **Recent failures** (last 15 runs): 0

### ❌ DB Freshness Guardian
- Run: [26340280066](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26340280066)
- Failed at: 2026-05-23T18:28:36Z
- **Classification:** UNKNOWN — needs manual log review
- **Log tail:**
```
Check DB table freshness	Run DB freshness check	2026-05-23T18:29:58.5144522Z   DB_STOCKS_NAME: ejaguiar1_stocks
Check DB table freshness	Run DB freshness check	2026-05-23T18:29:58.5144814Z   DB_BACKTESTS_PASSWORD: ***
Check DB table freshness	Run DB freshness check	2026-05-23T18:29:58.5145083Z   DB_BACKTESTS_HOST: mysql.50webs.com
Check DB table freshness	Run DB freshness check	2026-05-23T18:29:58.5145579Z   DB_BACKTESTS_USER: ejaguiar1_backtests
Check DB table freshness	Run DB freshness check	2026-05-23T18:29:58.5145881Z   DB_BACKTESTS_NAME: ejaguiar1_backtests
Check DB table freshness	Run DB freshness check	2026-05-23T18:29:58.5146222Z   DB_FRESHNESS_OUTPUT: audit_dashboard/data/db_freshness.json
Check DB table freshness	Run DB freshness check	2026-05-23T18:29:58.5146563Z ##[endgroup]
Check DB table freshness	Run DB freshness check	2026-05-23T18:29:58.5203330Z === DB Freshness Guardian ===
Check DB table freshness	Run DB freshness check	2026-05-23T18:29:59.4061490Z WARNING backtests freshness: no created_at or imported_at in backtest_trades
Check DB table freshness	Run DB freshness check	2026-05-23T18:29:59.4066173Z INFO Freshness report written: /home/runner/work/findtorontoevents_antigravity.ca/findtorontoevents_antigravity.ca/audit_dashboard/data/db_freshness.json (overall=RED)
Check DB table freshness	Run DB freshness check	2026-05-23T18:29:59.4085442Z INFO Overall DB freshness: RED
Check DB table freshness	Run DB freshness check	2026-05-23T18:29:59.4194014Z ##[error]Process completed with exit code 2.
```

### ❌ actions-failure-guardian
- Run: [26340174401](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26340174401)
- Failed at: 2026-05-23T18:23:26Z
- **Classification:** UNKNOWN — needs manual log review
- **Log tail:**
```
monitor-and-retry	Run failure guardian script	2026-05-23T18:24:52.8595586Z              ^^^^^^
monitor-and-retry	Run failure guardian script	2026-05-23T18:24:52.8596365Z   File "/home/runner/work/findtorontoevents_antigravity.ca/findtorontoevents_antigravity.ca/scripts/actions_failure_guardian.py", line 506, in main
monitor-and-retry	Run failure guardian script	2026-05-23T18:24:52.8597264Z     runs = load_runs(repo, token, pages=pages, per_page=per_page)
monitor-and-retry	Run failure guardian script	2026-05-23T18:24:52.8597693Z            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
monitor-and-retry	Run failure guardian script	2026-05-23T18:24:52.8598527Z   File "/home/runner/work/findtorontoevents_antigravity.ca/findtorontoevents_antigravity.ca/scripts/actions_failure_guardian.py", line 57, in load_runs
monitor-and-retry	Run failure guardian script	2026-05-23T18:24:52.8599593Z     raise RuntimeError(f"Failed to fetch runs page {page}: {resp.status_code} {resp.text[:300]}")
monitor-and-retry	Run failure guardian script	2026-05-23T18:24:52.8600159Z RuntimeError: Failed to fetch runs page 2: 401 {
monitor-and-retry	Run failure guardian script	2026-05-23T18:24:52.8600512Z   "message": "Bad credentials",
monitor-and-retry	Run failure guardian script	2026-05-23T18:24:52.8600847Z   "documentation_url": "https://docs.github.com/rest",
monitor-and-retry	Run failure guardian script	2026-05-23T18:24:52.8601196Z   "status": "401"
monitor-and-retry	Run failure guardian script	2026-05-23T18:24:52.8601405Z }
monitor-and-retry	Run failure guardian script	2026-05-23T18:24:52.8794374Z ##[error]Process completed with exit code 1.
```

### (cached) CI Tests — run `26340018574`

**New deep-dives this check:** DB Freshness Guardian, actions-failure-guardian

⏭️ **Skipping next check** — complicated failure(s); cooldown 15 min until 18:46 UTC.

## CHECK 2026-05-23 18:47:10 UTC
- **Stale failures** (latest run failed, no success since): **3**
- **In progress:** 8
- **Recent failures** (last 15 runs): 0

### (cached) DB Freshness Guardian — run `26340280066`

### (cached) actions-failure-guardian — run `26340174401`

### (cached) CI Tests — run `26340018574`

## CHECK 2026-05-23 19:02:15 UTC
- **Stale failures** (latest run failed, no success since): **2**
- **In progress:** 4
- **Recent failures** (last 15 runs): 0

### (cached) DB Freshness Guardian — run `26340280066`

### (cached) CI Tests — run `26340018574`

## CHECK 2026-05-23 19:17:20 UTC
- **Stale failures** (latest run failed, no success since): **1**
- **In progress:** 10
- **Recent failures** (last 15 runs): 0

### (cached) DB Freshness Guardian — run `26340280066`

## CHECK 2026-05-23 19:32:26 UTC
- **Stale failures** (latest run failed, no success since): **1**
- **In progress:** 6
- **Recent failures** (last 15 runs): 0

### ❌ CI Tests
- Run: [26341266716](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26341266716)
- Failed at: 2026-05-23T19:16:12Z
- **Classification:** UNKNOWN — needs manual log review
- **Log tail:**
```
test (3.11)	Run all tests	2026-05-23T19:21:31.5799007Z SKIPPED [1] tests/test_tv_place_pick_fillrelative.py:66: could not import 'websocket': No module named 'websocket'
test (3.11)	Run all tests	2026-05-23T19:21:31.5799595Z SKIPPED [1] tests/test_vt_csv_edge_luxalgo_alts.py:545: No signals generated with this data
test (3.11)	Run all tests	2026-05-23T19:21:31.5800716Z XFAIL tests/test_phantom_halt_mixed_units_regression.py::test_phantom_halt_with_mixed_pnl_units_under_triggers - P0-DATA scope: pnl_pct unit normalization at ingest required first. Round 3 panel 5/5 consensus, reports/round3_bugs_qa_synthesis_2026_04_29.md (P0 items #3 and #5).
test (3.11)	Run all tests	2026-05-23T19:21:31.5801895Z FAILED tests/test_regime_gate.py::TestRegimeGate::test_exempt_contrarian_passes_volatile_regime - AssertionError: 0 != 1
test (3.11)	Run all tests	2026-05-23T19:21:31.5802675Z FAILED tests/test_regime_gate.py::TestRegimeGate::test_pick_without_macro_regime_passes_short - AssertionError: 0 != 1
test (3.11)	Run all tests	2026-05-23T19:21:31.5803413Z FAILED tests/test_regime_gate.py::TestRegimeGate::test_proven_exempt_contrarian_passes_volatile_regime - AssertionError: 0 != 1
test (3.11)	Run all tests	2026-05-23T19:21:31.5804131Z FAILED tests/test_regime_gate.py::TestRegimeGate::test_short_aligned_bearish_regime_passes - AssertionError: 0 != 1
test (3.11)	Run all tests	2026-05-23T19:21:31.5804834Z FAILED tests/test_regime_gate.py::TestRegimeGate::test_short_aligned_bullish_high_short_conf_passes - AssertionError: 0 != 1
test (3.11)	Run all tests	2026-05-23T19:21:31.5805532Z FAILED tests/test_regime_gate.py::TestRegimeGate::test_short_choppy_neutral_regime_passes - AssertionError: 0 != 1
test (3.11)	Run all tests	2026-05-23T19:21:31.5806215Z FAILED tests/test_regime_gate.py::TestRegimeGate::test_short_exempt_in_bullish_regime_passes - AssertionError: 0 != 1
test (3.11)	Run all tests	2026-05-23T19:21:31.5806826Z = 7 failed, 5833 passed, 56 skipped, 10 deselected, 1 xfailed, 6 warnings in 151.97s (0:02:31) =
test (3.11)	Run all tests	2026-05-23T19:21:32.4976066Z ##[error]Process completed with exit code 1.
```

**New deep-dives this check:** CI Tests

⏭️ **Skipping next check** — complicated failure(s); cooldown 15 min until 19:47 UTC.

## CHECK 2026-05-23 19:47:31 UTC
- **Stale failures** (latest run failed, no success since): **1**
- **In progress:** 6
- **Recent failures** (last 15 runs): 0

### (cached) CI Tests — run `26341266716`

## CHECK 2026-05-23 20:02:37 UTC
- **Stale failures** (latest run failed, no success since): **1**
- **In progress:** 2
- **Recent failures** (last 15 runs): 0

### (cached) CI Tests — run `26341266716`

## CHECK 2026-05-23 20:17:41 UTC
- **Stale failures** (latest run failed, no success since): **2**
- **In progress:** 12
- **Recent failures** (last 15 runs): 0

### ❌ [torontoevent.net] Deploy Rise of the Claw
- Run: [26342086147](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26342086147)
- Failed at: 2026-05-23T19:56:09Z
- **Classification:** UNKNOWN — needs manual log review
- **Log tail:**
```
deploy	Deploy to *** via FTP	2026-05-23T20:02:58.1049097Z   File "<stdin>", line 15, in <module>
deploy	Deploy to *** via FTP	2026-05-23T20:02:58.1049603Z   File "/usr/lib/python3.12/ftplib.py", line 121, in __init__
deploy	Deploy to *** via FTP	2026-05-23T20:02:58.1113168Z     self.connect(host)
deploy	Deploy to *** via FTP	2026-05-23T20:02:58.1114341Z   File "/usr/lib/python3.12/ftplib.py", line 158, in connect
deploy	Deploy to *** via FTP	2026-05-23T20:02:58.1114862Z     self.sock = socket.create_connection((self.host, self.port), self.timeout,
deploy	Deploy to *** via FTP	2026-05-23T20:02:58.1115317Z                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
deploy	Deploy to *** via FTP	2026-05-23T20:02:58.1115799Z   File "/usr/lib/python3.12/socket.py", line 852, in create_connection
deploy	Deploy to *** via FTP	2026-05-23T20:02:58.1192612Z     raise exceptions[0]
deploy	Deploy to *** via FTP	2026-05-23T20:02:58.1193319Z   File "/usr/lib/python3.12/socket.py", line 837, in create_connection
deploy	Deploy to *** via FTP	2026-05-23T20:02:58.1194024Z     sock.connect(sa)
deploy	Deploy to *** via FTP	2026-05-23T20:02:58.1194464Z TimeoutError: [Errno 110] Connection timed out
deploy	Deploy to *** via FTP	2026-05-23T20:02:58.1370480Z ##[error]Process completed with exit code 1.
```

### (cached) CI Tests — run `26341266716`

**New deep-dives this check:** [torontoevent.net] Deploy Rise of the Claw

⏭️ **Skipping next check** — complicated failure(s); cooldown 15 min until 20:32 UTC.

## CHECK 2026-05-23 20:32:47 UTC
- **Stale failures** (latest run failed, no success since): **1**
- **In progress:** 15
- **Recent failures** (last 15 runs): 0

### ❌ Sports Prediction Market Sync
- Run: [26342792780](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26342792780)
- Failed at: 2026-05-23T20:29:45Z
- **Classification:** UNKNOWN — needs manual log review
- **Log tail:**
```
failed to get run log: log not found
```

**New deep-dives this check:** Sports Prediction Market Sync

⏭️ **Skipping next check** — complicated failure(s); cooldown 15 min until 20:47 UTC.

## CHECK 2026-05-23 20:47:52 UTC
- **Stale failures** (latest run failed, no success since): **0**
- **In progress:** 10
- **Recent failures** (last 15 runs): 0

✅ **All clear** — no stale failures detected.

## CHECK 2026-05-23 21:02:57 UTC
- **Stale failures** (latest run failed, no success since): **0**
- **In progress:** 5
- **Recent failures** (last 15 runs): 0

✅ **All clear** — no stale failures detected.

## CHECK 2026-05-23 21:18:01 UTC
- **Stale failures** (latest run failed, no success since): **4**
- **In progress:** 6
- **Recent failures** (last 15 runs): 4

### ❌ QuantumFusion Crypto Engine
- Run: [26343772751](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26343772751)
- Failed at: 2026-05-23T21:16:56Z
- **Classification:** FLAKY — git push/rebase race during auto-commit
- **Log tail:**
```
quantum-fusion	Checkout repository	2026-05-23T21:17:00.3608111Z ##[group]Fetching the repository
quantum-fusion	Checkout repository	2026-05-23T21:17:00.3616538Z [command]/usr/bin/git -c protocol.version=2 fetch --no-tags --prune --no-recurse-submodules --depth=1 origin +aaa1a214930884e93fdca7d771fa88444a6ed802:refs/remotes/origin/main
quantum-fusion	Checkout repository	2026-05-23T21:17:00.5958072Z ##[error]fatal: could not read Username for 'https://github.com': terminal prompts disabled
quantum-fusion	Checkout repository	2026-05-23T21:17:00.5967596Z The process '/usr/bin/git' failed with exit code 128
quantum-fusion	Checkout repository	2026-05-23T21:17:00.5968339Z Waiting 19 seconds before trying again
quantum-fusion	Checkout repository	2026-05-23T21:17:19.6005524Z [command]/usr/bin/git -c protocol.version=2 fetch --no-tags --prune --no-recurse-submodules --depth=1 origin +aaa1a214930884e93fdca7d771fa88444a6ed802:refs/remotes/origin/main
quantum-fusion	Checkout repository	2026-05-23T21:17:19.8278263Z ##[error]fatal: could not read Username for 'https://github.com': terminal prompts disabled
quantum-fusion	Checkout repository	2026-05-23T21:17:19.8296519Z The process '/usr/bin/git' failed with exit code 128
quantum-fusion	Checkout repository	2026-05-23T21:17:19.8297244Z Waiting 20 seconds before trying again
quantum-fusion	Checkout repository	2026-05-23T21:17:39.8374295Z [command]/usr/bin/git -c protocol.version=2 fetch --no-tags --prune --no-recurse-submodules --depth=1 origin +aaa1a214930884e93fdca7d771fa88444a6ed802:refs/remotes/origin/main
quantum-fusion	Checkout repository	2026-05-23T21:17:40.0577888Z ##[error]fatal: could not read Username for 'https://github.com': terminal prompts disabled
quantum-fusion	Checkout repository	2026-05-23T21:17:40.0630651Z ##[error]The process '/usr/bin/git' failed with exit code 128
```

### ❌ Forward Trade Tracking v2
- Run: [26343752936](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26343752936)
- Failed at: 2026-05-23T21:16:05Z
- **Classification:** FLAKY — git push/rebase race during auto-commit
- **Log tail:**
```
track-signals	Checkout repository	2026-05-23T21:16:09.8578203Z ##[group]Fetching the repository
track-signals	Checkout repository	2026-05-23T21:16:09.8586676Z [command]/usr/bin/git -c protocol.version=2 fetch --no-tags --prune --no-recurse-submodules --depth=1 origin +aaa1a214930884e93fdca7d771fa88444a6ed802:refs/remotes/origin/main
track-signals	Checkout repository	2026-05-23T21:16:10.0032263Z ##[error]fatal: could not read Username for 'https://github.com': terminal prompts disabled
track-signals	Checkout repository	2026-05-23T21:16:10.0040515Z The process '/usr/bin/git' failed with exit code 128
track-signals	Checkout repository	2026-05-23T21:16:10.0041471Z Waiting 20 seconds before trying again
track-signals	Checkout repository	2026-05-23T21:16:30.0074052Z [command]/usr/bin/git -c protocol.version=2 fetch --no-tags --prune --no-recurse-submodules --depth=1 origin +aaa1a214930884e93fdca7d771fa88444a6ed802:refs/remotes/origin/main
track-signals	Checkout repository	2026-05-23T21:16:30.1412215Z ##[error]fatal: could not read Username for 'https://github.com': terminal prompts disabled
track-signals	Checkout repository	2026-05-23T21:16:30.1428658Z The process '/usr/bin/git' failed with exit code 128
track-signals	Checkout repository	2026-05-23T21:16:30.1429419Z Waiting 20 seconds before trying again
track-signals	Checkout repository	2026-05-23T21:16:50.1512350Z [command]/usr/bin/git -c protocol.version=2 fetch --no-tags --prune --no-recurse-submodules --depth=1 origin +aaa1a214930884e93fdca7d771fa88444a6ed802:refs/remotes/origin/main
track-signals	Checkout repository	2026-05-23T21:16:50.2657010Z ##[error]fatal: could not read Username for 'https://github.com': terminal prompts disabled
track-signals	Checkout repository	2026-05-23T21:16:50.2702222Z ##[error]The process '/usr/bin/git' failed with exit code 128
```

### ❌ DNA Genome Daily Pipeline
- Run: [26343740791](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26343740791)
- Failed at: 2026-05-23T21:15:26Z
- **Classification:** FLAKY — git push/rebase race during auto-commit
- **Log tail:**
```
strategy-permutation	Run actions/checkout@v6	2026-05-23T21:17:01.8507456Z ##[group]Fetching the repository
strategy-permutation	Run actions/checkout@v6	2026-05-23T21:17:01.8517603Z [command]/usr/bin/git -c protocol.version=2 fetch --no-tags --prune --no-recurse-submodules --depth=1 origin +aaa1a214930884e93fdca7d771fa88444a6ed802:refs/remotes/origin/main
strategy-permutation	Run actions/checkout@v6	2026-05-23T21:17:01.9286650Z ##[error]fatal: could not read Username for 'https://github.com': terminal prompts disabled
strategy-permutation	Run actions/checkout@v6	2026-05-23T21:17:01.9295389Z The process '/usr/bin/git' failed with exit code 128
strategy-permutation	Run actions/checkout@v6	2026-05-23T21:17:01.9296145Z Waiting 11 seconds before trying again
strategy-permutation	Run actions/checkout@v6	2026-05-23T21:17:12.9296989Z [command]/usr/bin/git -c protocol.version=2 fetch --no-tags --prune --no-recurse-submodules --depth=1 origin +aaa1a214930884e93fdca7d771fa88444a6ed802:refs/remotes/origin/main
strategy-permutation	Run actions/checkout@v6	2026-05-23T21:17:12.9983240Z ##[error]fatal: could not read Username for 'https://github.com': terminal prompts disabled
strategy-permutation	Run actions/checkout@v6	2026-05-23T21:17:13.0000359Z The process '/usr/bin/git' failed with exit code 128
strategy-permutation	Run actions/checkout@v6	2026-05-23T21:17:13.0000869Z Waiting 17 seconds before trying again
strategy-permutation	Run actions/checkout@v6	2026-05-23T21:17:30.0044867Z [command]/usr/bin/git -c protocol.version=2 fetch --no-tags --prune --no-recurse-submodules --depth=1 origin +aaa1a214930884e93fdca7d771fa88444a6ed802:refs/remotes/origin/main
strategy-permutation	Run actions/checkout@v6	2026-05-23T21:17:30.0758424Z ##[error]fatal: could not read Username for 'https://github.com': terminal prompts disabled
strategy-permutation	Run actions/checkout@v6	2026-05-23T21:17:30.0807824Z ##[error]The process '/usr/bin/git' failed with exit code 128
```

### ❌ Real-Time Battle Test - Eliminate Losers, Optimize Winners
- Run: [26343739696](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26343739696)
- Failed at: 2026-05-23T21:15:23Z
- **Classification:** UNKNOWN — needs manual log review
- **Log tail:**
```
battle-test	Commit battle results	2026-05-23T21:16:54.7046543Z shell: /usr/bin/bash -e {0}
battle-test	Commit battle results	2026-05-23T21:16:54.7046807Z env:
battle-test	Commit battle results	2026-05-23T21:16:54.7047262Z   TOKEN_FOR_PUSH: ***
battle-test	Commit battle results	2026-05-23T21:16:54.7047507Z ##[endgroup]
battle-test	Commit battle results	2026-05-23T21:16:55.5679131Z [main c4ab28cc]  Battle Test: Real-time algorithm validation - 2026-05-23 21:16 UTC
battle-test	Commit battle results	2026-05-23T21:16:55.5679982Z  3 files changed, 61 insertions(+), 36 deletions(-)
battle-test	Commit battle results	2026-05-23T21:16:55.5767768Z   (remote URL updated with push token)
battle-test	Commit battle results	2026-05-23T21:16:55.6522846Z ERROR: Token validation failed (HTTP ?): Bad credentials
battle-test	Commit battle results	2026-05-23T21:16:55.6523920Z   → Check that GH_PAT secret is set and the token has 'repo' scope (full push access).
battle-test	Commit battle results	2026-05-23T21:16:55.6524716Z   → If using github.token directly, verify the workflow has 'permissions: contents: write'.
battle-test	Commit battle results	2026-05-23T21:16:55.6525418Z   → A 401/403 means the token is invalid or expired. A 404 means the repo path is wrong.
battle-test	Commit battle results	2026-05-23T21:16:55.6553048Z ##[error]Process completed with exit code 1.
```

**New deep-dives this check:** QuantumFusion Crypto Engine, Forward Trade Tracking v2, DNA Genome Daily Pipeline, Real-Time Battle Test - Eliminate Losers, Optimize Winners

⏭️ **Skipping next check** — complicated failure(s); cooldown 15 min until 21:32 UTC.
