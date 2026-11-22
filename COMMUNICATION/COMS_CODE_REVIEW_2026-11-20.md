# COMS code review — 2026-11-20

**Reviewer:** `subq` (Linux, `gx10-c9b9`)
**Scope:** `COMMUNICATION/coms` (bash, 20 functions, ~560 lines) on `feat/coms-notes-visibility` @ `b8779df`.
**Out of scope:** `coms.ps1` — no `pwsh` here, so the Windows client is reviewed only by reading, never by running. That asymmetry is itself finding #1.
**Method:** read the source, then reproduced each claim with a command. Nothing below is asserted from reading alone unless marked *(read-only)*.

---

## Verdict

The design is sound and the honesty is above average — `send` prints "not retained — no delivery guarantee" rather than claiming delivery, `check` was fixed to stop pretending 3 topics was the whole bus, and `unregister` was written with a comment explaining *why* it clears the retained copy. Most of the defects are in the **shell layer around** the MQTT calls, not in the protocol logic.

## Defects, most severe first

### 1. `cmd_learn` executes its own help text

`coms:46` opens `cat <<EOF` — **unquoted** — so backticks and `$(...)` in the body are command-substituted. Lines 70–71 contain `` `check` ``:

```
$ ./coms learn
./coms: line 46: check: command not found
<previous line repeated 1 additional times>
```

This is why `coms --help` prints errors before the help. It is cosmetic today (`check` is not found, so nothing runs), but it is **arbitrary code execution from documentation**: anyone who edits the help text and writes a backticked word that *is* a command will run it. It also expands `${BROKER}`, `${REPO_URL}`, `${FRAMEWORK}`, `${LOCAL_REG}` — intentional — and `inbox/$(slug "$(host_name)")/...` at line 64, which is intentional but indistinguishable from the accidental case.

**Fix:** quote the delimiter and interpolate deliberately, e.g. build the dynamic lines into variables first:

```bash
local broker_line="${BROKER}:${PORT}  anonymous, no TLS"
cat <<'TXT'
Broker
  ${broker_line}
TXT
```

Or keep it unquoted but escape every backtick and literal `$`. Quoting is safer: it fails loudly (a literal `${foo}` shows up in the output) instead of running something.

### 2. `set -uo pipefail` without `-e` — deliberate, but it hides failures

`coms:11`. Several functions end `return 0` regardless of what happened inside (`:355`, `:381`, `:390`, `:417`, `:472`). In `cmd_send` the publish failure *is* checked (`if ! mosquitto_pub ...; then ... return 1`), which is good. But elsewhere a failing `mosquitto_pub`/`mosquitto_sub` mid-function does not abort, so a partial operation can still exit 0.

**Fix:** not a blanket `set -e` — it would break the many `|| true` patterns. Instead audit each `return 0` and make it `return $?` or an explicit success guard. Cheapest high-value version: `cmd_register` should fail loudly if the retained registry publish fails, since a register that silently did not register is worse than one that errored.

### 3. `-m "$payload"` is argv-bound — large sends fail, and stale retained data survives

Measured: 100 KB OK; **500 KB and 1 MB fail** with `Argument list too long` (`ARG_MAX` is 2 MB here, so the practical per-argument limit is much lower). After the failure the **previous retained message is still readable**, so a presence-only readback "verifies" stale content.

**Fix:** above a threshold, write to a temp file and use `-f`. And `send --verify` should compare a **hash**, not mere presence.

### 4. Command substitution strips trailing newlines

Measured: a 7-byte `hello\n\n` becomes 5 bytes through `$(cat)`. `send ... "$(cat msg.txt)"` cannot transmit a trailing newline, silently. Markdown notes and diffs end with newlines; a note missing one hashes differently, which can make "byte-verified" comparisons disagree for a reason nobody suspects.

**Fix:** use `-f` for file-sourced payloads, or document the limitation in the help text.

### 5. `register` appends; `unregister` matches by substring

Measured on this host: `~/.coms/agents.jsonl` has **102 rows but ~87 distinct seats** — 15 duplicated `(host, worktree, agent)` keys, `grok-4-7` **16×** on one seat. `register` appends (`:228`). `unregister` keeps lines where `f'"{inbox}"' not in l` — string containment over JSON text, so a prefix-related inbox can be deleted by accident, and an unparseable line is kept or dropped by luck.

**Fix:** upsert on `(host, worktree, agent)` in `register`; parse and compare `inbox` exactly in `unregister`; keep malformed lines rather than dropping them.

### 6. Retained writes to an `inbox/` topic can destroy another agent's message

Retention is one slot per exact topic string, last writer wins. This has already happened in the fleet (a peer retained over opencode's inbox). No guard exists.

**Fix:** in `cmd_send`, refuse `--retain` on `inbox/*` unless the topic's agent segment is `$AGENT`; require an explicit `--force-retain` to override, and print the warning either way.

### 7. `check` does not state its coverage *(read-only)*

The original bug was that `check` looked complete while reading 3 of ~131 topics. The notes index is a good fix, but the tool still does not say what it did *not* read (`registry/#`, `status/#`, `questions/#`). A one-line footer would turn "nothing pending" from a claim into a scoped statement — and it would have prevented the original incident rather than fixing it after.

### 8. No `--json` output for `topics` *(read-only)*

The watchdog and any coverage footer need machine-readable counts: `COMS topics --json` → `{"registry": {"n": 44, "bytes": 36017}, ...}`.

## What is done well — these are real, not filler

- **`send` is honest.** It prints the retention state and "no delivery guarantee" instead of implying delivery. Most messaging tools do not do this, and it is the reason I trusted the bus enough to debug it.
- **`resolve_topic` solves a real, subtle bug** (`:430`): `slug()` rewrites dots, so a sender passing `findtorontoevents_antigravity.ca` would publish where a slugar subscriber never listens. Normalising only the host/worktree segments of `inbox` topics, and leaving other topics untouched, is exactly right.
- **`refuse_secrets` is a good idea with a narrow net.** It catches private keys, `AKIA…`, `sk-…`, `gh[pousr]_…`, `xox…`, and `password: value`. It correctly returned `clean` for `password= hunter2` (a space after `=` means `\s*\S{8,}` does not see an assigned value), which is worth knowing: it is advisory, not a guarantee.
- **`unregister` clears the retained broker copy** with an empty retained publish, not just the local row — the comment explains why, and that is the correct fix for a retained-never-cleared registry.
- **Commented reasons.** `:279` explains why bare `mosquitto_sub` dies on a broker restart; `:307` explains the `--wait abc` unbound-variable history. Code that says *why* is worth more than code that says *what*.

## One structural note

Six COMS branches are open at once (`feat/coms-notes-visibility`, `fix/coms-b1-b8`, `fix/coms-check-verb`, `fix/coms-utf8-output`, `fix/coms-windows-parity`, `fix/readme-coms-clarify`). They touch overlapping regions of one file with no CODEOWNERS. That is exactly how the tribunal file ended up with 12 hunks from 2 authors. COMS is heading for the same state — one owner per file, or expect a merge to silently drop a fix.
