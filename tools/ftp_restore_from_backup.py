import os
import posixpath
import ssl
from ftplib import FTP_TLS, error_perm


def _load_env(env_path: str) -> dict:
    env: dict[str, str] = {}
    if not os.path.exists(env_path):
        return env
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def _ensure_remote_dir(ftp: FTP_TLS, remote_dir: str) -> None:
    if remote_dir in ("", "/"):
        return
    parts = [p for p in remote_dir.split("/") if p]
    cur = ""
    for p in parts:
        cur = cur + "/" + p
        try:
            ftp.mkd(cur)
        except error_perm:
            pass


def _walk_remote_files(ftp: FTP_TLS, root: str) -> list[str]:
    """Recursively list files under a remote directory using MLSD if available."""
    files: list[str] = []

    def _recurse(d: str) -> None:
        try:
            entries = list(ftp.mlsd(d))
        except Exception:
            # MLSD not supported; best-effort fallback: NLST (no type info)
            try:
                entries = [(p, {"type": "unknown"}) for p in ftp.nlst(d)]
            except Exception:
                return

        for name, facts in entries:
            # MLSD: name is basename; NLST fallback: name may be full path
            if name in (".", ".."):  # safety
                continue
            if name.startswith(root) and name != root:
                full = name
            else:
                full = posixpath.join(d.rstrip("/"), name)

            t = (facts or {}).get("type")
            if t == "dir":
                _recurse(full)
            elif t == "file":
                files.append(full)
            else:
                # Unknown; try to treat as file first, then dir.
                try:
                    ftp.size(full)
                    files.append(full)
                except Exception:
                    _recurse(full)

    _recurse(root)
    return files


def _download_bytes(ftp: FTP_TLS, remote_path: str) -> bytes:
    buf: list[bytes] = []

    def _cb(chunk: bytes) -> None:
        buf.append(chunk)

    ftp.retrbinary(f"RETR {remote_path}", _cb)
    return b"".join(buf)


def _upload_bytes(ftp: FTP_TLS, remote_path: str, data: bytes) -> None:
    import io

    bio = io.BytesIO(data)
    ftp.storbinary(f"STOR {remote_path}", bio)


def restore_from_backup(*, host: str, user: str, password: str, remote_root: str, backup_ts: str) -> None:
    backup_root = posixpath.join(remote_root.rstrip("/"), "backups", backup_ts)

    context = ssl.create_default_context()
    ftp = FTP_TLS(context=context)
    ftp.connect(host, 21, timeout=60)
    ftp.login(user, password)
    ftp.prot_p()

    backup_files = _walk_remote_files(ftp, backup_root)
    if not backup_files:
        raise SystemExit(f"No files found under backup: {backup_root}")

    for src in backup_files:
        rel = src[len(backup_root):].lstrip("/")
        dest = posixpath.join(remote_root.rstrip("/"), rel)
        _ensure_remote_dir(ftp, posixpath.dirname(dest))
        data = _download_bytes(ftp, src)
        _upload_bytes(ftp, dest, data)

    ftp.quit()


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    env = _load_env(os.path.join(os.path.dirname(here), ".env"))

    host = env.get("FTP_HOST", "")
    user = env.get("FTP_USER", "")
    password = env.get("FTP_PASS", "")
    remote_root = env.get("FTP_ROOT", "")

    if not host or not user or not password or not remote_root:
        raise SystemExit("Missing FTP_HOST/FTP_USER/FTP_PASS/FTP_ROOT in .env")

    backup_ts = os.environ.get("BACKUP_TS", "").strip()
    if not backup_ts:
        raise SystemExit("Set BACKUP_TS to the backup timestamp folder name, e.g. 20260131-174912")

    restore_from_backup(host=host, user=user, password=password, remote_root=remote_root, backup_ts=backup_ts)
    print(f"Restored from /backups/{backup_ts} to {remote_root}")


if __name__ == "__main__":
    main()
