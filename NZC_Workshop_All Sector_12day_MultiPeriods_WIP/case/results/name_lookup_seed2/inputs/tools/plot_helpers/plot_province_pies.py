"""Draw province capacity pie charts on a China base map (one scenario)."""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Wedge, Circle
from .formatting import format_quantity
from .validation import warn_unmatched_provinces, require_non_negative

PIE_RADIUS_FRACTION = 0.03  # max radius as fraction of map diagonal


def plot_province_pies(
    gdf,
    data_df,
    province_col='NAME_1',
    categories=None,
    colors=None,
    pie_scale=1.0,
    figsize=(14, 10),
    title='',
    legend_sizes=None,
    capacity_unit='MW',
    unit_scale=1.0,
    scale_max=None,
    outline_gdf=None,
    ax=None,
    include_color_legend=True,
    include_size_legend=True,
):
    """Draw pies on ax (or a new figure if ax is None). Returns without plt.show() when ax is provided."""
    if categories is None:
        categories = [c for c in data_df.columns if data_df[c].sum() > 0]
    if not categories:
        if ax is None:
            print(f'[{title}] No non-zero categories.')
        return
    if colors is None:
        cmap   = plt.cm.tab20
        colors = {cat: cmap(i) for i, cat in enumerate(categories)}

    warn_unmatched_provinces(data_df.index, gdf[province_col], context=title or 'pie map')

    # Project to Web Mercator for true circles
    gdf_proj = gdf.to_crs(epsg=3857)
    gdf_proj = gdf_proj.merge(data_df, left_on=province_col, right_index=True, how='left')
    present  = [c for c in categories if c in gdf_proj.columns]
    gdf_proj[present] = gdf_proj[present].fillna(0)
    require_non_negative({c: gdf_proj[c].min() for c in present if gdf_proj[c].min() < 0},
                         context='capacity')
    gdf_proj['cx']          = gdf_proj.geometry.centroid.x
    gdf_proj['cy']          = gdf_proj.geometry.centroid.y
    gdf_proj['total_value'] = gdf_proj[present].sum(axis=1)

    bounds   = gdf_proj.total_bounds
    map_diag = np.sqrt((bounds[2] - bounds[0])**2 + (bounds[3] - bounds[1])**2)
    max_r    = map_diag * PIE_RADIUS_FRACTION * pie_scale

    # Radius scales with sqrt(value) so *area* — not radius — is proportional
    # to the value, which is what a viewer actually perceives as "size".
    max_total = scale_max if scale_max is not None else max(gdf_proj['total_value'].max(), 1)
    gdf_proj['radius'] = (gdf_proj['total_value'] / max_total).clip(lower=0) ** 0.5 * max_r

    # Create figure only when no ax supplied
    owns_figure = ax is None
    if owns_figure:
        fig, ax = plt.subplots(figsize=figsize)

    ax.set_axis_off()

    if outline_gdf is not None:
        outline_gdf.to_crs(epsg=3857).plot(
            ax=ax, color='#F4F4F4', edgecolor='black', linewidth=0.7, zorder=-1)

    gdf_proj.plot(ax=ax, color='#F4F4F4', edgecolor='black', linewidth=0.7, zorder=0)
    gdf_proj.boundary.plot(ax=ax, linewidth=0.7, color='black', zorder=1)

    for _, row in gdf_proj.iterrows():
        cx, cy, r = row['cx'], row['cy'], row['radius']
        vals  = np.array([row[c] if c in row.index else 0.0 for c in present], dtype=float)
        total = vals.sum()
        if total == 0 or r == 0:
            continue
        angles     = np.cumsum(vals) / total * 360
        prev_angle = 0.0
        for cat, end_angle in zip(present, angles):
            ax.add_patch(Wedge(
                center=(cx, cy), r=r,
                theta1=prev_angle, theta2=end_angle,
                facecolor=colors.get(cat, '#cccccc'),
                edgecolor='white', linewidth=0.6, zorder=1000,
            ))
            prev_angle = end_angle

    if include_color_legend:
        patches = [mpatches.Patch(color=colors.get(c, '#cccccc'), label=c) for c in categories]
        ax.legend(handles=patches, loc='lower right', fontsize=8, framealpha=0.9,
                  title='Technology', title_fontsize=9)

    if include_size_legend and legend_sizes:
        legend_radii = [(s / max_total) ** 0.5 * max_r for s in legend_sizes]
        xlim, ylim   = ax.get_xlim(), ax.get_ylim()
        px  = (xlim[1] - xlim[0]) * 0.02
        py  = (ylim[1] - ylim[0]) * 0.02
        mr  = max(legend_radii)
        lcx = xlim[0] + px + mr
        y   = ylim[0] + py
        for size, radius in sorted(zip(legend_sizes, legend_radii)):
            cy_l = y + radius
            ax.add_patch(Circle(
                (lcx, cy_l), radius,
                facecolor='white', edgecolor='#555555', linewidth=1.2, zorder=2000))
            display_val = size * unit_scale
            ax.text(lcx + mr + px * 0.6, cy_l, f'{format_quantity(display_val)} {capacity_unit}',
                    va='center', ha='left', fontsize=9, zorder=2001)
            y += radius * 2 + py * 0.4

    ax.set_title(title, fontsize=12)

    if owns_figure:
        plt.tight_layout()
        plt.show()


def draw_size_legend(ax, legend_sizes, max_total, capacity_unit='MW', unit_scale=1.0):
    """Draw reference circles (area encodes value) in a horizontal row on their
    own dedicated axis, smallest to largest, left to right.

    Kept on a separate axis (rather than overlaid on a map subplot) so the
    legend never eats into a map's visible area.
    """
    ax.set_axis_off()
    if not legend_sizes:
        return

    sizes    = sorted(legend_sizes)
    ref_max_r = 1.0
    radii    = [(s / max_total) ** 0.5 * ref_max_r for s in sizes]
    gap      = ref_max_r * 1.8  # generous enough to clear the value labels below

    centers = []
    x = 0.0
    for r in radii:
        x += r
        centers.append(x)
        x += r + gap

    ax.set_xlim(-gap * 0.5, x - gap * 0.5)
    ax.set_ylim(-ref_max_r * 1.6, ref_max_r * 1.6)
    ax.set_aspect('equal', adjustable='box')

    for size, r, cx in zip(sizes, radii, centers):
        ax.add_patch(Circle(
            (cx, 0), r, facecolor='white', edgecolor='#555555',
            linewidth=1.2, zorder=10))
        display_val = size * unit_scale
        ax.text(cx, -r - ref_max_r * 0.3, f'{format_quantity(display_val)} {capacity_unit}',
                va='top', ha='center', fontsize=9)
