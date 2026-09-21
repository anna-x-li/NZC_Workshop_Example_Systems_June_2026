"""Load capacity.csv, flows.csv, and time_weights.csv from a MacroEnergy results folder."""

import pandas as pd
from pathlib import Path

CAPACITY_FILENAME     = 'capacity.csv'
FLOWS_FILENAME        = 'flows.csv'
TIME_WEIGHTS_FILENAME = 'time_weights.csv'


def load_period_data(results_dir):
    """Return (cap_df, flows_df, time_weights) from results_dir.

    time_weights is a Series indexed by time (values = hours each timestep represents,
    summing to 8760 for a full year).  None if time_weights.csv is absent.

    Raises FileNotFoundError if capacity.csv or flows.csv are missing.
    """
    p     = Path(results_dir)
    cap   = pd.read_csv(p / CAPACITY_FILENAME)
    flows = pd.read_csv(p / FLOWS_FILENAME)

    tw_path = p / TIME_WEIGHTS_FILENAME
    if tw_path.exists():
        tw           = pd.read_csv(tw_path)
        time_weights = tw.set_index('time')['weight']
    else:
        time_weights = None

    return cap, flows, time_weights
