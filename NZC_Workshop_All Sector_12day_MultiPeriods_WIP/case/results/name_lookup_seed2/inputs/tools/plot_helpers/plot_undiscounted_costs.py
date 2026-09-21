"""Charts of MacroEnergy.jl's own system-wide undiscounted cost totals --
Investment / FixedOM / VariableOM / Startup / Supply / NonServedDemand /
UnmetPolicyPenalty -- read directly from undiscounted_costs_by_type.csv, not
recomputed. See compute_costs.py / plot_cost_breakdowns.py for the separate
per-asset, $/unit-of-output *levelized* cost breakdown -- a different metric
built from flows + fuel prices, not the model's own cost accounting.

by_type DataFrames are wide, matching undiscounted_costs_by_type.csv on disk:
one row per resource type (plus a "Total" type row already summed across
every technology), one column per cost category (plus a row-wise "Total"
column). Every function here works directly on that shape.
"""

import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from .run_output import save_and_or_show, safe_filename

FIGSIZE_WIDTH_PER_PERIOD = 1.8
FIGSIZE_HEIGHT           = 6

# raw category (as it appears in undiscounted_costs_by_type.csv) -> (display label, color)
CATEGORY_STYLE = {
    'Investment':         ('Investment',              '#c05050'),
    'FixedOM':             ('Fixed O&M',                '#c1558f'),
    'VariableOM':           ('Variable O&M',              '#6aab6a'),
    'Startup':             ('Startup',                 '#e8a838'),
    'Supply':              ('Fuel / Commodity Supply',  '#4e6a8c'),
    'NonServedDemand':     ('Non-Served Demand',       '#b0b0b0'),
    'UnmetPolicyPenalty':  ('Unmet Policy Penalty',    '#707070'),
}
_DEFAULT_COLOR = '#aaaaaa'


def _category_totals(by_type_df):
    """category -> value, from the 'Total' type row (already summed across every technology)."""
    if by_type_df.empty:
        return pd.Series(dtype=float)
    row = by_type_df[by_type_df['type'] == 'Total']
    if row.empty:
        return pd.Series(dtype=float)
    return row.iloc[0].drop(['type', 'Total'], errors='ignore').astype(float)


def plot_undiscounted_cost_bars(cost_data_by_period, period_labels, unit='$B', unit_scale=1e-9,
                                show=True, output_dir=None, dpi=150):
    """Stacked bar: x = scenario/period, bars = cost category.

    unit_scale: multiply raw $ values before plotting (default 1e-9 -> $ billions).
    """
    per_period_totals = {
        label: _category_totals(cost_data_by_period[label]['by_type'])
        for label in period_labels if label in cost_data_by_period
    }
    per_period_totals = {l: t for l, t in per_period_totals.items() if not t.empty}
    if not per_period_totals:
        print('No undiscounted cost data found in any loaded scenario.')
        return

    known_categories = list(CATEGORY_STYLE.keys())
    all_seen = {c for totals in per_period_totals.values() for c in totals.index}
    unknown  = sorted(all_seen - set(known_categories))
    categories = [
        c for c in known_categories + unknown
        if any(per_period_totals[l].get(c, 0.0) != 0 for l in per_period_totals)
    ]
    if not categories:
        print('Undiscounted costs are zero in all loaded scenarios.')
        return

    present_periods = [l for l in period_labels if l in per_period_totals]
    n = len(present_periods)
    fig, ax = plt.subplots(figsize=(max(6, n * FIGSIZE_WIDTH_PER_PERIOD), FIGSIZE_HEIGHT))

    bottom = np.zeros(n)
    for cat in categories:
        vals = np.array([per_period_totals[l].get(cat, 0.0) for l in present_periods]) * unit_scale
        label, color = CATEGORY_STYLE.get(cat, (cat, _DEFAULT_COLOR))
        ax.bar(present_periods, vals, bottom=bottom, color=color, label=label,
              edgecolor='white', linewidth=0.5)
        bottom += vals

    ax.set_xlabel('Scenario', fontsize=11)
    ax.set_ylabel(f'Undiscounted System Cost ({unit})', fontsize=11)
    ax.set_title('Undiscounted System Cost by Category and Scenario', fontsize=13)
    ax.legend(loc='upper left', bbox_to_anchor=(1.01, 1), fontsize=9,
             title='Cost Category', title_fontsize=10, framealpha=0.9)
    plt.xticks(rotation=20, ha='right')
    plt.tight_layout()
    save_and_or_show(fig, 'undiscounted_cost_bars', show, output_dir, dpi)


def plot_undiscounted_cost_by_tech(cost_data_by_period, period_labels, top_n=15,
                                   unit='$B', unit_scale=1e-9,
                                   show=True, output_dir=None, dpi=150):
    """Horizontal stacked bar per period: the top_n technology types by total
    undiscounted cost, stacked by category.

    'type' here is the raw MacroEnergy.jl asset/edge type (e.g.
    'ThermalPower{Coal}', 'Node{NaturalGas}') -- one chart per period, since
    which technologies dominate cost can differ period to period.
    """
    for label in period_labels:
        if label not in cost_data_by_period:
            continue
        df = cost_data_by_period[label]['by_type']
        if df.empty:
            continue
        df = df[df['type'] != 'Total'].drop(columns=['Total'], errors='ignore').set_index('type')
        if df.empty:
            print(f'  {label}: no technology-level undiscounted cost data -- skipping.')
            continue

        totals_by_tech = df.sum(axis=1).sort_values(ascending=False)
        top_types = list(totals_by_tech.head(top_n).index)

        pivot = df.loc[top_types] * unit_scale  # keep cost-descending order

        categories = [c for c in CATEGORY_STYLE if c in pivot.columns] + \
                    [c for c in pivot.columns if c not in CATEGORY_STYLE]

        y = np.arange(len(top_types))
        fig, ax = plt.subplots(figsize=(9, max(4, 0.4 * len(top_types))))

        left = np.zeros(len(top_types))
        for cat in categories:
            vals = pivot[cat].values
            disp_label, color = CATEGORY_STYLE.get(cat, (cat, _DEFAULT_COLOR))
            ax.barh(y, vals, left=left, color=color, label=disp_label, edgecolor='white', linewidth=0.5)
            left += vals

        ax.set_yticks(y)
        ax.set_yticklabels(top_types, fontsize=8)
        ax.invert_yaxis()  # largest cost at top
        ax.set_xlabel(f'Undiscounted Cost ({unit})', fontsize=11)
        title = f'Undiscounted Cost by Technology — {label}' if len(period_labels) > 1 \
               else 'Undiscounted Cost by Technology'
        ax.set_title(title, fontsize=13)
        ax.legend(loc='upper left', bbox_to_anchor=(1.01, 1), fontsize=9,
                 title='Cost Category', title_fontsize=10, framealpha=0.9)
        plt.tight_layout()
        save_and_or_show(fig, safe_filename(f'undiscounted_cost_by_tech_{label}'), show, output_dir, dpi)


def build_undiscounted_cost_summary_csv(cost_data_by_period, output_path=None):
    """Wide table: rows = cost category, columns = period/scenario -- the
    'Total' type row of each period's undiscounted_costs_by_type.csv.
    """
    cols = {
        label: _category_totals(data['by_type'])
        for label, data in cost_data_by_period.items()
    }
    cols = {l: c for l, c in cols.items() if not c.empty}
    if not cols:
        return pd.DataFrame()

    summary = pd.DataFrame(cols)
    if output_path:
        summary.to_csv(output_path)
        print(f'  Saved summary CSV: {output_path}')
    return summary


def plot_undiscounted_costs(cost_data_by_period, period_labels, top_n=15,
                            show=True, output_dir=None, dpi=150):
    """Orchestrate every undiscounted-cost chart for the given periods/scenarios:
    the cross-scenario category bar chart, a per-period technology breakdown,
    and (if output_dir is given) a summary CSV.

    cost_data_by_period: {label: data} from resolve_undiscounted_costs()
                        (or a single-entry dict for one period/scenario).

    Returns the summary DataFrame (rows = category, columns = period).
    """
    plot_undiscounted_cost_bars(cost_data_by_period, period_labels, show=show, output_dir=output_dir, dpi=dpi)
    plot_undiscounted_cost_by_tech(cost_data_by_period, period_labels, top_n=top_n,
                                   show=show, output_dir=output_dir, dpi=dpi)

    summary_path = None
    if output_dir is not None:
        os.makedirs(output_dir, exist_ok=True)
        summary_path = os.path.join(output_dir, 'undiscounted_cost_summary.csv')
    return build_undiscounted_cost_summary_csv(cost_data_by_period, output_path=summary_path)
