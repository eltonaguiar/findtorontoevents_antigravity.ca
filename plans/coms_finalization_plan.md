# COMS Finalization & Validation Plan (2026-11-20)

## Status Overview
The COMS framework has undergone significant stability improvements, culminating in the merge of PR #9 (`feat/coms-notes-visibility`). 

### Current Health
- **Linux**: Fully operational. `topics` subcommand, `notes/*` visibility, and `check` functionality are verified.
- **Windows**: Root causes for PS 5.1 argv-quoting and BOM-related parsing errors have been resolved. Round-trip payload verification (6KB+) is successful.
- **Infrastructure**: Broker is stable. The "temp-file" approach for `send` and `check` effectively bypasses shell-quoting limitations.

## Identified Remaining Bugs & Risks

### 1. Registry Upsert Logic (Priority: Medium)
- **Bug**: `register` appends to the local registry and publishes to MQTT, but doesn't effectively "upsert" existing seats in a way that prevents duplicate entries in the global roster.
- **Risk**: Inaccurate agent counts and fragmented status reports.
- **Fix**: Implement a cleaner "unregister-then-register" or a server-side (simulated) deduplication in the `roster` command.

### 2. Watch Task Exhaustion (Priority: Low)
- **Bug**: `coms-watch` tasks are self-disabling after reaching a 50-cycle limit.
- **Risk**: Agents stop waking up automatically.
- **Fix**: Implement a cycle-reset mechanism or increase the cap with a health-check heartbeat.

### 3. `cmd_learn` Heredoc Injection (Priority: Medium)
- **Bug**: The `learn` command uses an unquoted heredoc that could potentially execute arbitrary code if documentation contains specific shell sequences.
- **Risk**: Security vulnerability in the documentation-learning loop.
- **Fix**: Quote the heredoc (`<<'EOF'`) to ensure content is treated as a literal string.

### 4. Topic Naming Discipline (Priority: Low)
- **Bug**: Some agents (e.g., `hermes-deepseek-flash`) publish to topics without the canonical `prefix/` structure.
- **Risk**: Poluting the global namespace and breaking automated filtering.
- **Fix**: Enforce topic prefixes in the `send` command's validation logic.

## Testing Plan (The "Final Gauntlet")

To declare COMS "Production Ready," we will execute the following matrix:

| Test ID | Scenario | Success Criteria | Target |
| :--- | :--- | :--- | :--- |
| **T1** | **Cross-OS Roundtrip** | Linux `send` $\rightarrow$ Windows `check` $\rightarrow$ Windows `send` $\rightarrow$ Linux `check` (exact byte match) | Linux $\leftrightarrow$ Win |
| **T2** | **Stress Payload** | Send 500KB+ payload (large log) via temp-file method; verify no truncation | Both |
| **T3** | **Notes Indexing** | Create 10 `notes/<slug>` entries; verify `COMS check` lists all 10 with correct sizes | Both |
| **T4** | **Concurrent Register** | Register 3 agents simultaneously; verify `roster` shows 3 distinct seats | Both |
| **T5** | **Tombstone Test** | `unregister` an agent; verify the retained MQTT topic is cleared immediately | Both |
| **T6** | **BOM/ASCII Check** | Run `verify_coms_windows.ps1` on a fresh PS 5.1 instance; verify 0 parsing errors | Windows |

## Execution Roadmap

1. **Immediate**: Publish this plan via COMS.
2. **Phase 1 (Fixes)**: Patch `cmd_learn` quoting and `register` upsert logic.
3. **Phase 2 (Validation)**: Execute the "Final Gauntlet" tests.
4. **Phase 3 (Wrap)**: Update `AGENTCOMMS.txt` with the final verified version and close the COMS modification chapter.

## Communication Protocol
I will poll `mentions/all` and my `inbox` every 10 minutes. I will reply to any blocks or suggestions regarding this plan immediately via COMS.
