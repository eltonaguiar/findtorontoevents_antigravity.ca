import os
import posixpath
import re
import ssl
from datetime import datetime, timezone
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


def _iter_local_files(local_root: str, include_exts: set[str] | None, exclude_dirs: set[str]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for dirpath, dirnames, filenames in os.walk(local_root):
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
        for fn in filenames:
            if include_exts is not None:
                ext = os.path.splitext(fn)[1].lower()
                if ext not in include_exts:
                    continue
            local_path = os.path.join(dirpath, fn)
            rel = os.path.relpath(local_path, local_root)
            rel_posix = rel.replace("\\", "/")
            out.append((local_path, rel_posix))
    return out


def _filter_by_prefixes(files: list[tuple[str, str]], prefixes: list[str]) -> list[tuple[str, str]]:
    if not prefixes:
        return files
    norm = [p.strip().replace("\\", "/").strip("/") for p in prefixes if p.strip()]
    if not norm:
        return files
    out: list[tuple[str, str]] = []
    for local_path, rel_posix in files:
        rel_norm = rel_posix.lstrip("/")
        if any(rel_norm == p or rel_norm.startswith(p + "/") for p in norm):
            out.append((local_path, rel_posix))
    return out


def _iter_local_files_from_list(local_root: str, rel_paths: list[str]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for rel in rel_paths:
        rel = rel.strip().replace("\\", "/").lstrip("/")
        if not rel:
            continue
        local_path = os.path.join(local_root, rel)
        if not os.path.isfile(local_path):
            raise FileNotFoundError(f"Missing local file: {local_path}")
        out.append((local_path, rel))
    return out


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


def _remote_exists(ftp: FTP_TLS, remote_path: str) -> bool:
    parent = posixpath.dirname(remote_path)
    name = posixpath.basename(remote_path)
    try:
        items = ftp.nlst(parent)
    except error_perm:
        return False
    for item in items:
        if item.rstrip("/") == (parent.rstrip("/") + "/" + name).rstrip("/"):
            return True
        if posixpath.basename(item.rstrip("/")) == name:
            return True
    return False


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


def backup_and_upload(
    *,
    host: str,
    user: str,
    password: str,
    remote_root: str,
    local_root: str,
    include_exts: set[str] | None,
    include_files: list[str] | None = None,
    include_prefixes: list[str] | None = None,
    backup_prefix: str = "backups",
) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    backup_root = posixpath.join(remote_root.rstrip("/"), backup_prefix, ts)

    context = ssl.create_default_context()
    ftp = FTP_TLS(context=context)
    ftp.connect(host, 21, timeout=60)
    ftp.login(user, password)
    ftp.prot_p()

    files: list[tuple[str, str]] = []
    if include_files:
        files.extend(_iter_local_files_from_list(local_root, include_files))

    walked = _iter_local_files(
        local_root,
        include_exts=include_exts,
        exclude_dirs={"node_modules", ".git", "backups"},
    )

    walked = _filter_by_prefixes(walked, include_prefixes or [])
    files.extend(walked)

    # Deduplicate by remote-relative path
    dedup: dict[str, str] = {}
    for local_path, rel_posix in files:
        dedup[rel_posix] = local_path
    files = [(lp, rp) for rp, lp in dedup.items()]

    for local_path, rel_posix in files:
        remote_path = posixpath.join(remote_root.rstrip("/"), rel_posix)
        backup_path = posixpath.join(backup_root, rel_posix)

        remote_dir = posixpath.dirname(remote_path)
        backup_dir = posixpath.dirname(backup_path)
        _ensure_remote_dir(ftp, remote_dir)
        _ensure_remote_dir(ftp, backup_dir)

        if _remote_exists(ftp, remote_path):
            try:
                data = _download_bytes(ftp, remote_path)
                _upload_bytes(ftp, backup_path, data)
            except Exception:
                # If a file can't be backed up, do not block deployment.
                pass

        with open(local_path, "rb") as f:
            ftp.storbinary(f"STOR {remote_path}", f)

    ftp.quit()
    return backup_root


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    env = _load_env(os.path.join(os.path.dirname(here), ".env"))

    host = env.get("FTP_HOST", "")
    user = env.get("FTP_USER", "")
    password = env.get("FTP_PASS", "")
    remote_root = env.get("FTP_ROOT", "")

    if not host or not user or not password or not remote_root:
        raise SystemExit("Missing FTP_HOST/FTP_USER/FTP_PASS/FTP_ROOT in .env")

    local_root = os.path.dirname(here)

    include_files_raw = (os.environ.get("INCLUDE_FILES") or env.get("INCLUDE_FILES") or "").strip()
    include_files = [p.strip() for p in include_files_raw.split(",") if p.strip()]

    include_prefixes_raw = (os.environ.get("INCLUDE_PREFIXES") or env.get("INCLUDE_PREFIXES") or "").strip()
    include_prefixes = [p.strip() for p in include_prefixes_raw.split(",") if p.strip()]

    include = (os.environ.get("INCLUDE_EXTS") or env.get("INCLUDE_EXTS") or ".html,.htm").strip()
    include_exts = {("." + e.strip().lstrip(".")) for e in include.split(",") if e.strip()}

    backup_root = backup_and_upload(
        host=host,
        user=user,
        password=password,
        remote_root=remote_root,
        local_root=local_root,
        include_exts=None if include_files else include_exts,
        include_files=include_files or None,
        include_prefixes=include_prefixes or None,
    )

    print(f"Backup created at: {backup_root}")


if __name__ == "__main__":
    main()
