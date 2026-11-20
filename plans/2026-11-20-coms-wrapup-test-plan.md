# COMS wrap-up: status, defects and test plan (2026-11-20)

**Owner:** `freebuff` (Linux client + broker-side tests). **Windows client:** `kilo` — COMS
tooling is explicitly *outside* the financial deploy lease, so this split does not conflict.
**Measured at:** 2026-11-20T20:20Z, both hosts probed directly (no peer report taken on trust).

## 1. Status

| Surface | State | Evidence |
|---|---|---|
| Linux client | byte-identical to repo `COMMUNICATION/coms` (20,075 B, `diff` empty) | `md5sum`, `diff -q` |
| Linux broker reach | 47 registry seats, 69 notes / 249,175 B | `COMS topics 'registry/#'`, `'notes/#'` |
| Windows client | branch `feat/coms-notes-visibility` @ `a02cf7e`, clean tree, `coms.ps1` 15,427 B on disk | `git status`, `%~zF` |
| Windows tasks | `\COMS-heartbeat` Ready, `\COMS-watch-50` Ready, `runs.txt` = 5 | `schtasks /query` |
| Windows verify | **INFO 4 / PASS 5 / SKIP 3 / FAIL 1** | `verify_coms_windows.ps1 -Agent kilo` |
| Windows readback | 6,068 B payload (148 quotes, 74 newlines) read back exact | peer-verified, re-asserted in suite |

## 2. Defects (each measured, not inferred)

### B1 — Linux help text executes its own content (shell injection in `cmd_learn`)
`COMS notacommand` prints `line 46: check: command not found` **twice** before the help body.
`cmd_learn` uses an unquoted heredoc (`cat <<EOF`), so backticks/`$( )` inside the help prose run
as shell. Any future help line that contains a command substitution is executed on the machine of
whoever asks for help. **Fix:** quote the heredoc (`<<'EOF'`) and escape nothing else. **Size:** 1 char.
**Test:** `COMS notacommand 2>&1 | grep -c 'command not found'` must be 0.

### B2 — Windows derives the seat from CWD (silent misdelivery)
The verify run reports `checking inbox/desktop-081g9oh/zerou/kilo`, but the documented seat is
`inbox/desktop-081g9oh/agent_folderframework/kilo`. The client takes the worktree from the current
directory, so an agent running from `%USERPROFILE%` reads an inbox nobody writes to, while its real
inbox fills up. This is the exact failure the bus exists to prevent, and it is invisible: `check`
exits 0 and prints a plausible seat. **Fix:** read the worktree from the registry entry for the
agent, or require an explicit `-Worktree`; print the resolved topic plus its source.
**Test:** run from `E:\AGENT_FOLDERFRAMEWORK\COMMUNICATION` and from `%USERPROFILE%`; both must
resolve to the registered seat, or exit non-zero.

### B3 — Retain guard absent on Windows
`[INFO] retain guard on foreign inbox -- guard ABSENT on this build`. Linux refuses to `--retain`
into another seat's inbox; Windows does not, so a Windows `send -Retain` can clobber a peer's
retained payload (last-writer-wins, no history). **Fix:** port the Linux guard, fail closed,
`-Force` to override. **Test:** attempt a write to a foreign inbox; expect non-zero exit and an
unchanged readback hash.

### B4 — Roster is append-only (duplicate seats on both platforms)
Linux `~/.coms/agents.jsonl`: **103 rows / 35 distinct / 15 ids duplicated**, worst `gx10-c9b9__auditpage__grok-4-7` ×16.
Windows: **29 rows / 11 distinct / 18 duplicated** (9× hermes-deepseek-flash, 7× opencode).
One defect, two implementations. Cheap and it degrades every "who is alive" decision, including
the lease's consent rule. **Fix:** upsert by `swarmbus_id`, keep the newest `registered_at`, move
the old row to `.bak` once. **Test:** register twice; rows and distinct must not change.

### B5 — `*` is accepted as a topic pattern but is not an MQTT wildcard
`COMS topics 'notes/deploy-lease*'` → `no retained topics` while the topic exists; `notes/+`
returns it. The failure mode is a **false negative**: an agent concludes a note was never
published. I hit this myself and nearly reported a tool bug. **Fix:** reject `*` with a hint
(`use + or #`), or map it. **Test:** `topics 'notes/*'` exits non-zero and names the wildcards.

## 3. Risks

- **R1 — Windows depends on external `mosquitto_pub/sub`.** Absent from PATH, so 3 of 9 verify
  tests skip, including the 500 KB payload test. A transport path that has never run is not a path.
- **R2 — One retained slot per inbox.** A second DM overwrites the first; there is no history and
  no delivery receipt. Durable content belongs in `notes/`, inboxes are wake-up only.
- **R3 — No retention policy.** 69 notes / 249 KB and rising, plus junk: `status/zoo-trunc-probe`
  (100,000 B), `notes/subq-phase-a-result-20261120` (32 B, a `/tmp` filename), bare topic
  `hermes-deepseek-flash` (malformed publish). Owners should clear their own; no one deletes a peer's.
- **R4 — Anonymous broker, no TLS** (`192.168.2.52:1883`). Any LAN host can read or write any
  inbox. Acceptable only while the LAN is trusted; never put a secret on the bus.
- **R5 — `check` window + QoS1 non-retained.** Publish outside the 3 s window with no subscriber
  and the message is gone, while `send` still prints "sent". Silent by design, so it must be said
  out loud in the help text.
- **R6 — Two clients, no conformance fixtures.** bash and PowerShell drift by construction; the
  only parity artifact is a Windows-only verify script. A shared, language-neutral fixture set is
  the fix, and it is the spine of the plan below.

## 4. Test plan

Tiers are gates: a lower tier failing blocks the next.

### Tier 0 — invariants that must stay true (run before and after every change)
| ID | Command | Expected |
|---|---|---|
| T0.1 | `COMS check --agent freebuff` | exit 0, prints the resolved seat |
| T0.2 | `COMS check` (no flag) | exit 2, usage message |
| T0.3 | `COMS topics 'registry/#'` | exit 0, 47 seats |
| T0.4 | `COMS topics 'notes/+'` | lists notes (positive control for B5) |
| T0.5 | Windows `verify_coms_windows.ps1 -Agent kilo` | INFO 4 / PASS 5 / SKIP ≤3 / **FAIL 0** |

### Tier 1 — regression test per defect (blocking)
| ID | Defect | Assertion |
|---|---|---|
| T1.1 | B1 | unknown command emits no `command not found`; help text keeps literal backticks |
| T1.2 | B2 | same seat from two different CWDs on Windows; mismatched seat exits non-zero |
| T1.3 | B3 | foreign-inbox retain refused, readback hash unchanged |
| T1.4 | B4 | double register leaves rows/distinct unchanged (Linux and Windows) |
| T1.5 | B5 | `topics 'notes/*'` exits non-zero with a wildcard hint |

### Tier 2 — transport and semantics
| ID | Test | Pass criterion |
|---|---|---|
| T2.1 | payload fidelity matrix: 1 B, 71 B with quotes+newlines, 1 KB, 6 KB, 500 KB; ASCII, em-dash, emoji | byte-exact readback both directions |
| T2.2 | cross-platform interop: Linux → Windows and Windows → Linux, 6 KB with quotes | exact match, no truncation, no double-CR |
| T2.3 | non-retained publish with no subscriber | documented as lost; `send` says so |
| T2.4 | last-writer-wins on one retained topic | only the second payload survives; help states it |
| T2.5 | `check` window boundary: publish at 2.9 s and 3.1 s | first arrives, second requires `--wait` |
| T2.6 | seat isolation: DM to one seat does not appear in another seat's inbox | isolated; broadcast only via `all` |
| T2.7 | unregister clears the retained topic without a literal empty payload | topic gone, not zero-length |

### Tier 3 — ops and hygiene
| ID | Test | Pass criterion |
|---|---|---|
| T3.1 | notes GC: cap per author, 7-day TTL, index rebuild | `notes/#` count bounded; nothing a peer still cites is deleted |
| T3.2 | schema rejection: topic must match one of the four shapes, notes payload ≥ 80 B | malformed publish exits non-zero |
| T3.3 | watchdog: `COMS-watch-50` increments `runs.txt`, task stays Ready | increments; `maxRuns=0` does not disable it |
| T3.4 | broker restart: retained messages survive `systemctl restart mosquitto` | same topic count and payload hashes before/after |
| T3.5 | secret scan: grep bus payloads for key-shaped strings | zero matches |

## 5. Order of work (today)

1. **Now:** land this plan; post the defect list to the bus; kilo confirms it owns B2/B3.
2. **Next:** B1 + B5 on Linux (one-line heredoc fix, one argument guard) with T1.1/T1.5.
3. **Then:** B4 upsert on both platforms with T1.4 (it blocks every liveness claim).
4. **Then:** B2 + B3 on Windows with T1.2/T1.3, and re-run T0.5 to FAIL 0.
5. **Then:** T2.1–T2.4 across both directions; decide the 500 KB path (bundle mosquitto vs .NET MQTT).
6. **Last:** T3.1–T3.5, T3.4 only in a maintenance window with the human's go-ahead.

## 6. Exit criteria for "COMS is wrapped up"

- T0.5 has **FAIL 0** and **SKIP ≤ 1** on Windows.
- B1–B5 each closed with its Tier-1 test green in CI or in a recorded manual transcript.
- Roster: `rows == distinct` on both hosts.
- T2.1–T2.4 green in both directions, including the 500 KB payload.
- A notes retention policy merged, with the junk topics cleared by their owners.
- This document updated with the result column, not replaced.

## 7. Non-goals

No broker auth/TLS work today (needs a maintenance window and the human's call). No change to the
four topic shapes. No deletion of a peer's retained topic. No financial-surface changes — those
stay behind the deploy lease.

## 8. Results (measured 2026-11-20T20:10Z)

Branch `coms-b1-b5-fixes-20261120` @ `bad7a54` in `eltonaguiar/AGENT_FOLDERFRAMEWORK`, validated on
both hosts. Client installed at `~/.local/bin/COMS`; Windows checkout pulled to the same tip.

| Defect | Fix | Verified by |
|---|---|---|
| B1 | `cat <<'EOF'` in `cmd_learn` | `notacommand` exits 2, **0** "command not found", literal backticks still in the help |
| B5 | `*` rejected with a hint | `topics 'notes/*'` exits 2 and names `+`/`#`; `notes/+` still lists (84 notes at test time) |
| B4 | upsert by `swarmbus_id` | double register leaves **1** row on Linux (isolated HOME) and **1** occurrence on Windows; in-place `goal` update confirmed |
| B2 | registry-first seat resolution + `-WorktreeName` | from `E:\AGENT_FOLDERFRAMEWORK\COMMUNICATION` **and** `C:\Users\zerou` both resolve to `inbox/desktop-081g9oh/agent_folderframework/kilo` `[seat source: registry-newest]` |
| B3 | retain guard, `-Force` override | foreign-inbox `--retain` refused with a non-zero exit (`B3=REFUSED_NONZERO`) |

Existing roster damage repaired with the new `COMMUNICATION/dedupe_roster.py` (timestamped `.bak` kept):
Linux 104 rows -> 36, Windows 30 rows -> 12.

Windows verify suite: **PASS 7 / INFO 3 / SKIP 3 / FAIL 0** (was PASS 5 / FAIL 1).

**Exit criteria: partially met.** `FAIL 0` is met. `SKIP <= 1` is **not** met — the three skips are
all "mosquitto binaries absent from Windows PATH" (independently confirmed by kilo), so the 500 KB
payload path on Windows still has never run. That is R1, not a passing test.

Still open: no CI in this repo (copilot asked for one), 500 KB path on Windows, notes GC policy,
broker-restart test (needs a maintenance window).

