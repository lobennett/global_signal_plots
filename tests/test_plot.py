import pytest
from pathlib import Path
import numpy as np
import nibabel as nib
from global_signal_plots.scan import collect_traces, DEFAULT_GLOB
from global_signal_plots.plot import render_pdf

def test_render_pdf_creates_file(tmp_path):
    func = tmp_path / "sub-s03" / "ses-01" / "func"
    func.mkdir(parents=True)
    nib.save(nib.Nifti1Image(np.ones((2, 2, 2, 6), np.float32), np.eye(4)),
             func / "sub-s03_ses-01_task-stroop_run-1_echo-2_bold.nii.gz")
    traces = collect_traces(tmp_path, glob=DEFAULT_GLOB)
    pdf = tmp_path / "gs.pdf"
    render_pdf(traces, pdf, tr_marker=None)
    assert pdf.exists() and pdf.stat().st_size > 0



def test_volume_axis_and_pretrim_marker_unchanged(tmp_path, monkeypatch):
    from matplotlib.backends.backend_pdf import PdfPages
    captured = []
    savefig = PdfPages.savefig
    def capture(pdf, figure, **kwargs):
        captured.extend(figure.axes)
        return savefig(pdf, figure, **kwargs)
    monkeypatch.setattr(PdfPages, "savefig", capture)
    meta = {"subject": "s01", "session": None, "task": "rest", "run": "1", "echo": "2"}
    render_pdf([(meta, np.arange(10))], tmp_path / "out.pdf", tr_marker=7)
    np.testing.assert_array_equal(captured[0].lines[0].get_xdata(), np.arange(10))
    np.testing.assert_array_equal(captured[0].lines[0].get_ydata(), np.arange(10))
    assert list(captured[0].lines[1].get_xdata()) == [7, 7]


def test_empty_pdf_input_fails_without_touching_old_file(tmp_path):
    path = tmp_path / "out.pdf"
    path.write_bytes(b"old pdf")
    with pytest.raises(ValueError):
        render_pdf([], path)
    assert path.read_bytes() == b"old pdf"
