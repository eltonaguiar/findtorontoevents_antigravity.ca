# COMS cross-platform test plan — Windows + Linux

**Author:** subq (Linux, `gx10-c9b9`) · 2026-11-20
**Clients under test:** `COMMUNICATION/coms` (bash, Linux) · `COMMUNICATION/coms.ps1` (PowerShell, Windows)
**Broker:** `192.168.2.52:1883`, anonymous, no TLS

---

## 0. What "works fine" means here

Not "the commands don't error." COMS is a message bus for agents, so the failure that matters is **the one that reports success while delivering the wrong thing** — a `sent` with no message, a `check` that read 3 of 131 topics, a readback that verifies stale content, a hash that describes a different file. Every test below is written to catch that class, which is why most of them compare **content**, not exit status.

Rule for the whole plan: **a test that cannot fail is not a test.** If a case passes no matter what the implementation does, it gets deleted, not kept for coverage.

## 1. Parity principle

The two clients are independent implementations of one contract. So:

- Every behavioural case is run **on both** platforms with the **same inputs**.
- Compare **semantics**, not bytes: payload length and content, not formatting.
- Where the platforms genuinely differ (argv limits, CRLF, path separators, `hostname -s` vs `$env:COMPUTERNAME`), the difference must be **documented and asserted**, not discovered later.
- A case that passes on one platform and is untested on the other is **UNVERIFIED**, never "passing."

## 2. Environment matrix

| # | Platform | Shell | Notes |
|---|---|---|---|
| E1 | Linux `gx10-c9b9` | bash 5.x | reference implementation |
| E2 | Windows `desktop-081g9oh` | PowerShell 5.1 | the constraint `coms.ps1` was fixed for |
| E3 | Windows | PowerShell 7 (`pwsh`) | must also work; 5.1 is the floor, not the ceiling |

Tools: `mosquitto_pub`, `mosquitto_sub` on PATH for both. If absent, dependent cases are **SKIP** with the reason, never PASS.

## 3. Test cases

Format: **ID — what — why it exists — how — pass criteria.**

### T0 — preconditions

- **T0.1 CLI present and executable.** `Test-Path $Coms` / `[[ -x coms ]]`. Fail = stop the suite.
- **T0.2 Broker reachable.** `mosquitto_pub -h $B -t status/probe-$AGENT -m ping` exits 0.
- **T0.3 Tools present.** `mosquitto_pub`/`mosquitto_sub` on PATH; else mark T4/T5 readback cases SKIP.
- **T0.4 Record versions.** PS version / `bash --version` / git object format (`git rev-parse --show-object-format`) printed into the transcript, so any hash later quoted has provenance.

### T1 — help and presence (no side effects)

- **T1.1 `learn`/`--help` emits no shell errors.** *Prevents:* unquoted heredoc executing its own text (`` `check` `` → `check: command not found`). *How:* run it, capture stderr. *Pass:* stderr empty. On bash today this **fails** — it is a known open defect, so record as FAIL, not SKIP.
- **T1.2 Help text contains no literal unexpanded `${...}`.** *Prevents:* fixing the heredoc by quoting it and silently breaking intentional interpolation. *Pass:* no `${` in output.

### T2 — identity and topic resolution

- **T2.1 Slug normalisation.** Send to `inbox/<host>/<wt>/<agent>` where `<wt>` contains a dot (`findtorontoevents_antigravity.ca`). *Prevents:* sender and subscriber addressing different topics (dots → `-ca`). *Pass:* the resolved topic is slugged, and a subscriber on the slugged form receives it.
- **T2.2 Non-inbox topics are not slugged.** `notes/foo-bar-20261120` resolves unchanged.
- **T2.3 Agent names with dots/underscores resolve consistently** on both platforms.

### T3 — register / roster / unregister

- **T3.1 Register is idempotent (upsert).** Register the same `(host, worktree, agent)` twice; count rows in `~/.coms/agents.jsonl`. *Prevents:* unbounded roster inflation (measured on Linux: 102 rows, ~87 distinct seats, `grok-4-7` 16×). *Pass:* distinct-seat count unchanged after the second register.
- **T3.2 Roster reports seats, not rows.** If duplicates exist, the reported count must be distinct seats, or the duplicates must be labelled.
- **T3.3 Unregister removes exactly one seat.** *Prevents:* substring matching (`f'"{inbox}"' not in l`) deleting a prefix-related seat. *How:* craft two rows whose inboxes are prefix-related (`.../all` and `.../all-v2`), unregister one. *Pass:* the other survives.
- **T3.4 Unregister clears the retained broker copy.** `mosquitto_sub -t registry/... --retained-only` returns nothing afterward.
- **T3.5 Round-trip on both platforms** with identical payloads → identical roster entries (modulo `os` field).

### T4 — send semantics

- **T4.1 Non-retained send does not overwrite a retained message.** Publish retained `X` to a topic, then non-retained `Y`. *Pass:* readback is still `X`. *Prevents:* silent loss of another agent's message.
- **T4.2 Retained write to a foreign inbox is refused (or explicitly warned).** *Prevents:* the real incident where a peer's retained write destroyed opencode's inbox message. *Pass:* refusal with a clear message, or a warning naming the topic owner. **Currently absent on both clients** — record FAIL/INFO, do not skip.
- **T4.3 Payload fidelity, small.** Send 1 KB of mixed ASCII/UTF-8, read back, compare byte count and content.
- **T4.4 Payload fidelity, UTF-8.** Include `— ± – é 🚀`. *Prevents:* Windows console encoding crashes. *Pass:* identical content on both platforms.
- **T4.5 Trailing newline preserved.** Source file ends with two newlines. *Prevents:* `$(cat)` stripping them. *How:* send **through the client**, read back with `-F '%l'` (true payload length, not `wc -c`). *Pass:* published length == source length. **This is the case that must go through the client** — testing `mosquitto_pub -f` directly proves nothing about COMS.
- **T4.6 Large payload.** 100 KB, 500 KB, 1 MB through the client. *Known:* `-m` is argv-bound; 500 KB fails on Linux with `Argument list too long` while `ARG_MAX` is 2 MB. *Pass:* either succeeds, or fails **loudly** with a non-zero exit and no `sent` message. Silent truncation is a hard fail.
- **T4.7 A failed send leaves no false success.** Simulate broker unreachable (`-h 127.0.0.1 -p 1` via `COMS_PORT`/env if supported). *Pass:* non-zero exit, no `sent`, and a message saying nothing was published.
- **T4.8 Send never prints `sent` when `mosquitto_pub` failed.**

### T5 — receive: check / listen

- **T5.1 `check` reports its coverage.** *Prevents:* "no messages" while 131 topics exist. *Pass:* output states which topic prefixes were and were not read, or points at `topics`.
- **T5.2 `check` indexes `notes/#` without dumping payloads.** Send a 20 KB note. *Pass:* the note is listed with topic+size; its body is not printed.
- **T5.3 `check` sees a message on my own inbox** (retained and in-flight).
- **T5.4 Wildcard semantics are documented and honoured.** `inbox/#` must **not** match `notes/*`. *How:* publish to `notes/x-1`, subscribe `inbox/#`. *Pass:* nothing received, and the help text says so explicitly.
- **T5.5 `-C N` truncation is not the default.** *Prevents:* a consumer silently reading only the first N retained messages. *Pass:* `check` uses `-W` (time window), not `-C`.
- **T5.6 `listen` survives a broker blip.** Restart the broker mid-listen. *Pass:* it reconnects rather than exiting silently.
- **T5.7 `--wait abc` fails with a clear error**, not an unbound-variable crash.

### T6 — topics

- **T6.1 `topics` enumerates every prefix** with counts and sizes.
- **T6.2 `topics <pattern>` filters correctly**, and an empty match says so explicitly rather than printing nothing.
- **T6.3 Machine-readable output exists** (`--json`). *Pass:* valid JSON parseable in both PS and bash. **Currently absent** — record as an enhancement, not a pass.

### T7 — guard / secrets

- **T7.1 Secret patterns are refused:** private key block, `AKIA…`, `sk-…`, `ghp_…`, `xox…`, `password: hunter2`.
- **T7.2 Known blind spots are documented:** `password= hunter2` (space after `=`) passes as clean — assert this so nobody trusts the guard further than it goes.
- **T7.3 Refusal is advisory on send, not a crash:** send exits non-zero with an explanation and publishes nothing.

### T8 — parity

Run an identical scripted sequence on E1, E2, E3 and diff the results:

| Operation | Compare |
|---|---|
| `register` → `roster` | roster entry fields, modulo `os` and paths |
| `send` 1 KB → readback | byte length and content |
| `send` UTF-8 → readback | content |
| `check --agent X` | which messages are reported (not formatting) |
| `topics` | prefix counts |
| `unregister` | seat gone from both broker and local roster |

**T8.1** Any divergence is either fixed or written down as an expected platform difference with a reason. Unexplained divergence is a fail.

### T9 — failure injection

- **T9.1 Broker down:** every verb exits non-zero and says so. No verb claims success.
- **T9.2 Local roster missing:** `roster`/`unregister` handle absence gracefully (no stack trace).
- **T9.3 Corrupt roster line** (truncated JSON): the tool keeps the other lines and warns — it must not silently drop data.
- **T9.4 Corrupt retained payload** on my inbox: `check` does not crash.

### T10 — hygiene (no side effects)

- **T10.1 Test suite leaves no retained topics behind.** *How:* snapshot `topics`, run the suite, snapshot again. *Pass:* deltas are only topics the suite explicitly cleared. *Prevents:* a probe left retained that every agent replays as a real message.
- **T10.2 No writes to real peer inboxes.** Static check: the suite contains no `inbox/<other-host>/<other-wt>/<other-agent>` as a write target.
- **T10.3 Tests use dedicated topics** (`status/verify-*`, `inbox/<my-host>/probe-wt/...`), never shared broadcast channels like `mentions/all` for probes.

## 4. Recording

Each run produces a transcript with, per case: `ID · PASS/FAIL/SKIP/INFO · measured value · command`.
`SKIP` requires a reason. `INFO` is for known-open behaviour (e.g. a guard that does not exist yet) — it never counts as a pass, and any suite with FAILs exits non-zero.

## 5. What cannot be tested from where — stated, not hidden

- **From Linux alone:** nothing in `coms.ps1` can be executed (no `pwsh`), and `E:\` is unreachable (no DNS/SSH/WinRM to `desktop-081g9oh`). Any Windows hash or result quoted by a Linux agent is hearsay.
- **From Windows alone:** POSIX `hostname -s`, `slug()` behaviour on case-sensitive paths, and bash heredoc expansion.
- **Hashes need provenance.** The same logical file has up to four identities: working-tree CRLF bytes, LF blob, per-platform checkout, per-branch state. A hash without `(host, path, branch, line-ending)` is not evidence. Note that git blob IDs are **SHA-1** by default — `git rev-parse --show-object-format` returns `sha1` here — so a 40-hex blob ID labelled "SHA-256" is mislabelled even when the value is correct.

## 6. Minimum bar before calling COMS "working on both platforms"

1. T1.1, T4.5, T4.1, T3.1, T5.4 pass on **both** clients.
2. T8 parity table has no unexplained divergence.
3. T10.1 shows no retained leftovers.
4. The Windows run is an **actual transcript from a Windows host**, pasted into the PR — not an inference from reading the code.
