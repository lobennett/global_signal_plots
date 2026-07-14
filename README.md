# global_signal_plots

Generic global-signal QA for BOLD data: computes per-scan global-signal
metrics and renders per-subject PDF traces from any BIDS/derivatives dataset.

This package is a **pure producer**: it computes metrics and (optionally)
draws plots. It applies **no study-specific thresholds** and makes **no
exclusion decisions** — those live in the consuming study package (e.g.
`network_qa`), which reads the `gs_metrics.tsv` this tool writes.

## Install

Runs on Sherlock; nibabel/matplotlib should be installed on a compute node,
not the login node.

```bash
sh_dev -c 2 -m 8000 -t 00:30:00 -p normal
module load uv
cd global_signal_plots
uv sync
```

## Usage

```bash
uv run nf-global-signal \
  --bids-dir /path/to/fmriprep/derivatives \
  --out-tsv gs_metrics.tsv \
  --out-pdf gs.pdf \
  --tr-marker 7
```

- `--bids-dir` — dataset/derivatives root to glob for BOLD files.
- `--out-tsv` — output path for the standardized `gs_metrics.tsv`.
- `--out-pdf` (optional) — if given, also render a per-subject PDF of
  global-signal traces (one page per subject, one axis per matched run).
- `--glob` (optional) — BOLD glob relative to `--bids-dir`. When omitted, the
  default scans BOTH the session layout `sub-*/ses-*/func/*echo-2*bold.nii.gz`
  and the session-less layout `sub-*/func/*echo-2*bold.nii.gz` (union, deduped),
  so single-session datasets are not silently missed. Both target echo-2 of
  multi-echo BOLD acquisitions. Pass `--glob` to override for single-echo
  layouts or other naming conventions. A BOLD file that fails to load is logged
  and skipped rather than aborting the run.
- `--tr-marker` (optional) — volume index at which to draw a vertical marker
  line in the PDF (e.g. to flag a known artifact TR). Has no effect without
  `--out-pdf`.

## `gs_metrics.tsv` schema

| Column    | Type  | Description                                              |
|-----------|-------|------------------------------------------------------------|
| `subject` | str   | Bare subject ID (no `sub-` prefix)                        |
| `session` | str   | Bare session ID (no `ses-` prefix); empty string for session-less layouts |
| `task`    | str   | Task label                                                 |
| `run`     | str   | Bare run ID                                                |
| `mean_gs` | float | Mean of the global-signal trace (whole-FOV spatial mean per volume, not brain-masked) |
| `gs_std`  | float | Standard deviation of the global-signal trace              |
| `n_volumes` | int | Number of volumes (timepoints) in the trace                |

The four key columns (`subject session task run`) always appear first, as
bare IDs, for stable joins with other QA tools' output (e.g. `motion_qa`'s
`motion_metrics.tsv`). Thresholds, flags, and exclusion decisions are the
consumer's responsibility — this package does not apply any.
