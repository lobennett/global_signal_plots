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
