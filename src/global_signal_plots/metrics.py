"""Global-signal computation (no plotting, no matplotlib dependency)."""
from __future__ import annotations

from pathlib import Path

import nibabel as nib
import numpy as np


def global_signal_timeseries(nifti_path: Path) -> np.ndarray:
    """Mean signal over all voxels at each timepoint (spatial mean per volume)."""
    img = nib.load(str(nifti_path))
    data = img.get_fdata()
    return np.mean(data, axis=(0, 1, 2))


def summarize_gs(gs: np.ndarray) -> dict:
    """Summary metrics for a global-signal trace."""
    gs = np.asarray(gs, dtype=float)
    return {
        "mean_gs": float(gs.mean()) if gs.size else 0.0,
        "gs_std": float(gs.std()) if gs.size else 0.0,
        "n_volumes": int(gs.size),
    }
