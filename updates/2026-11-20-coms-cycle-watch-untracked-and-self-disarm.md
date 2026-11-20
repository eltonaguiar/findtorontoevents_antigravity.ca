# COMS cycle watcher: untracked asset + silent self-disarm (2026-11-20)

## What was broken

Two defects in `tools/coms_cycle_watch.py`, both discovered while auditing the
Windows-side COMS watcher scripts (`coms-watch.ps1`, `coms-agent-wake.ps1`).

### 1. The script was not in git, but a shipped ledger points at it

```
$ git ls-files --error-unmatch tools/coms_cycle_watch.py
error: pathspec ... did not match any file(s) known to git

$ git grep -l 'coms_cycle_watch' HEAD
HEAD:reports/TODO_LEDGER_2026-11-19.json     <-- tracked
```

`reports/TODO_LEDGER_2026-11-19.json` is committed to `main` and references a
script that existed only in one working tree. Anyone cloning the repo, or any
agent working from a fresh checkout, gets a ledger whose verification step
cannot run. The file was also **not** gitignored — it had simply never been
added. Nothing was protecting it from loss.

### 2. It disarms itself silently on exhaustion — the same bug as the Windows watch

```python
def disarm() -> None:
    rc, cur = sh("crontab -l", timeout=30)
    keep = "\n".join(l for l in cur.splitlines() if MARK not in l)
    subprocess.run("crontab -", shell=True, input=keep + "\n", ...)
    sh(f"echo '{now()} cron disarmed (cycles exhausted, todos closed)' >> {ACTIONS}")
```

`MAX_CYCLES = 3`. After three cycles with no open todos, the script **removes
its own crontab line**. It leaves one append-only log line and nothing else.

Measured end state on this host:

```
$ cat .coms_cycle_state.json
{ "cycle": 3, "started_at": "2026-11-19T23:57:23Z", "replies": 3,
  "open_todos": 0, "last_run": "2026-11-20T00:30:11Z" }

$ tail -1 reports/coms_cycle_actions.log
2026-11-20T00:30:11Z cron disarmed (cycles exhausted, todos closed)

$ crontab -l | grep -i cycle
(no coms lines)
```

The watcher is gone. Nothing surfaced that fact — you had to go looking.

**Why this matters more than it looks:** the fleet's standing rule is that a
watch must *alert* on exhaustion, never *remove itself*. Self-removal converts
"my coverage expired" into "there is nothing to report." Those are opposite
states, and the quiet one is indistinguishable from healthy. This is the same
defect independently observed in the Windows watcher, so it is a **systemic
pattern across both platforms**, not a one-off typo.

## What was changed

Nothing in the script's behaviour. **This commit is preservation only**, verbatim:

| | |
|---|---|
| Path | `tools/coms_cycle_watch.py` |
| Bytes | 6,793 |
| Lines | 180 |
| SHA-256 | `4d48ff03aef2af36a008000ddb55a9093a52ac74f39085634411c69c5053e3e3` |
| git blob SHA-1 | `1bb2295024535ebef509a65910191ca2bee01c98` |

The file was copied byte-for-byte from the working tree and verified by
`sha256sum` on both sides before staging. `disarm()` was **deliberately left
intact** — silently "fixing" another agent's script while claiming to preserve
it would misrepresent the commit. The defect is recorded here and fixed in a
separate change.

## Deliberately NOT done

- **The Windows watch scripts are not committed.** They live at
  `C:\Users\zerou\.coms\watch\` on `desktop-081g9oh`. There is no route to them
  from this host: no DNS for `desktop-081g9oh`, WinRM 5985 closed, SSH closed,
  no CIFS/SMB mount, and no `pwsh`. They cannot be committed from here and were
  not fabricated. Tracked as an open request on COMS.
- `disarm()` not modified (see above).
- No other file touched. `coms_cycle_watch.py` was **never executed** during this
  work — `py_compile` only.

## How it was verified

```
$ sha256sum tools/coms_cycle_watch.py            # in the commit branch
4d48ff03...5053e3e3  tools/coms_cycle_watch.py
$ sha256sum <working tree>/tools/coms_cycle_watch.py
4d48ff03...5053e3e3  tools/coms_cycle_watch.py   <-- identical

$ python3 -c "import py_compile; py_compile.compile('tools/coms_cycle_watch.py', doraise=True)"
syntax OK

$ git ls-tree HEAD reports/TODO_LEDGER_2026-11-19.json
100644 blob 81416413...  reports/TODO_LEDGER_2026-11-19.json   <-- dangling ref now resolved
```

## Follow-up

1. Fix `disarm()` to leave the crontab line in place and emit a loud retained
   COMS alert instead. Until then, any host running this will quietly stop
   watching after 3 cycles.
2. Obtain `coms-watch.ps1` / `coms-agent-wake.ps1` from the Windows host and
   commit under `COMMUNICATION/watch/` with hashes in the commit message.
3. Adopt hash provenance: every hash claim must state **host + branch + path +
   hash algorithm**. A 40-hex value is a git blob **SHA-1**, not SHA-256; a
   working-tree `Get-FileHash SHA256` over a CRLF file can never equal the SHA-256
   of the LF blob. Raised by subq while reviewing Kilo's inventory.
