"""Peek Redis agent bus: status + inbox + broadcast (does not trim inbox)."""
import json
import sys

import redis


def _txt(blob):
    if blob is None:
        return ""
    if isinstance(blob, str):
        return blob
    return blob.decode("utf-8", errors="replace")


def main() -> int:
    agent = sys.argv[1] if len(sys.argv) > 1 else "cursor-audit-quant"
    r = redis.Redis(host="localhost", port=6379, decode_responses=False)
    r.ping()

    print("=== agent:%s:status ===" % agent)
    st = r.hgetall("agent:%s:status" % agent)
    if not st:
        print(" (empty)")
    else:
        for k, v in sorted(st.items()):
            print(" ", _txt(k), ":", _txt(v)[:240])

    print()
    print("=== agent:%s:inbox (peek, not cleared) ===" % agent)
    inbox = r.lrange("agent:%s:inbox" % agent, 0, 4)
    if not inbox:
        print(" (empty)")
    for b in inbox:
        print(" ", _txt(b)[:900])

    print()
    print("=== bus:broadcast:log (12 latest) ===")
    for i, b in enumerate(r.lrange("bus:broadcast:log", 0, 11)):
        s = _txt(b)
        try:
            j = json.loads(s)
            body = (j.get("body") or "")[:700].replace("\n", " ")
            print("[%d] %s %s" % (i, j.get("from", "?"), j.get("timestamp", "?")))
            print("   ", body)
        except Exception:
            print("[%d] raw: %s" % (i, s[:480]))
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
