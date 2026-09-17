"""Load and dissolve China province GeoDataFrames from gadm (36 or 41) + outline GeoJSON."""

import geopandas as gpd

# Maps gadm NAME_1 (whitespace stripped, so "Nei Mongol" and "NeiMongol" both
# match) → model province names (add entries for new spellings)
GEOJSON_RENAME = {
    'NeiMongol':     'Innermongolia',
    'NingxiaHui':    'Ningxia',
    'XinjiangUygur': 'Xinjiang',
    'Xizang':        'Tibet',
}

# Regions in gadm that are not modelled as provinces
EXCLUDE_REGIONS = ['HongKong', 'Macau']


def load_gdf(geojson_path, outline_path=None):
    """Return (gdf, outline_gdf). gdf is dissolved to 31 provinces matching model names.

    outline_path: optional path to a separate country-outline GeoJSON. When
    omitted, the outline is derived by dissolving gdf's own province polygons
    into a single national boundary.
    """
    gdf = gpd.read_file(geojson_path)
    gdf['NAME_1'] = gdf['NAME_1'].str.replace(' ', '', regex=False).replace(GEOJSON_RENAME)
    gdf = gdf[~gdf['NAME_1'].isin(EXCLUDE_REGIONS)]
    gdf = gdf.dissolve(by='NAME_1').reset_index()  # merge duplicate polygons (Xinjiang, Tibet)
    if outline_path is not None:
        outline = gpd.read_file(outline_path)
    else:
        outline = gdf.dissolve()[['geometry']]
    return gdf, outline
