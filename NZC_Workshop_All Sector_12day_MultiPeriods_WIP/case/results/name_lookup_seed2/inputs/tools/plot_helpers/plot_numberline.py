"""Uniform province pies arranged left-to-right by total capacity on a number line."""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Wedge
from .formatting import format_quantity

PIE_RADIUS            = 0.38   # radius in rank-spacing units
FIGSIZE_WIDTH_PER_PIE = 0.9    # inches per province
FIGSIZE_HEIGHT        = 4.5    # figure height


def plot_sector_numberline(sector_name, renamed_dfs, period_labels, categories, colors, unit,
                           unit_scale=1.0):
    """
    Draw uniform-size province pies sorted by total capacity (one figure per scenario).
    unit_scale: multiply capacity values before labelling (e.g. 8760/1e6 for T/hr → Mt/yr).
    All pies are the same radius so technology proportions are directly comparable.
    """
    if renamed_dfs is None or categories is None:
        print(f'{sector_name}: no data for numberline plot.')
        return

    for label in period_labels:
        df = renamed_dfs.get(label)
        if df is None or df.empty:
            print(f'{sector_name} [{label}]: no data for numberline plot.')
            continue

        totals   = df.sum(axis=1)
        has_data = totals[totals > 0].sort_values()
        if has_data.empty:
            print(f'{sector_name} [{label}]: no non-zero provinces for numberline.')
            continue

        n         = len(has_data)
        provinces = list(has_data.index)
        fig_w     = max(10, n * FIGSIZE_WIDTH_PER_PIE)
        fig, ax   = plt.subplots(figsize=(fig_w, FIGSIZE_HEIGHT))
        ax.set_aspect('equal')
        ax.set_axis_off()

        ax.axhline(0, xmin=0.02, xmax=0.98, color='#aaaaaa', linewidth=1.0, zorder=0)
        ax.annotate('', xy=(n - 0.1, 0), xytext=(n - 0.5, 0),
                    arrowprops=dict(arrowstyle='->', color='#aaaaaa', lw=1.2))

        for i, prov in enumerate(provinces):
            x    = float(i)
            vals = df.loc[prov].reindex(categories, fill_value=0).values.astype(float)
            if vals.sum() == 0:
                continue
            angles = np.cumsum(vals) / vals.sum() * 360
            prev   = 0.0
            for cat, end in zip(categories, angles):
                ax.add_patch(Wedge(
                    center=(x, 0), r=PIE_RADIUS,
                    theta1=prev, theta2=end,
                    facecolor=colors.get(cat, '#cccccc'),
                    edgecolor='white', linewidth=0.5, zorder=10,
                ))
                prev = end
            label_val = has_data[prov] * unit_scale
            ax.text(x, PIE_RADIUS + 0.08, format_quantity(label_val),
                    ha='center', va='bottom', fontsize=6.5, color='#444444')
            ax.text(x, -PIE_RADIUS - 0.08, prov,
                    ha='right', va='top', fontsize=7.5, rotation=40, rotation_mode='anchor')

        ax.set_xlim(-0.8, n + 0.2)
        ax.set_ylim(-2.2, 1.4)
        ax.text(-0.6, -1.8, f'← less {unit}', fontsize=8, color='#777777', va='center')
        ax.text(n - 0.5, -1.8, f'more {unit} →', fontsize=8, color='#777777',
                va='center', ha='right')
        ax.set_title(
            f'{sector_name} — Technology Mix by Province ({label})\n'
            f'All pies same size · ordered left→right by total {unit}',
            fontsize=11, pad=8,
        )
        active  = [c for c in categories if (c in df.columns) and df[c].sum() > 0]
        patches = [mpatches.Patch(color=colors.get(c, '#cccccc'), label=c) for c in active]
        ax.legend(handles=patches, bbox_to_anchor=(1.01, 1), loc='upper left',
                  fontsize=8, framealpha=0.9, title='Technology', title_fontsize=9)
        plt.tight_layout()
        plt.show()
