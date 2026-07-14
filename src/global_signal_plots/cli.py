"""nf-global-signal CLI: BOLD -> gs_metrics.tsv (+ optional PDF of traces)."""
from __future__ import annotations

import argparse
from pathlib import Path

from global_signal_plots.io import write_metrics_tsv
from global_signal_plots.scan import (
    DEFAULT_GLOBS,
    collect_traces,
    rows_from_traces,
)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="nf-global-signal", description=__doc__.splitlines()[0])
    ap.add_argument("--bids-dir", required=True, help="dataset/derivatives root to glob")
    ap.add_argument("--out-tsv", required=True, help="output gs_metrics.tsv path")
    ap.add_argument("--out-pdf", default=None, help="optional PDF of GS traces")
    ap.add_argument("--glob", default=None,
                    help="BOLD glob relative to --bids-dir; overrides the default "
                         f"session + session-less patterns {DEFAULT_GLOBS}")
    ap.add_argument("--tr-marker", type=int, default=None,
                    help="draw a vertical marker at this volume index in the PDF")
    args = ap.parse_args(argv)

    glob = args.glob if args.glob is not None else DEFAULT_GLOBS
    # Compute each global-signal trace exactly once, then reuse for TSV + PDF.
    traces = collect_traces(Path(args.bids_dir), glob=glob)
    rows = rows_from_traces(traces)
    write_metrics_tsv(rows, Path(args.out_tsv))
    if args.out_pdf:
        from global_signal_plots.plot import render_pdf
        render_pdf(traces, Path(args.out_pdf), tr_marker=args.tr_marker)
    print(f"nf-global-signal: wrote {len(rows)} rows to {args.out_tsv}")


if __name__ == "__main__":
    main()
