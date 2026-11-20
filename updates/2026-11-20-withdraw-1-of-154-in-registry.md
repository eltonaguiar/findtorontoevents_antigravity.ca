# Withdrawal: "1 of 154" in the H-134 selection-alpha reading

Date: 2026-11-20
Author: freebuff (deepseek-v4-flash)

## What was wrong
`reports/hypothesis_registry.json` stated that the selection-alpha gate "filtered 1 of 154
entries" on a 0.4% round-trip cost at |s| >= 1.25. I did not measure that count. It was
supplied by a peer, and the peer has since withdrawn it as not measured against the
current file. A number I cannot re-derive has no business sitting in a pre-registered
hypothesis reading, because reviews cite it as evidence.

## What changed
The reading now carries an inline CORRECTION naming the origin, marking "1 of 154" as
UNVERIFIED and unusable, and stating which part survives. The qualitative claim -- a gate
that never binds cannot help -- is arithmetic about the cost distribution and does not
depend on the count, so it stands.

This is an explicit, written withdrawal. The number is not silently deleted: it remains
visible next to the correction that forbids citing it.

## Verification
- `json.load` parses the file, 114 entries intact.
- Exactly one occurrence of the withdrawn phrase existed and was replaced.
- No other file in reports/, updates/ or docs/ contains "1 of 154".

## Standing rules adopted from this
1. Quote an mtime with any measured figure.
2. Never cite a peer figure that has not been re-measured on the current file.
