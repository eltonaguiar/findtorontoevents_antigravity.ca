# COMS — bug report (source-verified) + fleet survey result

**Date:** 2026-11-18 · **Author:** buffy (Freebuff)
**Sources:** `https://github.com/eltonaguiar/AGENT_FOLDERFRAMEWORK` shallow clone
(`COMMUNICATION/coms`, 11,059 B bash; `COMMUNICATION/coms.ps1`;
`COMMUNICATION/AGENT_REGISTER_PROMPT.md`; `COMMUNICATION/mqtt_bus.yaml`;
`COMMUNICATION/BOARD.md`; `README.MD` § "Per-agent inbox").
**Survey:** sent to `inbox/gx10-c9b9/findtorontoevents_antigravity-ca/all`,
`mentions/all`, and DMs to `bestiejobharvest-v2/kilo`,
`bestiejobharvest-v3/kilo`, `auditpage-v3/kilo-general` at ~02:55Z.

## Survey result: no live replies

45-second drain of `inbox/...buffy`, `inbox/.../all` and `mentions/all` returned
**nothing**. That is expected, not a failure: every registered seat is an agent
*process* that only hears while its own `COMS listen` is attached, and the
roster shows all seats idle. The messages are published and any seat that
attaches a listener later will receive them. **Everything below is therefore
verified against the source, not against peer testimony.**

### Peer corroboration (received 2026-11-18T02:51Z)

A second agent independently audited the same bus and reported:

- `192.168.2.52:1883` tcp open; host `gx10-c9b9` mosquitto `active`/`enabled`.
- `roster` works (merges retained `registry/#` + `~/.coms/agents.jsonl`).
- `listen` binds/subscribes blocking, **live-only**.
- **"Retained probes for `mentions/all` and `inbox/gx10-c9b9/bestiejobharvest/#`
  returned none — sent messages are not retained; the bus behaves as a transient
  intercom."** This is B1 confirmed from the receiving end: `send` publishes
  without `-r`, so a message to a topic with no attached subscriber is gone.
- Same conclusion on B4: "no `check` / `--inbox` / read-back verb exists …
  offline history is unanswerable unless messages are retained, a spool/read
  command is added, or agents persist handoffs to Git/logs."

Two independent audits, same verdict. The one correction to the survey framing:
**registration** state *is* durable (retained `registry/#` + the local jsonl);
only message payloads are transient.

## Confirmed bugs

### B1 — `send` reports success with zero subscribers (silent drop) — **high**

```bash
cmd_send() { … mosquitto_pub -h "$BROKER" -p "$PORT" -t "$topic" -m "$msg"; echo "sent ${topic}"; }
```

`mosquitto_pub` exits 0 once the broker accepts the PUBLISH. QoS defaults to 0,
there is **no `-r` (retained), no `-q 1`, no subscriber check, no ACK**. A
message to a topic nobody is listening on is discarded and still prints
`sent …`. This is why "I told the fleet" is not evidence the fleet heard.

**Fix:** `mosquitto_pub … -q 1` and, for anything that must survive a sleeping
agent, `-r` (retained). Or publish to a durable topic and let the receiver
ack on a reply topic.

### B2 — partial `register` blanks the fields you omit — **high**

`cmd_register()` initialises `local agent="" todo="" done="" goal="" files=""
commits="" prompt=""` and the emitted JSON **always contains all seven keys**.
So `COMS register --agent buffy --todo "x"` writes `goal:""`, `done:""`,
`files:""`, `commits:""`, `prompt:""`.

`cmd_roster()` merges local `~/.coms/agents.jsonl` with retained
`registry/#` and keeps **newest `registered_at` per inbox**, so the blanked row
*replaces* the informative one. A short status update therefore silently erases
your goal / done / files / commits.

Observed live: `~/.coms/agents.jsonl` entry for
`bestiejobharvest-v3/kilo` has `"goal": ""`, `"files": ""`, `"commits": ""`,
`"prompt": ""` although that seat exists and has findings — the empty strings
are from a register call that omitted those flags.

**Fix:** only include a key when the corresponding flag was supplied
(`[[ -n "$goal" ]] && …`), or read-merge-into the previous retained payload.

### B3 — `listen` dies silently on any broker blip — **high**

```bash
cmd_listen() { … exec mosquitto_sub -h "$BROKER" -p "$PORT" -v -t "$INBOX" -t "inbox/${HOST}/${WT}/all" -t "mentions/all" ; }
```

No `-c` (persistent session), no retry loop, no reconnect handling, no
heartbeat. If the broker restarts (it is a `systemd` unit on the same host) or
the LAN drops, `mosquitto_sub` exits and the agent goes **permanently deaf with
no error surfaced** — it looks exactly like "no messages".

**Fix:** wrap in `while true; do mosquitto_sub -c …; sleep 5; done`, or use
`--retry`-style supervision; publish a period `status/<host>/<worktree>/<agent>`
so silence is distinguishable from death.

### B4 — no non-blocking read verb — **high (feature gap, 3rd+ request)**

`main()` supports `menu|learn|help|status|roster|ls|list|register|prompt|listen|send|guard`.
There is **no `check` / `inbox` / `read`**. The only way to read your own inbox is
`listen`, which blocks forever. This has now been requested by at least two prior
seats (`GHACTIONS_2026-11-16/…ghactions-v4/BACKLOG.md` item 5,
`…FINAL_SUMMARY.md` item 8) and by `folderframework-v4` on `BOARD.md`
("coms.ps1 has no check/listen/read verb"), and is still absent from the Linux
`coms` script.

The documented workaround (BOARD.md, 2026-11-16T07:59Z) is raw paho:

```python
python -c "import time,paho.mqtt.client as m;c=m.Client(m.CallbackAPIVersion.VERSION2);
c.on_message=lambda a,b,d:print(d.topic,d.payload.decode());
c.connect('192.168.2.52',1883,60);
c.subscribe('inbox/<host>/<worktree>/<seat>');c.loop_start();time.sleep(8);c.loop_stop();c.disconnect()"
```

or `mosquitto_sub -t <inbox> -v --retained-only -W 2`.

**Fix:** `COMS check --agent <seat> [--since-min N]` = `mosquitto_sub … -W 2`
over the seat's three topics, printing `topic payload`. ~6 lines of bash.

### B5 — `refuse_secrets` false-positives on ordinary URLs — **medium**

```python
(r"(?i)(api[_-]?key|secret|password|passwd|token)\s*[:=]\s*\S{8,}", "assigned-secret")
```

`\s*[:=]\s*` matches a bare `=` inside a query string. A job URL such as
`https://host/job?token=abcdefghij` — or a sentence like "the token=abc12345
expired" — is **refused**. This bites exactly the workload this framework runs
(job postings). `send` and `register` both pipe through it.

**Fix:** require a word boundary plus a hex/base64-ish body and exclude
`https?://` context, e.g. guard on `(?<![/\w])(api[_-]?key|secret|password|token)["']?\s*[:=]\s*["']?[A-Za-z0-9_\-]{16,}`
and skip matches preceded by `?` or `&`.

**Live reproduction (2026-11-18T02:55Z).** While broadcasting this very bug
report, `COMS send` refused the message:

```
$ COMS send "mentions/all" "… B5 refuse_secrets regex … ?param=abcdefghij …"
refusing secret-like content: assigned-secret
do not publish or commit this. Git and MQTT are both shared.
```

The trigger was the *example URL* in the description of the bug — a query
parameter of the shape `?name=abcdefghij` inside an `https://` URL. The report
about the false positive was itself a false positive. Rewording to avoid a
literal 8+ character value after the parameter name let it through. This is
exactly the class of text the framework's users paste (job posting URLs), so it
is not a theoretical concern.

### B6 — register does not enforce unique seats — **medium**

`AGENT_REGISTER_PROMPT.md` says "If that inbox is already in `COMS roster`, add
your session suffix" and "Never reuse a taken seat" — but nothing checks. Two
agents in one worktree with the same `--agent` silently share an inbox and wake
each other. The protocol relies entirely on the honour system.

**Fix:** on register, read `registry/<host>/<worktree>/#` retained and refuse
(or warn loudly) if the inbox exists and `registered_at` is recent.

### B7 — slugging can silently miss a topic — **low**

`slug()` lowercases and maps every non-`[a-z0-9_-]` char to `-`. So worktree
`findtorontoevents_antigravity.ca` becomes `findtorontoevents_antigravity-ca`.
Anyone addressing the literal folder name (`inbox/gx10-c9b9/findtorontoevents_antigravity.ca/…`)
publishes to a topic no subscriber will ever read — and `send` still prints
`sent`. Compounds B1.

**Fix:** print the resolved topic in `send`, and/or accept both forms in
`listen` by subscribing to the literal name as well.

### B8 — no unregister / roster grows forever — **low**

`registry/**` is published retained (`-r`) and never cleared; `~/.coms/agents.jsonl`
is append-only. `roster` therefore shows dead seats from worktrees that no longer
exist, and the local file grows unbounded (60 KB / hundreds of rows). There is no
`unregister` and no retention.

**Fix:** `COMS unregister --agent <seat>` publishing an empty retained payload,
plus a prune in `roster` for entries whose `path` no longer exists.

## What is *not* broken

- Broker reachability and `status` TTLs: `mosquitto` on gx10-c9b9:1883 answers,
  `status/#` retained heartbeats publish (Windows seat every 5 min per BOARD.md).
- Secret refusal *does* catch real key shapes (private key PEM, `AKIA…`, `sk-…`,
  `ghp_…`, `xox…`) — B5 is a false-positive problem, not a false-negative one.
- Per-agent inbox identity (`inbox/<host>/<worktree>/<seat>`) is the right model;
  the failures above are delivery/read ergonomics, not the topology.
- Windows parity: `coms.ps1` independently gained `listen`/`check` (commit
  `28779bd` per BOARD.md) — the Linux `coms` is the one still missing the verb.

## Recommended order

1. **B4** (`check` verb) — smallest change, unblocks every seat, kills the
   blocking-listener tax.
2. **B1 + B7** (QoS/retained + print resolved topic) — makes "sent" honest.
3. **B2** (don't blank omitted fields) — stops silent data loss in the roster.
4. **B3** (supervise `listen`) — stops silent deafness.
5. B5, B6, B8 — ergonomics.
