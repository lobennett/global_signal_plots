"""Serialize per-scan metric rows to the standardized <tool>_metrics.tsv."""
from __future__ import annotations

from pathlib import Path
from contextlib import contextmanager
import errno
import os
import shutil
import tempfile

import pandas as pd

KEY_COLS = ["subject", "session", "task", "run"]
ACL_XATTR = "system.posix_acl_access"
_NO_ACL_ERRNOS = (errno.ENODATA, errno.ENOTSUP, errno.EOPNOTSUPP)


def read_access_acl(path) -> bytes | None:
    """Return a file's POSIX access ACL, or None when it carries none.

    Platforms and filesystems without POSIX ACL extended attributes report
    None; their access is described by the mode bits alone.
    """
    if not hasattr(os, "getxattr"):
        return None
    try:
        return os.getxattr(path, ACL_XATTR)
    except OSError as exc:
        if exc.errno in _NO_ACL_ERRNOS:
            return None
        raise


@contextmanager
def staged_outputs(paths: list[Path]):
    """Build outputs beside their destinations, then replace with rollback.

    A prior product's owner, group, mode bits and POSIX access ACL are
    reproduced on both its staged replacement and its rollback backup before
    any replacement; nothing is published if that cannot be done.

    Each rename is atomic, but multiple files are not a crash-safe transaction.
    Callers must serialize runs targeting the same paths.
    """
    def preserve_access(source, target):
        original = source.stat()
        current = target.stat()
        if (original.st_uid, original.st_gid) != (current.st_uid, current.st_gid):
            os.chown(target, original.st_uid, original.st_gid)
        shutil.copymode(source, target)
        acl = read_access_acl(source)
        if acl is not None:
            os.setxattr(target, ACL_XATTR, acl)
        elif read_access_acl(target) is not None:
            os.removexattr(target, ACL_XATTR)

    paths = [Path(path).resolve() for path in paths]
    if len(set(paths)) != len(paths):
        raise ValueError("TSV and PDF output paths must be distinct")
    directories = []
    staged, backups, published = [], {}, []
    cleanup = True
    try:
        for path in paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            directory = Path(tempfile.mkdtemp(prefix=".gs-", dir=path.parent))
            directories.append(directory)
            staged.append(directory / f"new{path.suffix}")
            if path.exists():
                backup = directory / "previous"
                shutil.copy2(path, backup)
                preserve_access(path, backup)
                backups[path] = backup
        yield staged
        for source, target in zip(staged, paths):
            if target in backups:
                preserve_access(backups[target], source)
        for source, target in zip(staged, paths):
            os.replace(source, target)
            published.append(target)
    except BaseException:
        try:
            for path in reversed(published):
                if path in backups:
                    os.replace(backups[path], path)
                else:
                    path.unlink()
        except OSError as exc:
            cleanup = False
            raise RuntimeError(
                f"Output rollback failed; recover prior products from {directories}"
            ) from exc
        raise
    finally:
        if cleanup:
            for directory in directories:
                shutil.rmtree(directory)


def write_metrics_tsv(rows: list[dict], out_path: Path) -> Path:
    """Write rows to a TSV with key columns first, metric columns after.

    An empty rows list still writes a header-only TSV with the key columns.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        pd.DataFrame(columns=KEY_COLS).to_csv(out_path, sep="\t", index=False)
        return out_path
    df = pd.DataFrame(rows)
    metric_cols = [c for c in df.columns if c not in KEY_COLS]
    df = df[KEY_COLS + metric_cols]
    df.to_csv(out_path, sep="\t", index=False)
    return out_path
