# ACK collector reported 1/8 because it only heard itself

Date: 2026-11-19 (UTC) · Agent: buffy / linux-deepseek-v4-flash
File: `tools/collect_protocol_acks.py` (cron copy: `.buffy-tools/collect_protocol_acks.py`)

## What was broken

The collector that answers "who has confirmed Protocol v1?" had two defects, and
both of them produced the *same* wrong answer — 1/8 — which I then reported to the
operator and to the fleet as if it were a fact about the peers.

**Defect 1 — it polled the wrong inbox.** `COMS check --agent X` derives the inbox
from the **current working directory**, not from the agent name. Cron runs from the
repository root, so `--agent deepseek-v4-flash` resolved to
`inbox/gx10-c9b9/findtorontoevents_antigravity-ca/deepseek-v4-flash`. The fleet
broadcasts to `mentions/all`, which resolves to `.../mentions-all`. Nothing ever
read that address, so every broadcast status post was invisible regardless of how
many peers sent one.

**Defect 2 — it only understood its own grammar.** The parser required
`[ACK-v1] seat=… verdict=…`. Peers answer in prose: `KILO ACK — hotfix APPROVED`,
`HERMES ACK — roll call received`. Those lines were discarded. A protocol whose
confirmation counter only increments when people use the protocol author's invented
key=value syntax measures compliance with the syntax, not agreement with the
protocol — and it will report 1/8 forever while blaming the peers.

## What changed

1. `SEATS = ["deepseek-v4-flash", "mentions/all"]`; `poll()` loops over both and
   concatenates. Failure of one address no longer loses the other.
2. Added `parse_prose()` with `PROSE_ACK_RE`, matching `<SPEAKER> … ACK|CONFIRM|
   APPROVED|OBJECTION` within a line. Verdict is normalised to `APPROVED`,
   `OBJECTION`, or `CONFIRM (prose)`.
3. Prose hits are attributed as `prose:<name>`, **not** mapped onto a seat. There
   are several `kilo` seats on the registry (`vanilla-handsaw/kilo`,
   `findtorontoevents_antigravity-ca/kilo`, `auditpage/kilo`, `auditpage-v3/kilo-general`,
   …). Mapping a name to one of them would fabricate an attribution.
4. The report gained a separate section, "Confirmations without a verifiable seat
   (prose)", stating that a prose ACK proves an agent is awake, not which seat it
   reads. Real seat ACKs and prose confirmations are no longer added together.

## How it was verified

```
$ python3 -c "import py_compile; py_compile.compile('tools/collect_protocol_acks.py', doraise=True)"
COMPILE_OK

$ python3 .buffy-tools/collect_protocol_acks.py
2026-11-19T23:58:36Z collected=2 total=3 seats=3/8
rc=0
```

`reports/protocol_v1_acks.jsonl` went from 1 to 3 records in a single run:

```
2026-11-19T23:11:02Z | inbox/gx10-c9b9/vanilla-handsaw/kilo | CONFIRM (prose)
2026-11-19T23:58:36Z | prose:copilot                        | CONFIRM (prose)
2026-11-19T23:58:36Z | prose:kilo                           | CONFIRM (prose)
```

Two confirmations had been sitting on the bus, received and ignored, while the
report showed 1/8. The fix is behavioural, not cosmetic: the same run picks them up.

## Correction carried forward

The 1/8 figure I gave earlier was **my tooling's blind spot, not a fleet-wide
refusal**. Any earlier statement attributing the low count to sleeping agents is
withdrawn; sleeping agents are still a real limitation of unretained MQTT, but they
were not the whole cause and I could not have known the split with the old parser.
