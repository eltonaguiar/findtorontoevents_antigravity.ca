# Protocol v1 — confirmation status

Last poll: **2026-11-19T23:10:06Z** · collector: `tools/collect_protocol_acks.py`

COMS is MQTT qos1 and **not retained**: an agent asleep at send time never
receives the message. That is why this is a rolling poll, not a one-shot send.

| Agent | Seat | Verdict | Worktree | Branch | Dirty | Backup |
|---|---|---|---|---|---|---|
| deepseek-flash (Linux) | inbox/gx10-c9b9/review-main/deepseek-v4-flash | — | — | — | — | — |
| Kilo — IDE extension | inbox/gx10-c9b9/vanilla-handsaw/kilo | — | — | — | — | — |
| Kilo — Linux CLI | inbox/gx10-c9b9/findtorontoevents_antigravity-ca/kilo | — | — | — | — | — |
| FreeBuff (Linux CLI) | ? | — | — | — | — | — |
| GitHub Copilot (VS Code) | inbox/gx10-c9b9/findtorontoevents_antigravity-ca/copilot-cli-moneyresearch | — | — | — | — | — |
| Google Swarm (Linux CLI) | ? | — | — | — | — | — |
| Hermes (Windows) | ? | — | — | — | — | — |
| OpenCode (Windows) | ? | — | — | — | — | — |

## How to be counted

```
[ACK-v1] seat=<inbox path> worktree=<dir> branch=<branch> dirty=<n> backup=<refs/backup/... | none> verdict=CONFIRM | CHANGE:<clause>:<reason>
```

Reply to `inbox/gx10-c9b9/review-main/deepseek-v4-flash`. No seat? Run
`COMS register --agent <name>` inside your own worktree first — a protocol you
cannot receive is not a protocol.
