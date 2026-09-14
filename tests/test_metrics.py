import pytest
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



@pytest.mark.parametrize("shape", [(2, 2, 2), (2, 2, 2, 4, 2), (2, 2, 2, 0), (0, 2, 2, 4)])
def test_rejects_nonempty_4d_violations(tmp_path, shape):
    path = tmp_path / "bad.nii.gz"
    nib.save(nib.Nifti1Image(np.ones(shape), np.eye(4)), path)
    with pytest.raises(ValueError, match="nonempty 4D"):
        global_signal_timeseries(path)


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_rejects_nonfinite_voxels(tmp_path, value):
    data = np.ones((2, 2, 2, 4))
    data[0, 0, 0, 1] = value
    path = tmp_path / "bad.nii.gz"
    nib.save(nib.Nifti1Image(data, np.eye(4)), path)
    with pytest.raises(ValueError, match="finite"):
        global_signal_timeseries(path)


@pytest.mark.parametrize("trace", [[], 1., [[1., 2.]], [np.nan], [np.inf], [1e308, -1e308]])
def test_rejects_invalid_trace_or_nonfinite_summary(trace):
    with pytest.raises(ValueError):
        summarize_gs(np.asarray(trace))


def test_whole_fov_includes_zero_background(tmp_path):
    data = np.zeros((2, 2, 2, 10))
    data[0, 0, 0, :] = np.arange(10) * 8
    path = tmp_path / "bold.nii.gz"
    nib.save(nib.Nifti1Image(data, np.eye(4)), path)
    np.testing.assert_array_equal(global_signal_timeseries(path), np.arange(10))


def test_spatial_mean_overflow_is_rejected(tmp_path):
    path = tmp_path / "bad.nii.gz"
    nib.save(nib.Nifti1Image(np.full((2, 2, 2, 4), 1e308), np.eye(4)), path)
    with pytest.raises(ValueError, match="finite"):
        global_signal_timeseries(path)
