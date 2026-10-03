"""Tenant-scoped immutable file storage (filesystem only)."""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import BinaryIO

MAX_FILE_BYTES = 10 * 1024 * 1024


def store_upload(
    stream: BinaryIO | Iterable[bytes],
    tenant_id: str,
    data_dir: str | Path,
    *,
    max_bytes: int = MAX_FILE_BYTES,
) -> tuple[Path, str, int]:
    """Stream to a temporary file, enforce the cap, then atomically publish by hash."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", tenant_id):
        raise ValueError("invalid_tenant_id")
    root = Path(data_dir) / "files" / tenant_id
    root.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".upload-", suffix=".tmp", dir=root)
    temp_path = Path(temp_name)
    digest = hashlib.sha256()
    size = 0
    try:
        with os.fdopen(fd, "wb") as target:
            chunks = (
                iter(lambda: stream.read(1024 * 1024), b"")
                if hasattr(stream, "read")
                else iter(stream)
            )
            for chunk in chunks:
                if not isinstance(chunk, bytes):
                    raise TypeError("upload chunks must be bytes")
                size += len(chunk)
                if size > max_bytes:
                    raise ValueError("too_large")
                digest.update(chunk)
                target.write(chunk)
            target.flush()
            os.fsync(target.fileno())
        sha = digest.hexdigest()
        final_path = root / sha
        if final_path.exists():
            temp_path.unlink()
        else:
            os.replace(temp_path, final_path)
        return final_path, sha, size
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise


def cleanup_temporary_files(data_dir: str | Path, *, older_than_seconds: int = 0) -> int:
    """Remove abandoned .upload-*.tmp files below DATA_DIR/files."""
    base = Path(data_dir) / "files"
    if not base.exists():
        return 0
    import time

    cutoff = time.time() - older_than_seconds
    removed = 0
    for path in base.glob("**/.upload-*.tmp"):
        try:
            if path.stat().st_mtime <= cutoff:
                path.unlink()
                removed += 1
        except FileNotFoundError:
            pass
    return removed
