# R01 round-open fill — verdict

**Checked:** 2026-11-23T10:31:00.795344+00:00  ·  **Open:** 2026-11-23T14:30:00Z  ·  **Fill waiter:** alive
**Verdict:** `REFUSED_PRE_OPEN` — the tool refused: no instrument had a bar at or after the round start. This is a refusal, not a result.

- artefact: `reports/r01_round_open_fill_2026-11-23.json` (status `NOT_OPEN_YET`, generated `2026-11-23T09:49:48Z`)
- filled rows: **0**
- instruments listed in the artefact: 25

## Waiter log (last lines)
```
[waiter] 2026-11-23T10:19:24.216025+00:00 target 2026-11-23T14:32:00+00:00 wait 252.6 min
[waiter] 2026-11-23T10:24:24.216180+00:00 247.6 min to go
[waiter] 2026-11-23T10:29:24.216339+00:00 242.6 min to go
```

A verdict of `REFUSED_PRE_OPEN` after 14:35Z is itself a finding: it would mean the feed still had no bar for the round start, not that the fill was skipped.
