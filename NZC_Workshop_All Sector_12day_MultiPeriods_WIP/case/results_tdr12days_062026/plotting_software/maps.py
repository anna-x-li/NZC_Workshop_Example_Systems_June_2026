"""Plot assets by province: pie charts across multiple assets, or a single
color-coded quantity map when only one asset is present.

Both plot types assume non-negative values (quantities like emissions,
capacity, demand, ...) since a pie wedge or a circle radius can't represent
a negative amount; a negative value raises ``ValueError`` rather than being
silently mis-plotted.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .formatting import assign_colors, format_map_quantity, legend_values, round_2sf
from .geodata import load_province_geodata
from .io_utils import active_assets, load_asset_table

_RADIUS_UNIT = 80_000  # meters, at pie_scale/circle_scale == 1.0 (EPSG:3857 units)


def _draw_circle_legend(ax, plt, Circle, sizes, max_value, scale, unit_label, title):
    """Draw a stacked legend of reference circles at increasing sizes."""
    if not sizes:
        return
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    plot_width = xlim[1] - xlim[0]
    plot_height = ylim[1] - ylim[0]
    pad_x = plot_width * 0.02
    pad_y = plot_height * 0.02

    sizes_and_radii = sorted(
        (size, (size / max_value) ** 0.5 * scale * _RADIUS_UNIT) for size in sizes if size > 0
    )
    if not sizes_and_radii:
        return
    max_radius = max(radius for _, radius in sizes_and_radii)

    legend_cx = xlim[0] + pad_x + max_radius
    y_start = ylim[0] + pad_y

    legend_height = sum(2 * radius for _, radius in sizes_and_radii)
    legend_spacing = pad_y * 0.4 * (len(sizes_and_radii) - 1)
    title_y = y_start + legend_height + legend_spacing + pad_y * 0.9
    ax.text(legend_cx - max_radius, title_y, title, fontsize=9, fontweight="bold", ha="left", va="bottom")

    y = y_start
    for size, radius in sizes_and_radii:
        cy = y + radius
        ax.add_patch(
            Circle((legend_cx, cy), radius, facecolor="white", edgecolor="#555555", linewidth=1.2, zorder=20)
        )
        label = format_map_quantity(round_2sf(size))
        if unit_label:
            label = f"{label} {unit_label}"
        ax.text(legend_cx + max_radius + pad_x * 0.6, cy, label, va="center", ha="left", fontsize=9, zorder=21)
        y += radius * 2 + pad_y * 0.4


def _warn_unmatched_provinces(data_provinces, gdf, province_col):
    """Print a warning for any data province name absent from the map.

    A silent left-join would otherwise plot those provinces as zero with no
    indication that the mismatch (typo, different romanization, etc.), not
    an actual zero value, is the cause.
    """
    known = set(gdf[province_col])
    unmatched = sorted(set(data_provinces) - known)
    if unmatched:
        print(
            f"Warning: {len(unmatched)} province name(s) in the data don't match any "
            f"'{province_col}' value in the map and will be plotted as zero: {unmatched}"
        )


def _require_non_negative(values_by_label: dict):
    """Raise with the offending labels if any value is negative."""
    negative = [label for label, value in values_by_label.items() if value < 0]
    if negative:
        raise ValueError(
            f"Negative values aren't supported (a size can't represent a negative "
            f"amount): {negative}"
        )


def _new_map_axes(gdf_proj, figsize):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=figsize)
    ax.set_axis_off()
    gdf_proj.plot(ax=ax, color="#F4F4F4", edgecolor="black", linewidth=0.7, zorder=0)
    gdf_proj.boundary.plot(ax=ax, linewidth=0.7, color="black", zorder=1)
    return fig, ax


def _finish_map_figure(fig, ax, plt, title, output_path, show):
    ax.set_title(title, fontsize=18)
    fig.tight_layout()
    if output_path is not None:
        fig.savefig(output_path, dpi=250, bbox_inches="tight")
        print(f"Saved {output_path}")
    if show:
        plt.show()
    plt.close(fig)


def _project_with_centroids(gdf):
    """Reproject to Web Mercator and add per-feature centroid (cx, cy) columns."""
    gdf_proj = gdf.to_crs(epsg=3857)
    gdf_proj["cx"] = gdf_proj.geometry.centroid.x
    gdf_proj["cy"] = gdf_proj.geometry.centroid.y
    return gdf_proj


def plot_pie_map(
    asset_by_province: pd.DataFrame,
    gdf=None,
    output_path: str | Path | None = None,
    *,
    province_col: str = "NAME_1",
    categories=None,
    colors: dict | None = None,
    pie_scale: float = 2.8,
    figsize=(14, 10),
    title: str = "",
    unit_label: str = "",
    legend_title: str = "Asset",
    size_legend_title: str = "Total",
    show_size_legend: bool = True,
    show: bool = False,
):
    """Draw one pie per province, with wedges sized/colored by asset.

    ``asset_by_province`` must be indexed by province name, with one column
    per asset category (i.e. the transpose of the raw asset-rows CSV).
    ``colors`` maps category name to a matplotlib color; categories without
    an entry get one assigned automatically.
    """
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Wedge

    if asset_by_province.empty:
        print("No data to plot; skipping pie map.")
        return None

    categories = list(asset_by_province.columns) if categories is None else categories
    colors = assign_colors(categories, plt=plt) if colors is None else colors

    if gdf is None:
        gdf = load_province_geodata()
    _warn_unmatched_provinces(asset_by_province.index, gdf, province_col)

    gdf_proj = _project_with_centroids(gdf)
    gdf_proj = gdf_proj.merge(asset_by_province, left_on=province_col, right_index=True, how="left")
    gdf_proj[categories] = gdf_proj[categories].fillna(0)
    _require_non_negative(
        {cat: gdf_proj[cat].min() for cat in categories if gdf_proj[cat].min() < 0}
    )

    gdf_proj["total_value"] = gdf_proj[categories].sum(axis=1)
    max_value = gdf_proj["total_value"].max() or 1
    gdf_proj["radius"] = (gdf_proj["total_value"] / max_value) ** 0.5 * pie_scale * _RADIUS_UNIT

    fig, ax = _new_map_axes(gdf_proj, figsize)
    for _, row in gdf_proj.iterrows():
        values = row[categories].values.astype(float)
        total = values.sum()
        if total == 0:
            continue
        angles = np.cumsum(values) / total * 360
        previous_angle = 0
        for category, angle in zip(categories, angles):
            ax.add_patch(
                Wedge(
                    center=(row["cx"], row["cy"]),
                    r=row["radius"],
                    theta1=previous_angle,
                    theta2=angle,
                    facecolor=colors[category],
                    edgecolor="none",
                    zorder=1000,
                )
            )
            previous_angle = angle

    ax.legend(
        handles=[Wedge((0, 0), 1, 0, 360, facecolor=colors[cat], label=cat) for cat in categories],
        loc="lower right",
        frameon=True,
        title=legend_title,
        fontsize=11,
        title_fontsize=12,
    )
    if show_size_legend:
        _draw_circle_legend(
            ax, plt, Circle, legend_values(max_value), max_value, pie_scale, unit_label, size_legend_title
        )

    _finish_map_figure(fig, ax, plt, title, output_path, show)
    return fig


def plot_quantity_map(
    values: pd.Series,
    gdf=None,
    output_path: str | Path | None = None,
    *,
    province_col: str = "NAME_1",
    color: str = "#f28e2b",
    circle_scale: float = 2.8,
    figsize=(14, 10),
    title: str = "",
    unit_label: str = "",
    size_legend_title: str = "Total",
    show_size_legend: bool = True,
    show: bool = False,
):
    """Draw one color-coded, size-scaled circle per province for a single asset.

    ``values`` must be a Series indexed by province name.
    """
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle

    values = values.fillna(0)
    if (values == 0).all():
        print("No nonzero quantities to plot; skipping quantity map.")
        return None
    _require_non_negative({province: value for province, value in values.items() if value < 0})

    if gdf is None:
        gdf = load_province_geodata()
    _warn_unmatched_provinces(values.index, gdf, province_col)

    gdf_proj = _project_with_centroids(gdf)
    gdf_proj = gdf_proj.merge(values.rename("value"), left_on=province_col, right_index=True, how="left")
    gdf_proj["value"] = gdf_proj["value"].fillna(0)
    max_value = gdf_proj["value"].max() or 1

    fig, ax = _new_map_axes(gdf_proj, figsize)
    for _, row in gdf_proj.iterrows():
        if row["value"] <= 0:
            continue
        radius = (row["value"] / max_value) ** 0.5 * circle_scale * _RADIUS_UNIT
        ax.add_patch(
            Circle(
                (row["cx"], row["cy"]),
                radius,
                facecolor=color,
                edgecolor="white",
                linewidth=0.5,
                alpha=0.75,
                zorder=10,
            )
        )

    if show_size_legend:
        _draw_circle_legend(
            ax, plt, Circle, legend_values(max_value), max_value, circle_scale, unit_label, size_legend_title
        )

    _finish_map_figure(fig, ax, plt, title, output_path, show)
    return fig


def plot_asset_map(
    source,
    gdf=None,
    output_path: str | Path | None = None,
    *,
    orient: str = "asset_rows",
    province_col: str = "NAME_1",
    title: str = "",
    unit_label: str = "",
    colors: dict | None = None,
    single_asset_color: str = "#f28e2b",
    pie_scale: float = 2.8,
    quantity_scale: float = 2.8,
    legend_title: str = "Asset",
    size_legend_title: str | None = None,
    figsize=(14, 10),
    show: bool = False,
):
    """Plot assets by province, auto-choosing pies vs. a quantity map.

    ``source`` is a path to a CSV (or an already-loaded DataFrame) shaped
    like ``co2emissions.csv``: one row per asset, one column per province.
    If more than one asset has a nonzero value anywhere in the table, this
    draws a pie chart per province across those active assets. If exactly
    one asset is active, it draws a single-color quantity map sized by that
    asset's value instead. If none are active, nothing is plotted.

    ``colors`` (category -> matplotlib color) only applies to the pie-chart
    case, since a single-asset map has just one color: ``single_asset_color``.
    """
    asset_by_province = load_asset_table(source, orient=orient)
    live = active_assets(asset_by_province)

    if not live:
        print("No nonzero assets found; nothing to plot.")
        return None

    if gdf is None:
        gdf = load_province_geodata(province_col=province_col)

    if len(live) > 1:
        province_by_asset = asset_by_province.loc[live].T
        return plot_pie_map(
            province_by_asset,
            gdf=gdf,
            output_path=output_path,
            province_col=province_col,
            colors=colors,
            pie_scale=pie_scale,
            figsize=figsize,
            title=title,
            unit_label=unit_label,
            legend_title=legend_title,
            size_legend_title=size_legend_title or "Total",
            show=show,
        )

    asset_name = live[0]
    values = asset_by_province.loc[asset_name]
    return plot_quantity_map(
        values,
        gdf=gdf,
        output_path=output_path,
        province_col=province_col,
        color=single_asset_color,
        circle_scale=quantity_scale,
        figsize=figsize,
        title=title or str(asset_name),
        unit_label=unit_label,
        size_legend_title=size_legend_title or f"Total {asset_name}",
        show=show,
    )
