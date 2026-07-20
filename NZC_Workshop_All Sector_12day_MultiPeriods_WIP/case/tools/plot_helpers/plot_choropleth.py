"""Shared choropleth-map drawing for per-province, single-value CO2 maps.

Used by plot_co2_injection.py and plot_co2_export.py — each extracts a
different quantity from capacity.csv into a province -> value Series, then
hands it to this one function to actually draw it. Everything from "project
the map" onward is identical between the two callers, so it lives here once.
"""

import matplotlib
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import pandas as pd
from .validation import warn_unmatched_provinces

MAP_WIDTH_PER_PERIOD = 8
MAP_HEIGHT           = 8


def plot_choropleth_series(prov_data, period_labels, gdf, gdf_outline=None,
                           cmap_name='YlOrRd', suptitle='', cbar_label='',
                           warn_context='choropleth map'):
    """
    Draw one choropleth map per period, all in a row, with a shared color
    scale and one colorbar for the whole figure.

    prov_data: {period_label: pandas Series indexed by province name}.
              Every period is normalized to the SAME color scale (the max
              across all periods), so color intensity is comparable across
              periods, not just within one map.
    """
    for series in prov_data.values():
        if not series.empty:
            warn_unmatched_provinces(series.index, gdf['NAME_1'], context=warn_context)

    global_max = max((s.max() for s in prov_data.values() if not s.empty), default=1.0) or 1.0

    gdf_proj         = gdf.to_crs(epsg=3857)
    gdf_outline_proj = gdf_outline.to_crs(epsg=3857) if gdf_outline is not None else None

    cmap = matplotlib.colormaps[cmap_name]
    norm = mcolors.Normalize(vmin=0, vmax=global_max)
    n    = len(period_labels)
    fig, axes = plt.subplots(1, n, figsize=(max(12, n * MAP_WIDTH_PER_PERIOD), MAP_HEIGHT), squeeze=False)
    axes = axes[0]

    for ax, label in zip(axes, period_labels):
        ax.set_axis_off()
        if gdf_outline_proj is not None:
            gdf_outline_proj.plot(ax=ax, color='#cccccc', edgecolor='black', linewidth=0.5, zorder=-1)
        gdf_work          = gdf_proj.copy()
        gdf_work['val']   = gdf_work['NAME_1'].map(prov_data.get(label, pd.Series(dtype=float))).fillna(0)
        gdf_work['color'] = gdf_work['val'].apply(lambda v: cmap(norm(v)))
        gdf_work.plot(ax=ax, color=gdf_work['color'].tolist(), edgecolor='black', linewidth=0.4)
        ax.set_title(label, fontsize=10)

    fig.suptitle(suptitle, fontsize=13)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=axes.tolist(), fraction=0.015, pad=0.03, shrink=0.85)
    cbar.set_label(cbar_label, fontsize=9)
    plt.tight_layout()
    plt.show()
