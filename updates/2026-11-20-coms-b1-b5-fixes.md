# COMS client fixes B1-B5 (2026-11-20)

## What was broken (all measured, none inferred)

| ID | Defect | Measurement before the fix |
|---|---|---|
| B1 | `cmd_learn` used an unquoted heredoc, so backticks in the help prose ran as shell | `COMS notacommand` printed `line 46: check: command not found` twice |
| B2 | Windows derived the seat from the current directory | verify run reported `inbox/desktop-081g9oh/zerou/kilo`; the registered seat is `.../agent_folderframework/kilo`, so `check` read an inbox nobody writes to and exited 0 |
| B3 | No retain guard in the Windows client | `[INFO] retain guard on foreign inbox -- guard ABSENT on this build`; a Windows `send -Retain` could clobber a peer's retained payload |
| B4 | Roster append-only on both platforms | Linux 103 rows / 35 distinct / 15 ids duplicated (worst x16); Windows 29 rows / 11 distinct / 18 duplicated |
| B5 | `*` accepted as a topic pattern although it is not an MQTT wildcard | `topics 'notes/deploy-lease*'` returned "no retained topics" while the note existed; `notes/+` found it |

## What changed

`COMMUNICATION/coms` (+39): quoted heredoc; `*` rejected with a hint naming `+` and `#`; roster
written by an upsert that merges non-empty fields per `swarmbus_id`.

`COMMUNICATION/coms.ps1` (+75): `Worktree` resolves `-WorktreeName`, then the registry row for the
agent on this host, then the git toplevel, then the cwd, and records `$script:WtSource` which `check`
prints; `-Force`-guarded refusal on `--retain` into another seat's inbox; roster upsert.

`COMMUNICATION/dedupe_roster.py` (new): repairs the existing damage, dry-run by default, keeps a
timestamped `.bak`.

## How it was verified

Linux, isolated `HOME`: unknown command exits 2 with zero shell executions; `notes/*` exits 2 with
the hint while `notes/+` still lists 84 notes; double register leaves 1 row and updates `goal` in
place; `check` exits 0 and `check` without `--agent` exits 2.

Windows over OpenSSH (`win081g9oh`): seat identical from both `E:\AGENT_FOLDERFRAMEWORK\COMMUNICATION`
and `C:\Users\zerou` (`[seat source: registry-newest]`); foreign-inbox retain refused with a
non-zero exit; double register yields one occurrence; `verify_coms_windows.ps1 -Agent kilo` goes from
**PASS 5 / FAIL 1** to **PASS 7 / FAIL 0** (SKIP 3).

Rosters repaired: Linux 104 -> 36, Windows 30 -> 12, both with `.bak` copies.

## What is not verified

- Windows still skips 3 transport cases because `mosquitto_pub`/`mosquitto_sub` are not on PATH
  (independently confirmed). The 500 KB payload path on Windows has therefore never run.
- No CI exists in `AGENT_FOLDERFRAMEWORK`; these checks are a recorded transcript, not a gate.
- The branch was pushed but **no PR could be opened**: the `gh` token is invalid on both hosts.
  Merge is pending a re-auth or a human click.

## Correction, same day: B3 was not Windows-only

The table above says the retain guard was missing from the Windows client and implies Linux had
one. That was wrong, and `coms.ps1`'s own comment said the same thing. Measured directly by
retaining into a seat nobody owns:

```
$ COMS send --retain inbox/ci-probe-host/ci-probe-wt/ci-probe-agent 'guard probe'
sent inbox/ci-probe-host/ci-probe-wt/ci-probe-agent (qos1, retained)   # exit 0
$ mosquitto_sub -t that-topic --retained-only
guard probe                                                           # it landed
```

So **neither** client had the guard; the Windows port had been written against a false premise.
Both now refuse, with `--force` as the explicit override, and the Linux acceptance suite asserts
that a refused retain publishes 0 bytes while the worktree-wide `all` broadcast still passes.

Second correction in the same area: `send -m` cannot carry a large payload on either platform.
Linux caps one argv element at 128 KiB (`MAX_ARG_STRLEN`), the Win32 command line at 32767
characters. Both clients gained a file-based send (`--file` / `-File`), and the 500 KB path is now
tested end to end on Windows (500,000 of 500,000 bytes) instead of being skipped.

