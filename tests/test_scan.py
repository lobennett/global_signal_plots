from pathlib import Path
import numpy as np
import nibabel as nib
import pandas as pd
from global_signal_plots.scan import scan_bold, collect_traces, DEFAULT_GLOB
from global_signal_plots.io import write_metrics_tsv, KEY_COLS

def _make_bold(tmp_path, name, sub="sub-s03", ses="ses-01"):
    parts = [str(tmp_path), sub]
    if ses:
        parts.append(ses)
    parts.append("func")
    func = Path(*parts)
    func.mkdir(parents=True, exist_ok=True)
    data = np.ones((2, 2, 2, 4), dtype=np.float32)
    nib.save(nib.Nifti1Image(data, np.eye(4)), func / name)

def test_scan_bold_rows(tmp_path):
    _make_bold(tmp_path, "sub-s03_ses-01_task-stroop_run-1_echo-2_bold.nii.gz")
    rows = scan_bold(tmp_path, glob=DEFAULT_GLOB)
    assert len(rows) == 1
    assert rows[0]["subject"] == "s03" and rows[0]["task"] == "stroop"
    assert abs(rows[0]["mean_gs"] - 1.0) < 1e-6

def test_scan_bold_writes_tsv(tmp_path):
    _make_bold(tmp_path, "sub-s03_ses-01_task-stroop_run-1_echo-2_bold.nii.gz")
    rows = scan_bold(tmp_path, glob=DEFAULT_GLOB)
    out = tmp_path / "gs_metrics.tsv"
    write_metrics_tsv(rows, out)
    df = pd.read_csv(out, sep="\t")
    assert list(df.columns[:4]) == KEY_COLS
    assert "mean_gs" in df.columns

def test_scan_bold_sessionless_layout(tmp_path):
    # single-session (no ses-*) layout: sub-*/func/... — default globs must find it
    _make_bold(tmp_path, "sub-s03_task-stroop_run-1_echo-2_bold.nii.gz", ses=None)
    rows = scan_bold(tmp_path)  # default = both session + session-less globs
    assert len(rows) == 1
    assert rows[0]["subject"] == "s03" and rows[0]["task"] == "stroop"
    # missing ses- becomes empty string in the row (not None)
    assert rows[0]["session"] == ""

def test_scan_bold_skips_corrupt(tmp_path):
    # one good file + one corrupt file: good file yields a row, corrupt is skipped
    _make_bold(tmp_path, "sub-s03_ses-01_task-stroop_run-1_echo-2_bold.nii.gz")
    bad_func = tmp_path / "sub-s03" / "ses-01" / "func"
    bad = bad_func / "sub-s03_ses-01_task-rest_run-1_echo-2_bold.nii.gz"
    bad.write_bytes(b"not a nifti file")
    rows = scan_bold(tmp_path, glob=DEFAULT_GLOB)
    assert len(rows) == 1
    assert rows[0]["task"] == "stroop"

def test_collect_traces_computes_once(tmp_path):
    _make_bold(tmp_path, "sub-s03_ses-01_task-stroop_run-1_echo-2_bold.nii.gz")
    traces = collect_traces(tmp_path, glob=DEFAULT_GLOB)
    assert len(traces) == 1
    meta, gs = traces[0]
    assert meta["subject"] == "s03"
    assert len(gs) == 4 and abs(float(gs.mean()) - 1.0) < 1e-6
