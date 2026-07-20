"""Transport flow maps: capacity pies with transport arrows overlaid, series layout."""

import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch, Wedge
from .formatting import format_quantity
from .validation import require_non_negative, warn_unmatched_provinces

# Matches source (always a Region) and destination (province or named storage site).
# e.g. Region1Beijing_to_Region3Hebei_cement OR Region1Beijing_to_BohaiOnshore_CO2_Pipeline
_TRANSPORT_RE = re.compile(r'(Region\d+.+?)_to_([A-Za-z][A-Za-z0-9]*)')

MAP_WIDTH_PER_PERIOD = 8   # inches per subplot column
MAP_HEIGHT           = 8   # figure height
_LEGEND_W_IN         = 1.4 # inches reserved on the right for the arrow scale legend


def _province_from_region(token):
    m = re.match(r'Region\d+(.+)', token)
    return m.group(1) if m else token


def _parse_transport(resource_id):
    m = _TRANSPORT_RE.search(str(resource_id))
    if not m:
        return None, None
    return _province_from_region(m.group(1)), _province_from_region(m.group(2))


def _get_transport_flows(cap_df, commodity, cap_col='capacity'):
    """Extract transport capacity, deduplicated: one arrow per province pair (dominant direction)."""
    trans = cap_df[
        cap_df['resource_type'].str.contains('Transmission', na=False) &
        (cap_df['commodity'] == commodity)
    ].copy()
    if trans.empty:
        return pd.DataFrame(columns=['src', 'dst', cap_col])

    parsed = trans['resource_id'].apply(
        lambda r: pd.Series(_parse_transport(r), index=['src', 'dst'])
    )
    trans = trans.join(parsed).dropna(subset=['src', 'dst'])
    flows = trans.groupby(['src', 'dst'])[cap_col].sum().reset_index()
    flows = flows[flows[cap_col] > 0].copy()

    # Deduplicate bidirectional pairs: keep only the dominant direction
    flows['_key'] = flows.apply(
        lambda r: tuple(sorted([r['src'], r['dst']])), axis=1
    )
    flows = flows.sort_values(cap_col, ascending=False).drop_duplicates(subset='_key')
    return flows.drop(columns='_key').reset_index(drop=True)


def _draw_base(ax, gdf_proj, gdf_outline_proj=None):
    ax.set_axis_off()
    if gdf_outline_proj is not None:
        gdf_outline_proj.plot(ax=ax, color='#F4F4F4', edgecolor='black', linewidth=0.7, zorder=-1)
    gdf_proj.plot(ax=ax, color='#F4F4F4', edgecolor='black', linewidth=0.7, zorder=0)
    gdf_proj.boundary.plot(ax=ax, linewidth=0.7, color='black', zorder=1)


def _draw_pies(ax, gdf_proj, data_df, categories, colors, scale_max, max_r):
    """Draw capacity pie wedges at zorder=1500 — on top of arrows."""
    if data_df is None or data_df.empty:
        return
    warn_unmatched_provinces(data_df.index, gdf_proj['NAME_1'], context='transport pies')
    gdf_work = gdf_proj.merge(data_df, left_on='NAME_1', right_index=True, how='left')
    present  = [c for c in categories if c in gdf_work.columns]
    if not present:
        return
    gdf_work[present]       = gdf_work[present].fillna(0)
    require_non_negative({c: gdf_work[c].min() for c in present if gdf_work[c].min() < 0},
                         context='capacity')
    gdf_work['total_value'] = gdf_work[present].sum(axis=1)
    # sqrt so *area*, not radius, tracks the value (matches plot_province_pies).
    gdf_work['radius']      = (gdf_work['total_value'] / max(scale_max, 1)).clip(lower=0) ** 0.5 * max_r

    for _, row in gdf_work.iterrows():
        cx, cy, r = row['cx'], row['cy'], row['radius']
        vals  = np.array([row.get(c, 0.0) for c in present], dtype=float)
        total = vals.sum()
        if total == 0 or r == 0:
            continue
        angles = np.cumsum(vals) / total * 360
        prev   = 0.0
        for cat, end in zip(present, angles):
            ax.add_patch(Wedge(
                (cx, cy), r, prev, end,
                facecolor=colors.get(cat, '#cccccc'),
                edgecolor='white', linewidth=0.6, zorder=1500,
            ))
            prev = end


def _select_display_flows(flows, cap_col, top_n=None, min_fraction=0.02, max_flow=1.0):
    """Return the subset of flows actually drawn on the map (shared by arrows + legend)."""
    if flows is None or flows.empty:
        return flows.iloc[0:0] if flows is not None else pd.DataFrame(columns=['src', 'dst', cap_col])
    return flows.nlargest(top_n, cap_col) if top_n is not None else \
           flows[flows[cap_col] >= max_flow * min_fraction]


def _flow_to_lw(flow_val, max_flow, min_lw, max_lw):
    """Log-normalised line/tail width for a flow value, shared by arrows and legend."""
    norm = float(np.clip(np.log1p(flow_val) / np.log1p(max_flow), 0, 1))
    return min_lw + (max_lw - min_lw) * norm, norm


def _draw_arrows(ax, display, centroids, max_flow, cap_col, fig_dpi,
                 arrow_color='#34495e', max_lw=7.0, min_lw=0.8):
    """
    Draw transport arrows (zorder ~1000, below pies) for an already-filtered `display` DataFrame.
    Width is log-normalised so small and large flows are both visible.
    Arrows are semi-transparent (alpha=0.5) so pies drawn on top remain readable.
    """
    if display is None or display.empty:
        return

    missing = set()
    for _, row in display.sort_values(cap_col).iterrows():
        src, dst = row['src'], row['dst']
        if src not in centroids.index: missing.add(src); continue
        if dst not in centroids.index: missing.add(dst); continue
        x0, y0 = centroids.loc[src, 'cx'], centroids.loc[src, 'cy']
        x1, y1 = centroids.loc[dst, 'cx'], centroids.loc[dst, 'cy']

        tail_w, norm = _flow_to_lw(row[cap_col], max_flow, min_lw, max_lw)

        # Arrow length in points (display pixels converted via fig dpi) — caps head
        # proportions for very short routes so heads don't dwarf the shaft.
        p0 = np.array(ax.transData.transform((x0, y0)))
        p1 = np.array(ax.transData.transform((x1, y1)))
        display_len_pt = max(float(np.linalg.norm(p1 - p0)) / fig_dpi * 72, 1.0)

        tail_w   = min(tail_w, display_len_pt * 0.30)
        head_len = min(tail_w * 2.5, display_len_pt * 0.25)
        head_wid = tail_w * 2.0

        style = (f'simple,head_width={head_wid:.2f},'
                 f'head_length={head_len:.2f},tail_width={tail_w:.2f}')
        ax.add_patch(FancyArrowPatch(
            (x0, y0), (x1, y1),
            arrowstyle=style,
            facecolor=arrow_color,
            edgecolor='none',
            alpha=0.5,
            shrinkA=0, shrinkB=0,
            zorder=1000 + int(norm * 50),
        ))
    if missing:
        print(f'  WARNING: centroids not found for {sorted(missing)}')


def plot_transport_series(
    commodity,
    all_cap,
    period_labels,
    gdf,
    gdf_outline=None,
    capacity_renamed_dfs=None,
    pie_categories=None,
    pie_colors=None,
    pie_scale=1.0,
    cap_col='capacity',
    unit='T/hr',
    arrow_color='#34495e',
    max_linewidth=7.0,
    min_linewidth=0.8,
    top_n=30,
    min_flow_fraction=0.02,
    **_ignored,   # absorb deprecated kwargs without error
):
    """
    One combined map series: capacity pies with transport arrows overlaid.
    One figure, all periods in a row. Pies drawn on top of (semi-transparent) arrows.

    Arrows are monochromatic (arrow_color) — only width encodes magnitude.
    Width is log-normalised so both tiny and large flows are visible.
    Bidirectional pairs are deduplicated: only the dominant direction is shown.

    An arrow-scale legend is drawn to the right of all maps (outside the map area).
    """
    # ── Project GDF ───────────────────────────────────────────────────────────
    gdf_proj         = gdf.to_crs(epsg=3857).copy()
    gdf_proj['cx']   = gdf_proj.geometry.centroid.x
    gdf_proj['cy']   = gdf_proj.geometry.centroid.y
    centroids        = gdf_proj.set_index('NAME_1')[['cx', 'cy']]
    gdf_outline_proj = gdf_outline.to_crs(epsg=3857) if gdf_outline is not None else None

    bounds   = gdf_proj.total_bounds
    map_diag = np.sqrt((bounds[2] - bounds[0])**2 + (bounds[3] - bounds[1])**2)
    max_r    = map_diag * 0.03 * pie_scale

    # ── Pie scale_max ─────────────────────────────────────────────────────────
    has_pies    = (capacity_renamed_dfs is not None
                   and pie_categories is not None
                   and pie_colors is not None)
    pie_scale_max = 1
    if has_pies:
        pie_scale_max = max(
            (df.sum(axis=1).max() for df in capacity_renamed_dfs.values() if not df.empty),
            default=1,
        ) or 1

    # ── Extract + deduplicate transport flows ─────────────────────────────────
    all_flows = {}
    for label in period_labels:
        cap_df = all_cap.get(label)
        if cap_df is None or cap_df.empty or cap_col not in cap_df.columns:
            all_flows[label] = pd.DataFrame(columns=['src', 'dst', cap_col])
        else:
            all_flows[label] = _get_transport_flows(cap_df, commodity, cap_col)

    max_flow = max(
        (f[cap_col].max() for f in all_flows.values()
         if not f.empty and cap_col in f.columns and len(f) > 0),
        default=1,
    ) or 1

    # Filter to the same subset that will actually be drawn, once, so the arrows
    # and the scale legend are guaranteed to reflect the same data.
    all_display = {
        label: _select_display_flows(all_flows[label], cap_col, top_n, min_flow_fraction, max_flow)
        for label in period_labels
    }
    displayed_vals = pd.concat(
        [d[cap_col] for d in all_display.values() if not d.empty]
    ) if any(not d.empty for d in all_display.values()) else pd.Series(dtype=float)

    # ── Figure: extra width on the right for the arrow scale legend ───────────
    n          = len(period_labels)
    maps_w     = max(12, n * MAP_WIDTH_PER_PERIOD)
    total_w    = maps_w + _LEGEND_W_IN
    maps_frac  = maps_w / total_w   # fraction of figure width used by maps

    fig, axes = plt.subplots(1, n, figsize=(total_w, MAP_HEIGHT), squeeze=False)
    axes = axes[0]

    # Constrain subplots to the left maps_frac of the figure
    fig.subplots_adjust(left=0.01, right=maps_frac - 0.01, top=0.93, bottom=0.05)

    for ax, label in zip(axes, period_labels):
        _draw_base(ax, gdf_proj, gdf_outline_proj)
        ax.set_title(label, fontsize=10)

        # Arrows first (lower zorder), pies on top
        display = all_display[label]
        if display.empty:
            ax.text(0.5, 0.5, 'no transport data', transform=ax.transAxes,
                    ha='center', va='center', color='gray', fontsize=9)
        else:
            _draw_arrows(ax, display, centroids, max_flow, cap_col, fig.dpi,
                         arrow_color=arrow_color,
                         max_lw=max_linewidth, min_lw=min_linewidth)

        if has_pies:
            data_df = capacity_renamed_dfs.get(label)
            if data_df is not None and not data_df.empty:
                _draw_pies(ax, gdf_proj.copy(), data_df, pie_categories, pie_colors,
                           pie_scale_max, max_r)

    fig.suptitle(
        f'{commodity} — Capacity + Transport Flows\n'
        f'Arrow width ∝ transport capacity ({unit}, log scale) · top {top_n} corridors',
        fontsize=13,
    )

    if has_pies:
        patches = [mpatches.Patch(color=pie_colors.get(c, '#cccccc'), label=c)
                   for c in pie_categories]
        fig.legend(handles=patches, loc='lower center',
                   ncol=min(len(pie_categories), 6),
                   bbox_to_anchor=(maps_frac / 2, -0.01), fontsize=9,
                   title='Technology', title_fontsize=10, framealpha=0.9)

    # ── Arrow scale legend: dedicated axes to the right of all maps ───────────
    last_pos  = axes[-1].get_position()
    leg_left  = maps_frac + 0.01
    leg_ax    = fig.add_axes([
        leg_left,
        last_pos.y0 + last_pos.height * 0.10,
        (1.0 - leg_left - 0.01),
        last_pos.height * 0.70,
    ])
    _draw_arrow_scale_legend(leg_ax, displayed_vals, max_flow, unit,
                             max_linewidth, min_linewidth, arrow_color)

    plt.show()


def _draw_arrow_scale_legend(ax, displayed_vals, max_flow, unit, max_lw, min_lw, arrow_color):
    """
    Draw a scale legend for arrow widths in a dedicated axes.

    Reference lines are drawn at the max, median, and min of the flows actually
    displayed on the map (not arbitrary fractions of the theoretical max) — so the
    legend always spans the real range a viewer sees, even when the distribution
    is heavily skewed (a few large corridors, many small ones). Line widths use the
    same log-normalisation as _draw_arrows, so the visual correspondence is exact.
    """
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_facecolor('white')
    for spine in ax.spines.values():
        spine.set_edgecolor('#cccccc')
        spine.set_linewidth(0.8)
    ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)

    ax.text(0.5, 0.96, f'Flow\n({unit})',
            ha='center', va='top', fontsize=7, fontweight='bold')

    if displayed_vals is None or displayed_vals.empty:
        ax.text(0.5, 0.5, 'no data', ha='center', va='center', fontsize=8, color='gray')
        return

    ref_vals = sorted({displayed_vals.max(), displayed_vals.median(), displayed_vals.min()},
                      reverse=True)
    n = len(ref_vals)

    for i, flow_val in enumerate(ref_vals):
        lw, _ = _flow_to_lw(flow_val, max_flow, min_lw, max_lw)
        # y position: evenly spaced in lower 75% of the axes
        y = 0.72 - i * (0.60 / (n - 1)) if n > 1 else 0.5

        ax.plot([0.08, 0.62], [y, y], color=arrow_color, linewidth=lw,
                solid_capstyle='butt')

        ax.text(0.66, y, format_quantity(flow_val), ha='left', va='center', fontsize=6.5)
