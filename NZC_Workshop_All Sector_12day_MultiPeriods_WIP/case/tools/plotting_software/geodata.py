"""Loading and preparing province boundary geodata."""

from __future__ import annotations

from pathlib import Path

DEFAULT_MAP_PATH = Path(__file__).resolve().parent / "data" / "gadm36_CHN_1.json"

# GADM level-1 names that don't match the province labels used in the
# asset/results CSVs.
DEFAULT_PROVINCE_RENAME = {
    "Nei Mongol": "Innermongolia",
    "Xizang": "Tibet",
    "Ningxia Hui": "Ningxia",
    "Xinjiang Uygur": "Xinjiang",
}


def load_province_geodata(map_path=None, rename: dict | None = None, province_col: str = "NAME_1"):
    """Load a province boundary GeoDataFrame.

    Defaults to the bundled China (GADM level 1) boundaries. Pass ``map_path``
    to use a different boundary file (any format geopandas can read), and
    ``rename`` to override the default province-name normalization (pass an
    empty dict to disable renaming).
    """
    import geopandas as gpd

    map_path = Path(map_path) if map_path else DEFAULT_MAP_PATH
    if not map_path.exists():
        raise FileNotFoundError(f"Province boundary file not found: {map_path}")

    gdf = gpd.read_file(map_path)
    rename = DEFAULT_PROVINCE_RENAME if rename is None else rename
    if rename and province_col in gdf.columns:
        gdf[province_col] = gdf[province_col].replace(rename)
    return gdf
