import pytest
from pathlib import Path
import numpy as np
import nibabel as nib
import pandas as pd
from global_signal_plots.cli import main

def test_cli_writes_tsv_and_pdf(tmp_path):
    func = tmp_path / "sub-s03" / "ses-01" / "func"
    func.mkdir(parents=True)
    nib.save(nib.Nifti1Image(np.ones((2, 2, 2, 6), np.float32), np.eye(4)),
             func / "sub-s03_ses-01_task-stroop_run-1_echo-2_bold.nii.gz")
    out_tsv = tmp_path / "gs_metrics.tsv"
    out_pdf = tmp_path / "gs.pdf"
    main(["--bids-dir", str(tmp_path), "--out-tsv", str(out_tsv),
          "--out-pdf", str(out_pdf), "--tr-marker", "7"])
    df = pd.read_csv(out_tsv, sep="\t")
    assert len(df) == 1 and "mean_gs" in df.columns
    assert out_pdf.exists()



def _scan(root, data=None):
    func = root / "sub-s03/ses-01/func"
    func.mkdir(parents=True, exist_ok=True)
    path = func / "sub-s03_ses-01_task-rest_run-1_echo-2_bold.nii.gz"
    nib.save(nib.Nifti1Image(np.ones((2, 2, 2, 4)) if data is None else data, np.eye(4)), path)
    return path


def _args(root, tsv, pdf):
    return ["--bids-dir", str(root), "--out-tsv", str(tsv), "--out-pdf", str(pdf)]


@pytest.mark.parametrize("case", ["missing", "file", "empty", "corrupt", "nan", "3d", "5d", "zero"])
@pytest.mark.parametrize("prior", [False, True])
def test_failed_run_preserves_prior_products(tmp_path, case, prior, capsys):
    root = tmp_path / "input"
    tsv, pdf = tmp_path / "out.tsv", tmp_path / "out.pdf"
    if prior:
        good = tmp_path / "good"
        _scan(good)
        main(_args(good, tsv, pdf))
    old = {p: p.read_bytes() if p.exists() else None for p in (tsv, pdf)}
    capsys.readouterr()
    if case == "file":
        root.write_text("not a directory")
    elif case == "empty":
        root.mkdir()
    elif case == "corrupt":
        _scan(root).write_bytes(b"corrupt")
    elif case in ("nan", "3d", "5d", "zero"):
        data = {"nan": np.full((2, 2, 2, 4), np.nan), "3d": np.ones((2, 2, 2)),
                "5d": np.ones((2, 2, 2, 4, 2)), "zero": np.ones((2, 2, 2, 0))}[case]
        _scan(root, data)
    with pytest.raises(SystemExit) as exc:
        main(_args(root, tsv, pdf))
    assert exc.value.code != 0
    output = capsys.readouterr()
    assert "failed" in output.err.lower()
    assert "wrote" not in output.out
    assert {p: p.read_bytes() if p.exists() else None for p in (tsv, pdf)} == old


def test_pdf_failure_preserves_both_outputs(tmp_path, monkeypatch):
    from matplotlib.axes import Axes
    root = tmp_path / "input"
    path = _scan(root)
    tsv, pdf = tmp_path / "out.tsv", tmp_path / "out.pdf"
    main(_args(root, tsv, pdf))
    before = tsv.read_bytes(), pdf.read_bytes()
    nib.save(nib.Nifti1Image(np.full((2, 2, 2, 4), 5.), np.eye(4)), path)
    def fail_plot(*args, **kwargs):
        raise RuntimeError("injected plot failure")
    monkeypatch.setattr(Axes, "plot", fail_plot)
    with pytest.raises(SystemExit):
        main(_args(root, tsv, pdf))
    assert (tsv.read_bytes(), pdf.read_bytes()) == before


def test_partial_success_replaces_both_products(tmp_path):
    root = tmp_path / "input"
    path = _scan(root)
    tsv, pdf = tmp_path / "table/out.tsv", tmp_path / "plot/out.pdf"
    main(_args(root, tsv, pdf))
    before = tsv.read_bytes(), pdf.read_bytes()
    nib.save(nib.Nifti1Image(np.full((2, 2, 2, 4), 5.), np.eye(4)), path)
    path.with_name(path.name.replace("run-1", "run-2")).write_bytes(b"corrupt")
    main(_args(root, tsv, pdf))
    rows = pd.read_csv(tsv, sep="\t")
    assert len(rows) == 1 and rows.mean_gs.iloc[0] == 5.
    assert tsv.read_bytes() != before[0] and pdf.read_bytes() != before[1]
    assert pdf.read_bytes().startswith(b"%PDF")


@pytest.mark.parametrize("prior", [False, True])
def test_publication_failure_rolls_back(tmp_path, monkeypatch, prior):
    import os
    root = tmp_path / "input"
    _scan(root)
    tsv, pdf = tmp_path / "out.tsv", tmp_path / "out.pdf"
    if prior:
        main(_args(root, tsv, pdf))
    before = {p: p.read_bytes() if p.exists() else None for p in (tsv, pdf)}
    replace = os.replace
    def fail_pdf(source, target):
        if Path(target) == pdf:
            raise OSError("injected publication failure")
        return replace(source, target)
    monkeypatch.setattr(os, "replace", fail_pdf)
    with pytest.raises(SystemExit):
        main(_args(root, tsv, pdf))
    assert {p: p.read_bytes() if p.exists() else None for p in (tsv, pdf)} == before


def test_same_output_path_rejected(tmp_path):
    root = tmp_path / "input"
    _scan(root)
    out = tmp_path / "output"
    out.write_bytes(b"prior output")
    with pytest.raises(SystemExit):
        main(_args(root, out, out))
    assert out.read_bytes() == b"prior output"


def test_table_write_failure_preserves_outputs(tmp_path, monkeypatch):
    import global_signal_plots.cli as cli
    root = tmp_path / "input"
    _scan(root)
    tsv, pdf = tmp_path / "out.tsv", tmp_path / "out.pdf"
    main(_args(root, tsv, pdf))
    before = tsv.read_bytes(), pdf.read_bytes()
    def fail_write(rows, path):
        path.write_text("partial table")
        raise OSError("injected table failure")
    monkeypatch.setattr(cli, "write_metrics_tsv", fail_write)
    with pytest.raises(SystemExit):
        main(_args(root, tsv, pdf))
    assert (tsv.read_bytes(), pdf.read_bytes()) == before
    assert not list(tmp_path.glob(".gs-*"))


def test_tsv_only_success(tmp_path):
    root = tmp_path / "input"
    _scan(root)
    tsv = tmp_path / "out.tsv"
    main(["--bids-dir", str(root), "--out-tsv", str(tsv)])
    rows = pd.read_csv(tsv, sep="\t")
    assert len(rows) == 1 and rows.mean_gs.iloc[0] == 1.
    assert not list(tmp_path.glob(".gs-*"))
