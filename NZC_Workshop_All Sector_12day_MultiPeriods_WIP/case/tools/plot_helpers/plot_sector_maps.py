"""Orchestrate province pie maps for one sector across all scenarios (series layout)."""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from .extract_capacity   import extract_capacity, build_sector_style
from .plot_province_pies import plot_province_pies, draw_size_legend
from .formatting         import round_2sf

MAP_WIDTH_PER_PERIOD = 8     # inches per subplot column
MAP_HEIGHT           = 8     # figure height in inches
SIZE_LEGEND_HEIGHT   = 1.1   # inches for the horizontal size-legend row


def plot_sector_maps(
    sector_name,
    sector_cfg,
    all_cap,
    period_labels,
    gdf,
    gdf_outline,
    subtype_style,
    cap_col='capacity',
):
    """
    Plot all-periods province pie map series for one sector (one figure, periods in a row).

    Returns (categories, colors, renamed_dfs) — all None if no data found.
    sector_cfg may include 'exclude_types': list of resource_type values to drop
    (e.g. intermediate products like AluminumRefining).
    """
    commodities        = sector_cfg['commodities']
    unit               = sector_cfg['unit']
    pie_scale          = sector_cfg['pie_scale']
    unit_scale         = sector_cfg.get('unit_scale', 1.0)
    exclude_types      = sector_cfg.get('exclude_types', [])
    component_filters  = sector_cfg.get('component_filters', {})

    raw_dfs = {
        label: extract_capacity(
            all_cap.get(label, pd.DataFrame()), commodities, cap_col,
            exclude_resource_types=exclude_types,
            component_filters=component_filters,
        )
        for label in period_labels
    }

    if all(df.empty for df in raw_dfs.values()):
        print(f'{sector_name}: no data in any scenario — skipping maps.')
        return None, None, None

    # Explicit zero-capacity reporting
    for lbl, df in raw_dfs.items():
        if df.empty:
            continue
        zero_cols = [c for c in df.columns if df[c].sum() == 0]
        if zero_cols:
            zero_display = [subtype_style[c][0] if c in subtype_style else c for c in zero_cols]
            print(f'  INFO {sector_name} [{lbl}]: zero capacity — {", ".join(zero_display)}')

    categories, colors, renamed_dfs = build_sector_style(raw_dfs, subtype_style)
    if not categories:
        print(f'{sector_name}: all capacity values are zero — skipping maps.')
        return None, None, None

    # Shared scale_max so circle sizes are comparable across all period maps
    scale_max = max(
        (df.sum(axis=1).max() for df in renamed_dfs.values() if not df.empty),
        default=1,
    )
    legend_sizes = sorted({round_2sf(scale_max * f) for f in (0.25, 0.5, 1.0) if scale_max > 0})

    # ── Series layout: one figure, all periods in a row, plus a size-legend row ──
    n     = len(period_labels)
    fig_w = max(12, n * MAP_WIDTH_PER_PERIOD)
    fig   = plt.figure(figsize=(fig_w, MAP_HEIGHT + SIZE_LEGEND_HEIGHT))
    gs    = fig.add_gridspec(
        2, n, height_ratios=[MAP_HEIGHT, SIZE_LEGEND_HEIGHT], hspace=0.05,
    )
    axes       = [fig.add_subplot(gs[0, i]) for i in range(n)]
    legend_ax  = fig.add_subplot(gs[1, :])

    for i, (label, ax) in enumerate(zip(period_labels, axes)):
        df = renamed_dfs.get(label)
        if df is None or df.empty:
            ax.set_title(f'{label}\n(no data)', fontsize=10)
            ax.set_axis_off()
            continue
        plot_province_pies(
            gdf, df, ax=ax,
            title=label,
            categories=categories,
            colors=colors,
            pie_scale=pie_scale,
            scale_max=scale_max,
            capacity_unit=unit,
            unit_scale=unit_scale,
            outline_gdf=gdf_outline,
            include_color_legend=False,   # legend at figure level
            include_size_legend=False,    # drawn once, on its own row below
        )

    # Size legend on its own row — kept off every map so no period's map
    # shrinks or gets obscured to make room for it.
    draw_size_legend(
        legend_ax, legend_sizes, scale_max,
        capacity_unit=unit, unit_scale=unit_scale,
    )

    # Shared figure title and legend
    fig.suptitle(f'{sector_name} — Installed Capacity by Province', fontsize=14, y=1.02)
    legend_patches = [
        mpatches.Patch(color=colors.get(c, '#cccccc'), label=c) for c in categories
    ]
    fig.legend(
        handles=legend_patches,
        loc='lower center',
        ncol=min(len(categories), 6),
        bbox_to_anchor=(0.5, -0.03),
        fontsize=9,
        title='Technology',
        title_fontsize=10,
        framealpha=0.9,
    )
    plt.tight_layout()
    plt.show()

    return categories, colors, renamed_dfs
