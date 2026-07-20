"""Parse flows.csv to compute national CO2 emissions totals by sector and technology."""

import re
import pandas as pd

_REGION_PREFIX = re.compile(r'^Region\d+')


def _match_edge_suffix(col, co2_edge_map):
    """Return the co2_edge_map suffix this column matches, or None.

    Rather than guessing where the "Region<N><Province>_" prefix ends with a
    letters-only regex (which would misparse if a province name ever contained
    an underscore), this peels one underscore-separated token off the front at
    a time and checks the remainder against co2_edge_map directly — co2_edge_map
    already enumerates every valid suffix, so exact membership is a more
    reliable test than trying to (re-)derive the boundary independently.
    """
    m = _REGION_PREFIX.match(col)
    if not m:
        return None
    parts = col[m.end():].lstrip('_').split('_')
    for i in range(len(parts)):
        candidate = '_'.join(parts[i:])
        if candidate in co2_edge_map:
            return candidate
    return None


def extract_co2_emissions(flows_df, co2_edge_map, time_weights=None):
    """
    Sum national CO2 from flows_df, keeping gross emissions and CCS/BECCS
    capture as two separate totals per key rather than netting them together.

    co2_edge_map values can be:
      str         → {sector: total}           (legacy format)
      (str, str)  → {(sector, tech): total}   (new format for per-technology breakdown)

    A CCS/capture edge and its non-CCS parent are typically mapped to the same
    key (that's what lets the caller group and color them together). Each
    matched column's own weighted total is routed to the capture bucket or the
    emission bucket using two rules, in order:

      1. If the edge name contains "captured", it goes to the capture bucket
         as a negative amount (-abs(val)) regardless of its raw sign — most
         technologies report the physically-captured quantity in flows.csv as
         a *positive* number (tonnes captured), not as a negative offset, so
         sign alone can't be trusted for these.
      2. Otherwise, it's routed by its own raw sign — this covers ordinary
         positive emission edges, and also BECCS's "co2_edge", which the model
         already reports as a pre-computed *negative* net total (verified:
         BECCS's co2_edge == -(co2_emission_edge + co2_captured_edge) exactly,
         so BECCS's own "_captured_edge" must NOT also be mapped in
         co2_edge_map, or its capture would be counted twice).

    The two buckets are never added together here, so "how much was emitted"
    and "how much was captured" stay visible as two separate numbers all the
    way through, instead of only ever seeing their net.

    time_weights: optional Series indexed by time (same values as time_weights.csv).
      When provided, each flow timestep is multiplied by its weight before summing,
      giving annual totals (weights sum to 8760 h/yr).
      When None, a plain unweighted sum is used (suitable only if flows are already
      annual totals).

    Returns (pos_totals, neg_totals) — two dicts with a consistent key type
    (all str or all tuple) and only their own nonzero entries. neg_totals
    values are negative.
    """
    if flows_df.empty:
        return {}, {}

    # Build a weight array aligned to flows_df rows
    if time_weights is not None:
        if 'time' in flows_df.columns:
            weights_arr = time_weights.reindex(flows_df['time']).values
        else:
            weights_arr = time_weights.values[:len(flows_df)]
    else:
        weights_arr = None

    pos_totals = {}
    neg_totals = {}
    for col in flows_df.columns:
        suffix = _match_edge_suffix(col, co2_edge_map)
        if suffix is None:
            continue
        key = co2_edge_map[suffix]
        if weights_arr is not None:
            val = float((flows_df[col].values * weights_arr).sum())
        else:
            val = float(flows_df[col].sum())
        if val == 0:
            continue
        if 'captured' in suffix.lower():
            neg_totals[key] = neg_totals.get(key, 0.0) - abs(val)
        elif val > 0:
            pos_totals[key] = pos_totals.get(key, 0.0) + val
        else:
            neg_totals[key] = neg_totals.get(key, 0.0) + val

    return pos_totals, neg_totals
