"""Append-only call log for the swarm.

Every worker invocation appends a single JSON line to swarm_runs/_calls.jsonl.

Schema versioning (item 6, 2026-05-03):
    Each row carries a `"v"` field as the FIRST key.
        v="1": current schema (16 fields = 11 base + 5 imp-B audit-trail).
        v=missing: legacy pre-imp-B row; downstream parsers should default
                   imp-B fields to "" / 0 and treat ok/low_signal at face
                   value. Bump to "2" the next time we add or rename a
                   field. See SPEC.md §"Logging schema versioning".

Base schema (always present, v=1):
    v, ts_utc, engine, prompt_bytes, output_bytes, latency_s, returncode,
    ok, low_signal, error, run_dir, out_file, model, pr.

Audit-trail completeness fields (added in imp-B; backward-compat — older rows
omit them; readers must default to "" / 0):
    retry_count        : number of retries before this call (0 on first try)
    model_fingerprint  : actual model id reported by the API (e.g. deepseek
                         returns "deepseek-chat-v3-0324"); CLI engines leave
                         this empty since they don't expose it reliably.
    tokens_in          : prompt_tokens from API `usage` (0 if not provided)
    tokens_out         : completion_tokens from API `usage` (0 if not provided)
    transport_status   : HTTP status / "ok" / "timeout" / "closed-by-peer" /
                         "rc=<n>" — closes the "silent retry success" class
                         where original 504 + retry 200 looked ok=true.

`low_signal` flags suspicious calls. Triggers (item 4, 2026-05-03):
    - returncode != 0
    - output_bytes < 50  (process produced essentially no output)
    - output_bytes >= 50 BUT the output is a parseable JSON envelope
      lacking any substantive content (concerns / strengths /
      commentary_text / answer / summary / q1_per_class). Schema-valid
      `{"verdict":"COMMENT_ONLY"}`-style empty envelopes pass the
      byte-count gate but are still vacuous; this catches them and
      appends `empty_envelope` to the error string.
"""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LOG_DIR = REPO / "swarm_runs"
LOG_PATH = LOG_DIR / "_calls.jsonl"
_LOCK = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# Item 6 (2026-05-03): every JSONL row written from this version onward
# carries `"v": SCHEMA_VERSION` as the first field. Bump when adding or
# renaming a column. Missing `v` in a legacy row = pre-imp-B.
SCHEMA_VERSION = "1"


def _envelope_has_substance(raw: str) -> bool:
    """Return True if `raw` is either NOT a JSON object (no opinion) OR is
    a JSON object with at least one substantive field populated.

    Item 4 (2026-05-03): catches the schema-valid empty-envelope class
    where worker_runner emits `{"verdict":"COMMENT_ONLY", ...stub fields}`
    after a parse-failure or banner-only response. Such envelopes pass
    the >=50 byte gate but contain no signal.

    Conservative: if the output isn't JSON at all (e.g. a plain text
    review from a CLI engine), we assume substance and let the byte-
    count gate decide. Only JSON dicts get the substance check.

    Substantive fields (any one populated triggers True):
        concerns, strengths, commentary_text, answer, summary, q1_per_class
    """
    try:
        obj = json.loads(raw)
    except Exception:
        return True  # not JSON; rely on byte count alone
    if not isinstance(obj, dict):
        return True
    for k in ("concerns", "strengths", "commentary_text", "answer",
              "summary", "q1_per_class"):
        v = obj.get(k)
        if not v:
            continue
        if isinstance(v, list) and len(v) > 0:
            return True
        if isinstance(v, str) and len(v.strip()) > 20:
            return True
        if isinstance(v, dict) and len(v) > 0:
            return True
    return False


def log_call(*, engine: str, prompt_bytes: int, output_bytes: int,
             latency_s: float, returncode: int, error: str = "",
             run_dir: str = "", out_file: str = "", model: str = "",
             pr: int | None = None,
             retry_count: int = 0,
             model_fingerprint: str = "",
             tokens_in: int = 0,
             tokens_out: int = 0,
             transport_status: str = "",
             low_signal_override: bool | None = None,
             extra: dict | None = None) -> None:
    """Append one log entry. Never raises; failures swallowed.

    `low_signal_override`: if not None, replaces the default heuristic.
    Used by CallTimer to wire in the empty-envelope check (item 4)
    without re-deriving it from output_bytes here.
    """
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        default_low_signal = output_bytes < 50 or returncode != 0
        low_signal = (low_signal_override
                      if low_signal_override is not None
                      else default_low_signal)
        rec = {
            # Item 6: schema version FIRST. Legacy rows lack this key.
            "v": SCHEMA_VERSION,
            "ts_utc": _now(),
            "engine": engine,
            "model": model,
            "pr": pr,
            "prompt_bytes": prompt_bytes,
            "output_bytes": output_bytes,
            "latency_s": round(latency_s, 2),
            "returncode": returncode,
            "ok": returncode == 0 and output_bytes >= 50 and not low_signal,
            "low_signal": low_signal,
            "error": (error or "")[:500],
            "run_dir": run_dir,
            "out_file": out_file,
            # imp-B audit-trail completeness fields:
            "retry_count": int(retry_count or 0),
            "model_fingerprint": (model_fingerprint or "")[:200],
            "tokens_in": int(tokens_in or 0),
            "tokens_out": int(tokens_out or 0),
            "transport_status": (transport_status or ("ok" if returncode == 0 else f"rc={returncode}"))[:80],
        }
        if extra:
            rec.update({k: v for k, v in extra.items() if k not in rec})
        line = json.dumps(rec, ensure_ascii=False) + "\n"
        with _LOCK, LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line)
    except Exception as e:
        try:
            (LOG_DIR / "_calls.errors.txt").open("a", encoding="utf-8").write(
                f"{_now()} log_call failed: {e}\n"
            )
        except Exception:
            pass


class CallTimer:
    """Context manager for a swarm call. with CallTimer(...) as t: t.set_output(out).

    Audit-trail completeness fields (imp-B): set via set_retry_count,
    set_model_fingerprint, set_tokens, set_transport_status — or via direct
    attribute assignment. Defaults preserve backward compat (0 / "").
    """

    def __init__(self, *, engine: str, model: str = "", pr: int | None = None,
                 run_dir: str = "", out_file: str = "", prompt_bytes: int = 0,
                 retry_count: int = 0, model_fingerprint: str = "",
                 tokens_in: int = 0, tokens_out: int = 0,
                 transport_status: str = ""):
        self.engine = engine
        self.model = model
        self.pr = pr
        self.run_dir = run_dir
        self.out_file = out_file
        self.prompt_bytes = prompt_bytes
        self.output_bytes = 0
        self.returncode = 0
        self.error = ""
        self._t0 = 0.0
        # Item 4 (2026-05-03): keep a small slice of the raw output so
        # __exit__ can run the empty-envelope check. Capped at 8 KB —
        # plenty for the substance fields we look at, and avoids
        # ballooning memory on large CLI responses.
        self._raw: str = ""
        self._RAW_MAX = 8 * 1024
        # imp-B fields — top-level on the JSONL row, not buried in `extra`.
        self.retry_count = int(retry_count or 0)
        self.model_fingerprint = model_fingerprint or ""
        self.tokens_in = int(tokens_in or 0)
        self.tokens_out = int(tokens_out or 0)
        self.transport_status = transport_status or ""

    def __enter__(self) -> "CallTimer":
        self._t0 = time.time()
        return self

    def set_output(self, output) -> None:
        if isinstance(output, str):
            self.output_bytes = len(output.encode("utf-8", errors="replace"))
            # Truncate before stashing — see _RAW_MAX rationale in __init__.
            self._raw = output[:self._RAW_MAX] if output else ""
        elif isinstance(output, (bytes, bytearray)):
            self.output_bytes = len(output)
            try:
                self._raw = bytes(output[:self._RAW_MAX]).decode(
                    "utf-8", errors="replace")
            except Exception:
                self._raw = ""

    def set_rc(self, rc: int) -> None:
        self.returncode = rc

    def set_error(self, err: str) -> None:
        self.error = err

    # imp-B setters — explicit API; direct attr-set also supported.
    def set_retry_count(self, n: int) -> None:
        self.retry_count = int(n or 0)

    def set_model_fingerprint(self, fp: str) -> None:
        self.model_fingerprint = fp or ""

    def set_tokens(self, tokens_in: int = 0, tokens_out: int = 0) -> None:
        self.tokens_in = int(tokens_in or 0)
        self.tokens_out = int(tokens_out or 0)

    def set_transport_status(self, status: str) -> None:
        self.transport_status = status or ""

    def set_meta(self, meta: dict | None) -> None:
        """Bulk-apply a meta dict (as returned by api_consult.call_*).
        Recognised keys: model_fingerprint, tokens_in, tokens_out,
        transport_status. Unknown keys ignored (back-compat for callers
        that pre-date imp-B)."""
        if not meta:
            return
        if "model_fingerprint" in meta:
            self.set_model_fingerprint(meta.get("model_fingerprint") or "")
        if "tokens_in" in meta or "tokens_out" in meta:
            self.set_tokens(meta.get("tokens_in", 0), meta.get("tokens_out", 0))
        if "transport_status" in meta:
            self.set_transport_status(meta.get("transport_status") or "")
        if "retry_count" in meta:
            self.set_retry_count(meta.get("retry_count") or 0)

    def __exit__(self, exc_type, exc, tb) -> None:
        latency = time.time() - self._t0
        if exc_type is not None:
            self.error = self.error or f"{exc_type.__name__}: {exc}"
            if self.returncode == 0:
                self.returncode = -1

        # Item 4 (2026-05-03): empty-envelope detection. The legacy
        # heuristic flagged low_signal on byte count alone; a schema-
        # valid `{"verdict":"COMMENT_ONLY"}` stub passes the >=50 byte
        # gate but is just as vacuous as a 0-byte response. If the
        # output cleared the size gate but lacks substantive fields,
        # mark it low_signal anyway and append `empty_envelope` to the
        # error string (don't overwrite — preserves any pre-existing
        # error like a transport timeout that was retried away).
        low_signal_final: bool | None = None
        base_low = self.output_bytes < 50 or self.returncode != 0
        if not base_low and self._raw and not _envelope_has_substance(self._raw):
            low_signal_final = True
            tag = "empty_envelope"
            if self.error:
                if tag not in self.error:
                    self.error = f"{self.error}; {tag}"
            else:
                self.error = tag

        log_call(
            engine=self.engine, prompt_bytes=self.prompt_bytes,
            output_bytes=self.output_bytes, latency_s=latency,
            returncode=self.returncode, error=self.error,
            run_dir=self.run_dir, out_file=self.out_file,
            model=self.model, pr=self.pr,
            retry_count=self.retry_count,
            model_fingerprint=self.model_fingerprint,
            tokens_in=self.tokens_in,
            tokens_out=self.tokens_out,
            transport_status=self.transport_status,
            low_signal_override=low_signal_final,
        )
