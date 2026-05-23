"""Feature-flag manager backed by a JSON config file.

All public methods are thread-safe (RLock).  Reads use a snapshot model:
the flag dict is copied under the lock and the copy is returned, so callers
never hold the lock while doing slow work.

``reload()`` uses mtime + content-hash so same-second writes that actually
change content are still detected.
"""

from __future__ import annotations

import json
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional


class FeatureFlagManager:
    """JSON-backed feature flag manager.

    Parameters
    ----------
    path : str | Path
        Path to the JSON file containing the flag definitions.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._lock = threading.RLock()
        self._mtime: float = 0.0
        self._content_hash: int = 0
        self._flags: Dict[str, Any] = {}
        self._load()

    # ── public API ──────────────────────────────────────────────────

    def is_enabled(self, flag_name: str) -> bool:
        """Return ``True`` if the flag exists and is truthy."""
        with self._lock:
            val = self._flags.get(flag_name)
        return bool(val)

    def get(self, flag_name: str, default: Any = None) -> Any:
        """Return the value of *flag_name*, or *default* if missing."""
        with self._lock:
            return deepcopy(self._flags.get(flag_name, default))

    def set_flag(self, flag_name: str, value: Any) -> None:
        """Set *flag_name* to *value* and persist to disk atomically."""
        with self._lock:
            self._flags[flag_name] = value
            self._write_unlocked()

    def reload(self) -> bool:
        """Re-read the file if it changed on disk.

        Returns ``True`` when the in-memory state was updated.
        """
        try:
            stat = self._path.stat()
        except FileNotFoundError:
            return False

        with self._lock:
            if stat.st_mtime == self._mtime:
                # Same mtime — fall back to content hash to catch
                # same-second writes that actually changed content.
                raw = self._path.read_text()
                if hash(raw) == self._content_hash:
                    return False
                return self._parse(raw)
            return self._load_unlocked()

    def list_flags(self) -> Dict[str, Any]:
        """Return a shallow copy of all flags."""
        with self._lock:
            return dict(self._flags)

    def diff(self) -> Dict[str, List[str]]:
        """Compare on-disk file to in-memory state.

        Returns a dict with keys ``added``, ``removed``, ``changed``.
        """
        with self._lock:
            raw = self._path.read_text()
            try:
                disk_flags: Dict[str, Any] = json.loads(raw)
            except json.JSONDecodeError:
                return {"added": [], "removed": [], "changed": []}

            mem_keys = set(self._flags)
            disk_keys = set(disk_flags)

            added = sorted(disk_keys - mem_keys)
            removed = sorted(mem_keys - disk_keys)
            changed = sorted(
                k for k in mem_keys & disk_keys
                if self._flags[k] != disk_flags[k]
            )
            return {"added": added, "removed": removed, "changed": changed}

    # ── internals ───────────────────────────────────────────────────

    def _load(self) -> None:
        """Initial load (called from ``__init__``)."""
        with self._lock:
            self._load_unlocked()

    def _load_unlocked(self) -> bool:
        """Load from disk.  Caller must hold ``_lock``."""
        raw = self._path.read_text()
        return self._parse(raw)

    def _parse(self, raw: str) -> bool:
        """Parse *raw* JSON string and update internal state.

        Caller must hold ``_lock``.
        """
        try:
            flags = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in {self._path}: {exc}") from exc

        self._flags = flags
        self._mtime = self._path.stat().st_mtime
        self._content_hash = hash(raw)
        return True

    def _write_unlocked(self) -> None:
        """Persist current flags to disk atomically.

        Caller must hold ``_lock``.
        """
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._flags, indent=2, ensure_ascii=False))
        tmp.replace(self._path)
        self._mtime = self._path.stat().st_mtime
        self._content_hash = hash(self._path.read_text())
