"""Stacked bar chart of national capacity totals by technology, one bar per scenario."""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

FIGSIZE_WIDTH_PER_PERIOD = 1.8  # inches per bar
FIGSIZE_HEIGHT           = 6    # chart height


def plot_capacity_bars(sector_name, renamed_dfs, period_labels, categories, colors, unit,
                       unit_scale=1.0):
    """
    Draw stacked bar chart aggregated to national totals.
    unit_scale: multiply raw capacity values before display (e.g. 8760/1e6 for T/hr → Mt/yr).
    Zero-capacity techs are omitted.
    """
    totals = pd.DataFrame({
        label: renamed_dfs[label].sum()
        for label in period_labels
        if label in renamed_dfs and not renamed_dfs[label].empty
    }).reindex(categories).fillna(0)

    if unit_scale != 1.0:
        totals *= unit_scale

    totals = totals.loc[totals.sum(axis=1) > 0]
    if totals.empty:
        print(f'{sector_name}: no capacity to plot in bar chart.')
        return

    present_periods = [l for l in period_labels if l in totals.columns]
    n     = len(present_periods)
    fig_w = max(6, n * FIGSIZE_WIDTH_PER_PERIOD)
    fig, ax = plt.subplots(figsize=(fig_w, FIGSIZE_HEIGHT))

    bottom = np.zeros(n)
    for tech in totals.index:
        vals = totals.loc[tech, present_periods].values
        ax.bar(present_periods, vals, bottom=bottom,
               color=colors.get(tech, '#888888'), label=tech,
               edgecolor='white', linewidth=0.5)
        bottom += vals

    ax.set_xlabel('Scenario', fontsize=11)
    ax.set_ylabel(f'National Capacity ({unit})', fontsize=11)
    ax.set_title(f'{sector_name} — National Capacity by Scenario', fontsize=13)
    ax.legend(loc='upper left', bbox_to_anchor=(1.01, 1),
              fontsize=9, title='Technology', title_fontsize=10, framealpha=0.9)
    plt.xticks(rotation=20, ha='right')
    plt.tight_layout()
    plt.show()
