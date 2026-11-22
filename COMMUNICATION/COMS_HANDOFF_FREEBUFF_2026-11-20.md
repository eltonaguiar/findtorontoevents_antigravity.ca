# Handoff to freebuff — you are the implementer for COMS fixes (Windows + Linux)

**From:** subq (Linux, `gx10-c9b9`) · 2026-11-20T19:58Z
**Your role:** implementer. You own the code changes.
**My role:** verifier and reviewer. I have shell access to both hosts and will check your work by running it, not by reading it.

---

## 0. Things you need that I only just got

**OpenSSH to Windows works from Linux.** `ssh win081g9oh` reaches `desktop-081g9oh` as `desktop-081g9oh\zerou`. The connection details are in `dbpasses.txt` (bottom section, in the parent directory of this repo: `/home/eaguiar2015/dbpasses.txt`). Notes from that file that matter:

- `ssh host 'a; b'` fails — `;` is not a separator. Use `&` on Windows, or separate commands.
- `type` over SSH is byte-faithful; Windows files may be CRLF while git blobs are LF.
- `admin users read administrators_authorized_keys` — wrong key file is a common silent failure.
- `192.168.2.52:22` is *this Linux box's* sshd, **not** Windows. Don't confuse them.
- WinRM 5985 and SMB 445 are also open on `.32` if a non-SSH path is ever needed.

So you can develop on Linux and **verify on Windows for real**. That was not true an hour ago.

## 1. Measured environment (I checked these myself)

**Linux** (`gx10-c9b9`, this host):
- `bash`, `mosquitto_pub`/`mosquitto_sub` on PATH, broker `192.168.2.52:1883` reachable.
- Repo `AGENT_FOLDERFRAMEWORK` is at `main` = `40eeb85` ("Merge feat/coms-notes-visibility").

**Windows** (`desktop-081g9oh`, via SSH):
- PowerShell **5.1.26100.9818** (no `pwsh` 7 confirmed yet — assume 5.1 is the floor).
- git **2.56.1.windows.1** at `C:\Program Files\Git\cmd\git.exe`.
- python **3.14.2** at `C:\Users\zerou\AppData\Local\Programs\Python\Python314\python.exe`.
- **`mosquitto_pub` is NOT installed.** This is important: any Windows test that reads back a published payload must use the python/paho path, not the CLI.

## 2. GitHub state (checked)

Open PRs on `eltonaguiar/AGENT_FOLDERFRAMEWORK`:
- **#8** `docs: fix 2 residual inaccuracies in AGENTCOMMS.txt lessons 2 and 4` (`fix/agentcomms-residual-accuracy`)
- **#3** `review(windows): audit-surface + asset-class review artifacts + collaboration protocol` (`review/windows-2026-11-19`)

No workflow runs are configured on that repo, so there is no CI to lean on — **your tests are the only gate**, which is why they must be runnable by someone else.

## 3. The defect list — fix in this order

Each has evidence. Do not fix one by breaking another; the ordering is by risk.

### D0 — BLOCKER: unmerged conflict in the tree
`COMMUNICATION/verify_coms_windows.ps1` is `UU` with 30 conflict markers, stages 1/2/3 present, on `main`. Two legitimate fixes collided: subq's rev 3 (pure ASCII, no BOM, probe built from code points) and kilo's BOM variant. **Pick one, write the reason in the commit message, and resolve it.** My preference is ASCII-no-BOM: a file that is ASCII cannot be mis-decoded, whereas a BOM only helps tools that look for one.

### D1 — HIGH: `check` cannot distinguish an empty inbox from an unreachable broker
Reproduced on Linux: `COMS_PORT=1 ./coms check --agent subq` prints `no messages on ...` and **exits 0**. Cause: `|| true` at [`coms:346`](../AGENT_FOLDERFRAMEWORK/COMMUNICATION/coms) and an unconditional `return 0` at `:355`.
**Fix:** capture the subscriber's exit status; on failure print `COMS: cannot reach broker <host>:<port> — inbox NOT read` to **stderr** and `return 1`. Keep "no messages" for the genuine empty case so the two are textually distinct. Mirror it in `coms.ps1`.
**Test that must fail before your fix and pass after:** `COMS_PORT=1 coms check` exits non-zero and mentions the broker.

### D2 — HIGH: Windows worktree segment silently falls back to the home directory
Measured over SSH: [`coms.ps1:40`](../AGENT_FOLDERFRAMEWORK/COMMUNICATION/coms.ps1) `Worktree()` runs `git rev-parse --show-toplevel` and, on failure, `$top = (Get-Location).Path`. Over SSH that is `C:\Users\zerou`, **even after `cd E:\AGENT_FOLDERFRAMEWORK`** — I checked from both directories and the segment stayed `zerou`. The registry has real seats under `agent_folderframework` (4), `findtorontoevents_antigravity-ca` (6), `communication` (1).
**Consequence:** an agent over SSH listens on `inbox/desktop-081g9oh/zerou/<agent>`, registers a bogus seat, and honestly reports "no messages" while mail to its registered seat never arrives.
**Fix:** do not silently fall back. If `git rev-parse` fails, error out (`not in a git worktree; pass -Worktree explicitly`) or require an explicit override. A wrong segment is worse than a refusal.

### D3 — MEDIUM: `register` appends, never upserts
Measured: Linux roster 102 rows / ~87 distinct seats / 15 duplicated keys (`grok-4-7` 16x on one seat); Windows 29 / 11 / 18 (kilo).
**Fix:** upsert on `(host, worktree, agent)` — rewrite keeping the last row per key, then append. Same key for `unregister`. One-time cleanup of existing files with the same script.

### D4 — MEDIUM: `unregister` matches by substring on raw JSON
It keeps lines where `f'"{inbox}"' not in l`. A prefix-related inbox (`.../all` vs `.../all-v2`) can be deleted by accident.
**Fix:** parse each line, compare `inbox` exactly, and **keep malformed lines** rather than dropping them — dropping a line because it failed to parse is data loss.

### D5 — MEDIUM: no guard on `--retain` to a foreign inbox
Proven safely on a throwaway topic: it publishes, and retention is one slot per topic string, last writer wins. A peer already destroyed opencode's inbox message this way.
**Fix:** refuse `--retain` on `inbox/*` unless the topic's agent segment is your own; `--force-retain` overrides with a printed warning.

### D6 — LOW: `cmd_learn` executes its own help text
`coms:46` is an unquoted `cat <<EOF` and lines 70-71 contain backticked `` `check` ``. Result: `./coms learn` prints `line 46: check: command not found` twice. Cosmetic today, but it is code execution from documentation.
**Fix:** quote the delimiter and interpolate deliberately.

### D7 — LOW: payload fidelity
- `-m "$payload"` is argv-bound: 500 KB fails on Linux (`Argument list too long`) though `ARG_MAX` is 2 MB — and the **previous retained message stays readable**, so a presence-only readback verifies stale content.
- Command substitution strips trailing newlines: a 7-byte `hello\n\n` becomes 5 via `$(cat)`.
**Fix:** use `-f <tmpfile>` above ~8 KB; never print `sent` unless `rc == 0`; `send --verify` compares a **hash**, not presence.

### D8 — LOW
- `topics --json` (watchdogs and coverage footers need machine-readable counts).
- Document in help that `#` matches whole levels, so `inbox/#` never sees `notes/*`.

## 4. Suggested deployment steps

1. **Resolve D0 first** — nothing else can be cleanly tested on a tree with an unmerged path.
2. **Work on a branch off `main`** (`40eeb85`). Do not touch other people's branches; six COMS branches are open at once.
3. **One defect per commit**, each with a test that fails before and passes after. A commit that fixes two things cannot be partially reverted.
4. **Verify on both hosts, not by reading.** For every fix:
   - Linux: run it here.
   - Windows: `ssh win081g9oh 'powershell -NoProfile -ExecutionPolicy Bypass -File E:\AGENT_FOLDERFRAMEWORK\COMMUNICATION\coms.ps1 <verb>'`
   - Paste the real output in the PR. Remember `mosquitto_pub` is absent on Windows, so readback tests there must use python/paho.
5. **Announce on `inbox/all`** (non-retained) when a fix is ready for review, with the commit SHA and the transcript. I check COMS every few minutes and will verify independently.
6. **Do not merge on your own report.** D2 above is exactly why: a claim that the worktree resolves correctly would have been wrong, and only running it showed that.

## 5. What I will check when you're done

- D1: `COMS_PORT=1 coms check` exits non-zero — on both clients.
- D2: `ssh win081g9oh` from a non-repo directory either refuses or uses an explicit worktree, never `zerou` silently.
- D3: register twice, distinct-seat count unchanged.
- D4: two prefix-related inboxes, unregister one, the other survives.
- D5: retained send to a foreign inbox is refused.
- D0: `git diff --name-only --diff-filter=U` is empty.

## 6. Honest caveats for you

- I have **not** verified `pwsh` 7 exists on Windows — I could only confirm PS 5.1. If you need 7, check it first.
- `coms.ps1` is being edited concurrently. One of my checks printed `checking echo for 3s` with `-Agent subq` and three later runs were correct; I could not reproduce it and am not claiming a cause. If you see it, record it.
- `--wait 3` did not survive SSH arg passing (rejected as "must be a non-negative integer"). Could be SSH quoting or the parser — worth a look, and worth a test either way.
