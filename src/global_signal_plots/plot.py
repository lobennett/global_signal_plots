"""Render per-subject global-signal traces to a single PDF (matplotlib)."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402

from global_signal_plots.discover import parse_bold_meta
from global_signal_plots.metrics import global_signal_timeseries


def render_pdf(rows: list[dict], root: Path, pdf_path: Path,
               glob: str, tr_marker: int | None = None) -> Path:
    """One page per subject; one axis per matched run. tr_marker draws a vline."""
    root, pdf_path = Path(root), Path(pdf_path)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    paths = sorted(root.glob(glob))
    by_sub: dict[str, list[Path]] = {}
    for p in paths:
        by_sub.setdefault(parse_bold_meta(p.name)["subject"], []).append(p)

    with PdfPages(pdf_path) as pdf:
        for subject, sub_paths in by_sub.items():
            n = len(sub_paths)
            fig, axes = plt.subplots(n, 1, figsize=(12, 2.5 * n), squeeze=False)
            for i, p in enumerate(sub_paths):
                ax = axes[i][0]
                ax.plot(global_signal_timeseries(p), color="#1a5276", linewidth=1.0)
                if tr_marker is not None:
                    ax.axvline(x=tr_marker, color="#c0392b", linestyle="--", alpha=0.7)
                ax.set_title(p.name, fontsize=7)
            fig.suptitle(f"sub-{subject}")
            fig.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)
    return pdf_path
