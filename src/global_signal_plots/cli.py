"""nf-global-signal CLI: BOLD -> gs_metrics.tsv (+ optional PDF of traces)."""
from __future__ import annotations

import argparse
from pathlib import Path

from global_signal_plots.io import write_metrics_tsv
from global_signal_plots.scan import DEFAULT_GLOB, scan_bold


def main(argv=None):
    ap = argparse.ArgumentParser(prog="nf-global-signal", description=__doc__.splitlines()[0])
    ap.add_argument("--bids-dir", required=True, help="dataset/derivatives root to glob")
    ap.add_argument("--out-tsv", required=True, help="output gs_metrics.tsv path")
    ap.add_argument("--out-pdf", default=None, help="optional PDF of GS traces")
    ap.add_argument("--glob", default=DEFAULT_GLOB,
                    help=f"BOLD glob relative to --bids-dir (default: {DEFAULT_GLOB})")
    ap.add_argument("--tr-marker", type=int, default=None,
                    help="draw a vertical marker at this volume index in the PDF")
    args = ap.parse_args(argv)

    rows = scan_bold(Path(args.bids_dir), glob=args.glob)
    write_metrics_tsv(rows, Path(args.out_tsv))
    if args.out_pdf:
        from global_signal_plots.plot import render_pdf
        render_pdf(rows, Path(args.bids_dir), Path(args.out_pdf),
                   glob=args.glob, tr_marker=args.tr_marker)
    print(f"nf-global-signal: wrote {len(rows)} rows to {args.out_tsv}")


if __name__ == "__main__":
    main()
