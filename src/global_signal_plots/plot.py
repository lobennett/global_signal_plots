"""Render per-subject global-signal traces to a single PDF (matplotlib)."""
from __future__ import annotations

from pathlib import Path

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402


def _label(meta: dict) -> str:
    """Reconstruct a BIDS-style label from parsed entities for the axis title."""
    parts = [f"sub-{meta['subject']}"]
    for key, prefix in (("session", "ses"), ("task", "task"),
                        ("run", "run"), ("echo", "echo")):
        if meta.get(key):
            parts.append(f"{prefix}-{meta[key]}")
    return "_".join(parts)


def render_pdf(traces: list[tuple[dict, np.ndarray]], pdf_path: Path,
               tr_marker: int | None = None) -> Path:
    """One page per subject; one axis per run. tr_marker draws a vline.

    Consumes the already-computed ``(meta, gs_trace)`` pairs from
    :func:`global_signal_plots.scan.collect_traces` -- no re-glob, no recompute.
    Plotting errors abort, so a successful PDF includes every supplied trace.
    The CLI stages this file before publishing outputs.
    """
    pdf_path = Path(pdf_path)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    by_sub: dict[str, list[tuple[dict, np.ndarray]]] = {}
    for meta, gs in traces:
        by_sub.setdefault(meta["subject"], []).append((meta, gs))

    with PdfPages(pdf_path) as pdf:
        for subject, items in by_sub.items():
            n = len(items)
            fig, axes = plt.subplots(n, 1, figsize=(12, 2.5 * n), squeeze=False)
            try:
                for i, (meta, gs) in enumerate(items):
                    ax = axes[i][0]
                    ax.plot(gs, color="#1a5276", linewidth=1.0)
                    if tr_marker is not None:
                        ax.axvline(x=tr_marker, color="#c0392b",
                                   linestyle="--", alpha=0.7)
                    ax.set_title(_label(meta), fontsize=7)
                fig.suptitle(f"sub-{subject}")
                fig.tight_layout()
                pdf.savefig(fig)
            finally:
                plt.close(fig)
    return pdf_path
