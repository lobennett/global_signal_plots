"""Serialize per-scan metric rows to the standardized <tool>_metrics.tsv."""
from __future__ import annotations

from pathlib import Path
from contextlib import contextmanager
import os
import shutil
import tempfile

import pandas as pd

KEY_COLS = ["subject", "session", "task", "run"]


@contextmanager
def staged_outputs(paths: list[Path]):
    """Build outputs beside their destinations, then replace with rollback.

    Each rename is atomic, but multiple files are not a crash-safe transaction.
    Callers must serialize runs targeting the same paths.
    """
    def preserve_access(source, target):
        original = source.stat()
        current = target.stat()
        if (original.st_uid, original.st_gid) != (current.st_uid, current.st_gid):
            os.chown(target, original.st_uid, original.st_gid)
        shutil.copymode(source, target)

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
