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

## Tests

On Python 3.11 or newer, create a virtual environment and run the full suite:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --editable '.[plot]' 'pytest>=8'
MPLBACKEND=Agg python -m pytest -ra
```

GitHub Actions runs these tests on Ubuntu with Python 3.11 for pushes and pull
requests. Tests generate small synthetic NIfTI fixtures and cover discovery,
global-signal metrics, scanning, TSV output, PDF rendering, and the CLI. They
require no participant data, credentials, or external services. Real participant
datasets and Sherlock execution are not validated by this software suite.
Dependencies follow `pyproject.toml`; this repository has no tracked lockfile.

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
  default scans BOTH the session layout `sub-*/ses-*/func/*_echo-2_*bold.nii.gz`
  and the session-less layout `sub-*/func/*_echo-2_*bold.nii.gz` (union, deduped),
  so single-session datasets are not silently missed. Both target echo-2 of
  multi-echo BOLD acquisitions. Pass `--glob` to override for single-echo
  layouts or other naming conventions. Echo 20 does not match the default.
  Invalid files are logged and skipped when other usable scans remain.
- `--tr-marker` (optional) — volume index at which to draw a vertical marker
  line in the PDF (e.g. to flag a known artifact TR). Has no effect without
  `--out-pdf`.

## Coverage and output failures

Inputs must be nonempty finite 4D images. Each run reports distinct matched
files as `attempted`, usable files as `succeeded`, and skipped files as `failed`.
Warnings identify invalid files. All files sharing the same
`subject/session/task/run` identity are skipped as ambiguous; choose a narrower
`--glob` when several acquisitions, spaces or echoes share that identity.

An invalid root or no usable scans exits nonzero without replacing prior
outputs. When a PDF is requested, both products are staged before publication;
a plotting or writing failure does not publish a new table alongside an old
PDF. Ordinary replacement failures roll back prior products. Treat the CLI
exit status as authoritative: files left after failure may belong to a prior
run.

Rerunning over existing outputs preserves their access restrictions: the owner,
group, mode bits and POSIX access ACL of each prior product are reproduced on
its replacement before publication, so a rerun under a permissive umask does not
widen access to restricted QA outputs. If those restrictions cannot be
reproduced — for example a prior output owned by another user, so `chown` or the
ACL update fails with `Operation not permitted` — the run exits nonzero and
publishes nothing, leaving the prior outputs in place; have the owner rerun or
remove the stale products. Non-POSIX ACL flavors (e.g. macOS/NFSv4) are not
reproduced.

Do not run concurrent writers to the same destinations. Replacement is atomic
per file, not a crash-safe transaction across both files. See
[the audit record](docs/CODE-REVIEW.md) for evidence and limits.

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
