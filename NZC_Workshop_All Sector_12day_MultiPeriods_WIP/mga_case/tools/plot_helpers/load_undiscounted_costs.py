"""Load undiscounted_costs*.csv (system-wide cost accounting) from a MacroEnergy results folder.

Distinct from load_cost_data.py / compute_costs.py, which build a per-asset,
$/unit-of-output *levelized* cost recipe from flows + fuel prices. The three
files loaded here are MacroEnergy.jl's own system-wide cost totals, already
computed and aggregated by the model -- nothing in this module recomputes
anything, it just reads what the model already wrote.
"""

import os
import pandas as pd

TOTALS_FILENAME  = 'undiscounted_costs.csv'           # FixedCost / VariableCost / TotalCost, one row each
BY_TYPE_FILENAME = 'undiscounted_costs_by_type.csv'   # wide: one row per type (+ a "Total" type row),
                                                       # one column per cost category (+ a row-wise "Total" column)
BY_ZONE_FILENAME = 'undiscounted_costs_by_zone.csv'   # zone x category (Investment/FixedOM/VariableOM only)
FULL_FILENAME     = 'undiscounted_costs_full.csv'     # zone x type x category -- large, opt-in only


def load_undiscounted_costs(results_dir, include_full=False):
    """Return {'totals', 'by_type', 'by_zone'[, 'full']} DataFrames from results_dir.

    results_dir is the folder directly containing the undiscounted_costs*.csv
    files -- same convention as load_data.load_period_data(), i.e. a
    config.PERIODS entry's path, not a folder-of-periods.

    Raises FileNotFoundError if undiscounted_costs_by_type.csv is missing --
    every plot function in plot_undiscounted_costs.py depends on it. The
    other files are optional and fall back to an empty DataFrame.
    """
    by_type_path = os.path.join(results_dir, BY_TYPE_FILENAME)
    if not os.path.exists(by_type_path):
        raise FileNotFoundError(by_type_path)

    def _read_if_present(filename):
        path = os.path.join(results_dir, filename)
        if os.path.exists(path):
            return pd.read_csv(path, encoding='utf-8-sig')
        return pd.DataFrame()

    data = {
        'totals':  _read_if_present(TOTALS_FILENAME),
        'by_type': pd.read_csv(by_type_path, encoding='utf-8-sig'),
        'by_zone': _read_if_present(BY_ZONE_FILENAME),
    }
    if include_full:
        data['full'] = _read_if_present(FULL_FILENAME)
    return data


def resolve_undiscounted_costs(periods, include_full=False):
    """
    Turn a period/scenario selection into {label: cost_data}, ready for
    plot_undiscounted_costs().

    periods: the same [(label, path), ...] list used everywhere else in the
            pipeline (config.PERIODS) -- path already points at the exact
            folder containing that period/scenario's CSVs.

    A period that fails to load (e.g. missing undiscounted_costs_by_type.csv)
    is skipped with a message rather than raising, matching how the rest of
    the pipeline handles a missing/incomplete results folder.
    """
    cost_data_by_period = {}
    for label, path in periods:
        try:
            cost_data_by_period[label] = load_undiscounted_costs(path, include_full=include_full)
        except FileNotFoundError as e:
            print(f'  [SKIP] {label}: {e}')
    return cost_data_by_period
