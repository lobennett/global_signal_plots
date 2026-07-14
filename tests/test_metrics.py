import numpy as np
import nibabel as nib
from global_signal_plots.metrics import global_signal_timeseries, summarize_gs

def test_global_signal_timeseries(tmp_path):
    # 2x2x2 volume, 5 timepoints; known per-volume means 0,1,2,3,4
    data = np.zeros((2, 2, 2, 5), dtype=np.float32)
    for t in range(5):
        data[..., t] = t
    p = tmp_path / "bold.nii.gz"
    nib.save(nib.Nifti1Image(data, affine=np.eye(4)), p)
    gs = global_signal_timeseries(p)
    assert np.allclose(gs, [0, 1, 2, 3, 4])

def test_summarize_gs():
    m = summarize_gs(np.array([0.0, 1.0, 2.0, 3.0, 4.0]))
    assert abs(m["mean_gs"] - 2.0) < 1e-6
    assert m["n_volumes"] == 5
    assert m["gs_std"] > 0
