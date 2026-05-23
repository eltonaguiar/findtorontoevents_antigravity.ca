"""SQLite-backed session sidecar for the swarm.

Goal: persist enough state per (engine x prompt) so a follow-up turn can be
issued via one of three modes:

1. **Native** — the underlying CLI/API has a real session id (claude `--resume`,
   some engines via `cli_session_id` field). We just store it and pass it back.
2. **JSONL replay** — for stateless APIs (deepseek/cerebras/xai/inception), we
   replay the message log via `replay_messages()` and prepend it to the next
   prompt as `messages=[...]`.
3. **MD-context fallback** — when no session id and no API replay path exists
   (CLI engines without resume support), `render_md_context()` produces a
   compressed markdown preamble suitable for `worker_runner.py --context-md`.

Schema is created lazily on first call (idempotent `CREATE TABLE IF NOT EXISTS`).
WAL mode is enabled so concurrent swarm workers can write without lock storms.

DB path: `<repo>/swarm_runs/_sessions.db`.

CLI usage (ops):

    python tools/swarm/session_manager.py list [--engine X] [--since-hours 24]
    python tools/swarm/session_manager.py show <session_id>
    python tools/swarm/session_manager.py expire [--hours 72]
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import sqlite3
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
DB_PATH = REPO / "swarm_runs" / "_sessions.db"

_UTC_FMT = "%Y-%m-%dT%H:%M:%SZ"


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime(_UTC_FMT)


def _connect(db_path: Path | str | None = None) -> sqlite3.Connection:
    p = Path(db_path) if db_path else DB_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    return conn


@contextlib.contextmanager
def get_connection(db_path: Path | str | None = None):
    """Context manager: open a connection, yield it, close on exit.
    All functions in this module call `with get_connection(...) as conn:`
    rather than managing the connection lifecycle manually, ensuring
    that every code path — success, exception, early return — closes the
    connection. Without this, `sqlite3.ProgrammingError: closed` fires on
    any second call within the same process.
    """
    conn = _connect(db_path)
    try:
        yield conn
    finally:
        conn.close()


def init_db(db_path: Path | str | None = None) -> None:
    """Create tables/indices on first call. Idempotent. Enables WAL."""
    with _connect(db_path) as conn:
        try:
            conn.execute("PRAGMA journal_mode=WAL")
        except sqlite3.DatabaseError:
            pass
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                engine TEXT NOT NULL,
                model TEXT,
                created_utc TEXT NOT NULL,
                last_used_utc TEXT NOT NULL,
                prompt_bytes INTEGER,
                prompt_sha256 TEXT,
                cli_session_id TEXT,
                status TEXT,
                metadata_json TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL REFERENCES sessions(session_id),
                ts_utc TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                output_bytes INTEGER DEFAULT 0,
                latency_s REAL DEFAULT 0.0
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_engine_status ON sessions(engine, status)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_session_msgs ON messages(session_id, id)"
        )
        conn.commit()


def new_session(
    engine: str,
    prompt: str,
    *,
    model: str = "",
    cli_session_id: str = "",
    metadata: dict | None = None,
    db_path: Path | str | None = None,
) -> str:
    """Insert a fresh session row, return the generated session_id (UUID4)."""
    init_db(db_path)
    sid = str(uuid.uuid4())
    now = _now_utc()
    pbytes = len(prompt.encode("utf-8")) if prompt else 0
    psha = (
        hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        if prompt
        else ""
    )
    meta_json = json.dumps(metadata or {}, ensure_ascii=False)
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO sessions "
            "(session_id, engine, model, created_utc, last_used_utc, "
            "prompt_bytes, prompt_sha256, cli_session_id, status, metadata_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (sid, engine, model or "", now, now,
             pbytes, psha, cli_session_id or "", "active", meta_json),
        )
        # First message = the originating user prompt.
        if prompt:
            conn.execute(
                "INSERT INTO messages "
                "(session_id, ts_utc, role, content, output_bytes, latency_s) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (sid, now, "user", prompt, pbytes, 0.0),
            )
        conn.commit()
    return sid


def record_message(
    session_id: str,
    role: str,
    content: str,
    *,
    output_bytes: int = 0,
    latency_s: float = 0.0,
    db_path: Path | str | None = None,
) -> None:
    """Append a message and bump last_used_utc on the parent session."""
    init_db(db_path)
    now = _now_utc()
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO messages "
            "(session_id, ts_utc, role, content, output_bytes, latency_s) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, now, role, content, int(output_bytes or 0), float(latency_s or 0.0)),
        )
        conn.execute(
            "UPDATE sessions SET last_used_utc = ? WHERE session_id = ?",
            (now, session_id),
        )
        conn.commit()


def update_session(
    session_id: str,
    *,
    status: str | None = None,
    cli_session_id: str | None = None,
    model: str | None = None,
    db_path: Path | str | None = None,
) -> None:
    """Patch select session columns."""
    init_db(db_path)
    sets, vals = [], []
    if status is not None:
        sets.append("status = ?")
        vals.append(status)
    if cli_session_id is not None:
        sets.append("cli_session_id = ?")
        vals.append(cli_session_id)
    if model is not None:
        sets.append("model = ?")
        vals.append(model)
    if not sets:
        return
    sets.append("last_used_utc = ?")
    vals.append(_now_utc())
    vals.append(session_id)
    with _connect(db_path) as conn:
        conn.execute(
            f"UPDATE sessions SET {', '.join(sets)} WHERE session_id = ?",
            vals,
        )
        conn.commit()


def get_session(
    session_id: str, db_path: Path | str | None = None
) -> dict[str, Any] | None:
    init_db(db_path)
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        return dict(row) if row else None


def list_active(
    engine: str | None = None,
    since_hours: float | None = None,
    db_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Return sessions with status='active', filtered by engine/since_hours."""
    init_db(db_path)
    where = ["status = 'active'"]
    params: list[Any] = []
    if engine:
        where.append("engine = ?")
        params.append(engine)
    if since_hours is not None:
        cutoff = (
            datetime.now(timezone.utc) - timedelta(hours=since_hours)
        ).strftime(_UTC_FMT)
        where.append("last_used_utc >= ?")
        params.append(cutoff)
    sql = (
        "SELECT * FROM sessions WHERE "
        + " AND ".join(where)
        + " ORDER BY last_used_utc DESC"
    )
    with _connect(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def expire_older_than(
    hours: float = 72.0, db_path: Path | str | None = None
) -> int:
    """Mark active sessions older than `hours` as expired. Return count."""
    init_db(db_path)
    cutoff = (
        datetime.now(timezone.utc) - timedelta(hours=hours)
    ).strftime(_UTC_FMT)
    with _connect(db_path) as conn:
        cur = conn.execute(
            "UPDATE sessions SET status = 'expired' "
            "WHERE status = 'active' AND last_used_utc < ?",
            (cutoff,),
        )
        conn.commit()
        return cur.rowcount or 0


def replay_messages(
    session_id: str, db_path: Path | str | None = None
) -> list[dict[str, str]]:
    """Return [{role, content}, ...] in chronological order for API replay.

    Suitable for stuffing into an OpenAI-style `messages=[...]` payload.
    """
    init_db(db_path)
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages "
            "WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        ).fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in rows]


def render_md_context(
    session_id: str,
    *,
    max_chars: int = 4000,
    db_path: Path | str | None = None,
) -> str:
    """Compress prior messages into a Markdown preamble.

    Newest messages get full text; older ones are tail-truncated. The result
    is capped at `max_chars` and ends with a separator so the next prompt can
    be appended cleanly.
    """
    msgs = replay_messages(session_id, db_path=db_path)
    if not msgs:
        return ""
    sess = get_session(session_id, db_path=db_path)
    header_lines = ["# Prior session context"]
    if sess:
        header_lines.append(
            f"_Session `{session_id}` · engine `{sess.get('engine')}` · "
            f"model `{sess.get('model') or '-'}` · "
            f"started `{sess.get('created_utc')}`_"
        )
    header_lines.append("")
    header = "\n".join(header_lines) + "\n"

    # Build from newest backwards so the most recent context is preserved
    # when we hit the budget.
    budget = max(512, max_chars - len(header) - 64)
    blocks: list[str] = []
    used = 0
    for m in reversed(msgs):
        role = m["role"].upper()
        content = m["content"] or ""
        # Soft per-block cap so a single huge message can't eat the budget.
        per_cap = min(2000, max(256, budget // 2))
        if len(content) > per_cap:
            content = content[: per_cap - 20] + "\n…(truncated)"
        block = f"## {role}\n\n{content}\n"
        if used + len(block) > budget:
            break
        blocks.append(block)
        used += len(block)
    blocks.reverse()
    body = "\n".join(blocks)
    return header + body + "\n---\n"


# ---------------------------------------------------------------- CLI ops ---


def _print_table(rows: list[dict[str, Any]], cols: list[str]) -> None:
    if not rows:
        print("(no rows)")
        return
    widths = {c: max(len(c), max(len(str(r.get(c) or "")) for r in rows)) for c in cols}
    print("  ".join(c.ljust(widths[c]) for c in cols))
    print("  ".join("-" * widths[c] for c in cols))
    for r in rows:
        print("  ".join(str(r.get(c) or "").ljust(widths[c]) for c in cols))


def _cmd_list(args: argparse.Namespace) -> int:
    rows = list_active(engine=args.engine, since_hours=args.since_hours)
    if getattr(args, "json", False):
        # Force utf-8 stdout to dodge cp1252 crashes on Windows when
        # metadata contains non-ASCII chars.
        try:
            sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except Exception:
            pass
        emit: list[dict[str, Any]] = []
        for r in rows:
            row = dict(r)
            # Parse metadata_json from raw string into dict so callers can
            # read out_file etc. without re-parsing.
            raw_meta = row.get("metadata_json")
            if isinstance(raw_meta, str) and raw_meta:
                try:
                    row["metadata_json"] = json.loads(raw_meta)
                except (json.JSONDecodeError, TypeError):
                    # Leave the raw string in place so callers can still see it.
                    pass
            elif raw_meta is None:
                row["metadata_json"] = {}
            emit.append({
                "session_id": row.get("session_id"),
                "engine": row.get("engine"),
                "model": row.get("model"),
                "status": row.get("status"),
                "created_utc": row.get("created_utc"),
                "last_used_utc": row.get("last_used_utc"),
                "prompt_bytes": row.get("prompt_bytes"),
                "prompt_sha256": row.get("prompt_sha256"),
                "cli_session_id": row.get("cli_session_id"),
                "metadata_json": row.get("metadata_json"),
            })
        json.dump(emit, sys.stdout, ensure_ascii=False, indent=2, default=str)
        sys.stdout.write("\n")
        return 0
    cols = ["session_id", "engine", "model", "status",
            "created_utc", "last_used_utc", "prompt_bytes"]
    _print_table(rows, cols)
    print(f"\n{len(rows)} active session(s).")
    return 0


def _cmd_show(args: argparse.Namespace) -> int:
    sess = get_session(args.session_id)
    if not sess:
        print(f"session not found: {args.session_id}", file=sys.stderr)
        return 2
    print(json.dumps(sess, indent=2, default=str))
    print("\n# Messages")
    for m in replay_messages(args.session_id):
        snippet = (m["content"] or "")[:200].replace("\n", " ")
        print(f"  [{m['role']:>9}] {snippet}")
    return 0


def _cmd_expire(args: argparse.Namespace) -> int:
    n = expire_older_than(hours=args.hours)
    print(f"expired {n} session(s) older than {args.hours}h")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")

    p_list = sub.add_parser("list", help="list active sessions")
    p_list.add_argument("--engine")
    p_list.add_argument("--since-hours", type=float, default=None)
    p_list.add_argument("--json", action="store_true",
                        help="emit JSON array (machine-readable; metadata_json parsed to dict)")
    p_list.set_defaults(func=_cmd_list)

    p_show = sub.add_parser("show", help="show session detail + messages")
    p_show.add_argument("session_id")
    p_show.set_defaults(func=_cmd_show)

    p_exp = sub.add_parser("expire", help="mark old active sessions expired")
    p_exp.add_argument("--hours", type=float, default=72.0)
    p_exp.set_defaults(func=_cmd_expire)

    args = ap.parse_args(argv)
    if not args.cmd:
        # Default: list.
        return _cmd_list(argparse.Namespace(engine=None, since_hours=None, json=False))
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
