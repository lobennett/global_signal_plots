"""Walk a BIDS/derivatives tree, compute per-scan global-signal metric rows."""
from __future__ import annotations

from pathlib import Path

from global_signal_plots.discover import parse_bold_meta
from global_signal_plots.metrics import global_signal_timeseries, summarize_gs

# Default targets echo-2 multi-echo BOLD; override on the CLI for other layouts.
DEFAULT_GLOB = "sub-*/ses-*/func/*echo-2*bold.nii.gz"


def scan_bold(root: Path, glob: str = DEFAULT_GLOB) -> list[dict]:
    """Return one metric row per matched BOLD file (key entities + GS summary)."""
    root = Path(root)
    rows: list[dict] = []
    for path in sorted(root.glob(glob)):
        meta = parse_bold_meta(path.name)
        gs = global_signal_timeseries(path)
        rows.append({
            "subject": meta["subject"], "session": meta["session"],
            "task": meta["task"], "run": meta["run"],
            **summarize_gs(gs),
        })
    return rows
