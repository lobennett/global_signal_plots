"""Walk a BIDS/derivatives tree, compute per-scan global-signal metric rows."""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from global_signal_plots.discover import parse_bold_meta
from global_signal_plots.metrics import global_signal_timeseries, summarize_gs

logger = logging.getLogger(__name__)

# Default targets echo-2 multi-echo BOLD. Both the session (``sub-*/ses-*/func``)
# and session-less (``sub-*/func``) layouts are scanned so single-session
# datasets are not silently missed. Override on the CLI for other layouts.
DEFAULT_GLOBS = (
    "sub-*/ses-*/func/*echo-2*bold.nii.gz",
    "sub-*/func/*echo-2*bold.nii.gz",
)
# Back-compat: the primary (session) pattern, still importable as DEFAULT_GLOB.
DEFAULT_GLOB = DEFAULT_GLOBS[0]


def _iter_bold_paths(root: Path, glob) -> list[Path]:
    """Resolve one glob string or an iterable of them; dedupe + sort the union."""
    patterns = (glob,) if isinstance(glob, str) else tuple(glob)
    paths = {p for pattern in patterns for p in Path(root).glob(pattern)}
    return sorted(paths)


def collect_traces(root: Path, glob=DEFAULT_GLOBS) -> list[tuple[dict, np.ndarray]]:
    """Return ``[(meta, gs_trace)]`` for each matched BOLD file.

    Each file's global-signal trace is computed exactly once here so it can be
    shared between the metrics TSV and the PDF (no double I/O). A file that
    fails to load is logged and skipped, so one corrupt/unreadable NIfTI never
    aborts the whole run -- finding bad scans is the point of the tool.
    """
    root = Path(root)
    traces: list[tuple[dict, np.ndarray]] = []
    for path in _iter_bold_paths(root, glob):
        try:
            gs = global_signal_timeseries(path)
        except Exception as exc:  # noqa: BLE001 - resilience over a bad file
            logger.warning("skipping unreadable BOLD file %s: %s", path, exc)
            continue
        traces.append((parse_bold_meta(path.name), gs))
    return traces


def rows_from_traces(traces: list[tuple[dict, np.ndarray]]) -> list[dict]:
    """Build standardized metric rows from collected (meta, trace) pairs."""
    rows: list[dict] = []
    for meta, gs in traces:
        rows.append({
            "subject": meta["subject"],
            # a missing ses- entity -> empty string, not None, for a clean TSV
            "session": meta["session"] or "",
            "task": meta["task"],
            "run": meta["run"],
            **summarize_gs(gs),
        })
    return rows


def scan_bold(root: Path, glob=DEFAULT_GLOBS) -> list[dict]:
    """Return one metric row per matched BOLD file (key entities + GS summary)."""
    return rows_from_traces(collect_traces(root, glob=glob))
