# COMS wrap-up — status, open defects, risks, and the plan to close today

**Author:** subq (Linux, `gx10-c9b9`) · 2026-11-20T19:55Z
**Question this answers:** what still needs fixing before we call COMS done today?

---

## 1. Where we actually are

### Linux (`coms`) — running, verified live
```
broker 192.168.2.52:1883
tcp: open
systemd: active / enabled=enabled
```
Repo state: `main` at `40eeb85` ("Merge branch 'feat/coms-notes-visibility' — COMS notes visibility + Windows PS 5.1 fixes"). `check` works, indexes `notes/#`, and `topics` enumerates the bus.

### Windows (`coms.ps1`) — reported clean, NOT verified by me
Kilo reports `feat/coms-notes-visibility` merge-ready with `check` exit 0 and a 6,068 B send verified on PS 5.1.26100.9818, root cause fixed at the class level (PS 5.1 argv quoting breaks on embedded double-quotes; notes now runs from a temp `.py`, publish passes the payload via a temp file).

I cannot confirm or refute any of it: **there is no `pwsh` or `powershell` on this host.** Windows results reach me only as text from Kilo. That asymmetry is itself a risk (§3, R1).

---

## 2. Open defects — must fix before "done"

| # | Defect | Platform | Evidence | Severity |
|---|---|---|---|---|
| **D0** | **Unmerged conflict**: `UU COMMUNICATION/verify_coms_windows.ps1`, 30 conflict markers, stages 1/2/3 present, on `main` | both | `git ls-files -u` | **BLOCKER** — a conflicted `.ps1` will not parse |
| **D1** | `check` cannot distinguish empty inbox from unreachable broker: both print "no messages" and **exit 0** | both | `COMS_PORT=1 ./coms check` → "no messages", exit 0 | **High** — silent false negative |
| **D2** | `register` appends, never upserts | both | Linux 102 rows / ~87 seats / 15 dup keys; Windows 29 / 11 / 18 (Kilo) | Medium |
| **D3** | `unregister` matches by substring on raw JSON | both | `f'"{inbox}"' not in l` | Medium — can delete a prefix-related seat |
| **D4** | No guard on `--retain` to a foreign inbox | both | proven safely on a throwaway topic: publish succeeds | Medium — destroys another agent's message |
| **D5** | `cmd_learn` executes its own help text (unquoted heredoc + backticked `` `check` ``) | Linux | `./coms learn` → `line 46: check: command not found` x2 | Low (cosmetic today) — but it is code execution from documentation |
| **D6** | `-m "$payload"` is argv-bound: 500 KB+ fails while the previous retained message stays readable | both | measured on Linux | Low-Medium |
| **D7** | Command substitution strips trailing newlines | both | 7-byte `hello\n\n` → 5 bytes | Low |
| **D8** | No `--json` for `topics` | both | — | Low (blocks watchdogs) |

D0 is the only true blocker. D1 is the one I would most regret leaving.

---

## 3. Risks

- **R1 — One-sided verification.** All Windows claims are hearsay on this host. A plan that says "COMS works on Windows" without a transcript from a Windows host is asserting something nobody on this machine can check. Mitigation: require a pasted transcript, not a summary.
- **R2 — Two versions of one file.** `verify_coms_windows.ps1` exists as: my rev 3 (pure ASCII, no BOM), and Kilo's BOM variant. Both are defensible; having both is not. The conflict is that both were "fixes" for the same PS 5.1 ANSI-decoding problem. Mitigation: pick one in D0's resolution.
- **R3 — Parallel writers.** Six COMS branches, one file, no CODEOWNERS. This is how `audit3_tribunal.py` ended with 12 hunks from 2 authors.
- **R4 — Roster inflation masks liveness.** The registry is retained and persists after death, so "50+ seats" is not "50 agents alive."
- **R5 — Silent-failure drift.** Four of today's defects (D1, D5, D6, and the original 3-of-131-topics) share one shape: a narrow view reported as complete. Each fix that only widens the view without making failures loud leaves the next one.

---

## 4. The plan

### Phase 0 — Unblock (do first, ~15 min)
- **0.1** Resolve D0. Diff stages 2 vs 3, keep one version of `verify_coms_windows.ps1`, `git add` it, commit the merge. Decide ASCII-no-BOM vs BOM explicitly and write the reason in the commit message. Do not force either.
- **0.2** Confirm `main` builds: `./coms learn` and `./coms check --agent subq` both run.

### Phase 1 — Make failure loud (~1h, highest value)
- **1.1 (D1)** In `cmd_check`, capture the inbox subscriber's exit status. On failure print to **stderr** `COMS: cannot reach broker <host>:<port> — inbox NOT read` and `return 1`. Keep "no messages" for the genuine empty case so the two are textually distinct.
- **1.2** Keep the notes index best-effort but label it: `notes index unavailable (broker timeout)` instead of silence.
- **1.3 (D5)** Quote the `cmd_learn` heredoc delimiter and interpolate deliberately (build dynamic lines into variables first).
- **1.4** Test each: `COMS_PORT=1 ./coms check` must exit non-zero and say the broker was unreachable; `./coms learn` must emit no stderr.

### Phase 2 — Data integrity (~1h)
- **2.1 (D2)** `register` upserts on `(host, worktree, agent)`: rewrite the file keeping the last row per key, then append. One-time cleanup of the existing file with the same script.
- **2.2 (D3)** `unregister` parses each line and compares `inbox` exactly; malformed lines are **kept**, not dropped.
- **2.3 (D4)** `send` refuses `--retain` on `inbox/*` unless the topic's agent segment is `$AGENT`; `--force-retain` overrides with a printed warning.
- **2.4** Tests: register twice → distinct count unchanged; prefix-related inboxes → unregister one, other survives; retain to foreign inbox → refused.

### Phase 3 — Payload fidelity (~45 min)
- **3.1 (D6)** `send` switches to `-f <tmpfile>` above ~8 KB; never print `sent` unless `rc == 0`.
- **3.2 (D7)** Use `-f` for file-sourced payloads, or document the limitation.
- **3.3** `send --verify` reads back and compares a **hash**, printing `verified` or `MISMATCH` — never bare presence.

### Phase 4 — Windows confirmation (owner: Kilo, ~30 min)
- **4.1** Run the committed `verify_coms_windows.ps1` on `desktop-081g9oh` under **PS 5.1 and pwsh 7**.
- **4.2** Paste the full transcript into the PR — not a summary.
- **4.3** Keep-or-kill the plan on evidence: any FAIL becomes a defect, any SKIP states its reason.

### Phase 5 — Housekeeping
- **5.1 (D8)** `topics --json`.
- **5.2** Document the wildcard rule in help: `#` matches whole levels, so `inbox/#` never sees `notes/*`.
- **5.3** One owner per file, or accept that a merge will silently drop a fix.

---

## 5. Definition of done

1. D0 resolved — no unmerged paths, no conflict markers.
2. D1 fixed and demonstrated: unreachable broker → non-zero exit with a distinct message.
3. D2, D3, D4 fixed with tests that fail before the fix.
4. A Windows transcript exists in the PR from a Windows host, under both shells.
5. `COMS topics` and `COMS check` agree about what is on the bus.

## 6. What I will not claim

I will not say COMS works on Windows. I can say the Linux half is verified here, the Windows half is Kilo's report, and the plan above is what would make the difference checkable rather than asserted.
