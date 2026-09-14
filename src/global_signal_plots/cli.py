"""nf-global-signal CLI: BOLD -> gs_metrics.tsv (+ optional PDF of traces)."""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from global_signal_plots.io import staged_outputs, write_metrics_tsv
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
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    glob = args.glob if args.glob is not None else DEFAULT_GLOBS
    # Compute each global-signal trace exactly once, then reuse for TSV + PDF.
    try:
        traces = collect_traces(Path(args.bids_dir), glob=glob)
        rows = rows_from_traces(traces)
        outputs = [Path(args.out_tsv)]
        if args.out_pdf:
            outputs.append(Path(args.out_pdf))
        with staged_outputs(outputs) as staged:
            write_metrics_tsv(rows, staged[0])
            if args.out_pdf:
                from global_signal_plots.plot import render_pdf
                render_pdf(traces, staged[1], tr_marker=args.tr_marker)
    except Exception as exc:
        ap.exit(1, f"nf-global-signal: failed; no completed new output set: {exc}\n")
    print(f"nf-global-signal: wrote {len(rows)} rows to {args.out_tsv}")


if __name__ == "__main__":
    main()
