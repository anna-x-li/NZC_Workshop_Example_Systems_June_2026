"""Loading generic asset-by-province tables.

The expected CSV shape matches e.g. ``co2emissions.csv``: the first column
is the asset/category name and the remaining columns are provinces, with one
row per asset. Any CSV in that shape works, regardless of what the "asset"
actually represents.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_asset_table(source, orient: str = "asset_rows") -> pd.DataFrame:
    """Load an asset-by-province table.

    Parameters
    ----------
    source:
        Path to a CSV file, or an already-loaded DataFrame.
    orient:
        ``"asset_rows"`` (default) if rows are assets and columns are
        provinces, or ``"province_rows"`` if rows are provinces and columns
        are assets.

    Returns
    -------
    DataFrame indexed by asset name, with one column per province.
    """
    if orient not in {"asset_rows", "province_rows"}:
        raise ValueError("orient must be 'asset_rows' or 'province_rows'")

    if isinstance(source, pd.DataFrame):
        df = source.copy()
    else:
        df = pd.read_csv(Path(source), index_col=0)

    return df if orient == "asset_rows" else df.T


def active_assets(asset_by_province: pd.DataFrame, tol: float = 1e-12) -> list:
    """Return asset names (row labels) with at least one nonzero value."""
    return list(asset_by_province.index[asset_by_province.abs().sum(axis=1) > tol])
