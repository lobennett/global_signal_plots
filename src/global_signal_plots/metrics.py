"""Global-signal computation (no plotting, no matplotlib dependency)."""
from __future__ import annotations

from pathlib import Path

import nibabel as nib
import numpy as np


def global_signal_timeseries(nifti_path: Path) -> np.ndarray:
    """Mean signal over all voxels at each timepoint (spatial mean per volume).

    This is a whole-FOV mean, NOT a brain-masked mean (matches the extraction
    source): every voxel in the volume contributes, including out-of-brain
    background. Supply a masked/brain-extracted BOLD image if you want a
    brain-only global signal.
    """
    img = nib.load(str(nifti_path))
    if len(img.shape) != 4 or any(size == 0 for size in img.shape):
        raise ValueError(f"Expected nonempty 4D BOLD image, got shape {img.shape}")
    with np.errstate(over="ignore", invalid="ignore"):
        gs = np.mean(img.get_fdata(), axis=(0, 1, 2))
    # A nonfinite voxel or an overflowing sum makes its volume's mean nonfinite.
    summarize_gs(gs)
    return gs


def summarize_gs(gs: np.ndarray) -> dict:
    """Summary metrics for a global-signal trace."""
    gs = np.asarray(gs, dtype=float)
    if gs.ndim != 1 or not gs.size or not np.isfinite(gs).all():
        raise ValueError("Expected a nonempty finite 1D global-signal trace")
    with np.errstate(over="ignore", invalid="ignore"):
        mean, std = float(gs.mean()), float(gs.std())
    if not np.isfinite([mean, std]).all():
        raise ValueError("Global-signal summary must be finite")
    return {
        "mean_gs": mean,
        "gs_std": std,
        "n_volumes": int(gs.size),
    }
