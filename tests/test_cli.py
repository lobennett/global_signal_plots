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
