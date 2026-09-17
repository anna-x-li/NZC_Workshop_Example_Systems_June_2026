"""Stacked bar chart of national CO2 emissions broken down by technology within each sector."""

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from .extract_co2 import extract_co2_emissions

FIGSIZE_WIDTH_PER_PERIOD = 1.8
FIGSIZE_HEIGHT           = 4.5


def plot_co2_bar(all_flows, period_labels, co2_edge_map, sector_co2_colors,
                 tech_co2_colors=None, all_weights=None):
    """
    Draw stacked CO2 bar chart. Y-axis in megatonnes (Mt).

    Supports two modes depending on co2_edge_map value type:
      str   → stacked by sector (legacy, one colour per sector)
      tuple → stacked by technology within each sector (new, uses tech_co2_colors)

    Gross emissions and CCS/BECCS capture are kept as separate segments rather
    than netted together: each key's gross-emission total stacks upward in its
    normal color, and — only if that key has any capture at all — a second,
    lighter (alpha-reduced) segment for its captured CO2 stacks downward below
    zero, labeled "... (CCS captured)". This makes both "how much was emitted"
    and "how much was captured" visible as two distinct numbers, rather than
    only ever showing their net.

    all_weights: {label: time_weights Series} from load_period_data().  When provided,
                 CO2 flows are multiplied by their time weights before summing, giving
                 true annual totals in tonnes (weights sum to 8760 h/yr).

    tech_co2_colors: {tech_display_name: hex_color}. If None or key missing,
                     falls back to the sector colour from sector_co2_colors.
    """
    # ── Collect per-period data ───────────────────────────────────────────────
    co2_by_period = {}
    for label in period_labels:
        flows   = all_flows.get(label, pd.DataFrame())
        weights = (all_weights or {}).get(label)
        if not flows.empty:
            co2_by_period[label] = extract_co2_emissions(flows, co2_edge_map, time_weights=weights)

    if not co2_by_period:
        print('No CO2 data found in any loaded scenario.')
        return

    # ── Detect format from the first non-empty (pos or neg) result ────────────
    sample = next((pos or neg for pos, neg in co2_by_period.values() if pos or neg), {})
    tech_mode = bool(sample) and isinstance(next(iter(sample)), tuple)

    if not tech_mode:
        _plot_by_sector(co2_by_period, period_labels, sector_co2_colors)
    else:
        _plot_by_tech(co2_by_period, period_labels, sector_co2_colors,
                      tech_co2_colors or {}, co2_edge_map)


def _plot_by_sector(co2_by_period, period_labels, sector_co2_colors):
    """Legacy mode: one stacked segment per sector, gross emissions and CCS capture separate."""
    # Any sector present in the data but missing from sector_co2_colors still gets
    # plotted (with an auto-assigned color) rather than silently reindexed away —
    # mirrors build_sector_style's "unknown category" handling on the capacity side.
    known_sectors   = list(sector_co2_colors.keys())
    all_seen        = {s for pos, neg in co2_by_period.values() for s in list(pos) + list(neg)}
    unknown_sectors = sorted(all_seen - set(known_sectors))
    sectors         = known_sectors + unknown_sectors

    present_periods = [l for l in period_labels if l in co2_by_period]
    n               = len(present_periods)
    present_sectors = [
        s for s in sectors
        if any(co2_by_period[l][0].get(s, 0) != 0 or co2_by_period[l][1].get(s, 0) != 0
              for l in present_periods)
    ]

    if not present_sectors:
        print('CO2 emissions are zero in all loaded scenarios.')
        return

    fig, ax = plt.subplots(figsize=(max(6, n * FIGSIZE_WIDTH_PER_PERIOD), FIGSIZE_HEIGHT))
    bottom_pos     = np.zeros(n)
    bottom_neg     = np.zeros(n)
    cmap           = matplotlib.colormaps['tab20']
    legend_patches = []

    for i, sector in enumerate(present_sectors):
        pos_vals = np.array([co2_by_period[l][0].get(sector, 0.0) for l in present_periods])
        neg_vals = np.array([co2_by_period[l][1].get(sector, 0.0) for l in present_periods])
        color    = sector_co2_colors.get(sector) or cmap(i % 20)

        if pos_vals.sum() != 0:
            _stack_bar(ax, present_periods, pos_vals, color, sector, bottom_pos, bottom_neg)
            bottom_pos += pos_vals
            legend_patches.append(mpatches.Patch(color=color, label=sector))
        if neg_vals.sum() != 0:
            _stack_bar(ax, present_periods, neg_vals, color, f'{sector} (CCS captured)',
                      bottom_pos, bottom_neg, alpha=0.55)
            bottom_neg += neg_vals
            legend_patches.append(mpatches.Patch(color=color, alpha=0.55,
                                                 label=f'{sector} (CCS captured)'))

    ax.axhline(0, color='black', linewidth=0.8, zorder=5)
    _format_co2_axes(ax, 'National CO2 Emissions by Sector and Scenario')
    ax.legend(handles=legend_patches, loc='upper left', bbox_to_anchor=(1.01, 1),
              fontsize=9, title='Sector', title_fontsize=10, framealpha=0.9)
    plt.xticks(rotation=20, ha='right')
    plt.tight_layout()
    plt.show()


def _plot_by_tech(co2_by_period, period_labels, sector_co2_colors,
                  tech_co2_colors, co2_edge_map):
    """New mode: stacked by technology; sectors grouped by ordering in co2_edge_map.

    Each (sector, tech) key can contribute up to two segments per bar: its
    gross-emission total stacking upward (normal color), and — only if that
    key has any capture at all — its CCS-captured total stacking downward
    (same color, lighter) as a separate legend entry.
    """
    # Build ordered list of unique (sector, tech) keys from co2_edge_map insertion order
    seen  = set()
    order = []
    for val in co2_edge_map.values():
        if isinstance(val, tuple) and val not in seen:
            seen.add(val)
            order.append(val)

    all_keys = sorted(
        {k for pos, neg in co2_by_period.values() for k in list(pos) + list(neg)},
        key=lambda k: order.index(k) if k in order else 999,
    )
    # Include any key that is non-zero (positive OR negative) in at least one period
    present_keys = [
        k for k in all_keys
        if any(co2_by_period.get(l, ({}, {}))[0].get(k, 0) != 0 or
              co2_by_period.get(l, ({}, {}))[1].get(k, 0) != 0
              for l in period_labels)
    ]

    if not present_keys:
        print('CO2 emissions are zero in all loaded scenarios.')
        return

    present_periods = [l for l in period_labels if l in co2_by_period]
    n               = len(present_periods)
    fig, ax         = plt.subplots(figsize=(max(6, n * FIGSIZE_WIDTH_PER_PERIOD), FIGSIZE_HEIGHT))
    bottom_pos      = np.zeros(n)
    bottom_neg      = np.zeros(n)
    legend_patches  = []

    prev_sector = None

    for (sector, tech) in present_keys:
        pos_vals = np.array([co2_by_period.get(l, ({}, {}))[0].get((sector, tech), 0.0)
                             for l in present_periods])
        neg_vals = np.array([co2_by_period.get(l, ({}, {}))[1].get((sector, tech), 0.0)
                             for l in present_periods])
        color = tech_co2_colors.get(tech) or sector_co2_colors.get(sector, '#cccccc')

        if prev_sector != sector and prev_sector is not None:
            # Thin white separator line between sector groups at current bottom level
            for xi in range(n):
                y = bottom_pos[xi] if bottom_pos[xi] > 0 else bottom_neg[xi]
                ax.plot([xi - 0.4, xi + 0.4], [y, y],
                        color='white', linewidth=1.5, zorder=50)
        prev_sector = sector

        if pos_vals.sum() != 0:
            _stack_bar(ax, present_periods, pos_vals, color, f'{sector} — {tech}',
                      bottom_pos, bottom_neg)
            bottom_pos += pos_vals
            legend_patches.append(mpatches.Patch(color=color, label=f'{sector} — {tech}'))

        if neg_vals.sum() != 0:
            _stack_bar(ax, present_periods, neg_vals, color, f'{sector} — {tech} (CCS captured)',
                      bottom_pos, bottom_neg, alpha=0.55)
            bottom_neg += neg_vals
            legend_patches.append(mpatches.Patch(color=color, alpha=0.55,
                                                 label=f'{sector} — {tech} (CCS captured)'))

    # Horizontal zero line so net-zero is visually clear
    ax.axhline(0, color='black', linewidth=0.8, zorder=5)

    _format_co2_axes(ax, 'National CO2 Emissions by Technology and Scenario')
    ax.legend(handles=legend_patches, loc='upper left', bbox_to_anchor=(1.01, 1),
              fontsize=8, title='Sector — Technology', title_fontsize=9, framealpha=0.9)
    plt.xticks(rotation=20, ha='right')
    plt.tight_layout()
    plt.show()


def _stack_bar(ax, x_labels, vals, color, label, bottom_pos, bottom_neg, alpha=1.0):
    """Draw one bucket's bars, splitting positive and negative portions.

    In practice `vals` here is already single-signed (a pure gross-emission
    array or a pure CCS-capture array, never mixed) — but the pos/neg split
    is kept so this still degrades safely if a mixed-sign array is ever
    passed in directly.
    """
    pos = np.where(vals > 0, vals, 0)
    neg = np.where(vals < 0, vals, 0)
    kw  = dict(color=color, edgecolor='white', linewidth=0.3, alpha=alpha)
    if pos.sum() != 0:
        ax.bar(x_labels, pos, bottom=bottom_pos, label=label, **kw)
        label = None  # avoid duplicate legend entries
    if neg.sum() != 0:
        ax.bar(x_labels, neg, bottom=bottom_neg, label=label, **kw)


def _format_co2_axes(ax, title):
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x / 1e6:.1f}'))
    ax.set_xlabel('Scenario', fontsize=11)
    ax.set_ylabel('CO₂ Emissions (Mt)', fontsize=11)
    ax.set_title(title, fontsize=13)
