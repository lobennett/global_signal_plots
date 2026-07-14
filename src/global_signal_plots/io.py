"""Serialize per-scan metric rows to the standardized <tool>_metrics.tsv."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

KEY_COLS = ["subject", "session", "task", "run"]


def write_metrics_tsv(rows: list[dict], out_path: Path) -> Path:
    """Write rows to a TSV with key columns first, metric columns after.

    An empty rows list still writes a header-only TSV with the key columns.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        pd.DataFrame(columns=KEY_COLS).to_csv(out_path, sep="\t", index=False)
        return out_path
    df = pd.DataFrame(rows)
    metric_cols = [c for c in df.columns if c not in KEY_COLS]
    df = df[KEY_COLS + metric_cols]
    df.to_csv(out_path, sep="\t", index=False)
    return out_path
